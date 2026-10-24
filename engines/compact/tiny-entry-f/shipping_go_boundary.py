"""Pure fixed sole-GO block transform; no IO/products."""
import ast,hashlib
INPUT=(7863, '0ba7f01ae4df9a306a5dc3e790a451f272657d2411f66f972ef394d7170cfc5a')
OUTPUT=(7840, '67279ef99a5ade0b3b8c66564abc15e4ccd9bead3253ca18e4b88b6d87e14ca1')
EDITS=((6703, 6703, b'static void x(void){k();W a=-1,d=0,f=0;for(char*t=w();t;t=w()){if((*t==\'w\'||*t==\'b\')&&(!strcmp(t+1,"time")||!strcmp(t+1,"inc"))){W n=qm(w());if((*t==\'w\')==(Z.s>0)){if(t[1]==\'t\')a=n;else d=n;}}}if(~a){f=a/30+(d>86400000?86400000:d)*3/4;if(f>a/5)f=a/5;if(!f)f=1;}else f=1000;qc=q()+(f>86400000?86400000:f);atomic_store(&V,0);pthread_mutex_lock(&J);C=2;U->b=U[1].b=-1;pthread_cond_broadcast(&u);pthread_mutex_unlock(&J);}', b''), (7703, 7285, b'x();', b'{k();W a=-1,d=0,f=0;for(char*t=w();t;t=w()){if((*t==\'w\'||*t==\'b\')&&(!strcmp(t+1,"time")||!strcmp(t+1,"inc"))){W n=qm(w());if((*t==\'w\')==(Z.s>0)){if(t[1]==\'t\')a=n;else d=n;}}}if(~a){f=a/30+(d>86400000?86400000:d)*3/4;if(f>a/5)f=a/5;if(!f)f=1;}else f=1000;qc=q()+(f>86400000?86400000:f);atomic_store(&V,0);pthread_mutex_lock(&J);C=2;U->b=U[1].b=-1;pthread_cond_broadcast(&u);pthread_mutex_unlock(&J);}'))
GAPS=((0, 0, 6703, '4986e1e4bdab2b030648ffb133831d32c2bcf928462323cd6f2647b889804517'), (7121, 6703, 582, '77bcdfe149d11cc2157d8914e5a10343b9fd6842443f4064228a070454ad4ddd'), (7707, 7684, 156, 'af7c4858bff6947af201cdf8c867385017725c4f621d3e63251712eaa705ebcc'))

def pin(b):return len(b),hashlib.sha256(b).hexdigest()
def rewrite(source,inverse=False):
 if type(source)is not bytes or pin(source)!=(OUTPUT if inverse else INPUT):raise ValueError('soleGO fixed input differs')
 result=source
 for old_at,new_at,old,new in reversed(EDITS):
  at,before,after=(new_at,new,old)if inverse else(old_at,old,new)
  if source[at:at+len(before)]!=before:raise ValueError('soleGO fixed span differs')
  result=result[:at]+after+result[at+len(before):]
 if pin(result)!=(INPUT if inverse else OUTPUT):raise ValueError('soleGO fixed output differs')
 return result
def restore_source(source):return rewrite(source,True)
def transform_source(source):
 result=rewrite(source)
 if restore_source(result)!=source:raise ValueError('soleGO full inverse differs')
 for a,b,n,h in GAPS:
  if source[a:a+n]!=result[b:b+n]or pin(source[a:a+n])!=(n,h):raise ValueError('soleGO protected gap differs')
 return result,{'stage':'late-full-F-sole-GO-boundary','input':INPUT,'output':OUTPUT,'full_inverse':True,'spans':2,'protected_gaps':3,'GO_body_bytes_unchanged':399,'raw_delta':-23,'runtime_qualified':False}

def source_literal(source,previous):
 original=restore_source(source);expression,kind=previous(original)
 if ast.literal_eval(expression)!=original:raise ValueError('actual prior soleGO literal differs')
 old,new=original.decode('ascii'),source.decode('ascii')
 if expression.count(old)!=1:raise ValueError('one soleGO literal required')
 result=expression.replace(old,new,1)
 if result.replace(new,old,1)!=expression or ast.literal_eval(result)!=source:raise ValueError('soleGO literal inverse differs')
 return result,kind
