"""Pure final full-F local spelling replay; DEV/alternate policy bypass it.

The fixed preimage and declared binding spans were reviewed with whole-function
fresh names and actual compiler native/diagnostic identity. This is a fixed
source adapter, not a search or runtime input. It reads no external evidence.
"""
import hashlib

BEFORE=(8538,'47353a15426e508cf2975d0bcba529052aac791b9461f952a88084b5e0e8d5a0')
AFTER=(8538,'400ad454b0e3108814636bab4060f224ae4b2d28cdc7929c8c98590adb46c59d')
COMPLEMENT=(8479, '66edd0be39b6b60786ee65dd697a8078ba0c723e535d5eb7c972b7ec0f634b8f')
ANCHORS=((784, b'W r(W x){'), (3257, b'void o(za*p){'), (4010, b'static S U(zc*w,const za*p,S a,S d,S f,S g,Y*l){'), (5235, b'void i(zc*w,const za*p){'))
GROUPS=(('r', 'x', 'd', 9), ('o', 'f', 'i', 9), ('U', 'H', 'u', 15), ('i', 'g', 'q', 13), ('o', 't', 'q', 13))
EDITS=(
    (790, b'x', b'd'),
    (793, b'x', b'd'),
    (796, b'x', b'd'),
    (799, b'x', b'd'),
    (826, b'x', b'd'),
    (829, b'x', b'd'),
    (832, b'x', b'd'),
    (866, b'x', b'd'),
    (869, b'x', b'd'),
    (3312, b't', b'q'),
    (3318, b't', b'q'),
    (3324, b't', b'q'),
    (3331, b't', b'q'),
    (3344, b'f', b'i'),
    (3348, b'f', b'i'),
    (3352, b'f', b'i'),
    (3360, b't', b'q'),
    (3362, b'f', b'i'),
    (3367, b'f', b'i'),
    (3374, b't', b'q'),
    (3379, b'f', b'i'),
    (3387, b't', b'q'),
    (3392, b'f', b'i'),
    (3401, b't', b'q'),
    (3407, b'f', b'i'),
    (3413, b'f', b'i'),
    (3418, b't', b'q'),
    (3426, b't', b'q'),
    (3429, b't', b'q'),
    (3433, b't', b'q'),
    (3440, b't', b'q'),
    (4339, b'H', b'u'),
    (4385, b'H', b'u'),
    (4398, b'H', b'u'),
    (4401, b'H', b'u'),
    (4431, b'H', b'u'),
    (4444, b'H', b'u'),
    (4899, b'H', b'u'),
    (4990, b'H', b'u'),
    (4997, b'H', b'u'),
    (5017, b'H', b'u'),
    (5135, b'H', b'u'),
    (5146, b'H', b'u'),
    (5159, b'H', b'u'),
    (5162, b'H', b'u'),
    (5189, b'H', b'u'),
    (5330, b'g', b'q'),
    (5362, b'g', b'q'),
    (5367, b'g', b'q'),
    (5371, b'g', b'q'),
    (5379, b'g', b'q'),
    (5458, b'g', b'q'),
    (5463, b'g', b'q'),
    (5498, b'g', b'q'),
    (5505, b'g', b'q'),
    (5515, b'g', b'q'),
    (5604, b'g', b'q'),
    (5671, b'g', b'q'),
    (5689, b'g', b'q'),
)

def _pin(raw):return len(raw),hashlib.sha256(raw).hexdigest()
def _need(ok,message):
    if not ok:raise ValueError(message)

def transform_source(source):
    _need(type(source) is bytes and _pin(source)==BEFORE,'fixed pre-name full-F source required')
    for at,old in ANCHORS:
        _need(source[at:at+len(old)]==old,'fixed function declaration differs')
    parts=[];gaps=[];rows=[];cursor=0
    for at,old,new in EDITS:
        _need(at>=cursor and source[at:at+len(old)]==old,'fixed binding token span differs')
        gap=source[cursor:at];gaps.append(gap);parts.extend((gap,new))
        rows.append({'offset':at,'old':old.decode(),'new':new.decode()});cursor=at+len(old)
    gaps.append(source[cursor:]);parts.append(source[cursor:]);candidate=b''.join(parts)
    _need(_pin(candidate)==AFTER,'fixed local-spelling result differs')
    inverse=[];candidate_gaps=[];cursor=0
    for at,old,new in EDITS:
        _need(candidate[at:at+len(new)]==new,'fixed inverse token differs')
        gap=candidate[cursor:at];candidate_gaps.append(gap);inverse.extend((gap,old));cursor=at+len(new)
    candidate_gaps.append(candidate[cursor:]);inverse.append(candidate[cursor:])
    _need(b''.join(inverse)==source and candidate_gaps==gaps,'fixed spelling inverse/gap differs')
    _need(_pin(b''.join(gaps))==COMPLEMENT,'fixed spelling source complement differs')
    return candidate,{'stage':'full-F final local binding names','input_bytes':BEFORE[0],
        'input_sha256':BEFORE[1],'output_bytes':AFTER[0],'output_sha256':AFTER[1],
        'groups':GROUPS,'edits':rows,'exact_inverse':True,'each_protected_gap_exact':True,
        'complement_bytes':COMPLEMENT[0],'complement_sha256':COMPLEMENT[1],
        'canonical_DEV_alternate_policies_changed':False,'fixed_resource_profile_changed':False,
        'native_entire_bytes_equal_in_qualification':True,'raw_source_delta':0,
        'runtime_evidence_is_generation_input':False}
