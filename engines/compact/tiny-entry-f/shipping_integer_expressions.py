"""Fixed full-F integer spellings after its direct-walker stage.

int32 constants retain mate29872/ply127/depth1..126. The TT mask changes
unsigned32 to int32 spelling, but W:uint64_t & converts both to262143.
MTD q/d are plain stack ints: q+(q==d) has the same two q/one d reads,
with no calls/writes/volatile; existing interval/stop guards protect +1.
Operand read ordering, source/native/code layout/performance identity is
not claimed. All7 source spans,8 gaps and the whole inverse are fixed.
Canonical/DEV/actual optional selected/F8 pre-name bypass this stage;
optional separate full_reference applies it explicitly. No external reads.
"""
import hashlib

INPUT=(8410,'0185b1140d96adc4c0e48ba08ee52e296f733046a9958c6810ecec2e39e4a884')
OUTPUT=(8385,'acae5c84a77a22d52335aa905ac1b72117d7c74c3ac06e0fc86300c368a540c5')
EDITS=((3393, 3393, b'((1u<<18)-1)', b'262143'), (4132, 4126, b'f==128-1', b'f==127'), (4309, 4301, b'abs(u)>30000-128', b'abs(u)>29872'), (5070, 5058, b'abs(u)>30000-128', b'abs(u)>29872'), (5225, 5209, b'a<=128-2', b'a<127'), (5290, 5271, b'q==d?q+1:q', b'q+(q==d)'), (5597, 5576, b'abs(q)<30000-128', b'abs(q)<29872'))
GAPS=((0, 0, 3393, '274394f87fb4e778a69929431962cc9fd6d66725da155f7e6c6b74a62a9a1a07'), (3405, 3399, 727, '5fef0588a6752aa54f6be820231fa1c6c1c9a36e56102469a26ce2f359e3be61'), (4140, 4132, 169, '064809cdad1553fbe817b869a7ef2c11425c66b232830aec07838b0f213d5842'), (4325, 4313, 745, '1880abb402a639409d4982f40dc9eb75d25e8ea41fc96a98085de50d68462b98'), (5086, 5070, 139, '2580955b765f0c35eeb4e6fcf49b19769fbc591e4efef9a1c7d3a05049d87d98'), (5233, 5214, 57, '01094d14c92ad2eb4de53ba5fccc60274aaec66532a17d5e5c6a4e56914ffe5c'), (5300, 5279, 297, '056a01a837fc7ed56f7d6a002cf9225a28942e6cf5fd0eab5d804e05f671b555'), (5613, 5588, 2797, 'c67bf3af9e3ec22c254654b56fa9e6bcbaa781eeaf510205dad720751ee6a695'))

def _pin(raw):return len(raw),hashlib.sha256(raw).hexdigest()
def _need(ok,message):
    if not ok:raise ValueError(message)

def transform_source(source):
    _need(type(source)is bytes and _pin(source)==INPUT,'fixed full-F post-walker integer input differs')
    result=source
    for old_at,new_at,old,new in reversed(EDITS):
        _need(source[old_at:old_at+len(old)]==old,'fixed F integer input span differs')
        result=result[:old_at]+new+result[old_at+len(old):]
    _need(_pin(result)==OUTPUT,'fixed F integer output differs')
    inverse=result
    for old_at,new_at,old,new in reversed(EDITS):
        _need(result[new_at:new_at+len(new)]==new,'fixed F integer output span differs')
        inverse=inverse[:new_at]+old+inverse[new_at+len(new):]
    _need(inverse==source,'F integer full inverse differs')
    for old_at,new_at,length,digest in GAPS:
        old=source[old_at:old_at+length];new=result[new_at:new_at+length]
        _need(old==new and hashlib.sha256(old).hexdigest()==digest,'F integer protected gap differs')
    return result,{'family':'F','policy':'full-fixed2','stage':'integer-expressions-after-direct-walker',
        'input_bytes':INPUT[0],'input_sha256':INPUT[1],
        'output_bytes':OUTPUT[0],'output_sha256':OUTPUT[1],
        'literal_regions':7,'protected_gaps':8,'full_inverse':True,'raw_source_delta':-25,
        'same_int32_thresholds_depths_and_W_index':True,'private_MTD_interval_and_reads_preserved':True,
        'native_identity_claimed':False,'canonical_DEV_actual_optional_F8_changed':False,'external_reads':0}
