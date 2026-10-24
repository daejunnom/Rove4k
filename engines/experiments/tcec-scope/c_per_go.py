"""Fixed full-F TCEC candidates with fresh search threads for each GO.

Worker records remain static and retain history, continuation and correction
learning between moves. Async uses an atomic completion chain for the last
worker's result and main-owned joins before the next position/GO. Its final
quit/EOF exits the process without a final result guarantee. Spawn and main
are synchronous comparison policies; their queued commands wait for finite
search completion and do not meet the immediate ready-during-search contract.
"""
import hashlib


INPUTS = {
    'F2': (7712, '546df93f9d7f6e6f8b8bdf76b8e3d5e7f9c92913f33db7bd77deec8d50bef20e'),
    'F8': (7868, 'fb18e915ca1236a25c9c2969c8c2b45d8000e2a701aede3490306b6246eb4865'),
}
VARIANTS = ('spawn', 'main', 'async')


def pin(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def require(value, message):
    if not value:
        raise ValueError(message)


def transform_source(source, *, family='F2', variant='async'):
    """Transform one complete admitted source; no file or compiler operations."""
    require(family in INPUTS and variant in VARIANTS, 'explicit F2/F8 per-GO policy required')
    require(type(source) is bytes and (len(source), hashlib.sha256(source).hexdigest()) == INPUTS[family],
            'fixed maintained full-F input differs')
    count = 2 if family == 'F2' else 8
    st = 'aa ' if family == 'F2' else 'static '
    declarations = (st + 'pthread_mutex_t J=PTHREAD_MUTEX_INITIALIZER;' + st +
        'pthread_cond_t u=PTHREAD_COND_INITIALIZER;' + st + f'S C={count},A;')
    work = (st + 'void*qq(void*p){X*w=p;pthread_mutex_lock(&J);--C;pthread_cond_broadcast(&u);'
        'for(;;){while(w->b>=0&&!A)pthread_cond_wait(&u,&J);if(A)break;w->b=0;'
        'pthread_mutex_unlock(&J);i(w,&Z);pthread_mutex_lock(&J);'
        'if(!--C)y(),pthread_cond_broadcast(&u);}pthread_mutex_unlock(&J);H NULL;}')
    wait = (st + 'void k(void){atomic_store(&V,1);pthread_mutex_lock(&J);'
        'while(C)pthread_cond_wait(&u,&J);pthread_mutex_unlock(&J);}')
    startup = (f'for(;d<{count};d++){{U[d].a=d;if(pthread_create(a+d,NULL,qq,U+d))'
        '{f=2;goto shutdown;}}k();')
    publish = ('pthread_mutex_lock(&J);C=' + str(count) + ';' +
        ('U->b=U[1].b=-1;' if count == 2 else 'for(S i=0;i<8;i++)U[i].b=-1;') +
        'pthread_cond_broadcast(&u);pthread_mutex_unlock(&J);')
    terminal = ('}}k();shutdown:pthread_mutex_lock(&J);A=1;pthread_cond_broadcast(&u);'
        'pthread_mutex_unlock(&J);for(S i=0;i<d;i++)if(pthread_join(a[i],NULL))f=2;free(B);H f;}')
    asynchronous = variant == 'async'
    if asynchronous:
        launch = (f'atomic_store(&A,{count});C={count};for(S n=0;n<{count};n++)'
            '{U[n].a=n;U[n].b=0;if(pthread_create(t+n,NULL,qq,U+n))exit(2);}')
    elif variant == 'spawn':
        launch = (f'pthread_t t[{count}];for(S n=0;n<{count};n++){{U[n].a=n;U[n].b=0;'
            'if(pthread_create(t+n,NULL,qq,U+n))exit(2);}' +
            f'for(S n=0;n<{count};n++)if(pthread_join(t[n],NULL))exit(2);y();')
    else:
        launch = (f'pthread_t t[{count-1}];U->b=0;for(S n=1;n<{count};n++){{U[n].a=n;U[n].b=0;'
            'if(pthread_create(t+n-1,NULL,qq,U+n))exit(2);}qq(U);' +
            f'for(S n=0;n<{count-1};n++)if(pthread_join(t[n],NULL))exit(2);y();')
    replacements = (
        ('pool-only declarations', declarations,
         st + f'pthread_t t[{count}];' + st + 'S C;' + st + 'atomic_int A;' if asynchronous else ''),
        ('one-shot worker', work, st + 'void*qq(void*p){i(p,&Z);' +
         ('if(atomic_fetch_sub(&A,1)==1)y();' if asynchronous else '') + 'H NULL;}'),
        ('pool wait function', wait, st + 'void k(void){atomic_store(&V,1);'
         'while(C)if(pthread_join(t[--C],NULL))exit(2);}' if asynchronous else ''),
        ('startup handles and status', f'S main(void){{pthread_t a[{count}];S d=0,f=0;', 'S main(void){'),
        ('persistent thread startup', startup, ''),
        ('position is after prior GO joins', 'else if(!strcmp(l,"position")){k();z();}',
         'else if(!strcmp(l,"position")){' + ('k();' if asynchronous else '') + 'z();}'),
        ('GO is after prior GO joins', 'else if(!strcmp(l,"go")){k();',
         'else if(!strcmp(l,"go")){' + ('k();' if asynchronous else '')),
        ('GO-owned thread lifetime and result', publish, launch),
        ('process-final exit', terminal, '}}H 0;}'),
    )
    text = source.decode('ascii')
    found = []
    for role, old, new in replacements:
        require(text.count(old) == 1, 'one exact per-GO role required: ' + role)
        at = text.index(old)
        found.append((at, old.encode(), new.encode(), role))
    found.sort()
    result = source
    last = 0
    for at, old, new, role in found:
        require(at >= last, 'overlapping per-GO edits')
        last = at + len(old)
    for at, old, new, role in reversed(found):
        result = result[:at] + new + result[at+len(old):]
    spans, gaps = [], []
    old_at = new_at = delta = 0
    for at, old, new, role in found:
        start = at + delta
        gap = source[old_at:at]
        require(gap == result[new_at:start], 'per-GO protected complement differs')
        gaps.append({'old_start': old_at, 'new_start': new_at, **pin(gap)})
        spans.append({'role': role, 'old_start': at, 'new_start': start,
                      'old': old.decode(), 'new': new.decode()})
        old_at, new_at = at+len(old), start+len(new)
        delta += len(new)-len(old)
    require(source[old_at:] == result[new_at:], 'per-GO protected suffix differs')
    gaps.append({'old_start': old_at, 'new_start': new_at, **pin(source[old_at:])})
    require(all(token not in result for token in
        (b'pthread_mutex_', b'pthread_cond_', b'shutdown:', b'free(B)')), 'pool-only lifecycle remains')
    require(result.count(b'pthread_create(') == result.count(b'pthread_join(') == 1,
            'one bounded spawn/join site required')
    proof = {'kind': 'fixed-full-F-per-GO', 'family': family, 'variant': variant,
        'input': pin(source), 'output': pin(result), 'raw_delta': len(result)-len(source),
        'spans': spans, 'protected_gaps': gaps, 'full_inverse': True,
        'contract': {'workers': count, 'tt_bits': 18, 'ply': 128,
            'persistent_worker_records_and_learners': True,
            'clock_local_counter_and_search_bodies_unchanged': True,
            'all_NBRQ_and_position_parser_unchanged': True,
            'completed_depth_seed': 'all workers b=0 before think; best/depth completed updates unchanged',
            'result_selection': 'unchanged strict completed-depth comparison; worker0 ties; fallback retained',
            'publication': ('seq_cst fetch_sub completion chain before last-worker selector; '
                            'main joins before next GO/position' if asynchronous else
                            'pthread_join before selector, next GO and position mutation'),
            'worker_lifetime': ('fresh every GO; main joins exactly once before next GO/position; '
                                'completed joinable storage may persist between jobs' if asynchronous else
                                'fresh every GO; all joined before command input resumes'),
            'startup_native_TIDs': 1,
            'active_native_TID_cap': count if variant == 'main' else count+1,
            'between_GO_native_TIDs': 1,
            'join_owner': 'main',
            'thread_creation_or_join_failure': 'process-wide exit2; no recovery/reuse',
            'process_final': ('main return0 without terminal joins/free; active result may be lost' if asynchronous else
                              'main return0 without terminal joins/free (already no active GO)'),
            'input_during_GO': 'asynchronous' if asynchronous else 'synchronous',
            'input_detail': ('isready may reply during search; next GO/position stops and joins prior work' if asynchronous else
                             'queued until finite GO completes; no immediate ready/quit promise'),
            'same_as_persistent_pool': False}, 'runtime_qualified': False}
    require(restore_source(result, proof) == source, 'per-GO full inverse differs')
    return result, proof


def restore_source(candidate, proof):
    require(type(candidate) is bytes and proof.get('kind') == 'fixed-full-F-per-GO'
            and pin(candidate) == proof.get('output'), 'per-GO output pin differs')
    result = candidate
    for edit in reversed(proof['spans']):
        at, old, new = edit['new_start'], edit['old'].encode(), edit['new'].encode()
        require(result[at:at+len(new)] == new, 'per-GO inverse span differs')
        result = result[:at] + old + result[at+len(new):]
    require(pin(result) == proof['input'], 'per-GO input inverse differs')
    return result
