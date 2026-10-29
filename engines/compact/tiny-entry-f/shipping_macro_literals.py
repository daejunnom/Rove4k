"""Late shipping specialization for the exact full-F fixed-int source domain.

MOVES512 and MATE30000 retain int token types at every admitted use.  Only
these definitions and their fixed numeric uses change.  Source locations and
preprocessor macro dumps are not public observations of this fixed domain.
The function reads no files and starts no process.  DEV and optional-policy
bypasses are the caller's responsibility before this exact input is admitted.
"""
import hashlib
INPUT = (8793, '6d1f0c57ac56c4e4d25022b58716c94704a5ce4ed4a110e3ca7d281b1d3b21d4')
OUTPUT = (8755, '8a6383c9185defbcb68c03a3acfca72c0b16f2ccec09a44d9575d80a262365ae')
COMPLEMENT = (8708, '2962a9ad1911b4ca6f0a2d2b330671e81ae42ee6ff06615eec2c4385f2196887')
EDITS = ((169, 169, b'#define MOVES 512\n', b''), (187, 169, b'#define MATE 30000\n', b''), (2559, 2522, b'MOVES', b'512'), (4381, 4342, b'MOVES', b'512'), (4398, 4357, b'MOVES', b'512'), (4421, 4378, b'MATE', b'30000'), (4549, 4507, b'MATE', b'30000'), (5293, 5252, b'MATE', b'30000'), (5327, 5287, b'MATE', b'30000'), (5534, 5495, b'MATE', b'30000'), (5541, 5503, b'MATE', b'30000'), (5892, 5855, b'MATE', b'30000'), (6396, 6360, b'MOVES', b'512'))

def _pin(data):
    return len(data), hashlib.sha256(data).hexdigest()

def transform_source(data, family='F'):
    if family != 'F' or not isinstance(data, bytes):
        raise ValueError('fixed full-F bytes domain required')
    if _pin(data) != INPUT:
        raise ValueError('fixed full-F input identity')
    parts=[]; gaps=[]; previous=0
    for old_at,new_at,old,new in EDITS:
        if old_at < previous or data[old_at:old_at+len(old)] != old:
            raise ValueError('fixed macro edit literal')
        gap=data[previous:old_at]
        parts.extend((gap,new)); gaps.append(gap)
        previous=old_at+len(old)
    parts.append(data[previous:]); gaps.append(data[previous:])
    result=b''.join(parts)
    if _pin(result) != OUTPUT or _pin(b''.join(gaps)) != COMPLEMENT:
        raise ValueError('fixed macro output or complement identity')
    inverse=[]; previous=0; previous_old=0
    for old_at,new_at,old,new in EDITS:
        gap=result[previous:new_at]
        if gap != data[previous_old:old_at] or result[new_at:new_at+len(new)] != new:
            raise ValueError('fixed macro inverse gap or literal')
        inverse.extend((gap,old))
        previous=new_at+len(new); previous_old=old_at+len(old)
    tail=result[previous:]
    if tail != data[previous_old:]:
        raise ValueError('fixed macro inverse tail')
    inverse.append(tail)
    if b''.join(inverse) != data:
        raise ValueError('fixed macro complete inverse')
    return result, {
        'family':'F', 'operation':'fixed-int-macro-literals',
        'input':{'bytes':INPUT[0],'sha256':INPUT[1]},
        'output':{'bytes':OUTPUT[0],'sha256':OUTPUT[1]},
        'edits':len(EDITS), 'all_gaps_equal':True, 'full_inverse':True,
        'complement':{'bytes':COMPLEMENT[0],'sha256':COMPLEMENT[1]},
        'expanded_tokens':'MOVES4 uses int512; MATE7 uses int30000; two definitions removed',
        'scope':'exact full-F shipping source only; no general macro or source-location equivalence'
    }
