"""Replay one fixed B shipping global-function map after types.

This standalone program owns these functions; they are not an external symbol
API. main, external/header references, objects, types, members and all opaque
or directive tokens remain unchanged. 9 functions retain C external
linkage kinds while their implementation-only names change. DEV bypasses this
stage. No AST, experiment, report, artifact or external source is an input.
"""
import hashlib
import re

INPUT_BYTES = 11167
INPUT_SHA256 = '6ae7748ee0e56a925405692385a8adfd141274aaee845efaae406416664b1755'
OUTPUT_BYTES = 11009
OUTPUT_SHA256 = 'ce6a8b884009a4735ad5c9dbc948b444fe1af185ee7b40dd6335946625b92587'
GROUPS = (
    ('mix', 'b', (931, 1393, 1446, 1469, 1492, 5718)),
    ('walk', 'c', (1811, 2390, 2449, 2537, 2630, 3889)),
    ('attacked', 'e', (2650, 3072, 3582, 5371, 6939)),
    ('make', 'h', (3205, 4699, 5633, 6716, 8445)),
    ('now', 'q', (745, 4428, 4876, 4890, 10064)),
    ('value', 'r', (1080, 1629, 1729, 6335, 6362)),
    ('gen', 'v', (3862, 5544, 8371)),
    ('start', 'k', (3912, 9355, 10398)),
    ('dead', 'y', (2707, 5505)),
    ('result', 'd', (8495, 8921)),
    ('think', 'i', (7698, 8874)),
    ('work', 's', (8689, 10477)),
)
TOKEN = re.compile(rb"""//[^\n]*|/\*[\s\S]*?\*/|"(?:\\[\s\S]|[^"\\])*"|'(?:\\[\s\S]|[^'\\])*'|[A-Za-z_][A-Za-z_0-9]*""")
DIRECTIVE = re.compile(rb'(?m)^[ \t]*#[^\n]*(?:\\\n[^\n]*)*')
OBSERVERS = {b'asm', b'__asm', b'__asm__', b'__func__', b'__FUNCTION__',
             b'__PRETTY_FUNCTION__', b'__builtin_dump_struct'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def transform_source(source):
    if type(source) is not bytes or len(source) != INPUT_BYTES or sha(source) != INPUT_SHA256:
        raise ValueError('exact post-types B shipping source required')
    tokens = list(TOKEN.finditer(source))
    identifiers = {t.start(): t.group() for t in tokens if t.group()[:1] in b'ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz'}
    opaque = [(t.start(), t.end(), t.group()) for t in tokens if t.start() not in identifiers]
    directives = [(t.start(), t.end(), t.group()) for t in DIRECTIVE.finditer(source)]
    if set(identifiers.values()) & OBSERVERS:
        raise ValueError('name-observing or asm input is outside fixed policy')
    if len(GROUPS) != 12 or len({row[0] for row in GROUPS}) != 12 or len({row[1] for row in GROUPS}) != 12:
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
    if len(edits) != 46:
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
    return result, {'stage':'shipping-after-types','mapped_functions':12,'physical_edits':46,
                    'local_renames':0,'exact_inverse':True,'protected_complement_bytes':sum(map(len,complement)),
                    'protected_complement_sha256':sha(b''.join(complement)),
                    'directives_and_opaque_exact':True,'DEV_bypasses_stage':True,
                    'standalone_TU_implementation_names_only':True,
                    'main_external_API_objects_types_members_unchanged':True,
                    'entire_native_identity_to_predecessor':False,
                    'exact_reviewed_new_native_identity_required':True}
