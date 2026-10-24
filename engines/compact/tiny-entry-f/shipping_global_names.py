"""Replay one fixed F shipping global-function map after startup.

This standalone program owns these functions; they are not an external symbol
API. main, external/header references, objects, types, members and all opaque
or directive tokens remain unchanged. Eight functions retain C external
linkage kinds while their implementation-only names change. DEV bypasses this
stage. No AST, experiment, report, artifact or external source is an input.
"""
import hashlib
import re

INPUT_BYTES = 9422
INPUT_SHA256 = '109cb9df07a6d2a44b2930abcdadaba2246d953e1276a70a66ecb182fd77544a'
OUTPUT_BYTES = 9318
OUTPUT_SHA256 = 'e280d859127c5d250ca912cfe636518fd088813ffce4266589fa6f04b7e87424'
GROUPS = (
    ('aF', 'b', (1411, 2289, 2415, 2425, 2438, 2448, 3648, 3663, 3677, 3692)),
    ('aa', 'c', (1600, 2490, 3314, 3369, 3454, 4525, 6231)),
    ('aH', 'e', (2601, 2940, 2991, 3224, 3382, 3467)),
    ('ab', 'h', (1848, 1988, 2114, 4756, 5320, 6885)),
    ('ag', 'r', (899, 1282, 1335, 1357, 1379, 4838)),
    ('ad', 's', (1047, 1472, 1525, 5125, 5147)),
    ('ay', 'k', (7431, 8121, 8843, 9211, 9254)),
    ('aD', 'l', (1313, 2232, 2530, 3718)),
    ('aG', 'g', (1571, 1634, 2759, 3527)),
    ('al', 'v', (4207, 5106, 5368, 6258)),
    ('ao', 'S', (4174, 4398, 5388, 5624)),
    ('aA', 'j', (6581, 6851, 7038)),
    ('aB', 'n', (2041, 2466, 2472)),
    ('aC', 'd', (1259, 1458, 1511)),
    ('ae', 'o', (3548, 7756, 8738)),
    ('ah', 'T', (3501, 4680, 6822)),
    ('ai', 'q', (714, 4062, 8467)),
    ('aj', 'U', (4452, 5445, 5990)),
    ('ak', 'V', (3749, 4864, 5784)),
    ('ar', 'u', (6762, 7891, 8504)),
    ('aE', 'w', (1880, 2518)),
    ('ac', 'i', (5807, 7303)),
    ('as', 'x', (8110, 9247)),
    ('at', 'y', (6933, 7346)),
    ('av', 'z', (7647, 9216)),
    ('aw', 'A', (7971, 8294)),
    ('ax', 'B', (7120, 8813)),
    ('az', 'C', (7559, 8733)),
)
TOKEN = re.compile(rb"""//[^\n]*|/\*[\s\S]*?\*/|"(?:\\[\s\S]|[^"\\])*"|'(?:\\[\s\S]|[^'\\])*'|[A-Za-z_][A-Za-z_0-9]*""")
DIRECTIVE = re.compile(rb'(?m)^[ \t]*#[^\n]*(?:\\\n[^\n]*)*')
OBSERVERS = {b'asm', b'__asm', b'__asm__', b'__func__', b'__FUNCTION__',
             b'__PRETTY_FUNCTION__', b'__builtin_dump_struct'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def transform_source(source):
    if type(source) is not bytes or len(source) != INPUT_BYTES or sha(source) != INPUT_SHA256:
        raise ValueError('exact post-startup F shipping source required')
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
    if len(edits) != 104:
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
    return result, {'stage':'shipping-after-startup','mapped_functions':28,'physical_edits':104,
                    'local_renames':0,'exact_inverse':True,'protected_complement_bytes':sum(map(len,complement)),
                    'protected_complement_sha256':sha(b''.join(complement)),
                    'directives_and_opaque_exact':True,'DEV_bypasses_stage':True,
                    'standalone_TU_implementation_names_only':True,
                    'main_external_API_objects_types_members_unchanged':True,
                    'entire_native_identity_to_predecessor_required':True}
