"""Pure fixed shipping replay: derive fallback from the immutable completed root.

The caller applies this after its maintained final shipping source stage and
bypasses it for canonical DEV and reduced actual F policies. Each table owns
only a global fallback declaration, its eager GO setup, and its sole result
consumer. Result still runs under the existing last-worker mutex before flush
and completion publication. No file, process, recipe or receipt is read here.
"""
import hashlib

_CASES = {'A': ((9011, '4c9e83760ad39668239be2b6f8bcd8dd76f24d64bf8660ec2a95f7a4139c55ea'),
       (8995, 'a52d492bcdfe623863153b9d5d651c6218fa1511e3253c3d6efe80b81c017101'),
       ((6322, 6322, b'static Y qe;', b''),
        (6779, 6767, b'Y H=w->H?w->H:qe;', b'E fb;Y H=w->H?w->H:i(&ql,0,&fb);'),
        (8112, 8115, b'E c;qe=i(&ql,0,&c);', b'')),
       ((0, 0, 6322, '900ed82951218726595f4caea7debd5d900d3c3279f7169935f80598508b2696'),
        (6334, 6322, 445, '8b5ccf20bb4a66ff44a8d48ad4cccf38b898dea932aabe1ff70f9de761bfb55f'),
        (6796, 6799, 1316, '491a087890c24e67f47c2cc87bfe90d417c2dcd784923778a165de723bc7db39'),
        (8131, 8115, 880, '92cb01dbeac77b58bc1fc9591946b474288989eb1e69f995b26573af55954b1d'))),
 'B': ((10507, '8c7a110e5282e75128cf76c4b706a0c79ca5890be25a93e38f1734e9fb53089e'),
       (10491, 'a10c8545156da1bb2f0ceaddc7f19dcca1740baa9b962905404dacbda9b0c5f5'),
       ((7741, 7741, b'static N qe;', b''),
        (8202, 8190, b'N a=w->zi?w->zi:qe;', b'za fb;N a=w->zi?w->zi:H(&ql,0,&fb);'),
        (9540, 9544, b'za c;qe=H(&ql,0,&c);', b'')),
       ((0, 0, 7741, 'c96b9fac3fdcb9c5d8bb1bcac55dcd12a1d7818839007d90f04dd03d6e020302'),
        (7753, 7741, 449, '06cf09b729c46e1379486d2057b703a20f16ad6a983b59fd156295d073a12558'),
        (8221, 8225, 1319, 'b94e423e262bd30949c2ed2554f36e7cffff4a9a86557a6c720fccd5b79676c0'),
        (9560, 9544, 947, '545ce7e5ee4df545cc88e1be96910ce061aec45491688e4903c04077c75fca00'))),
 'C': ((9992, 'c7b8eeb2488e4ec0b9ebbdd721db311397dc5b29abc91dcb1f153046ceb2bebd'),
       (9958, '1c7d102dfc3eda05cad0c7f2032537b67633f364341037ff57237a3600a209ad'),
       ((7035, 7035, b'static T fallback;', b''),
        (7517, 7499, b'T a=w->zi?w->zi:fallback;', b'za fb;T a=w->zi?w->zi:G(&position,0,&fb);'),
        (8989, 8987, b'za c;fallback=G(&position,0,&c);', b'')),
       ((0, 0, 7035, 'f41f8a55aeafabc94760acad05b0d7afd62fb585ab95612379331e472638d88a'),
        (7053, 7035, 464, 'e77b8b24c38fb7435057d91c172b1948bfb8a5ffc3dcc0d3dd22c17dced8c899'),
        (7542, 7540, 1447, '0aba3e675e691adffdc68300f3292919b1385ea84b3d0f613291888f884949ee'),
        (9021, 8987, 971, '07b91362c12b835ea3c1f14dacbdb902835dcfb1b2b4ec4d7d19db57cbcc33e7'))),
 'E': ((10360, '6e9e7eb6a439934aba2d48f9387f710a95a0032a89233ff2b676b5d6451d47fb'),
       (10326, '9ad6770abe1b2b69e13d5f43bf3bcd06bc29914ca074d2320b200dcdfad91e99'),
       ((7303, 7303, b'static T fallback;', b''),
        (7785, 7767, b'T a=w->zi?w->zi:fallback;', b'za fb;T a=w->zi?w->zi:E(&position,0,&fb);'),
        (9255, 9253, b'za c;fallback=E(&position,0,&c);', b'')),
       ((0, 0, 7303, '2a6491ea080866da0ee28148f7b324271bccc85b008ba286186c498fd5681da5'),
        (7321, 7303, 464, 'a095724df2443f7874a9f20720c663fb32fd1422d3e22be53d6cedd3e0c5f4e7'),
        (7810, 7808, 1445, 'be49712ec04c67bbae68391ba9b0a4e5734fd587ce2eddbbe2dcdf1ee002855c'),
        (9287, 9253, 1073, 'cd90071817339654a67a1e359d179c20fa96a77864099bdcd29ea8553d15dd5b'))),
 'F': ((8566, 'c7da40086c5f6d0616b21a990e1296c405d6486808eb34b5d2de3c486f5e4c5e'),
       (8550, 'a5ee66aac85b5681e255e880553b9602228946f36d0b0a8ad950fb5b1cea4f2f'),
       ((5947, 5947, b'static Y qe;', b''),
        (6369, 6357, b'Y a=w->d?w->d:qe;', b'za fb;Y a=w->d?w->d:u(&ql,0,&fb);'),
        (7675, 7679, b'za c;qe=u(&ql,0,&c);', b'')),
       ((0, 0, 5947, 'a89cc2a433f68acffcc5ba5911938a90f771d1ba4cdb4789797264db57b8a0c4'),
        (5959, 5947, 410, '097a6f3be071871850b6c37f99ca4412cffffe88992e19d299a3b6712f0c3469'),
        (6386, 6390, 1289, 'cbed2bd66380c16259cf5f5e1a44ef7f22c1d236b1d1baadf6ef895ea249f675'),
        (7695, 7679, 871, '4eea6b4da9ab342be86e5352601336c8173d47e31b9b445ae744ddf8e5874d0b')))}


def _pin(data):return len(data),hashlib.sha256(data).hexdigest()

def transform_source(source,*,family):
    """Replay one exact three-region shipping form; reject other source classes."""
    if type(source) is not bytes or family not in _CASES:
        raise ValueError('fixed lazy-fallback family/source required')
    before,after,edits,gaps=_CASES[family]
    if _pin(source)!=before:
        raise ValueError('fixed late shipping lazy-fallback input differs')
    parts=[];cursor=written=0
    for old_at,new_at,old,new in edits:
        if old_at<cursor or source[old_at:old_at+len(old)]!=old or source.count(old)!=1:
            raise ValueError('owned fallback declaration/consumer/setup differs')
        gap=source[cursor:old_at]
        if written+len(gap)!=new_at:
            raise ValueError('fixed lazy-fallback output position differs')
        parts.extend((gap,new));written=new_at+len(new);cursor=old_at+len(old)
    parts.append(source[cursor:]);result=b''.join(parts)
    if _pin(result)!=after:
        raise ValueError('fixed lazy-fallback output differs')
    complement=[]
    for old_at,new_at,length,digest in gaps:
        old=source[old_at:old_at+length];new=result[new_at:new_at+length]
        if old!=new or hashlib.sha256(old).hexdigest()!=digest:
            raise ValueError('protected fallback complement differs')
        complement.append(old)
    inverse=result
    for old_at,new_at,old,new in reversed(edits):
        if inverse[new_at:new_at+len(new)]!=new:
            raise ValueError('fixed lazy-fallback inverse position differs')
        inverse=inverse[:new_at]+old+inverse[new_at+len(new):]
    if inverse!=source:
        raise ValueError('full lazy-fallback inverse differs')
    return result,{
        'family':family,'stage':'late-shipping-immutable-root-lazy-fallback',
        'input_bytes':before[0],'input_sha256':before[1],
        'output_bytes':after[0],'output_sha256':after[1],
        'raw_delta':after[0]-before[0],'owned_regions':3,'protected_gaps':4,
        'full_inverse':True,'all_gaps_equal':True,
        'protected_complement_bytes':sum(len(x)for x in complement),
        'protected_complement_sha256':hashlib.sha256(b''.join(complement)).hexdigest(),
        'global_fallback_and_eager_GO_setup_removed':True,
        'selected_nonzero_best_short_circuit_retained':True,
        'same_immutable_root_first_legal_or_terminal_zero':True,
        'depth_winner_tie_epoch_completion_join_bytes_protected':True,
        'scratch_owner':'last result worker after think returned',
        'GO_work_and_output_query_timing_changed':True,
        'worker_result_stack_peak_measured':False,
        'query_call_counter_instrumented':False,
        'canonical_DEV_and_reduced_actual_F':'caller bypass',
        'new_native_identity_required':True,
        'external_reads':0,'compiler_codec_engine_executed_by_transform':0,
    }
