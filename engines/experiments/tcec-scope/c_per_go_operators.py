"""Optional two-span refinement of the frozen full-F async per-GO candidate.

C11 N1570 6.2.6.1p9 gives direct atomic stores seq_cst semantics;
6.5.3.1p2-3 and 6.5.16.2p3 give atomic prefix decrement seq_cst RMW.
https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf

A starts at positive W before any thread creation and exactly W workers
decrement it. Thus old-value==1 and !new-value select the same last worker,
with the same acquire/release publication chain. C remains main-only, and
both C=W and atomic A=W are complete before the first pthread_create.
This does not fold the loop index into C or change join ownership/lifetime.
"""
import hashlib


INPUTS = {
    'F2': (7158, '11524f3147574d75198259afa63e4ee92729e3ecc80cfa9856bcff21eff85c3b'),
    'F8': (7301, 'bcbc1dcadebc8bb4dc0a5c21a31d6fc0053037b6a07b7444b533b803d0458c41'),
}
POST_INPUTS = {
    'F2': (7043, '9511f2b0542bf04abeb06cae49a2dd559535b912ac0dec6cc2852cd451e9fc71'),
    'F8': (7186, 'd5abfdd3000b956b0a2a1de11d65fbe379e99d8a327f1470c5439d077a0e0748'),
}
KIND = 'fixed-full-F-per-GO-atomic-operators'


def pin(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def require(ok, detail):
    if not ok:
        raise ValueError(detail)


def transform_source(source, *, family):
    identity = (len(source), hashlib.sha256(source).hexdigest()) if type(source) is bytes else None
    require(family in INPUTS and identity in (INPUTS[family], POST_INPUTS[family]),
            'exact frozen full-F async per-GO source required')
    count = 2 if family == 'F2' else 8
    replacements = (
        ('seq_cst last-completion RMW', b'if(atomic_fetch_sub(&A,1)==1)y();', b'if(!--A)y();'),
        ('main count and seq_cst pending initialization', f'atomic_store(&A,{count});C={count};'.encode(),
         f'A=C={count};'.encode()),
    )
    spans = []
    for role, old, new in replacements:
        require(source.count(old) == 1, 'one exact atomic operator role required: '+role)
        spans.append({'role': role, 'old_start': source.index(old), 'old': old.decode(), 'new': new.decode()})
    spans.sort(key=lambda e: e['old_start'])
    result, old_at, new_at, delta, gaps = source, 0, 0, 0, []
    for edit in reversed(spans):
        at, old, new = edit['old_start'], edit['old'].encode(), edit['new'].encode()
        result = result[:at]+new+result[at+len(old):]
    for edit in spans:
        at, old, new = edit['old_start'], edit['old'].encode(), edit['new'].encode()
        start = at+delta
        require(at >= old_at and source[old_at:at] == result[new_at:start], 'atomic protected gap differs')
        gaps.append({'old_start': old_at, 'new_start': new_at, **pin(source[old_at:at])})
        edit['new_start'] = start
        old_at, new_at = at+len(old), start+len(new)
        delta += len(new)-len(old)
    require(source[old_at:] == result[new_at:], 'atomic protected suffix differs')
    gaps.append({'old_start': old_at, 'new_start': new_at, **pin(source[old_at:])})
    proof = {'kind': KIND, 'family': family,
        'input_stage': 'post-c-input' if identity == POST_INPUTS[family] else 'raw-async',
        'input': pin(source), 'output': pin(result),
        'spans': spans, 'protected_gaps': gaps, 'raw_delta': len(result)-len(source), 'full_inverse': True,
        'contract': {'atomic_pending_type': 'unchanged atomic_int', 'pending_store': 'seq_cst',
            'completion_RMW': 'seq_cst prefix decrement; zero selects last completed worker',
            'publication_chain': 'unchanged transitive acquire/release RMW chain before result selection',
            'main_only_join_count': count, 'loop_index_and_fixed_worker_count_unchanged': True,
            'search_learners_join_selector_input_and_failure_bodies_unchanged': True,
            'standard': 'C11 N1570 6.2.6.1p9, 6.5.3.1p2-3, 6.5.16.2p3'},
        'runtime_qualified': False}
    require(restore_source(result, proof) == source, 'atomic full inverse differs')
    return result, proof


def restore_source(candidate, proof):
    require(type(candidate) is bytes and proof.get('kind') == KIND and pin(candidate) == proof.get('output'),
            'atomic refinement output differs')
    result = candidate
    for edit in reversed(proof['spans']):
        at, old, new = edit['new_start'], edit['old'].encode(), edit['new'].encode()
        require(result[at:at+len(new)] == new, 'atomic inverse span differs')
        result = result[:at]+old+result[at+len(new):]
    require(pin(result) == proof['input'], 'atomic inverse input differs')
    return result
