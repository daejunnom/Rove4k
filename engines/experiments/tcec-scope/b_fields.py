"""One fixed full-B member spelling after the qualified compact stage.

The measured combined mapping changes only three struct declarations and their
member accesses.  Member order, types, dimensions, storage and executable code
are unchanged.  It reads no experiment, receipt, generated engine or compiler.
The earlier native comparison is evidence metadata, never a generation input.
"""
import hashlib
import re


INPUT = (8828, '8b0547d11841697d53bda2e59fb12018e6599a88ffd3a2f68a7b3f27930975bf')
OUTPUT = (8770, '23d9de0788b0058c0a11744290bdf2d39582b16d6af48501d9021bbb57f54bfe')
DECLARATIONS = (
    ('worker', 'typedef struct{I id,zB;N zi;D z4,zQ[4224];int16_t zM[128][128],zw[13][13],zx[1024];}zd;',
     {'id': 'i', 'zB': 'd', 'zi': 'm', 'z4': 'n', 'zQ': 'k', 'zM': 'h', 'zw': 'c', 'zx': 'f'},
     ('id', 'zB', 'zi', 'z4', 'zQ', 'zM', 'zw', 'zx')),
    ('entry', 'typedef struct{atomic_flag zY;D zP,zA;}zb;',
     {'zY': 'a', 'zP': 'h', 'zA': 'v'}, ('zY', 'zP', 'zA')),
    ('board', 'typedef struct{int8_t b[128];D bb[2][7];I s,c,e,k[2],zL,v;D h,r;}za;',
     {'bb': 'a', 'zL': 'n'}, ('b', 'bb', 's', 'c', 'e', 'k', 'zL', 'v', 'h', 'r')),
)
TOKEN = re.compile(rb'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|->|[A-Za-z_]\w*|[^\s]')
REFERENCE = {
    'external_comparison': 'rove4k-B-field-alias-20261025-v1/result.json',
    'external_comparison_sha256': 'aef60e74dcf8f11b533a6bdec7b99ae459b62cdd6cdd73652fc38c162633d170',
    'external_proof': 'rove4k-B-field-alias-20261025-v1/3/proof.json',
    'external_proof_sha256': '4ecd808228049646f01d0b3565128936e1126ea88184c411d4705e56bf56888c',
    'native_bytes': 25912,
    'native_sha256': 'f9f41338fad0e28aee26499f2015357aba05dcdecae8e1da1b60c1e676f5b27b',
    'native_identity': 'two actual same-recipe compiler invocations, full bytes equal',
    'whole_bytes': 4265,
    'whole_sha256': 'ae75ae715ce0ec4452cf23821e79ee2d1ea7f3d6fbac7280889901364477fe4a',
    'runtime_qualification': 'separate canonical fresh build and JIT UCI checks required',
}


def pin(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def require(value, message):
    if not value:
        raise ValueError(message)


def restore_source(candidate, proof):
    require(type(candidate) is bytes and proof.get('kind') == 'tcec-B-fields-v1'
            and pin(candidate) == proof.get('output'), 'B fields output differs')
    data = candidate
    for edit in reversed(proof['edits']):
        at = edit['new_start']
        old, new = edit['old'].encode('ascii'), edit['new'].encode('ascii')
        require(data[at:at + len(new)] == new, 'B fields inverse span differs')
        data = data[:at] + old + data[at + len(new):]
    require(pin(data) == proof['input'], 'B fields inverse input differs')
    return data


def transform_source(source):
    """Return the one admitted combined spelling and its complete inverse."""
    require(type(source) is bytes and (len(source), pin(source)['sha256']) == INPUT,
            'exact qualified full-B compact source required')
    macros = set(re.findall(rb'^#define\s+([A-Za-z_]\w*)', source, re.M))
    changes, mapping, bodies = [], {}, []
    for name, text, names, fields in DECLARATIONS:
        old = text.encode('ascii')
        require(source.count(old) == 1, 'one exact B struct declaration required: ' + name)
        require(not {value.encode('ascii') for value in names.values()} & macros,
                'B member alias collides with a macro')
        require(len(set(names.get(value, value) for value in fields)) == len(fields),
                'B alias duplicates another member in its struct')
        require(not set(mapping) & set(names), 'ambiguous old B member name')
        new = re.sub(rb'[A-Za-z_]\w*',
            lambda match: names.get(match.group().decode('ascii'), match.group().decode('ascii')).encode('ascii'), old)
        at = source.index(old)
        changes.append((at, at + len(old), 'declaration-' + name, old, new))
        bodies.append((at, at + len(old)))
        mapping.update(names)
    tokens = list(TOKEN.finditer(source))
    references = {name: 0 for name in mapping}
    for index, token in enumerate(tokens):
        old = token.group()
        if index and tokens[index - 1].group() in (b'.', b'->'):
            name = old.decode('ascii')
            if name in mapping:
                require(not any(a <= token.start() < b for a, b in bodies),
                        'B member access overlaps a declaration')
                changes.append((token.start(), token.end(), 'member-reference', old,
                                mapping[name].encode('ascii')))
                references[name] += 1
    require(all(references.values()), 'B renamed member has no actual reference')
    changes.sort()
    parts, edits, gaps = [], [], []
    old_at = new_at = 0
    for at, end, role, old, new in changes:
        require(at >= old_at, 'B member edits overlap')
        gap = source[old_at:at]
        gaps.append({'old_start': old_at, 'new_start': new_at, **pin(gap)})
        parts.extend((gap, new))
        new_at += len(gap)
        edits.append({'role': role, 'old_start': at, 'new_start': new_at,
                      'old': old.decode('ascii'), 'new': new.decode('ascii')})
        old_at, new_at = end, new_at + len(new)
    parts.append(source[old_at:])
    gaps.append({'old_start': old_at, 'new_start': new_at, **pin(source[old_at:])})
    candidate = b''.join(parts)
    require((len(candidate), pin(candidate)['sha256']) == OUTPUT,
            'B member output differs from the measured combined spelling')
    proof = {'kind': 'tcec-B-fields-v1', 'input': pin(source), 'output': pin(candidate),
             'mapping': mapping, 'references': references, 'edits': edits,
             'protected_gaps': gaps, 'full_inverse': True, 'macro_collisions': [],
             'field_order_types_dimensions_and_storage_unchanged': True,
             'ordinary_identifiers_literals_and_function_bodies_except_member_names_unchanged': True,
             'reference_evidence': REFERENCE.copy()}
    require(restore_source(candidate, proof) == source, 'B member full inverse differs')
    for gap in gaps:
        a, b, n = gap['old_start'], gap['new_start'], gap['bytes']
        require(source[a:a + n] == candidate[b:b + n], 'B member protected gap differs')
    return candidate, proof
