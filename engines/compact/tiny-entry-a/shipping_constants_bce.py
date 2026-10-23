"""Inline four fixed shipping object macros after the original BCE setter guard.

This pure literal splice is restricted to the three admitted source identities.
No compiler, codec, parser, file read or engine execution occurs here. Complete
CPP headers and entire native equality were checked separately by firstcost.
"""
import hashlib

_CONSTANTS = (('PLY', '128'), ('MOVES', '512'), ('HISTORY', '4096'), ('MATE', '30000'))
_PINS = {'B': (10062, 'dc385886847510bddb694d918fae885564bd313a12e77973f31eabff45589afc', 9981, 'b6b3404cf790b64776c0d703af878e17e0ff90222143500c5dc77fab503df5e9'), 'C': (9612, '932ccb25ae6472c70f1fcb9bb118fb61f702866e7e5dab29ed10a84eef661f6b', 9527, '38886cea518a700b7d6f209475dbd80055becce8e4599377a7de0966494f7796'), 'E': (9951, 'cb94c4c661bf00d37bfed7cd9bb0dfd61557fa6dbc5247c782298211ea9ecd4a', 9866, '51e1db47b52d2ec12f0573911a923e9fe400c809ac225270a7821137e72122b7')}
_USES = {'B': {'PLY': (584, 5007, 5244, 5267, 5419, 6781, 6895, 6918, 7114), 'MOVES': (3528, 4921, 4939, 7622), 'HISTORY': (576, 671, 8476, 8618), 'MATE': (4309, 4656, 4976, 5104, 5239, 5262, 5414, 6698, 6776, 6890, 6913, 7150, 7155)}, 'C': {'PLY': (603, 4773, 4910, 4933, 6143, 6257, 6280, 6486), 'MOVES': (2762, 4696, 4714, 7017), 'HISTORY': (595, 716, 7966, 8108), 'MATE': (4742, 4905, 4928, 6056, 6138, 6252, 6275, 6522, 6527)}, 'E': {'PLY': (575, 5040, 5177, 5200, 6381, 6495, 6518, 6724), 'MOVES': (2727, 4962, 4980, 7255), 'HISTORY': (567, 688, 8204, 8346), 'MATE': (5009, 5172, 5195, 6293, 6376, 6490, 6513, 6760, 6765)}}
_DEFINITIONS = {'B': {'PLY': 169, 'MOVES': 186, 'HISTORY': 204, 'MATE': 225}, 'C': {'PLY': 188, 'MOVES': 205, 'HISTORY': 223, 'MATE': 244}, 'E': {'PLY': 169, 'MOVES': 186, 'HISTORY': 204, 'MATE': 225}}

def _sha(data):
    return hashlib.sha256(data).hexdigest()

def _edits(family):
    rows = []
    for name, literal in _CONSTANTS:
        at = _DEFINITIONS[family][name]
        rows.append((at, ('#define '+name+' '+literal+'\n').encode(), b''))
        rows.extend((offset, name.encode(), literal.encode()) for offset in _USES[family][name])
    return sorted(rows)

METADATA = {
    family: {
        'family': family,
        'stage': 'late-shipping-four-int-object-macros',
        'input_bytes': values[0], 'input_sha256': values[1],
        'output_bytes': values[2], 'output_sha256': values[3],
        'raw_delta': values[2]-values[0],
        'constants': {name: literal for name, literal in _CONSTANTS},
        'owned_regions': len(_edits(family)),
        'protected_gaps': len(_edits(family))+1,
        'full_inverse': True,
        'scope': 'fixed unsuffixed int tokens in shipping2; earlier guards/canonical/DEV unchanged',
        'source_observation': 'macro-table and diagnostic source locations change',
        'external_reads_compiler_codec_engine': 0,
    } for family, values in _PINS.items()
}

def transform_source(source, *, family):
    if type(source) is not bytes or type(family) is not str or family not in _PINS:
        raise ValueError('fixed BCE bytes and explicit family required')
    before_size, before_sha, after_size, after_sha = _PINS[family]
    if len(source) != before_size or _sha(source) != before_sha:
        raise ValueError('four-int source differs from original setter output')
    parts, inverse_rows, gaps = [], [], []
    cursor = output_cursor = 0
    for at, old, new in _edits(family):
        if at < cursor or source[at:at+len(old)] != old:
            raise ValueError('fixed four-int token/definition span changed')
        gap = source[cursor:at]
        parts.extend((gap, new))
        output_cursor += len(gap)
        gaps.append((cursor, at, output_cursor-len(gap), output_cursor))
        inverse_rows.append((output_cursor, old, new))
        output_cursor += len(new)
        cursor = at+len(old)
    parts.append(source[cursor:])
    result = b''.join(parts)
    gaps.append((cursor, len(source), output_cursor, len(result)))
    for lo, hi, out_lo, out_hi in gaps:
        if source[lo:hi] != result[out_lo:out_hi]:
            raise ValueError('protected four-int gap changed')
    restored = result
    for at, old, new in reversed(inverse_rows):
        if restored[at:at+len(new)] != new:
            raise ValueError('fixed four-int inverse span changed')
        restored = restored[:at]+old+restored[at+len(new):]
    if restored != source or len(result) != after_size or _sha(result) != after_sha:
        raise ValueError('four-int full inverse or result identity failed')
    return result, dict(METADATA[family])
