"""Replay the qualified B static-function and automatic-name occurrence maps.

Only one exact post-spelling source is admitted. The two literal maps retain
declaration/reference byte positions. Normal builds need neither Clang nor
experiment, report, generated-source or other-family inputs. Canonical DEV is
outside this shipping-only domain. Native image differences are qualified
separately; this helper does not assert old whole-ELF identity.
"""
import hashlib

FAMILY = 'B'
STATIC_BINDING = (13071, '96e6e330e5289d1c404dac0402e8b672a89c52e193a9d4f9aebb02e0c9042ffa', 12678, 'fe8ef598de236d93738467b4aeaa41d6dff4128dcd7a03f0642431e85fb9957d')
LOCALS_BINDING = (12678, 'fe8ef598de236d93738467b4aeaa41d6dff4128dcd7a03f0642431e85fb9957d', 12220, 'daa9ca6e03260320c13a0a551a0c2586ed53d24d49ebba74f87b57b57814ba9f')
STATIC_AST_MAP_SHA256 = '7bbfe3a0bafe069530bd4c14db7896928594e2d4aa3ef2ad48acecfea8f10831'
LOCALS_AST_MAP_SHA256 = 'b34857ee27d93fbfe98b1ce4da69be4c80b1eb86616f821a89612c4eb667daad'
STATIC_DECLARATIONS = (('bit', 'o', (1394, 1701, 1724, 1812, 1834, 2084, 2161, 2214, 2271)),
 ('piece', 'I', (1459, 1737, 1847)),
 ('state', 'S', (1531, 3080, 3430, 4653)),
 ('put', 'M', (1635, 2751, 2763, 2786, 3144, 3291, 3303, 3318, 3330, 4579, 4595, 4610, 4626)),
 ('attackers', 'l', (1918, 2399, 5619)),
 ('ep', 'C', (2643, 3418)),
 ('rights', 'O', (2869, 3350, 3361)),
 ('add', 'g', (3505, 3864, 3921, 4156, 4337, 4437)),
 ('probe', 'K', (4694, 6738, 8978)),
 ('claim', 'A', (4954, 6301)),
 ('learn', 'F', (5113, 8523, 8548)),
 ('piece_index', 'J', (5173, 7225, 7321, 8565)),
 ('capture', 'y', (5215, 6027, 6080, 7363, 7533, 7858, 8693)),
 ('exchange', 'D', (5435, 5871, 6134)),
 ('see', 'Q', (5947, 7563, 7935)),
 ('search', 'P', (6208, 7046, 8057, 8206, 8266, 8326, 9150)),
 ('text', 'T', (9469, 9886, 10090)),
 ('parse', 'H', (9787, 10988)),
 ('wait', 'U', (10502, 11445, 12813, 12897)),
 ('clear', 'B', (10632, 12256)),
 ('set_position', 'R', (10745, 12820)),
 ('number', 'G', (11111, 11633, 11771)),
 ('read_line', 'N', (11285, 12486)),
 ('go', 'E', (11434, 12887)))
LOCALS_DECLARATIONS = (('yf', 'd', (1220, 1242, 1247, 1277)),
 ('zI', 'f', (1228, 1265)),
 ('ze', 'i', (1235, 1296)),
 ('zs', 'j', (1254, 1317)),
 ('yl', 'm', (1287, 1370, 1374)),
 ('z6', 'a', (1649, 1663, 1673, 1683, 1700, 1723, 1741)),
 ('sq', 'a', (1907, 2004, 2081, 2130, 2185)),
 ('yp', 'f', (1914, 1924, 2007)),
 ('result', 'j', (1938, 2028, 2103, 2154, 2243, 2301)),
 ('z5', 'm', (1947, 2237)),
 ('sq', 'a', (2337, 2359)),
 ('yp', 'd', (2344, 2362)),
 ('zZ', 'd', (2395, 2474, 2499, 2559)),
 ('zR', 'f', (2400, 2479, 2567)),
 ('zu', 'i', (2405, 2504, 2571)),
 ('zJ', 'a', (2915, 2965, 3101, 3114, 3171, 3189, 3192, 3197, 3208, 3211, 3216, 3248, 3274)),
 ('to', 'd', (2926, 2977, 3062, 3080, 3098, 3168, 3186, 3205, 3258, 3280)),
 ('yc', 'f', (2935, 3125, 3132)),
 ('yv', 'i', (2969, 2988, 3073, 3139)),
 ('yi', 'j', (3183, 3225)),
 ('yy', 'n', (3202, 3235)),
 ('z1', 'a', (3419, 3545)),
 ('pawn', 'd', (3446, 3459)),
 ('yd', 'f', (3456, 3500, 3511)),
 ('z1', 'f', (3596, 3771, 3826, 4059, 4238, 4336)),
 ('zJ',
  'j',
  (3627, 3632, 3639, 3648, 3657, 3688, 3701, 3735, 3777, 3790, 3832, 3979, 4065, 4142, 4244, 4342)),
 ('to', 'm', (3732, 3748, 3764, 3780, 3815, 3835)),
 ('first', 'q', (3852, 3904, 3940)),
 ('zS', 't', (3896, 3948)),
 ('to', 'u', (3976, 3986, 3995, 4014, 4041, 4068)),
 ('yv', 'w', (4006, 4021, 4037, 4080)),
 ('zN', 'x', (4115, 4146, 4162, 4195, 4208, 4227, 4247, 4280, 4293, 4306, 4325, 4345)),
 ('yo', 'z', (4128, 4183, 4268)),
 ('zP', 'a', (4588, 4613, 4717, 4744)),
 ('zA', 'd', (4600, 4708, 4726, 4734, 4818)),
 ('zr', 'a', (4998, 5010, 5019)),
 ('zn', 'd', (5005, 5015, 5022)),
 ('zi', 'a', (5450, 5747, 5750, 5765)),
 ('zq', 'd', (5464, 5486, 5512, 5534, 5538)),
 ('yd', 'f', (5547, 5603, 5614)),
 ('zK', 'j', (5674, 5744, 5753)),
 ('zK', 'a', (5855, 5912, 5919, 5983)),
 ('zB',
  'a',
  (6042, 6684, 6689, 6769, 6784, 6834, 6852, 6963, 7773, 7799, 7854, 8231, 8249, 8252, 8384, 8644, 8649)),
 ('zf',
  'd',
  (6049,
   6335,
   6733,
   6993,
   6996,
   7648,
   7824,
   7941,
   7967,
   7973,
   8001,
   8019,
   8025,
   8049,
   8078,
   8204,
   8207,
   8216)),
 ('zk', 'f', (6056, 6716, 7652, 7820, 8056, 8074, 8220, 8365)),
 ('z9', 'n', (6063, 6371, 6484, 6641, 6665, 6671, 6765, 6868, 7827, 7976, 8028, 8081, 8344, 8570, 8594)),
 ('yj', 't', (6085, 8188, 8192)),
 ('zG', 'u', (6093, 6536, 6761, 7543, 8329, 8380, 8683)),
 ('zT', 'x', (6100, 7838, 7987, 8039, 8092, 8227, 8375)),
 ('zt', 'z', (6126, 6475, 6971, 7874, 8335, 8398)),
 ('zC', 'L', (6160, 6261, 6367, 6433)),
 ('yh', 'V', (6178, 6242, 6265)),
 ('zD', 'W', (6183, 6203, 6208, 6234)),
 ('z1', 'X', (6285, 6323, 6418, 7072, 7507, 7513, 7519)),
 ('ym', 'Y', (6304, 7117, 7270, 7355, 7484, 7490, 7525, 7531)),
 ('zy', 'Z', (6314, 6401, 7057, 7442, 7474)),
 ('zB', 'a', (8812, 8817, 8827, 8860, 8967)),
 ('zi', 'd', (8838, 8879, 8949)),
 ('yl', 'f', (8851, 8958)),
 ('zX', 'a', (9377, 9404, 9438, 9455)),
 ('zX', 'a', (9515, 9553, 9580, 9615, 9632)),
 ('z2', 'd', (9535, 9586, 9603)),
 ('zi', 'a', (9750, 9781)),
 ('z0', 'd', (9773, 9784, 9811)),
 ('yn', 'a', (9892, 9968, 10019)),
 ('zQ', 'a', (10450, 10569, 10709, 10742, 10754)),
 ('z1', 'd', (10475, 10505, 10510, 10515, 10582, 10605)),
 ('yk', 'f', (10499, 10615, 10644)),
 ('zg', 'a', (10964, 11020, 11069)),
 ('clock', 'a', (11108, 11321, 11470, 11515, 11526)),
 ('zO', 'd', (11116, 11453, 11480, 11501)),
 ('zp', 'f', (11121, 11467, 11512, 11523, 11538, 11541, 11552, 11570, 11591)),
 ('ya', 'j', (11130, 11329, 11463)),
 ('yk', 'm', (11140, 11172, 11201, 11303, 11436)),
 ('yp', 'p', (11253, 11311)),
 ('yp', 'q', (11386, 11444)),
 ('yw', 'a', (11807, 11971, 12640)),
 ('zz', 'd', (11817, 11929, 11934, 11943, 11950, 11974, 11990, 12617)),
 ('ys', 'f', (11822, 11995, 12652, 12673)),
 ('zW',
  'j',
  (11832,
   12121,
   12171,
   12185,
   12200,
   12215,
   12229,
   12244,
   12265,
   12322,
   12385,
   12419,
   12444,
   12467,
   12486,
   12500)),
 ('ys', 'm', (12116, 12128, 12143)))


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
