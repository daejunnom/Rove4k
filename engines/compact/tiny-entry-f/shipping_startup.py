"""Fixed shipping-only F calloc payload initialization sharing.

The complete post-unit-bound source admits one startup az call before the
first worker creation. Its two payload members are uint64_t, whose calloc
zero bytes represent integer zero. Atomic flag initialization remains explicit.
DEV never enters this stage; its quiescent reset/clear path stays unchanged.
No experiment, report, generated artifact or external source is an input.
"""
import hashlib

INPUT_BYTES = 9442
INPUT_SHA256 = '245dae234e80c514d64da9109326dbf50077d703f6f353011f97aac682bdfd20'
OUTPUT_BYTES = 9422
OUTPUT_SHA256 = '109cb9df07a6d2a44b2930abcdadaba2246d953e1276a70a66ecb182fd77544a'
OLD = b'static void az(void){for(size_t i=0;i<((size_t)1<<18);i++){qq[i].a=qq[i].b=0;atomic_flag_clear(&qq[i].zN);}}'
NEW = b'static void az(void){for(size_t i=0;i<((size_t)1<<18);i++)atomic_flag_clear(&qq[i].zN);}'
CALL = b'qq=calloc((size_t)1<<18,sizeof*qq);if(!qq)return 2;az();'
ENTRY = b'typedef struct{atomic_flag zN;W a,b;}Z;'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def transform_source(source):
    if type(source) is not bytes or len(source) != INPUT_BYTES or sha(source) != INPUT_SHA256:
        raise ValueError('exact post-unit-bound F shipping source required')
    if (source.count(OLD) != 1 or NEW in source or source.count(b'az(') != 2 or
            source.count(CALL) != 1 or source.count(ENTRY) != 1 or
            source.count(b'typedef uint64_t W;') != 1 or source.count(b'qq=') != 1 or
            source.count(b'calloc(') != 1 or source.count(b'pthread_create(') != 1):
        raise ValueError('sole calloc startup/function/type contract differs')
    main = source.index(b'int main(void){')
    call = source.index(CALL)
    spawn = source.index(b'pthread_create(')
    if not main < call < spawn or source.index(OLD) >= main:
        raise ValueError('startup initialization no longer precedes worker publication')
    before, after = source.split(OLD)
    result = before + NEW + after
    if result.count(NEW) != 1 or result.replace(NEW, OLD) != source:
        raise ValueError('startup expression inverse differs')
    if len(result) != OUTPUT_BYTES or sha(result) != OUTPUT_SHA256:
        raise ValueError('fixed startup output differs')
    return result, {
        'stage': 'shipping-after-unit-bound', 'exact_inverse': True,
        'protected_complement_bytes': len(before) + len(after),
        'protected_complement_sha256': sha(before + after),
        'removed': 'only qq[i].a=qq[i].b=0 after checked calloc',
        'unsigned64_key_payload_calloc_zero': True,
        'sole_az_definition_and_startup_call': True,
        'initialization_before_first_pthread_create': True,
        'atomic_flag_clear_preserved': True, 'DEV_bypasses_stage': True,
        'TT_key_payload_layout_probe_search_clock_pool_policy_unchanged': True,
        'entire_native_identity_to_predecessor': False,
    }
