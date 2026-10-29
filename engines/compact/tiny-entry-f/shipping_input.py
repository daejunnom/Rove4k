"""One fixed, order-independent F shipping text profile, after EP semantics.

Only literal function regions have role projection. No AST/name allocation or
generic preprocessor is used; the admitted old input bodies have #if DEV only.
"""
import hashlib
import re

READABLE = 'f9ca456f55ef34c83af9e2e605026415126c9ba0f6eedf10db479a6467c0b357'
SHIPPING = '3549063cbdca22c83536e0879b5e7baff8c7cbef3b5911f4152850732c86300c'
COMMON = {'Board':'za','position':'ql','game_length':'qh','game_keys':'qg',
          'workers':'qr','table':'qq','stopped':'qp','deadline':'qc','mutex':'qj',
          'command':'qb','epoch':'qd','pending':'qk','quitting':'qm','fallback':'qe',
          'wait':'ay','clear':'az','start':'ae','parse':'ar','go':'as','number':'aw',
          'work':'ax','set_position':'av','read_line':'au','now':'ai','WORKERS':'2','TT_BITS':'18'}
SCOPES = {
 'set_position':{'keys':'a','save':'f','moves':'d','token':'d'},
 'number':{'end':'e'},
 'read_line':{'bad':'a'},
 'go':{'clock':'a','inc':'d','budget':'f','present':'g','save':'i','side':'j'},
 'main':{'threads':'a','created':'d','status':'f','line':'g','save':'j','token':'l','c':'n','id':'a'},
}
# The second identical old GO branch used a distinct existing physical alias.
OLD_GO_SECOND = ('else if(!strcmp(t,"winc")||!strcmp(t,"binc")){int j=',
                 'else if(!strcmp(t,"winc")||!strcmp(t,"binc")){int l=')

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

# Ordinary standalone normal-stage adaptation. The literal bodies, role maps,
# lexer/projection, old physical alias corrections and patch proof above remain
# unchanged. No experiment or receipt is a runtime/build input of this helper.
PROFILE_READABLE_BYTES = 28587
PROFILE_READABLE_SHA256 = 'fe1309f37fbc204844c8f2854d79bb891b9c996af214f28086ce64373701d530'
PROFILE_SHIPPING_BYTES = 9728
PROFILE_SHIPPING_SHA256 = '845f731a0f1fabd62bae629ad191aadd39525d0db7d59628224e315f09c0519d'
POLICY = 'NUL-free bounded text; exact command token; GO order independent; malformed extras differ'


def _prepare(readable):
    """Collect the one fixed five-region plan from the exact EP readable."""
    need(len(readable)==25720 and sha(readable)==READABLE,'semantic readable pin differs')
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
            projected=projected[:start]+projected[start:end].replace(b'j',b'l')+projected[end:]
        if name=='main':
            source=b'int f=au(g);if(f<0)break;if(!f)continue;'
            target=b'int j=au(g);if(j<0)break;if(!j)continue;'
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


def _readable_pair(readable,changes,bindings):
    """Bind f9ca -> fe130 with exact inverse/complement, without a shipping input."""
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
    """Produce the exact corrected dual readable before DEV specialization.

    This checks the readable pair and fixed projected role plan only. There is
    no actual shipping input, so concrete old shipping region occurrence checks
    belong solely to transform_source. Old DEV output/native identity remains
    unverified until a separately authorized actual generation and comparison.
    """
    changes,_,bindings=_prepare(readable)
    return _readable_pair(readable,changes,bindings)


def transform_source(source, *, readable):
    """Apply the same five roles after the existing EP shipping semantic stage."""
    need(len(source)==9925 and sha(source)==SHIPPING,'postsemantic shipping pin differs')
    canonical_changes,shipping_changes,bindings=_prepare(readable)
    canonical,readable_metadata=_readable_pair(readable,canonical_changes,bindings)
    for binding,(old,_) in zip(bindings,shipping_changes):
        need(source.count(old)==1,
             'readable/shipping fixed role relation differs: '+binding['function'])
    candidate,proof=patch(source,shipping_changes)
    need(len(candidate)==PROFILE_SHIPPING_BYTES and sha(candidate)==PROFILE_SHIPPING_SHA256,
         'profile shipping output pin differs')
    return candidate,{'stage':'shipping-after-EP-semantics',
                      'input_bytes':len(source),'input_sha256':SHIPPING,
                      'output_bytes':len(candidate),'output_sha256':PROFILE_SHIPPING_SHA256,
                      'semantic_readable_sha256':READABLE,
                      'profile_readable_sha256':sha(canonical),
                      'fixed_function_roles':bindings,'shipping':proof,
                      'readable_relation':readable_metadata,
                      'canonical_pair_checked':True,'shipping_relation_checked':True,
                      'candidate_count':1,'C_AST':False,'compiler_preprocessing':False,
                      'DEV_identity_verified':False,'policy':POLICY}
