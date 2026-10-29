"""Replay one fixed E shipping capture-only Move-bit3 representation.

Generated valid 0x88 from squares leave bit3 free. FROM119 removes the
capture tag; TO, PROMO and the internal TT Move17 boundary stay unchanged.
Quiet promotion remains tag0 with PROMO tested separately. E19 weights,
S/R feature bodies, Board accumulators and quiet raw-Move noise are in
the protected complement. Capture moves bypass the raw quiet-noise tier.
This changes the private Move/TT ABI: use a fresh TT and never mix old/new
payloads. Raw native/Move/TT identity or runtime qualification is not claimed.
Canonical/DEV bypass this exact shipping stage. Every rule below is an
owned literal; the function reads no files and starts no processes.
"""
import hashlib

INPUT=(10286,'d5dcfbc1abb8ffb61283680b84cd84a175fc5fe68515ea8156ff86ba4c8e38bd')
OUTPUT=(10210,'060847dbe19b898d5a7a0f7b49ee35b2338529abb2b63073798453db227ee147')
COMPLEMENT=(9938,'31dd351095d2ba79ef18b3931381bc9afa12f5a1c218c69b84078351cb35b877')
EDITS=(
    (344,344,b'#define FROM(m) ((m)&127)',b'#define FROM(m) ((m)&119)','FROM strips reserved capture bit3'),
    (2684,2684,b'static void g(T*a,int*n,int zJ,int to,int d){int f=d&&!(to+16&96);for(int z=f?2:0;z<=(f?5:0);z++){if(*n>=MOVES)abort();a[(*n)++]=MOVE(zJ,to,z);}}',b'static void g(T*a,int*n,int zJ,int to,int d){int f=d>1&&!(to+16&96);for(int z=f?2:0;z<=(f?5:0);z++){if(*n>=MOVES)abort();a[(*n)++]=MOVE(zJ,to,z)|(d&1)*8;}}','capture-only generator classes'),
    (3020,3030,b'g(f,&n,m,q,1);',b'g(f,&n,m,q,2);','quiet single pawn push class2'),
    (3309,3319,b'g(f,&n,m,v,a==1);',b'g(f,&n,m,v,a==1?3:!!w);','pawn capture EP class3/nonpawn target class'),
    (4796,4812,b'static int l(const za*p,T m){return p->b[TO(m)]||(abs(p->b[FROM(m)])==1&&TO(m)==p->e);}',b'','remove repeated mailbox capture predicate'),
    (5648,5577,b'm==tt?1000000:l(p,m)?',b'm==tt?1000000:m&8?','capture ordering tier'),
    (5938,5864,b'yu=l(p,m)||PROMO(m)',b'yu=(m&8)||PROMO(m)','QS/reduction tactical predicate'),
    (6544,6469,b'!l(p,zj)&&!PROMO(zj)',b'!(zj&8)&&!PROMO(zj)','quiet correction eligibility'),
)
GAPS=(
    (0,0,344,'c10fb12b282b19ede8a119457b98034731b6d14681756d0f370231df1d868685'),
    (369,369,2315,'9e33b474486295bd4ccec092c9c792275780884efdf3929338d408f8b112da4d'),
    (2829,2839,191,'4a35bb428bb2f63eb1334b834513affc44c7aa0b5f2556669e8b17ba01217bd7'),
    (3034,3044,275,'e8c16243023cba2d0be0d0661bdd55ec2c9d36682fb81ea38d915accf3565d5e'),
    (3326,3342,1470,'f2444da9f21381b597e0ee2632f50e5ebe3c39833fa81cf6804e1b47636018c5'),
    (4883,4812,765,'2b2a3fdb4b2b99ed28888f68d4f5c09682d32c7e7c4524213632c35d0dec57bd'),
    (5669,5595,269,'ab262a0e1f6e57f98984f4d9b55ea525cb753f3b31ce7a82324bdb34c20101e8'),
    (5957,5882,587,'4eaa18241207ef0c7d337b92c538f80cb1eafcbddc4f117c4e2db1b3a421fdbb'),
    (6564,6488,3722,'e23f158dd959fe1d08d77f930b0031ce15f77c7d57a238267a907b789a67210a'),
)

def _pin(data):return len(data),hashlib.sha256(data).hexdigest()

def transform_source(source):
    """Replay exactly eight source edits, verifying all protected bytes."""
    if type(source) is not bytes or _pin(source)!=INPUT or b'\r' in source:
        raise ValueError('exact current E shipping source required for capture metadata')
    if len(EDITS)!=8 or len(GAPS)!=9:
        raise ValueError('fixed E capture edit/gap schema differs')
    parts=[];old_gaps=[];cursor=written=0
    for old_at,new_at,old,new,role in EDITS:
        if old_at<cursor or source[old_at:old_at+len(old)]!=old or source.count(old)!=1:
            raise ValueError('fixed E capture role differs: '+role)
        gap=source[cursor:old_at]
        if written+len(gap)!=new_at:
            raise ValueError('fixed E capture target offset differs')
        parts.extend((gap,new));old_gaps.append(gap)
        written=new_at+len(new);cursor=old_at+len(old)
    parts.append(source[cursor:]);old_gaps.append(source[cursor:])
    candidate=b''.join(parts)
    inverse=[];new_gaps=[];cursor=previous_old=0
    for old_at,new_at,old,new,role in EDITS:
        gap=candidate[cursor:new_at]
        if gap!=source[previous_old:old_at] or candidate[new_at:new_at+len(new)]!=new:
            raise ValueError('fixed E capture inverse literal/gap differs: '+role)
        inverse.extend((gap,old));new_gaps.append(gap)
        cursor=new_at+len(new);previous_old=old_at+len(old)
    inverse.append(candidate[cursor:]);new_gaps.append(candidate[cursor:])
    if (_pin(candidate)!=OUTPUT or b''.join(inverse)!=source or old_gaps!=new_gaps
            or len(old_gaps)!=9 or _pin(b''.join(old_gaps))!=COMPLEMENT):
        raise ValueError('fixed E capture output/inverse/nine gaps/complement differs')
    for gap,(old_at,new_at,length,digest) in zip(old_gaps,GAPS):
        if (len(gap)!=length or source[old_at:old_at+length]!=gap
                or candidate[new_at:new_at+length]!=gap or _pin(gap)!=(length,digest)):
            raise ValueError('fixed E capture protected gap pin differs')
    return candidate,{
        'family':'E','stage':'E-shipping-capture-only-Move-bit3',
        'input_bytes':INPUT[0],'input_sha256':INPUT[1],
        'output_bytes':OUTPUT[0],'output_sha256':OUTPUT[1],
        'raw_delta':-76,'edits':8,'literal_regions':8,'gap_count':9,'protected_gaps':9,
        'full_inverse':True,'all_gaps_equal':True,'each_gap_pin_checked':True,
        'complement_bytes':COMPLEMENT[0],'complement_sha256':COMPLEMENT[1],
        'private_Move_ABI_changed':True,'capture_bit':3,'FROM_mask':119,
        'TO_PROMO_TT17_unchanged':True,'quiet_promotion_tag':0,'PROMO_separate':True,
        'classes':{'quiet_castle_doublepush':0,'nonpawn_capture':1,'pawn_push':2,'pawn_capture_EP':3},
        'quiet_raw_Move_noise_unchanged':True,'E19_weights_S_R_and_accumulators_protected':True,
        'fresh_TT_required':True,'old_new_TT_state_must_not_mix':True,
        'canonical_DEV_unchanged':True,'native_Move_TT_raw_identity_claimed':False,
        'runtime_qualification_claimed':False,'external_reads':0,
        'compiler_codec_engine_executed_by_transform':0}
