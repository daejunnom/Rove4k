"""Scalar H28 staging of the preserved H24 sources, not a generic codec selector.

Native/model21/BCJ/full-image geometry remain unchanged. H28 uses a 512 MiB
temporary context table, released by the same checked munmap before entry.
The caller selects only scalar shipping; HQ/DEV and all original H24 APIs
retain the original sources. Data below is ordinary fixed producer input.
"""
import hashlib

FORMAT = 'rove4k-context-h28-base10-fixed21-body232-zero4-v1'
FIXED = {'packer.py': {'before': 'af95c8fd8a38f999bb846f024e13689d417e28c0ce0ec830f8a200b4cef3fd7e', 'after': '20509f31c3c19d49a0ed895b4a17deab6cab9de3d12dcc671e49fc3d617dd25d', 'edits': [(6465, 'rove4k-context-h24-base10-fixed21-body232-zero4-v3', 'rove4k-context-h28-base10-fixed21-body232-zero4-v1')]}, 'loader/codec.py': {'before': '7e57f503a26d20a5e1033a8d2f366d2315c4f407c98198167842ef53e4f74004', 'after': 'ea2cf9e902c11453113aa6817d985abdeff8a99e3abb797d76564c9b908f7a1e', 'edits': [(50, 'H24/base10', 'H28/base10'), (798, "FORMAT='rove4k-context-h24-base10-u32-zero4-v1'", "FORMAT='rove4k-context-h28-base10-u32-zero4-v1'"), (846, "PACKET_FORMAT='rove4k-context-h24-base10-fixed21-replay-zero4-v2'", "PACKET_FORMAT='rove4k-context-h28-base10-fixed21-replay-zero4-v1'"), (912, "BODY_PACKET_FORMAT='rove4k-context-h24-base10-fixed21-body232-zero4-v3'", "BODY_PACKET_FORMAT='rove4k-context-h28-base10-fixed21-body232-zero4-v1'"), (984, 'TABLE_BYTES=1<<25', 'TABLE_BYTES=1<<29'), (2079, "fixed.get('hash_bits')!=24", "fixed.get('hash_bits')!=28"), (4378, 'at=(value>>8)*2', 'at=(value>>4)*2'), (5846, "'hash_bits':24", "'hash_bits':28")]}, 'loader/decoder.h': {'before': '162129fbc2e876252d7a3f58bda9672aff3a1a6170c35903b73624e571b60fd6', 'after': '7bd44a4a7c26c2629406d17af2191f81f4c0995469885ebcc16e1b4fe9b5ddc4', 'edits': [(232, 'zeroed 32 MiB table', 'zeroed 512 MiB table'), (2188, 'at=(hash>>8)*2', 'at=(hash>>4)*2')]}, 'loader/loader.c': {'before': '41aae27e0991b82eae46bcf6665dcf5fe1d18d8b56e72c82cc100fe5427deba0', 'after': '6d66628492281d50d77c485278c97ceefdee62f30ff6c6f7081f6a3186d2676e', 'edits': [(416, '#define CONTEXT_BYTES 33554432UL', '#define CONTEXT_BYTES 536870912UL'), (1634, 'fixed H24 table', 'fixed H28 table')]}, 'loader/models.json': {'before': '3101a5638551990cb2d5a33d6d28fbab436d04d301b676cc2e45afa63b7f6920', 'after': '0b766e6597a685ff55ea5d49ad684188e5242847e09dec32ee50c5274af55239', 'edits': [(15, 'rove4k-context-h24-base10-u32-zero4-v1', 'rove4k-context-h28-base10-u32-zero4-v1'), (58, '"hash_bits": 24', '"hash_bits": 28'), (103, '"table_bytes": 33554432', '"table_bytes": 536870912')]}}

def prepare_sources(sources):
    if set(sources) != set(FIXED):
        raise ValueError('exact scalar H28 source set required')
    result = {}
    for name, fixed in FIXED.items():
        original = sources[name]
        if hashlib.sha256(original).hexdigest() != fixed['before']:
            raise ValueError('H28 predecessor differs: '+name)
        cursor = 0
        output = bytearray()
        inverse = []
        gaps = []
        for at, old, new in fixed['edits']:
            old, new = old.encode(), new.encode()
            if at < cursor or original[at:at+len(old)] != old:
                raise ValueError('H28 literal differs: '+name)
            gap = original[cursor:at]
            gaps.append(gap)
            output += gap
            inverse.append((len(output), old, new))
            output += new
            cursor = at+len(old)
        gaps.append(original[cursor:])
        output += gaps[-1]
        output = bytes(output)
        if hashlib.sha256(output).hexdigest() != fixed['after']:
            raise ValueError('H28 output differs: '+name)
        restored = bytearray(output)
        for at, old, new in reversed(inverse):
            if restored[at:at+len(new)] != new:
                raise ValueError('H28 inverse literal differs: '+name)
            restored[at:at+len(new)] = old
        cursor = 0
        actual_gaps = []
        for at, old, new in inverse:
            actual_gaps.append(output[cursor:at])
            cursor = at+len(new)
        actual_gaps.append(output[cursor:])
        if bytes(restored) != original or actual_gaps != gaps:
            raise ValueError('H28 inverse/complement differs: '+name)
        result[name] = output
    return result
