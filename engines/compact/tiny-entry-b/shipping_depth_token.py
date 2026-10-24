"""Fixed B completed-depth job token after the actual int-alias/EP stages.

This is a state-protocol representation change, not arbitrary-entry equivalence.
Actual startup already folds readiness into pending2/null-w; there is no qn.
GO drains first, then publishes both -1 tokens under qj; each stable owner claims
0 under qj before think. Completed depths 1..126 and result/flush/drain fences
stay unchanged. Direct private think callers must seed depth0. Canonical/DEV,
singular/PVS/exclusion/SEE/TT/learners/model and partial-created joins are outside
the six edited roles. No files, reports, compiler or runtime are inputs here.
"""
import ast
import hashlib

INPUT=(9759,'1bc4d0f68300913c8bdf4edbe55b8d79082f9ac198b53619ab5d42169e094e87')
OUTPUT=(9744,'4b3412e3dddbe4cc9b40172be66d577aa998dc65e4ffa5876827f6b92654c5a8')
EDITS=(
 (6768,6768,b'w->zB=0;',b''),
 (7077,7069,b'static unsigned qd;',b''),
 (7636,7609,b'zd*w=0;unsigned a=0;',b'zd*w=0,*a=p;'),
 (7736,7701,b'while(a==qd&&!qm)',b'while(a->zB>=0&&!qm)'),
 (7792,7760,b'w=p;a=qd;',b'w=a;w->zB=0;'),
 (8866,8837,b'qk=2;qd++;',b'qk=2;qr->zB=qr[1].zB=-1;'),
)
GAPS=(
 (0,0,6768,'fc4b33f3e0d3c3146df820a5e2ec6abc90e11710543846b819455e6294d03be9'),
 (6776,6768,301,'c1c9c4b7f9ecb62f82ced59c31e54eb1fbfeeea5fdddb8c8ed60e915e0095629'),
 (7096,7069,540,'7c96d3f6f0ab3e0617b3b5eec7d4da94b5db081ad2ab170de35844e547875067'),
 (7656,7621,80,'16ed8c7241e6cadbb0edda73e1c0c64e02cb141707fd5a2871395752706ac94f'),
 (7753,7721,39,'2db75265c2eb7155de557c4303b1197fc74ab4768a44e348bc6a26c01633116a'),
 (7801,7772,1065,'0288a95d4222e37e86454444af42e93f1bdb46e826b0923543ba2950cba513d2'),
 (8876,8861,883,'780e953920eb8bc75c50ad1df984228d7d38e39db48201d9d085f850f4122f89'),
)
BOOT_INPUT=(11804,'2c9b90d862a88bb3bd20d7f6e42d2a8a7a463121ee07675f9ef6fac7c9b1c8c2')
BOOT_OUTPUT=(11789,'efc80af6e4d6f1dcd2d93a3b05831a7d60b73362f9aff03785bdff3ea6386604')
METADATA={'family':'B','stage':'completed-depth-jobtoken-after-current-EP-int-alias',
 'input_bytes':INPUT[0],'input_sha256':INPUT[1],'output_bytes':OUTPUT[0],'output_sha256':OUTPUT[1],
 'raw_delta':-15,'owned_roles':6,'protected_gaps':7,'full_inverse':True,
 'job_token':'signed zB -1 published/unclaimed,0 claimed/no completed depth,1..126 completed',
 'actual_startup':'pending qk=2/null w; separate qn already absent before this stage',
 'stable_owner':'a=p; own zB predicate and claim0 under qj before unique s->i(w,&ql)',
 'GO':'U drain then existing clock/deadline then qj pending2 and both depth-1 publication',
 'fences':'last pending0 result/own fflush precedes broadcast; producer drains before reuse',
 'partial_create':'unchanged goto shutdown bypasses startup wait/ending drain; actual-created joins',
 'direct_private_think':'caller must seed depth0; arbitrary-entry equivalence not claimed',
 'singular_PVS_exclusion_SEE_TT_learners_eval_main_unchanged':True,
 'canonical_DEV_changed':False,'native_layout_identity_claimed':False,'runtime_claimed':False,'external_reads':0}

def pin(data):return len(data),hashlib.sha256(data).hexdigest()
def need(value,message):
 if not value:raise ValueError('B depth token: '+message)
def _forward(source):
 need(type(source)is bytes and pin(source)==INPUT,'exact current EP/int-alias source required')
 out=source
 for a,b,old,new in reversed(EDITS):
  need(source[a:a+len(old)]==old and source.count(old)==1,'owned source role differs')
  out=out[:a]+new+out[a+len(old):]
 need(pin(out)==OUTPUT,'candidate source differs')
 for a,b,n,digest in GAPS:
  need(source[a:a+n]==out[b:b+n] and pin(source[a:a+n])==(n,digest),'protected gap differs')
 need(b'qn'not in source and b'qn'not in out and b'qd'not in out,'actual startup/epoch role differs')
 return out
def restore_source(source):
 need(type(source)is bytes and pin(source)==OUTPUT,'fixed final token source required')
 out=source
 for a,b,old,new in reversed(EDITS):
  need(source[b:b+len(new)]==new,'inverse owned role differs')
  out=out[:b]+old+out[b+len(new):]
 need(pin(out)==INPUT and _forward(out)==source,'complete inverse differs')
 return out
def transform_source(source):
 out=_forward(source)
 need(restore_source(out)==source,'full forward/inverse differs')
 return out,dict(METADATA)
def transform_bootstrap(previous,*,source):
 baseline=restore_source(source)
 need(type(previous)is bytes and pin(previous)==BOOT_INPUT,'actual corrected-owner previous bootstrap required')
 need(previous.count(baseline)==1,'actual previous source literal must be unique')
 result=previous.replace(baseline,source,1)
 need(pin(result)==BOOT_OUTPUT and result.replace(source,baseline,1)==previous,'bootstrap inverse/output differs')
 oldtree=ast.parse(previous);newtree=ast.parse(result)
 old=[n for n in ast.walk(oldtree)if isinstance(n,ast.Constant)and n.value==baseline]
 new=[n for n in ast.walk(newtree)if isinstance(n,ast.Constant)and n.value==source]
 need(len(old)==len(new)==1,'one actual compiler-source bytes constant required')
 new[0].value=baseline
 need(ast.dump(oldtree,include_attributes=False)==ast.dump(newtree,include_attributes=False),'outside source AST differs')
 return result,{'stage':'B-depth-token-literal-after-actual-old-guards-and-corrected-owner',
  'input_bytes':BOOT_INPUT[0],'input_sha256':BOOT_INPUT[1],'output_bytes':BOOT_OUTPUT[0],'output_sha256':BOOT_OUTPUT[1],
  'existing_fixed_source_generation_chain_precedes_new_stage':True,
  'generic_previous_literal_envelope_consumed_by_caller':True,
  'previous_B_package_has_no_fixed_literal_stage_guard':True,
  'corrected_compiler_owner_already_applied':True,'outside_source_literal_unchanged':True,
  'AST_only_source_constant_change':True,'full_inverse':True,'external_reads':0}
