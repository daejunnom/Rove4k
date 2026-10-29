"""Opt-in ordered castle-arm sharing on three exact full W256 sources.

The two emission arms become a +1 then -1 loop inside their unchanged king
home/check guard. Rights, empty-square tests, short-circuit attack calls and
emission order retain their values and sequence. Extra loop work may affect
timing. The caller owns module authentication, later C/rules validation and
complete submission cost; this source-only transform claims none of those.
"""
from hashlib import sha256
import json


SCHEMA = "rove4k.compact-castle-source.v1"
PROJECTION = dict(path="engines/experiments/tcec-next/spelling_compound.py", bytes=9472,
    sha256="4e2a1599ab5b6f294b1cb59a10a1ec6667b5a2e0c993c1ce48895cddb7e55fce")
INPUTS = {
    ("A", "tcec-provisional"): (7597, "f85fa3716aed39fe9b2ca973ac3d87650dbac95dfa9cedbaf800ada4f6375a23"),
    ("C", "tcec-provisional"): (8166, "c7b2ec5554f35af50f90b63f7c3c728c76d725d9de5a37aef96d95bbcb13b0f0"),
    ("E", "tcec-provisional"): (7780, "d9da4822b16da457786b6517675015c7a91c110a6685ffb9444eea945bbcff58"),
}
CONTEXT = {"A": ("L", "J"), "C": ("int", "return"), "E": ("L", "J")}
BEFORE = (b"if((p->c&(1<<w))&&!p->b[u+1]&&!p->b[u+2]&&!c(p,u+1,-s))k(B,&n,o,u+2,0);"
          b"if((p->c&(2<<w))&&!p->b[u-1]&&!p->b[u-2]&&!p->b[u-3]&&!c(p,u-1,-s))k(B,&n,o,u-2,0);")
DOMAIN = dict(board="initialized admitted standard-chess 0x88 Board", sides=[-1, 1],
    rights_range=[0, 15], king_homes=[4, 116], rights_shifts=[0, 2],
    loop_directions=[1, -1], loop_after_last=-3, actual_shift_range=[0, 3],
    white_access_range=[1, 7], black_access_range=[113, 119],
    enclosing_output_pointer_nonnull=True, outer_king_home_and_check_guard_unchanged=True,
    kingside_before_queenside=True, attack_side_effect_sequence_preserved=True,
    no_added_attack_or_emitter_calls=True, arbitrary_Board_equivalence_claimed=False)


def pin(data):
    return dict(bytes=len(data), sha256=sha256(data).hexdigest())


def require(value, message):
    if not value:
        raise ValueError(message)


def _proof_types(value):
    if type(value) is dict:
        require(all(type(key) is str for key in value), "exact JSON proof key types required")
        for item in value.values():
            _proof_types(item)
    elif type(value) is list:
        for item in value:
            _proof_types(item)
    else:
        require(value is None or type(value) in (str, int, bool), "exact JSON proof value types required")


def _admit(data, family, profile_id):
    require(type(family) is str and type(profile_id) is str and (family, profile_id) in INPUTS,
            "finite A/C/E W256 castle candidate required; P4/P28 are not admitted")
    require(type(data) is bytes and (len(data), sha256(data).hexdigest()) == INPUTS[family, profile_id],
            "exact selected full W256 source required; C/E must already include EP sharing")


def _region(data, family):
    """Literal/context checks only; synthetic callers here receive no admission."""
    integer, returned = CONTEXT[family]
    if integer == "L":
        require(data.count(b"#define L int\n") == data.count(b"#define J return\n") == 1,
                "exact family L/J macro aliases required")
    else:
        require(b"#define L " not in data and b"#define J " not in data,
                "C must retain its ordinary int/return context")
    guard = ("if(B&&a==6){" + integer + " u=s>0?4:116,w=s>0?0:2;"
             "if(o==u&&!c(p,u,-s)){").encode("ascii")
    walker = ("static " + integer + " g(const E*p,Y*B," + integer + " f," + integer + " s){").encode("ascii")
    suffix = ("}}}" + returned + " n;}").encode("ascii")
    require(data.count(BEFORE) == data.count(guard) == data.count(walker) == 1,
            "one exact castle arm pair, outer guard and walker required")
    at = data.index(BEFORE)
    require(data.index(walker) < data.index(guard) and
            data.index(guard) + len(guard) == at and data[at+len(BEFORE):].startswith(suffix),
            "castle arms must remain inside their exact final walker guard")
    after = ("for(" + integer + " d=1;d>=-1;d-=2)"
             "if((p->c&(1<<w+(d<0)))&&!p->b[u+d]&&!p->b[u+2*d]"
             "&&(d>0||!p->b[u-3])&&!c(p,u+d,-s))k(B,&n,o,u+2*d,0);").encode("ascii")
    require(len(BEFORE) == 154 and len(after) == (123 if family == "C" else 121),
            "fixed castle arm byte geometry differs")
    return at, after, guard


def transform(data, *, family, profile_id, projection):
    """Share exactly one arm pair; the production path remains unselected."""
    _admit(data, family, profile_id)
    require(projection.SCHEMA == "rove4k.selected-spelling-compound.v1",
            "authenticated existing compound projection owner required")
    at, after, guard = _region(data, family)
    row = dict(input_begin=at, before=BEFORE.decode("ascii"), after=after.decode("ascii"),
        role="ordered-kingside-queenside-sharing", component="castle-directions")
    candidate, edits, gaps = projection._splice(data, [row])
    require(len(edits) == 1 and len(gaps) == 2 and candidate.count(guard) == 1
            and projection._inverse_edits(candidate, edits) == data,
            "one castle region, protected guard or full inverse differs")
    proof = dict(schema=SCHEMA, family=family, profile_id=profile_id,
        input=pin(data), output=pin(candidate), projection=dict(PROJECTION),
        domain=json.loads(json.dumps(DOMAIN)),
        edits=edits, protected_gaps=gaps, protected_outer_guard=pin(guard), full_inverse=True,
        source_only=True, resources_changed=False, Board_layout_changed=False,
        maker_or_evaluation_changed=False, models_changed=False, features_removed=False,
        search_policy_changed=False, move_encoding_changed=False, ordering_or_ties_changed=False,
        TT_or_atomic_publication_changed=False, production_selected=False,
        extra_loop_work=True, timing_equivalence_claimed=False,
        C_semantics_executed=False, native_identity_claimed=False, runtime_qualified=False)
    return candidate, proof


def restore_source(candidate, proof, *, projection):
    """Restore and replay the full canonical typed proof, including all gaps."""
    require(type(candidate) is bytes and type(proof) is dict and proof.get("schema") == SCHEMA
            and type(proof.get("edits")) is list and pin(candidate) == proof.get("output"),
            "castle candidate and complete bound output proof required")
    require(projection.SCHEMA == "rove4k.selected-spelling-compound.v1",
            "authenticated existing compound projection owner required")
    _proof_types(proof)
    original = projection._inverse_edits(candidate, proof["edits"])
    _admit(original, proof.get("family"), proof.get("profile_id"))
    require(pin(original) == proof.get("input"), "castle inverse source differs")
    replay, expected = transform(original, family=proof["family"],
        profile_id=proof["profile_id"], projection=projection)
    require(replay == candidate and json.dumps(expected, sort_keys=True, allow_nan=False) ==
            json.dumps(proof, sort_keys=True, allow_nan=False),
            "castle metadata, typed domain, protected gaps or inverse differs")
    return original
