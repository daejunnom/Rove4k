"""Pure fixed full-F job-local MTD seed/witness stage. No IO/products."""
import ast,hashlib
INPUT=(7885, '47419319e3bfa0eb0e43a9ced1705c7f6283218af8a92157bda47c49ac2dd852')
OUTPUT=(7863, '0ba7f01ae4df9a306a5dc3e790a451f272657d2411f66f972ef394d7170cfc5a')
EDITS=((482, 482, b'S a,b,c;Y d;', b'S a,b;Y d;'), (4858, 4856, b'w->e=0;w->c=0;w->d=0;', b'w->e=0;S q=0;Y b=w->d=0;'), (4900, 4901, b'S d=-30000,f=30000,q=w->c;Y b=w->d;', b'S d=-30000,f=30000;'), (5174, 5159, b'w->d=b;w->c=q;w->b=a;', b'w->d=b;w->b=a;'))
GAPS=((0, 0, 482, '9a11b6aa4f8e5d9c244ddc1d34dd761a0bf0500c832be3e2ee3d59d7524134f5'), (494, 492, 4364, '8d5976e71ce7e3025fb2a10dee34c156110a7300cb54a997bde1d5a1df1db2b1'), (4879, 4880, 21, '4a8c17666275c52683582707eca6c67ce4e44d1b2facc0670dfbfaebba476327'), (4935, 4920, 239, 'f5eca5e244549a2bb3e7dfce2a233cebb3c7395d1fa12826f7507cbbb513ba9f'), (5195, 5173, 2690, '92603a80bca6403da9bdea62a582950f0e311860d7cab9cf9233bcf43f7d00e7'))
def _pin(b):return len(b),hashlib.sha256(b).hexdigest()
def _rewrite(source,inverse=False):
 if type(source)is not bytes or _pin(source)!=(OUTPUT if inverse else INPUT):raise ValueError('fixed MTD local-state input differs')
 result=source
 for a,b,old,new in reversed(EDITS):
  at,old,new=(b,new,old)if inverse else(a,old,new)
  if source[at:at+len(old)]!=old:raise ValueError('fixed MTD state span differs')
  result=result[:at]+new+result[at+len(old):]
 if _pin(result)!=(INPUT if inverse else OUTPUT):raise ValueError('fixed MTD local-state output differs')
 return result
def restore_source(source):return _rewrite(source,True)
def transform_source(source):
 result=_rewrite(source)
 if restore_source(result)!=source:raise ValueError('full MTD local-state inverse differs')
 for a,b,n,h in GAPS:
  if source[a:a+n]!=result[b:b+n]or _pin(source[a:a+n])!=(n,h):raise ValueError('MTD local-state gap differs')
 return result,dict(stage='late-full-F-job-local-MTD-seed-and-witness',input=INPUT,output=OUTPUT,raw_delta=-22,spans=4,protected_gaps=5,full_inverse=True,layout_native_identity_claimed=False,runtime_qualified=False)
def source_literal(source,previous):
 original=restore_source(source);expression,kind=previous(original)
 if ast.literal_eval(expression)!=original:raise ValueError('actual prior MTD literal differs')
 old,new=original.decode('ascii'),source.decode('ascii')
 if expression.count(old)!=1:raise ValueError('one MTD literal required')
 result=expression.replace(old,new,1)
 if result.replace(new,old,1)!=expression or ast.literal_eval(result)!=source:raise ValueError('MTD literal inverse differs')
 return result,kind
