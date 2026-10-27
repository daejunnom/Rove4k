"""Opt-in C/E EP trial sharing on six exact full source-profile payloads.

The private normalizer only needs a nonzero legality result. Its caller supplies
an initialized admitted Board and either a legal double-push EP target or the
validated FEN target. The existing maker applies that EP capture to a discarded
child; it clears EP before its nested normalizer, so nesting is bounded. Extra
private hash/model work and timing differ. Full functional/runtime qualification
and complete-file size remain the caller's separate responsibilities.

No files, environments, project modules, compilers or codecs are read/executed.
A/B/F already share their maker in current source and are not new candidates.
D compression is paused and outside this module's finite input domain.
"""
from hashlib import sha256
import json


SCHEMA = "rove4k.compact-ep-source.v1"
PROJECTION = {
    "path": "engines/experiments/tcec-next/spelling_compound.py",
    "bytes": 9472,
    "sha256": "4e2a1599ab5b6f294b1cb59a10a1ec6667b5a2e0c993c1ce48895cddb7e55fce",
}
INPUTS = {
    ("C", "test-p4"): (8199, "86b7dd0e5f206d10086d098ce82083d4d12910df91a7f1215915727327f1d42a"),
    ("C", "test-p28"): (8232, "b3a968d2287a8418ce32b7b2f9f019c4695b55a32fd4f332eab89e16d012d2d0"),
    ("C", "tcec-provisional"): (8201, "ae131e49609b34eefaa54499f79f2aa738d103cbc800c1d7a70cde359106b807"),
    ("E", "test-p4"): (7815, "198bccf29d1441f63e3fd07b5da9ab4164fe3c31393af7ad35ab72d4d3fe08ff"),
    ("E", "test-p28"): (7848, "de83f406f1c7916277f71e75c4b6ac2a5aa77663ab9f7e3ec2af11e8480668b8"),
    ("E", "tcec-provisional"): (7817, "d3069c36dec5becdca14b69e49016b9a3a6b4c762da91471e7ba8c73debad4f3"),
}
CONTEXT = {"C": dict(integer="int", returned="return"),
           "E": dict(integer="L", returned="J")}
DOMAIN = dict(board="initialized admitted 0x88 Board", sides=[-1, 1],
    pieces_per_side_max=16, EP_target="valid double push or validated FEN",
    white_EP_rank=5, black_EP_rank=2, EP_step_magnitudes=[15, 17], double_push_magnitude=32,
    FEN_halfmove_max=1000000, TCEC_history_max=4096,
    inner_EP_cleared_before_recursion=True, extra_maker_calls_per_EP_trial=1,
    max_live_maker_frames_from_outer_make=2,
    private_trial_child_discarded=True, provisional_unsigned_hash_context_discarded=True,
    maker_trial_input_Board_unmodified=True, normalizer_may_clear_EP=True,
    only_EP_boolean_consumed=True,
    arbitrary_uninitialized_Board_equivalence_claimed=False)


def pin(data):
    return dict(bytes=len(data), sha256=sha256(data).hexdigest())


def require(value, message):
    if not value:
        raise ValueError(message)


def _admit(source, family, profile_id):
    require(type(family) is str and type(profile_id) is str
            and (family, profile_id) in INPUTS, "finite C/E P4/P28/provisional EP candidate required")
    require(type(source) is bytes and (len(source), sha256(source).hexdigest()) == INPUTS[family, profile_id],
            "exact selected full profile EP source required")


def _regions(source, family):
    context = CONTEXT[family]
    integer, returned = context["integer"], context["returned"]
    trial = ("E t=*p;t.b[q]=t.b[p->e-p->s*16]=0;t.b[p->e]=(int8_t)p->s;"
             "if(!c(&t,p->k[p->s<0],-p->s))" + returned + ";")
    body = ("static void D(E*p){if(p->e<0)" + returned + ";for(" + integer +
            " d=-1;d<=1;d+=2){" + integer + " q=p->e-p->s*16+d;"
            "if(!(q&0x88)&&p->b[q]==p->s){" + trial + "}}p->e=-1;}")
    declaration = integer + " v(const E*,Y,E*);"
    delegated = "E t;if(v(p,MOVE(q,p->e,0),&t))" + returned + ";"
    before = body.encode("ascii")
    require(source.count(before) == 1 and body.count(trial) == 1
            and declaration.encode("ascii") not in source,
            "one exact private EP region and absent maker declaration required")
    maker_start = (integer + " v(const E*p,Y m,E*w){").encode("ascii")
    require(source.count(maker_start) == 1 and source.count(b"static void k(") == 1,
            "exact protected maker and following declaration required")
    begin = source.index(maker_start)
    end = source.index(b"static void k(", begin)
    maker = source[begin:end]
    required = (b"*w=*p;", b"w->e=-1;", b"if(abs(a-o)==32)w->e=o+s*16;",
                ("if(c(w,w->k[s<0],-s))" + returned + " 0;D(w);").encode("ascii"),
                b"w->r=w->aI?((p->r<<1)|(p->r>>63))^w->h:w->h;")
    require(all(maker.count(part) == 1 for part in required),
            "protected maker EP-clear, legality, nesting or private state roles differ")
    after = (declaration + body.replace(trial, delegated)).encode("ascii")
    return before, after, maker


def transform_source(source, *, family, profile_id, projection):
    """Replace the private normalizer region; its producer remains unselected."""
    _admit(source, family, profile_id)
    require(projection.SCHEMA == "rove4k.selected-spelling-compound.v1",
            "authenticated existing compound projection owner required")
    before, after, maker = _regions(source, family)
    row = dict(input_begin=source.index(before), before=before.decode("ascii"),
        after=after.decode("ascii"), role="private-EP-trial-to-maker", component="ep-maker-shared")
    candidate, edits, gaps = projection._splice(source, [row])
    require(len(edits) == 1 and len(gaps) == 2
            and projection._inverse_edits(candidate, edits) == source and candidate.count(maker) == 1,
            "one EP region, protected maker or full inverse differs")
    proof = dict(schema=SCHEMA, family=family, profile_id=profile_id,
        input=pin(source), output=pin(candidate), projection=dict(PROJECTION), domain=dict(DOMAIN),
        edits=edits, protected_gaps=gaps, protected_maker=pin(maker), full_inverse=True,
        source_only=True, resources_changed=False, models_changed=False, features_removed=False,
        move_encoding_changed=False, ordering_or_ties_changed=False,
        TT_or_atomic_publication_changed=False, production_selected=False,
        extra_private_state_work=True, timing_equivalence_claimed=False,
        native_identity_claimed=False, runtime_qualified=False)
    return candidate, proof


def restore_source(candidate, proof, *, projection):
    """Restore actual source and replay its complete domain/splice/gap metadata."""
    require(type(candidate) is bytes and type(proof) is dict and proof.get("schema") == SCHEMA
            and type(proof.get("edits")) is list and pin(candidate) == proof.get("output"),
            "EP candidate and complete output proof required")
    require(projection.SCHEMA == "rove4k.selected-spelling-compound.v1",
            "authenticated existing compound projection owner required")
    source = projection._inverse_edits(candidate, proof["edits"])
    _admit(source, proof.get("family"), proof.get("profile_id"))
    require(pin(source) == proof.get("input"), "EP inverse source differs")
    replay, expected = transform_source(source, family=proof["family"],
        profile_id=proof["profile_id"], projection=projection)
    require(replay == candidate and json.dumps(expected, sort_keys=True, allow_nan=False) ==
            json.dumps(proof, sort_keys=True, allow_nan=False),
            "EP metadata, protected gaps or inverse differs")
    return source
