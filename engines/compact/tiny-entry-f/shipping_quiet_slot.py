"""Pure fixed quiet-cutoff continuation-slot reuse; no IO/products.

After successful make, !P excludes promotions and the child destination holds
the parent's source piece, including castling.  Recursive search does not mutate
that board, so its existing Q is the same learner index for either 2 or 8 workers.
Do not rewrite quiet ordering: its moves can still include quiet promotions.
"""
import ast,hashlib
INPUT=(7840, '67279ef99a5ade0b3b8c66564abc15e4ccd9bead3253ca18e4b88b6d87e14ca1')
OUTPUT=(7830, '43bc67816e91077c4cfd182ec6ba44aed7d0223d012cff82f5366ad58da63582')
EDITS=((4683, 4683, b'an(&w->i[g][(p->b[N]+6)],R);', b'an(&w->i[g][Q],R);'),)
GAPS=((0, 0, 4683, '1ff6bcbba982ad340a3daedb24cd0a9fb8dc389e45025336306a0740c5165119'), (4711, 4701, 3129, 'b22a1cca53e9b90135567104cca3dde27de38384d073823d9a6984080ea16987'))

def pin(b):return len(b),hashlib.sha256(b).hexdigest()

def rewrite(source,inverse=False):
 if type(source)is not bytes or pin(source)!=(OUTPUT if inverse else INPUT):raise ValueError('quiet slot fixed input differs')
 result=source
 for old_at,new_at,old,new in reversed(EDITS):
  at,before,after=(new_at,new,old)if inverse else(old_at,old,new)
  if source[at:at+len(before)]!=before or source.count(before)!=1:raise ValueError('quiet slot fixed span differs')
  result=result[:at]+after+result[at+len(before):]
 if pin(result)!=(INPUT if inverse else OUTPUT):raise ValueError('quiet slot fixed output differs')
 return result

def restore_source(source):return rewrite(source,True)

def transform_source(source):
 result=rewrite(source)
 if restore_source(result)!=source:raise ValueError('quiet slot full inverse differs')
 for a,b,n,h in GAPS:
  if source[a:a+n]!=result[b:b+n]or pin(source[a:a+n])!=(n,h):raise ValueError('quiet slot protected gap differs')
 return result,{'stage':'late-full-F-quiet-continuation-slot','input':INPUT,'output':OUTPUT,'full_inverse':True,'spans':1,'protected_gaps':2,'raw_delta':-10,'quiet_order_unchanged':True,'runtime_qualified':False}

def source_literal(source,previous):
 original=restore_source(source);expression,kind=previous(original)
 if ast.literal_eval(expression)!=original:raise ValueError('actual prior quiet slot literal differs')
 old,new=original.decode('ascii'),source.decode('ascii')
 if expression.count(old)!=1:raise ValueError('one quiet slot literal required')
 result=expression.replace(old,new,1)
 if result.replace(new,old,1)!=expression or ast.literal_eval(result)!=source:raise ValueError('quiet slot literal inverse differs')
 return result,kind
