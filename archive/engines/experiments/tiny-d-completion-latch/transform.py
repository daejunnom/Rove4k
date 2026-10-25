"""One exact runtime-only pending-latch transformation; no alternative variants."""
import hashlib
import re

CONTROL_SHA = '82c62b57e500918827721553d67d9e23073c6cb5ca79dc22cdb8e38ab15f8e63'
CANDIDATE_SHA = '5b20d4e60d60b5edfb4b7b5a15217346098f0bd9ccdd155a7369c90743e81ed1'
CHANGES = (
    ('atomic-storage',
     b'static atomic_int epoch,pending,completed,ready,quitting,ids[WORKERS];',
     b'static atomic_int epoch,pending,quitting,ids[WORKERS];'),
    ('startup-arrival',
     b'    atomic_fetch_add_explicit(&ready,1,memory_order_release);wake(&ready);',
     b'    atomic_fetch_sub_explicit(&pending,1,memory_order_release);wake(&pending);'),
    ('finish-output-reservation',
     b'        if(atomic_fetch_sub_explicit(&pending,1,memory_order_acq_rel)==1){\n'
     b'            result();atomic_store_explicit(&completed,seen,memory_order_release);wake(&completed);\n',
     b'        if(atomic_fetch_sub_explicit(&pending,1,memory_order_acq_rel)==2){\n'
     b'            result();atomic_store_explicit(&pending,0,memory_order_release);wake(&pending);\n'),
    ('zero-only-wait',
     b'/* Completion is distinct from the last search decrement: a new command must\n'
     b' * not change workers/position while final bestmove publication is in flight. */\n'
     b'static void wait(void){\n'
     b'    atomic_store_explicit(&stopped,1,memory_order_relaxed);\n'
     b'    int target=atomic_load_explicit(&epoch,memory_order_relaxed),done;\n'
     b'    while((done=atomic_load_explicit(&completed,memory_order_acquire))!=target)futex_wait(&completed,done,1);\n'
     b'}\n',
     b'/* pending counts startup arrivals, then workers plus an output reservation.\n'
     b' * Only zero releases storage after the complete bestmove has been written. */\n'
     b'static void wait(void){\n'
     b'    atomic_store_explicit(&stopped,1,memory_order_relaxed);\n'
     b'    int count;while((count=atomic_load_explicit(&pending,memory_order_acquire)))futex_wait(&pending,count,1);\n'
     b'}\n'),
    ('go-reservation',
     b'    atomic_store_explicit(&pending,WORKERS,memory_order_relaxed);atomic_fetch_add_explicit(&epoch,1,memory_order_release);wake(&epoch);',
     b'    atomic_store_explicit(&pending,WORKERS+1,memory_order_relaxed);atomic_fetch_add_explicit(&epoch,1,memory_order_release);wake(&epoch);'),
    ('runtime-startup-initialization',
     b'    for(;created<WORKERS;created++){\n',
     b'    atomic_store_explicit(&pending,WORKERS,memory_order_relaxed);\n'
     b'    for(;created<WORKERS;created++){\n'),
    ('startup-zero-barrier',
     b'    int count;while((count=atomic_load_explicit(&ready,memory_order_acquire))<WORKERS)futex_wait(&ready,count,1);\n'
     b'    for(;;){\n',
     b'    wait();\n'
     b'    for(;;){\n'),
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def apply(control):
    if sha(control) != CONTROL_SHA or b'\r' in control:
        raise ValueError('exact LF control runtime required')
    candidate = control
    for name, before, after in CHANGES:
        if candidate.count(before) != 1:
            raise ValueError('single exact runtime boundary required: ' + name)
        candidate = candidate.replace(before, after)
    inverse = candidate
    for name, before, after in reversed(CHANGES):
        if inverse.count(after) != 1:
            raise ValueError('single inverse runtime boundary required: ' + name)
        inverse = inverse.replace(after, before)
    if inverse != control:
        raise ValueError('runtime complement changed')
    if re.search(rb'\b(?:ready|completed)\b', candidate):
        raise ValueError('separate ready/completed consumer remains')
    if sha(candidate) != CANDIDATE_SHA:
        raise ValueError('one fixed candidate runtime identity required')
    masked = control
    for index, (_, before, _) in enumerate(CHANGES):
        masked = masked.replace(before, ('@@LATCH_%d@@' % index).encode())
    return candidate, {'control_runtime_bytes': len(control), 'candidate_runtime_bytes': len(candidate),
        'runtime_source_byte_change': len(candidate) - len(control), 'control_runtime_sha256': sha(control),
        'candidate_runtime_sha256': sha(candidate), 'exact_change_names': [name for name, _, _ in CHANGES],
        'inverse_complement_exact': True, 'masked_complement_sha256': sha(masked),
        'startup_private_stopped_change': 'startup success now calls wait and sets stopped1; GO resets0 before epoch publication',
        'partial_clone_failure_bypasses_startup_wait': True,
        'output_reservation': 'pending1 until result returns; only pending0 release is completion',
        'candidate_variants': 1}
