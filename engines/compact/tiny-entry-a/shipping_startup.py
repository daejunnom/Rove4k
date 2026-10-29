"""A-only final startup-zero stage after capture bits; DEV bypasses it.

calloc supplies all-bits-zero storage. W is unsigned exact-width uint64_t,
so both TT key/data fields already have value0 (and no padding/trap concern).
The sole startup caller is before pthread_create; this is not a table reset.
Explicit atomic_flag_clear is retained for every entry. No file, artifact,
experiment, report, AST tool or network is a generation input.
"""
import hashlib

READABLE = '71f9ff6ce1b7f555ad85c3bf49766381c0627315da94acf0c49eeee7bee4a734'
INPUT_SHA256 = 'b4aa345388c20d4701732a2ce561bd2714b1f1d26b756aa79c05ae8dfc006cf8'
OUTPUT_SHA256 = '7dc2243e255e2b191e4bb7785826c69556c45534ed4c1832796ccdca637d4f55'
BEFORE = b'static void aX(void){for(size_t i=0;i<((size_t)1<<18);i++){qq[i].aT=qq[i].U=0;atomic_flag_clear(&qq[i].zN);}}'
AFTER = b'static void aX(void){for(size_t i=0;i<((size_t)1<<18);i++)atomic_flag_clear(&qq[i].zN);}'
CALLER = b'qq=calloc((size_t)1<<18,sizeof*qq);if(!qq)return 2;aX();'
OFFSET = 7496
END = 7605
COMPLEMENT_BYTES = 9282
COMPLEMENT_SHA256 = '4ef280e525fc856e114c0afa086aac5e9f03f7602e481ebc6f2abc4648146580'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def need(value, message):
    if not value:
        raise ValueError(message)


def startup_context(source):
    need(source.count(b'aX(') == 2 and source.count(CALLER) == 1,
         'startup clear must have exactly its definition and sole fresh-calloc caller')
    need(source.count(b'qq=calloc(') == 1 and source.count(b'pthread_create(') == 1,
         'startup allocation/thread creation boundary differs')
    need(source.index(b'int main(void)') < source.index(CALLER) < source.index(b'pthread_create('),
         'startup clear must precede all worker creation')
    need(source.count(b'typedef uint64_t W;') == 1 and
         source.count(b'typedef struct{atomic_flag zN;W aT,U;}Z;') == 1,
         'zero-initialized unsigned TT field contract differs')


def transform_source(source, *, readable):
    need(type(readable) is bytes and sha(readable) == READABLE,
         'exact canonical A readable source required before startup stage')
    need(type(source) is bytes and len(source) == 9391 and sha(source) == INPUT_SHA256,
         'exact post-capture A4727 shipping source required')
    startup_context(source)
    need(source[OFFSET:END] == BEFORE and source.count(BEFORE) == 1,
         'sole startup clear literal region differs')
    candidate = source[:OFFSET] + AFTER + source[END:]
    need(candidate[OFFSET:OFFSET+len(AFTER)] == AFTER and candidate.count(AFTER) == 1,
         'startup output region differs')
    inverse = candidate[:OFFSET] + BEFORE + candidate[OFFSET+len(AFTER):]
    complement = source[:OFFSET] + source[END:]
    need(inverse == source and len(candidate) == 9370 and sha(candidate) == OUTPUT_SHA256,
         'startup exact output or inverse differs')
    need(len(complement) == COMPLEMENT_BYTES and sha(complement) == COMPLEMENT_SHA256,
         'startup protected source complement differs')
    startup_context(candidate)
    need(AFTER.count(b'atomic_flag_clear(&qq[i].zN);') == 1,
         'explicit per-entry atomic_flag initialization must remain')
    return candidate, {
        'family': 'A', 'stage': 'shipping-after-capture-only',
        'input_bytes': 9391, 'input_sha256': INPUT_SHA256,
        'output_bytes': 9370, 'output_sha256': OUTPUT_SHA256,
        'literal_regions': 1, 'old_start': OFFSET, 'old_end': END,
        'new_end': OFFSET+len(AFTER), 'exact_inverse': True,
        'protected_complement_bytes': COMPLEMENT_BYTES,
        'protected_complement_sha256': COMPLEMENT_SHA256,
        'startup_definition_plus_sole_call_count': 2,
        'fresh_calloc_before_workers': True, 'reset_consumer_admitted': False,
        'unsigned_uint64_zero_fields': True, 'atomic_flag_clear_retained': True,
        'new_native_identity': True, 'DEV_not_transformed': True,
        'external_evidence_is_not_generation_input': True,
    }
