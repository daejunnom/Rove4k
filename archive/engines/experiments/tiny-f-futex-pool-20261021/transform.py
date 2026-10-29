"""One exact F4720 shipping-only pthread/atomic-epoch private-futex pool.

No preprocessing, naming pass, resource variation or normal-source mutation.
The entire supplied current shipping source is bound before six literal edits.
"""
import hashlib


INPUT_BYTES = 9464
INPUT_SHA256 = 'd942731c54f82da8dfa1aa5fedcc6328b56b32fe0ab527b5396847ceea541f26'

PAIRS = (
    ('Linux-ABI-and-errors',
     b'#include <limits.h>\n',
     b'#include <limits.h>\n#include <errno.h>\n'
     b'#if !defined(__linux__)||!defined(__x86_64__)\n#error Linux_x86_64_required\n#endif\n'
     b'_Static_assert(sizeof(long)==8&&sizeof(atomic_uint)==4&&sizeof(atomic_int)==4&&'
     b'_Alignof(atomic_uint)>=4&&_Alignof(atomic_int)>=4&&ATOMIC_INT_LOCK_FREE==2,"futex ABI");'
     b'extern long syscall(long,...);\n'),
    ('pool-state-and-syscall',
     b'static pthread_mutex_t qj=PTHREAD_MUTEX_INITIALIZER;static pthread_cond_t qb=PTHREAD_COND_INITIALIZER,qf=PTHREAD_COND_INITIALIZER;static unsigned qd;static int qk=2,qm;',
     b'static atomic_uint qd;static atomic_int qk=2,qm;'
     b'static void futex(void*p,int operation,unsigned value){'
     b'if(syscall(202L,p,(long)operation,(long)value,0L,0L,0L)<0&&'
     b'(operation!=128||(errno!=EINTR&&errno!=EAGAIN)))_Exit(2);}'),
    ('worker-startup-search-and-output-reservation',
     b'static void*ax(void*p){zc*w=p;unsigned a=0;pthread_mutex_lock(&qj);--qk;pthread_cond_broadcast(&qf);for(;;){while(a==qd&&!qm)pthread_cond_wait(&qb,&qj);if(qm)break;a=qd;pthread_mutex_unlock(&qj);ac(w,&ql);pthread_mutex_lock(&qj);if(!--qk)at(),pthread_cond_broadcast(&qf);}pthread_mutex_unlock(&qj);return NULL;}',
     b'static void*ax(void*p){zc*w=p;unsigned a=0;--qk;futex(&qk,129,INT_MAX);'
     b'for(;;){unsigned job=qd;if(qm)break;if(a==job){futex(&qd,128,a);continue;}'
     b'a=job;ac(w,&ql);if(--qk==1){at();qk=0;futex(&qk,129,INT_MAX);}}return NULL;}'),
    ('wait-and-cancel',
     b'static void ay(void){atomic_store(&qp,1);pthread_mutex_lock(&qj);while(qk)pthread_cond_wait(&qf,&qj);pthread_mutex_unlock(&qj);}',
     b'static void ay(void){atomic_store(&qp,1);int n;while((n=qk))futex(&qk,128,n);}'),
    ('GO-release-publication',
     b'pthread_mutex_lock(&qj);qk=2;qd++;pthread_cond_broadcast(&qb);pthread_mutex_unlock(&qj);',
     b'qk=3;qd++;futex(&qd,129,INT_MAX);'),
    ('quit-and-partial-create-failure-publication',
     b'pthread_mutex_lock(&qj);qm=1;pthread_cond_broadcast(&qb);pthread_mutex_unlock(&qj);',
     b'qm=1;qd++;futex(&qd,129,INT_MAX);'),
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def transform_source(source):
    if type(source) is not bytes or len(source) != INPUT_BYTES or sha(source) != INPUT_SHA256:
        raise ValueError('only the exact current F4720 shipping source is admitted')
    if b'\r' in source:
        raise ValueError('exact LF source required')
    edits = []
    for role, old, new in PAIRS:
        if source.count(old) != 1:
            raise ValueError('fixed current pool region changed: ' + role)
        start = source.index(old)
        edits.append((start, role, old, new))
    edits.sort()
    output = bytearray()
    complement = bytearray()
    cursor = 0
    metadata = []
    for start, role, old, new in edits:
        if start < cursor:
            raise ValueError('overlapping exact pool edits')
        unchanged = source[cursor:start]
        output.extend(unchanged)
        complement.extend(unchanged)
        at = len(output)
        output.extend(new)
        metadata.append({'role': role, 'input_offset': start, 'output_offset': at,
                         'old_bytes': len(old), 'new_bytes': len(new),
                         'old_sha256': sha(old), 'new_sha256': sha(new)})
        cursor = start + len(old)
    output.extend(source[cursor:])
    complement.extend(source[cursor:])
    candidate = bytes(output)
    inverse = candidate
    for row, (_, _, old, new) in reversed(list(zip(metadata, edits))):
        at = row['output_offset']
        if inverse[at:at + len(new)] != new:
            raise ValueError('candidate positional inverse mismatch')
        inverse = inverse[:at] + old + inverse[at + len(new):]
    if inverse != source:
        raise ValueError('candidate did not restore the complete old source')
    for forbidden in (b'pthread_mutex_', b'pthread_cond_'):
        if forbidden in candidate:
            raise ValueError('old synchronization consumer survived')
    for retained in (b'pthread_create', b'pthread_join', b'flockfile(stdout)',
                     b'fflush(stdout)', b'funlockfile(stdout)'):
        if candidate.count(retained) != source.count(retained):
            raise ValueError('retained lifetime/output consumer changed')
    return candidate, {
        'stage': 'F4720-only pthread-create/join plus three SC atomic words and private futex',
        'input': {'bytes': len(source), 'sha256': sha(source)},
        'output': {'bytes': len(candidate), 'sha256': sha(candidate)},
        'edits': metadata, 'inverse_exact': True,
        'unmodified_complement_bytes': len(complement), 'unmodified_complement_sha256': sha(complement),
        'old_pool_replaced_bytes': sum(len(old) for role, old, _ in PAIRS if role != 'Linux-ABI-and-errors'),
        'memory_order': 'C11 sequentially consistent atomic reads/writes/increments/decrements',
        'startup_pending': 2, 'search_pending_including_output_reservation': 3,
        'successful_partial_create_prefix_join_retained': True,
        'ordinary_quit_EOF_join_retained': True,
        'unexpected_futex_failure': '_Exit(2), not a successful-join claim',
        'worker_count': 2, 'total_threads': 3, 'TT_bits': 18, 'PLY': 128,
        'DEV_modified': False, 'normal_sources_modified': False,
    }
