"""One semantic ownership rewrite, admitted only for the exact original runtime."""
import hashlib

ORIGINAL_SHA = '5b20d4e60d60b5edfb4b7b5a15217346098f0bd9ccdd155a7369c90743e81ed1'
LOOP = b'    for(int i=0;i<WORKERS;i++){workers[i].depth=workers[i].score=0;workers[i].best=0;workers[i].nodes=0;}\n'
BEFORE = b'        seen=current;think(w,&position);\n'
AFTER = b'        seen=current;w->best=0;think(w,&position);\n'


def transform(original):
    if hashlib.sha256(original).hexdigest() != ORIGINAL_SHA:
        raise ValueError('unknown original D runtime')
    if original.count(LOOP) != 1 or original.count(BEFORE) != 1:
        raise ValueError('original two fragments differ')
    candidate = original.replace(LOOP, b'').replace(BEFORE, AFTER)
    # Both exact fragments are adjacent to unchanged publication statements.
    fence = b'    atomic_store_explicit(&pending,WORKERS+1,memory_order_relaxed);'
    if candidate.count(AFTER) != 1 or candidate.count(fence) != 1:
        raise ValueError('candidate placement differs')
    restored = candidate.replace(AFTER, BEFORE).replace(fence, LOOP+fence)
    if restored != original or len(candidate) != len(original)-96:
        raise ValueError('change escaped the exact two-fragment complement')
    return candidate
