"""Finite D structural source candidates, separate from selected producers.

The complete valid-input source chain is replayed before any edit. Candidate
semantics require the independent actual-search probe; this module alone is
neither native equivalence, runtime qualification nor a selection decision.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

KIND = "D-structural-search-source-v1"
VALID_SHA = "2aa36a2b0e8ba9b8c90739223b36a77fddf5fc9f718d36a8a92711f8fc75cdb0"
OPTIONS = ("union-order", "previous-piece", "constant-start", "unsigned-history")
FILES = {"tiny.h","board.c","search.c","runtime.c","start.S","image.ld"}


def pin(data):
    return dict(bytes=len(data),sha256=sha256(data).hexdigest())


def inventory(files):
    return {n:pin(d) for n,d in sorted(files.items())}


def _admit(files,valid,arity,owner,publication,proof):
    path=Path(valid.__file__)
    if path.parts[-4:] != ("engines","experiments","tiny-d-submission","valid_input.py"):
        raise ValueError("genuine frozen D valid-input authority required")
    raw=path.read_bytes().replace(b"\r\n",b"\n")
    if b"\r" in raw or pin(raw)["sha256"]!=VALID_SHA:
        raise ValueError("D valid-input authority differs")
    if set(files)!=FILES or any(not isinstance(d,bytes) or b"\r" in d for d in files.values()):
        raise ValueError("complete normalized six-file D source required")
    restored=valid.restore(files,proof,arity,owner,publication)
    again,again_proof=valid.transform(restored,arity,owner,publication,proof["arity"],mode=proof["mode"])
    if again!=files or again_proof!=proof or proof["mode"]!="one-byte-valid":
        raise ValueError("complete canonical one-byte source proof required")
    return pin(raw)


def _mix(value):
    mask=(1<<64)-1
    value=(value+0x9e3779b97f4a7c15)&mask
    value=((value^(value>>30))*0xbf58476d1ce4e5b9)&mask
    value=((value^(value>>27))*0x94d049bb133111eb)&mask
    return value^(value>>31)


def start_fields():
    """Independent field derivation; no compiled image or original start call."""
    back=(4,2,3,5,6,3,2,4);pieces={}
    for f,v in enumerate(back):
        pieces.update({f:v,16+f:1,96+f:-1,112+f:-v})
    h=_mix(2048+15)
    for q,v in pieces.items():h^=_mix(q+(v+6)*128)
    return dict(s=1,c=15,e=-1,k=[4,116],half=0,v=0,h=h,r=h,b=[pieces.get(q,0) for q in range(128)])


START = b'''void start(Board *p){
    static const int8_t back[8]={4,2,3,5,6,3,2,4};
    Board t={0};t.s=1;t.c=15;t.e=-1;
    for(int f=0;f<8;f++){put(&t,f,back[f]);put(&t,16+f,1);put(&t,96+f,-1);put(&t,112+f,-back[f]);}
    t.h^=state(&t);t.r=t.h;*p=t;
}
'''


def _constant_start():
    fields=start_fields()
    board=",".join("["+str(q)+"]="+str(v) for q,v in enumerate(fields["b"]) if v)
    return ("void start(Board *p){static const Board t={.s=1,.c=15,.e=-1,.k={4,116},"
        ".h=UINT64_C("+str(fields["h"])+"),.r=UINT64_C("+str(fields["r"])+"),.b={"+board+"}};*p=t;}\n").encode()


def _roles(options):
    roles={n:[] for n in ("tiny.h","board.c","search.c")}
    if "union-order" in options:
        roles["search.c"] += [
            ("same-width-overlapping-move-score-scratch",b"    Move moves[MOVES],bestmove=0;\n    int scores[MOVES],count=gen(p,moves),legal=0,old=alpha,best=-MATE;",
             b"    typedef struct{Move move;int score;} Ranked;\n    union{Move raw[MOVES];Ranked ranked[MOVES];} order;\n"
             b"    _Static_assert(sizeof(Move)==4 && sizeof(int)==4 && sizeof(Ranked)==8 && offsetof(Ranked,score)==4,\"D ranked scratch\");\n"
             b"    Move bestmove=0;int count=gen(p,order.raw),legal=0,old=alpha,best=-MATE;"),
            ("draw-path-before-expansion",b"for(int i=0;i<count;i++)if(make(p,moves[i],&q))",b"for(int i=0;i<count;i++)if(make(p,order.raw[i],&q))"),
            ("backward-in-place-pure-score-expansion",b"    for(int i=0;i<count;i++){\n        Move m=moves[i];int from=FROM(m),to=TO(m),pi=piece_index(p->b[from]);\n        scores[i]=",
             b"    for(int i=count;i--;){\n        Move m=order.raw[i];int from=FROM(m),to=TO(m),pi=piece_index(p->b[from]);\n        order.ranked[i].move=m;order.ranked[i].score="),
            ("same-promotion-score",b"if(PROMO(m))scores[i]+=",b"if(PROMO(m))order.ranked[i].score+="),
            ("strict-score-selection-and-same-replacement",b"        int j=i;for(int k=i+1;k<count;k++)if(scores[k]>scores[j])j=k;\n        Move m=moves[j];moves[j]=moves[i];\n        scores[j]=scores[i];",
             b"        int j=i;for(int k=i+1;k<count;k++)if(order.ranked[k].score>order.ranked[j].score)j=k;\n        Move m=order.ranked[j].move;order.ranked[j]=order.ranked[i];")]
    if "previous-piece" in options:
        roles["search.c"] += [
            ("carry-actual-prior-piece-index",b"int ply,Move previous,Move *root)",b"int ply,int prior,Move *root)"),
            ("remove-only-reconstructed-prior",b"    int prior=previous?piece_index(p->b[TO(previous)]):6;\n",b""),
            ("post-promotion-child-prior",b"-alpha,ply+1,m,0);",b"-alpha,ply+1,piece_index(q.b[to]),0);"),
            ("root-has-no-prior-piece",b"depth,-MATE,MATE,0,0,&best);",b"depth,-MATE,MATE,0,6,&best);")]
    if "constant-start" in options:
        roles["board.c"].append(("independently-derived-static-start",START,_constant_start()))
    if "unsigned-history" in options:
        roles["tiny.h"].append(("only-positive-learners-unsigned",
            b"int16_t history[128][128],continuation[13][13],correction[1024];",
            b"uint16_t history[128][128],continuation[13][13];int16_t correction[1024];"))
        roles["search.c"].append(("same-positive-bonus-recurrence",
            b"static void learn(int16_t *cell,int bonus){\n    *cell+=(bonus-*cell*abs(bonus)/16384);\n}",
            b"static void learn(uint16_t *cell,unsigned bonus){\n    *cell+=(bonus-*cell*bonus/16384);\n}"))
    return roles


def _project(data,roles):
    edits=[]
    for role,before,after in roles:
        if data.count(before)!=1:raise ValueError("unique D structural role required: "+role)
        edits.append((data.index(before),role,before,after))
    parts,records,gaps,cursor,target=[],[],[],0,0
    for begin,role,before,after in sorted(edits):
        if begin<cursor:raise ValueError("overlapping D structural source edits")
        gap=data[cursor:begin];parts.extend((gap,after));gaps.append(pin(gap));target+=len(gap)
        records.append(dict(role=role,target=target,before=before.decode(),after=after.decode()))
        target+=len(after);cursor=begin+len(before)
    parts.append(data[cursor:]);gaps.append(pin(data[cursor:]))
    output=b"".join(parts)
    return output,dict(input=pin(data),output=pin(output),edits=records,gaps=gaps)


def _restore(data,record):
    if pin(data)!=record["output"]:raise ValueError("D structural output differs")
    parts,gaps,cursor=[],[],0
    for row in record["edits"]:
        begin,after=row["target"],row["after"].encode()
        if begin<cursor or data[begin:begin+len(after)]!=after:raise ValueError("D structural edit inverse differs")
        gap=data[cursor:begin];parts.extend((gap,row["before"].encode()));gaps.append(pin(gap));cursor=begin+len(after)
    parts.append(data[cursor:]);gaps.append(pin(data[cursor:]))
    result=b"".join(parts)
    if pin(result)!=record["input"] or gaps!=record["gaps"]:raise ValueError("D structural protected complement differs")
    return result


def _proof(files,result,edits,authority,valid_proof,options):
    return dict(kind=KIND,input=inventory(files),output=inventory(result),source_edits=edits,
        options=list(options),valid_authority=authority,valid=deepcopy(valid_proof),
        initial_position=start_fields() if "constant-start" in options else None,
        semantics=dict(union_order="raw Move expansion runs backward; strict score > and replacement pair unchanged",
            previous_piece="root6; child prior from actual post-make/promotion destination piece",
            constant_start="all Board fields independently derived; unspecified array/padding bytes static zero",
            unsigned_history="BSS0; only depth^2 bonus1..15876; cells0..16384; max product260112384; correction signed"),
        no_libc_runtime=True,persistent_pool=True,atomic128_TT=True,algorithm_features_removed=False,
        independent_semantics_required=True,native_identity_claimed=False,selected=False)


def transform(files,valid,arity,owner,publication,valid_proof,*,options):
    if (not isinstance(options,(tuple,list)) or not options or len(set(options))!=len(options) or
            any(n not in OPTIONS for n in options)):
        raise ValueError("finite explicit D structural candidates required")
    options=tuple(n for n in OPTIONS if n in options)
    authority=_admit(files,valid,arity,owner,publication,valid_proof)
    result,edits=dict(files),{}
    for name,roles in _roles(options).items():
        if roles:result[name],edits[name]=_project(files[name],roles)
    proof=_proof(files,result,edits,authority,valid_proof,options)
    if restore(result,proof,valid,arity,owner,publication)!=files:raise ValueError("D structural full inverse differs")
    return result,proof


def restore(files,proof,valid,arity,owner,publication):
    if proof.get("kind")!=KIND or inventory(files)!=proof.get("output"):
        raise ValueError("unknown or incomplete D structural proof")
    options=tuple(proof["options"])
    if not options or options!=tuple(n for n in OPTIONS if n in options):raise ValueError("D structural option order differs")
    original=dict(files)
    for name,record in proof["source_edits"].items():original[name]=_restore(files[name],record)
    authority=_admit(original,valid,arity,owner,publication,proof["valid"])
    expected,edits=dict(original),{}
    for name,roles in _roles(options).items():
        if roles:expected[name],edits[name]=_project(original[name],roles)
    if files!=expected or proof!=_proof(original,expected,edits,authority,proof["valid"],options):
        raise ValueError("D structural canonical source/proof replay differs")
    return original
