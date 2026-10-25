"""Separate target-centric D attacks and generation-only scalar walker.

Only a fully replayed 5261-byte source class is accepted. Generation preserves
the scalar direction/ray/near-to-far order; attack geometry is a new semantic
candidate requiring independent rules and full search residue comparison.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

KIND = "D-target-centric-attack-source-v1"
SEARCH_SHA = "cd5fa7b2c3c9c1d40664153bbd7f1e3146b03e3de8b237134f6e8321f8e0d8d6"
FILES = {"tiny.h","board.c","search.c","runtime.c","start.S","image.ld"}
SEARCH_OPTIONS = ["previous-piece","unsigned-history"]
FORWARD = b'''static int walk(const Board *,Move *,int,int);
int attacked(const Board *p,int sq,int side){return walk(p,0,sq,side);}
'''
ATTACK = b'''static int walk(const Board *,Move *,int);
int attacked(const Board *p,int sq,int s){
    for(int i=0;i<16;i++){
        int to=sq+steps[i];
        if(!(to&0x88)&&p->b[to]==s*(i<8?2:6))return 1;
    }
    for(int d=-1;d<=1;d+=2){int to=sq-s*16+d;if(!(to&0x88)&&p->b[to]==s)return 1;}
    for(int i=8;i<16;i++)for(int to=sq+steps[i];!(to&0x88);to+=steps[i]){
        int v=p->b[to];if(v){if(v==s*5||v==s*(i<12?4:3))return 1;break;}
    }
    return 0;
}
'''
OLD_WALK = b'''static int walk(const Board *p,Move *moves,int sq,int s){
    int n=0;
    for(int from=0;from<128;from++){
        if(from&0x88){from+=7;continue;}
        int a=abs(p->b[from]);if(p->b[from]*s<=0)continue;
        if(moves&&a==1){
            int to=from+s*16;
            if(!(to&0x88)&&!p->b[to]){
                add(moves,&n,from,to,2);
                if((from>>4)==(s>0?1:6)&&!p->b[to+s*16])add(moves,&n,from,to+s*16,0);
            }
        }
        int first=a==1?(s>0?12:14):a==2?0:a==3?12:8;
        int last=a==1?first+2:a==2?8:a==4?12:16;
        for(int i=first;i<last;i++){
            int step=steps[i];
            for(int to=from+step;!(to&0x88);to+=step){
                int target=p->b[to];
                if(!moves&&to==sq)return 1;
                if(target*s>0||(moves&&a==1&&!target&&to!=p->e))break;
                if(moves)add(moves,&n,from,to,a==1?3:!!target);
                if(target||a<3||a==6)break;
            }
        }
        if(moves&&a==6){
            int home=s>0?4:116,shift=s>0?0:2;
            if(from==home&&!attacked(p,home,-s)){
                for(int d=1;d>=-1;d-=2)
                    if((p->c&((d>0?1:2)<<shift))&&!p->b[home+d]&&!p->b[home+2*d]&&(d>0||!p->b[home-3])&&!attacked(p,home+d,-s))add(moves,&n,from,home+2*d,0);
                }
        }
    }
    return n;
}'''
GEN = b'int gen(const Board *p,Move *moves){return walk(p,moves,0,p->s);}'


def pin(data):
    return dict(bytes=len(data),sha256=sha256(data).hexdigest())


def inventory(files):
    return {n:pin(d) for n,d in sorted(files.items())}


def _admit(files,search,valid,arity,owner,publication,search_proof):
    path=Path(search.__file__)
    if path.parts[-4:]!=("engines","experiments","tiny-d-submission","search_compact.py"):
        raise ValueError("genuine D structural source authority required")
    raw=path.read_bytes().replace(b"\r\n",b"\n")
    if b"\r" in raw or pin(raw)["sha256"]!=SEARCH_SHA:
        raise ValueError("D structural source authority differs")
    if set(files)!=FILES or any(not isinstance(d,bytes) or b"\r" in d for d in files.values()):
        raise ValueError("complete six-file normalized D source required")
    if search_proof.get("options")!=SEARCH_OPTIONS:
        raise ValueError("exact previous-piece/unsigned-history base required")
    original=search.restore(files,search_proof,valid,arity,owner,publication)
    again,proof=search.transform(original,valid,arity,owner,publication,search_proof["valid"],options=SEARCH_OPTIONS)
    if again!=files or proof!=search_proof:
        raise ValueError("complete D structural base proof differs")
    # Shipping has only these three references after DEV/HQ preprocessing:
    # prototype, scalar definition, and gen call; attacked no longer calls it.
    return pin(raw)


def _new_walk():
    data=OLD_WALK.replace(b"int sq,int s)",b"int s)",1)
    for old,new in ((b"if(moves&&a==1)",b"if(a==1)"),
                    (b"                if(!moves&&to==sq)return 1;\n",b""),
                    (b"(moves&&a==1&&!target",b"(a==1&&!target"),
                    (b"if(moves)add(",b"add("),
                    (b"if(moves&&a==6)",b"if(a==6)")):
        if data.count(old)!=1:raise ValueError("exact scalar gen role differs")
        data=data.replace(old,new,1)
    return data


def _roles():
    return [("dedicated-target-centric-attacks",FORWARD,b"#if D_HQ || DEV\n"+FORWARD+b"#else\n"+ATTACK+b"#endif\n"),
            ("generation-only-same-direction-order",OLD_WALK,_new_walk()),
            ("gen-only-callgraph",GEN,b"#if D_HQ || DEV\n"+GEN+b"\n#else\nint gen(const Board *p,Move *moves){return walk(p,moves,p->s);}\n#endif")]


def _project(data):
    records=[]
    for role,before,after in _roles():
        if data.count(before)!=1:raise ValueError("unique D attack source role required: "+role)
        records.append((data.index(before),role,before,after))
    parts,edits,gaps,cursor,target=[],[],[],0,0
    for begin,role,before,after in sorted(records):
        if begin<cursor:raise ValueError("overlapping D attack edits")
        gap=data[cursor:begin];parts.extend((gap,after));gaps.append(pin(gap));target+=len(gap)
        edits.append(dict(role=role,target=target,before=before.decode(),after=after.decode()))
        target+=len(after);cursor=begin+len(before)
    parts.append(data[cursor:]);gaps.append(pin(data[cursor:]))
    output=b"".join(parts)
    return output,dict(input=pin(data),output=pin(output),edits=edits,gaps=gaps)


def _restore(data,record):
    if pin(data)!=record["output"]:raise ValueError("D attack output differs")
    parts,gaps,cursor=[],[],0
    for row in record["edits"]:
        begin,after=row["target"],row["after"].encode()
        if begin<cursor or data[begin:begin+len(after)]!=after:raise ValueError("D attack role inverse differs")
        gap=data[cursor:begin];parts.extend((gap,row["before"].encode()));gaps.append(pin(gap));cursor=begin+len(after)
    parts.append(data[cursor:]);gaps.append(pin(data[cursor:]));result=b"".join(parts)
    if pin(result)!=record["input"] or gaps!=record["gaps"]:raise ValueError("D attack protected complement differs")
    return result


def _proof(files,result,edit,authority,base):
    return dict(kind=KIND,input=inventory(files),output=inventory(result),source_edits={"board.c":edit},
        search_authority=authority,base=deepcopy(base),options=SEARCH_OPTIONS,
        attack_mode="target-centric-knight-king-pawn-and-first-occupied-slider-rays",
        gen_order="unchanged from-square/direction/ray near-to-far including all promotions/castles",
        pinned_piece_attacks=True,friendly_target_attacks=True,EP_and_castling_legality_retained=True,
        inactive_DEV_HQ_original=True,no_libc_runtime=True,persistent_pool=True,atomic128_TT=True,
        independent_rules_and_search_required=True,native_identity_claimed=False,selected=False)


def transform(files,search,valid,arity,owner,publication,search_proof):
    authority=_admit(files,search,valid,arity,owner,publication,search_proof)
    result=dict(files);result["board.c"],edit=_project(files["board.c"])
    proof=_proof(files,result,edit,authority,search_proof)
    if restore(result,proof,search,valid,arity,owner,publication)!=files:
        raise ValueError("D attack complete inverse differs")
    return result,proof


def restore(files,proof,search,valid,arity,owner,publication):
    if proof.get("kind")!=KIND or inventory(files)!=proof.get("output") or set(proof.get("source_edits",{}))!={"board.c"}:
        raise ValueError("unknown or incomplete D attack proof")
    original=dict(files);original["board.c"]=_restore(files["board.c"],proof["source_edits"]["board.c"])
    authority=_admit(original,search,valid,arity,owner,publication,proof["base"])
    expected=dict(original);expected["board.c"],edit=_project(original["board.c"])
    if files!=expected or proof!=_proof(original,expected,edit,authority,proof["base"]):
        raise ValueError("D attack canonical source/proof replay differs")
    return original
