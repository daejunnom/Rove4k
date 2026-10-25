"""Separate scalar D submission frontend: bounded in-place tokens and IDs.

Only the DEV0 submission frontend is replaced. All six source inputs and their
complete prior structural proof are admitted and inverted. Required commands,
validated gen/make move replay, decimal bounds, clock arithmetic, publication
barriers and the selected valid-line/terminal contracts are retained.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

KIND="D-in-place-command-frontend-source-v1"
SEARCH_SHA="cd5fa7b2c3c9c1d40664153bbd7f1e3146b03e3de8b237134f6e8321f8e0d8d6"
FILES={"tiny.h","board.c","search.c","runtime.c","start.S","image.ld"}
TOKEN_BEGIN=b"typedef struct{const char *p;unsigned n;} Span;\n"
TOKEN_END=b"\n#if DEV\nstatic char *decimal"
POSITION_BEGIN=b"static void set_position(char *input){\n"
POSITION_END=b"\n\n\nstatic int read_line"
GO_BEGIN=b"static void go(char *s){\n"
GO_END=b"\n#if DEV\nstatic uint64_t perft"
MAIN_OLD=b'''        const char *cursor=line;Span command=scan(&cursor);
        if(word(command,"position")){wait();set_position((char *)cursor);}
        else if(word(command,"go"))go((char *)cursor);
        else if(scan(&cursor).n)continue;
        else if(word(command,"uci")){output("uciok\\n");}
        else if(word(command,"isready")){output("readyok\\n");}
        else if(word(command,"quit"))break;
'''
MAIN_NEW=b'''        char *cursor=line;int command=D_command(scan(&cursor));
        if(command==1){wait();set_position(cursor);}
        else if(command==2)go(cursor);
        else if(*scan(&cursor))continue;
        else if(command==3){output("uciok\\n");}
        else if(command==4){output("readyok\\n");}
        else if(command==5)break;
'''
TOKENS=b'''static char *scan(char **cursor){
    char *s=*cursor;while(*s&&(unsigned char)*s<=32)s++;
    char *first=s;while((unsigned char)*s>32)s++;
    if(*s)*s++=0;*cursor=s;return first;
}
static int word(const char *token,const char *name){
    while(*token&&*token==*name)token++,name++;
    return !*token&&!*name;
}
static int D_command(const char *token){
    const char *name="position\\0go\\0uci\\0isready\\0quit";
    for(int id=1;id<=5;id++){if(word(token,name))return id;while(*name++);}
    return 0;
}
static uint64_t number(const char *token){
    uint64_t n=0;while(*token){unsigned d=(unsigned)(*token++-'0');
        if(d>9||n>((uint64_t)LLONG_MAX-d)/10)return 0;n=n*10+d;}
    return n;
}
static uint64_t amount(char **cursor){
    char *s=*cursor;while(*s&&(unsigned char)*s<=32)s++;
    if(*s&&(unsigned)(*s-'0')>9)return 0;
    return number(scan(cursor));
}
static int parse_apply(const Board *b,const char *token,Board *child){
    unsigned n=0;while(token[n])n++;if(n!=4&&n!=5)return 0;
    unsigned a=(unsigned)(token[0]-'a'),r=(unsigned)(token[1]-'1');
    unsigned c=(unsigned)(token[2]-'a'),s=(unsigned)(token[3]-'1');
    if((a|r|c|s)>7)return 0;unsigned promotion=0;
    if(n==5){for(promotion=2;promotion<6&&"  nbrq"[promotion]!=token[4];promotion++);if(promotion==6)return 0;}
    Move move=MOVE(a+(r<<4),c+(s<<4),promotion),list[MOVES];int count=gen(b,list);
    for(int i=0;i<count;i++)if((list[i]&~8u)==move)return make(b,list[i],child);
    return 0;
}
'''
POSITION=b'''static void set_position(char *input){
    char *cursor=input,*token=scan(&cursor);Board b,c;uint64_t keys[HISTORY];int n=1;
    if(!word(token,"startpos"))return;start(&b);
    token=scan(&cursor);if(*token&&!word(token,"moves"))return;
    keys[0]=b.h;
    while(*(token=scan(&cursor))){
        if(n==HISTORY||!parse_apply(&b,token,&c))return;
        b=c;keys[n++]=b.h;
    }
    position=b;game_length=n;memcpy(game_keys,keys,n*sizeof *keys);
}
'''
GO=b'''static void go(char *s){
    wait();uint64_t clock=0,inc=0,budget=0;int present=0;char *cursor=s;
    for(char *token;*(token=scan(&cursor));){
        if(word(token,"wtime")||word(token,"btime")||word(token,"winc")||word(token,"binc")){
            int side=*token=='w'?1:-1;uint64_t n=amount(&cursor);
            if(side==position.s){if(token[1]=='t'){clock=n;present=1;}else inc=n;}
        }
    }
    if(present){budget=clock/30+(inc>86400000?86400000:inc)*3/4;if(budget>clock/5)budget=clock/5;if(!budget)budget=1;}else budget=1000;
    deadline=now()+(budget>86400000?86400000:budget);
    fallback=first(&position);atomic_store_explicit(&stopped,0,memory_order_relaxed);
    atomic_store_explicit(&pending,WORKERS+1,memory_order_relaxed);atomic_fetch_add_explicit(&epoch,1,memory_order_release);wake(&epoch);
}
'''


def pin(data):return dict(bytes=len(data),sha256=sha256(data).hexdigest())
def inventory(files):return {n:pin(d) for n,d in sorted(files.items())}


def _admit(files,search,valid,arity,owner,publication,proof):
    path=Path(search.__file__)
    if path.parts[-4:]!=("engines","experiments","tiny-d-submission","search_compact.py"):
        raise ValueError("genuine frozen structural search authority required")
    data=path.read_bytes().replace(b"\r\n",b"\n")
    if b"\r" in data or pin(data)["sha256"]!=SEARCH_SHA:raise ValueError("structural search authority differs")
    if set(files)!=FILES or any(not isinstance(d,bytes) or b"\r" in d for d in files.values()):
        raise ValueError("complete normalized six-file D source required")
    if proof["options"]!=["previous-piece","unsigned-history"]:raise ValueError("explicit proved-win structural control required")
    restored=search.restore(files,proof,valid,arity,owner,publication)
    replay,replayed=search.transform(restored,valid,arity,owner,publication,proof["valid"],options=proof["options"])
    if replay!=files or replayed!=proof:raise ValueError("complete structural source/proof replay differs")
    return pin(data)


def _section(data,begin,end):
    if data.count(begin)!=1 or data.count(end)!=1:raise ValueError("unique frontend section required")
    a,b=data.index(begin),data.index(end)
    if b<=a:raise ValueError("frontend section order differs")
    return data[a:b]


def _roles(runtime):
    return (("in-place-token-command-decimal-and-validated-move-parser",_section(runtime,TOKEN_BEGIN,TOKEN_END),TOKENS),
        ("same-atomic-startpos-history-commit",_section(runtime,POSITION_BEGIN,POSITION_END),POSITION),
        ("same-clock-budget-and-search-publication",_section(runtime,GO_BEGIN,GO_END),GO),
        ("exact-command-IDs-and-noop-unknown",MAIN_OLD,MAIN_NEW))


def _project(data,roles):
    rows=[]
    for role,before,after in roles:
        if data.count(before)!=1:raise ValueError("unique frontend role required: "+role)
        rows.append((data.index(before),role,before,after))
    parts,records,gaps,cursor,target=[],[],[],0,0
    for begin,role,before,after in sorted(rows):
        if begin<cursor:raise ValueError("overlapping frontend source edits")
        gap=data[cursor:begin];parts.extend((gap,after));gaps.append(pin(gap));target+=len(gap)
        records.append(dict(role=role,target=target,before=before.decode(),after=after.decode()));target+=len(after);cursor=begin+len(before)
    parts.append(data[cursor:]);gaps.append(pin(data[cursor:]));result=b"".join(parts)
    return result,dict(input=pin(data),output=pin(result),edits=records,gaps=gaps)


def _restore(data,record):
    if pin(data)!=record["output"]:raise ValueError("frontend output differs")
    parts,gaps,cursor=[],[],0
    for row in record["edits"]:
        begin,after=row["target"],row["after"].encode()
        if begin<cursor or data[begin:begin+len(after)]!=after:raise ValueError("frontend inverse edit differs")
        gap=data[cursor:begin];parts.extend((gap,row["before"].encode()));gaps.append(pin(gap));cursor=begin+len(after)
    parts.append(data[cursor:]);gaps.append(pin(data[cursor:]));result=b"".join(parts)
    if pin(result)!=record["input"] or gaps!=record["gaps"]:raise ValueError("frontend protected complement differs")
    return result


def _proof(files,result,edit,authority,search_proof):
    return dict(kind=KIND,input=inventory(files),output=inventory(result),source_edits={"runtime.c":edit},
        options=deepcopy(search_proof["options"]),
        search_authority=authority,search=deepcopy(search_proof),
        command_ids={"position":1,"go":2,"uci":3,"isready":4,"quit":5,"unknown":0},
        scope="DEV0 scalar submission only; canonical DEV runtime remains unchanged",
        contracts=dict(valid_lines="non-NUL payload<=32767; same bounded one-byte reader unchanged",
            tokens="ASCII<=32 whitespace, private-buffer NUL delimiters, all scans remain in the terminated line",
            unknown="exact IDs; unknown/extra-argument handshake commands cannot enter GO",
            replay="same gen and make; full atomic state/history commit after every validated token",
            clocks="same LLONG_MAX decimal acceptance, missing-value lookahead, side/duplicate handling and budget arithmetic",
            ownership="normal position/GO waits, pending and epoch publication, startup and terminal policy unchanged"),
        other_five_files_unchanged=True,independent_semantics_required=True,native_identity_claimed=False,selected=False)


def transform(files,search,valid,arity,owner,publication,search_proof):
    authority=_admit(files,search,valid,arity,owner,publication,search_proof)
    result=dict(files);result["runtime.c"],edit=_project(files["runtime.c"],_roles(files["runtime.c"]))
    proof=_proof(files,result,edit,authority,search_proof)
    if restore(result,proof,search,valid,arity,owner,publication)!=files:raise ValueError("complete frontend inverse differs")
    return result,proof


def restore(files,proof,search,valid,arity,owner,publication):
    if proof.get("kind")!=KIND or inventory(files)!=proof.get("output") or set(proof.get("source_edits",{}))!={"runtime.c"}:
        raise ValueError("unknown or incomplete frontend proof")
    original=dict(files);original["runtime.c"]=_restore(files["runtime.c"],proof["source_edits"]["runtime.c"])
    authority=_admit(original,search,valid,arity,owner,publication,proof["search"])
    expected=dict(original);expected["runtime.c"],edit=_project(original["runtime.c"],_roles(original["runtime.c"]))
    if files!=expected or proof!=_proof(original,expected,edit,authority,proof["search"]):raise ValueError("canonical frontend source/proof replay differs")
    return original
