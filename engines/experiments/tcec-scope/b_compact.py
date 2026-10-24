"""Finite full-B source forms after the minimal TCEC lifetime/input stages.

This experiment admits two exact source stages.  It removes only unconsumed shipping
score copies and a recursively forwarded unused SEE argument.  Optional literal
and macro forms are compared by actual complete package cost; none is selected
by raw source length.  Search, learning, move generation, clocks and resources
are not replaced.  Source locations and private C layout/names are not an ABI.
"""
import hashlib
import re


INPUTS = ((9370, 'c4ac5454dd41f91d521eec410cf91e495adf86d7efbb26db8c3a08e2000df168'),
          (9283, '299576f55bde0bf125cfd81c9eeb074b16f58d428453c6378de1a58c45e4e504'))
TOKEN = re.compile(rb'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[A-Za-z_]\w*')
FORMS = ('score', 'see', 'constants', 'promotion', 'bitindex', 'hash', 'return', 'static', 'atomic', 'mutex')


def pin(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def require(value, message):
    if not value:
        raise ValueError(message)


def restore_source(candidate, proof):
    require(type(candidate) is bytes and proof.get('kind') == 'tcec-B-compact-v1'
            and pin(candidate) == proof.get('output'), 'B compact output differs')
    data = candidate
    for edit in reversed(proof['edits']):
        at = edit['new_start']
        old, new = edit['old'].encode('ascii'), edit['new'].encode('ascii')
        require(data[at:at + len(new)] == new, 'B compact inverse span differs')
        data = data[:at] + old + data[at + len(new):]
    require(pin(data) == proof['input'], 'B compact inverse input differs')
    return data


def transform_source(source, *, forms=('score', 'see')):
    """Return a bounded equivalent form and exact inverse/protected spans.

    ``score`` drops the Worker score field and its stores, while still calling
    P for all search effects.  ``see`` removes only Q's unused forwarded Worker
    parameter.  Other forms expand back to the same C preprocessing tokens or
    fixed unsigned-64/constant-expression values on the admitted Linux target.
    """
    require(type(source) is bytes and (len(source), pin(source)['sha256']) in INPUTS,
            'exact post-TCEC full-B source required')
    require(isinstance(forms, (list, tuple)) and len(forms) == len(set(forms))
            and all(form in FORMS for form in forms), 'unknown/duplicate B compact form')
    forms = tuple(form for form in FORMS if form in forms)
    changes, declarations = [], []

    def exact(role, old, new, count=1):
        old, new = old.encode('ascii'), new.encode('ascii')
        require(source.count(old) == count, 'B compact source role count differs: ' + role)
        start = 0
        for _ in range(count):
            at = source.index(old, start)
            changes.append((at, at + len(old), role, old, new))
            start = at + len(old)

    def token(role, old, new):
        old, new = old.encode('ascii'), new.encode('ascii')
        hits = [match for match in TOKEN.finditer(source) if match.group() == old]
        require(hits and not any(match.group() == new for match in TOKEN.finditer(source)),
                'B compact macro token collision: ' + role)
        changes.extend((match.start(), match.end(), role, old, new) for match in hits)

    if 'score' in forms:
        exact('unused-worker-score-field', 'I id,zB,yl;', 'I id,zB;')
        exact('unused-worker-score-reset', 'w->yl=0;', '')
        exact('unused-worker-score-copy', 'w->yl=f;', '')
        exact('unused-result-binding', 'I f=P(w,p,a,-30000,30000,0,6,&d,0,1);',
              'P(w,p,a,-30000,30000,0,6,&d,0,1);')
    if 'see' in forms:
        exact('unused-SEE-parameter', 'Q(zd*w,const za*p,N m)', 'Q(const za*p,N m)')
        exact('unused-SEE-recursive-argument', 'Q(w,&t,MOVE(zJ,yv,z))', 'Q(&t,MOVE(zJ,yv,z))')
        exact('unused-SEE-caller-argument', 'Q(w,p,m)', 'Q(p,m)')
    if 'constants' in forms:
        for old, new, count in [('30000-128', '29872', 4), ('-30000+128', '-29872', 2),
                                ('128-1', '127', 1), ('128-2', '126', 1),
                                ('4096+128', '4224', 1), ('((1u<<18)-1)', '262143u', 1),
                                ('(1<<18)', '262144', 1),
                                ('calloc(1<<18,', 'calloc(262144,', 1)]:
            exact('fold-' + old, old, new, count)
    if 'promotion' in forms:
        exact('boolean-promotion-range', 'for(I z=f?2:0;z<=(f?5:0);z++)',
              'for(I z=f*2;z<=f*5;z++)')
        exact('zero-promotion-material', '(f?qi[f]-100:0)', '(qi[f]-100*!!f)')
    if 'bitindex' in forms:
        exact('ctz-0x88-index', '(i&7)+(i&56)*2', 'i+(i&56)', 2)
        exact('0x88-bit-index', '((q>>4)*8+(q&7))', '((q+(q&7))/2)')
    if 'hash' in forms:
        for value in ('0x9e3779b97f4a7c15', '0xbf58476d1ce4e5b9', '0x94d049bb133111eb'):
            exact('u64-literal-' + value, 'UINT64_C(' + value + ')', value + 'UL')
        exact('u64-one', 'UINT64_C(1)', '((D)1)')
    if 'return' in forms:
        declarations.append('#define l return\n')
        token('return-macro', 'return', 'l')
    if 'static' in forms:
        declarations.append('#define J static\n')
        token('static-macro', 'static', 'J')
    if 'atomic' in forms:
        declarations.extend(('#define ac atomic_load_explicit(&qp,memory_order_relaxed)\n',
                             '#define ad(x) atomic_store(&qp,x)\n'))
        exact('stop-load-macro', 'atomic_load_explicit(&qp,memory_order_relaxed)', 'ac', 6)
        exact('stop-set-macro', 'atomic_store(&qp,1)', 'ad(1)', 4)
        exact('stop-clear-macro', 'atomic_store(&qp,0)', 'ad(0)', 1)
    if 'mutex' in forms:
        declarations.extend(('#define ae pthread_mutex_lock(&qj)\n',
                             '#define af pthread_mutex_unlock(&qj)\n',
                             '#define ag pthread_cond_broadcast(&qb)\n',
                             '#define ah pthread_cond_wait(&qb,&qj)\n'))
        exact('mutex-lock-macro', 'pthread_mutex_lock(&qj)', 'ae', 5)
        exact('mutex-unlock-macro', 'pthread_mutex_unlock(&qj)', 'af', 4)
        exact('cond-broadcast-macro', 'pthread_cond_broadcast(&qb)', 'ag', 2)
        exact('cond-wait-macro', 'pthread_cond_wait(&qb,&qj)', 'ah', 3)
    if declarations:
        exact('macro-definitions', '#define I int\n', '#define I int\n' + ''.join(declarations))
    changes.sort()
    pieces, edits, gaps = [], [], []
    old_at = new_at = 0
    for at, end, role, old, new in changes:
        require(at >= old_at, 'B compact edits overlap: ' + role)
        gap = source[old_at:at]
        pieces.extend((gap, new))
        gaps.append({'old_start': old_at, 'new_start': new_at, **pin(gap)})
        new_at += len(gap)
        edits.append({'role': role, 'old_start': at, 'new_start': new_at,
                      'old': old.decode('ascii'), 'new': new.decode('ascii')})
        old_at, new_at = end, new_at + len(new)
    pieces.append(source[old_at:])
    gaps.append({'old_start': old_at, 'new_start': new_at, **pin(source[old_at:])})
    result = b''.join(pieces)
    proof = {'kind': 'tcec-B-compact-v1', 'forms': forms, 'input': pin(source),
             'output': pin(result), 'edits': edits, 'protected_gaps': gaps,
             'full_inverse': True, 'source_only': True,
             'search_learning_NBRQ_repetition_time_resources_preserved': True,
             'native_identity_claimed': False, 'runtime_qualified': False}
    require(restore_source(result, proof) == source, 'B compact full inverse differs')
    for gap in gaps:
        a, b, n = gap['old_start'], gap['new_start'], gap['bytes']
        require(source[a:a + n] == result[b:b + n], 'B compact protected gap differs')
    return result, proof
