"""ONE F probabilistic partial-tag TT policy; not full-key equivalence."""
import hashlib

BASE_BYTES = 9690
BASE_SHA256 = 'e0aa8dd94f6dbfa1a3da172cde28492083d259b780344f49e7f5eb906523f9f6'
CANDIDATE_BYTES = 9626
CANDIDATE_SHA256 = 'dd999295295e490efd727b5957ceaf5e3368360a6356a15b85e96d1cabb6ba0a'
PAIRS = ((b'typedef struct{atomic_flag zN;uint64_t a,b;}zb;', b'typedef _Atomic uint64_t zb;'), (b'static uint64_t ak(uint64_t a,uint64_t d){zb*e=qq+(a&((1u<<18)-1));if(atomic_flag_test_and_set_explicit(&e->zN,memory_order_acquire))return 0;if(d)e->a=a,e->b=d;else d=e->a==a?e->b:0;atomic_flag_clear_explicit(&e->zN,memory_order_release);return d;}', b'static uint64_t ak(uint64_t a,uint64_t d){zb*e=qq+(a&((1u<<18)-1));if(d)atomic_store_explicit(e,(a>>43<<43)|d,memory_order_relaxed);else{d=atomic_load_explicit(e,memory_order_relaxed);d=(d>>43)==(a>>43)?d&((1ULL<<43)-1):0;}return d;}'), (b'static void az(void){for(size_t i=0;i<((size_t)1<<18);i++){qq[i].a=qq[i].b=0;atomic_flag_clear(&qq[i].zN);}}', b'static void az(void){for(size_t i=0;i<((size_t)1<<18);i++)atomic_init(qq+i,0);}'))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def transform(source):
    if len(source) != BASE_BYTES or sha(source) != BASE_SHA256:
        raise ValueError('exact uncombined F4728 full-key control required')
    candidate = source
    for old, new in PAIRS:
        if candidate.count(old) != 1:
            raise ValueError('fixed TT old span is not unique')
        candidate = candidate.replace(old, new, 1)
    inverse = candidate
    before, after = source, candidate
    for index, (old, new) in enumerate(PAIRS):
        if inverse.count(new) != 1:
            raise ValueError('fixed TT new span is not unique')
        inverse = inverse.replace(new, old, 1)
        marker = ('$TTSPAN'+str(index)).encode()
        before = before.replace(old, marker, 1)
        after = after.replace(new, marker, 1)
    if inverse != source or before != after:
        raise ValueError('TT inverse/protected complement differs')
    if len(candidate) != CANDIDATE_BYTES or sha(candidate) != CANDIDATE_SHA256:
        raise ValueError('fixed partial-tag candidate differs')
    return candidate, {'policy_change': 'probabilistic TT identity, not lossless/full-key equivalence',
                       'inverse_equal': True, 'protected_complement_equal': True,
                       'key_tag_bits': 21, 'index_bits': 18, 'payload_bits': 43,
                       'ignored_key_bits': [18, 42], 'source_delta': -64,
                       'payload_caller_domain': 'unchanged actual move17/score16/depth8/bound2 formatter; valid bound2/3 nonzero',
                       'single_word_relaxed_load_store': True, 'atomic_init_before_workers': True,
                       'shipping_profile_assertions_added': False}
