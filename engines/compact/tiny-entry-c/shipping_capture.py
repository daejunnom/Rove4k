"""Fixed C shipping-only capture metadata, after lazy fallback.

Canonical readable and DEV retain their existing Move/reference domain. The
caller invokes this only for the exact full shipping source. Generated valid
0x88 from squares leave bit3 free; capture-only metadata uses that bit, FROM119
strips it, and TO/PROMO/Move17 keep their domains. Quiet promotion remains tag0.
All source rules are owned literals; no external artifact or receipt is read.
"""
import hashlib

INPUT=(9958,'1c7d102dfc3eda05cad0c7f2032537b67633f364341037ff57237a3600a209ad')
OUTPUT=(9882,'11b0c4ee8703d0feac9338ddf8b53e7225e92d644a57c3351be22585f28e538a')
EDITS=((372, 372, b'#define FROM(m) ((m)&127)', b'#define FROM(m) ((m)&119)', 'FROM strips reserved capture bit3'), (2709, 2709, b'static void g(T*a,int*n,int zJ,int to,int d){int f=d&&!(to+16&96);for(int z=f?2:0;z<=(f?5:0);z++){if(*n>=MOVES)abort();a[(*n)++]=MOVE(zJ,to,z);}}', b'static void g(T*a,int*n,int zJ,int to,int d){int f=d>1&&!(to+16&96);for(int z=f?2:0;z<=(f?5:0);z++){if(*n>=MOVES)abort();a[(*n)++]=MOVE(zJ,to,z)|(d&1)*8;}}', 'capture-only generator classes'), (3045, 3055, b'g(f,&n,m,q,1);', b'g(f,&n,m,q,2);', 'quiet single pawn push class2'), (3334, 3344, b'g(f,&n,m,v,a==1);', b'g(f,&n,m,v,a==1?3:!!w);', 'pawn capture EP class3/nonpawn target class'), (4544, 4560, b'static int l(const za*p,T m){return p->b[TO(m)]||(abs(p->b[FROM(m)])==1&&TO(m)==p->e);}', b'', 'remove repeated mailbox capture predicate'), (5395, 5324, b'm==tt?1000000:l(p,m)?', b'm==tt?1000000:m&8?', 'capture ordering tier'), (5715, 5641, b'yu=l(p,m)||PROMO(m)', b'yu=(m&8)||PROMO(m)', 'QS/reduction tactical predicate'), (6320, 6245, b'!l(p,zj)&&!PROMO(zj)', b'!(zj&8)&&!PROMO(zj)', 'quiet correction eligibility'))
GAPS=((0, 0, 372, 'a6afd0779da2430c2ca32a03cd7746bacf7e041efcd8a075969361967962656a'), (397, 397, 2312, 'eef3e926b2d7b01fccaa376c451e17b85b31b9ab42795af3a459ea08f265e42e'), (2854, 2864, 191, '11d0c7625833735760a55dec4aa7f1ad6d7123a0e50cc5ef6bceb57f0f00ee17'), (3059, 3069, 275, 'e8c16243023cba2d0be0d0661bdd55ec2c9d36682fb81ea38d915accf3565d5e'), (3351, 3367, 1193, '1405f34df01455ca704233ff651f1461e8c96fc991462a637e173704a0564a9c'), (4631, 4560, 764, '4b9741b6f99825870866f79bdba449b138ed30a7ad332c7af6349255709ea160'), (5416, 5342, 299, 'a66a5bde2e0e9943392bad8fd02cae34b504a52a82672f67ec6c646bbd18c5b2'), (5734, 5659, 586, '5c7a52ccd9d3bc698cd0842b970128bc58132bd5fd4a56f0a0bf3d5a73967ec7'), (6340, 6264, 3618, '15425f08abd9aef04dcce371397317c6702556dba4edb462a8bb256fd7b0f98d'))

def _pin(data):return len(data),hashlib.sha256(data).hexdigest()

def transform_source(source):
    if type(source) is not bytes or _pin(source)!=INPUT or b'\r' in source:
        raise ValueError('exact current C shipping source required for capture metadata')
    parts=[];cursor=written=0
    for old_at,new_at,old,new,role in EDITS:
        if old_at<cursor or source[old_at:old_at+len(old)]!=old or source.count(old)!=1:
            raise ValueError('fixed C capture role differs: '+role)
        gap=source[cursor:old_at]
        if written+len(gap)!=new_at:raise ValueError('C capture target offset differs')
        parts.extend((gap,new));written=new_at+len(new);cursor=old_at+len(old)
    parts.append(source[cursor:]);candidate=b''.join(parts)
    if _pin(candidate)!=OUTPUT:raise ValueError('C capture output differs')
    for old_at,new_at,length,digest in GAPS:
        old=source[old_at:old_at+length];new=candidate[new_at:new_at+length]
        if old!=new or hashlib.sha256(old).hexdigest()!=digest:
            raise ValueError('protected C capture complement differs')
    inverse=candidate
    for old_at,new_at,old,new,role in reversed(EDITS):
        if inverse[new_at:new_at+len(new)]!=new:raise ValueError('C capture inverse span differs')
        inverse=inverse[:new_at]+old+inverse[new_at+len(new):]
    if inverse!=source:raise ValueError('C capture full inverse differs')
    return candidate,{'stage':'C-shipping-capture-only-Move-bit3','input_bytes':INPUT[0],
        'input_sha256':INPUT[1],'output_bytes':OUTPUT[0],'output_sha256':OUTPUT[1],
        'literal_regions':len(EDITS),'protected_gaps':len(GAPS),'full_inverse':True,
        'all_gaps_equal':True,'private_Move_ABI_changed':True,'capture_bit':3,'FROM_mask':119,
        'TO_PROMO_TT17_unchanged':True,'quiet_promotion_tag':0,'PROMO_separate':True,
        'classes':{'quiet_castle_doublepush':0,'nonpawn_capture':1,'pawn_push':2,'pawn_capture_EP':3},
        'quiet_raw_Move_noise_unchanged':True,'old_new_TT_state_must_not_mix':True,
        'canonical_DEV_unchanged':True,'new_native_identity_required':True,'external_reads':0}
