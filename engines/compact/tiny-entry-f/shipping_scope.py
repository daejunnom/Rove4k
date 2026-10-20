"""Replay the exact F automatic-name map proved by declaration/reference ASTs.

The generic independent analyzer is in engines/experiments/tiny-scope-names.
This maintained replay admits one exact post-storage source. It needs neither
libclang nor external reference engines. Each tuple retains one declaration's
physical occurrences; identifiers are never replaced by spelling alone.
"""
import hashlib

INPUT_SHA256 = 'c63a450245ff4ca703a5abe2dc75d840c7c7e936bb2a30a726c30014e3a92e90'
OUTPUT_SHA256 = '4e7a2a76ea753ebc3ccbcb4371ea76810c06b193e45b2f6ca70e66bd79112e9a'
AST_MAP_SHA256 = 'bac3ae02d4890b78d33a7e4cfca85b0bd01440e039c192f43a27c84304dfc153'
DECLARATIONS = (('z3', 'd', (1180, 1202, 1207, 1237)), ('zz', 'f', (1188, 1225)), ('zd', 'g', (1195, 1256)),
 ('zm', 'i', (1214, 1277)), ('z8', 'j', (1247, 1330, 1334)), ('zV', 'a', (1545, 1559, 1572, 1587)),
 ('sq', 'a', (1734, 1759)), ('yc', 'd', (1741, 1762)), ('zP', 'd', (1790, 1869, 1894, 1954)),
 ('zH', 'f', (1795, 1874, 1962)), ('zo', 'g', (1800, 1899, 1966)),
 ('zA', 'a', (2307, 2357, 2495, 2508, 2565, 2583, 2586, 2591, 2602, 2605, 2610, 2645, 2673)),
 ('to', 'd', (2318, 2369, 2455, 2474, 2492, 2562, 2580, 2599, 2656, 2680)), ('z0', 'f', (2327, 2519, 2526)),
 ('yf', 'g', (2361, 2380, 2466, 2533)), ('z5', 'i', (2577, 2620)), ('yh', 'j', (2596, 2631)),
 ('zR', 'a', (2816, 2938)), ('zW', 'd', (2843, 2854)), ('z1', 'f', (2851, 2893, 2904)),
 ('zR', 'f', (2995, 3123, 3177, 3233, 3420, 3452, 3486, 3492, 3538, 3664, 3757)), ('sq', 'g', (3002, 3428)),
 ('zA', 'j', (3028, 3033, 3040, 3049, 3058, 3089, 3102, 3140, 3183, 3196, 3239, 3377, 3498, 3579, 3670, 3763)),
 ('to', 'l', (3137, 3153, 3169, 3186, 3221, 3242)), ('aq', 'm', (3259, 3308, 3341)), ('zI', 'o', (3300, 3346)),
 ('to', 'q', (3374, 3384, 3393, 3412, 3424, 3467, 3501)), ('yf', 't', (3404, 3443, 3463, 3513)),
 ('zD', 'u', (3552, 3583, 3593, 3626, 3639, 3652, 3673, 3706, 3719, 3732, 3745, 3766)),
 ('yb', 'w', (3565, 3614, 3694)), ('zR', 'a', (3810, 3826)), ('zF', 'a', (4063, 4088, 4192, 4219)),
 ('zt', 'd', (4075, 4183, 4201, 4209, 4293)), ('zl', 'a', (4474, 4486, 4494)), ('zi', 'd', (4481, 4490, 4497)),
 ('zZ', 'a', (4672, 4754)), ('zA', 'd', (4680, 4740, 4766)), ('to', 'f', (4691, 4744)), ('zq', 'g', (4700, 4772)),
 ('zu', 'a', (4838, 5430, 5435, 5500, 5980, 6116, 6134, 6137, 6344, 6349)),
 ('zh', 'd', (4845, 5462, 5478, 5936, 5987, 6109, 6238)),
 ('zX', 'f', (4852, 5124, 5235, 5387, 5411, 5417, 5990, 6226, 6270, 6294)), ('zZ', 'g', (4859, 5671, 6172)),
 ('z6', 'l', (4867, 6092, 6096)), ('zn', 'n', (4894, 5226, 5508, 6217)), ('zv', 'o', (4922, 5023, 5120, 5184)),
 ('z4', 't', (4940, 5004, 5027)), ('zw', 'u', (4945, 4965, 4970, 4996)),
 ('zR', 'x', (5045, 5082, 5169, 5552, 5795, 5801, 5807)), ('zg', 'y', (5055, 6084, 6300)),
 ('z9', 'z', (5064, 5582, 5687, 5772, 5778, 5813, 5819)), ('zr', 'A', (5074, 5154, 5537, 5730, 5762)),
 ('zJ', 'B', (5086, 5856, 6207)), ('zf', 'C', (5091, 5517, 5932, 6074, 6078, 6234, 6248, 6396)),
 ('zy', 'D', (5104, 5520)), ('zF', 'E', (5250, 5289, 6382)),
 ('zt', 'F', (5283, 5303, 5330, 5342, 5356, 6297, 6385)), ('tt', 'G', (5300, 5591)),
 ('z8', 'H',
  (5317, 5371, 5383, 5393, 5407, 5458, 5475, 5490, 5968, 6071, 6081, 6105, 6245, 6254, 6266, 6276, 6290, 6324)),
 ('zj', 'I', (5338, 5421, 5443, 5451, 5468, 6231, 6371)), ('yi', 'J', (5352, 5425)),
 ('z2', 'K', (5497, 5514, 5922)), ('zA', 'L', (5562, 5653, 5657)), ('to', 'M', (5573, 5629, 5633)),
 ('zA', 'N', (5863, 6150, 6184)), ('to', 'O', (5874, 5914, 6154)), ('ye', 'P', (5883, 5928, 6123)),
 ('zT', 'Q', (5904, 5995)), ('zi', 'R', (6131, 6158, 6190)), ('zu', 'a', (6511, 6516, 6526, 6631, 6876)),
 ('zO', 'd', (6536, 6582, 6600, 6708, 6768, 6791)), ('yj', 'f', (6545, 6585, 6715, 6756, 6795)),
 ('z8', 'g', (6553, 6596, 6603, 6608, 6621, 6705, 6712, 6749, 6759, 6771, 6867, 6940, 6961)),
 ('zh', 'i', (6593, 6634, 6752)), ('zQ', 'j', (6616, 6642, 6777, 6783)),
 ('zx', 'l', (6958, 6977, 6984, 6994, 7003, 7050)), ('zl', 'm', (7019, 7046, 7054)),
 ('zM', 'a', (7483, 7515, 7543, 7582, 7598)), ('zS', 'd', (7498, 7549, 7571)), ('zf', 'a', (7712, 7744)),
 ('zQ', 'd', (7735, 7747, 7774)), ('ya', 'a', (7853, 7929, 7980)), ('zG', 'a', (8407, 8523, 8642, 8675, 8687)),
 ('zR', 'd', (8432, 8462, 8467, 8472, 8536, 8559)), ('z7', 'f', (8456, 8569, 8598)),
 ('ze', 'a', (8899, 8955, 9004)), ('clock', 'a', (9045, 9259, 9409, 9454, 9465)),
 ('zE', 'd', (9053, 9392, 9419, 9440)), ('zk', 'f', (9058, 9406, 9451, 9462, 9477, 9480, 9491, 9508, 9529)),
 ('zY', 'g', (9067, 9267, 9402)), ('z7', 'i', (9077, 9109, 9138, 9241, 9375)), ('yc', 'j', (9190, 9249)),
 ('yc', 'l', (9324, 9383)), ('yg', 'a', (9688, 9850, 10439)),
 ('zs', 'd', (9698, 9808, 9813, 9822, 9829, 9853, 9867, 10416)), ('yd', 'f', (9703, 9872, 10451, 10472)),
 ('zL', 'g',
  (9713, 9916, 9966, 9980, 9995, 10010, 10024, 10039, 10060, 10117, 10180, 10214, 10241, 10264, 10283, 10298)),
 ('yd', 'j', (9910, 9923, 9938)))


def transform_source(data):
    if type(data) is not bytes or len(data)!=10477 or hashlib.sha256(data).hexdigest()!=INPUT_SHA256:
        raise ValueError('exact F post-storage source required for bound scope map')
    pieces=[];offset=0;inverse=[];produced=0
    edits=sorted((position,old.encode(),new.encode())
                 for old,new,positions in DECLARATIONS for position in positions)
    for position,old,new in edits:
        if position<offset or data[position:position+len(old)]!=old:
            raise ValueError('overlap or stale declaration-bound source occurrence')
        prefix=data[offset:position];pieces.extend((prefix,new));produced+=len(prefix)
        inverse.append((produced,produced+len(new),old));produced+=len(new)
        offset=position+len(old)
    pieces.append(data[offset:]);result=b''.join(pieces)
    if len(result)!=10011 or hashlib.sha256(result).hexdigest()!=OUTPUT_SHA256:
        raise ValueError('scope-name output differs from exact qualified source')
    restored=bytearray(result)
    for start,end,old in reversed(inverse):restored[start:end]=old
    if bytes(restored)!=data:raise ValueError('scope-map inverse changed input')
    return result,{'input_sha256':INPUT_SHA256,'output_sha256':OUTPUT_SHA256,
                   'AST_map_sha256':AST_MAP_SHA256,'declarations':98,'physical_edits':451,
                   'source_saved_bytes':466,'exact_inverse':True,
                   'policy':'automatic names unique within functions, reused between functions',
                   'runtime_name_resolution':False,'AST_tool_required_by_normal_build':False}


# Independent exact member stage; the preceding automatic map stays unchanged.
MEMBER_INPUT_SHA256 = '4e7a2a76ea753ebc3ccbcb4371ea76810c06b193e45b2f6ca70e66bd79112e9a'
MEMBER_OUTPUT_SHA256 = '00239e23500d41c45801cdb19c4e7c8cc8b22cf29bebd7e4fbc8fdd1e08c7916'
MEMBER_AST_PROOF_SHA256 = 'cf87b30109b2ce58fe461f3c4ed22e42b67851dc52f5e132b9f733e9f6c37317'
MEMBER_INPUT_POLICY_SHA256 = '98c38def96bd2b505922b22d26b9dacef30def36cb73d0fd1b63051a34a8afed'
MEMBER_DECLARATIONS = (('za', 16, 'zB', 'a', (336, 2379, 2409, 2492, 2685, 4757, 4786, 5084)),
 ('zb', 23, 'zF', 'a', (547, 4045, 4068, 7953)),
 ('zb', 24, 'zt', 'b', (550, 4053, 4077, 7962)),
 ('zc', 27, 'id', 'a', (576, 4627, 9387)),
 ('zc', 28, 'zu', 'b', (579, 6127, 6531, 7329, 7335)),
 ('zc', 29, 'z8', 'c', (582, 6135, 6244, 6523)),
 ('zc', 30, 'zf', 'd', (590, 6143, 6258, 6514, 7355, 7361)),
 ('zc', 31, 'zU', 'e', (602, 4235, 4289, 6119)),
 ('zc', 32, 'zG', 'f', (605, 4834, 5691, 6167)),
 ('zc', 33, 'zK', 'g', (625, 4778, 4813, 5697, 5740, 6151)),
 ('zc', 34, 'zC', 'h', (636, 4578, 5867)),
 ('zc', 35, 'zp', 'i', (649, 4590, 5886)),
 ('zc', 36, 'zq', 'j', (660, 4547, 6675)))


def transform_members(data):
    if type(data) is not bytes or len(data)!=10011 or hashlib.sha256(data).hexdigest()!=MEMBER_INPUT_SHA256:
        raise ValueError('exact F post-scope source required for bound member map')
    edits=sorted((position,old.encode(),new.encode())
                 for owner,ordinal,old,new,positions in MEMBER_DECLARATIONS for position in positions)
    if len(MEMBER_DECLARATIONS)!=13 or len(edits)!=57:
        raise ValueError('exact thirteen-field/fifty-seven-position member map required')
    pieces=[];offset=0;inverse=[];produced=0
    for position,old,new in edits:
        if position<offset or data[position:position+len(old)]!=old:
            raise ValueError('overlap or stale declaration-bound member occurrence')
        gap=data[offset:position];pieces.extend((gap,new));produced+=len(gap)
        inverse.append((produced,produced+len(new),old));produced+=len(new)
        offset=position+len(old)
    pieces.append(data[offset:]);result=b''.join(pieces)
    if len(result)!=9954 or hashlib.sha256(result).hexdigest()!=MEMBER_OUTPUT_SHA256:
        raise ValueError('member output differs from exact qualified source')
    restored=bytearray(result)
    for start,end,old in reversed(inverse):restored[start:end]=old
    if bytes(restored)!=data:raise ValueError('member-map inverse changed input')
    return result,{'input_sha256':MEMBER_INPUT_SHA256,'output_sha256':MEMBER_OUTPUT_SHA256,
                   'AST_proof_sha256':MEMBER_AST_PROOF_SHA256,'input_policy_sha256':MEMBER_INPUT_POLICY_SHA256,
                   'owned_fields':13,'physical_edits':57,'source_saved_bytes':57,'exact_inverse':True,
                   'protected_atomic_member':'zb.zN','runtime_name_resolution':False,
                   'AST_tool_required_by_normal_build':False}
