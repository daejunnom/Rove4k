"""Replay the qualified full-F plain-int keyword source form.

The exact input has no S token in code or directives. Seven include lines
precede the inserted ordinary S macro;91 plain int keyword positions change.
Widths such as int8_t/int16_t, literals, headers and all other bytes retain
their spelling. This is an owned fixed-source transformation, not a general
macro equivalence rule. Source/macro dumps and line identities differ.
The function reads no files and starts no processes. DEV and actual optional
policies bypass it; their separate full-reference generation uses it.
"""
import hashlib

INPUT=(8755,'8a6383c9185defbcb68c03a3acfca72c0b16f2ccec09a44d9575d80a262365ae')
OUTPUT=(8587,'a1ebe0f07ddf1889a9caa17f6903a5f2ecbc62ac3249d7006176a8aa5ce736cd')
COMPLEMENT=(8482,'aae6295ad689722f2b29c5b2d1c35830d19e2455b448dac6a80ad7be65b2b810')
INT_OFFSETS=(254, 478, 508, 592, 722, 882, 888, 894, 914, 964, 1099, 1105, 1250, 1256, 1263, 1394, 1413, 1417, 1422, 1439, 1445, 1471, 1490, 1502, 1534, 1686, 1750, 1770, 1876, 1882, 1948, 1975, 2218, 2433, 2439, 2446, 2453, 2460, 2487, 2575, 2596, 2602, 2609, 2621, 2666, 2722, 2830, 2903, 2920, 2936, 2962, 3100, 3314, 3384, 3445, 3782, 3945, 3977, 4004, 4011, 4100, 4134, 4156, 4162, 4168, 4174, 4204, 4254, 4351, 4454, 4565, 4591, 4617, 4763, 4780, 4792, 4932, 5171, 5466, 5488, 5537, 5866, 6108, 6375, 6392, 6509, 7227, 7985, 8015, 8246, 8688)
EDITS=((167,167,b'',b'#define S int\n'),)+tuple((a,a+14-2*i,b'int',b'S') for i,a in enumerate(INT_OFFSETS))

def _pin(data):return len(data),hashlib.sha256(data).hexdigest()

def transform_source(source,family='F'):
    if family!='F' or type(source) is not bytes or _pin(source)!=INPUT:
        raise ValueError('fixed full-F int keyword input differs')
    parts=[];gaps=[];cursor=written=0
    for start,target,old,new in EDITS:
        gap=source[cursor:start]
        if start<cursor or source[start:start+len(old)]!=old or written+len(gap)!=target:
            raise ValueError('fixed int keyword edit literal/offset differs')
        parts.extend((gap,new));gaps.append(gap);cursor=start+len(old);written=target+len(new)
    parts.append(source[cursor:]);gaps.append(source[cursor:]);candidate=b''.join(parts)
    inverse=[];newgaps=[];cursor=previous_old=0
    for start,target,old,new in EDITS:
        gap=candidate[cursor:target]
        if gap!=source[previous_old:start] or candidate[target:target+len(new)]!=new:
            raise ValueError('fixed int keyword inverse literal/gap differs')
        inverse.extend((gap,old));newgaps.append(gap);cursor=target+len(new);previous_old=start+len(old)
    inverse.append(candidate[cursor:]);newgaps.append(candidate[cursor:])
    if _pin(candidate)!=OUTPUT or b''.join(inverse)!=source or gaps!=newgaps or _pin(b''.join(gaps))!=COMPLEMENT:
        raise ValueError('fixed int keyword output/inverse/complement differs')
    return candidate,{'family':'F','stage':'plain-int-keyword-token','input_bytes':INPUT[0],'input_sha256':INPUT[1],
        'output_bytes':OUTPUT[0],'output_sha256':OUTPUT[1],'raw_delta':-168,'int_tokens':91,'edits':92,
        'macro_insert_offset':167,'headers_unchanged':True,'full_inverse':True,'all_gaps_equal':True,
        'gap_count':93,'complement_bytes':COMPLEMENT[0],'complement_sha256':COMPLEMENT[1],
        'scope':'exact full-F owned source; general macro/source-location equivalence not claimed','external_reads':0,
        'compiler_codec_engine_executed_by_transform':0}
