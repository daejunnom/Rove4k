"""Source-owned scalar D profiles for the general 4K division.

The maintained own-ELF remains an exact control. This producer deliberately
starts with its readable dynamic-TT sources, not a restored image or an old
generated source. The new startup clear belongs to the existing persistent
workers, before their release arrival. No target TT is allocated here.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CANONICAL = ROOT / "engines/compact/tiny-entry-d"
HOST = "engines/experiments/tcec-scope/build.py"
HOST_SHA = "fc916e798952cff1c915a6846e758874bc2d858b3c59dec73870b95c7e3d4828"
UNITS = ("board.c", "search.c", "runtime.c", "start.S")
FILES = ("tiny.h", *UNITS, "image.ld")


def normalized(path):
    data = Path(path).read_bytes().replace(b"\r\n", b"\n")
    if b"\r" in data:
        raise ValueError("lone CR in named source: " + str(path))
    return data


def pin(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def production():
    return load("tiny_d_production_contracts", ROOT / "engines/scripts/production.py")


def project(source, edits):
    """Apply unique, disjoint roles and retain their full inverse/complement."""
    rows = []
    for role, before, after in edits:
        if source.count(before) != 1:
            raise ValueError("unique source role required: " + role)
        rows.append((source.index(before), role, before, after))
    result, at, target, proof, gaps = [], 0, 0, [], []
    for begin, role, before, after in sorted(rows):
        if begin < at:
            raise ValueError("overlapping source roles: " + role)
        gap = source[at:begin]
        gaps.append(pin(gap))
        result.extend((gap, after))
        target += len(gap)
        proof.append(dict(role=role, begin=begin, target=target,
                          before=before.decode(), after=after.decode()))
        target += len(after)
        at = begin + len(before)
    result.append(source[at:])
    gaps.append(pin(source[at:]))
    output = b"".join(result)
    record = dict(input=pin(source), output=pin(output), edits=proof, gaps=gaps)
    if restore(output, record) != source:
        raise ValueError("full source inverse differs")
    return output, record


def restore(output, record):
    if pin(output) != record["output"]:
        raise ValueError("projection output differs")
    parts, at, gaps = [], 0, []
    for row in record["edits"]:
        begin, after = row["target"], row["after"].encode()
        if begin < at or output[begin:begin + len(after)] != after:
            raise ValueError("projection target differs")
        gap = output[at:begin]
        parts.extend((gap, row["before"].encode()))
        gaps.append(pin(gap))
        at = begin + len(after)
    parts.append(output[at:])
    gaps.append(pin(output[at:]))
    source = b"".join(parts)
    if pin(source) != record["input"] or gaps != record["gaps"]:
        raise ValueError("protected complement differs")
    return source


INITIALIZE = b"""    Worker *w=p;int seen=0;
    /* Entry=16B, pages=256 entries: each worker owns whole fresh pages.
     * All writes precede the existing release arrival; main waits acquire.
     * bits<=34 and workers<=512 keep every intermediate within size_t. */
    size_t pages=((size_t)1<<TT_BITS)/256;
    size_t begin=pages*(unsigned)w->id/WORKERS*256;
    size_t end=pages*((unsigned)w->id+1)/WORKERS*256;
    memset(table+begin,0,(end-begin)*sizeof *table);
"""


def prepare(profile, *, equivalent_edits=True):
    api = production()
    spec = api.engine_spec("D")
    layout = profile.layout(entry_bytes=16)
    # Keep the arithmetic domain of the actual emitted body explicit.
    if not 8 <= layout.bits <= 34 or not 1 <= profile.workers <= 512:
        raise ValueError("unsupported D profile domain")
    recipe_data = normalized(CANONICAL / "recipe.json")
    recipe = json.loads(recipe_data)
    inputs, files = {}, {}
    expected = recipe["native_source_sha256"]
    for name in FILES:
        logical = "engines/compact/tiny-entry-d/native/" + name
        data = normalized(CANONICAL / "native" / name)
        if pin(data)["sha256"] != expected["native/" + name]:
            raise ValueError("maintained D source differs: " + name)
        files[name] = data
        inputs[logical] = pin(data)
    closure = api.SourceClosure.validate(spec, engine_inputs=tuple(inputs), tool_inputs=(
        "engines/compact/tiny-entry-d/recipe.json",
        "engines/compact/tiny-entry-d/shipping_fused_ray.py",
        "engines/experiments/tiny-d-submission/source.py",
        "engines/scripts/production.py"))
    helper_path = CANONICAL / "shipping_fused_ray.py"
    helper_data = normalized(helper_path)
    # The maintained recipe is the authority for this existing pure transform.
    if pin(helper_data)["sha256"] != recipe["shipping_source_sha256"]["shipping_fused_ray.py"]:
        raise ValueError("maintained scalar transform differs")
    helper = load("tiny_d_submission_fused", helper_path)
    files["board.c"], fused = helper.transform_source(files["board.c"])
    proof = {"family": "D", "input_sources": inputs,
             "recipe": pin(recipe_data), "fused": fused,
             "dynamic_TT": True, "cleanup_policy": "loader-owned-fd",
             "model": "scalar-full", "resource": profile.to_record(16),
             "source_edits": {}, "test_only": False, "equivalent_edits": equivalent_edits}
    proof["source_closure"] = closure.to_record()
    edits = {
        "tiny.h": [("profile-width-domain", b"#define MOVES 512",
                    b'_Static_assert(sizeof(size_t)==8 && TT_BITS>=8 && TT_BITS<=34,"D TT width");\n'
                    b'_Static_assert(WORKERS>=1 && WORKERS<=512,"D worker width");\n#define MOVES 512')],
        "search.c": [("64bit-TT-mask", b"(1u<<TT_BITS)", b"(UINT64_C(1)<<TT_BITS)")],
        "runtime.c": [("parallel-TT-before-startup-arrival", b"    Worker *w=p;int seen=0;\n", INITIALIZE)],
        "board.c": [("scalar-only-header", b'#include "hq.h"\n', b"")],
    }
    if equivalent_edits:
        edits["tiny.h"].append(("unread-scalar-score", b"int id,depth,score; Move best;", b"int id,depth; Move best;"))
        edits["search.c"] += [
            ("unread-score-reset", b"w->nodes=0;w->depth=0;w->score=0;", b"w->nodes=0;w->depth=0;"),
            ("unread-score-local", b"int score=search(w,p,depth,-MATE,MATE,0,0,&best);", b"search(w,p,depth,-MATE,MATE,0,0,&best);"),
            ("unread-score-publish", b"w->best=best;w->score=score;w->depth=depth;", b"w->best=best;w->depth=depth;"),
        ]
        edits["runtime.c"] += [
            ("REP-copy", b"void *memcpy(void *v,const void *u,size_t n){unsigned char *d=v;const unsigned char *s=u;while(n--)*d++=*s++;return v;}",
             b'void *memcpy(void *v,const void *u,size_t n){void *d=v;const void *s=u;__asm__ volatile("rep movsb":"+D"(d),"+S"(s),"+c"(n)::"memory");return v;}'),
            ("REP-fill", b"void *memset(void *v,int c,size_t n){unsigned char *d=v;while(n--)*d++=(unsigned char)c;return v;}",
             b'void *memset(void *v,int c,size_t n){void *d=v;__asm__ volatile("rep stosb":"+D"(d),"+c"(n):"a"((unsigned char)c):"memory");return v;}'),
            ("bounded-shipping-reply", b"char move[6],reply[256],*s=reply;", b"char move[6],reply[16],*s=reply;"),
        ]
        edits["board.c"] += [
            ("signed-byte-directions", b"static const int steps[16]={33,31,18,14,-14,-18,-31,-33,1,-1,16,-16,17,15,-15,-17};",
             b"static const int8_t steps[16]={33,31,18,14,-14,-18,-31,-33,1,-1,16,-16,17,15,-15,-17};"),
            ("byte-back-rank", b"static const int back[8]={4,2,3,5,6,3,2,4};",
             b"static const int8_t back[8]={4,2,3,5,6,3,2,4};"),
        ]
    for name, roles in edits.items():
        files[name], proof["source_edits"][name] = project(files[name], roles)
    proof["outputs"] = {name: pin(data) for name, data in files.items()}
    return files, proof
