"""Replay one exact A automatic-name map proved by declaration/reference ASTs.

The normal build admits one exact post-storage input and needs no AST library,
experiment, report, external engine or runtime spelling lookup. Each tuple is
one declaration and its physical occurrences, never a spelling-wide rewrite.
"""
import hashlib

INPUT_SHA256 = '9e764bbbea91f198a4cb5aff62aae9f3007df5f715d4d8b8142e4795b5109d5a'
OUTPUT_SHA256 = 'a3414baa5034a62067f74f7f8fff9a1578827f37e6ca59b0db8e5bc1968df312'
AST_MAP_SHA256 = 'c7c84366437df666fd353213242a3ae9e2e6e71c0914992b563a9012619241cf'
DECLARATIONS = (('z3', 'd', (1191, 1213, 1218, 1248)),
 ('zz', 'f', (1199, 1236)),
 ('zd', 'g', (1206, 1266)),
 ('zm', 'i', (1225, 1287)),
 ('zV', 'a', (1551, 1565, 1578, 1593)),
 ('sq', 'a', (1738, 1763)),
 ('bd', 'd', (1745, 1766)),
 ('a7', 'd', (1793, 1872, 1897, 1957)),
 ('zH', 'f', (1798, 1877, 1965)),
 ('zo', 'g', (1803, 1902, 1969)),
 ('to', 'a', (2316, 2366, 2429, 2448, 2466, 2534, 2551, 2567, 2620, 2643)),
 ('z0', 'd', (2325, 2491, 2498)),
 ('ad', 'f', (2358, 2440, 2505)),
 ('z5', 'g', (2548, 2585)),
 ('yh', 'i', (2564, 2596)),
 ('zW', 'a', (2804, 2815)),
 ('aR', 'd', (2812, 2854, 2865)),
 ('sq', 'f', (2938, 3348)),
 ('to', 'g', (3065, 3080, 3096, 3111, 3145, 3164)),
 ('aG', 'j', (3181, 3230, 3263)),
 ('zI', 'm', (3222, 3268)),
 ('to', 'q', (3296, 3305, 3314, 3333, 3344, 3386, 3417)),
 ('ad', 't', (3325, 3363, 3382, 3429)),
 ('af', 'u', (3467, 3497, 3507, 3540, 3553, 3566, 3585, 3618, 3631, 3644, 3657, 3676)),
 ('yb', 'w', (3480, 3528, 3606)),
 ('aT', 'a', (3968, 3992, 4095, 4119)),
 ('zl', 'a', (4372, 4384, 4393)),
 ('aK', 'd', (4379, 4389, 4396)),
 ('aH', 'a', (4575, 5179, 5709, 5772, 5980, 5999, 6131, 6262)),
 ('aD', 'd', (4582, 4856, 4965, 5109, 5131, 5137, 5778, 5914, 5959, 6005, 6243, 6452, 6474)),
 ('zZ', 'f', (4589, 5418, 6190)),
 ('z6', 'g', (4597, 6104, 6108)),
 ('aL', 'n', (4624, 4956, 5222, 5820, 6234, 6285)),
 ('zv', 't', (4652, 4753, 4852, 4914)),
 ('av', 'u', (4670, 4734, 4757)),
 ('zw', 'x', (4675, 4695, 4700, 4726)),
 ('aj', 'y', (4793, 5321, 5466, 5551, 5557, 5589, 5595)),
 ('a2', 'z', (4803, 4885, 5263, 5509, 5541)),
 ('a4', 'A', (4814, 5631, 5744, 5807, 6224)),
 ('zV', 'D', (4819, 6254)),
 ('aC', 'F', (4836, 5234, 5858)),
 ('aT', 'I', (4980, 5018, 6558)),
 ('tt', 'J', (5029, 5330)),
 ('ao', 'K', (5064, 5141, 5161, 5169, 5185, 6248, 6277, 6547)),
 ('yi', 'L', (5077, 5145)),
 ('z2', 'M', (5212, 5228, 5696)),
 ('to', 'N', (5297, 5368, 5372, 5408)),
 ('pi', 'O', (5306, 5422)),
 ('to', 'P', (5648, 5688, 6172)),
 ('az', 'Q', (5657, 5702, 5815, 6144)),
 ('zT', 'R', (5678, 5783, 5919, 5964, 6010)),
 ('aE', 'S', (5798, 5851, 5855, 5903, 5928)),
 ('aK', 'T', (6152, 6176, 6207)),
 ('aM', 'V', (6337, 6355, 6362, 6372, 6381, 6407)),
 ('aB', 'a', (7242, 7274, 7308, 7352, 7368)),
 ('zS', 'd', (7257, 7314, 7330)),
 ('zQ', 'a', (7500, 7511, 7538)),
 ('ya', 'a', (7617, 7693, 7744)),
 ('aA', 'a', (8169, 8281, 8398, 8431, 8443)),
 ('aJ', 'd', (8217, 8325, 8354)),
 ('ze', 'a', (8655, 8711, 8760)),
 ('a1', 'a', (8801, 9011, 9157, 9198, 9205)),
 ('zE', 'd', (8806, 9141, 9164, 9185)),
 ('zY', 'f', (8819, 9016, 9151)),
 ('aJ', 'g', (8829, 8861, 8890, 8993, 9124)),
 ('bd', 'i', (8942, 9001)),
 ('bd', 'j', (9073, 9132)),
 ('yg', 'a', (9419, 9575, 10146)),
 ('ak', 'd', (9433, 9595, 10158, 10179)),
 ('ak', 'f', (9633, 9645, 9660)))


def transform_source(data):
    if type(data) is not bytes or len(data)!=10184 or hashlib.sha256(data).hexdigest()!=INPUT_SHA256:
        raise ValueError('exact A post-storage source required for bound scope map')
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
    if len(result)!=9910 or hashlib.sha256(result).hexdigest()!=OUTPUT_SHA256:
        raise ValueError('scope-name output differs from exact qualified source')
    restored=bytearray(result)
    for start,end,old in reversed(inverse):restored[start:end]=old
    if bytes(restored)!=data:raise ValueError('scope-map inverse changed input')
    return result,{'input_sha256':INPUT_SHA256,'output_sha256':OUTPUT_SHA256,
                   'AST_map_sha256':AST_MAP_SHA256,'declarations':70,'physical_edits':274,
                   'source_saved_bytes':274,'exact_inverse':True,
                   'policy':'automatic names unique within functions, reused between functions',
                   'runtime_name_resolution':False,'AST_tool_required_by_normal_build':False}
