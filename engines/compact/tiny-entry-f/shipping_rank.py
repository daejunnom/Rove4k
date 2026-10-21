"""Fixed full-F2 local HCE rank fold, after its two-worker selector.

Only the pure value function changes. Valid0x88 rank r is0..7, r^7=7-r,
and vertical abs-center is reflection invariant. Empty-piece coefficients
are all zero. Board/Move/key/learners, full HCE/MTD/TT and resources stay.
Canonical/DEV, optional products and F8 bypass this late fixed source stage.
No external report, tool, source or runtime result is a generation input.
"""
import hashlib

INPUT=(8513,'9f2804e0bc9467ee5f831cf7e2f90bb27f54117a50228ffb3ad1681d4873a272')
OUTPUT=(8509,'a2d094c954ca7e0d02d38e0810c62c9fc8e754a536ee7770bc98214dee7d3142')
OFFSET=877
OLD=b'S s(S v,S q){static const S qi[7]={24576,48228,98624,65866,27124,41860,0};S a=qi[abs(v)],d=q>>4,f=q&7,g=v>0?d:7-d,i=7-abs(2*f-7)-abs(2*d-7),j=(a&1023)+g*((a>>10)&7)+i*((a>>13)-3);return v>0?j:-j;}'
NEW=b'S s(S v,S q){static const S qi[7]={24576,48228,98624,65866,27124,41860,0};S a=qi[abs(v)],d=q>>4^7*(v<0),f=q&7,i=7-abs(2*f-7)-abs(2*d-7),j=(a&1023)+d*((a>>10)&7)+i*((a>>13)-3);return v>0?j:-j;}'
GAPS=((877,'70645e4183f41c65c947ffb5fb10795f8abb477bc99a84bde7003f6c0cb8c04a'),
      (7440,'3edec69be09c07284683d6f72c48f3e41f0ee5fc541a126a30d55a966c3d1e8c'))

def _pin(data):return len(data),hashlib.sha256(data).hexdigest()

def transform_source(source):
    if type(source) is not bytes or _pin(source)!=INPUT:
        raise ValueError('fixed full-F2 post-selector rank input differs')
    if source.count(OLD)!=1 or source[OFFSET:OFFSET+len(OLD)]!=OLD:
        raise ValueError('sole actual HCE rank function differs')
    before,after=source[:OFFSET],source[OFFSET+len(OLD):]
    if (_pin(before),_pin(after))!=GAPS:
        raise ValueError('HCE rank protected complement differs')
    result=before+NEW+after
    if (_pin(result)!=OUTPUT or result.count(NEW)!=1
            or result[:OFFSET]!=before or result[OFFSET+len(NEW):]!=after
            or result[:OFFSET]+OLD+result[OFFSET+len(NEW):]!=source):
        raise ValueError('HCE rank output/gaps/inverse differs')
    return result,{'family':'F','policy':'full-fixed2','stage':'local-HCE-rank-after-selector',
        'input_bytes':INPUT[0],'input_sha256':INPUT[1],
        'output_bytes':OUTPUT[0],'output_sha256':OUTPUT[1],
        'raw_delta':-4,'edits':1,'gaps':2,'exact_inverse':True,
        'C_int_rank0to7_piece_minus6to6_including0':True,
        'Board_Move_key_TT_learner_orientation_changed':False,
        'native_entire_byte_identity_to_predecessor':False,'external_reads':0}
