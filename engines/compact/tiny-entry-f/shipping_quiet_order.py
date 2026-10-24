"""Pure fixed full-F quiet-order single-caller inline; no IO/products."""
import ast,hashlib
INPUT=(7979, '03fc7a4d8c3d99b1cdd633b47ef1939cb80247e72e0ef1acfbc5bc477155dd27')
OUTPUT=(7905, '04e5472a5970a87ca784a71fa8a6ce483fa728e254ca45bc71e9de638b54bec7')
EDITS=((3630, 3630, b'static S ap(X*w,const I*p,Y m,S a){S d=FROM(m),f=TO(m),g=w->j[(p->h^m)&1023]/64;H w->h[d][f]+w->i[a][(p->b[d]+6)]+g+(S)((m*37u+w->a*19u)%17);}', b''), (4312, 4170, b'ap(w,p,m,g)', b'w->h[L][M]+w->i[g][(p->b[L]+6)]+w->j[(p->h^m)&1023]/64+(S)((m*37u+w->a*19u)%17)'))
GAPS=((0, 0, 3630, '5511cc1965a8d8d91fb40d614a85cd0dd2dce5d33139c9f8ae3ec1ec3d73eddc'), (3772, 3630, 540, 'dbc12e305da525934eadc488933b04328b76f646b2002d4c85899f6c2afce871'), (4323, 4249, 3656, '913e3bca485733833eabf72e5da06428c6743adafe8f45188b5f3925a46accfe'))
def _pin(b):return len(b),hashlib.sha256(b).hexdigest()
def _rewrite(source,inverse=False):
 if type(source)is not bytes or _pin(source)!=(OUTPUT if inverse else INPUT):raise ValueError('fixed quiet-order input differs')
 result=source
 for a,b,old,new in reversed(EDITS):
  at,old,new=(b,new,old)if inverse else(a,old,new)
  if source[at:at+len(old)]!=old:raise ValueError('fixed quiet-order span differs')
  result=result[:at]+new+result[at+len(old):]
 if _pin(result)!=(INPUT if inverse else OUTPUT):raise ValueError('fixed quiet-order output differs')
 return result
def restore_source(source):return _rewrite(source,True)
def transform_source(source):
 result=_rewrite(source)
 if restore_source(result)!=source:raise ValueError('full quiet-order inverse differs')
 for a,b,n,h in GAPS:
  if source[a:a+n]!=result[b:b+n]or _pin(source[a:a+n])!=(n,h):raise ValueError('quiet-order gap differs')
 return result,dict(stage='late-full-F-single-caller-quiet-order-inline',input=INPUT,output=OUTPUT,raw_delta=-74,spans=2,protected_gaps=3,full_inverse=True,runtime_qualified=False)
def source_literal(source,previous):
 original=restore_source(source);expression,kind=previous(original)
 if ast.literal_eval(expression)!=original:raise ValueError('actual prior quiet-order literal differs')
 old,new=original.decode('ascii'),source.decode('ascii')
 if expression.count(old)!=1:raise ValueError('one quiet-order literal required')
 result=expression.replace(old,new,1)
 if result.replace(new,old,1)!=expression or ast.literal_eval(result)!=source:raise ValueError('quiet-order literal inverse differs')
 return result,kind
