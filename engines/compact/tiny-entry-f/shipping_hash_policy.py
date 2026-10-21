"""Explicit full/default F hash-policy change, after terminal-loop replay.

Delete only the fixed pre-add from a pure by-value hash function. All hash
values, rolling context, TT and correction buckets change. The remaining
64-bit finalizer is bijective; this is not a claim about position-XOR
collision quality, equal search traces or strength. Full F features stay.
DEV bypass and full-reference ownership belong to the caller.
"""
import hashlib

STAGE='explicit-full-F-no-preadd-hash-policy'
CASES = {'F': ((8998, '94593b739c14afc27bbec0db7d9027cef65e4c7ee1b358f105b1b08f1072ebd2'), (8966, '298f9b9670f7de293e99e56a6c9b7532b29e009fd7f38f90751845f9d675d85b'), ('explicit-no-preadd-hash-policy', 'all-hash-values-and-buckets-change', 'remaining-bijective-64bit-finalizer', 'full-feature-F-retained'), ((869, 869, b'x+=UINT64_C(0x9e3779b97f4a7c15);', b''),))}

def transform_source(source, *, family):
    """Replay fixed literal spans; never read cost artifacts or run build tools."""
    before, after, features, edits = CASES[family]
    if type(source) is not bytes or (len(source), hashlib.sha256(source).hexdigest()) != before:
        raise ValueError('late source replay input differs: ' + family)
    pieces=[]; gaps=[]; cursor=target_cursor=0
    for start,target,old,new in edits:
        if start<cursor or source[start:start+len(old)]!=old:
            raise ValueError('late source replay literal differs')
        gap=source[cursor:start]
        if target_cursor+len(gap)!=target:
            raise ValueError('late source replay target differs')
        pieces.extend((gap,new));gaps.append(gap)
        cursor=start+len(old);target_cursor=target+len(new)
    pieces.append(source[cursor:]);gaps.append(source[cursor:]);candidate=b''.join(pieces)
    if (len(candidate),hashlib.sha256(candidate).hexdigest())!=after:
        raise ValueError('late source replay output differs')
    inverse=candidate;new_gaps=[];cursor=0
    for start,target,old,new in edits:
        if candidate[target:target+len(new)]!=new:
            raise ValueError('late source replay candidate span differs')
        new_gaps.append(candidate[cursor:target]);cursor=target+len(new)
    new_gaps.append(candidate[cursor:])
    for start,target,old,new in reversed(edits):
        inverse=inverse[:target]+old+inverse[target+len(new):]
    if inverse!=source or gaps!=new_gaps:
        raise ValueError('late source replay inverse/complement differs')
    remainder=b''.join(gaps)
    return candidate,dict(family=family,stage=STAGE,input_bytes=before[0],input_sha256=before[1],
        output_bytes=after[0],output_sha256=after[1],features=list(features),literal_spans=len(edits),
        exact_inverse=True,complement_bytes=len(remainder),complement_sha256=hashlib.sha256(remainder).hexdigest(),
        external_reads=0,compiler_codec_engine_executed_by_transform=0)
