"""Fixed late C object constants after the SIMD-cross pool stage.
The 28 fixed spans expand four project-owned object macros to identical
unsuffixed int bodies, with29 protected gaps and a full inverse. All other
directives, literals, function macros and code bytes are protected. The actual
full-header340501-token and entire-native comparison passed; macro-table and
source-location identity are not claimed. No IO/compiler/report/AST/external
inputs. Canonical/DEV bypass this fixed shipping-only representation."""
import ast
import hashlib
INPUT=(9075, 'ce9c91755d91ee8e9b58639d6d904e68ab6a4e4d65f45cb5a57b40b38093164b')
OUTPUT=(8992, 'a82b3d17f132fba5e3949c9d2750ad2eeb5e2034db36d27daca2d8d3cdcd1329')
EDITS=((195, 195, b'#define PLY 128\n', b''), (212, 196, b'#define MOVES 512\n', b''), (230, 196, b'#define HISTORY 4096\n', b''), (251, 196, b'#define MATE 30000\n', b''), (614, 540, b'HISTORY', b'4096'), (622, 545, b'PLY', b'128'), (702, 625, b'HISTORY', b'4096'), (4600, 4520, b'PLY', b'128'), (4613, 4533, b'MOVES', b'512'), (4630, 4548, b'MOVES', b'512'), (4657, 4573, b'MATE', b'30000'), (4781, 4698, b'MATE', b'30000'), (4786, 4704, b'PLY', b'128'), (4802, 4720, b'MATE', b'30000'), (4807, 4726, b'PLY', b'128'), (5854, 5773, b'MATE', b'30000'), (5928, 5848, b'MATE', b'30000'), (5933, 5854, b'PLY', b'128'), (6031, 5952, b'MATE', b'30000'), (6036, 5958, b'PLY', b'128'), (6052, 5974, b'MATE', b'30000'), (6057, 5980, b'PLY', b'128'), (6228, 6151, b'PLY', b'128'), (6263, 6186, b'MATE', b'30000'), (6268, 6192, b'MATE', b'30000'), (6707, 6632, b'MOVES', b'512'), (7542, 7465, b'HISTORY', b'4096'), (7684, 7604, b'HISTORY', b'4096'))
GAPS=((0, 0, 195, '519322237976b54b25bbd2efc887ec6e705c615d144ff343ffd9983aca205249'), (211, 195, 1, '01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b'), (230, 196, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (251, 196, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (270, 196, 344, '5e13c89ebf8ab5a2de8ec6e8ab7420f9d994cb003e3a9614f303c9aaab982575'), (621, 544, 1, 'a318c24216defe206feeb73ef5be00033fa9c4a74d0b967f6532a26ca5906d3b'), (625, 548, 77, '3bde245eaf83d163eba2b2c0395166208a9b9481007187ed0d77502e38f2c9c1'), (709, 629, 3891, '3bd49a114c930b1b06858dba7f3ae9d6dff562c786e7e12a33ce7ec9709bb983'), (4603, 4523, 10, '4034aa356ba2b80a40d725d22e4dd6c0e90bab02075ef765865831ef6f1cac11'), (4618, 4536, 12, '3430c69b5d38e1d9a6ded914e99ca3e5300d6e3b7d8b929f0dd61b1ae6dcf1ca'), (4635, 4551, 22, 'c7d652d50704fee8c97f48ab3d1f5eb2cb766892ebde8c9f3b1fa7ce0d77abee'), (4661, 4578, 120, 'c5a2a864ec61b2740c5602766dea2e0f0b2a4660cd72868ebbdb9c6fc578df90'), (4785, 4703, 1, '3973e022e93220f9212c18d0d0c543ae7c309e46640da93a4a0314de999f5112'), (4789, 4707, 13, 'd1117fbdd9a4fc4c11f5bccb1fbcad9df70b20c318d16bc2da5468fcecf5f63f'), (4806, 4725, 1, 'a318c24216defe206feeb73ef5be00033fa9c4a74d0b967f6532a26ca5906d3b'), (4810, 4729, 1044, '30ede5654d6c278ead20fa045b4b4e319c8b27ea06fcc2792920452d0c03b7f0'), (5858, 5778, 70, '5daef0e4a388d8e74a92a93e61b0cb88f04fd12b2682d98d1bce12337488a14b'), (5932, 5853, 1, '3973e022e93220f9212c18d0d0c543ae7c309e46640da93a4a0314de999f5112'), (5936, 5857, 95, '2287423e97d2c2531750e5f1a5c4c1f4bca8a8f57bda6dc94692921f81ecf045'), (6035, 5957, 1, '3973e022e93220f9212c18d0d0c543ae7c309e46640da93a4a0314de999f5112'), (6039, 5961, 13, '33373088aa1ca402199872684d972015bb2840c2c38ec5237078d8ca7b5dc56d'), (6056, 5979, 1, 'a318c24216defe206feeb73ef5be00033fa9c4a74d0b967f6532a26ca5906d3b'), (6060, 5983, 168, 'fe5e78ed4f652a0170cf6c74b1b28a3368fd7b68372b55280436e0f1d6827754'), (6231, 6154, 32, '1f0abd32c61bad2f4c07213f452c7a8438bb0cc8dd2b197d891fbf01df2d19ec'), (6267, 6191, 1, 'd03502c43d74a30b936740a9517dc4ea2b2ad7168caa0a774cefe793ce0b33e7'), (6272, 6197, 435, '8f6e8c2081270a020a4acd807ec748e2539705738c038b6665cc5fa95e62de1b'), (6712, 6635, 830, '4f360ed1c78a6b41adad339d00990b404cb2dfda2137e7bdaeaedf4071f131b3'), (7549, 7469, 135, '9cfbb7d45e0fc6429217f608dcffc70edb164402e62f636661e0da3f4869a391'), (7691, 7608, 1384, '289ca0fd45871f2dc675206d254a90262301a87b66cc84589d517eb1fd04ad6f'))
def pin(b):return len(b),hashlib.sha256(b).hexdigest()
def forward(source):
 if type(source)is not bytes or pin(source)!=INPUT:raise ValueError('fixed late C constant input')
 out=source
 for a,b,old,new in reversed(EDITS):
  if source[a:a+len(old)]!=old:raise ValueError('fixed C constant role')
  out=out[:a]+new+out[a+len(old):]
 if pin(out)!=OUTPUT:raise ValueError('fixed C constant output')
 for a,b,n,h in GAPS:
  if source[a:a+n]!=out[b:b+n]or pin(source[a:a+n])!=(n,h):raise ValueError('C constant protected gap')
 if inverse(out)!=source:raise ValueError('C constant complete inverse')
 return out
def inverse(source):
 if type(source)is not bytes or pin(source)!=OUTPUT:raise ValueError('fixed C constant inverse input')
 out=source
 for a,b,old,new in reversed(EDITS):
  if source[b:b+len(new)]!=new:raise ValueError('C constant inverse role')
  out=out[:b]+old+out[b+len(new):]
 if pin(out)!=INPUT:raise ValueError('fixed C constant restored input')
 return out

BOOT_INPUT=(10036,'0b51f88fe6033b480c0429a41337e1ea100a82db05632d70d29f4678488b520a')
BOOT_OUTPUT=(9953,'efc5e1c5156661dfe91386285b5fdedacebceb0eef8779f79ca22bf2f315a65c')
def restore_source(source):return inverse(source)
def transform_source(source):
 result=forward(source)
 return result,{'family':'C','stage':'late-four-object-constants-after-cross-pool','input_bytes':INPUT[0],'input_sha256':INPUT[1],'output_bytes':OUTPUT[0],'output_sha256':OUTPUT[1],'raw_delta':-83,'edits':28,'protected_gaps':29,'full_inverse':True,'full_header_CPP_tokens':340501,'entire_native_equal':True,'canonical_DEV_changed':False,'external_reads':0}
def transform_bootstrap(previous,*,source):
 baseline=restore_source(source)
 if type(previous)is not bytes or pin(previous)!=BOOT_INPUT:raise ValueError('actual C pool bootstrap differs')
 q=chr(34)*3;old=('br'+q+baseline.decode('ascii')+q).encode('ascii');new=('br'+q+source.decode('ascii')+q).encode('ascii')
 if previous.count(old)!=1 or ast.literal_eval(old.decode())!=baseline or ast.literal_eval(new.decode())!=source:
  raise ValueError('actual C raw source literal differs')
 result=previous.replace(old,new,1)
 if result.count(new)!=1 or result.replace(new,old,1)!=previous or pin(result)!=BOOT_OUTPUT:
  raise ValueError('C late constants bootstrap inverse/output differs')
 calls=[n for n in ast.walk(ast.parse(result))if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and n.func.attr=='communicate']
 if len(calls)!=1 or ast.literal_eval(calls[0].args[0])!=source:raise ValueError('C compiler stdin differs')
 return result,{'stage':'late-four-constants-literal-after-actual-pool-bootstrap','input_bytes':BOOT_INPUT[0],'input_sha256':BOOT_INPUT[1],
  'output_bytes':BOOT_OUTPUT[0],'output_sha256':BOOT_OUTPUT[1],'actual_previous_pool_cross_common_guard_consumed':True,
  'outside_source_literal_unchanged':True,'full_inverse':True,'compiler_resources_codec_changed':False,'external_reads':0}
