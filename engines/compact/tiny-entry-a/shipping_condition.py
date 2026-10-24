"""Pure final A condition-object sharing and guarded literal adapter.

Current broadcast3/signal0 is retained. All waits use qj and their original
epoch/quitting or pending while predicate. Final startup/completion broadcast
wakes the controller and idle workers; output flush stays before pending-zero
notification under qj. Extra wakeups/rechecks/mutex contention/timing and native
storage/address may differ. Partial creation remains a source argument only.
Canonical/DEV bypass this stage. No evidence/artifact/parser/codec is read.
"""
import hashlib

BEFORE=(8914,'5319dd376e8e7fe6c03c6b40f6fc81b571902d75a663148ffbae00b615059c18')
AFTER=(8886,'d4132c23d226fa5490c5f213b3954ba6a9ce6f3f5f1a5594877a4d910685fe96')
EDITS=((6147, 6147, b'static pthread_cond_t qb=PTHREAD_COND_INITIALIZER,qf=PTHREAD_COND_INITIALIZER;', b'static pthread_cond_t qb=PTHREAD_COND_INITIALIZER;'), (6936, 6908, b'qf', b'qb'), (7197, 7169, b'qf', b'qb'))
GAPS=((0, 0, 6147, '6323011ccf5eb6569f85f0040c6babf7aea382e183250ae61d89265dc1af8d46'), (6225, 6197, 711, '2521e63477abce0f6976ff6bd9d49b8f00982515d60e1456cf2a620713c4f701'), (6938, 6910, 259, 'fa28dcd52d65496d4f2a7d6162d84bcf6614ccc3a78b05663687a09a86e61aca'), (7199, 7171, 1715, '690ff8b346bca4a7993054e4af075003299487ce1f389e9e8884fa6d9c412ec1'))
OLD_SINGLE=(8922,'6a302f1649be794a902cc58477e78782addf2315f2ca408f79de05fb6d978258')
OLD_DOUBLE=(8922,'86bf50499d1daccf38ffd8551594ac70f2abf0104379e4fa1995abfe295d0376')
NEW_SINGLE=(8894, '957d4e1848186f23a7646fa5394a6ee7e32654d24d514c4f49a9d5f5c6e81280')
NEW_DOUBLE=(8894, '5db2c92e7c3f9d1f1e89dec4c9bfae0178cfcaa7d291feaeafbe137823ae592d')

def _pin(raw):return len(raw),hashlib.sha256(raw).hexdigest()
def _need(ok,message):
    if not ok:raise ValueError(message)

def _forward(source):
    _need(type(source)is bytes and _pin(source)==BEFORE,'fixed A named source required')
    candidate=source
    for old_at,new_at,old,new in reversed(EDITS):
        _need(source[old_at:old_at+len(old)]==old,'A condition input anchor differs')
        candidate=candidate[:old_at]+new+candidate[old_at+len(old):]
    _need(_pin(candidate)==AFTER,'fixed A one-condition source differs')
    return candidate

def _inverse(candidate):
    _need(type(candidate)is bytes and _pin(candidate)==AFTER,'fixed A condition result required')
    source=candidate
    for old_at,new_at,old,new in reversed(EDITS):
        _need(candidate[new_at:new_at+len(new)]==new,'A condition output anchor differs')
        source=source[:new_at]+old+source[new_at+len(new):]
    _need(_pin(source)==BEFORE,'A condition full inverse differs')
    return source

def transform_source(source):
    candidate=_forward(source)
    _need(_inverse(candidate)==source,'A condition source inverse differs')
    for old_at,new_at,length,digest in GAPS:
        old=source[old_at:old_at+length];new=candidate[new_at:new_at+length]
        _need(old==new and hashlib.sha256(old).hexdigest()==digest,'A condition protected gap differs')
    return candidate,{'input_bytes':BEFORE[0],'input_sha256':BEFORE[1],
        'output_bytes':AFTER[0],'output_sha256':AFTER[1],'literal_regions':3,
        'protected_gaps':4,'full_inverse':True,'raw_source_delta':-28,
        'broadcast_sites':3,'signal_sites':0,'predicate_wait_sites':2,
        'same_mutex_and_original_while_predicates':True,
        'startup_and_completion_only_final_pending_zero_notify':True,
        'output_flush_before_completion_notify':True,
        'extra_wakes_contention_timing_native_equivalence_claimed':False,
        'canonical_DEV_search_learners_TT_resource_policy_changed':False,'external_reads':0}

def transform_literal(expression,previous):
    _need(type(expression)is str and _pin(expression.encode())==NEW_SINGLE,'fixed new A raw-single literal required')
    _need(expression[:5]=='br'+chr(39)*3 and expression[-3:]==chr(39)*3,'A input raw-single delimiter differs')
    original=expression[:5]+_inverse(expression[5:-3].encode()).decode()+expression[-3:]
    _need(_pin(original.encode())==OLD_SINGLE,'A original names literal preimage differs')
    guarded=previous(original)
    _need(type(guarded)is str and _pin(guarded.encode())==OLD_DOUBLE,'existing A names literal guard differs')
    _need(guarded[:5]=='br'+chr(34)*3 and guarded[-3:]==chr(34)*3,'A guarded raw-double delimiter differs')
    selected=guarded[:5]+_forward(guarded[5:-3].encode()).decode()+guarded[-3:]
    _need(_pin(selected.encode())==NEW_DOUBLE,'fixed new A raw-double literal differs')
    return selected
