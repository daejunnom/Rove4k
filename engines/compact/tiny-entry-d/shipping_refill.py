"""One late H28-private decoder control flow; not a generic decoder API.

Valid fixed packets preserve every decoded byte and input cursor. Invalid
partial private writes/return4 versus5 priority may differ; all failures still
bad-exit126 before native entry. H24/HQ never select this stage.
"""
import hashlib

POLICY = 'H28-private-shared-prefill-refill-v1'
BEFORE = '7bd44a4a7c26c2629406d17af2191f81f4c0995469885ebcc16e1b4fe9b5ddc4'
AFTER = '0b5314621d708024cc28c679abf62f201949c9233512ed5cce322508532b45da'
EDITS = [(1461, 'cx_u32 value=0,range=0x80000000u,prefix=0;', 'cx_u32 value=0,range=1,prefix=0;'), (1555, '    for(unsigned k=0;k<31;k++)if(cx_append(&in,&value))return 4;\n    for(cx_u32 left=bits;left;left--){', '    for(cx_u32 left=bits+1;left;left--){\n        while(!(range&0x80000000u)){\n            range<<=1;\n            if(cx_append(&in,&value))return 4;\n        }\n        if(left==1)break;'), (2650, '        while(!(range&0x80000000u)){\n            range<<=1;\n            if(cx_append(&in,&value))return 4;\n        }\n        /* All probabilities', '        /* All probabilities')]

def transform_source(source):
    if hashlib.sha256(source).hexdigest() != BEFORE:
        raise ValueError('exact H28 decoder predecessor required')
    output = bytearray()
    cursor = 0
    inverse = []
    gaps = []
    for at, old, new in EDITS:
        old, new = old.encode(), new.encode()
        if at < cursor or source[at:at+len(old)] != old:
            raise ValueError('shared-refill literal differs')
        gaps.append(source[cursor:at])
        output += gaps[-1]
        inverse.append((len(output), old, new))
        output += new
        cursor = at+len(old)
    gaps.append(source[cursor:])
    output += gaps[-1]
    output = bytes(output)
    if hashlib.sha256(output).hexdigest() != AFTER:
        raise ValueError('shared-refill output differs')
    restored = bytearray(output)
    for at, old, new in reversed(inverse):
        if restored[at:at+len(new)] != new:
            raise ValueError('shared-refill inverse differs')
        restored[at:at+len(new)] = old
    cursor = 0
    actual_gaps = []
    for at, old, new in inverse:
        actual_gaps.append(output[cursor:at])
        cursor = at+len(new)
    actual_gaps.append(output[cursor:])
    if bytes(restored) != source or gaps != actual_gaps:
        raise ValueError('shared-refill complement differs')
    return output
