"""Replay the fixed MaterialNoise-v1 implementation-function spelling map.

Only exact post-material-noise shipping input is admitted. This standalone TU
owns these 29 functions; nine retain C external linkage kinds but are not an
external symbol API. main, external/header references, objects, types, members,
all directive and opaque bytes remain unchanged. Full F and DEV bypass this
stage. No AST, experiment, report, artifact or external source is an input.
"""
import hashlib
import re

INPUT_BYTES = 8779
INPUT_SHA256 = 'a4f3dafc7a99ac180d582350a34ec41a78e6f51f6ec202bc1e88dcda8fd24323'
OUTPUT_BYTES = 8677
OUTPUT_SHA256 = 'dd1599d4d414107383fd534701c3c7e58a4eb861a47ab174a405f7a8cc64335e'
GROUPS = (
    ('aF', 'b', (1269, 2143, 2269, 2279, 2292, 2302, 3502, 3517, 3531, 3546)),
    ('aH', 'c', (2455, 2794, 2845, 3078, 3236, 3321)),
    ('aa', 'e', (1454, 2344, 3168, 3223, 3308, 4139)),
    ('ab', 'g', (1702, 1842, 1968, 4370, 4945, 6242)),
    ('ag', 'h', (867, 1140, 1193, 1215, 1237, 4452)),
    ('ad', 'r', (1015, 1330, 1381, 4739, 4759)),
    ('ay', 'k', (6788, 7478, 8200, 8568, 8611)),
    ('aD', 'l', (1171, 2086, 2384, 3572)),
    ('aG', 'i', (1425, 1488, 2613, 3381)),
    ('aA', 'j', (5938, 6208, 6395)),
    ('aB', 'n', (1895, 2320, 2326)),
    ('aC', 'd', (1117, 1316, 1367)),
    ('ae', 'o', (3402, 7113, 8095)),
    ('ah', 'v', (3355, 4294, 6179)),
    ('ai', 'q', (682, 3916, 7824)),
    ('aj', 's', (4072, 5039, 5513)),
    ('ak', 'N', (3603, 4478, 5307)),
    ('al', 'O', (3984, 4720, 4975)),
    ('ar', 'u', (6119, 7248, 7861)),
    ('aE', 'w', (1734, 2372)),
    ('ac', 'x', (5330, 6660)),
    ('af', 'Q', (1505, 4258)),
    ('am', 'R', (3832, 4118)),
    ('as', 'y', (7467, 8604)),
    ('at', 'z', (6290, 6703)),
    ('av', 'A', (7004, 8573)),
    ('aw', 'B', (7328, 7651)),
    ('ax', 'C', (6477, 8170)),
    ('az', 'D', (6916, 8090)),
)
TOKEN = re.compile(rb"""//[^\n]*|/\*[\s\S]*?\*/|"(?:\\[\s\S]|[^"\\])*"|'(?:\\[\s\S]|[^'\\])*'|[A-Za-z_][A-Za-z_0-9]*""")
DIRECTIVE = re.compile(rb'(?m)^[ \t]*#[^\n]*(?:\\\n[^\n]*)*')
OBSERVERS = {b'asm', b'__asm', b'__asm__', b'__func__', b'__FUNCTION__',
             b'__PRETTY_FUNCTION__', b'__builtin_dump_struct'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def transform_source(source):
    if type(source) is not bytes or len(source) != INPUT_BYTES or sha(source) != INPUT_SHA256:
        raise ValueError('exact post-material-noise F shipping source required')
    tokens = list(TOKEN.finditer(source))
    identifiers = {t.start(): t.group() for t in tokens if t.group()[:1] in b'ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz'}
    opaque = [(t.start(), t.end(), t.group()) for t in tokens if t.start() not in identifiers]
    directives = [(t.start(), t.end(), t.group()) for t in DIRECTIVE.finditer(source)]
    if set(identifiers.values()) & OBSERVERS:
        raise ValueError('name-observing or asm input is outside fixed policy')
    if len(GROUPS) != 29 or len({row[0] for row in GROUPS}) != 29 or len({row[1] for row in GROUPS}) != 29:
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
    if len(edits) != 102:
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
    return result, {'stage':'shipping-after-material-noise','mapped_functions':29,'physical_edits':102,
                    'local_renames':0,'exact_inverse':True,'protected_complement_bytes':sum(map(len,complement)),
                    'protected_complement_sha256':sha(b''.join(complement)),
                    'directives_and_opaque_exact':True,'DEV_bypasses_stage':True,'full_policy_bypasses_stage':True,
                    'standalone_TU_implementation_names_only':True,
                    'main_external_API_objects_types_members_unchanged':True,
                    'entire_native_identity_to_predecessor_required':True}
