"""Pure late E terminal sharing, after shipping_center and only in shipping.

Terminal mask0/1/2/3 shares legal generation/iteration. Terminal scoring,
private ordering/work and timing may differ; no ordinary-search change is
claimed from snapshots. This stage reads no research artifact or executable.
"""
import hashlib

INPUT_BYTES=10190
INPUT_SHA='34cc868b06252cb25a58be54d9e8fecb26cd6705d159533363ab57aa96b70bcd'
OUTPUT_BYTES=10142
OUTPUT_SHA='260c30750d1ee11a569d1d8916a9d7fb38883df80571559f16e1b5a05cfb783c'
SPANS=((5085, 5085, b'if(x||n==PLY-1){za q;for(int i=0;i<Y;i++)if(e(p,W[i],&q)){if(!x){atomic_store(&stopped,1);}return 0;}return v?-MATE+n:0;}', b'x|=2*(n==PLY-1);'), (5240, 5135, b'zA=G(zP,0);', b'zA=x?0:G(zP,0);'), (5440, 5339, b'int ye=a<=0&&!v;', b'int ye=!x&&a<=0&&!v;'), (5793, 5696, b'if(!e(p,m,&q))continue;++Z;', b'if(!e(p,m,&q))continue;if(x){if(x==2)atomic_store(&stopped,1);return 0;}++Z;'))
GAPS=((0, 0, 5085, '7c95a261029c7bf14a0814d7bf707e822923fcdc5aebd563b2c247fbe777d78d'), (5206, 5101, 34, 'b414f55ee8c5b82296ef3862d4917410afe92f9636c4d95cc52e2b03f4a5d896'), (5251, 5150, 189, 'c08bc392e78c69f118a70ff489ae78c04b39ba428150570924016d67b6cb1950'), (5456, 5359, 337, 'a3cf546d0c8bdcf0d239ec8643f7e1762ca90627799873bbb7f89b0f0bf64c34'), (5820, 5772, 4370, '2b523191d74a580dec6c83a3c023c2ff5d487104dac5a71da50840312dbbe186'))
COMPLEMENT_BYTES=10015
COMPLEMENT_SHA='da9f03bdbed0852b6959492949b67a6d03ac0a3be0a326c29172048738450a30'
METADATA={'family': 'E', 'stage': 'late-shipping-terminal-sharing', 'input_bytes': 10190, 'input_sha256': '34cc868b06252cb25a58be54d9e8fecb26cd6705d159533363ab57aa96b70bcd', 'output_bytes': 10142, 'output_sha256': '260c30750d1ee11a569d1d8916a9d7fb38883df80571559f16e1b5a05cfb783c', 'raw_delta': -48, 'owned_regions': 4, 'protected_gaps': 5, 'full_inverse': True, 'all_gaps_equal': True, 'protected_complement_bytes': 10015, 'protected_complement_sha256': 'da9f03bdbed0852b6959492949b67a6d03ac0a3be0a326c29172048738450a30', 'terminal_mask': {'ordinary': 0, 'draw': 1, 'cap_only': 2, 'draw_and_cap': 3}, 'actual_call_domain': 'initialized production zd Worker, valid za Board, n0..127 and yb0..12; generated moves from h and legal e on private child', 'preserved': 'draw precedence; cap-only stopped store; no-legal mate/stale; terminal entire G-call suppression; QS/standpat bypass; first legal return before ++Z/path/learners/TT-store/root publication; logical19/physical21 coefficients and update order; unchanged nonterminal search', 'terminal_private_observation_delta': 'terminal paths now score/sort private generated moves before legal make; private first legal child/order/work, wall time and SMP interleaving can differ', 'state_contract': 'parent Board and public/owned search state preserved in terminal return domain; no equality claim for private ordering/scratch or transient timing', 'canonical_DEV': 'caller bypass; earlier canonical/model/DEV reference admission unchanged', 'native_entire_bytes_equal_to_predecessor': False, 'runtime_qualification_claimed': False, 'external_reads': 0, 'compiler_codec_engine_executed_by_transform': 0}

def _sha(data):return hashlib.sha256(data).hexdigest()

def transform_source(source):
    if type(source) is not bytes or len(source)!=INPUT_BYTES or _sha(source)!=INPUT_SHA:
        raise ValueError('exact final E centered-feature shipping source required')
    result=[];end=0
    for old_at,new_at,old,new in SPANS:
        if source[old_at:old_at+len(old)]!=old or source.count(old)!=1:
            raise ValueError('fixed E terminal literal region differs')
        result.extend((source[end:old_at],new));end=old_at+len(old)
    result=b''.join(result)+source[end:]
    rest=[]
    for old_at,new_at,size,digest in GAPS:
        a=source[old_at:old_at+size];b=result[new_at:new_at+size]
        if a!=b or len(a)!=size or _sha(a)!=digest:
            raise ValueError('terminal protected gap differs')
        rest.append(a)
    complement=b''.join(rest)
    if len(complement)!=COMPLEMENT_BYTES or _sha(complement)!=COMPLEMENT_SHA:
        raise ValueError('terminal protected complement differs')
    inverse=[];end=0
    for old_at,new_at,old,new in SPANS:
        if result[new_at:new_at+len(new)]!=new:
            raise ValueError('terminal output region differs')
        inverse.extend((result[end:new_at],old));end=new_at+len(new)
    if b''.join(inverse)+result[end:]!=source:
        raise ValueError('terminal exact full inverse differs')
    if len(result)!=OUTPUT_BYTES or _sha(result)!=OUTPUT_SHA:
        raise ValueError('fixed E terminal candidate differs')
    return result,dict(METADATA)
