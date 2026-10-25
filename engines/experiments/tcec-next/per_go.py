"""Asynchronous per-GO workers for the exact selected full A/B/C/E sources.

Worker records and all learners retain process lifetime. The main thread owns
join handles, joins before GO/position reuse, and keeps reading UCI during the
search. An atomic completion chain publishes the unchanged result selector.
Only the pool lifecycle changes; search, clocks, board and learner bodies are
protected byte ranges. This is a source projection, not a runtime claim.
"""
import hashlib


INPUTS = {
    'A': (7869, '248479972fb803223e353b37fbe85f95248d469b4c1c3382babeb15625b0aa72'),
    'B': (8770, '23d9de0788b0058c0a11744290bdf2d39582b16d6af48501d9021bbb57f54bfe'),
    'C': (8486, 'ade8c284fdc5e116e6efd5607a18ba018dbdabf4110675d5eb920eb50fd6aa15'),
    'E': (8063, '80f7c14239baffca5ab1cca8a2f4777691f3dfc7d068b511dc022332590889e5'),
}
CONFIG = {
    # static, int, return, mutex/pending, handles, count, worker type,
    # worker fn, think fn, root, selector, stop, join fn, array, id, depth
    'A': ('static', 'L', 'J', 'I', 'qb', 'qk', 'M', 'A', 'C', 'F', 'x', 'X', 'j', 'K', 'id', 'C'),
    'B': ('J', 'I', 'l', 'qj', 'qb', 'qk', 'zd', 's', 'i', 'ql', 'd', 'qp', 'U', 'qr', 'i', 'd'),
    'C': ('static', 'int', 'return', 'qj', 'qb', 'qk', 'ai', 'A', 'C', 'ql', 'x', 'qp', 'j', 'qr', 'id', 'C'),
    'E': ('static', 'L', 'J', 'qj', 'qb', 'qk', 'ai', 'A', 'C', 'ql', 'x', 'qp', 'j', 'qr', 'id', 'C'),
}
KIND = 'selected-full-ABCE-async-per-GO-v1'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def pin(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def _function(text, signature):
    require(text.count(signature) == 1, 'one exact lifecycle function required: '+signature)
    start = text.index(signature)
    at, depth, quote, escaped = start+len(signature)-1, 0, None, False
    while at < len(text):
        char = text[at]
        if quote:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == quote:
                quote = None
        elif char in ('"', "'"):
            quote = char
        elif char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return text[start:at+1]
        at += 1
    raise ValueError('unterminated lifecycle function')


def transform_source(source, *, family):
    require(type(source) is bytes and family in INPUTS
            and (len(source), hashlib.sha256(source).hexdigest()) == INPUTS[family],
            'exact selected full A/B/C/E source required')
    st, it, ret, pending, handles, count, wt, worker, think, root, select, stop, join, array, ident, depth = CONFIG[family]
    text = source.decode('ascii')
    prefix = st+' '
    declaration = (prefix+'pthread_mutex_t '+pending+'=PTHREAD_MUTEX_INITIALIZER;'+prefix+
                   'pthread_cond_t '+handles+'=PTHREAD_COND_INITIALIZER;'+prefix+it+' '+count+'=2;')
    once = (prefix+'void*'+worker+'(void*p){'+think+'(p,&'+root+');if(!--'+pending+')'+select+'();'+ret+' 0;}')
    wait = (prefix+'void '+join+'(void){atomic_store(&'+stop+',1);while('+count+')'
            'if(pthread_join('+handles+'[--'+count+'],0))exit(2);}')
    publish = ('pthread_mutex_lock(&'+pending+');'+count+'=2;'+array+'->'+depth+'='+array+'[1].'+depth+
               '=-1;pthread_cond_broadcast(&'+handles+');pthread_mutex_unlock(&'+pending+');')
    launch = (pending+'='+count+'=2;for('+it+' n=0;n<2;n++){'+array+'[n].'+ident+'=n;'+array+'[n].'+depth+
              '=0;if(pthread_create('+handles+'+n,0,'+worker+','+array+'+n))exit(2);}')
    loop_id = 'd' if family == 'B' else 'V'
    startup = ('for('+it+' '+loop_id+'=0;'+loop_id+'<2;'+loop_id+'++){'+array+'['+loop_id+'].'+ident+'='+loop_id+
               ';if(pthread_create(&a,NULL,'+worker+','+array+'+'+loop_id+'))'+ret+' 2;}')
    startup += ('pthread_mutex_lock(&'+pending+');while('+count+')pthread_cond_wait(&'+handles+','+'&'+pending+
                ');pthread_mutex_unlock(&'+pending+');' if family == 'B' else join+'();')
    edits = (
        ('pool declarations', declaration, prefix+'pthread_t '+handles+'[2];'+prefix+it+' '+count+';'+prefix+'atomic_int '+pending+';'),
        ('one-shot worker', _function(text, prefix+'void*'+worker+'(void*p){'), once),
        ('main-owned drain', _function(text, prefix+'void '+join+'(void){'), wait),
        ('GO-owned launch', publish, launch),
        ('startup local handle', 'pthread_t a;', ''),
        ('startup workers', startup, ''),
    )
    found = []
    for role, old, new in edits:
        require(text.count(old) == 1, 'one exact lifecycle role required: '+role)
        found.append(dict(role=role, old_start=text.index(old), old=old, new=new))
    found.sort(key=lambda e: e['old_start'])
    result, old_at, new_at, delta, gaps = source, 0, 0, 0, []
    for edit in reversed(found):
        at, old, new = edit['old_start'], edit['old'].encode(), edit['new'].encode()
        result = result[:at]+new+result[at+len(old):]
    for edit in found:
        at, old, new = edit['old_start'], edit['old'].encode(), edit['new'].encode()
        start = at+delta
        require(at >= old_at and source[old_at:at] == result[new_at:start], 'overlapping lifecycle edit')
        gaps.append(dict(old_start=old_at, new_start=new_at, **pin(source[old_at:at])))
        edit['new_start'] = start
        old_at, new_at, delta = at+len(old), start+len(new), delta+len(new)-len(old)
    require(source[old_at:] == result[new_at:], 'protected lifecycle suffix differs')
    gaps.append(dict(old_start=old_at, new_start=new_at, **pin(source[old_at:])))
    require(b'pthread_mutex_' not in result and b'pthread_cond_' not in result,
            'persistent pool operation remains')
    require(result.count(b'pthread_create(') == result.count(b'pthread_join(') == 1,
            'exactly one main-owned create/join site required')
    proof = dict(kind=KIND, family=family, input=pin(source), output=pin(result),
                 raw_delta=len(result)-len(source), spans=found, protected_gaps=gaps, full_inverse=True,
                 contract=dict(workers=2, tt_bits=18, ply=128, persistent_worker_and_learner_storage=True,
                               search_board_history_selector_bodies_and_clock_budget_expressions_unchanged=True,
                               startup_threads=1, active_threads=3, between_GO_threads=1,
                               publication='seq_cst pending store and two decrement RMW chain; last worker unchanged selector',
                               join_owner='main; exactly once before next GO/position mutation',
                               failure='create/join error process-wide exit2',
                               final='main process-wide exit; active closing result optional',
                               active_ready=True), runtime_qualified=False)
    require(restore_source(result, proof) == source, 'full lifecycle inverse differs')
    return result, proof


def restore_source(candidate, proof):
    require(type(candidate) is bytes and proof.get('kind') == KIND and pin(candidate) == proof.get('output'),
            'per-GO output pin differs')
    result = candidate
    for edit in reversed(proof['spans']):
        at, old, new = edit['new_start'], edit['old'].encode(), edit['new'].encode()
        require(result[at:at+len(new)] == new, 'per-GO inverse role differs')
        result = result[:at]+old+result[at+len(new):]
    require(pin(result) == proof['input'], 'per-GO restored input differs')
    return result
