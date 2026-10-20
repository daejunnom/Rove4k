"""Fixed B legal-LVA ordering model; no general C transform or external input."""
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


def transform(source,domain):
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
        'old_visit_DEV_stack_evidence_inherited':False,'native_whole_runtime_unknown':True}
