"""B-only post-spelling incoming-move SEE semantics from ordinary literals.

Canonical and DEV keep the old API. This shipping specialization reads no
external report, experiment, compiler/AST data or other repository module.
"""
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


def _transform(source, readable, domain):
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


DOMAIN = {'readable_old': {'identity': {'bytes': 1485, 'sha256': '06832a1f95ccddac3e31387ab44b35e12e078211ad620526aeb2ab8ce9169b84'}, 'identifier_counts': {'Board': 4, 'COUNT': 2, 'Exchange': 2, 'MATE': 1, 'MOVE': 1, 'Move': 1, 'PROMO': 2, 'SEE_INCOMPLETE': 1, 'TO': 3, 'Worker': 1, '__builtin_ctzll': 1, 'abs': 3, 'atomic_load_explicit': 1, 'atomic_store': 1, 'attackers': 1, 'b': 4, 'best': 4, 'candidates': 5, 'capture': 2, 'complete': 3, 'const': 2, 'continue': 1, 'deadline': 2, 'e': 8, 'exchange': 3, 'for': 1, 'from': 3, 'gain': 7, 'i': 3, 'if': 8, 'int': 9, 'm': 9, 'make': 2, 'material': 4, 'memory_order_relaxed': 1, 'now': 2, 'p': 12, 'promotion': 3, 'return': 6, 's': 1, 'see': 1, 'see_calls': 1, 'see_incomplete': 1, 'static': 2, 'stopped': 2, 't': 6, 'target': 7, 'uint64_t': 1, 'visits': 1, 'w': 3, 'while': 1, 'z': 6}}, 'readable_new': {'identity': {'bytes': 1085, 'sha256': '56cb2aea9345bef6fc566bf30bcaee7cf4385dfb01e4250a8f50285780a48c73'}, 'identifier_counts': {'Board': 3, 'COUNT': 2, 'Exchange': 2, 'MATE': 1, 'MOVE': 1, 'Move': 2, 'PROMO': 2, 'SEE_INCOMPLETE': 1, 'TO': 1, 'Worker': 1, '__builtin_ctzll': 1, 'abs': 2, 'atomic_load_explicit': 1, 'atomic_store': 1, 'attackers': 1, 'b': 3, 'best': 4, 'candidates': 5, 'capture': 1, 'complete': 3, 'const': 2, 'deadline': 2, 'e': 8, 'exchange': 3, 'for': 1, 'from': 3, 'gain': 6, 'i': 3, 'if': 7, 'int': 9, 'm': 8, 'make': 1, 'material': 2, 'memory_order_relaxed': 1, 'now': 2, 'p': 7, 'promotion': 3, 'return': 6, 's': 1, 'score': 3, 'see': 1, 'see_calls': 1, 'see_incomplete': 1, 'static': 2, 'stopped': 2, 't': 6, 'target': 7, 'uint64_t': 1, 'visits': 1, 'w': 3, 'while': 1, 'z': 4}}, 'shipping_old': {'identity': {'bytes': 711, 'sha256': 'b14d22e98583863746b28c8f8be97e343efc8319eb666f93ed2352292e32573e'}, 'identifier_counts': {'D': 3, 'MATE': 1, 'MOVE': 1, 'Move': 1, 'PROMO': 2, 'Q': 1, 'SEE_INCOMPLETE': 1, 'TO': 3, '__builtin_ctzll': 1, 'a': 8, 'abs': 3, 'atomic_load_explicit': 1, 'atomic_store': 1, 'b': 4, 'const': 2, 'continue': 1, 'd': 5, 'e': 8, 'f': 3, 'for': 1, 'i': 3, 'if': 8, 'int': 9, 'j': 3, 'l': 1, 'm': 9, 'make': 2, 'memory_order_relaxed': 1, 'now': 2, 'p': 12, 'qc': 2, 'qi': 4, 'qp': 2, 'return': 6, 's': 1, 'static': 2, 't': 6, 'uint64_t': 1, 'w': 1, 'while': 1, 'y': 2, 'yA': 1, 'yv': 7, 'z': 6, 'zJ': 3, 'za': 4, 'zc': 2, 'zd': 1, 'zv': 3}}, 'shipping_new': {'identity': {'bytes': 639, 'sha256': 'd65866537c0308c5703bf51eeda5adf0d9c1fe06605d468ee630efd56ae37411'}, 'identifier_counts': {'D': 3, 'MATE': 1, 'MOVE': 1, 'Move': 2, 'PROMO': 2, 'Q': 1, 'SEE_INCOMPLETE': 1, 'TO': 1, '__builtin_ctzll': 1, 'a': 6, 'abs': 2, 'atomic_load_explicit': 1, 'atomic_store': 1, 'b': 3, 'const': 2, 'd': 5, 'e': 8, 'f': 3, 'for': 1, 'i': 3, 'if': 7, 'int': 9, 'j': 7, 'l': 1, 'm': 8, 'make': 1, 'memory_order_relaxed': 1, 'now': 2, 'p': 7, 'qc': 2, 'qi': 2, 'qp': 2, 'return': 6, 's': 1, 'static': 2, 't': 6, 'uint64_t': 1, 'w': 1, 'while': 1, 'y': 1, 'yA': 1, 'yv': 7, 'z': 4, 'zJ': 3, 'za': 3, 'zc': 2, 'zd': 1, 'zv': 3}}, 'readable_candidate': {'bytes': 28553, 'sha256': '1c5917a22d3442d38c735a9e7e7b284bf3b5b233ae16507ad3277e1bcd4997c9'}}
CANONICAL_PIN = {'bytes': 28953, 'sha256': '1f879828346dfbc6023f6abfbbf1e1d2062e8e2dc0e9919aade254ba7a0a97f6'}
INPUT_PIN = {'bytes': 12220, 'sha256': 'daa9ca6e03260320c13a0a551a0c2586ed53d24d49ebba74f87b57b57814ba9f'}
OUTPUT_PIN = {'bytes': 12148, 'sha256': '6c9081115f5caf209cacc502e19035247a3178aef86c4912fb3a923a651904ce'}


def transform_source(source, *, readable):
    if type(source) is not bytes or type(readable) is not bytes:
        raise ValueError('immutable bytes required for fixed B core specialization')
    if info(source) != INPUT_PIN or info(readable) != CANONICAL_PIN:
        raise ValueError('exact canonical28953 and post-spelling12220 inputs required')
    output, metadata = _transform(source, readable, DOMAIN)
    if info(output) != OUTPUT_PIN:
        raise ValueError('fixed shipping12148 identity differs')
    metadata.update(stage='B shipping incoming-Move SEE; after unchanged spelling maps',
                    readable_proposal=DOMAIN['readable_new']['identity'],
                    canonical_and_DEV_API_changed=False, new_native_identity_required=True,
                    metadata_exception_applied=False, runtime_evidence_inherited=False)
    return output, metadata
