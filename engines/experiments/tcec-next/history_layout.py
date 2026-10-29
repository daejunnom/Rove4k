"""Exact full-C projections for immutable prefix and dense quiet history.

The key prefix remains the published global qg/qh. A private path slot j is
the former worker key[qh+j]. History mapping is a bijection only on valid
0x88 squares; all reachable ordering/update consumers use generated legal
from/to squares. No timing, compiler, file I/O or source fallback occurs here.
"""
import hashlib
import re

INPUTS = {
    'A': (7869, '248479972fb803223e353b37fbe85f95248d469b4c1c3382babeb15625b0aa72'),
    'B': (8770, '23d9de0788b0058c0a11744290bdf2d39582b16d6af48501d9021bbb57f54bfe'),
    'C': (8486, 'ade8c284fdc5e116e6efd5607a18ba018dbdabf4110675d5eb920eb50fd6aa15'),
    'E': (8063, '80f7c14239baffca5ab1cca8a2f4777691f3dfc7d068b511dc022332590889e5'),
    'F': (6901, '46bd9a21026afb7e289acbec67078235563534685f9413fbb989664f7728ea22'),
    'F8': (7049, 'ef538c8d400dcb0fb50e16a4e80886ff7ef192ea4d44a480d49031d71c109e5e'),
}
INFO = {
    'A': ('M', 'K', 'aA', 'zC', 'o', 'P', 'o', 'P'),
    'B': ('zd', 'qr', 'k', 'h', 'zJ', 'to', 'zJ', 'to'),
    'C': ('ai', 'qr', 'aA', 'zC', 'o', 'P', 'o', 'P'),
    'E': ('ai', 'qr', 'aA', 'zC', 'o', 'P', 'o', 'P'),
    'F': ('X', 'U', 'f', 'h', 'L', 'M', 'N', 'O'),
    'F8': ('X', 'U', 'f', 'h', 'L', 'M', 'N', 'O'),
}

def pin(data):
    return len(data), hashlib.sha256(data).hexdigest()

def _require(condition, message):
    if not condition:
        raise ValueError(message)

def _index(name, style):
    if style == 'subtract':
        return name + '-' + name + '/16*8'
    if style == 'fold':
        return '(' + name + '+(' + name + '&7))/2'
    if style == 'macro':
        return 'hs(' + name + ')'
    raise ValueError('unknown exact history index spelling')

def transform_source(source, *, family, prefix=True, dense=True, style='subtract'):
    _require(type(source) is bytes and family in INPUTS and pin(source) == INPUTS[family],
             'fixed current full-C history input differs')
    _require(type(prefix) is bool and type(dense) is bool and (prefix or dense),
             'select at least one history projection')
    _require(style in ('subtract', 'fold', 'macro'), 'unknown history index spelling')
    edits = []

    def replace(old, new, role):
        old, new = old.encode(), new.encode()
        _require(source.count(old) == 1, 'history role must occur exactly once: ' + role)
        edits.append((source.index(old), old, new, role))

    worker, _, path, history, rf, rt, uf, ut = INFO[family]
    if prefix and family not in ('F', 'F8'):
        if family == 'B':
            replace('k[4224]', 'k[128]', 'private-path-declaration')
            replace('w->k[i]', '(i<qh?qg[i]:w->k[i-qh])', 'key-prefix-query')
            replace('w->k[W]=q.h;', 'w->k[n]=q.h;', 'private-child-key-write')
            replace('memcpy(w->k,qg,qh*sizeof(D));', '', 'remove-key-prefix-copy')
        else:
            declaration = 'aA[HISTORY+PLY]' if family == 'A' else 'aA[4096+128]'
            replace(declaration, 'aA[128]', 'private-path-declaration')
            replace('w->aA[i]', '(i<qh?qg[i]:w->aA[i-qh])', 'key-prefix-query')
            replace('w->aA[qh+d]=q.h;', 'w->aA[d]=q.h;', 'private-child-key-write')
            replace('memcpy(w->aA,qg,qh*sizeof(W));', '', 'remove-key-prefix-copy')
    if dense:
        if style == 'macro':
            _require(re.search(rb'\bhs\b', source) is None, 'new history macro name already used')
            marker = b'#define MOVE'
            at = source.index(b'\n', source.index(marker)) + 1
            edits.append((at, b'', b'#define hs(s) ((s)-(s)/16*8)\n', 'dense-index-macro'))
        replace(history + '[128][128]', history + '[64][64]', 'dense-history-declaration')
        # The two accesses may use identical index names. Apply their single
        # shared literal at both admitted sites rather than guessing contexts.
        accesses = {(rf, rt), (uf, ut)}
        for a, b in sorted(accesses):
            old = ('w->' + history + '[' + a + '][' + b + ']').encode()
            new = ('w->' + history + '[' + _index(a, style) + '][' + _index(b, style) + ']').encode()
            count = source.count(old)
            _require(count == (2 if (rf, rt) == (uf, ut) else 1), 'history read/update count differs')
            for match in re.finditer(re.escape(old), source):
                edits.append((match.start(), old, new, 'dense-history-access'))
    edits.sort()
    chunks, gaps, rows = [], [], []
    cursor = target = 0
    for start, old, new, role in edits:
        _require(start >= cursor and source[start:start+len(old)] == old, 'overlapping history edits')
        gap = source[cursor:start]
        chunks.extend((gap, new)); gaps.append(pin(gap)); target += len(gap)
        rows.append(dict(start=start, target=target, old=old.decode(), new=new.decode(), role=role))
        cursor = start + len(old); target += len(new)
    chunks.append(source[cursor:]); gaps.append(pin(source[cursor:]))
    candidate = b''.join(chunks)
    proof = dict(stage='full-C-history-layout-v1', family=family, prefix=prefix, dense=dense,
                 style=style, input=pin(source), output=pin(candidate), edits=rows,
                 protected_gaps=gaps, full_inverse=True,
                 existing_shared_prefix=family in ('F','F8'),
                 key_mapping='old.keys[qh+j]=new.path[j]; absolute i<qh reads qg[i]',
                 prefix_immutable_until_all_search_and_result_work_returns=True,
                 qh_bounds=[1,4096], entry_ply_bounds=[0,127], max_parent_path_write=126,
                 square_mapping='valid square 16*r+f maps to 8*r+f, r/f in0..7',
                 read_update_sites=2, learner_values_and_update_arithmetic_unchanged=True,
                 history_bytes=(32768,8192) if dense else (32768,32768),
                 key_bytes=((1024 if family in ('F','F8') else 33792),
                            (1024 if prefix or family in ('F','F8') else 33792)),
                 Worker_layout_native_and_memory_timing_unchanged=False,
                 compiler_codec_or_runtime_executed=False)
    _require(restore_source(candidate, proof) == source, 'history internal inverse differs')
    return candidate, proof

def restore_source(candidate, proof):
    _require(type(candidate) is bytes and pin(candidate) == tuple(proof['output']), 'history output differs')
    parts, gaps = [], []
    cursor = 0
    for row in proof['edits']:
        old, new = row['old'].encode(), row['new'].encode()
        target = row['target']
        _require(target >= cursor and candidate[target:target+len(new)] == new, 'history inverse span differs')
        gap = candidate[cursor:target]
        parts.extend((gap, old)); gaps.append(pin(gap)); cursor=target+len(new)
    parts.append(candidate[cursor:]); gaps.append(pin(candidate[cursor:]))
    original=b''.join(parts)
    _require(gaps == [tuple(x) for x in proof['protected_gaps']] and pin(original)==tuple(proof['input'])
             and pin(original)==INPUTS[proof['family']], 'history inverse input/gaps differ')
    return original

def source_edits(source, *, family, prefix=True, dense=True, style='subtract'):
    """Admitted base-coordinate edits for explicit nonoverlapping composition."""
    _, proof = transform_source(source, family=family, prefix=prefix, dense=dense, style=style)
    return [dict(begin=row['start'], before=row['old'].encode(), after=row['new'].encode(),
                 role=row['role']) for row in proof['edits']]
