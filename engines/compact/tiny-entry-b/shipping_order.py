"""Pure B shipping legal-LVA ordering stage after the fixed input profile.

Only ordinary embedded literals, fixed roles and full source pins are inputs.
DEV bypasses this stage and remains the old full-minimax reference model.
"""
import hashlib
import re
from collections import Counter

OLD_READABLE = b'''static int exchange(Exchange *e,const Board *p,Move m){
    Board t;if(!make(p,m,&t))return -MATE;
    int target=TO(m),gain=material[abs(p->b[target])];
    if(!p->b[target]&&capture(p,m))gain=100;
    gain+=PROMO(m)?material[PROMO(m)]-100:0;
    if(++e->visits>1000000||atomic_load_explicit(&stopped,memory_order_relaxed)||now()>=deadline){
        e->complete=0;if(now()>=deadline)atomic_store(&stopped,1);return 0;
    }
    int best=0;uint64_t candidates=attackers(&t,target,t.s);
    while(candidates){
        int i=__builtin_ctzll(candidates),from=(i&7)+(i&56)*2;candidates&=candidates-1;
        int promotion=abs(t.b[from])==1&&((target>>4)==0||(target>>4)==7);
        for(int z=promotion?2:0;z<=(promotion?5:0);z++){
            int score=exchange(e,&t,MOVE(from,target,z));
            if(!e->complete)return 0;if(score>best)best=score;
        }
    }
    return gain-best;
}
static int see(Worker *w,const Board *p,Move m){
    COUNT(w,see_calls);Exchange e={0,1};int gain=exchange(&e,p,m);
    if(e.complete)return gain;COUNT(w,see_incomplete);return SEE_INCOMPLETE;
}
'''

NEW_READABLE = b'''static int sequence(Worker *w,const Board *p,Move m){
    Board t;if(!make(p,m,&t))return -MATE;
    int target=TO(m),gain=material[abs(p->b[target])];
    if(!p->b[target]&&capture(p,m))gain=100;
    gain+=PROMO(m)?material[PROMO(m)]-100:0;
    if(atomic_load_explicit(&stopped,memory_order_relaxed)||now()>=deadline){
        if(now()>=deadline)atomic_store(&stopped,1);return SEE_INCOMPLETE;
    }
    uint64_t candidates=attackers(&t,target,t.s);
    for(int kind=1;kind<7;kind++){
        uint64_t origins=candidates&t.bb[t.s<0][kind];
        while(origins){
            int i=__builtin_ctzll(origins),from=(i&7)+(i&56)*2;origins&=origins-1;
            int promotion=kind==1&&((target>>4)==0||(target>>4)==7);
            int best=-MATE;
            for(int z=promotion?2:0;z<=(promotion?5:0);z++){
                int score=sequence(w,&t,MOVE(from,target,z));
                if(score==SEE_INCOMPLETE)return SEE_INCOMPLETE;
                if(score>best)best=score;
            }
            if(best!=-MATE)return gain-(best>0?best:0);
        }
    }
    return gain;
}
'''

OLD_SEE = b'''static int D(zc*e,const za*p,Move m){za t;if(!make(p,m,&t))return-MATE;int yv=TO(m),j=qi[abs(p->b[yv])];if(!p->b[yv]&&y(p,m))j=100;j+=PROMO(m)?qi[PROMO(m)]-100:0;if(++e->yA>1000000||atomic_load_explicit(&qp,memory_order_relaxed)||now()>=qc){e->zv=0;if(now()>=qc)atomic_store(&qp,1);return 0;}int a=0;uint64_t d=l(&t,yv,t.s);while(d){int i=__builtin_ctzll(d),zJ=(i&7)+(i&56)*2;d&=d-1;int f=abs(t.b[zJ])==1&&((yv>>4)==0||(yv>>4)==7);for(int z=f?2:0;z<=(f?5:0);z++){int j=D(e,&t,MOVE(zJ,yv,z));if(!e->zv)return 0;if(j>a)a=j;}}return j-a;}static int Q(zd*w,const za*p,Move m){zc e={0,1};int a=D(&e,p,m);if(e.zv)return a;return SEE_INCOMPLETE;}'''

NEW_SEE = b'''static int Q(zd*w,const za*p,Move m){za t;if(!make(p,m,&t))return-MATE;int yv=TO(m),j=qi[abs(p->b[yv])];if(!p->b[yv]&&y(p,m))j=100;j+=PROMO(m)?qi[PROMO(m)]-100:0;if(atomic_load_explicit(&qp,memory_order_relaxed)||now()>=qc){if(now()>=qc)atomic_store(&qp,1);return SEE_INCOMPLETE;}uint64_t d=l(&t,yv,t.s);for(int k=1;k<7;k++){uint64_t b=d&t.bb[t.s<0][k];while(b){int i=__builtin_ctzll(b),zJ=(i&7)+(i&56)*2;b&=b-1;int f=k==1&&((yv>>4)==0||(yv>>4)==7);int a=-MATE;for(int z=f?2:0;z<=(f?5:0);z++){int j=Q(w,&t,MOVE(zJ,yv,z));if(j==SEE_INCOMPLETE)return SEE_INCOMPLETE;if(j>a)a=j;}if(a!=-MATE)return j-(a>0?a:0);}}return j;}'''

OLD_TYPE = b'''typedef struct{unsigned yA;int zv;}zc;'''

OLD_QS = b'''if(ye&&!PROMO(m)){int s=Q(w,p,m);if(s!=SEE_INCOMPLETE&&s<0)continue;}'''

ORDERING = b'''if(y(p,m)||PROMO(m)){int s=Q(w,p,m);if(s!=SEE_INCOMPLETE)Y[i]+=s*32;}'''

OLD_NET_ROLES = {'Exchange': 'zc', 'Board': 'za', 'exchange': 'D', 'stopped': 'qp', 'deadline': 'qc', 'attackers': 'l', 'material': 'qi', 'visits': 'yA', 'complete': 'zv', 'target': 'yv', 'best': 'a', 'candidates': 'd', 'from': 'zJ', 'promotion': 'f', 'gain': 'j', 'score': 'j', 'capture': 'y'}
OLD_WRAPPER_ROLES = {'Exchange': 'zc', 'Board': 'za', 'exchange': 'D', 'stopped': 'qp', 'deadline': 'qc', 'attackers': 'l', 'material': 'qi', 'visits': 'yA', 'complete': 'zv', 'target': 'yv', 'best': 'a', 'candidates': 'd', 'from': 'zJ', 'promotion': 'f', 'gain': 'a', 'score': 'j', 'capture': 'y', 'Worker': 'zd', 'see': 'Q'}
NEW_ROLES = {'Worker': 'zd', 'Board': 'za', 'sequence': 'Q', 'stopped': 'qp', 'deadline': 'qc', 'attackers': 'l', 'material': 'qi', 'target': 'yv', 'gain': 'j', 'capture': 'y', 'candidates': 'd', 'kind': 'k', 'origins': 'b', 'from': 'zJ', 'promotion': 'f', 'best': 'a', 'score': 'j'}



def info(data):
    return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}


def code(data):
    return re.sub(rb'/\*.*?\*/',b'',data,flags=re.S)


def counts(data):
    return dict(sorted(Counter(x.decode() for x in re.findall(rb'[A-Za-z_][A-Za-z_0-9]*',code(data))).items()))


def project(part,roles):
    part=code(part).replace(b'COUNT(w,see_calls);',b'').replace(b'COUNT(w,see_incomplete);',b'')
    if b'"' in part or b"'" in part:raise ValueError('fixed model region has an opaque literal')
    part=re.sub(rb'[A-Za-z_][A-Za-z_0-9]*',lambda m:roles.get(m.group().decode(),m.group().decode()).encode(),part)
    word=b'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_0123456789'
    return re.sub(rb'\s+',lambda m:b' ' if m.start() and m.end()<len(part) and part[m.start()-1] in word and part[m.end()] in word else b'',part).strip()


def _transform(source,domain):
    if type(source) is not bytes or info(source)!=domain['input']:
        raise ValueError('one fixed B input-profile preimage required')
    literals={'old_readable':OLD_READABLE,'new_readable':NEW_READABLE,'old_see':OLD_SEE,
              'new_see':NEW_SEE,'old_exchange_type':OLD_TYPE,'old_QS':OLD_QS}
    for name,data in literals.items():
        if info(data)!=domain[name]['identity'] or counts(data)!=domain[name]['identifier_counts']:
            raise ValueError('literal/count domain differs: '+name)
    first,last=OLD_READABLE.split(b'static int see(',1)
    if project(first,OLD_NET_ROLES)+project(b'static int see('+last,OLD_WRAPPER_ROLES)!=OLD_SEE:
        raise ValueError('old readable/physical model binding differs')
    if project(NEW_READABLE,NEW_ROLES)!=NEW_SEE:
        raise ValueError('new readable/physical model binding differs')
    patches=[]
    for name,old,new in [('Exchange',OLD_TYPE,b''),('SEE',OLD_SEE,NEW_SEE),('QS',OLD_QS,b'')]:
        if source.count(old)!=1 or (new and new in source):raise ValueError('one immutable old region required: '+name)
        a=source.index(old);patches.append((a,a+len(old),name,old,new))
    patches.sort();parts=[];retained=[];rows=[];at=0;offset=0
    for a,b,name,old,new in patches:
        if a<at:raise ValueError('overlapping fixed changes')
        same=source[at:a];parts.append(same);retained.append(same);offset+=len(same)
        rows.append({'name':name,'old_start':a,'old_end':b,'new_start':offset,'new_end':offset+len(new),
                     'old':info(old),'new':info(new)})
        parts.append(new);offset+=len(new);at=b
    parts.append(source[at:]);retained.append(source[at:]);output=b''.join(parts)
    inverse=output
    for row,patch in reversed(list(zip(rows,patches))):
        old,new=patch[3],patch[4];a,b=row['new_start'],row['new_end']
        if inverse[a:b]!=new:raise ValueError('inverse replacement preimage differs')
        inverse=inverse[:a]+old+inverse[b:]
    if inverse!=source:raise ValueError('full raw inverse differs')
    if output.count(ORDERING)!=1 or OLD_QS in output:
        raise ValueError('ordering/disabled-QS policy differs')
    tokens=re.findall(rb'[A-Za-z_][A-Za-z_0-9]*',output)
    if b'D' in tokens or b'zc' in tokens:raise ValueError('old net/Exchange reference remains')
    if info(output)!=domain['output']:raise ValueError('one literal output differs')
    return output,{'regions':rows,'protected_complement':info(b''.join(retained)),
        'full_inverse':True,'three_regions_disjoint':True,'input_processing_and_all_other_bytes_identical':True,
        'readable_role_binding':True,'literal_count_domain':True,'ordering_call_and_unknown_guard_exact':True,
        'all_four_promotions_and_legal_make_retained_in_declared_model':True,
        'QS_SEE_pruning_disabled':True,'full_minimax_equivalence':False,'policy_changed':True,
        'old_visit_DEV_stack_evidence_inherited':False,'helper_executes_native_or_runtime':False}


DOMAIN = {'input': {'bytes': 11829, 'sha256': '11a32cc6c48ad16856e7968c5ba91456257c1b249590f0aa71a371d2fd276a93'}, 'output': {'bytes': 11702, 'sha256': 'd0b914e337f56623f7d1028381ccc4b012da02c4bc0681737a7a6a6e571274c7'}, 'old_readable': {'identity': {'bytes': 1085, 'sha256': '56cb2aea9345bef6fc566bf30bcaee7cf4385dfb01e4250a8f50285780a48c73'}, 'identifier_counts': {'Board': 3, 'COUNT': 2, 'Exchange': 2, 'MATE': 1, 'MOVE': 1, 'Move': 2, 'PROMO': 2, 'SEE_INCOMPLETE': 1, 'TO': 1, 'Worker': 1, '__builtin_ctzll': 1, 'abs': 2, 'atomic_load_explicit': 1, 'atomic_store': 1, 'attackers': 1, 'b': 3, 'best': 4, 'candidates': 5, 'capture': 1, 'complete': 3, 'const': 2, 'deadline': 2, 'e': 8, 'exchange': 3, 'for': 1, 'from': 3, 'gain': 6, 'i': 3, 'if': 7, 'int': 9, 'm': 8, 'make': 1, 'material': 2, 'memory_order_relaxed': 1, 'now': 2, 'p': 7, 'promotion': 3, 'return': 6, 's': 1, 'score': 3, 'see': 1, 'see_calls': 1, 'see_incomplete': 1, 'static': 2, 'stopped': 2, 't': 6, 'target': 7, 'uint64_t': 1, 'visits': 1, 'w': 3, 'while': 1, 'z': 4}}, 'new_readable': {'identity': {'bytes': 1079, 'sha256': 'e3b6ef7c8144ce74890377e827f83a06eafacd4e4e6ae4688fb788498e0f8c73'}, 'identifier_counts': {'Board': 2, 'MATE': 3, 'MOVE': 1, 'Move': 1, 'PROMO': 2, 'SEE_INCOMPLETE': 3, 'TO': 1, 'Worker': 1, '__builtin_ctzll': 1, 'abs': 1, 'atomic_load_explicit': 1, 'atomic_store': 1, 'attackers': 1, 'b': 2, 'bb': 1, 'best': 6, 'candidates': 2, 'capture': 1, 'const': 1, 'deadline': 2, 'for': 2, 'from': 2, 'gain': 5, 'i': 3, 'if': 7, 'int': 8, 'kind': 5, 'm': 6, 'make': 1, 'material': 2, 'memory_order_relaxed': 1, 'now': 2, 'origins': 5, 'p': 5, 'promotion': 3, 'return': 5, 's': 2, 'score': 4, 'sequence': 2, 'static': 1, 'stopped': 2, 't': 7, 'target': 7, 'uint64_t': 2, 'w': 2, 'while': 1, 'z': 4}}, 'old_see': {'identity': {'bytes': 639, 'sha256': 'd65866537c0308c5703bf51eeda5adf0d9c1fe06605d468ee630efd56ae37411'}, 'identifier_counts': {'D': 3, 'MATE': 1, 'MOVE': 1, 'Move': 2, 'PROMO': 2, 'Q': 1, 'SEE_INCOMPLETE': 1, 'TO': 1, '__builtin_ctzll': 1, 'a': 6, 'abs': 2, 'atomic_load_explicit': 1, 'atomic_store': 1, 'b': 3, 'const': 2, 'd': 5, 'e': 8, 'f': 3, 'for': 1, 'i': 3, 'if': 7, 'int': 9, 'j': 7, 'l': 1, 'm': 8, 'make': 1, 'memory_order_relaxed': 1, 'now': 2, 'p': 7, 'qc': 2, 'qi': 2, 'qp': 2, 'return': 6, 's': 1, 'static': 2, 't': 6, 'uint64_t': 1, 'w': 1, 'while': 1, 'y': 1, 'yA': 1, 'yv': 7, 'z': 4, 'zJ': 3, 'za': 3, 'zc': 2, 'zd': 1, 'zv': 3}}, 'new_see': {'identity': {'bytes': 619, 'sha256': '48b28df30eea0ea73755ff95150581e471d0e2944137d2113f0d7e837ee286ec'}, 'identifier_counts': {'MATE': 3, 'MOVE': 1, 'Move': 1, 'PROMO': 2, 'Q': 2, 'SEE_INCOMPLETE': 3, 'TO': 1, '__builtin_ctzll': 1, 'a': 6, 'abs': 1, 'atomic_load_explicit': 1, 'atomic_store': 1, 'b': 7, 'bb': 1, 'const': 1, 'd': 2, 'f': 3, 'for': 2, 'i': 3, 'if': 7, 'int': 8, 'j': 9, 'k': 5, 'l': 1, 'm': 6, 'make': 1, 'memory_order_relaxed': 1, 'now': 2, 'p': 5, 'qc': 2, 'qi': 2, 'qp': 2, 'return': 5, 's': 2, 'static': 1, 't': 7, 'uint64_t': 2, 'w': 2, 'while': 1, 'y': 1, 'yv': 7, 'z': 4, 'zJ': 2, 'za': 2, 'zd': 1}}, 'old_exchange_type': {'identity': {'bytes': 38, 'sha256': '2ca863ce510660796ed2c4f44c9f142ea3659a8432c640f3b72e26b2b6a30d41'}, 'identifier_counts': {'int': 1, 'struct': 1, 'typedef': 1, 'unsigned': 1, 'yA': 1, 'zc': 1, 'zv': 1}}, 'old_QS': {'identity': {'bytes': 69, 'sha256': 'e5149595f074b3fb20dd03c764fa56618786d8aba9df7a38a4d189097b3be0e0'}, 'identifier_counts': {'PROMO': 1, 'Q': 1, 'SEE_INCOMPLETE': 1, 'continue': 1, 'if': 2, 'int': 1, 'm': 2, 'p': 1, 's': 3, 'w': 1, 'ye': 1}}}
COMPLEMENT_PIN = {'bytes':11083,'sha256':'fcdabe2a1e418bb681d214dead40b229ce4d40ee2504da28be420242e646ccdf'}


def transform_source(source):
    output,metadata=_transform(source,DOMAIN)
    if metadata['protected_complement']!=COMPLEMENT_PIN:
        raise ValueError('fixed B all-gap complement differs')
    metadata.update(stage='B legal-LVA ordering after fixed shipping input profile',
        declared_model='first legal pre-capture kind then ctz source; all selected-source promotions maximized; decline0',
        approximate_negative_is_pruning_certificate=False,
        canonical_and_DEV_model_changed=False,
        DEV_model_equivalent_to_shipping=False,
        new_full_native_identity_required=True,
        old_minimax_visit_stack_evidence_inherited=False,
        production_wallclock_or_strength_proved_by_helper=False,
        metadata_exception_applied=False)
    return output,metadata
