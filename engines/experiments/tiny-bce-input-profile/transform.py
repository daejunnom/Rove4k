"""One source-only B/C/E shipping input-profile proposal.

Pure bytes in/out. This is not a normal build input or a cost/runtime producer.
Only the exact admitted function regions have literal role projection; there
is no C AST, compiler preprocessing, generic renaming or alias allocation.
"""
import hashlib
import re

DOMAINS = {
    'B': (28953, '1f879828346dfbc6023f6abfbbf1e1d2062e8e2dc0e9919aade254ba7a0a97f6',
          12148, '6c9081115f5caf209cacc502e19035247a3178aef86c4912fb3a923a651904ce'),
    'C': (26692, '15999279c5bd4690db7129bda032c6b5962acbd814236719cda40755ae31794b',
          11086, '90a566c5e814cf87dd38f92f40ce8fe7115c4d4d07f75d9ff0981ffaae1fbc28'),
    'E': (28001, '0a7fe69022051e1893ffbd52ade7a2fbb3f342fe20b581bb786d6997b46fb712',
          11703, 'd3368da33e992e3abdc3bbcab8917edaff8ef751fe7948d11364251a5f6f9ff8'),
}
OUTPUTS = {
    'B': (32312, '206df7aae4b10d7c743cd4f9ab35c404373a0af7847d4faf054ce657ef46a4cc',
          11829, '11a32cc6c48ad16856e7968c5ba91456257c1b249590f0aa71a371d2fd276a93'),
    'C': (29558, 'a24ff07fee3a7e143bf78cdbf03a6fccf668849085ae8368495c5784c4b3004f',
          10886, 'd6265b2cabf0dfbe96744acc9cbfcccfe29c0a292901b326ee2f1f061b93aeca'),
    'E': (31360, '1720e6cfc1ebf548ccb5a3d53199a4937cf6644fb48e6d5b22db1ede57ab1273',
          11378, '761e301cdad7b1dcf15da6458959612606e93be8b863ba2072e2ba509cb857f9'),
}
FUNCTIONS = {
    'B': {'text':'T','parse':'H','wait':'U','clear':'B','set_position':'R',
          'number':'G','read_line':'N','go':'E'},
    'C': {'text':'S','parse':'G','wait':'V','clear':'y','set_position':'Q',
          'number':'F','read_line':'M','go':'D'},
    'E': {'text':'P','parse':'E','wait':'U','clear':'y','set_position':'N',
          'number':'D','read_line':'I','go':'B'},
}
B_GLOBALS = {'position':'ql','game_length':'qh','game_keys':'qg','workers':'qr',
             'table':'qq','stopped':'qp','deadline':'qc','mutex':'qj',
             'command':'qb','finished':'qf','epoch':'qd','pending':'qk',
             'ready':'qn','quitting':'qm','fallback':'qe'}
COMMON = {'Board':'za','Worker':'zd','WORKERS':'2','TT_BITS':'18',
          'depth':'zB','score':'yl','best':'zi','nodes':'z4'}
SCOPES = {
    'parse': {'list':'a','name':'d'},
    'set_position': {'keys':'a','moves':'d','token':'d','save':'f'},
    'number': {'end':'e'},
    'read_line': {'bad':'a'},
    'main': {'threads':'a','created':'d','status':'f','line':'j',
             'save':'m','token':'p','c':'n'},
}
PARSE = '''static Move parse(const Board *b,const char *s,Board *c){
    Move list[MOVES];char name[6];int n=gen(b,list);
    for(int i=0;i<n;i++){
        if(s){text(list[i],name);if(strcmp(s,name))continue;}
        if(make(b,list[i],c))return list[i];
    }return 0;
}
'''
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
GO_PREFIX = '''static void go(char *s){
    wait();uint64_t clock=0,inc=0,budget=0;int present=0;char *save;
    for(char *t=strtok_r(s," \\t\\r\\n",&save);t;t=strtok_r(NULL," \\t\\r\\n",&save)){
        if((*t=='w'||*t=='b')&&(!strcmp(t+1,"time")||!strcmp(t+1,"inc"))){
            uint64_t n=number(strtok_r(NULL," \\t\\r\\n",&save));
            if((*t=='w')==(position.s>0)){
                if(t[1]=='t'){clock=n;present=1;}else inc=n;
            }
        }
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
POLICY = ('NUL-free; <=32767 bytes before LF/final EOF, CR-inclusive; '
          'exact first command token, space/tab/CR/LF delimiters; '
          'whole ASCII unsigned decimal <=LLONG_MAX; exact four clock keys, '
          'last own-side value wins, unknown tokens have no arity')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def need(condition, message):
    if not condition:
        raise ValueError(message)


def _pin(data, size, digest, label):
    need(type(data) is bytes and len(data)==size and sha(data)==digest,
         label+' exact bytes/SHA-256 differs')


def active(body, development=False):
    """Select only exact admitted #if DEV/#else/#endif literal lines."""
    output, stack, enabled = [], [], True
    for line in body.splitlines(keepends=True):
        directive=line.strip()
        if directive=='#if DEV':
            stack.append(enabled);enabled=enabled and development
        elif directive=='#else':
            need(bool(stack),'unpaired else');enabled=stack[-1] and not development
        elif directive=='#endif':
            need(bool(stack),'unpaired endif');enabled=stack.pop()
        else:
            need(not directive.startswith('#'),'unadmitted function directive')
            if enabled:output.append(line)
    need(not stack,'unterminated DEV branch')
    return ''.join(output)


def project(body, family, scope):
    """Project these exact snippets only; keep string/character tokens opaque."""
    mapping=dict(COMMON);mapping.update(FUNCTIONS[family])
    if family=='B':mapping.update(B_GLOBALS)
    mapping.update(SCOPES.get(scope,{}))
    if scope=='go':
        mapping.update(clock='a',inc='d',budget='f',
                       present='i' if family=='C' else 'j',
                       save='j' if family=='C' else 'm',
                       side='m' if family=='C' else 'p')
    tokens=re.findall(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[A-Za-z_]\w*|[0-9]+|\s+|.',body)
    need(''.join(tokens)==body,'token projection does not cover bytes')
    tokens=[mapping.get(t,t) if re.fullmatch(r'[A-Za-z_]\w*',t) else t
            for t in tokens if not t.isspace()]
    output=[]
    for token in tokens:
        if output and (output[-1][-1].isalnum() or output[-1][-1]=='_') and (token[0].isalnum() or token[0]=='_'):
            output.append(' ')
        output.append(token)
    return ''.join(output).encode()


def patch(data, changes):
    """Splice unique fixed regions and prove byte inverse and every gap."""
    spans=[]
    for name,old,new in changes:
        need(old and data.count(old)==1,'literal old body count differs: '+name)
        spans.append((data.index(old),name,old,new))
    spans.sort();result=[];gaps=[];cursor=0;records=[];offset=0
    for pos,name,old,new in spans:
        need(pos>=cursor,'overlapping regions')
        gap=data[cursor:pos];result.extend((gap,new));gaps.append(gap)
        offset+=len(gap);records.append((offset,name,old,new))
        offset+=len(new);cursor=pos+len(old)
    result.append(data[cursor:]);gaps.append(data[cursor:]);candidate=b''.join(result)
    inverse=[];new_gaps=[];cursor=0
    for pos,name,old,new in records:
        need(candidate[pos:pos+len(new)]==new,'new region differs: '+name)
        gap=candidate[cursor:pos];new_gaps.append(gap);inverse.extend((gap,old));cursor=pos+len(new)
    new_gaps.append(candidate[cursor:]);inverse.append(candidate[cursor:])
    need(new_gaps==gaps and b''.join(inverse)==data,'inverse/complement differs')
    return candidate,{'exact_inverse':True,'complement_exact':True,
                      'complement_bytes':sum(map(len,gaps)),
                      'complement_sha256':sha(b''.join(gaps)),
                      'regions':[{'name':name,'offset':pos,'old_bytes':len(old),
                                  'new_bytes':len(new),'old_sha256':sha(old),
                                  'new_sha256':sha(new)} for pos,name,old,new in spans]}


def _prepare(readable, family):
    need(family in DOMAINS,'unadmitted family')
    rb,rh,_,_=DOMAINS[family];_pin(readable,rb,rh,family+' canonical')
    text=readable.decode('ascii');old={}
    if family!='C':
        begin=text.index('static Move first(const Board *b){')
        end=text.index('static void result(void){',begin)
        old['parse']=text[begin:end]
    else:
        begin=text.index('static Move parse(const Board *b,const char *s,Board *c){')
        end=text.index('static void result(void){',begin)
        need(text[begin:end]==PARSE,'C existing nullable parse differs')
    markers=('static void set_position(char *s){','static uint64_t number(const char *s){',
             'static int read_line(char *s){','static void go(char *s){','\n#if DEV\nstatic uint64_t perft(')
    positions=[text.index(m) for m in markers]
    # Own the existing LF after GO's closing brace. It is the separator before
    # the following DEV directive, not an extra byte added to the old body.
    positions[-1]+=1
    need(positions==sorted(positions),'function order differs')
    old.update({name:text[positions[i]:positions[i+1]]
                for i,name in enumerate(('set_position','number','read_line','go'))})
    old['main']=text[text.index('int main(void){'):]
    old_go=active(old['go']);budget=old_go[old_go.index('    if(present){'):]
    fallback='    fallback=first(&position);atomic_store(&stopped,0);'
    if family=='C':fallback='    Board c;fallback=parse(&position,0,&c);atomic_store(&stopped,0);'
    need(budget.count(fallback)==1,'GO fallback role differs')
    # Keep budget, exact family reset and publication; change only fallback call.
    new_go=GO_PREFIX+budget.replace(fallback,'    Board c;fallback=parse(&position,0,&c);atomic_store(&stopped,0);')
    prefix=old['main'].split('    for(;;){\n')[0]
    suffix=old['main'][old['main'].index('    wait();\nshutdown:'):]
    new={'parse':PARSE,'set_position':POSITION,'number':NUMBER,'read_line':'',
         'go':new_go,'main':prefix+LOOP+suffix}
    readable_changes=[];shipping_changes=[];bindings=[]
    for name,old_body in old.items():
        projected=project(active(old_body),family,name)
        if name=='go':
            first='m' if family=='C' else 'p';second='p' if family=='C' else 'q'
            a=('else if(!strcmp(t,"winc")||!strcmp(t,"binc")){int '+first+'=').encode()
            need(projected.count(a)==1,'second old clock branch differs')
            start=projected.index(a);end=projected.index(b'}',start)+1
            chunk=projected[start:end]
            chunk=chunk.replace(('int '+first+'=').encode(),('int '+second+'=').encode())
            chunk=chunk.replace(('if('+first+'==').encode(),('if('+second+'==').encode())
            projected=projected[:start]+chunk+projected[end:]
        if name=='main':
            a=('int f='+FUNCTIONS[family]['read_line']+'(j);if(f<0)break;if(!f)continue;').encode()
            b=('int m='+FUNCTIONS[family]['read_line']+'(j);if(m<0)break;if(!m)continue;').encode()
            need(projected.count(a)==1,'old main input status role differs')
            projected=projected.replace(a,b)
        replacement=project(new[name],family,name) if new[name] else b''
        old_lines=old_body if old_body.endswith('\n') else old_body+'\n'
        new_lines=new[name] if new[name].endswith('\n') else new[name]+'\n'
        dual='#if DEV\n'+old_lines+'#else\n'+new_lines+'#endif\n'
        need(active(dual,True)==active(old_body,True),'old DEV branch differs: '+name)
        need(active(dual,False)==active(new_lines,False),'shipping literal branch differs: '+name)
        readable_changes.append((name,old_body.encode(),dual.encode()))
        shipping_changes.append((name,projected,replacement))
        bindings.append({'function':name,'old_projected_bytes':len(projected),
                         'new_projected_bytes':len(replacement),
                         'old_projected_sha256':sha(projected),'new_projected_sha256':sha(replacement)})
    return readable_changes,shipping_changes,bindings


def transform_readable(readable, *, family):
    changes,_,bindings=_prepare(readable,family)
    result,proof=patch(readable,changes)
    rb,rh,_,_=OUTPUTS[family];_pin(result,rb,rh,family+' dual readable proposal')
    return result,{'family':family,'stage':'literal dual readable proposal',
                   'input_sha256':sha(readable),'output_bytes':len(result),'output_sha256':sha(result),
                   'fixed_function_roles':bindings,'proof':proof,
                   'old_DEV_body_selection_exact':True,'actual_DEV_tuple_verified':False,
                   'policy':POLICY,'C_AST':False,'compiler_preprocessing':False}


def transform_source(source, *, readable, family):
    _,_,sb,sh=DOMAINS[family];_pin(source,sb,sh,family+' postcurrent-stage shipping')
    readable_changes,changes,bindings=_prepare(readable,family)
    dual,readable_proof=patch(readable,readable_changes)
    rb,rh,sb,sh=OUTPUTS[family];_pin(dual,rb,rh,family+' dual readable proposal')
    if family=='C':
        existing=project(PARSE,family,'parse')
        need(source.count(existing)==1,'existing C nullable parse shipping relation differs')
    result,proof=patch(source,changes)
    _pin(result,sb,sh,family+' proposed shipping profile')
    return result,{'family':family,'stage':'shipping after existing final stage',
                   'input_bytes':len(source),'input_sha256':sha(source),
                   'output_bytes':len(result),'output_sha256':sha(result),
                   'source_saved_bytes':len(source)-len(result),
                   'readable_sha256':sha(readable),'dual_readable_bytes':len(dual),
                   'dual_readable_sha256':sha(dual),'fixed_function_roles':bindings,
                   'readable_proof':readable_proof,'shipping_proof':proof,
                   'C_existing_nullable_parse_unchanged':family=='C',
                   'old_DEV_body_selection_exact':True,'actual_DEV_tuple_verified':False,
                   'policy':POLICY,'C_AST':False,'compiler_preprocessing':False,
                   'native_compiles':0,'codec_calls':0,'engine_runs':0}
