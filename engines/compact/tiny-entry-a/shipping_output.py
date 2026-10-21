"""Pure final A fixed-two-worker result selection and individual stdio locks.

The complete-depth strict-greater comparison keeps worker0 on every tie.
The callback still holds qj through printf and fflush. Removing the outer
stdout lock permits main puts/fflush between those two calls: flush grouping,
visibility time, lock contention and scheduling are not trace-equivalent.
Canonical/DEV bypass this stage; old condition/names literal guards are reused.
No external file, artifact, parser, compiler, resource or codec is an input.
"""
import hashlib

BEFORE=(8886, 'd4132c23d226fa5490c5f213b3954ba6a9ce6f3f5f1a5594877a4d910685fe96')
AFTER=(8821, 'c8efc687c503e9872e004431af9fd07c07867ebb19a996fb9c4c0f4d6508f529')
EDITS=((6611, 6611, b'flockfile(stdout);', b''), (6629, 6611, b'ai*w=qr;for(int i=1;i<2;i++)if(qr[i].C>w->C)w=qr+i;', b'ai*w=qr+(qr[1].C>qr->C);'), (6770, 6725, b'funlockfile(stdout);', b''))
GAPS=((0, 0, 6611, 'b1d0fd95eebc21fea962a2e44c9333c17671b06f857509c8e0bb2cafc32db540'), (6629, 6611, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (6680, 6635, 90, '5a4cc303eaa33dc6e64a8b9bd15b7e587cdc49a59d42d849add9909b1c645d1b'), (6790, 6725, 2096, '39a9f84a27a3245a62a8d011e4c8abc3fa5510ad294e72e7a3b1e27129e238e8'))
OLD_SINGLE=(8894,'957d4e1848186f23a7646fa5394a6ee7e32654d24d514c4f49a9d5f5c6e81280')
OLD_DOUBLE=(8894,'5db2c92e7c3f9d1f1e89dec4c9bfae0178cfcaa7d291feaeafbe137823ae592d')
NEW_SINGLE=(8829,'d32ece21d8fa03174186718092b18a16a46640f6a2c456cf26a7d194b528ed47')
NEW_DOUBLE=(8829,'4bb7e888ed3797e0183841ce3eaae475de837fa079532e2f8aff7c55c2c297bc')

def _pin(raw):return len(raw),hashlib.sha256(raw).hexdigest()
def _need(ok,message):
    if not ok:raise ValueError(message)

def _forward(source):
    _need(type(source)is bytes and _pin(source)==BEFORE,'fixed A one-condition source required')
    candidate=source
    for old_at,new_at,old,new in reversed(EDITS):
        _need(source[old_at:old_at+len(old)]==old,'A output input anchor differs')
        candidate=candidate[:old_at]+new+candidate[old_at+len(old):]
    _need(_pin(candidate)==AFTER,'fixed A output source differs')
    return candidate

def _inverse(candidate):
    _need(type(candidate)is bytes and _pin(candidate)==AFTER,'fixed A output result required')
    source=candidate
    for old_at,new_at,old,new in reversed(EDITS):
        _need(candidate[new_at:new_at+len(new)]==new,'A output result anchor differs')
        source=source[:new_at]+old+source[new_at+len(new):]
    _need(_pin(source)==BEFORE,'A output full inverse differs')
    return source

def transform_source(source):
    candidate=_forward(source)
    _need(_inverse(candidate)==source,'A output source inverse differs')
    for old_at,new_at,length,digest in GAPS:
        old=source[old_at:old_at+length];new=candidate[new_at:new_at+length]
        _need(old==new and hashlib.sha256(old).hexdigest()==digest,'A output protected gap differs')
    return candidate,{'input_bytes':BEFORE[0],'input_sha256':BEFORE[1],
        'output_bytes':AFTER[0],'output_sha256':AFTER[1],
        'literal_regions':3,'protected_gaps':4,'protected_complement_bytes':8797,
        'full_inverse':True,'raw_source_delta':-65,'workers':2,
        'completed_depth_strict_greater_tie_worker0':True,
        'callback_holds_qj_through_printf_and_fflush':True,
        'single_bestmove_printf_and_following_fflush_retained':True,
        'main_stdio_may_interpose_between_worker_printf_and_fflush':True,
        'flush_grouping_visibility_contention_scheduling_trace_equivalent':False,
        'native_whole_identity_claimed':False,
        'canonical_DEV_rules_search_learners_TT_resources_changed':False,
        'external_reads':0}

def transform_literal(expression,previous):
    _need(type(expression)is str and _pin(expression.encode())==NEW_SINGLE,'fixed new A output raw-single literal required')
    _need(expression[:5]=='br'+chr(39)*3 and expression[-3:]==chr(39)*3,'A output raw-single delimiter differs')
    original=expression[:5]+_inverse(expression[5:-3].encode()).decode()+expression[-3:]
    _need(_pin(original.encode())==OLD_SINGLE,'A output previous literal preimage differs')
    guarded=previous(original)
    _need(type(guarded)is str and _pin(guarded.encode())==OLD_DOUBLE,'existing A condition/names literal guards differ')
    _need(guarded[:5]=='br'+chr(34)*3 and guarded[-3:]==chr(34)*3,'A output guarded raw-double delimiter differs')
    selected=guarded[:5]+_forward(guarded[5:-3].encode()).decode()+guarded[-3:]
    _need(_pin(selected.encode())==NEW_DOUBLE,'fixed A output raw-double literal differs')
    return selected
