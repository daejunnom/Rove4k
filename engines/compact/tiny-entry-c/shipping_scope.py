"""Replay the qualified C static-function and automatic-name occurrence maps.

Only one exact post-spelling source is admitted. The two literal maps retain
declaration/reference byte positions. Normal builds need neither Clang nor
experiment, report, generated-source or other-family inputs. Canonical DEV is
outside this shipping-only domain. Native image differences are qualified
separately; this helper does not assert old whole-ELF identity.
"""
import hashlib

FAMILY = 'C'
STATIC_BINDING = (12224, '20f06b6ed9ada03db6f8719f05ecdf9cb52802ab0a1acc8999627999db899046', 11868, '2bac34e9bd30d32551714772112c78c91ff99167506abc2e76cb4f673b499307')
LOCALS_BINDING = (11868, '2bac34e9bd30d32551714772112c78c91ff99167506abc2e76cb4f673b499307', 11455, 'f70cd11e8cdd1a3d2503255189e80ca9070cf310777d2ff8a89ec9beff732f82')
STATIC_AST_MAP_SHA256 = '7a31b5fa1461bb20ecac36f1fd4bcade6c2d9dea47634d2c31938034551e01cb'
LOCALS_AST_MAP_SHA256 = '11580a25c000d1c06f2d6641c2630c48c8dccacdc932c24730aa5c5fd52787c7'
STATIC_DECLARATIONS = (('piece', 'H', (1430, 1656, 1699)),
 ('state', 'R', (1502, 2496, 2846, 4184)),
 ('put', 'K', (1606, 2560, 2707, 2719, 2734, 2746, 4106, 4124, 4139, 4155)),
 ('walk', 'W', (1748, 1824, 3094, 3977)),
 ('ep', 'C', (2062, 2834)),
 ('rights', 'O', (2285, 2766, 2777)),
 ('add', 'g', (2921, 3294, 3351, 3623, 3808, 3908)),
 ('tiny_raw', 'U', (4426, 6036)),
 ('tiny_order', 'T', (4976, 6878)),
 ('probe', 'J', (5049, 6290, 8068)),
 ('claim', 'o', (5325, 5781)),
 ('learn', 'E', (5500, 7642, 7667)),
 ('piece_index', 'I', (5565, 6566, 6662, 7684)),
 ('capture', 'l', (5607, 6704, 7095, 7797)),
 ('search', 'P', (5703, 7187, 7333, 7390, 7447, 8275)),
 ('text', 'S', (8628, 8922, 9157)),
 ('parse', 'G', (8817, 10164, 11157)),
 ('result', 'N', (9018, 9536)),
 ('wait', 'V', (9635, 10612, 11597, 11946, 12030)),
 ('clear', 'y', (9790, 11432)),
 ('set_position', 'Q', (9912, 11953)),
 ('number', 'F', (10278, 10800, 10944)),
 ('read_line', 'M', (10452, 11619)),
 ('go', 'D', (10601, 12020)))
LOCALS_DECLARATIONS = (('yf', 'd', (1250, 1272, 1277, 1307)),
 ('zI', 'f', (1258, 1295)),
 ('ze', 'i', (1265, 1332)),
 ('zs', 'j', (1284, 1353)),
 ('yl', 'm', (1317, 1406, 1410)),
 ('z6', 'a', (1622, 1636, 1648)),
 ('sq', 'a', (1785, 1809)),
 ('yp', 'd', (1792, 1812)),
 ('zZ', 'd', (1842, 1921, 1946, 2006)),
 ('zR', 'f', (1847, 1926, 2014)),
 ('zu', 'i', (1852, 1951, 2018)),
 ('zJ', 'a', (2365, 2415, 2551, 2564, 2621, 2639, 2642, 2647, 2658, 2661, 2666, 2698, 2724)),
 ('to', 'd', (2376, 2427, 2512, 2530, 2548, 2618, 2636, 2655, 2708, 2730)),
 ('yc', 'f', (2385, 2575, 2582)),
 ('yv', 'i', (2419, 2438, 2523, 2589)),
 ('yi', 'j', (2633, 2675)),
 ('yy', 'n', (2652, 2685)),
 ('z1', 'a', (2869, 2995)),
 ('pawn', 'd', (2896, 2909)),
 ('yd', 'f', (2906, 2950, 2961)),
 ('z1', 'f', (3051, 3179, 3232, 3287, 3486, 3518, 3552, 3557, 3603, 3740, 3838)),
 ('sq', 'j', (3058, 3494)),
 ('zJ',
  'm',
  (3084, 3089, 3096, 3105, 3114, 3145, 3158, 3196, 3238, 3251, 3293, 3443, 3563, 3644, 3746, 3844)),
 ('to', 'q', (3193, 3209, 3225, 3241, 3276, 3296)),
 ('first', 't', (3313, 3365, 3401)),
 ('zS', 'u', (3357, 3409)),
 ('to', 'v', (3440, 3450, 3459, 3478, 3490, 3533, 3566)),
 ('yv', 'w', (3470, 3509, 3529, 3578)),
 ('zN', 'x', (3617, 3648, 3664, 3697, 3710, 3729, 3749, 3782, 3795, 3808, 3827, 3847)),
 ('yo', 'z', (3630, 3685, 3770)),
 ('z1', 'a', (3892, 3907)),
 ('zh', 'a', (4385, 4570, 4665, 4685)),
 ('z8', 'd', (4472, 4591)),
 ('zL', 'f', (4719, 4795, 4813, 4816, 4860, 4863)),
 ('zP', 'a', (4955, 4993, 5100, 5127)),
 ('write', 'd', (4962, 5088)),
 ('zA', 'f', (4977, 5109, 5117, 5201)),
 ('zr', 'a', (5397, 5409, 5418)),
 ('zn', 'd', (5404, 5414, 5425)),
 ('zB',
  'a',
  (5592, 6286, 6291, 6357, 6983, 7000, 7035, 7141, 7193, 7245, 7404, 7422, 7425, 7542, 7795, 7800)),
 ('zf',
  'd',
  (5599,
   5870,
   6335,
   6387,
   6390,
   6937,
   7010,
   7122,
   7150,
   7156,
   7179,
   7199,
   7205,
   7224,
   7255,
   7381,
   7384,
   7393)),
 ('zk', 'f', (5606, 6318, 6941, 7006, 7231, 7251, 7397, 7532)),
 ('z9', 'n', (5613, 5971, 6089, 6243, 6267, 6273, 7013, 7159, 7208, 7258, 7511, 7721, 7745)),
 ('yj', 'u', (5635, 7365, 7369)),
 ('zt', 'v', (5661, 6080, 6365, 7055, 7502, 7556)),
 ('zC', 'x', (5695, 5796, 5967, 6033)),
 ('yh', 'z', (5713, 5777, 5800)),
 ('zD', 'A', (5718, 5738, 5743, 5769)),
 ('z1', 'B', (5820, 5858, 6018, 6466, 6786, 6792, 6798, 6804)),
 ('ym', 'L', (5839, 6511, 6664, 6692, 6763, 6769, 6818, 6824, 6830, 6836)),
 ('zy', 'X', (5849, 6001, 6451, 6721, 6753)),
 ('zU', 'Y', (5862, 6877, 6976, 7042, 7492)),
 ('z6', 'Z', (5867, 7523)),
 ('zB', 'a', (7991, 7996, 8006, 8039, 8147)),
 ('zi', 'd', (8017, 8058, 8129)),
 ('yl', 'f', (8030, 8138)),
 ('zX', 'a', (8604, 8637, 8670, 8716, 8732)),
 ('z2', 'd', (8619, 8676, 8692)),
 ('zi', 'a', (8860, 8897)),
 ('z0', 'd', (8889, 8900, 8927)),
 ('yn', 'a', (9008, 9098, 9172)),
 ('zQ', 'a', (9661, 9780, 9898, 9953, 9965)),
 ('z1', 'd', (9686, 9716, 9721, 9726, 9793, 9816)),
 ('yk', 'f', (9710, 9826, 9855)),
 ('zg', 'a', (10175, 10231, 10280)),
 ('clock', 'a', (10319, 10538, 10693, 10738, 10749)),
 ('zO', 'd', (10327, 10676, 10703, 10724)),
 ('zp', 'f', (10332, 10690, 10735, 10746, 10761, 10764, 10775, 10799, 10820)),
 ('ya', 'i', (10341, 10546, 10686)),
 ('yk', 'j', (10351, 10383, 10412, 10514, 10653)),
 ('yp', 'm', (10464, 10522)),
 ('yp', 'p', (10603, 10661)),
 ('yw', 'a', (11014, 11220, 11827)),
 ('zz', 'd', (11024, 11173, 11178, 11192, 11199, 11223, 11244, 11804)),
 ('ys', 'f', (11029, 11249, 11839, 11863)),
 ('zW',
  'j',
  (11039,
   11291,
   11341,
   11355,
   11370,
   11385,
   11399,
   11414,
   11435,
   11492,
   11555,
   11589,
   11614,
   11637,
   11656,
   11670)),
 ('ys', 'm', (11286, 11298, 11313)))


def _replay(data,binding,declarations):
    input_bytes,input_sha256,output_bytes,output_sha256= binding
    if type(data) is not bytes or len(data)!=input_bytes or hashlib.sha256(data).hexdigest()!=input_sha256:
        raise ValueError('exact stage input required for fixed occurrence map')
    pieces=[];offset=0;inverse=[];produced=0
    edits=sorted((position,old.encode(),new.encode())
                 for old,new,positions in declarations for position in positions)
    for position,old,new in edits:
        if position<offset or data[position:position+len(old)]!=old:
            raise ValueError('overlap or stale declaration-bound source occurrence')
        prefix=data[offset:position];pieces.extend((prefix,new));produced+=len(prefix)
        inverse.append((produced,produced+len(new),old));produced+=len(new)
        offset=position+len(old)
    pieces.append(data[offset:]);result=b''.join(pieces)
    if len(result)!=output_bytes or hashlib.sha256(result).hexdigest()!=output_sha256:
        raise ValueError('fixed occurrence-map output differs from qualified source')
    restored=bytearray(result)
    for start,end,old in reversed(inverse):restored[start:end]=old
    if bytes(restored)!=data:raise ValueError('occurrence-map inverse changed input')
    return result,{'input_sha256':input_sha256,'output_sha256':output_sha256,
                   'declarations':len(declarations),'physical_edits':len(edits),
                   'source_saved_bytes':len(data)-len(result),'exact_inverse':True}


def transform_source(data):
    static,static_metadata=_replay(data,STATIC_BINDING,STATIC_DECLARATIONS)
    result,locals_metadata=_replay(static,LOCALS_BINDING,LOCALS_DECLARATIONS)
    return result,{'family':FAMILY,'static_functions':static_metadata,
                   'automatic_names':locals_metadata,
                   'static_AST_map_sha256':STATIC_AST_MAP_SHA256,
                   'locals_AST_map_sha256':LOCALS_AST_MAP_SHA256,
                   'input_sha256':STATIC_BINDING[1],'output_sha256':LOCALS_BINDING[3],
                   'source_saved_bytes':len(data)-len(result),
                   'policy':'fixed static declaration/reference map, then fixed automatic declaration/reference map',
                   'runtime_name_resolution':False,'AST_tool_required_by_normal_build':False,
                   'full_native_equal_to_previous_maintained':False,
                   'locals_full_native_equal_to_static_only':True}
