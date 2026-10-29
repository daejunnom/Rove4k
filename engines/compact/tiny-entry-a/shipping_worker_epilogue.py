"""Fixed late A shipping worker startup/completion epilogue sharing.

Canonical and DEV keep their existing worker function. This changes private
startup wake scheduling: only the final pending-zero arrival broadcasts. Job
completion/result/drain guarantees retain their source contract. No external
report, generated source or runtime receipt is a regeneration input.
"""
import hashlib

INPUT=(8987,'4fd5231ace3db9f7d8aca8c2e26871895905cd3e77cb38e4b41117bdca4f31d8')
OUTPUT=(8965,'6230471043c6259016908792bc4b8ad58cf089503e7195ce8a4b6cc6d9886533')
OFFSET=6870
BEFORE=b'static void*A(void*p){ai*w=p;unsigned a=0;pthread_mutex_lock(&qj);--qk;pthread_cond_broadcast(&qf);for(;;){while(a==qd&&!qm)pthread_cond_wait(&qb,&qj);if(qm)break;a=qd;pthread_mutex_unlock(&qj);C(w,&ql);pthread_mutex_lock(&qj);if(!--qk)x(),pthread_cond_broadcast(&qf);}pthread_mutex_unlock(&qj);return NULL;}'
AFTER=b'static void*A(void*p){ai*w=0;unsigned a=0;pthread_mutex_lock(&qj);for(;;){if(!--qk){if(w)x();pthread_cond_broadcast(&qf);}while(a==qd&&!qm)pthread_cond_wait(&qb,&qj);if(qm)break;w=p;a=qd;pthread_mutex_unlock(&qj);C(w,&ql);pthread_mutex_lock(&qj);}pthread_mutex_unlock(&qj);return NULL;}'
PREFIX='87c001ca53fbed0c722b33590361d83e1b48c75e1023e85c1ffe0ccd1827534d'
SUFFIX='73c651339de838735985cb069278b2d961572982b7d225241a1bb5e896ef0ad4'

def _sha(data):return hashlib.sha256(data).hexdigest()

def transform_source(source):
    if type(source) is not bytes or (len(source),_sha(source))!=INPUT:
        raise ValueError('exact A cached-evaluation shipping source required')
    if source.count(BEFORE)!=1 or source[OFFSET:OFFSET+len(BEFORE)]!=BEFORE:
        raise ValueError('A worker epilogue source role differs')
    prefix=source[:OFFSET];suffix=source[OFFSET+len(BEFORE):]
    if _sha(prefix)!=PREFIX or len(suffix)!=1809 or _sha(suffix)!=SUFFIX:
        raise ValueError('A worker epilogue protected complement differs')
    result=prefix+AFTER+suffix
    if (len(result),_sha(result))!=OUTPUT:
        raise ValueError('A worker epilogue result differs')
    if result[:OFFSET]+BEFORE+result[OFFSET+len(AFTER):]!=source:
        raise ValueError('A worker epilogue full inverse differs')
    return result,{'stage':'A-shipping-shared-worker-epilogue',
        'input_bytes':INPUT[0],'input_sha256':INPUT[1],
        'output_bytes':OUTPUT[0],'output_sha256':OUTPUT[1],
        'literal_regions':1,'protected_gaps':2,'full_inverse':True,
        'startup_finished_broadcasts_old_new':[2,1],
        'startup_marker':'local Worker pointer null until first dispatch',
        'epoch_wrap_independent_marker':True,'shared_state_layout_unchanged':True,
        'job_result_and_drain_contract_preserved':True,
        'native_identity_changed':True,'canonical_DEV_unchanged':True,
        'source_scope':'nonnull static worker entry; private startup scheduling changes',
        'external_reads':0}
