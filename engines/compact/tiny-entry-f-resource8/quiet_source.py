"""Pure fixed v11 input composition; preserve the original six-role helper.

Admit only new F2 quiet7830, invert its declared quiet stage to old7840,
run the unchanged old resource transform to7878, then apply the one local
quiet continuation edit to7868. No fallback, IO, compiler, codec or runtime.
"""
import ast,hashlib
INPUT=(7830,'43bc67816e91077c4cfd182ec6ba44aed7d0223d012cff82f5366ad58da63582')
ANCESTOR_F2=(7840,'67279ef99a5ade0b3b8c66564abc15e4ccd9bead3253ca18e4b88b6d87e14ca1')
ANCESTOR_F8=(7878,'ce54ace72c9c903ea555347ffab4a0bc4635b0c48c70c6c5409ecaa66b657373')
OUTPUT=(7868,'fb18e915ca1236a25c9c2969c8c2b45d8000e2a701aede3490306b6246eb4865')
OFFSET=4683
OLD=b'an(&w->i[g][(p->b[N]+6)],R);'
NEW=b'an(&w->i[g][Q],R);'
GAPS=((4683,'0f8fcff9dac4764be8e47c1351fd2098c44a77fdd0e33fca1b096ae20b303af5'),(3167,'b1ecd2f97367a3e6b544ad458da52a530f951a7e7323cd262e37295e3975176f'))
COMPLEMENT=(7850,'0276fdb43617fde9feb55f5320ad22f775c629293498c7a73bf00b125c0a9849')

def pin(raw):return len(raw),hashlib.sha256(raw).hexdigest()
def require(c,m):
 if not c:raise ValueError(m)
def restore_source(source):
 require(type(source)is bytes and pin(source)==OUTPUT,'fixed F8 quiet output differs')
 require(source[OFFSET:OFFSET+len(NEW)]==NEW and source.count(NEW)==1,'fixed F8 quiet output span differs')
 old=source[:OFFSET]+OLD+source[OFFSET+len(NEW):]
 require(pin(old)==ANCESTOR_F8,'fixed F8 quiet inverse differs')
 return old

def forward_source(source):
 require(type(source)is bytes and pin(source)==ANCESTOR_F8,'fixed F8 ancestor differs')
 prefix,suffix=source[:OFFSET],source[OFFSET+len(OLD):]
 require(source[OFFSET:OFFSET+len(OLD)]==OLD and source.count(OLD)==1 and (pin(prefix),pin(suffix))==GAPS,'fixed F8 quiet span/gaps differ')
 result=prefix+NEW+suffix
 require(pin(result)==OUTPUT and restore_source(result)==source and pin(prefix+suffix)==COMPLEMENT,'fixed F8 quiet output/inverse/complement differs')
 return result,{'stage':'local-F8-quiet-continuation-slot','input':ANCESTOR_F8,'output':OUTPUT,'full_inverse':True,'spans':1,'protected_gaps':GAPS,'whole_protected_complement':COMPLEMENT,'raw_delta':-10,'quiet_order_unchanged':True}

def transform_source(source,*,quiet_input,resource_transform):
 require(type(source)is bytes and pin(source)==INPUT,'only declared quiet7830 incoming source admitted')
 ancestor=quiet_input.restore_source(source)
 require(pin(ancestor)==ANCESTOR_F2,'F2 quiet inverse ancestor differs')
 replay,input_proof=quiet_input.transform_source(ancestor)
 require(replay==source and input_proof['full_inverse'],'F2 quiet forward replay differs')
 old8,legacy=resource_transform(ancestor)
 require(pin(old8)==ANCESTOR_F8 and legacy['full_inverse'] and legacy['spans']==6 and legacy['protected_gaps']==7,'old six-role ancestor proof differs')
 result,local=forward_source(old8)
 # Prove the ancestor resource inverse without changing its implementation.
 undo=restore_source(result)
 for edit in reversed(legacy['edits']):
  at=edit['new_start'];before=edit['new'].encode();after=edit['old'].encode()
  require(undo[at:at+len(before)]==before,'ancestor resource inverse span differs')
  undo=undo[:at]+after+undo[at+len(before):]
 require(undo==ancestor and quiet_input.transform_source(undo)[0]==source,'composed full inverse differs')
 # Actual incoming-to-output six roles and complete complementary bytes.
 edits=[];gaps=[];left=right=0
 for edit in legacy['edits']:
  a=edit['old_start']-(10 if edit['old_start']>OFFSET else 0)
  b=edit['new_start']-(10 if edit['new_start']>OFFSET else 0)
  old,new=edit['old'].encode(),edit['new'].encode()
  require(source[a:a+len(old)]==old and result[b:b+len(new)]==new,'outer fixed resource span differs')
  x,y=source[left:a],result[right:b]
  require(x==y,'outer protected gap differs')
  gaps.append({'old_start':left,'new_start':right,'bytes':len(x),'sha256':pin(x)[1]})
  edits.append({'role':edit['role'],'old_start':a,'new_start':b,'old':edit['old'],'new':edit['new']})
  left,right=a+len(old),b+len(new)
 x,y=source[left:],result[right:];require(x==y,'outer protected suffix differs')
 gaps.append({'old_start':left,'new_start':right,'bytes':len(x),'sha256':pin(x)[1]})
 direct=source;back=result
 for edit in reversed(edits):
  a,b=edit['old_start'],edit['new_start'];old,new=edit['old'].encode(),edit['new'].encode()
  direct=direct[:a]+new+direct[a+len(old):];back=back[:b]+old+back[b+len(new):]
 require(direct==result and back==source,'outer direct/full inverse differs')
 complement=b''.join(source[g['old_start']:g['old_start']+g['bytes']] for g in gaps)
 return result,{'stage':'fixed-F8-quiet-input-and-resource-composition','base_stage':'full-after-MTD-state-sole-GO-and-quiet-slot','input':INPUT,'output':OUTPUT,'raw_delta':38,'roles':legacy['roles'],'edits':edits,'spans':6,'protected_gaps':7,'gaps':gaps,'whole_protected_complement':{'bytes':len(complement),'sha256':pin(complement)[1]},'full_inverse':True,'all_gaps_equal':True,'input_quiet_ancestor':{'restored':ANCESTOR_F2,'proof':input_proof},'resource_ancestor':legacy,'resource_ancestor_output':ANCESTOR_F8,'local_quiet':local,'no_old_resource_helper_change':True,'runtime_qualified':False}

def source_literal(source,previous):
 original=restore_source(source);expression,kind=previous(original)
 require(ast.literal_eval(expression)==original,'actual prior F8 literal differs')
 old,new=original.decode('ascii'),source.decode('ascii')
 require(expression.count(old)==1,'one F8 source literal required')
 result=expression.replace(old,new,1)
 require(result.replace(new,old,1)==expression and ast.literal_eval(result)==source,'F8 quiet literal full inverse differs')
 return result,kind
