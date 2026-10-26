"""One source-only A/E terminal-owner and delayed-query hypothesis.

Inputs are the exact full P4 sources after the selected resource, phase,
E19/compound and A scan stages, before dependency cleanup. The caller supplies
the authenticated existing projection owner; this module performs no I/O,
dynamic imports, source generation, compilation, packaging or engine execution.

Terminal paths share the existing nullable legal-child resolver. A legal move
returns draw and sets cancellation only for t == 2, never t == 3. With no legal
move, checkmate/stalemate still takes priority over a draw claim. Other nodes
delay check, generation and evaluation until after the unchanged TT cutoff.
Claim/repetition, root TT, mate normalization, PVS, learners and E19 remain in
protected gaps. Pure-query counts and timing can change; no SMP trace, strength
or size improvement is claimed. Dependency cleanup must remain the last stage.
"""
from hashlib import sha256
import json


SCHEMA = "rove4k.terminal-queries-source.v1"
VARIANT = "terminal-owner-late-queries"
PROJECTION = {
    "path": "engines/experiments/tcec-next/spelling_compound.py",
    "bytes": 9472,
    "sha256": "4e2a1599ab5b6f294b1cb59a10a1ec6667b5a2e0c993c1ce48895cddb7e55fce",
}
# The projection identity is its canonical LF source. The reviewed Windows
# file already has only LF endings; candidate payloads are never normalized.
INPUTS = {
    ("A", "test-p4"): (7595, "02faeb563c435c02321fc6d497f54a31de01d9093be33bff5e44206a93dfbdc6"),
    ("E", "test-p4"): (7815, "198bccf29d1441f63e3fd07b5da9ab4164fe3c31393af7ad35ab72d4d3fe08ff"),
}
STAGES = {
    "A": ("resource", "phase-init", "compound", "square-successor", VARIANT, "dependency-cleanup"),
    "E": ("resource", "phase-init", "E19", "compound", VARIANT, "dependency-cleanup"),
}


def pin(data):
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


def require(value, message):
    if not value:
        raise ValueError(message)


def _admit(source, family, profile_id):
    require(type(family) is str and type(profile_id) is str
            and (family, profile_id) in INPUTS, "finite A/E P4 binding required")
    require(type(source) is bytes
            and (len(source), sha256(source).hexdigest()) == INPUTS[family, profile_id],
            "exact selected pre-dependency payload required")


def _edits(source, family):
    worker, moves, mate, cap, cancel, evaluation = (
        ("M", "MOVES", "MATE", "PLY", "X", "p->s*p->v") if family == "A" else
        ("ai", "512", "30000", "128", "qp", "p->s*S(p)"))
    start = "static L h(" + worker + "*w,"
    marker = "t|=(d==" + cap + "-1)*2;"
    declarations = ("Y B[" + moves + "],N=0;L y[" + moves
                    + "],z=T(p,B),A=0,D=G,H=-" + mate + ",F=" + evaluation + ";")
    terminal = ("if(t){E q;if(i(p,0,&q)){if(t==2)" + cancel
                + "=1;J 0;}J c(p,p->k[p->s<0],-p->s)?-" + mate + "+d:0;}")
    delayed_declarations = ("Y B[" + moves + "],N=0;L y[" + moves
                            + "],z,A=0,D=G,H=-" + mate + ",F;")
    cutoff = "if(d&&K&&k>=(C>0?C:0)&&(K==1||(K==2&&l>=a)||(K==3&&l<=G)))J l;"
    accepted = "E q;if(!v(p,m,&q))continue;"
    rows = (
        ("static-resolver-prototype", start, "static Y i(const E*,const char*,E*);" + start),
        ("defer-check", "L n=c(p,p->k[p->s<0],-p->s),t=p->aI>=100,u=0,x=qh+d-1-p->aI;",
         "L n,t=p->aI>=100,u=0,x=qh+d-1-p->aI;"),
        ("terminal-legality-owner", marker + declarations, marker + terminal + delayed_declarations),
        ("nonterminal-TT-query", "U=t?0:V(I,0);", "U=V(I,0);"),
        ("queries-after-unchanged-cutoff", cutoff,
         cutoff + "n=c(p,p->k[p->s<0],-p->s);z=T(p,B);F=" + evaluation + ";"),
        ("remove-ordered-terminal-consumer", accepted + "if(t){if(t==2)" + cancel + "=1;J 0;}++A;",
         accepted + "++A;"),
    )
    edits = []
    for role, before, after in rows:
        literal = before.encode("ascii")
        require(source.count(literal) == 1, "unique terminal-query span required: " + role)
        edits.append(dict(input_begin=source.index(literal), before=before, after=after,
                          role=role, component=VARIANT))
    return edits


def transform_source(source, *, family, profile_id, projection):
    """Project only a finite selected source with an authenticated caller owner."""
    _admit(source, family, profile_id)
    require(projection.SCHEMA == "rove4k.selected-spelling-compound.v1",
            "existing compound projection owner required")
    candidate, edits, gaps = projection._splice(source, _edits(source, family))
    require(len(edits) == 6 and len(gaps) == 7
            and projection._inverse_edits(candidate, edits) == source,
            "six edits, seven protected gaps and complete inverse required")
    proof = dict(schema=SCHEMA, variant=VARIANT, family=family, profile_id=profile_id,
                 input=pin(source), output=pin(candidate), projection=dict(PROJECTION),
                 stage_order=list(STAGES[family]), edits=edits, protected_gaps=gaps,
                 full_inverse=True, source_only=True)
    return candidate, proof


def restore_source(candidate, proof, *, projection):
    """Restore and replay the complete finite proof, including typed metadata."""
    require(type(candidate) is bytes and type(proof) is dict
            and proof.get("schema") == SCHEMA and proof.get("variant") == VARIANT
            and pin(candidate) == proof.get("output")
            and type(proof.get("edits")) is list and len(proof["edits"]) == 6,
            "terminal-query candidate and proof required")
    require(projection.SCHEMA == "rove4k.selected-spelling-compound.v1",
            "existing compound projection owner required")
    source = projection._inverse_edits(candidate, proof["edits"])
    _admit(source, proof.get("family"), proof.get("profile_id"))
    require(pin(source) == proof.get("input"), "terminal-query inverse input differs")
    replay, expected = transform_source(source, family=proof["family"],
                                       profile_id=proof["profile_id"], projection=projection)
    require(replay == candidate and
            json.dumps(expected, sort_keys=True, allow_nan=False) ==
            json.dumps(proof, sort_keys=True, allow_nan=False),
            "terminal-query full inverse, edits, protected gaps or proof differ")
    return source
