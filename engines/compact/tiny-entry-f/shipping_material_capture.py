"""Fixed capture-only Move bit3 in the explicit F material/noise branch.

Runs after material-only names, not the full-F map. Current emitter c and
classifier O bind seven literal roles; this policy has no correction tail.
Class0 quiet/castle/double,1 nonpawn capture,2 pawn push,3 pawn capture/EP;
only2/3 promote. Quiet N/B/R/Q promotions keep capturebit0. FROM119 strips
only the metadata bit. Generated tagged moves remain intact through make,
TT17/fullkey/exact horizon, unit-window search and attaining MTD witnesses.
Only quiets consume the unchanged stateless noise. Raw EP is make-only.

The fixed whole source, seven regions, inverse and protected complement are
embedded here. Full/default and DEV branches bypass this helper. No external
experiment, report, executable, AST or network is an input.
"""
import hashlib
INPUT_BYTES=8677
INPUT_SHA256='dd1599d4d414107383fd534701c3c7e58a4eb861a47ab174a405f7a8cc64335e'
OUTPUT_BYTES=8602
OUTPUT_SHA256='3752a0c745efb63a2c1ba08974789c10dc56b815428d11903fbc8f2b5461ea3b'
COMPLEMENT_BYTES=8338
COMPLEMENT_SHA256='45d040c81f266d688ec06601a4ddd07a4b33ba0c960785a50f9bde12b845d803'
REGIONS=({'new': '#define FROM(m) ((m)&119)',
  'new_end': 410,
  'new_sha256': '6c8a702f9bc593b323190dcb631d80e81a75a3a9232c6b0dc71864c108b37791',
  'new_start': 385,
  'old': '#define FROM(m) ((m)&127)',
  'old_end': 410,
  'old_sha256': '02f4329f5e62be74ef0c9b9365f7036c5869252297577171066d896b4eeaf0b5',
  'old_start': 385,
  'role': 'FROM decode'},
 {'new': 'static void c(Y*a,int*n,int zA,int to,int d){int f=d>1&&((to>>4)==0||(to>>4)==7);for(int '
         'z=f?2:0;z<=(f?5:0);z++){if(*n>=MOVES)abort();a[(*n)++]=MOVE(zA,to,z)|(d&1)*8;}}',
  'new_end': 2577,
  'new_sha256': '2328c9eea8bc434d709e8a524165c26f8babadcc520a02e3daa44285858da840',
  'new_start': 2409,
  'old': 'static void c(Y*a,int*n,int zA,int to,int d){int f=d&&((to>>4)==0||(to>>4)==7);for(int '
         'z=f?2:0;z<=(f?5:0);z++){if(*n>=MOVES)abort();a[(*n)++]=MOVE(zA,to,z);}}',
  'old_end': 2567,
  'old_sha256': '49d93ade0e554cf0d92d84dc29a6eb85c2d75d305024ffe5c65ee9732275cfbe',
  'old_start': 2409,
  'role': 'capture-only emitter'},
 {'new': 'c(f,&n,j,l,2);',
  'new_end': 2782,
  'new_sha256': 'bc42b4bac5fc20a61f578d874b530029bca7395de2a084ac71033db5ced9b03f',
  'new_start': 2768,
  'old': 'c(f,&n,j,l,1);',
  'old_end': 2772,
  'old_sha256': 'a41ca90e3c9fbaf6aca8d2b6419346349d61d63bfd3e7c3ef3de972446111d58',
  'old_start': 2758,
  'role': 'single pawn push class'},
 {'new': 'c(f,&n,j,q,a==1?3:!!t);',
  'new_end': 3073,
  'new_sha256': '4b3db7a21adc14eaa34856c3dfcc7466333a95a1c2e44469440d811454d67e04',
  'new_start': 3050,
  'old': 'c(f,&n,j,q,a==1);',
  'old_end': 3057,
  'old_sha256': 'b3709d070619f175f98335683c5ec621cd894976dfb2e3285159cf1d40952e15',
  'old_start': 3040,
  'role': 'geometric emission class'},
 {'new': '',
  'new_end': 3934,
  'new_sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
  'new_start': 3934,
  'old': 'static int O(const za*p,Y m){return p->b[TO(m)]||(abs(p->b[FROM(m)])==1&&TO(m)==p->e);}',
  'old_end': 4005,
  'old_sha256': 'c4d13a5dc9d1e7935a8aaaca14471739b56aff0172425ca5637a5eb7a24fc501',
  'old_start': 3918,
  'role': 'capture function removal'},
 {'new': 'm==G?1000000:m&8?',
  'new_end': 4589,
  'new_sha256': '5034ce58055b6e18045cf1fd042d930206ccae2a44dd7ed2e73ca50814f7e36c',
  'new_start': 4572,
  'old': 'm==G?1000000:O(p,m)?',
  'old_end': 4663,
  'old_sha256': 'a68dc82b86aedea9151f56893e381e017ade9a315f9194327e6d3ba159371b3d',
  'old_start': 4643,
  'role': 'capture ordering'},
 {'new': 'P=(m&8)||PROMO(m)',
  'new_end': 4848,
  'new_sha256': '0c8a7d7f500aa6d4414bcb2072429d1a27b46ab458973e019f744b2631351f7e',
  'new_start': 4831,
  'old': 'P=O(p,m)||PROMO(m)',
  'old_end': 4923,
  'old_sha256': '893ec61a6b377d7fe34824b42d2b2fec91d462000a828767641e9d19caa9983b',
  'old_start': 4905,
  'role': 'QS tactical flag'})
PROTECTED=('g(p,MOVE(q,p->e,0),&t)', '(m*37u+w->a*19u)%17', 'J==(a>0?a:0)', 'I!=2+(H>=d)', 'F&131071', 'D=p->s*p->v')
def sha(b):return hashlib.sha256(b).hexdigest()
def need(ok,message):
 if not ok:raise ValueError(message)
def transform_source(source):
 need(type(source) is bytes and len(source)==INPUT_BYTES and sha(source)==INPUT_SHA256,'exact material/noise source required')
 parts=[];gaps=[];last=offset=0
 for r in REGIONS:
  a,b=r['old_start'],r['old_end'];old,new=r['old'].encode(),r['new'].encode()
  need(a>=last and source[a:b]==old and source.count(old)==1,'role preimage differs')
  need(sha(old)==r['old_sha256'] and sha(new)==r['new_sha256'],'literal pin differs')
  gap=source[last:a];gaps.append(gap);parts.extend((gap,new));offset+=len(gap)
  need((offset,offset+len(new))==(r['new_start'],r['new_end']),'new role range differs')
  offset+=len(new);last=b
 parts.append(source[last:]);gaps.append(source[last:]);result=b''.join(parts);inverse=result
 for r in reversed(REGIONS):
  a,b=r['new_start'],r['new_end'];need(inverse[a:b]==r['new'].encode(),'inverse span differs');inverse=inverse[:a]+r['old'].encode()+inverse[b:]
 need(inverse==source and len(result)==OUTPUT_BYTES and sha(result)==OUTPUT_SHA256,'output/inverse differs')
 c=b''.join(gaps);need(len(c)==COMPLEMENT_BYTES and sha(c)==COMPLEMENT_SHA256,'complement differs')
 for v in PROTECTED:need(source.count(v.encode())==result.count(v.encode())==1,'material/MTD/rawEP consumer differs')
 return result,{'regions':REGIONS,'exact_inverse':True,'protected_complement_bytes':COMPLEMENT_BYTES,'protected_complement_sha256':COMPLEMENT_SHA256,'capture_bit':3,'FROM_mask':119,'TT_move_bits':17,'quiet_promotion_capturebit':0,'current_material_policy_unchanged':True,'optional_correction_tail_absent':True,'fullF_offsets_or_proof_replayed':False,'stage':'material-only-after-names','full_and_DEV_bypass':True,'private_Move_ABI_changed':True}
