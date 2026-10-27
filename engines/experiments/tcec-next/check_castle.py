"""Render actual-source castle checks through the existing rules driver.

The caller authenticates modules and owns later plain/fatal-UBSan compilation,
command settlement and output admission. No I/O, C execution, process, engine,
TT, codec or production selection is performed here.
"""
from hashlib import sha256
import json


SCHEMA = "rove4k.actual-function-castle-fixture.v1"
PROFILE = "tcec-provisional"
ORACLE = dict(path="engines/tests/chess_oracle.py", bytes=10730,
    sha256="aea285b5b5f07602c829595840d5270fa8dc25683ccd26c63607435679024db8")
BASE = "r3k2r/8/8/8/8/8/8/R3K2R w - - 0 1"
RIGHTS = {"K": 1, "Q": 2, "k": 4, "q": 8}


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(data):
    return dict(bytes=len(data), sha256=sha256(data).hexdigest())


def _target(oracle, *, side, tag, own_rights=3, changes=()):
    board = oracle.Board.from_fen(BASE)
    board.turn = side > 0
    letters = "KQ" if side > 0 else "kq"
    board.castling = "".join(letter for bit, letter in enumerate(letters) if own_rights & (1 << bit))
    for square, piece in changes:
        board.cells[oracle.square(square)] = piece
    require(board.ep == -1 and board.halfmove == 0 and board.fullmove == 1,
            "fixed castle setup must have no EP and bounded counters")
    pieces = [0 if piece == "." else " pnbrqk".index(piece.lower()) *
              (1 if piece.isupper() else -1) for piece in board.cells]
    require(all(sum(value * colour > 0 for value in pieces) <= 16 for colour in (-1, 1)),
            "fixed castle setup exceeds the admitted piece bound")
    for right, king, rook in (("K", "e1", "h1"), ("Q", "e1", "a1"),
                              ("k", "e8", "h8"), ("q", "e8", "a8")):
        if right in board.castling:
            require(board.cells[oracle.square(king)] == ("K" if right.isupper() else "k")
                    and board.cells[oracle.square(rook)] == ("R" if right.isupper() else "r"),
                    "castling rights require their actual home king and rook")
    home = 4 if side > 0 else 60
    raw = []
    if board.cells[home] == ("K" if side > 0 else "k") and not board.in_check():
        for bit, direction, free in ((0, 1, (1, 2)), (1, -1, (-1, -2, -3))):
            if (letters[bit] in board.castling and all(board.cells[home + d] == "." for d in free)
                    and not board.attacked(home + direction, not board.turn)):
                raw.append(oracle.coord(home) + oracle.coord(home + direction * 2))
    legal = sorted(str(move) for move in board.legal_moves())
    return dict(label=("white-" if side > 0 else "black-") + tag, moves=[], legal=legal,
        board=board, fen=board.fen(), pieces=pieces, side=side,
        rights=sum(RIGHTS[right] for right in board.castling), own_rights=own_rights,
        expected_raw_castles=raw, tag=tag)


def fixture_cases(oracle, *, rules):
    """Retain standard-start paths, then append initialized fixed-FEN cases."""
    standard, standard_coverage = rules.fixture_cases(oracle)
    require(type(standard) is list and standard and all(type(row) is dict
            and type(row.get("moves")) is list and type(row.get("legal")) is list for row in standard),
            "actual standard rules cases with retained paths required")
    targeted = []
    for side in (1, -1):
        rank, enemy_rank = ("1", "7") if side > 0 else ("8", "2")
        enemy_rook, own_knight = ("r", "N") if side > 0 else ("R", "n")
        for mask in range(4):
            targeted.append(_target(oracle, side=side, tag="rights-" + str(mask), own_rights=mask))
        targeted.append(_target(oracle, side=side, tag="home-check",
                                changes=(("e" + enemy_rank, enemy_rook),)))
        for file, direction in (("f", "kingside"), ("d", "queenside")):
            targeted.append(_target(oracle, side=side, tag=direction + "-transit-attacked",
                                    changes=((file + enemy_rank, enemy_rook),)))
        for file, direction in (("g", "kingside"), ("c", "queenside")):
            targeted.append(_target(oracle, side=side, tag=direction + "-destination-attacked",
                                    changes=((file + enemy_rank, enemy_rook),)))
        for file in "fgbcd":
            targeted.append(_target(oracle, side=side, tag="path-block-" + file,
                                    changes=((file + rank, own_knight),)))
        targeted.append(_target(oracle, side=side, tag="off-home-no-rights", own_rights=0,
            changes=(("e" + rank, "."), ("d2" if side > 0 else "d7", "K" if side > 0 else "k"))))
    for case in targeted:
        rank = "1" if case["side"] > 0 else "8"
        king, queen = "e" + rank + "g" + rank, "e" + rank + "c" + rank
        tag, raw, legal = case["tag"], case["expected_raw_castles"], case["legal"]
        if tag == "rights-3":
            require(raw == [king, queen] and king in legal and queen in legal,
                    "open case must emit both castles in kingside-first order")
        if tag == "home-check" or tag == "off-home-no-rights":
            require(not raw, "outer guard negative case unexpectedly emits a castle")
        for name, move in (("kingside", king), ("queenside", queen)):
            if tag == name + "-transit-attacked":
                require(move not in raw and move not in legal, "transit attack must prevent raw castle emission")
            if tag == name + "-destination-attacked":
                require(move in raw and move not in legal,
                        "destination-only attack must reach emission then fail actual maker legality")
    labels = [row["label"] for row in (*standard, *targeted)]
    require(len(labels) == len(set(labels)), "combined castle case labels must be distinct")
    coverage = dict(standard=standard_coverage, standard_cases=len(standard), targeted_cases=len(targeted),
        own_rights_masks={colour: sorted({row["own_rights"] for row in targeted
            if row["side"] == side}) for colour, side in (("white", 1), ("black", -1))},
        targeted_labels=[row["label"] for row in targeted],
        raw_castle_order="kingside-before-queenside", destination_attack_separate_from_transit=True,
        actual_attack_call_trace=False)
    return [*standard, *targeted], coverage


def _original_generator(control, proof, *, family, castle):
    integer, returned = castle.CONTEXT[family]
    signature = ("static " + integer + " g(const E*p,Y*B," + integer + " f," + integer + " s){").encode("ascii")
    wrapper = (integer + " T(const E*p,Y*B){" + returned + " g(p,B,0,p->s);}").encode("ascii")
    suffix = ("}}}" + returned + " n;}").encode("ascii")
    require(type(proof.get("edits")) is list and len(proof["edits"]) == 1
            and control.count(signature) == control.count(wrapper) == 1,
            "actual unique full-generator signature and T call arguments required")
    row = proof["edits"][0]
    at, before = row["input_begin"], row["before"].encode("ascii")
    require(type(at) is int and before == castle.BEFORE and control[at:at + len(before)] == before
            and control[at + len(before):at + len(before) + len(suffix)] == suffix,
            "actual original castle arm/end slice differs")
    start = control.index(signature)
    require(start < at, "actual generator must enclose the castle edit")
    original = control[start:at + len(before) + len(suffix)]
    require(original.count(b"g(") == 1, "copied original generator cannot have a self-call")
    renamed = original.replace(signature, signature.replace(b" g(", b" rv_castle_original_g(", 1), 1)
    return original, renamed, wrapper


START = r'''
static const struct {int8_t pieces[64];int side,rights,raw;} rv_castle_cases[]={@CASES@};
static void rv_castle_fixture_start(E*p){
 static size_t row;
 if(row++<@STANDARD@){q(p);return;}
 size_t i=row-1-@STANDARD@;
 if(i>=sizeof(rv_castle_cases)/sizeof(*rv_castle_cases))abort();
 E before,left,right;memset(p,0,sizeof *p);p->s=rv_castle_cases[i].side;
 p->c=rv_castle_cases[i].rights;p->e=-1;
 for(int square=0;square<64;square++)if(rv_castle_cases[i].pieces[square])
  b(p,(square/8)*16+square%8,rv_castle_cases[i].pieces[square]);
 p->h^=l(p);p->r=p->h;
 memcpy(&before,p,sizeof before);memcpy(&left,p,sizeof left);memcpy(&right,p,sizeof right);
 Y old_moves[512],new_moves[512];
 int old_n=rv_castle_original_g(&left,old_moves,0,left.s);
 int new_n=g(&right,new_moves,0,right.s);
 if(old_n<0||old_n>512||new_n!=old_n||memcmp(old_moves,new_moves,(size_t)old_n*sizeof(*old_moves))
  ||memcmp(&left,&before,sizeof before)||memcmp(&right,&before,sizeof before))abort();
 int home=p->s>0?4:116,mask=0,king=-1,queen=-1;
 for(int n=0;n<old_n;n++){
  int from=FROM(old_moves[n]),to=TO(old_moves[n]);
  if(from==home&&abs(to-home)==2){
   int direction=to>home?1:2;
   if(mask&direction)abort();mask|=direction;
   if(direction==1)king=n;else queen=n;
  }
 }
 if(mask!=rv_castle_cases[i].raw||(mask==3&&king>=queen)||memcmp(p,&before,sizeof before))abort();
}
'''


def _start_declarations(cases, standard_count, renamed):
    targeted = cases[standard_count:]
    require(targeted and all(row["moves"] == [] for row in targeted), "fixed FEN cases cannot replay standard paths")
    rows = []
    for case in targeted:
        mask = sum(1 if move[2] == "g" else 2 for move in case["expected_raw_castles"])
        rows.append("{{" + ",".join(map(str, case["pieces"])) + "}," +
                    ",".join(map(str, (case["side"], case["rights"], mask))) + "}")
    setup = START.replace("@CASES@", ",\n".join(rows)).replace("@STANDARD@", str(standard_count))
    require("@" not in setup, "unreplaced castle fixture setup field")
    return b"\n" + renamed + b"\n" + setup.encode("ascii")


def render_fixture(control_source, *, family, profile_id, castle, projection, oracle, rules):
    """Use a genuine pinned parent, actual original g and the existing C main."""
    require(profile_id == PROFILE and family in ("A", "C", "E"), "finite A/C/E W256 castle fixture required")
    candidate, proof = castle.transform(control_source, family=family, profile_id=profile_id, projection=projection)
    require(castle.restore_source(candidate, proof, projection=projection) == control_source
            and b"rv_castle_" not in control_source, "actual castle source inverse or fresh fixture namespace differs")
    original, renamed, wrapper = _original_generator(control_source, proof, family=family, castle=castle)
    cases, coverage = fixture_cases(oracle, rules=rules)
    standard_count = coverage["standard_cases"]
    declarations = _start_declarations(cases, standard_count, renamed)
    binding = dict(rules.BINDINGS[family], start="rv_castle_fixture_start")
    require(binding["board"] == "E" and binding["generate"] == "T" and binding["make"] == "v"
            and binding["four_args"] is False, "actual admitted A/C/E rules binding required")
    fixture = rules.render_bound_fixture(candidate, binding, cases, extra_declarations=declarations)
    stored_cases = [{key:value for key, value in row.items() if key != "board"} for row in cases]
    metadata = dict(schema=SCHEMA, family=family, profile_id=profile_id,
        control=pin(control_source), candidate=pin(candidate), fixture=pin(fixture),
        original_generator=pin(original), renamed_original_generator=pin(renamed),
        actual_T_wrapper=pin(wrapper), source_proof=proof, cases=stored_cases, coverage=coverage,
        oracle_source_required=dict(ORACLE), source_only=True,
        original_entry_called=False, TT_allocated=False, search_called=False,
        actual_attack_call_trace=False, planned_raw_generator_pairs=len(cases)-standard_count,
        planned_full_raw_count_and_integer_order=True, planned_const_input_Board_comparison=True,
        shared_unchanged_attack_and_emitter_owners=True, actual_put_and_state_hash=True,
        standard_start_uses_actual_q=True, fixed_FEN_start_override=True,
        C_semantics_executed=False, runtime_qualified=False, native_identity_claimed=False)
    return fixture, metadata


def check_output(data, metadata, *, rules):
    """Check stdout only after the caller has admitted successful execution."""
    require(type(data) is bytes and type(metadata) is dict and metadata.get("schema") == SCHEMA
            and type(metadata.get("cases")) is list and metadata.get("source_only") is True
            and metadata.get("original_entry_called") is False and metadata.get("TT_allocated") is False
            and metadata.get("actual_attack_call_trace") is False,
            "bound castle fixture cases and explicit execution scope required")
    observed = rules._compare_output(data, metadata["cases"])
    return dict(observed, standard_cases=metadata["coverage"]["standard_cases"],
        targeted_cases=metadata["coverage"]["targeted_cases"],
        raw_count_order_and_const_input_checks_in_fixture=True,
        actual_attack_call_trace=False, runtime_qualified=False)
