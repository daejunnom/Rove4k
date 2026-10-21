"""Pure fixed B/E shipping replay: derive history length from job base and ply.

Apply after the maintained lazy-fallback stage and bypass canonical/DEV.
The existing job history length is immutable during every search subtree.
Ordinary child calls retain ply+1 and the same key slot; same-position calls
retain their ply. The repetition loop retains the old nonnegative index set,
including short history with a large halfmove clock. Worker layout changes.
Only hashlib is used; no file, process, recipe or research receipt is read.
"""
import hashlib

_CASES = {'B': ((10491, 'a10c8545156da1bb2f0ceaddc7f19dcca1740baa9b962905404dacbda9b0c5f5'),
       (10451, '67603c505eec2377c4c4d96f19caf084178c104e44bd5d1aabed861341b55358'),
       ((589, 589, b'int zV;', b''),
        (5109,
         5102,
         b'int V=0,W=w->zV-1-p->zL;if(W<0)W=0;for(int i=w->zV-3;i>=W;i-=2)',
         b'int V=0,W=qh+n;for(int i=W-3;i>=0&&i>=W-1-p->zL;i-=2)'),
        (6443, 6426, b'w->zQ[w->zV++]=q.h;', b'w->zQ[W]=q.h;'),
        (6779, 6756, b'--w->zV;', b''),
        (7378, 7347, b'w->zV=qh;', b'')),
       ((0, 0, 589, 'aef0df1a1da5698cea9b400868ac212690a89ebfe622b1da52779328ecbeb4de'),
        (596, 589, 4513, '460b8db9582a993f56d10dedca024cbad304e5d9e6c17fcf21979ee4203e5e43'),
        (5172, 5155, 1271, '4b1c1f7aab621374214cbd5388e9978b5208b004e7432a15339ea2498f0396fd'),
        (6462, 6439, 317, '786927e70ca32a549ecc3d637561147f386d9961dd4a2c44e4e98df76216b925'),
        (6787, 6756, 591, '1ad54e89686713a542cc1c92b2825198d04532531a725429feb7d22addf504bb'),
        (7387, 7347, 3104, '5320cbe6fef416a0c88290e50e2a4cf4ba52e9601d79caf8078c31e1803447bf')),
       (10385, '6fadf64a9f742923bbc956d98dbf181d0634981fa3c7d8224e7494ce6525827e')),
 'E': ((10326, '9ad6770abe1b2b69e13d5f43bf3bcd06bc29914ca074d2320b200dcdfad91e99'),
       (10286, 'd5dcfbc1abb8ffb61283680b84cd84a175fc5fe68515ea8156ff86ba4c8e38bd'),
       ((580, 580, b'int zV;', b''),
        (5016,
         5009,
         b'int z=0,L=w->zV-1-p->zL;if(L<0)L=0;for(int i=w->zV-3;i>=L;i-=2)',
         b'int z=0,L=game_length+n;for(int i=L-3;i>=0&&i>=L-1-p->zL;i-=2)'),
        (6008, 6000, b'w->zQ[w->zV++]=q.h;', b'w->zQ[L]=q.h;'),
        (6295, 6281, b'--w->zV;', b''),
        (6883, 6861, b'w->zV=game_length;', b'')),
       ((0, 0, 580, 'ce6ba4447b777c2e4b8d64600940078a91ceaa5383cb4985bdb1c070b1bbce2c'),
        (587, 580, 4429, 'b8aae564eef1a86e573dbe5e20bb649625a4a23daad77ee68b4a53b49f0f2cf0'),
        (5079, 5071, 929, 'a025b7413f1369ead841cad31a3f79aaf3315b2b5757c5f368913226771cdb4a'),
        (6027, 6013, 268, 'd45dd1ff510d81fa3d8fbcd0848975cb8da65d7115962fc4ee714e91d653b7f7'),
        (6303, 6281, 580, '0396868f261fb9a91772012ab20fedd6e30fbc8c5aa23095270aacf362b1dcae'),
        (6901, 6861, 3425, '43a1e1b964cb4d4589b181d11be1613f86e49ee947f877bad2385429faba8863')),
       (10211, 'b99ea5a1da970ef5577d6287ed4bbb15e5b446cd927a5b1dc140aec1349bb8f2'))}

def _pin(data):return len(data),hashlib.sha256(data).hexdigest()


def transform_source(source,*,family):
    """Replay one fixed five-span history form and check its full complement."""
    if type(source) is not bytes or family not in _CASES:
        raise ValueError('fixed B/E history family/source required')
    before,after,edits,gaps,complement_pin=_CASES[family]
    if _pin(source)!=before:
        raise ValueError('fixed late shipping history input differs')
    parts=[];cursor=written=0
    for old_at,new_at,old,new in edits:
        if old_at<cursor or source[old_at:old_at+len(old)]!=old or source.count(old)!=1:
            raise ValueError('owned history cursor/loop/key/reset span differs')
        gap=source[cursor:old_at]
        if written+len(gap)!=new_at:
            raise ValueError('fixed history output position differs')
        parts.extend((gap,new));written=new_at+len(new);cursor=old_at+len(old)
    parts.append(source[cursor:]);result=b''.join(parts)
    if _pin(result)!=after:
        raise ValueError('fixed history output differs')
    complement=[]
    for old_at,new_at,length,digest in gaps:
        old=source[old_at:old_at+length];new=result[new_at:new_at+length]
        if old!=new or hashlib.sha256(old).hexdigest()!=digest:
            raise ValueError('protected history gap differs')
        complement.append(old)
    if _pin(b''.join(complement))!=complement_pin:
        raise ValueError('protected history complement differs')
    inverse=result
    for old_at,new_at,old,new in reversed(edits):
        if inverse[new_at:new_at+len(new)]!=new:
            raise ValueError('fixed history inverse position differs')
        inverse=inverse[:new_at]+old+inverse[new_at+len(new):]
    if inverse!=source:
        raise ValueError('full history inverse differs')
    return result,{
        'family':family,'stage':'late-shipping-history-length-from-job-base-and-ply',
        'input_bytes':before[0],'input_sha256':before[1],
        'output_bytes':after[0],'output_sha256':after[1],
        'raw_delta':after[0]-before[0],'owned_regions':5,'protected_gaps':6,
        'full_inverse':True,'all_gaps_equal':True,
        'protected_complement_bytes':complement_pin[0],
        'protected_complement_sha256':complement_pin[1],
        'private_Worker_cursor_reset_push_pop_removed':True,
        'entry_length':'immutable job history length plus unchanged recursion ply',
        'public_job_length_range':[1,4096],'entry_ply_range':[0,127],
        'key_capacity':4224,'ordinary_child_key_index_and_ply_preserved':True,
        'same_position_call_ply_and_history_length_preserved':True,
        'nonnegative_repetition_index_set_preserved':True,
        'recursive_arguments_and_other_logic_byte_protected':True,
        'job_publication_pool_and_lazy_fallback_byte_protected':True,
        'Worker_layout_and_native_identity_unchanged':False,
        'canonical_DEV':'caller bypass',
        'external_reads':0,'AST':False,'compiler_codec_engine_executed_by_transform':0,
    }
