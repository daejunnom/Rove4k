"""The fixed A shipping text profile and its exact readable/shipping role pairs.

Only literal function regions have role projection. No AST/name allocation or
generic preprocessor is used; the admitted old input bodies have #if DEV only.
"""
import hashlib
import re

READABLE = '71f9ff6ce1b7f555ad85c3bf49766381c0627315da94acf0c49eeee7bee4a734'
SHIPPING = 'a3414baa5034a62067f74f7f8fff9a1578827f37e6ca59b0db8e5bc1968df312'
COMMON = {'Board':'E','position':'ql','game_length':'qh','game_keys':'qg',
          'workers':'qr','table':'qq','stopped':'qp','deadline':'qc','mutex':'qj',
          'command':'qb','epoch':'qd','pending':'qk','quitting':'qm','fallback':'qe',
          'wait':'aW','clear':'aX','start':'am','parse':'aN','go':'aO','number':'aS',
          'work':'aV','set_position':'aU','read_line':'aQ','now':'as','WORKERS':'2','TT_BITS':'18'}
SCOPES = {
 'set_position':{'keys':'a','save':'d','moves':'B','token':'B'},
 'number':{'end':'e'},
 'read_line':{'bad':'a'},
 'go':{'clock':'a','inc':'d','budget':'S','present':'f','save':'g','side':'i'},
 'main':{'threads':'a','created':'V','status':'d','line':'R','save':'f','token':'g','c':'n'},
}
# The second identical old GO branch used a distinct existing physical alias.
OLD_GO_SECOND = ('else if(!strcmp(t,"winc")||!strcmp(t,"binc")){int i=',
                 'else if(!strcmp(t,"winc")||!strcmp(t,"binc")){int j=')

POSITION = '''static void set_position(char *s){
    Board b,c;uint64_t keys[HISTORY];int n=1;
    char *save,*token=strtok_r(s," \\t\\r\\n",&save);
    if(!token||strcmp(token,"startpos"))return;
    start(&b);keys[0]=b.h;
    token=strtok_r(NULL," \\t\\r\\n",&save);
    if(token){
        if(strcmp(token,"moves"))return;
        while((token=strtok_r(NULL," \\t\\r\\n",&save))){
            if(n==HISTORY||!parse(&b,token,&c))return;b=c;keys[n++]=b.h;
        }
    }
    position=b;game_length=n;memcpy(game_keys,keys,n*sizeof *keys);
}
'''
NUMBER = '''static uint64_t number(const char *s){
    char *end;if(!s||(unsigned)(*s-'0')>9)return 0;
    unsigned long long n=strtoull(s,&end,10);
    return *end||n>LLONG_MAX?0:n;
}
'''
GO = '''static void go(char *s){
    wait();uint64_t clock=0,inc=0,budget=0;int present=0;char *save;
    for(char *t=strtok_r(s," \\t\\r\\n",&save);t;t=strtok_r(NULL," \\t\\r\\n",&save)){
        if((*t=='w'||*t=='b')&&(!strcmp(t+1,"time")||!strcmp(t+1,"inc"))){
            uint64_t n=number(strtok_r(NULL," \\t\\r\\n",&save));
            if((*t=='w')==(position.s>0)){
                if(t[1]=='t'){clock=n;present=1;}else inc=n;
            }
        }
    }
    if(present){budget=clock/30+(inc>86400000?86400000:inc)*3/4;if(budget>clock/5)budget=clock/5;if(!budget)budget=1;}
    else budget=1000;
    deadline=now()+(budget>86400000?86400000:budget);
    Board c;fallback=parse(&position,0,&c);atomic_store(&stopped,0);
    pthread_mutex_lock(&mutex);pending=WORKERS;epoch++;pthread_cond_broadcast(&command);pthread_mutex_unlock(&mutex);
}
'''
LOOP = '''    while(fgets(line,sizeof line,stdin)){
        if(!strchr(line,'\\n')){
            int c=getchar();
            if(c!=EOF&&c!='\\n'){
                do{c=getchar();}while(c!=EOF&&c!='\\n');continue;
            }
        }
        char *save,*token=strtok_r(line," \\t\\r\\n",&save);
        if(!token)continue;
        if(!strcmp(token,"uci")){puts("uciok");fflush(stdout);}
        else if(!strcmp(token,"isready")){puts("readyok");fflush(stdout);}
        else if(!strcmp(token,"quit"))break;
        else if(!strcmp(token,"position")){wait();set_position(save);}
        else if(!strcmp(token,"go"))go(save);
    }
'''

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def need(condition, message):
    if not condition:
        raise ValueError(message)

def active(body):
    """Select only the pinned DEV/else literal lines, not arbitrary C macros."""
    output, stack, enabled = [], [], True
    for line in body.splitlines(keepends=True):
        directive=line.strip()
        if directive == '#if DEV':
            stack.append(enabled); enabled=False
        elif directive == '#else':
            need(bool(stack),'unpaired else');enabled=stack[-1]
        elif directive == '#endif':
            need(bool(stack),'unpaired endif');enabled=stack.pop()
        else:
            need(not directive.startswith('#'),'unadmitted function directive')
            if enabled:output.append(line)
    need(not stack,'unterminated DEV branch')
    return ''.join(output)

def project(body, scope):
    """Project only exact owned snippets; protect every C string/char literal."""
    mapping = dict(COMMON);mapping.update(SCOPES[scope])
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[A-Za-z_]\w*|[0-9]+|\s+|.',body)
    tokens = [mapping.get(t,t) if re.fullmatch(r'[A-Za-z_]\w*',t) else t for t in tokens if not t.isspace()]
    result=[]
    for token in tokens:
        if result and (result[-1][-1].isalnum() or result[-1][-1]=='_') and (token[0].isalnum() or token[0]=='_'):
            result.append(' ')
        result.append(token)
    return ''.join(result).encode()

def patch(data, changes):
    spans=[]
    for old,new in changes:
        need(old and data.count(old)==1,'literal old body count differs')
        spans.append((data.index(old),old,new))
    spans.sort();result=[];old_gaps=[];cursor=0;records=[];offset=0
    for pos,old,new in spans:
        need(pos>=cursor,'overlapping regions')
        gap=data[cursor:pos];result.extend((gap,new));old_gaps.append(gap)
        offset+=len(gap);records.append((offset,old,new));offset+=len(new);cursor=pos+len(old)
    result.append(data[cursor:]);old_gaps.append(data[cursor:]);candidate=b''.join(result)
    inverse=[];new_gaps=[];cursor=0
    for pos,old,new in records:
        need(candidate[pos:pos+len(new)]==new,'new region differs')
        gap=candidate[cursor:pos];new_gaps.append(gap);inverse.extend((gap,old));cursor=pos+len(new)
    new_gaps.append(candidate[cursor:]);inverse.append(candidate[cursor:])
    need(new_gaps==old_gaps and b''.join(inverse)==data,'inverse/complement differs')
    return candidate,{'exact_inverse':True,'complement_exact':True,
                      'complement_bytes':sum(map(len,old_gaps)),'complement_sha256':sha(b''.join(old_gaps)),
                      'regions':[{'offset':p,'old_bytes':len(o),'new_bytes':len(n),
                                  'old_sha256':sha(o),'new_sha256':sha(n)} for p,o,n in spans]}

def _prepare(readable):
    need(len(readable)==24820 and sha(readable)==READABLE,'A readable pin differs')
    text=readable.decode()
    markers=('static void set_position(char *s){','static uint64_t number(const char *s){',
             'static int read_line(char *s){','static void go(char *s){','\n#if DEV\nstatic uint64_t perft(')
    positions=[text.index(m) for m in markers]
    need(positions==sorted(positions),'function order differs')
    old={name:text[positions[i]:positions[i+1]] for i,name in enumerate(('set_position','number','read_line','go'))}
    old['main']=text[text.index('int main(void){'):]
    prefix=old['main'].split('    for(;;){\n')[0]
    suffix=old['main'][old['main'].index('    wait();\nshutdown:'):]
    new={'set_position':POSITION,'number':NUMBER,'read_line':'','go':GO,'main':prefix+LOOP+suffix}
    canonical_changes=[];shipping_changes=[];bindings=[]
    for name in ('set_position','number','read_line','go','main'):
        old_body=old[name]
        projected=project(active(old_body),name)
        if name=='go':
            a,b=OLD_GO_SECOND
            need(projected.count(a.encode())==1,'second GO declaration shape differs')
            start=projected.index(a.encode());end=projected.index(b'}',start)+1
            chunk=projected[start:end]
            need(chunk.count(b'int i=')==1 and chunk.count(b'if(i==ql.s)')==1,
                 'old second GO local role differs')
            chunk=chunk.replace(b'int i=',b'int j=').replace(b'if(i==ql.s)',b'if(j==ql.s)')
            projected=projected[:start]+chunk+projected[end:]
        if name=='main':
            source=b'int d=aQ(R);if(d<0)break;if(!d)continue;'
            target=b'int f=aQ(R);if(f<0)break;if(!f)continue;'
            need(projected.count(source)==1,'old main input local shape differs')
            projected=projected.replace(source,target)
        replacement=project(new[name],name) if new[name] else b''
        # Keep exact old DEV bodies; do not claim an unperformed DEV compilation.
        old_lines=old_body if old_body.endswith('\n') else old_body+'\n'
        new_lines=new[name] if new[name].endswith('\n') else new[name]+'\n'
        dual=('#if DEV\n'+old_lines+'#else\n'+new_lines+'#endif\n')
        canonical_changes.append((old_body.encode(),dual.encode()))
        shipping_changes.append((projected,replacement))
        bindings.append({'function':name,'old_projected_sha256':sha(projected),
                         'new_projected_sha256':sha(replacement),'old_bytes':len(projected),'new_bytes':len(replacement)})
    return canonical_changes,shipping_changes,bindings


# Standalone normal-stage adaptation. The fixed bodies, projection roles,
# old physical aliases and patch proof above require no experiment inputs.
PROFILE_READABLE_BYTES = 27687
PROFILE_READABLE_SHA256 = '63821a63cbf6507393e0617da9f611b778ada46c9a89b49fdefc8996bb461e2c'
PROFILE_SHIPPING_BYTES = 9713
PROFILE_SHIPPING_SHA256 = '1f4097d43c5f6e84d7cbd17906100354da25be205d44ca08fbf52732e63b624c'
POLICY = 'NUL-free bounded text; exact command token; GO order independent; malformed extras differ'


def _readable_pair(readable,changes,bindings):
    canonical,proof=patch(readable,changes)
    need(len(canonical)==PROFILE_READABLE_BYTES and sha(canonical)==PROFILE_READABLE_SHA256,
         'profile readable output pin differs')
    return canonical,{'stage':'readable-before-DEV-specialization',
                      'input_bytes':len(readable),'input_sha256':READABLE,
                      'output_bytes':len(canonical),'output_sha256':PROFILE_READABLE_SHA256,
                      'fixed_function_roles':bindings,'canonical':proof,
                      'canonical_pair_checked':True,'shipping_relation_checked':False,
                      'candidate_count':1,'C_AST':False,'compiler_preprocessing':False,
                      'DEV_identity_verified':False,'policy':POLICY}


def transform_readable(readable):
    """Select the exact old bodies in DEV using corrected dual directives.

    The readable pair is checked without inventing an unavailable shipping
    occurrence check. Diagnostic identity is proved only by actual generation.
    """
    changes,_,bindings=_prepare(readable)
    return _readable_pair(readable,changes,bindings)


def transform_source(source, *, readable):
    """Apply only the fixed five input roles after the unchanged A scope stage."""
    need(len(source)==9910 and sha(source)==SHIPPING,'postscope shipping pin differs')
    canonical_changes,shipping_changes,bindings=_prepare(readable)
    canonical,readable_metadata=_readable_pair(readable,canonical_changes,bindings)
    for binding,(old,_) in zip(bindings,shipping_changes):
        need(source.count(old)==1,
             'readable/shipping fixed role relation differs: '+binding['function'])
    candidate,proof=patch(source,shipping_changes)
    need(len(candidate)==PROFILE_SHIPPING_BYTES and sha(candidate)==PROFILE_SHIPPING_SHA256,
         'profile shipping output pin differs')
    return candidate,{'stage':'shipping-after-scope',
                      'input_bytes':len(source),'input_sha256':SHIPPING,
                      'output_bytes':len(candidate),'output_sha256':PROFILE_SHIPPING_SHA256,
                      'canonical_readable_sha256':READABLE,
                      'profile_readable_sha256':sha(canonical),
                      'fixed_function_roles':bindings,'shipping':proof,
                      'readable_relation':readable_metadata,
                      'canonical_pair_checked':True,'shipping_relation_checked':True,
                      'candidate_count':1,'C_AST':False,'compiler_preprocessing':False,
                      'DEV_identity_verified':False,'policy':POLICY}
