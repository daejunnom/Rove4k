"""Exact scalar-D prefix/history projections; no compiler or engine execution.

The admitted inputs are the two source.prepare() cohorts, before identifier
renaming or preprocessing. Runtime bytes bind the existing pending/output fence:
main cannot replace game_keys/game_length while a search owns their prefix.

Prefix storage changes no repetition window, path digest, move order or learner
update. Dense history is a bijection on gen()-proved valid 0x88 squares. These
source/domain claims are not native-cost, runtime, NUMA or strength evidence.
"""
from __future__ import annotations

from hashlib import sha256


INPUTS = {
    "resource-base": {
        "tiny.h": "7cf685ab2e30e190765429f6f139085c6704c95fd331ba333cba8764e2bbe9ee",
        "board.c": "0290b1baf87b6bf46d600eb623568971a23116d36de445fbc95a605116188e38",
        "search.c": "4be4e4752b7f5bc44edc50c5f365246bf5695dae88cf775a7cb8e8b22f57381c",
        "runtime.c": "35ef9f06d29e81375cc359f943d5a014b7767bd51413c1dda0e0d0ca5426c28a",
        "start.S": "4a6021518cfe67bee9e42806b596f4f0837e3e93487b1acfa115158ea019ba5b",
        "image.ld": "38756c865914b52432572864446fcc58b791dfb508af8a33156d5c190c01044b",
    },
    "equivalent-base": {
        "tiny.h": "959ede51dd300d3093e27bc28f664dc55449a5d9e72762a36fb097d8cdb2284c",
        "board.c": "ecd9d567a1f6c5ee185012a70915ab63c741bbf68b7a294d1604334c59db4e62",
        "search.c": "86e03ee45229b04b869ec2a810ddeec0cfc102a7d5179fc9d7cb2cf8b024868a",
        "runtime.c": "a0230b6a155b54366bc36eff65d3d850d8f6ab3bae9ef83fd64097f9b6ac4955",
        "start.S": "4a6021518cfe67bee9e42806b596f4f0837e3e93487b1acfa115158ea019ba5b",
        "image.ld": "38756c865914b52432572864446fcc58b791dfb508af8a33156d5c190c01044b",
    },
}

PREFIX_FIELDS = b"""#if D_HQ && !DEV
    uint64_t nodes,keys[HISTORY+PLY];
#else
    uint64_t nodes,keys[HISTORY+PLY]; int length;
#endif"""
PREFIX_READ = b"""#if D_HQ && !DEV
    int length=game_length+ply;
    int repetitions=0,end=length-1-p->half;
    if(end<0)end=0;
    for(int i=length-3;i>=end;i-=2)repetitions+=w->keys[i]==p->h;
#else
    int repetitions=0,end=w->length-1-p->half;
    if(end<0)end=0;
    for(int i=w->length-3;i>=end;i-=2)repetitions+=w->keys[i]==p->h;
#endif"""
SHARED_READ = b"""    int length=game_length+ply;
    int repetitions=0,end=length-1-p->half;
    if(end<0)end=0;
    for(int i=length-3;i>=end;i-=2)
        repetitions+=(i<game_length?game_keys[i]:w->keys[i-game_length])==p->h;"""
PREFIX_WRITE = b"""#if D_HQ && !DEV
        w->keys[length]=q.h;
#else
        w->keys[w->length++]=q.h;
#endif"""
PREFIX_POP = b"""#if !D_HQ || DEV
        --w->length;
#endif
"""
PREFIX_COPY = b"""#if !D_HQ || DEV
    w->length=game_length;
#endif
    memcpy(w->keys,game_keys,game_length*sizeof(uint64_t));
"""


def pin(data: bytes) -> dict:
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


def _project(source: bytes, edits: list[tuple[str, bytes, bytes]]) -> tuple[bytes, dict]:
    rows = []
    for role, before, after in edits:
        if not before or source.count(before) != 1:
            raise ValueError("unique storage role required: " + role)
        rows.append((source.index(before), role, before, after))
    output, proof, gaps, cursor, target = [], [], [], 0, 0
    for begin, role, before, after in sorted(rows):
        if begin < cursor:
            raise ValueError("overlapping storage role: " + role)
        gap = source[cursor:begin]
        output.extend((gap, after))
        gaps.append(pin(gap))
        target += len(gap)
        proof.append(dict(role=role, source=begin, target=target,
                          before=before.decode(), after=after.decode()))
        target += len(after)
        cursor = begin + len(before)
    output.append(source[cursor:])
    gaps.append(pin(source[cursor:]))
    result = b"".join(output)
    record = dict(input=pin(source), output=pin(result), edits=proof,
                  protected_gaps=gaps)
    if _restore(result, record) != source:
        raise ValueError("storage whole-source inverse differs")
    return result, record


def _restore(output: bytes, record: dict) -> bytes:
    if pin(output) != record["output"]:
        raise ValueError("storage output differs")
    result, gaps, cursor = [], [], 0
    for row in record["edits"]:
        begin, after = row["target"], row["after"].encode()
        if begin < cursor or output[begin:begin + len(after)] != after:
            raise ValueError("storage inverse role differs")
        gap = output[cursor:begin]
        gaps.append(pin(gap))
        result.extend((gap, row["before"].encode()))
        cursor = begin + len(after)
    result.append(output[cursor:])
    gaps.append(pin(output[cursor:]))
    restored = b"".join(result)
    if pin(restored) != record["input"] or gaps != record["protected_gaps"]:
        raise ValueError("storage inverse/complement differs")
    return restored


def transform(files: dict[str, bytes], *, prefix: bool = True,
              dense: bool = True) -> tuple[dict[str, bytes], dict]:
    if type(prefix) is not bool or type(dense) is not bool:
        raise ValueError("explicit Boolean storage projections required")
    if (not isinstance(files, dict) or not files or
            any(not isinstance(n, str) or not isinstance(data, bytes) or b"\r" in data
                for n, data in files.items())):
        raise ValueError("normalized D source mapping required")
    actual = {name: sha256(data).hexdigest() for name, data in files.items()}
    cohort = next((name for name, expected in INPUTS.items() if actual == expected), None)
    if cohort is None:
        raise ValueError("exact complete scalar D profile cohort required")
    result = dict(files)
    roles = {"tiny.h": [], "search.c": []}
    if prefix:
        roles["tiny.h"].append(("private-PLY-path-only", PREFIX_FIELDS,
                               b"    uint64_t nodes,keys[PLY];"))
        roles["search.c"] += [
            ("shared-prefix-repetition-read", PREFIX_READ, SHARED_READ),
            ("private-child-path-write", PREFIX_WRITE, b"        w->keys[ply]=q.h;"),
            ("ply-is-path-depth", PREFIX_POP, b""),
            ("immutable-prefix-no-copy", PREFIX_COPY, b""),
        ]
    if dense:
        roles["tiny.h"] += [
            ("dense-history-storage",
             b"int16_t history[128][128],continuation[13][13],correction[1024];",
             b"int16_t history[64][64],continuation[13][13],correction[1024];"),
            ("valid-square-bijection", b"int value(int,int);\n",
             b"int value(int,int);\nstatic inline int square64(int q){return (q+(q&7))>>1;}\n"),
        ]
        roles["search.c"] += [
            ("dense-history-order-read", b"w->history[from][to]+w->continuation[prior][pi]",
             b"w->history[square64(from)][square64(to)]+w->continuation[prior][pi]"),
            ("dense-history-learner-write", b"learn(&w->history[from][to],bonus);",
             b"learn(&w->history[square64(from)][square64(to)],bonus);"),
        ]
    edits = {}
    for name, changes in roles.items():
        if changes:
            result[name], edits[name] = _project(files[name], changes)
    proof = {
        "kind": "D-scalar-prefix-dense-storage-v1", "cohort": cohort,
        "prefix": prefix, "dense": dense,
        "scope": "D_HQ=0, DEV=0, PLY=128, HISTORY=4096; source/domain proof only",
        "input": {name: pin(data) for name, data in sorted(files.items())},
        "output": {name: pin(data) for name, data in sorted(result.items())},
        "source_edits": edits,
        "contracts": {
            "prefix_owner": "main; immutable until existing pending/output wait fence",
            "private_path": "keys[ply] stores the child at ply+1; length=game_length+ply",
            "repetition": "same logical index window and parity; shared prefix + private path",
            "history": "square64 is a bijection on gen-proved legal 0x88 endpoints",
            "learner_lifetime": "unchanged process lifetime; no clear/copy added",
            "search_policy_changed": False,
            "native_identity_claimed": False,
        },
        "raw_component_saving_bytes_per_worker": {
            "history_prefix": 4096 * 8 if prefix else 0,
            "dense_history": (128 * 128 - 64 * 64) * 2 if dense else 0,
        },
    }
    if restore(result, proof) != files:
        raise ValueError("complete storage cohort inverse differs")
    return result, proof


def restore(files: dict[str, bytes], proof: dict) -> dict[str, bytes]:
    if proof.get("kind") != "D-scalar-prefix-dense-storage-v1":
        raise ValueError("unknown D storage proof")
    if {name: pin(data) for name, data in sorted(files.items())} != proof["output"]:
        raise ValueError("complete storage output cohort differs")
    result = dict(files)
    for name, record in proof["source_edits"].items():
        result[name] = _restore(result[name], record)
    if {name: pin(data) for name, data in sorted(result.items())} != proof["input"]:
        raise ValueError("complete storage input cohort differs")
    return result
