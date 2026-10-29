"""Replay the qualified E static-function and automatic-name occurrence maps.

Only one exact post-spelling source is admitted. The two literal maps retain
declaration/reference byte positions. Normal builds need neither Clang nor
experiment, report, generated-source or other-family inputs. Canonical DEV is
outside this shipping-only domain. Native image differences are qualified
separately; this helper does not assert old whole-ELF identity.
"""
import hashlib

FAMILY = 'E'
STATIC_BINDING = (12641, 'af0ab88d9f4ce25154b3fda909fc00b9eca0cda8d8784b4b07e4926015a2c330', 12246, 'b54d840799ba0c63ae4adb4c2e90f62c3b10f443ff83ef05d1a9585d3cc9d95a')
LOCALS_BINDING = (12246, 'b54d840799ba0c63ae4adb4c2e90f62c3b10f443ff83ef05d1a9585d3cc9d95a', 11803, 'acd417f903ada227092b0ba371d6ad960ab80b4925ab64633b9b8a2774a9b3aa')
STATIC_AST_MAP_SHA256 = '5dafc885268a5f0fd719bf48302762043110135a210e060a5f5bdd113f464338'
LOCALS_AST_MAP_SHA256 = '0cb525d4a0534caac6e933f529fb142d687bd7be63bbb64a25ff3dc91e977bbe'
STATIC_DECLARATIONS = (('state', 'O', (1247, 2241, 2591, 3929)),
 ('put', 'H', (1351, 2305, 2452, 2464, 2479, 2491, 3851, 3869, 3884, 3900)),
 ('walk', 'V', (1493, 1569, 2839, 3722)),
 ('ep', 'A', (1807, 2579)),
 ('rights', 'K', (2030, 2511, 2522)),
 ('add', 'g', (2666, 3039, 3096, 3368, 3553, 3653)),
 ('tiny_center', 'Q', (4065, 4359, 4937, 4953)),
 ('tiny_white', 'T', (4143, 4711)),
 ('tiny_raw', 'S', (4684, 6202)),
 ('tiny_order', 'R', (4777, 6993)),
 ('probe', 'G', (5215, 6456, 8183)),
 ('claim', 'o', (5491, 5947)),
 ('learn', 'C', (5666, 7757, 7782)),
 ('piece_index', 'F', (5731, 6732, 6828, 7799)),
 ('capture', 'l', (5773, 6870, 7210, 7912)),
 ('search', 'M', (5869, 7302, 7448, 7505, 7562, 8382)),
 ('text', 'P', (8739, 9156, 9381)),
 ('parse', 'E', (9057, 10377)),
 ('result', 'J', (9242, 9758)),
 ('wait', 'U', (9857, 10856, 12363, 12447)),
 ('clear', 'y', (10012, 11750)),
 ('set_position', 'N', (10134, 12370)),
 ('number', 'D', (10522, 11044, 11188)),
 ('read_line', 'I', (10696, 12036)),
 ('go', 'B', (10845, 12437)))
LOCALS_DECLARATIONS = (('z6', 'a', (1371, 1385, 1401)),
 ('sq', 'a', (1542, 1566)),
 ('yp', 'd', (1549, 1569)),
 ('zZ', 'd', (1599, 1678, 1703, 1763)),
 ('zR', 'f', (1604, 1683, 1771)),
 ('zu', 'i', (1609, 1708, 1775)),
 ('zJ', 'a', (2122, 2172, 2308, 2321, 2378, 2396, 2399, 2404, 2415, 2418, 2423, 2455, 2481)),
 ('to', 'd', (2133, 2184, 2269, 2287, 2305, 2375, 2393, 2412, 2465, 2487)),
 ('yc', 'f', (2142, 2332, 2339)),
 ('yv', 'i', (2176, 2195, 2280, 2346)),
 ('yi', 'j', (2390, 2432)),
 ('yy', 'n', (2409, 2442)),
 ('z1', 'a', (2626, 2752)),
 ('pawn', 'd', (2653, 2666)),
 ('yd', 'f', (2663, 2707, 2718)),
 ('z1', 'f', (2808, 2936, 2989, 3044, 3243, 3275, 3309, 3314, 3360, 3497, 3595)),
 ('sq', 'j', (2815, 3251)),
 ('zJ',
  'm',
  (2841, 2846, 2853, 2862, 2871, 2902, 2915, 2953, 2995, 3008, 3050, 3200, 3320, 3401, 3503, 3601)),
 ('to', 'q', (2950, 2966, 2982, 2998, 3033, 3053)),
 ('first', 't', (3070, 3122, 3158)),
 ('zS', 'u', (3114, 3166)),
 ('to', 'v', (3197, 3207, 3216, 3235, 3247, 3290, 3323)),
 ('yv', 'w', (3227, 3266, 3286, 3335)),
 ('zN', 'x', (3374, 3405, 3421, 3454, 3467, 3486, 3506, 3539, 3552, 3565, 3584, 3604)),
 ('yo', 'z', (3387, 3442, 3527)),
 ('z1', 'a', (3649, 3664)),
 ('z7', 'd', (4074, 4278, 4447, 4493, 4507)),
 ('zl', 'i', (4090, 4352, 4392)),
 ('yl', 'j', (4100, 4211, 4296, 4543, 4563)),
 ('zm', 'm', (4184, 4203, 4281, 4322, 4355)),
 ('yq', 't', (4200, 4215, 4300)),
 ('zm', 'u', (4370, 4375, 4380, 4395, 4450, 4496, 4510, 4547)),
 ('zJ', 'd', (4680, 4711, 4814, 5014)),
 ('to', 'f', (4691, 4739, 4765, 4808, 5006)),
 ('piece', 'i', (4700, 4721, 5023)),
 ('yc', 'j', (4744, 4916, 4953)),
 ('zP', 'a', (5075, 5113, 5220, 5247)),
 ('write', 'd', (5082, 5208)),
 ('zA', 'f', (5097, 5229, 5237, 5321)),
 ('zr', 'a', (5517, 5529, 5538)),
 ('zn', 'd', (5524, 5534, 5545)),
 ('zB',
  'a',
  (5712, 6406, 6411, 6477, 7052, 7069, 7104, 7210, 7262, 7314, 7473, 7491, 7494, 7611, 7864, 7869)),
 ('zf',
  'd',
  (5719,
   5990,
   6455,
   6507,
   6510,
   7006,
   7079,
   7191,
   7219,
   7225,
   7248,
   7268,
   7274,
   7293,
   7324,
   7450,
   7453,
   7462)),
 ('zk', 'f', (5726, 6438, 7010, 7075, 7300, 7320, 7466, 7601)),
 ('z9', 'n', (5733, 6091, 6209, 6363, 6387, 6393, 7082, 7228, 7277, 7327, 7580, 7790, 7814)),
 ('yj', 'u', (5755, 7434, 7438)),
 ('zt', 'v', (5781, 6200, 6485, 7124, 7571, 7625)),
 ('zC', 'x', (5815, 5916, 6087, 6153)),
 ('yh', 'z', (5833, 5897, 5920)),
 ('zD', 'L', (5838, 5858, 5863, 5889)),
 ('z1', 'W', (5940, 5978, 6138, 6586, 6855, 6861, 6867, 6873)),
 ('ym', 'X', (5959, 6631, 6733, 6761, 6832, 6838, 6887, 6893, 6899, 6905)),
 ('zy', 'Y', (5969, 6121, 6571, 6790, 6822)),
 ('zU', 'Z', (5982, 6946, 7045, 7111, 7561)),
 ('zB', 'a', (8052, 8057, 8067, 8100, 8208)),
 ('zi', 'd', (8078, 8119, 8190)),
 ('yl', 'f', (8091, 8199)),
 ('zX', 'a', (8655, 8682, 8716, 8733)),
 ('zX', 'a', (8793, 8831, 8858, 8893, 8910)),
 ('z2', 'd', (8813, 8864, 8881)),
 ('zi', 'a', (9038, 9075)),
 ('z0', 'd', (9067, 9078, 9105)),
 ('yn', 'a', (9186, 9274, 9348)),
 ('zQ', 'a', (9837, 9956, 10096, 10151, 10163)),
 ('z1', 'd', (9862, 9892, 9897, 9902, 9969, 9992)),
 ('yk', 'f', (9886, 10002, 10031)),
 ('zg', 'a', (10373, 10429, 10478)),
 ('clock', 'a', (10517, 10736, 10891, 10936, 10947)),
 ('zO', 'd', (10525, 10874, 10901, 10922)),
 ('zp', 'f', (10530, 10888, 10933, 10944, 10959, 10962, 10973, 10997, 11018)),
 ('ya', 'j', (10539, 10744, 10884)),
 ('yk', 'm', (10549, 10581, 10610, 10712, 10851)),
 ('yp', 'p', (10662, 10720)),
 ('yp', 'q', (10801, 10859)),
 ('yw', 'a', (11290, 11496, 12205)),
 ('zz', 'd', (11300, 11449, 11454, 11468, 11475, 11499, 11520, 12182)),
 ('ys', 'f', (11305, 11525, 12217, 12241)),
 ('zW',
  'j',
  (11315,
   11669,
   11719,
   11733,
   11748,
   11763,
   11777,
   11792,
   11813,
   11870,
   11933,
   11967,
   11992,
   12015,
   12034,
   12048)),
 ('ys', 'm', (11664, 11676, 11691)))


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
