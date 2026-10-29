"""Exact B candidate replacing piece-type bitboards by mailbox classification.

The shared walker still visits the same occupancy bits.  Legal-LVA still tries
kind1..6 and, within one kind, increasing CTZ origin.  Each kind restarts from
the complete geometric attacker mask; an illegal pinned origin advances to
the next origin instead of suppressing later choices.  Search transitions,
first-move N/B/R/Q, EP and king safety remain the original functions.

Only two already frozen input sources are admitted.  This module performs no
compiler, file, subprocess, or artifact reads.  Source and layout arithmetic
are not runtime/performance/strength qualification.
"""
import hashlib

KIND = 'B-occupancy-only-mailbox-LVA-v1'
INPUTS = {
    'selected-pool': (8770, '23d9de0788b0058c0a11744290bdf2d39582b16d6af48501d9021bbb57f54bfe'),
    'per-GO': (8314, '005aa4fa0fb2729ea95753db7023d2fb5a9563a3f0279d7d833d656fcab44bab'),
}
VARIANTS = ('branch', 'continue')
OLD_Q = b'J I Q(const za*p,N m){za t;I j=h(p,m,&t)-1;if(j<0)l-30000;I yv=TO(m);if(q()>=qc)atomic_store(&qp,1);if(atomic_load_explicit(&qp,memory_order_relaxed))l SEE_INCOMPLETE;D d=c(&t,0,yv,t.s);for(I k=1;k<7;k++){D b=d&t.a[t.s<0][k];while(b){I i=__builtin_ctzll(b),zJ=i+(i&56);b&=b-1;I z=k==1&&!(yv+16&96)?5:0;I a=Q(&t,MOVE(zJ,yv,z));if(a==SEE_INCOMPLETE)l SEE_INCOMPLETE;if(a!=-30000)l j-(a>0?a:0);}}l j;}'
PREFIX = b'J I Q(const za*p,N m){za t;I j=h(p,m,&t)-1;if(j<0)l-30000;I yv=TO(m);if(q()>=qc)atomic_store(&qp,1);if(atomic_load_explicit(&qp,memory_order_relaxed))l SEE_INCOMPLETE;D d=c(&t,0,yv,t.s);for(I k=1;k<7;k++){D b=d;while(b){I i=__builtin_ctzll(b),zJ=i+(i&56);b&=b-1;'
SUFFIX = b'I z=k==1&&!(yv+16&96)?5:0;I a=Q(&t,MOVE(zJ,yv,z));if(a==SEE_INCOMPLETE)l SEE_INCOMPLETE;if(a!=-30000)l j-(a>0?a:0);'


def pin(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def require(value, message):
    if not value:
        raise ValueError(message)


def transform_source(source, *, variant='branch'):
    require(type(source) is bytes and variant in VARIANTS, 'explicit immutable B source and finite variant required')
    identity = len(source), hashlib.sha256(source).hexdigest()
    stages = [name for name, expected in INPUTS.items() if identity == expected]
    require(len(stages) == 1, 'exact selected B or exact B per-GO source required')
    new_q = (PREFIX + b'if(abs(t.b[zJ])==k){' + SUFFIX + b'}}}l j;}'
             if variant == 'branch' else
             PREFIX + b'if(abs(t.b[zJ])!=k)continue;' + SUFFIX + b'}}l j;}')
    edits = []
    for role, old, new in (
        ('Board occupancy representation', b'D a[2][7];', b'D a[2];'),
        ('put maintains only side occupancy', b'p->a[a<0][abs(a)]^=o(q);p->a[a<0][0]^=o(q);', b'p->a[a<0]^=o(q);'),
        ('shared walker reads same side occupancy', b'b=p->a[s<0][0];', b'b=p->a[s<0];'),
        ('LVA same kind and CTZ order from mailbox', OLD_Q, new_q),
    ):
        require(source.count(old) == 1, 'one exact B state role required: ' + role)
        edits.append({'role': role, 'old_start': source.index(old), 'old': old.decode(), 'new': new.decode()})
    edits.sort(key=lambda row: row['old_start'])
    result = source
    for edit in reversed(edits):
        at, old, new = edit['old_start'], edit['old'].encode(), edit['new'].encode()
        result = result[:at] + new + result[at+len(old):]
    gaps, old_at, new_at, delta = [], 0, 0, 0
    for edit in edits:
        at, old, new = edit['old_start'], edit['old'].encode(), edit['new'].encode()
        start = at + delta
        require(at >= old_at and source[old_at:at] == result[new_at:start], 'state protected gap differs')
        gaps.append({'old_start': old_at, 'new_start': new_at, **pin(source[old_at:at])})
        edit['new_start'] = start
        old_at, new_at = at+len(old), start+len(new)
        delta += len(new)-len(old)
    require(source[old_at:] == result[new_at:], 'state protected suffix differs')
    gaps.append({'old_start': old_at, 'new_start': new_at, **pin(source[old_at:])})
    require(result.count(b'p->a[') == 2 and b't.a[' not in result,
            'unexpected Board bitboard consumer remains')
    proof = {
        'kind': KIND, 'input_stage': stages[0], 'variant': variant,
        'input': pin(source), 'output': pin(result),
        'spans': edits, 'protected_gaps': gaps, 'raw_delta': len(result)-len(source),
        'full_inverse': True,
        'contract': {
            'maintained_value': 'side occupancy exactly equals old bb[side][0]',
            'deleted_duplicate': 'old type masks agree with mailbox piece type under the admitted Board invariant',
            'LVA_order': 'kind1..6, then increasing CTZ origin, restart full d for every kind',
            'illegal_origin': 'unchanged h return0 -> -30000, continue next origin of same kind',
            'promotion': 'all first generated N/B/R/Q and existing internal fixed-target queen composition unchanged',
            'stopped_incomplete': 'unchanged SEE_INCOMPLETE propagation and Q clock/checkpoint sites',
            'protected': 'general h, EP, castle, check, HCE/hash/context, search, learners, TT, line/input and lifecycle',
            'layout_arithmetic': {'removed_uint64_elements': 12, 'removed_bytes_if_uint64_8': 96,
                                  'measured_sizeof': False},
            'source_inspection_only': True,
        },
        'runtime_qualified': False,
    }
    require(_restore(result, proof) == source, 'state full inverse differs')
    return result, proof


def _restore(candidate, proof):
    require(type(candidate) is bytes and proof.get('kind') == KIND
            and pin(candidate) == proof.get('output'), 'state output pin differs')
    result = candidate
    for edit in reversed(proof['spans']):
        at, old, new = edit['new_start'], edit['old'].encode(), edit['new'].encode()
        require(result[at:at+len(new)] == new, 'state inverse replacement differs')
        result = result[:at] + old + result[at+len(new):]
    require(pin(result) == proof.get('input'), 'state inverse input differs')
    return result


def restore_source(candidate, proof):
    original = _restore(candidate, proof)
    repeated, expected = transform_source(original, variant=proof['variant'])
    require(repeated == candidate and expected == proof, 'state full protected proof differs')
    return original
