"""Fixed full C entries with process-wide TCEC terminal lifetime.

The persistent pool and every live-job publication/completion boundary remain.
Only process-final worker shutdown, handle retention, joins and table free are
removed.  A failed pthread_create returns 2 from main, ending the whole process.
The default terminal drain preserves completed output before main falls through
with status 0.  ``immediate`` is a separately declared quit/EOF contract that
does not wait for an active search.  This is not a general C optimizer.
"""
import hashlib


PROFILES = {
    'A': ((8335, '2d077291e5615790206a43399d809b23aca5a2deec17623cd4c32f40fcb1ebf4'), 2,
          'static', 'L', 'J', 'qk', 'qm', 'I', 'qb', 'A', 'K', 'id', 'V', 'd', 'N', 'j'),
    'B': ((9744, '4b3412e3dddbe4cc9b40172be66d577aa998dc65e4ffa5876827f6b92654c5a8'), 2,
          'static', 'I', 'return', 'qk', 'qm', 'qj', 'qb', 's', 'qr', 'id', 'd', 'f', 'qq', 'U'),
    'C': ((8970, '391944ca8e3fbe1c0064793232ad0664b8e282b812455c47d3047fcee9baec62'), 2,
          'static', 'int', 'return', 'qk', 'qm', 'qj', 'qb', 'A', 'qr', 'id', 'V', 'd', 'qq', 'j'),
    'E': ((8526, 'c0b01df4c8a330fce2fdfe28a15feb885ce1155e3dddf59b739c0c39f5652b75'), 2,
          'static', 'L', 'J', 'qk', 'qm', 'qj', 'qb', 'A', 'qr', 'id', 'V', 'd', 'qq', 'j'),
    'F2': ((7712, '546df93f9d7f6e6f8b8bdf76b8e3d5e7f9c92913f33db7bd77deec8d50bef20e'), 2,
           'aa', 'S', 'H', 'C', 'A', 'J', 'u', 'qq', 'U', 'a', 'd', 'f', 'B', 'k'),
    'F8': ((7868, 'fb18e915ca1236a25c9c2969c8c2b45d8000e2a701aede3490306b6246eb4865'), 8,
           'static', 'S', 'H', 'C', 'A', 'J', 'u', 'qq', 'U', 'a', 'd', 'f', 'B', 'k'),
}


def pin(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def require(value, message):
    if not value:
        raise ValueError(message)


def _profile(family, workers):
    require(family in ('A', 'B', 'C', 'E', 'F'), 'explicit maintained full family required')
    require(type(workers) is int and workers in ((2, 8) if family == 'F' else (2,)),
            'unsupported fixed full resource profile')
    return family + str(workers) if family == 'F' else family


def restore_source(candidate, proof):
    require(type(candidate) is bytes and proof.get('kind') == 'tcec-process-final-v1'
            and pin(candidate) == proof.get('output'), 'terminal source output pin differs')
    source = candidate
    for edit in reversed(proof['edits']):
        at = edit['new_start']
        old, new = edit['old'].encode('ascii'), edit['new'].encode('ascii')
        require(source[at:at + len(new)] == new, 'terminal source inverse span differs')
        source = source[:at] + old + source[at + len(new):]
    require(pin(source) == proof['input'], 'terminal source inverse input differs')
    return source


def transform_source(source, *, family='F', workers=2, final='drain'):
    """Return one exact shipping-source specialization and complete inverse.

    Runtime policy changes are confined to final process termination.  Memory,
    TT and learner state cannot be reused for another GO until the unchanged
    completion boundary has run.  No chess feature or promotion is removed.
    """
    key = _profile(family, workers)
    require(final in ('drain', 'immediate'), 'explicit terminal output policy required')
    (expected, count, storage, integer, returns, pending, quitting, mutex, condition,
     work, pool, identity, created, status, table, wait) = PROFILES[key]
    require(type(source) is bytes and (len(source), hashlib.sha256(source).hexdigest()) == expected,
            'unknown full C source for process-final specialization')
    text = source.decode('ascii')
    terminal = (
        'shutdown:pthread_mutex_lock(&' + mutex + ');' + quitting + '=1;'
        'pthread_cond_broadcast(&' + condition + ');pthread_mutex_unlock(&' + mutex + ');'
        'for(' + integer + ' i=0;i<' + created + ';i++)if(pthread_join(a[i],NULL))'
        + status + '=2;free(' + table + ');' + returns + ' ' + status + ';}')
    changes = [
        ('terminal-flag', f'{storage} {integer} {pending}={count},{quitting};',
         f'{storage} {integer} {pending}={count};'),
        ('worker-wait-predicate', '&&!' + quitting, ''),
        ('worker-terminal-branch', 'if(' + quitting + ')break;', ''),
        ('unreachable-worker-return', 'pthread_mutex_unlock(&' + mutex + ');' + returns + ' NULL;', ''),
        ('startup-storage', f'pthread_t a[{count}];{integer} {created}=0,{status}=0;', 'pthread_t a;'),
        ('startup-counter-scope', f'for(;{created}<{count};{created}++)',
         f'for({integer} {created}=0;{created}<{count};{created}++)'),
        ('partial-create-process-exit',
         f'if(pthread_create(a+{created},NULL,{work},{pool}+{created})){{{status}=2;goto shutdown;}}',
         f'if(pthread_create(&a,NULL,{work},{pool}+{created})){returns} 2;'),
        ('process-final', (wait + '();' if final == 'immediate' else '') + terminal, '}'),
    ]
    located = []
    for role, old, new in changes:
        require(text.count(old) == 1, 'one exact terminal source role required: ' + role)
        located.append((text.index(old), role, old, new))
    located.sort()
    pieces, edits, gaps = [], [], []
    old_at = new_at = 0
    for at, role, old, new in located:
        require(at >= old_at, 'overlapping terminal source roles')
        gap = source[old_at:at]
        pieces.extend((gap, new.encode('ascii')))
        gaps.append({'old_start': old_at, 'new_start': new_at, **pin(gap)})
        new_at += len(gap)
        edits.append({'role': role, 'old_start': at, 'new_start': new_at, 'old': old, 'new': new})
        old_at, new_at = at + len(old), new_at + len(new)
    pieces.append(source[old_at:])
    gaps.append({'old_start': old_at, 'new_start': new_at, **pin(source[old_at:])})
    result = b''.join(pieces)
    proof = {'kind': 'tcec-process-final-v1', 'family': family, 'workers': workers,
             'profile': key, 'final': final, 'input': pin(source), 'output': pin(result),
             'raw_delta': len(result) - len(source), 'edits': edits, 'protected_gaps': gaps,
             'full_inverse': True, 'runtime': 'persistent', 'runtime_qualified': False,
             'contract': {'terminal_status': 'main fallthrough0; pthread_create failure main return2',
                 'final_drain': final == 'drain',
                 'closing_result': 'existing stop/drain and flush retained' if final == 'drain'
                                   else 'active quit/EOF may end without closing result',
                 'GO_startup_position_completion_unchanged': True,
                 'workers_and_TT_resources_unchanged': True,
                 'learners_search_rules_and_NBRQ_unchanged': True,
                 'terminal_join_free_and_worker_return_removed': True,
                 'runtime_representation_change': 'process lifetime owns final worker and allocation release',
                 'not_preserved': ['per-worker terminal return and pthread_join errors',
                                   'partial-create worker recovery', 'final heap free observations']}}
    require(restore_source(result, proof) == source, 'terminal source complete inverse differs')
    for gap in gaps:
        a, b, n = gap['old_start'], gap['new_start'], gap['bytes']
        require(source[a:a + n] == result[b:b + n], 'terminal source protected gap differs')
    require(b'pthread_join(' not in result and b'goto shutdown' not in result,
            'terminal join/recovery remains in specialized source')
    return result, proof
