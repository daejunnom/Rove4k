"""Fixed F shipping capture-only Move bit3 after global-function spellings.

Generated 0x88 squares leave bit3 free; FROM masks it out with119. Class0
is quiet/castle/double push,1 nonpawn capture,2 pawn push,3 pawn capture/EP.
Only classes2/3 promote; N/B/R/Q quiet promotion retains capturebit0.
PROMO and TO, coherent full-key TT17 payload, full-depth MTD/unit-window
bounds and lower-witness publication remain exact. Quiet history/noise and
converged correction only consume moves whose capturebit is0. The one raw EP
constructor is make-only, never a classification ingress. This private Move
ABI is not interoperable with an untagged move producer or B's promo-OR tag.

The eight literal regions, inverse and all remaining bytes are fixed here.
DEV bypasses this stage. No experiment, report, executable, AST or network is
an input; full source pins are admission guards, not a generic minifier.
"""
import hashlib
INPUT_BYTES=9318
INPUT_SHA256='e280d859127c5d250ca912cfe636518fd088813ffce4266589fa6f04b7e87424'
OUTPUT_BYTES=9242
OUTPUT_SHA256='61e0f5c7f79b6c45efd225624def06bb1ac3c1b1edfe1cd0443c0f3498a4a447'
COMPLEMENT_BYTES=8959
COMPLEMENT_SHA256='a4d59cf5dc04c69c94d69e6b775506f9720df14458aeca83400db4f33a99628c'
REGIONS=({'role': 'FROM decode',
  'old_start': 385,
  'old_end': 410,
  'new_start': 385,
  'new_end': 410,
  'old': '#define FROM(m) ((m)&127)',
  'new': '#define FROM(m) ((m)&119)',
  'old_sha256': '02f4329f5e62be74ef0c9b9365f7036c5869252297577171066d896b4eeaf0b5',
  'new_sha256': '6c8a702f9bc593b323190dcb631d80e81a75a3a9232c6b0dc71864c108b37791'},
 {'role': 'capture-only emitter',
  'old_start': 2556,
  'old_end': 2714,
  'new_start': 2556,
  'new_end': 2724,
  'old': 'static void e(Y*a,int*n,int zA,int to,int d){int f=d&&((to>>4)==0||(to>>4)==7);for(int '
         'z=f?2:0;z<=(f?5:0);z++){if(*n>=MOVES)abort();a[(*n)++]=MOVE(zA,to,z);}}',
  'new': 'static void e(Y*a,int*n,int zA,int to,int d){int f=d>1&&((to>>4)==0||(to>>4)==7);for(int '
         'z=f?2:0;z<=(f?5:0);z++){if(*n>=MOVES)abort();a[(*n)++]=MOVE(zA,to,z)|(d&1)*8;}}',
  'old_sha256': '7b0bc954527f09bbe1274e843e9f2b50727b053fd2b432506cacb439c129bb2e',
  'new_sha256': '03aa773258ed56630647c8fb39f7202efc24ad51a5294b489b83a7bdff8894c5'},
 {'role': 'single pawn push class',
  'old_start': 2905,
  'old_end': 2919,
  'new_start': 2915,
  'new_end': 2929,
  'old': 'e(f,&n,j,l,1);',
  'new': 'e(f,&n,j,l,2);',
  'old_sha256': '1b5600d2ecccdc71608ec4096cd3d6bc354e5cb9fd1a2d4003c3ae82500c3f2e',
  'new_sha256': '1b7fe91c6f2f7c78c43f5bf9d28c9cd193951c2b949edeb1d0030e0a9554da9e'},
 {'role': 'geometric emission class',
  'old_start': 3187,
  'old_end': 3204,
  'new_start': 3197,
  'new_end': 3220,
  'old': 'e(f,&n,j,q,a==1);',
  'new': 'e(f,&n,j,q,a==1?3:!!t);',
  'old_sha256': '92085c35ccc99a1c8b909b44e954888719510133abed61849a81c2eb0d7ff5b6',
  'new_sha256': 'b37af9ec60dd9d1da3728d994e447a0336df59bd8fe98244d682cea3eed9583c'},
 {'role': 'capture function removal',
  'old_start': 4142,
  'old_end': 4229,
  'new_start': 4158,
  'new_end': 4158,
  'old': 'static int v(const za*p,Y m){return p->b[TO(m)]||(abs(p->b[FROM(m)])==1&&TO(m)==p->e);}',
  'new': '',
  'old_sha256': '36d654f9c90438a34b64d70f1f5f6d6d9ae592da0ee492bd0d464321b529df36',
  'new_sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'},
 {'role': 'capture ordering',
  'old_start': 5031,
  'old_end': 5051,
  'new_start': 4960,
  'new_end': 4977,
  'old': 'm==G?1000000:v(p,m)?',
  'new': 'm==G?1000000:m&8?',
  'old_sha256': '87ee9c55b27395d3ef66af054d60901101371615183d6368eef66d5f03cce720',
  'new_sha256': '5034ce58055b6e18045cf1fd042d930206ccae2a44dd7ed2e73ca50814f7e36c'},
 {'role': 'QS tactical flag',
  'old_start': 5300,
  'old_end': 5318,
  'new_start': 5226,
  'new_end': 5243,
  'old': 'P=v(p,m)||PROMO(m)',
  'new': 'P=(m&8)||PROMO(m)',
  'old_sha256': 'd2a7c400b1a8c1c77978d8cb9435166ebb09181c291ca56973974321700462cd',
  'new_sha256': '0c8a7d7f500aa6d4414bcb2072429d1a27b46ab458973e019f744b2631351f7e'},
 {'role': 'converged witness correction guard',
  'old_start': 6183,
  'old_end': 6203,
  'new_start': 6108,
  'new_end': 6127,
  'old': '!v(p,yk)&&!PROMO(yk)',
  'new': '!(yk&8)&&!PROMO(yk)',
  'old_sha256': '237d9cefea69dfb33ca07da97f87603ef4de751c8787de5ed3d23e2c7a3cc751',
  'new_sha256': '552a3db0bc0d1f123a093f880bc53ac5f22efbfe2cb4394bb7047a9a49b456de'})

def sha(b):return hashlib.sha256(b).hexdigest()
def need(ok,message):
    if not ok:raise ValueError(message)

def transform_source(source):
    need(type(source) is bytes and len(source)==INPUT_BYTES and sha(source)==INPUT_SHA256,'exact current Fglobalnames source required')
    need(source.count(b'MOVE(')==3 and source.count(b'h(p,MOVE(q,p->e,0),&t)')==1,'protected raw EP make-only constructor differs')
    pieces=[];gaps=[];last=offset=0
    for row in REGIONS:
        a,b=row['old_start'],row['old_end'];old,new=row['old'].encode(),row['new'].encode()
        need(a>=last and source[a:b]==old and source.count(old)==1,'fixed role/order differs: '+row['role'])
        need(sha(old)==row['old_sha256'] and sha(new)==row['new_sha256'],'literal region identity differs')
        gap=source[last:a];gaps.append(gap);pieces.extend((gap,new));offset+=len(gap)
        need(row['new_start']==offset and row['new_end']==offset+len(new),'output offset differs')
        offset+=len(new);last=b
    pieces.append(source[last:]);gaps.append(source[last:]);result=b''.join(pieces);inverse=result
    for row in reversed(REGIONS):
        a,b=row['new_start'],row['new_end'];need(inverse[a:b]==row['new'].encode(),'inverse preimage differs');inverse=inverse[:a]+row['old'].encode()+inverse[b:]
    need(inverse==source and len(result)==OUTPUT_BYTES and sha(result)==OUTPUT_SHA256,'exact output or inverse differs')
    complement=b''.join(gaps);need(len(complement)==COMPLEMENT_BYTES and sha(complement)==COMPLEMENT_SHA256,'protected complement differs')
    for literal in (b'h(p,MOVE(q,p->e,0),&t)',b'(p->h^m)&1023',b'(p->h^yk)&1023',b'J==(a>0?a:0)',b'F&131071'):
        need(source.count(literal)==result.count(literal)==1,'protected F consumer differs')
    return result,{'regions':REGIONS,'exact_inverse':True,'protected_complement_bytes':COMPLEMENT_BYTES,'protected_complement_sha256':COMPLEMENT_SHA256,'FROM_mask':119,'capture_bit':3,'TT_move_bits':17,'quiet_promotion_tag':0,'direct_EP_raw_geometry_make_only':True,'namespace_offset_map_replayed':False,'private_Move_ABI_changed':True,'stage':'shipping-after-globalnames','DEV_bypasses_stage':True,'fixed_literal_regions':8,'new_native_identity':True}
