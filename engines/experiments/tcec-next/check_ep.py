"""Render a small actual-function EP diagnostic, without I/O or C execution.

The caller authenticates the supplied module closure and later owns compilation,
resource bounds and execution. This is a targeted Board/legality diagnostic, not
an engine, TT, strength, timing, submission-size or runtime qualification.
"""
from hashlib import sha256
import json


SCHEMA = "rove4k.actual-function-ep-fixture.v1"
ORACLE = dict(path="engines/tests/chess_oracle.py", bytes=10730,
    sha256="aea285b5b5f07602c829595840d5270fa8dc25683ccd26c63607435679024db8")
HALFMOVES = (0, 99, 100, 1000000)
HASH_MODES = ("piece-only", "state-bound", "zero", "unsigned-max")
# These are fixed valid standard-chess placements. Keep the raw FEN EP field:
# normalizing it during setup would remove precisely the pinned trial at issue.
CASES = (
    ("white-legal", "7k/8/8/3pP3/8/8/8/K7 w - d6 0 1", ("e5d6",)),
    ("black-legal", "k7/8/8/8/3Pp3/8/8/7K b - d3 0 1", ("e4d3",)),
    ("white-horizontal-discovery", "k7/8/8/r4pPK/8/8/8/8 w - f6 0 1", ()),
    ("black-horizontal-discovery", "8/8/8/8/R4Ppk/8/8/K7 b - f3 0 1", ()),
    ("white-file-pin", "k3r3/8/8/3pP3/8/8/8/4K3 w - d6 0 1", ()),
    ("black-file-pin", "4k3/8/8/8/3Pp3/8/8/K3R3 b - d3 0 1", ()),
    ("white-no-capturer", "7k/8/8/3p4/8/8/P7/K7 w - d6 0 1", ()),
    ("black-no-capturer", "k7/7p/8/8/3P4/8/8/7K b - d3 0 1", ()),
    ("white-first-pinned-second-legal", "k1r5/8/8/2PpP3/8/8/8/2K5 w - d6 0 1", ("e5d6",)),
    ("black-first-pinned-second-legal", "2k5/8/8/8/2pPp3/8/8/K1R5 b - d3 0 1", ("e4d3",)),
    ("white-no-EP", "7k/8/8/8/8/8/P7/K7 w - - 0 1", ()),
    ("black-no-EP", "k7/7p/8/8/8/8/8/7K b - - 0 1", ()),
)


def pin(data):
    return dict(bytes=len(data), sha256=sha256(data).hexdigest())


def require(value, message):
    if not value:
        raise ValueError(message)


def fixture_cases(oracle):
    """Derive EP expectations from the independent oracle, retaining raw EP."""
    result = []
    for label, fen, expected in CASES:
        board = oracle.Board.from_fen(fen)
        fields = fen.split()
        raw = -1 if fields[3] == "-" else oracle.square(fields[3])
        require(board.ep == raw and not board.castling and board.halfmove == 0,
                "oracle setup must retain this fixed raw EP and no castling rights")
        side = 1 if fields[1] == "w" else -1
        require(board.turn == (side == 1), "fixed FEN side differs")
        pieces = [0 if char == "." else " pnbrqk".index(char.lower()) *
                  (1 if char.isupper() else -1) for char in board.cells]
        require(all(sum(value * colour > 0 for value in pieces) <= 16
                    for colour in (-1, 1)), "fixed placement exceeds admitted piece bound")
        legal = sorted(str(move) for move in board.legal_moves()
            if raw >= 0 and move.dst == raw and pieces[move.src] == side
            and pieces[raw] == 0 and move.src % 8 != raw % 8)
        require(legal == list(expected), "independent EP expectation differs: " + label)
        trials = []
        if raw >= 0:
            require(raw // 8 == (5 if side > 0 else 2) and pieces[raw] == 0
                    and pieces[raw - side * 8] == -side,
                    "fixed FEN EP geometry differs: " + label)
            pseudo = {str(move) for move in board.pseudo_moves()}
            target = (raw // 8) * 16 + raw % 8
            for offset in (-1, 1):
                source = target - side * 16 + offset
                if not source & 0x88 and pieces[(source >> 4) * 8 + (source & 7)] == side:
                    text = oracle.coord((source >> 4) * 8 + (source & 7)) + fields[3]
                    require(text in pseudo, "direct maker input is not an EP pawn pseudomove")
                    trials.append(dict(source=source, legal=int(text in legal), move=text))
        else:
            target = -1
        result.append(dict(label=label, fen=fen, pieces=pieces, side=side,
            raw_ep=target, expected_ep=target if legal else -1,
            legal_EP=legal, trials=trials))
    return result


DRIVER = r'''
static const struct {
 const char *label; int8_t pieces[64]; int side,ep,keep,from[2],legal[2];
} rv_ep_cases[]={@CASES@};
int main(void){
 static const int rv_ep_half[]={@HALF@};
 unsigned rv_ep_pairs=0,rv_ep_trials=0;
 for(size_t i=0;i<sizeof(rv_ep_cases)/sizeof(*rv_ep_cases);i++){
  E base;memset(&base,0,sizeof base);
  base.s=rv_ep_cases[i].side;base.c=0;base.e=rv_ep_cases[i].ep;
  for(int square=0;square<64;square++)if(rv_ep_cases[i].pieces[square])
   b(&base,(square/8)*16+square%8,rv_ep_cases[i].pieces[square]);
  if(base.e!=rv_ep_cases[i].ep)return 10;
  for(size_t half=0;half<sizeof(rv_ep_half)/sizeof(*rv_ep_half);half++){
   for(int mode=0;mode<4;mode++){
    E p,old,now,want,snapshot;memcpy(&p,&base,sizeof p);p.aI=rv_ep_half[half];
    if(mode==0){p.h=base.h;p.r=0;}
    if(mode==1){p.h=base.h^l(&p);p.r=p.h;}
    if(mode==2){p.h=0;p.r=0;}
    if(mode==3){p.h=(W)~(W)0;p.r=(W)~(W)0;}
    if(p.e!=rv_ep_cases[i].ep)return 11;
    memcpy(&old,&p,sizeof p);memcpy(&now,&p,sizeof p);memcpy(&want,&p,sizeof p);
    want.e=rv_ep_cases[i].keep?rv_ep_cases[i].ep:-1;
    rv_ep_original(&old);D(&now);
    if(memcmp(&old,&want,sizeof p)||memcmp(&now,&want,sizeof p)){
     fprintf(stderr,"EP Board differs: %s half=%d mode=%d old=%d new=%d expected=%d\n",
      rv_ep_cases[i].label,p.aI,mode,old.e,now.e,want.e);return 20;
    }
    rv_ep_pairs++;
    for(int trial=0;trial<2;trial++)if(rv_ep_cases[i].from[trial]>=0){
     int from=rv_ep_cases[i].from[trial];E child;
     if(p.e<0||(from&0x88)||p.b[from]!=p.s||p.b[p.e]
       ||abs(p.e-from-p.s*16)!=1||p.b[p.e-p.s*16]!=-p.s)return 30;
     memcpy(&snapshot,&p,sizeof p);
     int legal=!!v(&p,MOVE(from,p.e,0),&child);
     if(legal!=rv_ep_cases[i].legal[trial]||memcmp(&p,&snapshot,sizeof p)){
      fprintf(stderr,"EP maker differs: %s half=%d mode=%d from=%d\n",
       rv_ep_cases[i].label,p.aI,mode,from);return 31;
     }
     rv_ep_trials++;
    }
   }
  }
 }
 printf("{\"cases\":%zu,\"normalizer_pairs\":%u,\"direct_trials\":%u,"
  "\"full_board_equal\":true,\"trial_const_input\":true}\n",
  sizeof(rv_ep_cases)/sizeof(*rv_ep_cases),rv_ep_pairs,rv_ep_trials);
 return 0;
}
'''


def _driver(cases):
    rows = []
    for case in cases:
        trials = case["trials"] + [dict(source=-1, legal=0)] * (2-len(case["trials"]))
        rows.append("{" + json.dumps(case["label"]) + ",{" +
            ",".join(map(str, case["pieces"])) + "}," +
            ",".join(map(str, (case["side"], case["raw_ep"], int(bool(case["legal_EP"]))))) +
            ",{" + ",".join(str(trial["source"]) for trial in trials) + "},{" +
            ",".join(str(trial["legal"]) for trial in trials) + "}}")
    result = DRIVER.replace("@CASES@", ",\n".join(rows)).replace("@HALF@", ",".join(map(str, HALFMOVES)))
    require("@" not in result, "unreplaced EP fixture field")
    return result.encode("ascii")


def render_fixture(control_source, *, family, profile_id, ep, projection, oracle):
    """Render the admitted candidate plus actual original D; never run either."""
    candidate, proof = ep.transform_source(control_source, family=family,
        profile_id=profile_id, projection=projection)
    require(ep.restore_source(candidate, proof, projection=projection) == control_source,
            "actual EP control/candidate inverse differs")
    require(b"rv_ep_" not in control_source and len(proof["edits"]) == 1,
            "fresh fixture identifiers and one actual EP region required")
    row = proof["edits"][0]
    original = row["before"].encode("ascii")
    require(control_source[row["input_begin"]:row["input_begin"]+len(original)] == original
            and original.count(b"static void D(") == 1,
            "actual original normalizer slice differs")
    renamed = original.replace(b"static void D(", b"static void rv_ep_original(", 1)
    cases = fixture_cases(oracle)
    driver = _driver(cases)
    fixture = (b"#define main rv_ep_engine_main\n" + candidate + b"\n#undef main\n" +
               renamed + b"\n" + driver)
    multiplicity = len(HALFMOVES) * len(HASH_MODES)
    metadata = dict(schema=SCHEMA, family=family, profile_id=profile_id,
        control=pin(control_source), candidate=pin(candidate), fixture=pin(fixture),
        original_function=pin(original), candidate_region=pin(row["after"].encode("ascii")),
        oracle_source_required=dict(ORACLE), cases=cases, halfmoves=list(HALFMOVES),
        hash_modes=list(HASH_MODES), expected_normalizer_pairs=len(cases)*multiplicity,
        expected_direct_trials=sum(len(case["trials"]) for case in cases)*multiplicity,
        source_only=True, raw_FEN_EP_retained=True, actual_put_and_state_hash=True,
        planned_full_Board_comparison=True, planned_maker_const_input_comparison=True,
        input_domain="initialized valid fixed FEN Board; bounded half; explicit unsigned h/r",
        original_entry_called_by_driver=False, TT_or_search_called_by_driver=False,
        arbitrary_Board_equivalence_claimed=False, C_semantics_executed=False,
        runtime_qualified=False, native_identity_claimed=False)
    return fixture, metadata
