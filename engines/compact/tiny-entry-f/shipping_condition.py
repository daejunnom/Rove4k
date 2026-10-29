"""Pure late Ffull condition sharing, after the digit guard.

F startup decrements once outside the worker loop and broadcasts every arrival.
All four notifications remain broadcasts; both original epoch/quitting and
pending while predicates use qj. Last-completion y/strict-depth selection and
flush precede broadcast under qj. Extra wake/recheck/contention/timing and native
storage differ. Partial-create/fault paths remain source arguments only.
Actual optional selected C, canonical/DEV and F8 pre-name source bypass this;
optional separate full_reference calls it explicitly. No external input is read.
"""
import hashlib

BEFORE=(8497,'08532c38268ecf4691890a13529d09227a76eadb039813d3bb6f886170966954')
AFTER=(8469,'350fdabcac9809267bbb47a7f3a76e6029933e11455322e6306f705fb6554136')
EDITS=((5817, 5817, b'static pthread_cond_t qb=PTHREAD_COND_INITIALIZER,qf=PTHREAD_COND_INITIALIZER;', b'static pthread_cond_t qb=PTHREAD_COND_INITIALIZER;'), (6503, 6475, b'qf', b'qb'), (6672, 6644, b'qf', b'qb'), (6808, 6780, b'qf', b'qb'))
GAPS=((0, 0, 5817, '77b8f19f71f6956ca0770b882214bdcf7dd1cfc266449ec2c1f94510f20f978b'), (5895, 5867, 608, 'ed0606b8a8c1a496803f07b6648652fbe85e8397ccd0d5906682175aecafa161'), (6505, 6477, 167, '8f26266b79b3f94570ad185825bcd81e6c934b8b5f9796f95eff77ddacf8ba11'), (6674, 6646, 134, '461b56029aaed6763a14548f934c92e380627a1f4bedc071a9ab6be62e3d1d69'), (6810, 6782, 1687, 'fa5b5813d18075bc5e9bd4b0163d370a348a74e11a3f9e9edaf37f99dd6acd89'))

def _pin(raw):return len(raw),hashlib.sha256(raw).hexdigest()
def _need(ok,message):
    if not ok:raise ValueError(message)

def transform_source(source):
    _need(type(source)is bytes and _pin(source)==BEFORE,'fixed F full post-digit source required')
    candidate=source
    for old_at,new_at,old,new in reversed(EDITS):
        _need(source[old_at:old_at+len(old)]==old,'F condition input anchor differs')
        candidate=candidate[:old_at]+new+candidate[old_at+len(old):]
    _need(_pin(candidate)==AFTER,'fixed F one-condition source differs')
    inverse=candidate
    for old_at,new_at,old,new in reversed(EDITS):
        _need(candidate[new_at:new_at+len(new)]==new,'F condition output anchor differs')
        inverse=inverse[:new_at]+old+inverse[new_at+len(new):]
    _need(inverse==source,'F condition full inverse differs')
    for old_at,new_at,length,digest in GAPS:
        old=source[old_at:old_at+length];new=candidate[new_at:new_at+length]
        _need(old==new and hashlib.sha256(old).hexdigest()==digest,'F condition protected gap differs')
    return candidate,{'stage':'F full-only after digit guard or explicit separate full reference',
        'input_bytes':BEFORE[0],'input_sha256':BEFORE[1],
        'output_bytes':AFTER[0],'output_sha256':AFTER[1],
        'literal_regions':4,'protected_gaps':5,'full_inverse':True,'raw_source_delta':-28,
        'startup_each_arrival_broadcast':True,'broadcast_sites':4,'signal_sites':0,'wait_sites':2,
        'original_mutex_while_epoch_pending_and_created_join_preserved':True,
        'strict_depth_tie0_result_flush_before_completion_notify':True,
        'extra_wakes_contention_timing_native_equivalence_claimed':False,
        'canonical_DEV_F8_actual_optional_selected_changed':False,'external_reads':0}
