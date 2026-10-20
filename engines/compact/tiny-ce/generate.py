"""Strict C/E overlays over an owned, byte-frozen TinyA core.

Only fixed source shapes are replaced. Every engine keeps the complete board,
incremental HCE/hash, full-key coherent TT, PVS/QS and persistent startup pool.
"""
from pathlib import Path
import hashlib
import json
import struct

HERE = Path(__file__).resolve().parent
MODEL_CANONICAL_SHA256 = "4ff88c9f4dde9d51f69e32e8c9f57ce555361ea9d22086b41e8873bc06c72164"
WEIGHTS = (100, 320, 330, 500, 900, 3, 8, 5, 2, 1, -3, 6, -12, -8, 24, 10, 16, -1, 12, 2, 4)


def replace(text, before, after, count=1):
    if text.count(before) != count:
        raise ValueError(f"fixed TinyA overlay shape changed: {before!r}")
    return text.replace(before, after)


def model_record(data):
    model = json.loads(data)
    canonical = json.dumps(model, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    digest = hashlib.sha256(canonical).hexdigest()
    weights = tuple(model["evaluation"]["weights"] + model["ordering"]["weights"])
    if digest != MODEL_CANONICAL_SHA256 or weights != WEIGHTS:
        raise ValueError("the frozen hand-authored model identity changed")
    return {"id": model["id"], "provenance": model["provenance"],
            "canonical_json_sha256": digest, "weights": list(weights),
            "storage": "exact static signed-16", "coefficient_count": 21,
            "coefficient_bytes": 42,
            "signed16_le_sha256": hashlib.sha256(struct.pack("<21h", *weights)).hexdigest(),
            "raw_evaluation_abs_max": 56224, "ordering_abs_max": 24940,
            "accumulator": "signed-32", "training": False, "quantization": False}


def overlay(combined, variant, evaluator, model_bytes):
    if variant not in ("C", "E"):
        raise ValueError("only separate C or E candidates are selected")
    text = combined.decode().replace("\r\n", "\n")
    evaluation = evaluator.decode().replace("\r\n", "\n")
    model = model_record(model_bytes) if variant == "E" else None
    if variant == "E":
        evaluation = replace(evaluation, "@WEIGHTS@", ",".join(map(str, WEIGHTS)))
    # This location is directly before search.c. Board definitions already
    # precede both evaluators; no duplicate prototypes or module APIs are added.
    text = replace(text, "#if DEV\n#define COUNT(w,f)", evaluation + "\n#if DEV\n#define COUNT(w,f)")
    text = replace(text, "int evaluation=p->s*p->v;", "int evaluation=p->s*tiny_raw(p);")
    text = replace(text, "int error=best-p->s*p->v;", "int error=best-evaluation;")
    text = replace(text, "if(PROMO(m))scores[i]+=400000+PROMO(m)*1000;",
                   "if(PROMO(m))scores[i]+=400000+PROMO(m)*1000;\n        scores[i]+=tiny_order(p,m);")
    text = replace(text, "Rove4k A\\nuciok", "Rove4k " + variant + "\\nuciok")
    text = replace(text, "position.v*position.s", "tiny_raw(&position)*position.s", 2)
    text = replace(text, '\\"ply_aborts\\":%llu}',
                   '\\"ply_aborts\\":%llu,\\"leaf_calls\\":%llu,\\"ordering_calls\\":%llu}')
    text = replace(text, "(unsigned long long)uses,(unsigned long long)aborts);",
                   "(unsigned long long)uses,(unsigned long long)aborts,(unsigned long long)atomic_load(&tiny_leaf_calls),(unsigned long long)atomic_load(&tiny_order_calls));")
    if variant == "E":
        commands = r'''else if(!strcmp(line,"raw")){wait();printf("raw %d\n",tiny_white(&position));fflush(stdout);}
        else if(!strcmp(line,"model")){wait();printf("model");for(int i=0;i<21;i++)printf(" %d",tiny_weights[i]);puts("");fflush(stdout);}
        else if(!strncmp(line,"order ",6)){wait();Move m=parse(&position,line+6);printf("order %d\n",m?tiny_order(&position,m):INT_MIN);fflush(stdout);}
        '''
        text = replace(text, 'else if(!strncmp(line,"perft ",6))', commands + 'else if(!strncmp(line,"perft ",6))')
    return text.encode(), {"variant": variant, "model": model,
                            "leaf_scale": "signed centipawns, fixed across workers and TT publications",
                            "correction_residual": "best minus the same clamped static leaf evaluation",
                            "ordering": "frozen model added to actual move scores" if variant == "E" else "TinyA history/continuation/tactical ordering",
                            "simd": "fixed AVX2, actual leaf result consumed" if variant == "C" else None}
