"""One fixed pair of opaque-free SEE regions; no general C transform."""
import hashlib
import re
from collections import Counter

READABLE_OLD = b'''static int exchange(Exchange *e,const Board *p,int target){
    if(++e->visits>1000000||atomic_load_explicit(&stopped,memory_order_relaxed)||now()>=deadline){
        e->complete=0;if(now()>=deadline)atomic_store(&stopped,1);return 0;
    }
    int best=0;uint64_t candidates=attackers(p,target,p->s);
    while(candidates){
        int i=__builtin_ctzll(candidates),from=(i&7)+(i&56)*2;candidates&=candidates-1;
        int promotion=abs(p->b[from])==1&&((target>>4)==0||(target>>4)==7);
        for(int z=promotion?2:0;z<=(promotion?5:0);z++){
            /* The target contains the opponent's prior capturer. Shared
             * attackers proves exactly the generated capture geometry; these
             * four promotion choices are precisely gen's. make filters pins
             * and illegal king recaptures. No EP/castle can be a recapture. */
            Board t;if(!make(p,MOVE(from,target,z),&t))continue;
            int gain=material[abs(p->b[target])]+(z?material[z]-100:0)-exchange(e,&t,target);
            if(!e->complete)return 0;if(gain>best)best=gain;
        }
    }
    return best;
}
static int see(Worker *w,const Board *p,Move m){
    COUNT(w,see_calls);Board t;if(!make(p,m,&t))return -MATE;
    Exchange e={0,1};int gain=capture(p,m)?material[abs(p->b[TO(m)])]:0;
    if(!p->b[TO(m)]&&capture(p,m))gain=100;
    gain+=(PROMO(m)?material[PROMO(m)]-100:0)-exchange(&e,&t,TO(m));
    if(e.complete)return gain;COUNT(w,see_incomplete);return SEE_INCOMPLETE;
}
'''

READABLE_NEW = b'''static int exchange(Exchange *e,const Board *p,Move m){
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

SHIPPING_OLD = b'''static int D(zc*e,const za*p,int yv){if(++e->yA>1000000||atomic_load_explicit(&qp,memory_order_relaxed)||now()>=qc){e->zv=0;if(now()>=qc)atomic_store(&qp,1);return 0;}int a=0;uint64_t d=l(p,yv,p->s);while(d){int i=__builtin_ctzll(d),zJ=(i&7)+(i&56)*2;d&=d-1;int f=abs(p->b[zJ])==1&&((yv>>4)==0||(yv>>4)==7);for(int z=f?2:0;z<=(f?5:0);z++){za t;if(!make(p,MOVE(zJ,yv,z),&t))continue;int j=qi[abs(p->b[yv])]+(z?qi[z]-100:0)-D(e,&t,yv);if(!e->zv)return 0;if(j>a)a=j;}}return a;}static int Q(zd*w,const za*p,Move m){za t;if(!make(p,m,&t))return-MATE;zc e={0,1};int a=y(p,m)?qi[abs(p->b[TO(m)])]:0;if(!p->b[TO(m)]&&y(p,m))a=100;a+=(PROMO(m)?qi[PROMO(m)]-100:0)-D(&e,&t,TO(m));if(e.zv)return a;return SEE_INCOMPLETE;}'''

SHIPPING_NEW = b'''static int D(zc*e,const za*p,Move m){za t;if(!make(p,m,&t))return-MATE;int yv=TO(m),j=qi[abs(p->b[yv])];if(!p->b[yv]&&y(p,m))j=100;j+=PROMO(m)?qi[PROMO(m)]-100:0;if(++e->yA>1000000||atomic_load_explicit(&qp,memory_order_relaxed)||now()>=qc){e->zv=0;if(now()>=qc)atomic_store(&qp,1);return 0;}int a=0;uint64_t d=l(&t,yv,t.s);while(d){int i=__builtin_ctzll(d),zJ=(i&7)+(i&56)*2;d&=d-1;int f=abs(t.b[zJ])==1&&((yv>>4)==0||(yv>>4)==7);for(int z=f?2:0;z<=(f?5:0);z++){int j=D(e,&t,MOVE(zJ,yv,z));if(!e->zv)return 0;if(j>a)a=j;}}return j-a;}static int Q(zd*w,const za*p,Move m){zc e={0,1};int a=D(&e,p,m);if(e.zv)return a;return SEE_INCOMPLETE;}'''

ROLES_D = {'Exchange': 'zc', 'Board': 'za', 'exchange': 'D', 'stopped': 'qp', 'deadline': 'qc', 'attackers': 'l', 'material': 'qi', 'visits': 'yA', 'complete': 'zv', 'target': 'yv', 'best': 'a', 'candidates': 'd', 'from': 'zJ', 'promotion': 'f', 'gain': 'j', 'score': 'j', 'capture': 'y'}
ROLES_Q = {'Exchange': 'zc', 'Board': 'za', 'exchange': 'D', 'stopped': 'qp', 'deadline': 'qc', 'attackers': 'l', 'material': 'qi', 'visits': 'yA', 'complete': 'zv', 'target': 'yv', 'best': 'a', 'candidates': 'd', 'from': 'zJ', 'promotion': 'f', 'gain': 'a', 'score': 'j', 'capture': 'y', 'Worker': 'zd', 'see': 'Q'}



def info(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def code(data):
    return re.sub(rb'/\*.*?\*/', b'', data, flags=re.S)


def counts(data):
    return dict(sorted(Counter(x.decode() for x in re.findall(rb'[A-Za-z_][A-Za-z_0-9]*', code(data))).items()))


def compact(data):
    # These exact fixed regions have no strings, chars or directives.
    word = b'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_0123456789'
    return re.sub(rb'\s+', lambda m: b' ' if m.start() and m.end() < len(data) and data[m.start()-1] in word and data[m.end()] in word else b'', data).strip()


def project(data):
    first, second = data.split(b'static int see(', 1)
    result = []
    for part, roles in ((first, ROLES_D), (b'static int see('+second, ROLES_Q)):
        part = code(part).replace(b'COUNT(w,see_calls);', b'').replace(b'COUNT(w,see_incomplete);', b'')
        if b'"' in part or b"'" in part:
            raise ValueError('fixed region unexpectedly contains an opaque literal')
        part = re.sub(rb'[A-Za-z_][A-Za-z_0-9]*', lambda m: roles.get(m.group().decode(), m.group().decode()).encode(), part)
        result.append(compact(part))
    return b''.join(result)


def transform(source, readable, domain):
    for name, data in (('readable_old', READABLE_OLD), ('readable_new', READABLE_NEW), ('shipping_old', SHIPPING_OLD), ('shipping_new', SHIPPING_NEW)):
        if info(data) != domain[name]['identity'] or counts(data) != domain[name]['identifier_counts']:
            raise ValueError('fixed literal/count domain changed: '+name)
    if project(READABLE_OLD) != SHIPPING_OLD or project(READABLE_NEW) != SHIPPING_NEW:
        raise ValueError('fixed readable/shipping role relation differs')
    results, metadata = [], {}
    for label, data, old, new in (('readable', readable, READABLE_OLD, READABLE_NEW), ('shipping', source, SHIPPING_OLD, SHIPPING_NEW)):
        if data.count(old) != 1 or new in data:
            raise ValueError('sole immutable preimage required: '+label)
        before, after = data.split(old)
        result = before+new+after
        if result.count(new) != 1 or result.replace(new, old, 1) != data:
            raise ValueError('literal inverse differs: '+label)
        metadata[label] = {'old_region': info(old), 'new_region': info(new), 'source': info(result),
            'source_delta': len(result)-len(data), 'protected_complement': info(before+after), 'exact_inverse': True}
        results.append(result)
    if info(results[0]) != domain['readable_candidate']:
        raise ValueError('fixed readable candidate identity differs')
    metadata.update(fixed_role_projection=True, literal_count_domain=True, old_maps_or_guards_changed=False,
        full_legal_minimax_retained=True, model_or_search_policy_changed=False, new_frame_stack_identity_unqualified=True)
    return results[1], metadata
