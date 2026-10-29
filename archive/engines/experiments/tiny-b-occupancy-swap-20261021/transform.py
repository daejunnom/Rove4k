"""One fixed B geometry-only occupancy-swap ordering policy, not legal-LVA."""
import hashlib
import re

INPUT = {'bytes':11430,'sha256':'54759113c9949f0f3d619d5eefe5e8ac4d6b562baf4c09da7e7743907d3f8a2a'}
OUTPUT = {'bytes':11487,'sha256':'418b37627d4fb769bb6dd18a4659386e8fd07933fa95e0a1c9c9a70423d797f5'}

# Only this same-target query may read the deliberately incoherent scratch.
# No scratch make/HCE/hash/TT/search/learning consumers are permitted.
# Non-king pins/check evasion are deliberately ignored in this ordering model.
# Queen is the max of four recapture promotions only in target-invariant geometry.
# Production admission is startpos+legal replay, <=32 pieces, hence gain[32].
READABLE_SEE = b'''static int see(Worker *worker,const Board *position,Move move){
    Board scratch;
    if(!make(position,move,&scratch))return -MATE;
    int target=TO(move),gain[32],count=0,side=scratch.s,victim=abs(scratch.b[target]);
    gain[0]=qi[abs(position->b[target])];
    if(!position->b[target]&&!PROMO(move)&&(move&8))gain[0]=100;
    gain[0]+=PROMO(move)?qi[PROMO(move)]-100:0;
    for(;;){
        if(atomic_load_explicit(&qp,memory_order_relaxed)||now()>=qc){
            if(now()>=qc)atomic_store(&qp,1);
            return SEE_INCOMPLETE;
        }
        uint64_t attackers=l(&scratch,target,side),origins=0;
        int kind;
        for(kind=1;kind<7;kind++)if((origins=attackers&scratch.bb[side<0][kind]))break;
        if(!origins)break;
        int index=__builtin_ctzll(origins),from=(index&7)+(index&56)*2;
        scratch.b[from]=0;
        scratch.bb[side<0][0]&=~o(from);
        if(kind==6&&l(&scratch,target,-side))break;
        int promoted=kind==1&&((target>>4)==0||(target>>4)==7)?5:kind;
        ++count;
        gain[count]=qi[victim]+(promoted!=kind?800:0)-gain[count-1];
        victim=promoted;
        side=-side;
        if(kind==6)break;
    }
    while(count){
        int a=-gain[count-1],b=gain[count];
        gain[--count]=-(a>b?a:b);
    }
    return gain[0];
}
'''
ROLES = {'see':'Q','Worker':'zd','Board':'za','worker':'w','position':'p','move':'m',
         'scratch':'t','target':'yv','gain':'j','count':'n','side':'s','victim':'k',
         'attackers':'d','origins':'b','kind':'a','index':'i','from':'f','promoted':'z'}
OLD_SEE = b'static int Q(zd*w,const za*p,Move m){za t;if(!make(p,m,&t))return-MATE;int yv=TO(m),j=qi[abs(p->b[yv])];if(!p->b[yv]&&!PROMO(m)&&(m&8))j=100;j+=PROMO(m)?qi[PROMO(m)]-100:0;if(atomic_load_explicit(&qp,memory_order_relaxed)||now()>=qc){if(now()>=qc)atomic_store(&qp,1);return SEE_INCOMPLETE;}uint64_t d=l(&t,yv,t.s);for(int k=1;k<7;k++){uint64_t b=d&t.bb[t.s<0][k];while(b){int i=__builtin_ctzll(b),zJ=(i&7)+(i&56)*2;b&=b-1;int f=k==1&&((yv>>4)==0||(yv>>4)==7);int a=-MATE;for(int z=f?2:0;z<=(f?5:0);z++){int j=Q(w,&t,MOVE(zJ,yv,z));if(j==SEE_INCOMPLETE)return SEE_INCOMPLETE;if(j>a)a=j;}if(a!=-MATE)return j-(a>0?a:0);}}return j;}'
NEW_SEE = b'static int Q(zd*w,const za*p,Move m){za t;if(!make(p,m,&t))return-MATE;int yv=TO(m),j[32],n=0,s=t.s,k=abs(t.b[yv]);j[0]=qi[abs(p->b[yv])];if(!p->b[yv]&&!PROMO(m)&&(m&8))j[0]=100;j[0]+=PROMO(m)?qi[PROMO(m)]-100:0;for(;;){if(atomic_load_explicit(&qp,memory_order_relaxed)||now()>=qc){if(now()>=qc)atomic_store(&qp,1);return SEE_INCOMPLETE;}uint64_t d=l(&t,yv,s),b=0;int a;for(a=1;a<7;a++)if((b=d&t.bb[s<0][a]))break;if(!b)break;int i=__builtin_ctzll(b),f=(i&7)+(i&56)*2;t.b[f]=0;t.bb[s<0][0]&=~o(f);if(a==6&&l(&t,yv,-s))break;int z=a==1&&((yv>>4)==0||(yv>>4)==7)?5:a;++n;j[n]=qi[k]+(z!=a?800:0)-j[n-1];k=z;s=-s;if(a==6)break;}while(n){int a=-j[n-1],b=j[n];j[--n]=-(a>b?a:b);}return j[0];}'
ORDERING = b'if(m&8){int s=Q(w,p,m);if(s!=SEE_INCOMPLETE)Y[i]+=s*32;}'


def info(data):
    return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}


def transform(source):
    if info(source)!=INPUT:
        raise ValueError('exact actual qualified B5357 shipping input required')
    projected=re.sub(rb'[A-Za-z_][A-Za-z_0-9]*',lambda m:ROLES.get(m.group().decode(),m.group().decode()).encode(),READABLE_SEE)
    word=b'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_0123456789'
    projected=re.sub(rb'\s+',lambda m:b' ' if m.start() and m.end()<len(projected) and projected[m.start()-1] in word and projected[m.end()] in word else b'',projected).strip()
    if projected!=NEW_SEE:
        raise ValueError('fixed readable/physical roles differ')
    if source.count(OLD_SEE)!=1 or source.count(ORDERING)!=1:
        raise ValueError('one old SEE and one unchanged ordering caller required')
    at=source.index(OLD_SEE)
    result=source[:at]+NEW_SEE+source[at+len(OLD_SEE):]
    if result[:at]+OLD_SEE+result[at+len(NEW_SEE):]!=source:
        raise ValueError('full source inverse differs')
    if result.count(ORDERING)!=1 or b'Q(w,&t,' in result:
        raise ValueError('ordering or removed recursion differs')
    if OUTPUT is None or info(result)!=OUTPUT:
        raise ValueError('literal source-prepared output pin required')
    return result,{'old_fragment':info(OLD_SEE),'new_fragment':info(NEW_SEE),
        'old_start':at,'old_end':at+len(OLD_SEE),'new_end':at+len(NEW_SEE),
        'protected_complement':info(source[:at]+source[at+len(OLD_SEE):]),
        'full_inverse':True,'readable_role_binding':True,'ordering_unknown_guard_unchanged':True,
        'initial_actual_make':1,'scratch_consumers':'fixed-target l/walk query only',
        'declared_model':'geometric kind/ctz occupancy swap; nonking pins ignored; king destination geometric filter',
        'four_initial_promotions_preserved':True,'recapture_promotion_max':'queen dominance only within target-invariant geometry',
        'gain_capacity':32,'progress':'one distinct off-target origin removed per continuation',
        'negative_pruning_certificate':False,'QS_SEE_pruning_disabled':True,
        'legal_LVA_equivalence':False,'full_minimax_equivalence':False,
        'private_ABI_and_TT17_unchanged':True,'fullkey_TT_singular_learning_input_pool_complement_unchanged':True,
        'old_legal_model_runtime_strength_stack_evidence_inherited':False}
