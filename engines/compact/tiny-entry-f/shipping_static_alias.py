"""Pure full-F fixed static-keyword alias; no IO or engine policy changes.

The unoccupied identifier aa expands back to static at every admitted span.
The macro is inserted after includes and before the first declaration.  This
retains function linkage and storage duration.  The selected source was checked
against identical preprocessed bytes and native bytes; runtime qualification is
owned by its actual producer and selected execution, not this pure transform.
"""
import ast,hashlib
INPUT=(7830, '43bc67816e91077c4cfd182ec6ba44aed7d0223d012cff82f5366ad58da63582')
OUTPUT=(7740, 'f99f1c48e8a77d1f9483b09d46f2d68f7b1e92ea94dd437d708cc3e5a10dcfa9')
EDITS=((200, 200, b'', b'#define aa static\n'), (686, 704, b'static', b'aa'), (865, 879, b'static', b'aa'), (1039, 1049, b'static', b'aa'), (1082, 1088, b'static', b'aa'), (1167, 1169, b'static', b'aa'), (1316, 1314, b'static', b'aa'), (1538, 1532, b'static', b'aa'), (1683, 1673, b'static', b'aa'), (2202, 2188, b'static', b'aa'), (2338, 2320, b'static', b'aa'), (3046, 3024, b'static', b'aa'), (3219, 3193, b'static', b'aa'), (3430, 3400, b'static', b'aa'), (3561, 3527, b'static', b'aa'), (3604, 3566, b'static', b'aa'), (5314, 5272, b'static', b'aa'), (5365, 5319, b'static', b'aa'), (5414, 5364, b'static', b'aa'), (5429, 5375, b'static', b'aa'), (5566, 5508, b'static', b'aa'), (5720, 5658, b'static', b'aa'), (5849, 5783, b'static', b'aa'), (6130, 6060, b'static', b'aa'), (6251, 6177, b'static', b'aa'), (6330, 6252, b'static', b'aa'), (6376, 6294, b'static', b'aa'), (6602, 6516, b'static', b'aa'))
GAPS=((0, 0, 200, 'fef39602e6ecdcf69e8b988fbc07a8b7f5952ede6ad3df39c49773580b13bbab'), (200, 218, 486, 'a79bee6acfb7f7debdb95da624de5a92fd9155ad0e9a05c6a5e34874482f740c'), (692, 706, 173, 'b0d53297d5f63ff34fb93076313864f07bb5375e042cb73f30727ec000ce0dac'), (871, 881, 168, '56dd6e25cc72b2bb556fb3b76f18dd7147c78f627cab7999c61687aacb628238'), (1045, 1051, 37, 'b1fcf100217ee4420b160aa8f464ba0d4a24da8bb79e027af5826a19384c95e6'), (1088, 1090, 79, '16c18755989f7aca2ffb4f06a8a8a139fb53590b70cf413f03f7608fbd3340f5'), (1173, 1171, 143, 'd3e18c47c3e801f4bb2fc83183bb8fa849ced60c214348cc8cb044033c05f58f'), (1322, 1316, 216, '1082bafe65d2e18fe5021edab3eb3a44a70a3a9f11168893bfdd5ac358265c28'), (1544, 1534, 139, '59e2ddacdf7026549946691d8b82d78643d9fd01d7ab268a118c9c71c3d10fb0'), (1689, 1675, 513, '011e1f23554fda6a99a78cc3bc73badffb691b5150a216be1a7b97e6b2f03742'), (2208, 2190, 130, 'b69f3b7da4c6861d54217d59b91a0998982c79b605773b8cc280a06484bf6d24'), (2344, 2322, 702, 'c37fcc9b00753d8be6ef8ef27a2d5314d15e4f5e3d9ca4f14b3b3c60f40276af'), (3052, 3026, 167, '51bf39798dc6a0f9f24b67249b73073614e27609f10f6151423b3b7abf3db049'), (3225, 3195, 205, '1dcdb3fc7427629e955a9e58f6cd5dc996feec9a6e6f114beacf8c4782915b7b'), (3436, 3402, 125, '928d464171f9b7cebd5890c6ac01e2f74f0520c51363adc4cbf3c91e470298c0'), (3567, 3529, 37, '26ddd3d57d8ac15e6de8b127700f14ebf4e2c429f51f7b096eb0a42cc3cc56e0'), (3610, 3568, 1704, 'd98c05848a0c0f468f192f4342a01d16e791a728d780e8f4170a14d2fd86425d'), (5320, 5274, 45, 'cfc978c3cba3b6869a505539feaf08b7a82102d785c8371644ea672f5f7e38b7'), (5371, 5321, 43, 'd67ae51a68db670c189bea36ce1fd720deca7899984d9859a9d02951906a5092'), (5420, 5366, 9, '9ac0e7fd8cf68d0042ff7ceec1cd7848c3429927e9027c07e13ece9ad80119d1'), (5435, 5377, 131, '1ac6337ad0fc9b873999a9e6f58ff356329207511a8e796a07a41870e95cc67f'), (5572, 5510, 148, '6306a36fe11adaaeda2f21a17f7cb4ac08975261302c56fb30133c185e277db7'), (5726, 5660, 123, '089acd8ae8e04058b15163fc330708955fbe848f1ed82b7fbd8f37bc656d0198'), (5855, 5785, 275, 'fccd52a26a5edc0b8bc927da9f4bcb91dcb6ef9f792215754970831c967f172f'), (6136, 6062, 115, '9b2ed4d7f8e19bc47fc2aa77537356f30f7294b51d37ca0948894f37444a5951'), (6257, 6179, 73, 'b3a382f6b7083a2406870d3c29cd77ac4e62e7df3ca8b354a4e23c49e351e406'), (6336, 6254, 40, '28dac3c5b1efa9c93c6a6cd08367c1c995cf2773bbebdfcc4e46ca9b6af2f1a3'), (6382, 6296, 220, 'c41e400df8e1ca39f2209ea7067f581df62ee468565f4158789f3fee715b9731'), (6608, 6518, 1222, '53ba8a18c0a999bc169c30a706236444ba9b1152ef12651b78200306958a7fbb'))


def pin(data):return len(data),hashlib.sha256(data).hexdigest()

def rewrite(source,inverse=False):
 if type(source)is not bytes or pin(source)!=(OUTPUT if inverse else INPUT):raise ValueError('fixed static alias input differs')
 result=source
 for a,b,old,new in reversed(EDITS):
  at,before,after=(b,new,old)if inverse else(a,old,new)
  if source[at:at+len(before)]!=before:raise ValueError('fixed static alias span differs')
  result=result[:at]+after+result[at+len(before):]
 if pin(result)!=(INPUT if inverse else OUTPUT):raise ValueError('fixed static alias output differs')
 return result

def restore_source(source):return rewrite(source,True)

def transform_source(source):
 result=rewrite(source)
 if restore_source(result)!=source:raise ValueError('fixed static alias full inverse differs')
 for a,b,n,h in GAPS:
  if source[a:a+n]!=result[b:b+n]or pin(source[a:a+n])!=(n,h):raise ValueError('fixed static alias protected gap differs')
 return result,{'stage':'late-full-F-static-keyword-alias','input':INPUT,'output':OUTPUT,'raw_delta':-90,'spans':len(EDITS),'protected_gaps':len(GAPS),'keyword_references':27,'full_inverse':True,'engine_policy_unchanged':True,'runtime_qualified':False}

def source_literal(source,previous):
 original=restore_source(source);expression,kind=previous(original)
 if ast.literal_eval(expression)!=original:raise ValueError('actual prior static alias literal differs')
 old,new=original.decode('ascii'),source.decode('ascii')
 if expression.count(old)!=1:raise ValueError('one static alias literal required')
 result=expression.replace(old,new,1)
 if result.replace(new,old,1)!=expression or ast.literal_eval(result)!=source:raise ValueError('static alias literal inverse differs')
 return result,kind
