"""Pure C terminal-loop sharing after the signed-lane reduction.

The initialized production Board/path and own Worker domain is unchanged.
Draw/cap classify before TT; terminal paths skip the entire atomic TT call
and ordinary pruning. The first legal private child returns before root,
path/learner/TT writes. Local ordering reads, private child order/work and
timing may differ. Canonical and DEV bypass this fixed shipping-only stage.
No report, artifact, compiler, parser, codec or runtime input is read.
"""
import hashlib

BEFORE=(9848,'a661656a482be3ee8383443925c7c36114ce802e9d06ffed59f5479f7ccd37b9')
AFTER=(9800,'32861867de077f5d09eb631650b854164cd6f32369a57200337743a88f717103')
EDITS=((4818, 4818, b'if(x||n==PLY-1){za q;for(int i=0;i<X;i++)if(e(p,B[i],&q)){if(!x){atomic_store(&stopped,1);}return 0;}return v?-MATE+n:0;}', b'x|=2*(n==PLY-1);'), (4973, 4868, b'zA=J(zP,0);', b'zA=x?0:J(zP,0);'), (5173, 5072, b'int ye=a<=0&&!v;', b'int ye=!x&&a<=0&&!v;'), (5556, 5459, b'if(!e(p,m,&q))continue;++Y;', b'if(!e(p,m,&q))continue;if(x){if(x==2)atomic_store(&stopped,1);return 0;}++Y;'))
GAPS=((0, 0, 4818, '91d9db5a2a2b6e4a447f6fd8b301c0b587e6763fe6008660fa142a452b049cd7'), (4939, 4834, 34, '87e570ecb99f4aa36a241791ecf31c0e42cc0bb0f860c4aa2ac5a8b8f1d6ca21'), (4984, 4883, 189, 'c08bc392e78c69f118a70ff489ae78c04b39ba428150570924016d67b6cb1950'), (5189, 5092, 367, 'dd5f8c8bb68d68fa756800185d25f175641cea70d8b20eaa54003113cbc20e87'), (5583, 5535, 4265, 'a425c158b8c5c0ced1f77679966f743a9aaff0d265322f35a86ac200d7194305'))

def _pin(raw):return len(raw),hashlib.sha256(raw).hexdigest()
def _need(ok,message):
    if not ok:raise ValueError(message)

def transform_source(source):
    _need(type(source)is bytes and _pin(source)==BEFORE,'fixed after-lane-sum C source required')
    candidate=source
    for old_at,new_at,old,new in reversed(EDITS):
        _need(source[old_at:old_at+len(old)]==old and source.count(old)==1,'C terminal source anchor differs')
        candidate=candidate[:old_at]+new+candidate[old_at+len(old):]
    _need(_pin(candidate)==AFTER,'fixed C shared terminal source differs')
    inverse=candidate
    for old_at,new_at,old,new in reversed(EDITS):
        _need(candidate[new_at:new_at+len(new)]==new,'C terminal output anchor differs')
        inverse=inverse[:new_at]+old+inverse[new_at+len(new):]
    _need(inverse==source,'C terminal full inverse differs')
    for old_at,new_at,length,digest in GAPS:
        old=source[old_at:old_at+length];new=candidate[new_at:new_at+length]
        _need(old==new and hashlib.sha256(old).hexdigest()==digest,'C terminal protected gap differs')
    return candidate,{'stage':'C shipping after signed lane sum','input_bytes':BEFORE[0],
        'input_sha256':BEFORE[1],'output_bytes':AFTER[0],'output_sha256':AFTER[1],
        'literal_regions':4,'protected_gaps':5,'protected_complement_bytes':9673,
        'full_inverse':True,'all_gaps_equal':True,'raw_source_delta':-48,
        'terminal_encoding':{'ordinary':0,'draw':1,'cap_only':2,'draw_and_cap':3},
        'terminal_TT_call_and_pruning':False,'first_legal_returns_before_root_path_learners_TT_writes':True,
        'entry_stop_deadline_claim_policy_unchanged':True,'canonical_DEV_SIMD_weights_unchanged':True,
        'ordering_scratch_child_work_timing_equivalence_claimed':False,
        'production_initialized_Board_ownWorker_domain':True,'external_reads':0}
