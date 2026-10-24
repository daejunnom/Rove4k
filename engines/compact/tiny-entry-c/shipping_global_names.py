"""Replay one fixed C shipping global-function map after types.

This standalone program owns these functions; they are not an external symbol
API. main, external/header references, objects, types, members and all opaque
or directive tokens remain unchanged. 9 functions retain C external
linkage kinds while their implementation-only names change. DEV bypasses this
stage. No AST, experiment, report, artifact or external source is an input.
"""
import hashlib
import re

INPUT_BYTES = 10445
INPUT_SHA256 = 'd424d14f5cb16d7e6a39383821a70ef96cd6c69bcc99c5a948dc4f5a907546d4'
OUTPUT_BYTES = 10305
OUTPUT_SHA256 = '597b74bd71a843b58be58944c6763d09a31159caaf571c9dc80d39253beadbab'
GROUPS = (
    ('attacked', 'b', (1761, 2185, 2695, 3526, 3587, 3677, 4862, 6071)),
    ('mix', 'c', (975, 1463, 1516, 1539, 1562, 5212)),
    ('make', 'e', (2318, 5122, 5876, 7623)),
    ('value', 'h', (1179, 1437, 5627, 5654)),
    ('gen', 'r', (3729, 5035, 7549)),
    ('now', 'k', (786, 4524, 9387)),
    ('start', 'q', (3776, 8644, 9702)),
    ('dead', 's', (1817, 4996)),
    ('think', 'd', (6809, 8111)),
    ('work', 'u', (7883, 9814)),
)
TOKEN = re.compile(rb"""//[^\n]*|/\*[\s\S]*?\*/|"(?:\\[\s\S]|[^"\\])*"|'(?:\\[\s\S]|[^'\\])*'|[A-Za-z_][A-Za-z_0-9]*""")
DIRECTIVE = re.compile(rb'(?m)^[ \t]*#[^\n]*(?:\\\n[^\n]*)*')
OBSERVERS = {b'asm', b'__asm', b'__asm__', b'__func__', b'__FUNCTION__',
             b'__PRETTY_FUNCTION__', b'__builtin_dump_struct'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def transform_source(source):
    if type(source) is not bytes or len(source) != INPUT_BYTES or sha(source) != INPUT_SHA256:
        raise ValueError('exact post-types C shipping source required')
    tokens = list(TOKEN.finditer(source))
    identifiers = {t.start(): t.group() for t in tokens if t.group()[:1] in b'ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz'}
    opaque = [(t.start(), t.end(), t.group()) for t in tokens if t.start() not in identifiers]
    directives = [(t.start(), t.end(), t.group()) for t in DIRECTIVE.finditer(source)]
    if set(identifiers.values()) & OBSERVERS:
        raise ValueError('name-observing or asm input is outside fixed policy')
    if len(GROUPS) != 10 or len({row[0] for row in GROUPS}) != 10 or len({row[1] for row in GROUPS}) != 10:
        raise ValueError('fixed unique global map differs')
    edits = []
    for old, new, positions in GROUPS:
        old = old.encode(); new = new.encode()
        actual = tuple(at for at, spelling in identifiers.items() if spelling == old)
        if actual != positions or len(old) < 2 or len(new) != 1:
            raise ValueError('owned function physical inventory differs')
        for at in positions:
            if any(at < b and at+len(old) > a for a,b,_ in opaque+directives):
                raise ValueError('function edit overlaps opaque/directive region')
            edits.append((at, at+len(old), old, new))
    edits.sort()
    if len(edits) != 37:
        raise ValueError('fixed physical function edit count differs')
    parts = []; complement = []; inverse_edits = []; previous = 0; delta = 0
    for start, end, old, new in edits:
        if start < previous or source[start:end] != old:
            raise ValueError('function edits overlap or spelling differs')
        unchanged = source[previous:start]; parts.extend((unchanged,new)); complement.append(unchanged)
        inverse_edits.append((start+delta,start+delta+1,old,new)); delta += 1-len(old); previous = end
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
    return result, {'stage':'shipping-after-types','mapped_functions':10,'physical_edits':37,
                    'local_renames':0,'exact_inverse':True,'protected_complement_bytes':sum(map(len,complement)),
                    'protected_complement_sha256':sha(b''.join(complement)),
                    'directives_and_opaque_exact':True,'DEV_bypasses_stage':True,
                    'standalone_TU_implementation_names_only':True,
                    'main_external_API_objects_types_members_unchanged':True,
                    'entire_native_identity_to_predecessor':False,
                    'exact_reviewed_new_native_identity_required':True}
