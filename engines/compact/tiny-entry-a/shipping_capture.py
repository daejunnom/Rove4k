"""A-only final capture-bit stage after lexical names; DEV bypasses it.

Eight literal regions change the private generated Move ABI, not its decoded
coordinates. Capture-only bit3 excludes quiet promotions, including their old
history/continuation/noise tier; this is not B's promotion-inclusive tag.
All runtime inputs are ordinary source bytes passed by the builder. No file,
experiment, report, artifact, AST tool or network input is read by this module.
"""
import hashlib

READABLE = '71f9ff6ce1b7f555ad85c3bf49766381c0627315da94acf0c49eeee7bee4a734'
INPUT_BYTES = 9470
INPUT_SHA256 = '90b7d08d450ff6865bdc07873693f90f549dcf3d3a5cf411ad37c7609dd5c527'
OUTPUT_BYTES = 9391
OUTPUT_SHA256 = 'b4aa345388c20d4701732a2ce561bd2714b1f1d26b756aa79c05ae8dfc006cf8'
COMPLEMENT_BYTES = 9130
COMPLEMENT_SHA256 = '2e0f59026568f4fd69f5bf1c438cf8e47d21119a2ebc260d03aa05865423a92b'
REGIONS = ({'role': 'FROM decode',
  'old_start': 402,
  'old_end': 427,
  'new_start': 402,
  'new_end': 427,
  'old': '#define FROM(m) ((m)&127)',
  'new': '#define FROM(m) ((m)&119)',
  'old_sha256': '02f4329f5e62be74ef0c9b9365f7036c5869252297577171066d896b4eeaf0b5',
  'new_sha256': '6c8a702f9bc593b323190dcb631d80e81a75a3a9232c6b0dc71864c108b37791'},
 {'role': 'capture-only emitter',
  'old_start': 2630,
  'old_end': 2766,
  'new_start': 2630,
  'new_end': 2776,
  'old': 'static void bh(Y*B,int*n,int o,int to,int a){int d=a&&((to>>4)==0||(to>>4)==7);for(int '
         'z=d?2:0;z<=(d?5:0);z++){B[(*n)++]=MOVE(o,to,z);}}',
  'new': 'static void bh(Y*B,int*n,int o,int to,int a){int d=a>1&&((to>>4)==0||(to>>4)==7);for(int '
         'z=d?2:0;z<=(d?5:0);z++){B[(*n)++]=MOVE(o,to,z)|(a&1)*8;}}',
  'old_sha256': 'd08b40d09f75abbfb118d38723ec3afa32fd2e790fbe0b2d24eb415cacd7a5ac',
  'new_sha256': '9ae956ab3b2abb49d754ea77b634222ee0f92a784e43a59aea8df46c8e079943'},
 {'role': 'pawn push class',
  'old_start': 2957,
  'old_end': 2972,
  'new_start': 2967,
  'new_end': 2982,
  'old': 'bh(B,&n,o,g,1);',
  'new': 'bh(B,&n,o,g,2);',
  'old_sha256': '11ecb2aa0171c196d5c266cc8a94b12aba25a3e2bdc91f8d038fce3330939322',
  'new_sha256': 'a670aeb83574590a7ea388b0cbb65da731b9acaf9e2105fbb6f13b5214d974ef'},
 {'role': 'geometric emission class',
  'old_start': 3241,
  'old_end': 3259,
  'new_start': 3251,
  'new_end': 3275,
  'old': 'bh(B,&n,o,q,a==1);',
  'new': 'bh(B,&n,o,q,a==1?3:!!t);',
  'old_sha256': '546024efa8684451ce6896574fdab52b3b59ca8a7093de87bf5b30241882003c',
  'new_sha256': 'eb98b0c882f561403dfc855d39a67c068d60e807ede1f0ff4f5704f754f15ab7'},
 {'role': 'remove old mailbox capture classifier',
  'old_start': 4216,
  'old_end': 4303,
  'new_start': 4232,
  'new_end': 4232,
  'old': 'static int ax(const E*p,Y m){return p->b[TO(m)]||(abs(p->b[FROM(m)])==1&&TO(m)==p->e);}',
  'new': '',
  'old_sha256': '43f95e08484bf06957c5cfa9714d89da00de7ef3d4308e2db15760568cb77fed',
  'new_sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'},
 {'role': 'capture ordering predicate',
  'old_start': 5019,
  'old_end': 5040,
  'new_start': 4948,
  'new_end': 4965,
  'old': 'm==J?1000000:ax(p,m)?',
  'new': 'm==J?1000000:m&8?',
  'old_sha256': 'f25c35182c30587ec64a84ae0af0fbc14ef03ee4c794f50401e6c67485a84191',
  'new_sha256': 'baf83cbb5ce4241bf02eaf288e989af09b16e53eedafedc8fff6be3d7cee1f32'},
 {'role': 'QS reduction tactical flag',
  'old_start': 5331,
  'old_end': 5350,
  'new_start': 5256,
  'new_end': 5273,
  'old': 'Q=ax(p,m)||PROMO(m)',
  'new': 'Q=(m&8)||PROMO(m)',
  'old_sha256': '55b4ac2559ce0c49f881b7b84a1a5c2285ff4d07f6b9c25b80bc93760bec40fa',
  'new_sha256': '8f5004675f528912a1bd2ceadf9c7700c9ae30613521a9a2150e4e7f601c6eb5'},
 {'role': 'correction capture guard',
  'old_start': 5921,
  'old_end': 5940,
  'new_start': 5844,
  'new_end': 5861,
  'old': '!ax(p,N)&&!PROMO(N)',
  'new': '!(N&8)&&!PROMO(N)',
  'old_sha256': 'ad623de15cdf9608d7f657b250a8983b6d63104180241de2a5bef10a22b72b27',
  'new_sha256': 'fc1e57d0759b545593e85cc6db9ab0ae8660ff167c18eab664d861dfc21f49ce'})


def sha(data):
    return hashlib.sha256(data).hexdigest()


def need(value, message):
    if not value:
        raise ValueError(message)


def transform_source(source, *, readable):
    need(type(readable) is bytes and sha(readable) == READABLE,
         'exact canonical A readable source required before capture-bit stage')
    need(type(source) is bytes and len(source) == INPUT_BYTES and sha(source) == INPUT_SHA256,
         'exact post-lexical A4739 shipping source required')
    pieces, gaps = [], []
    last = offset = 0
    for row in REGIONS:
        a, b = row['old_start'], row['old_end']
        old, new = row['old'].encode(), row['new'].encode()
        need(a >= last and source[a:b] == old and source.count(old) == 1,
             'capture-bit source span/order differs: ' + row['role'])
        need(sha(old) == row['old_sha256'] and sha(new) == row['new_sha256'],
             'capture-bit literal region identity differs')
        gap = source[last:a]
        gaps.append(gap)
        pieces.extend((gap, new))
        offset += len(gap)
        need(row['new_start'] == offset and row['new_end'] == offset + len(new),
             'capture-bit output region offset differs')
        offset += len(new)
        last = b
    pieces.append(source[last:])
    gaps.append(source[last:])
    candidate = b''.join(pieces)
    inverse = candidate
    for row in reversed(REGIONS):
        a, b = row['new_start'], row['new_end']
        need(inverse[a:b] == row['new'].encode(), 'capture-bit inverse preimage differs')
        inverse = inverse[:a] + row['old'].encode() + inverse[b:]
    need(inverse == source and len(candidate) == OUTPUT_BYTES and sha(candidate) == OUTPUT_SHA256,
         'capture-bit exact output or inverse differs')
    complement = b''.join(gaps)
    need(len(complement) == COMPLEMENT_BYTES and sha(complement) == COMPLEMENT_SHA256,
         'capture-bit protected source complement differs')
    return candidate, {
        'family': 'A', 'stage': 'shipping-after-lexical-only',
        'input_bytes': INPUT_BYTES, 'input_sha256': INPUT_SHA256,
        'output_bytes': OUTPUT_BYTES, 'output_sha256': OUTPUT_SHA256,
        'regions': REGIONS, 'exact_inverse': True,
        'protected_complement_bytes': COMPLEMENT_BYTES,
        'protected_complement_sha256': COMPLEMENT_SHA256,
        'FROM_mask': 119, 'capture_bit': 3, 'TT_move_bits': 17,
        'emitter_classes': {'quiet_castle_doublepush': 0, 'nonpawn_capture': 1,
                            'single_pawn_push': 2, 'pawn_capture_or_EP': 3},
        'quiet_promotion_capture_bit': 0, 'B_promotion_inclusive_tag_imported': False,
        'private_Move_ABI_changed': True, 'old_full_native_equality_claimed': False,
        'F_autoapplication': False, 'DEV_not_transformed': True,
        'runtime_receipts_are_not_generation_inputs': True,
    }
