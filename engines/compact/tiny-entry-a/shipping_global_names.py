"""Replay one fixed A shipping global-function map after startup.

This standalone program owns these functions; they are not an external symbol
API. main, external/header references, objects, types, members and all opaque
or directive tokens remain unchanged. Eight functions retain C external
linkage kinds while their implementation-only names change. DEV bypasses this
stage. No AST, experiment, report, artifact or external source is an input.
"""
import hashlib
import re

INPUT_BYTES = 9370
INPUT_SHA256 = '7dc2243e255e2b191e4bb7785826c69556c45534ed4c1832796ccdca637d4f55'
OUTPUT_BYTES = 9265
OUTPUT_SHA256 = '06ca0bc2871c2b1a8ce1eeccc24d65680bbc874066498db6e0c295af89003a46'
GROUPS = (
    ('bf', 'b', (1446, 2328, 2455, 2465, 2478, 2488, 3678, 3693, 3707, 3722)),
    ('aa', 'c', (1633, 2047, 2530, 3347, 3402, 3487, 4321, 5408)),
    ('aq', 'e', (923, 1318, 1370, 1392, 1414, 4642)),
    ('au', 'h', (4243, 5349, 5471, 5515, 5559, 6222)),
    ('bh', 'k', (2642, 2967, 3018, 3251, 3415, 3500)),
    ('aW', 'j', (7380, 8069, 8791, 9159, 9202)),
    ('al', 'r', (1071, 1506, 1559, 4976, 4998)),
    ('ac', 'v', (2175, 4560, 5210, 6834)),
    ('ae', 's', (4210, 4931, 5276, 5755)),
    ('bc', 'l', (1349, 2269, 2570, 3748)),
    ('bg', 'g', (1605, 1666, 2787, 3559)),
    ('aF', 'O', (4165, 5723, 5742)),
    ('aN', 'i', (6702, 7839, 8451)),
    ('aZ', 'o', (6521, 6795, 6987)),
    ('am', 'q', (3580, 7704, 8685)),
    ('ar', 'T', (3534, 4481, 6760)),
    ('as', 'u', (738, 4095, 8415)),
    ('aw', 'V', (3779, 4669, 6071)),
    ('ba', 'n', (2102, 2506, 2512)),
    ('bb', 'd', (1295, 1492, 1545)),
    ('aO', 'w', (8058, 9195)),
    ('aP', 'x', (6882, 7295)),
    ('aS', 'y', (7919, 8242)),
    ('aU', 'z', (7596, 9164)),
    ('aV', 'A', (7069, 8761)),
    ('aX', 'B', (7508, 8680)),
    ('ag', 'C', (6094, 7252)),
    ('be', 'D', (1887, 2558)),
)
TOKEN = re.compile(rb"""//[^\n]*|/\*[\s\S]*?\*/|"(?:\\[\s\S]|[^"\\])*"|'(?:\\[\s\S]|[^'\\])*'|[A-Za-z_][A-Za-z_0-9]*""")
DIRECTIVE = re.compile(rb'(?m)^[ \t]*#[^\n]*(?:\\\n[^\n]*)*')
OBSERVERS = {b'asm', b'__asm', b'__asm__', b'__func__', b'__FUNCTION__',
             b'__PRETTY_FUNCTION__', b'__builtin_dump_struct'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def transform_source(source):
    if type(source) is not bytes or len(source) != INPUT_BYTES or sha(source) != INPUT_SHA256:
        raise ValueError('exact post-startup A shipping source required')
    tokens = list(TOKEN.finditer(source))
    identifiers = {t.start(): t.group() for t in tokens if t.group()[:1] in b'ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz'}
    opaque = [(t.start(), t.end(), t.group()) for t in tokens if t.start() not in identifiers]
    directives = [(t.start(), t.end(), t.group()) for t in DIRECTIVE.finditer(source)]
    if set(identifiers.values()) & OBSERVERS:
        raise ValueError('name-observing or asm input is outside fixed policy')
    if len(GROUPS) != 28 or len({row[0] for row in GROUPS}) != 28 or len({row[1] for row in GROUPS}) != 28:
        raise ValueError('fixed unique global map differs')
    edits = []
    for old, new, positions in GROUPS:
        old = old.encode(); new = new.encode()
        actual = tuple(at for at, spelling in identifiers.items() if spelling == old)
        if actual != positions or len(old) != 2 or len(new) != 1:
            raise ValueError('owned function physical inventory differs')
        for at in positions:
            if any(at < b and at+2 > a for a,b,_ in opaque+directives):
                raise ValueError('function edit overlaps opaque/directive region')
            edits.append((at, at+2, old, new))
    edits.sort()
    if len(edits) != 105:
        raise ValueError('fixed physical function edit count differs')
    parts = []; complement = []; inverse_edits = []; previous = 0; delta = 0
    for start, end, old, new in edits:
        if start < previous or source[start:end] != old:
            raise ValueError('function edits overlap or spelling differs')
        unchanged = source[previous:start]; parts.extend((unchanged,new)); complement.append(unchanged)
        inverse_edits.append((start+delta,start+delta+1,old,new)); delta -= 1; previous = end
    parts.append(source[previous:]); complement.append(source[previous:]); result = b''.join(parts)
    inverse = bytearray(result)
    for start,end,old,new in reversed(inverse_edits):
        if inverse[start:end] != new: raise ValueError('function inverse spelling differs')
        inverse[start:end] = old
    if bytes(inverse) != source or len(result) != OUTPUT_BYTES or sha(result) != OUTPUT_SHA256:
        raise ValueError('fixed output or exact inverse differs')
    if [t.group() for t in DIRECTIVE.finditer(result)] != [r[2] for r in directives]:
        raise ValueError('protected directive bytes differ')
    after_opaque = [t.group() for t in TOKEN.finditer(result) if t.group()[:1] not in b'ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz']
    if after_opaque != [r[2] for r in opaque]:
        raise ValueError('protected literal/comment bytes differ')
    return result, {'stage':'shipping-after-startup','mapped_functions':28,'physical_edits':105,
                    'local_renames':0,'exact_inverse':True,'protected_complement_bytes':sum(map(len,complement)),
                    'protected_complement_sha256':sha(b''.join(complement)),
                    'directives_and_opaque_exact':True,'DEV_bypasses_stage':True,
                    'standalone_TU_implementation_names_only':True,
                    'main_external_API_objects_types_members_unchanged':True,
                    'entire_native_identity_to_predecessor_required':True}
