"""B-only clock-first SEE guard; explicit polling-timing policy change.

Deadline is immutable and stop sticky within a production epoch. Complete
legal-LVA values and unknown propagation stay; cancellation observation order
and clock-call traces change. DEV bypass belongs to the caller.
"""
import hashlib

CASES = {('B', 'full'): ((10588, '13f1b0d74752f7aa2743616ad6465d1ee8e1497d70da7d3db242e38bdccc5c3b'),
                 (10577, 'd360c9ca23b30fe7f295d3f1e0012da9618a1a25a6b8b9cec19240fdac6396ae'),
                 ((4610,
                   4610,
                   b'if(atomic_load_explicit(&qp,memory_order_relaxed)||q()>=qc){if(q()>=qc)atomic_store(&qp,'
                   b'1);return SEE_INCOMPLETE;}',
                   b'if(q()>=qc)atomic_store(&qp,1);if(atomic_load_explicit(&qp,memory_order_relaxed))return '
                   b'SEE_INCOMPLETE;'),))}
def transform_source(source, *, family, policy='full'):
    """Replay only frozen literal spans; preserve every other byte."""
    before, after, edits = CASES[(family, policy)]
    if type(source) is not bytes or (len(source), hashlib.sha256(source).hexdigest()) != before:
        raise ValueError('fixed late forms input differs from fixed late source')
    pieces=[];gaps=[];cursor=target_cursor=0
    for start,target,old,new in edits:
        if start<cursor or source[start:start+len(old)]!=old:
            raise ValueError('fixed late forms literal differs')
        gap=source[cursor:start]
        if target_cursor+len(gap)!=target:
            raise ValueError('fixed late forms target differs')
        pieces.extend((gap,new));gaps.append(gap)
        cursor=start+len(old);target_cursor=target+len(new)
    pieces.append(source[cursor:]);gaps.append(source[cursor:]);candidate=b''.join(pieces)
    if (len(candidate),hashlib.sha256(candidate).hexdigest())!=after:
        raise ValueError('fixed late forms output differs')
    inverse=candidate;new_gaps=[];cursor=0
    for start,target,old,new in edits:
        if candidate[target:target+len(new)]!=new:
            raise ValueError('fixed late forms candidate span differs')
        new_gaps.append(candidate[cursor:target]);cursor=target+len(new)
    new_gaps.append(candidate[cursor:])
    for start,target,old,new in reversed(edits):
        inverse=inverse[:target]+old+inverse[target+len(new):]
    if inverse!=source or gaps!=new_gaps:
        raise ValueError('fixed late forms inverse/complement differs')
    remainder=b''.join(gaps)
    return candidate,dict(stage='late-B-clock-first-SEE-guard',family=family,policy=policy,
        input_bytes=before[0],input_sha256=before[1],output_bytes=after[0],output_sha256=after[1],
        literal_spans=len(edits),exact_inverse=True,complement_bytes=len(remainder),
        complement_sha256=hashlib.sha256(remainder).hexdigest(),
        external_reads=0,compiler_codec_engine_executed_by_transform=0)
