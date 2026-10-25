"""Defer scalar D's completed-iteration fields until think() returns.

The search still receives its own previous completed root witness. A cancelled
attempt cannot replace it. This is an event-boundary claim for the pinned
pending/output runtime, not native identity, timing or a search-policy change.
"""
from hashlib import sha256


KIND = "D-scalar-return-publication-v1"
_COMMON = {
    "image.ld": "38756c865914b52432572864446fcc58b791dfb508af8a33156d5c190c01044b",
    "start.S": "4a6021518cfe67bee9e42806b596f4f0837e3e93487b1acfa115158ea019ba5b",
}
_BASE = {
    "resource": {
        "board.c": "0290b1baf87b6bf46d600eb623568971a23116d36de445fbc95a605116188e38",
        "runtime.c": "35ef9f06d29e81375cc359f943d5a014b7767bd51413c1dda0e0d0ca5426c28a",
    },
    "equivalent": {
        "board.c": "ecd9d567a1f6c5ee185012a70915ab63c741bbf68b7a294d1604334c59db4e62",
        "runtime.c": "a0230b6a155b54366bc36eff65d3d850d8f6ab3bae9ef83fd64097f9b6ac4955",
    },
}
# Each tuple is the complete search/header pair for one admitted source cohort.
_SHAPES = {
    "resource-none": ("4be4e4752b7f5bc44edc50c5f365246bf5695dae88cf775a7cb8e8b22f57381c", "7cf685ab2e30e190765429f6f139085c6704c95fd331ba333cba8764e2bbe9ee"),
    "resource-prefix": ("c53aa4f416d56e2314fc313591ca9d92432e3848cd1100f5c598c3e389c60a46", "8038108f052e32d70f13c410040be61afe77a37cbea5240ae3f4b35076d3df84"),
    "resource-dense": ("7b5a2b3089fd57f78697ee5fa9febd8e59fef7a06c86fd991dcc5b852b0989c1", "92ca8ae06c27471f3831488b07c0c51fbf90fad16ea0729670ae5bb3009fcf0c"),
    "resource-prefix-dense": ("3617707a63d835d7396376421153ce9c3d02dfbe3c76cda39be87fbe5643dd3c", "a77cdb8fac5f7ed50c2b59ea6d2f86c80f6992e309e496449921123a1cb509e8"),
    "equivalent-none": ("86e03ee45229b04b869ec2a810ddeec0cfc102a7d5179fc9d7cb2cf8b024868a", "959ede51dd300d3093e27bc28f664dc55449a5d9e72762a36fb097d8cdb2284c"),
    "equivalent-prefix": ("2cb4632e29635d114680f8b21c21137545143f3c033546d3f8ac7c4307163194", "f918331fbc2bc140362ebe883fca7d897c97b3226bb10e8ce9918bc1eb233ce9"),
    "equivalent-dense": ("354b8e197a8216f830980af25467993e197dc585d47f44804ebe149adf513ac6", "1b154c9f6aea45fccc7dc6a31c393eb694afd901be41085555e11b10d38fd59d"),
    "equivalent-prefix-dense": ("035a02a87916a04d6686f2fe0555ee3063fe005dbb9385adba1a97756c5cb842", "bb0c832546d73da18d9099e2284b767991d3b99d6f710f33321073cd9f48af8f"),
}
INPUTS = {
    cohort: {**_COMMON, **_BASE[cohort.split("-", 1)[0]], "search.c": pair[0], "tiny.h": pair[1]}
    for cohort, pair in _SHAPES.items()
}
RUNTIME_ROLES = {
    "fresh-job-seed": b"seen=current;w->best=0;think(w,&position);",
    "worker-release-and-last-acquire": b"if(atomic_fetch_sub_explicit(&pending,1,memory_order_acq_rel)==2){",
    "output-before-reuse": b"result();atomic_store_explicit(&pending,0,memory_order_release);wake(&pending);",
    "main-acquire-fence": b"while((count=atomic_load_explicit(&pending,memory_order_acquire)))",
    "position-fence": b'if(word(command,"position")){wait();set_position((char *)cursor);}',
}


def pin(data):
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


def _pins(files):
    return {name: pin(data) for name, data in sorted(files.items())}


def _project(source, edits):
    rows = []
    for role, before, after in edits:
        if not before or source.count(before) != 1:
            raise ValueError("unique publication role required: " + role)
        rows.append((source.index(before), role, before, after))
    parts, proof, gaps, cursor, target = [], [], [], 0, 0
    for begin, role, before, after in sorted(rows):
        if begin < cursor:
            raise ValueError("overlapping publication roles")
        gap = source[cursor:begin]
        parts.extend((gap, after)); gaps.append(pin(gap)); target += len(gap)
        proof.append(dict(role=role, source=begin, target=target,
                          before=before.decode(), after=after.decode()))
        cursor = begin + len(before); target += len(after)
    parts.append(source[cursor:]); gaps.append(pin(source[cursor:]))
    output = b"".join(parts)
    record = dict(input=pin(source), output=pin(output), edits=proof, protected_gaps=gaps)
    if _restore(output, record) != source:
        raise ValueError("publication whole-source inverse differs")
    return output, record


def _restore(output, record):
    if pin(output) != record["output"]:
        raise ValueError("publication output differs")
    parts, gaps, cursor = [], [], 0
    for row in record["edits"]:
        begin, after = row["target"], row["after"].encode()
        if begin < cursor or output[begin:begin + len(after)] != after:
            raise ValueError("publication inverse role differs")
        gap = output[cursor:begin]
        parts.extend((gap, row["before"].encode())); gaps.append(pin(gap))
        cursor = begin + len(after)
    parts.append(output[cursor:]); gaps.append(pin(output[cursor:]))
    restored = b"".join(parts)
    if pin(restored) != record["input"] or gaps != record["protected_gaps"]:
        raise ValueError("publication inverse/complement differs")
    return restored


def _roles(score):
    reset = b"    w->nodes=0;w->depth=0;" + (b"w->score=0;" if score else b"") + b"\n"
    initialize = b"    w->nodes=0;Move completed=w->best;int depth" + (b",completed_score=0" if score else b"") + b";\n"
    publish = b"        w->best=best;" + (b"w->score=score;" if score else b"") + b"w->depth=depth;\n    }\n}\n"
    finish = (b"        completed=best;" + (b"completed_score=score;" if score else b"") +
              b"\n    }\n    w->best=completed;" + (b"w->score=completed_score;" if score else b"") +
              b"w->depth=depth-1;\n}\n")
    return [
        ("local-completed-state", reset, initialize),
        ("iteration-counter-survives-exit", b"    for(int depth=1;depth<=\n", b"    for(depth=1;depth<=\n"),
        ("previous-completed-root-seed", b"        Move best=w->best;\n", b"        Move best=completed;\n"),
        ("publish-only-after-iteration-loop", publish, finish),
    ]


def transform(files):
    if (not isinstance(files, dict) or not files or
            any(not isinstance(name, str) or not isinstance(data, bytes) or b"\r" in data
                for name, data in files.items())):
        raise ValueError("normalized D source mapping required")
    actual = {name: sha256(data).hexdigest() for name, data in files.items()}
    cohort = next((name for name, expected in INPUTS.items() if actual == expected), None)
    if cohort is None:
        raise ValueError("exact complete D publication cohort required")
    for role, body in RUNTIME_ROLES.items():
        if files["runtime.c"].count(body) != 1:
            raise ValueError("publication runtime reader closure differs: " + role)
    score = cohort.startswith("resource-")
    result = dict(files)
    result["search.c"], edit = _project(files["search.c"], _roles(score))
    proof = dict(kind=KIND, cohort=cohort, score_present=score,
                 scope="scalar D_HQ=0 DEV=0 PLY128; worker result observed after pending/output fence",
                 input=_pins(files), output=_pins(result), source_edits={"search.c": edit},
                 runtime_reader_closure=dict(source=pin(files["runtime.c"]),
                                            roles={role: pin(body) for role, body in RUNTIME_ROLES.items()}),
                 contracts=dict(seed="incoming w->best; runtime initializes each new job to zero",
                                iteration="only a root call followed by stopped==0 updates completed state",
                                cancellation="partial root mutation never replaces the last completed witness",
                                publication="think return writes fields before existing pending acq_rel",
                                reuse="main acquires zero only after result output",
                                nodes="unchanged claim/deadline counter and reset",
                                score="last completed score, or zero" if score else "absent"),
                 search_policy_changed=False, native_identity_claimed=False,
                 size_measured=False, runtime_qualified=False)
    if restore(result, proof) != files:
        raise ValueError("complete publication inverse differs")
    return result, proof


def restore(files, proof):
    if proof.get("kind") != KIND or proof.get("cohort") not in INPUTS:
        raise ValueError("unknown publication proof")
    if _pins(files) != proof["output"] or set(proof["source_edits"]) != {"search.c"}:
        raise ValueError("complete publication output cohort differs")
    result = dict(files)
    result["search.c"] = _restore(files["search.c"], proof["source_edits"]["search.c"])
    if (_pins(result) != proof["input"] or
            {name: sha256(data).hexdigest() for name, data in result.items()} != INPUTS[proof["cohort"]]):
        raise ValueError("complete publication input cohort differs")
    expected, record = _project(result["search.c"], _roles(proof["cohort"].startswith("resource-")))
    if (expected != files["search.c"] or record != proof["source_edits"]["search.c"] or
            proof["score_present"] != proof["cohort"].startswith("resource-") or
            proof["runtime_reader_closure"] != dict(source=pin(result["runtime.c"]),
                roles={role: pin(body) for role, body in RUNTIME_ROLES.items()})):
        raise ValueError("publication roles or reader proof differs")
    return result
