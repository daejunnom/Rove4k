"""Fixed C completed-depth job token, after the current SIMD cross stage.
Static depth0 is idle; -1 published underqj is unclaimed; own worker claims0
underqj before the unique shipping A->C(w,&ql) call. The typed a=p retains
w=NULL startup/completion sentinel. Direct C consumers must seed depth0; this
is not a general entry API equivalence. Completion x/fflush precedes qk0
broadcast; j drain and partial pthread-create joins remain exact.
No IO, compiler, report, AST or experiment inputs are read by this module.
Canonical/DEV and every board/model/SIMD/search/TT/learning body are unchanged.
"""
import ast
import hashlib
INPUT=(9093, 'da74d1c079ad0abebbb5a63040ca6f3306943ffb271b00e0117267bce0ee2d93')
OUTPUT=(9075, 'ce9c91755d91ee8e9b58639d6d904e68ab6a4e4d65f45cb5a57b40b38093164b')
EDITS=((6161, 6161, b'w->a5=0;w->C=0;w->l=0;', b'w->a5=0;w->l=0;'), (6469, 6462, b'static unsigned qd;', b''), (7020, 6994, b'ai*w=0;unsigned a=0;', b'ai*w=0,*a=p;'), (7120, 7086, b'while(a==qd&&!qm)', b'while(a->C>=0&&!qm)'), (7176, 7144, b'w=p;a=qd;', b'w=a;w->C=0;'), (8257, 8227, b'qk=2;qd++;', b'qk=2;qr->C=qr[1].C=-1;'))
GAPS=((0, 0, 6161, 'f03de5b2a2de0d64ed06f9e1a5e894d8ee25ae9a89455c76231bd4db7e0f7c69'), (6183, 6176, 286, '21facf01f7c9dde2fda7c03023da11ee3ac95c934d5ca35da3c8ca56f70acf25'), (6488, 6462, 532, '4c9ed8a5b721b6941bfa448a616406a688cc0c1bfad3f0d4d8b1401e085f831a'), (7040, 7006, 80, '9a3c8abac19f9e84b752bc16e75b56e763b8c273223c5e25b28de2fede40419e'), (7137, 7105, 39, '2db75265c2eb7155de557c4303b1197fc74ab4768a44e348bc6a26c01633116a'), (7185, 7155, 1072, 'b7b7f54642d49f90ea8652ec7be3814c7be649e7e6cb04ad68dcd004680abb98'), (8267, 8249, 826, '2d25b5a36f719cecca518e4a59b19bfd47414a76a6db983f5b36968ae726feac'))
BOOT_INPUT=(10054,'14405494f35ef3fcc40646d487adf57b35de10b0ef9e0182b5333e9be9be2d68')
BOOT_OUTPUT=(10036,'0b51f88fe6033b480c0429a41337e1ea100a82db05632d70d29f4678488b520a')
def pin(b):return len(b),hashlib.sha256(b).hexdigest()
def transform(source):
 if type(source)is not bytes or pin(source)!=INPUT:raise ValueError('fixed C pool input')
 out=source
 for a,b,old,new in reversed(EDITS):
  if source[a:a+len(old)]!=old:raise ValueError('C pool role')
  out=out[:a]+new+out[a+len(old):]
 if pin(out)!=OUTPUT:raise ValueError('C pool output')
 for a,b,n,h in GAPS:
  if source[a:a+n]!=out[b:b+n]or pin(source[a:a+n])!=(n,h):raise ValueError('C pool protected gap')
 if restore_source(out)!=source:raise ValueError('C pool complete inverse')
 return out
def restore_source(source):
 if type(source)is not bytes or pin(source)!=OUTPUT:raise ValueError('C pool inverse input')
 out=source
 for a,b,old,new in reversed(EDITS):
  if source[b:b+len(new)]!=new:raise ValueError('C pool inverse role')
  out=out[:b]+old+out[b+len(new):]
 if pin(out)!=INPUT:raise ValueError('C pool restored source')
 return out
def transform_source(source):
 result=transform(source)
 return result,{'family':'C','stage':'completed-depth-jobtoken-after-SIMD-cross','input_bytes':INPUT[0],'input_sha256':INPUT[1],
  'output_bytes':OUTPUT[0],'output_sha256':OUTPUT[1],'raw_delta':-18,'roles':6,'protected_gaps':7,'full_inverse':True,
  'job_token':'signed C -1 unclaimed,0 claimed underqj,1..126 completed depth',
  'actual_think_caller':'unique shipping A->C(w,&ql); direct think fixtures must seed0',
  'startup_w_null_drain_flush_broadcast_partial_join_preserved':True,
  'model_SIMD_search_TT_learning_input_unchanged':True,'canonical_DEV_changed':False,
  'native_identity_claimed':False,'external_reads':0}
def transform_bootstrap(previous,*,source):
 baseline=restore_source(source)
 if type(previous)is not bytes or pin(previous)!=BOOT_INPUT:raise ValueError('actual C cross bootstrap differs')
 q=chr(34)*3;old=('br'+q+baseline.decode('ascii')+q).encode('ascii');new=('br'+q+source.decode('ascii')+q).encode('ascii')
 if previous.count(old)!=1 or ast.literal_eval(old.decode())!=baseline or ast.literal_eval(new.decode())!=source:
  raise ValueError('actual C raw source literal differs')
 result=previous.replace(old,new,1)
 if result.count(new)!=1 or result.replace(new,old,1)!=previous or pin(result)!=BOOT_OUTPUT:
  raise ValueError('C pool bootstrap inverse/output differs')
 calls=[n for n in ast.walk(ast.parse(result))if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and n.func.attr=='communicate']
 if len(calls)!=1 or ast.literal_eval(calls[0].args[0])!=source:raise ValueError('C compiler stdin differs')
 return result,{'stage':'completed-depth-token-literal-after-actual-cross-bootstrap','input_bytes':BOOT_INPUT[0],'input_sha256':BOOT_INPUT[1],
  'output_bytes':BOOT_OUTPUT[0],'output_sha256':BOOT_OUTPUT[1],'actual_previous_cross_guard_consumed':True,
  'outside_source_literal_unchanged':True,'full_inverse':True,'compiler_resources_codec_changed':False,'external_reads':0}
