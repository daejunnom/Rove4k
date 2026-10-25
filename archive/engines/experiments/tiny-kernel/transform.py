"""One guarded direct-kernel architecture; no flag/spelling/codec search."""
from pathlib import Path
import hashlib

HERE = Path(__file__).resolve().parent
CONTROL_SHA256 = '109fa749bc2a137fc1384a9afa429d3734249df908f057a58c1fe105f0c43504'


def once(source, before, after):
    if source.count(before) != 1:
        raise ValueError('frozen control changed: ' + before[:70])
    return source.replace(before, after)


def transform(readable):
    if hashlib.sha256(readable).hexdigest() != CONTROL_SHA256:
        raise ValueError('exact qualified readable A source required')
    source = readable.decode()
    begin = source.index('static int walk(const Board *,Move *,int,int);')
    end = source.index('\nint dead(', begin)
    source = source[:begin] + (
        'enum KernelMode {K_SEARCH,K_ATTACK,K_FIRST,K_MATCH,K_COLLECT};\n'
        'static int kernel(Worker *,const Board *,int,int,int,int,int,Move *,enum KernelMode,Move,Board *);\n'
        'int attacked(const Board *p,int sq,int side){return kernel(0,p,0,0,0,0,0,0,K_ATTACK,(Move)(sq|(side<0?128:0)),0);}\n'
    ) + source[end:]
    begin = source.index('/* Internal contract: p came from start/FEN/a prior successful make, and m')
    end = source.index('\nvoid start(', begin)
    source = source[:begin] + source[end:]
    begin = source.index('static int search(')
    end = source.index('\nvoid think(', begin)
    emitter = (HERE / 'emit.c.in').read_text().replace('\r\n', '\n').strip()
    macro = '#define K_EMIT() ' + ' \\\n'.join(emitter.splitlines()) + '\n'
    kernel = (HERE / 'kernel.c.in').read_text().replace('\r\n', '\n')
    if kernel.count('/* EMITTER */') != 1:
        raise ValueError('one direct emitter required')
    source = source[:begin] + kernel.replace('/* EMITTER */', macro) + source[end:]
    source = once(source, 'int score=search(w,p,depth,-MATE,MATE,0,6,&best);',
                  'int score=kernel(w,p,depth,-MATE,MATE,0,6,&best,K_SEARCH,0,0);')
    begin = source.index('static Move first(')
    end = source.index('\nstatic void result(', begin)
    source = source[:begin] + '''static Move first(const Board *b){return kernel(0,b,0,0,0,0,0,0,K_FIRST,0,0);}
static Move parse(const Board *b,const char *s,Board *out){
    size_t n=strlen(s);if(n!=4&&n!=5)return 0;
    int f=s[0]-'a',r=s[1]-'1',t=s[2]-'a',u=s[3]-'1',prom=0;
    if((unsigned)f>7||(unsigned)r>7||(unsigned)t>7||(unsigned)u>7)return 0;
    if(n==5){const char *letters="nbrq",*x=strchr(letters,s[4]);if(!x)return 0;prom=2+(int)(x-letters);}
    return kernel(0,b,0,0,0,0,0,0,K_MATCH,MOVE(f+r*16,t+u*16,prom),out);
}
''' + source[end:]
    source = once(source, 'Move m=parse(&b,t);if(!m||n==HISTORY||!make(&b,m,&c))return;',
                  'if(n==HISTORY||!parse(&b,t,&c))return;')
    if 'Move moves[MOVES],bestmove' in source or 'static int search(' in source or 'static int walk(' in source:
        raise ValueError('obsolete shipping generator/search path remains')
    return source.encode(), {
        'architecture': 'one typed monolithic generation/copy-transition/search kernel; direct macro body, no callbacks or iterator context',
        'search_policy': 'TT, tactical, snapshot quiet rank>=32, remaining quiet; file-order xor worker_id&7 within stages',
        'rank': 'history+continuation+worker jitter<=16, frozen before any descendants',
        'rank_threshold': 32, 'whole_board_generation_sweeps_per_search_node_max': 5,
        'shipping_move_array': False, 'per_selected_move_full_rescan': False, 'seen_bitmap': False,
        'child_ownership': 'immutable parent; copied local child; one key push/pop before every cancellation return',
        'dev_collection': 'legal-only compatibility list; DEV make uses typed match, no shipping adapters',
        'control_sha256': CONTROL_SHA256,
        'source_recipe_sha256': {name: hashlib.sha256((HERE/name).read_bytes()).hexdigest()
                                 for name in ('transform.py', 'kernel.c.in', 'emit.c.in')},
    }
