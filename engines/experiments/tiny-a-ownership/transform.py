"""One fixed selected-A ownership/query change; no new parser or search policy."""
import hashlib

CONTROL_SHA256 = '321ab861fe8e8ebc1791cbd389edbecc53091ede195e172e9983f2455ee12c6d'


def once(source, old, new):
    if source.count(old) != 1:
        raise ValueError('selected source shape changed: ' + old[:72])
    return source.replace(old, new)


def transform(control):
    if hashlib.sha256(control).hexdigest() != CONTROL_SHA256:
        raise ValueError('exact 5207-byte selected readable control required')
    source = control.decode()
    first = source.index('static Move first(')
    end = source.index('static void result(', first)
    original_query = source[first:end]
    query = '''static Move parse(const Board *b,const char *s,Board *c){
    Move list[MOVES];char name[6];int n=gen(b,list);
    for(int i=0;i<n;i++){
        if(s){text(list[i],name);if(strcmp(s,name))continue;}
        if(make(b,list[i],c))return list[i];
    }return 0;
}
'''
    source = source[:first] + query + source[end:]
    source = once(source,
        'Move m=parse(&b,t);if(!m||n==HISTORY||!make(&b,m,&c))return;b=c;keys[n++]=b.h;',
        'if(n==HISTORY||!parse(&b,t,&c))return;b=c;keys[n++]=b.h;')
    source = once(source, 'fallback=first(&position);atomic_store(&stopped,0);',
                  'Board c;fallback=parse(&position,0,&c);atomic_store(&stopped,0);')
    source = once(source,
        '    for(int i=0;i<WORKERS;i++){workers[i].depth=workers[i].score=0;workers[i].best=0;workers[i].nodes=0;}\n', '')
    source = once(source, '    w->nodes=0;w->depth=0;w->score=0;\n',
                  '    w->nodes=0;w->depth=0;w->score=0;w->best=0;\n')
    # Independent board/search-body receipt reuse applies to exactly these
    # unchanged bytes, not to the broader private think()/parse() interfaces.
    def body(text):
        begin = text.index('static const int steps[16]')
        end = text.index('void think(', begin)
        return text[begin:end].encode()
    if body(source) != body(control.decode()):
        raise ValueError('board/hash/search body changed')
    return source.encode(), {
        'scope': 'one equivalent runtime ownership/query candidate',
        'control_sha256': CONTROL_SHA256,
        'changes': ['nullable-text legal query returns the already-made child',
                    'GO per-worker result reset is owned by think entry'],
        'query_validation': 'unchanged generated pseudo membership, text()/strcmp and make legality',
        'query_order': 'unchanged generator order; null text returns first legal witness',
        'transaction': 'local replay child commits only after complete valid history; no output use after query failure',
        'job_reset': 'each worker resets best/nodes/depth/score before any search, even when already stopped',
        'internal_contract_change': 'direct think() calls now clear preseeded best at entry; production GO already cleared it',
        'board_and_search_body_sha256': hashlib.sha256(body(source)).hexdigest(),
        'unchanged_board_and_search_body': True,
        'old_query_bytes': len(original_query.encode()),
        'new_query_bytes': len(query.encode()),
        'source_bytes_delta': len(source.encode()) - len(control),
        'new_decode_or_search_policy': False,
    }
