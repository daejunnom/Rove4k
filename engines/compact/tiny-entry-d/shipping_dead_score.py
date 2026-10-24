"""Scalar-only dead published score proposal; byte transform, no tool calls."""
import hashlib

POLICY = 'scalar-unread-published-score-v1'

INPUTS = {
    'tiny.h': 'dd9984b45046abbae0d203a9adf3cd826685723df41042ecb214e6757c76bdde',
    'search.c': '6f28dc49b1caf346ead734b4d054039418ce863d039a9ad18cd5b9477884f150',
}
EDITS = {
    'tiny.h': ((b'int id,depth,score; Move best;', b'int id,depth; Move best;'),),
    'search.c': (
        (b'w->nodes=0;w->depth=0;w->score=0;', b'w->nodes=0;w->depth=0;'),
        (b'int score=search(w,p,depth,-MATE,MATE,0,0,&best);', b'search(w,p,depth,-MATE,MATE,0,0,&best);'),
        (b'w->best=best;w->score=score;w->depth=depth;', b'w->best=best;w->depth=depth;'),
    ),
}


def transform_sources(sources, *, hq=0, dev=0):
    if hq not in (0, 1) or dev not in (0, 1):
        raise ValueError('fixed Boolean D profile required')
    if hq or dev:
        return dict(sources), {'applied': False, 'identity': True}
    if set(sources) != set(INPUTS):
        raise ValueError('two current scalar generated sources required')
    sha = lambda data: hashlib.sha256(data).hexdigest()
    result, proof = {}, {}
    for name, source in sources.items():
        if b'\r' in source or sha(source) != INPUTS[name]:
            raise ValueError('current normalized scalar source differs: '+name)
        output, cursor, gaps, inverse, rows = bytearray(), 0, [], [], []
        for old, new in EDITS[name]:
            if source.count(old) != 1:
                raise ValueError('unique dead-score role differs')
            at = source.index(old)
            if at < cursor:
                raise ValueError('source-role order differs')
            gap = source[cursor:at]
            gaps.append(gap)
            output += gap
            inverse.append((len(output), old, new))
            rows.append({'old_offset': at, 'new_offset': len(output), 'old_bytes': len(old), 'new_bytes': len(new)})
            output += new
            cursor = at+len(old)
        gaps.append(source[cursor:])
        output += gaps[-1]
        output = bytes(output)
        restored = bytearray(output)
        for at, old, new in reversed(inverse):
            if restored[at:at+len(new)] != new:
                raise ValueError('inverse role differs')
            restored[at:at+len(new)] = old
        cursor, actual_gaps = 0, []
        for at, old, new in inverse:
            actual_gaps.append(output[cursor:at])
            cursor = at+len(new)
        actual_gaps.append(output[cursor:])
        if bytes(restored) != source or actual_gaps != gaps:
            raise ValueError('full inverse/protected complement differs')
        result[name] = output
        proof[name] = {'old_bytes': len(source), 'old_sha256': sha(source),
            'new_bytes': len(output), 'new_sha256': sha(output), 'edits': rows,
            'gaps': [{'bytes': len(gap), 'sha256': sha(gap)} for gap in gaps],
            'full_inverse_exact': True, 'complement_exact': True}
    return result, {'applied': True, 'sources': proof, 'validation': 'source bytes only; no C behavior or cost result'}
