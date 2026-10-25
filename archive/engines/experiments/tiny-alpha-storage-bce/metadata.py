"""Check the explicitly pinned B metadata representation; never normalize an ELF.

The original full-file identity failure remains a failure.  This separate gate
accounts for every byte of two supplied, distinct ELF64 images and permits only
the literal layout, GNU build-ID descriptor, and object-name changes in policy.
It does not execute either image or establish semantic or ABI equivalence.
"""
from collections import Counter
import hashlib
import struct


HEADER_KEYS = ('type', 'machine', 'version', 'entry', 'phoff', 'shoff', 'flags',
               'ehsize', 'phentsize', 'phnum', 'shentsize', 'shnum', 'shstrndx')
SECTION_KEYS = ('name_offset', 'type', 'flags', 'address', 'offset', 'size',
                'link', 'info', 'alignment', 'entry_size')
PROGRAM_KEYS = ('type', 'flags', 'offset', 'vaddr', 'paddr', 'filesz', 'memsz',
                'alignment')
NOTE = '.note.gnu.build-id'


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _integer(value):
    return type(value) is int and value >= 0


def _hex(value, length, label):
    _require(isinstance(value, str) and len(value) == length * 2 and
             all(c in '0123456789abcdef' for c in value), label)
    return bytes.fromhex(value)


def _policy(policy):
    _require(isinstance(policy, dict) and set(policy) == {
        'control', 'candidate', 'allowed_layout', 'build_id',
        'symbol_name_pairs', 'symbol_count'}, 'policy keys')
    for side in ('control', 'candidate'):
        item = policy[side]
        _require(isinstance(item, dict) and set(item) == {'bytes', 'sha256'} and
                 _integer(item['bytes']) and item['bytes'] >= 64, 'file pin')
        _hex(item['sha256'], 32, 'file SHA-256 pin')
    _require(policy['control']['sha256'] != policy['candidate']['sha256'],
             'distinct full-file identities required')
    layout = policy['allowed_layout']
    _require(isinstance(layout, dict) and set(layout) == {
        'e_shoff', 'strtab_size', 'shstrtab_offset', 'tail_padding'}, 'layout keys')
    for key in ('e_shoff', 'strtab_size', 'shstrtab_offset'):
        _require(isinstance(layout[key], list) and len(layout[key]) == 2 and
                 all(_integer(v) for v in layout[key]), 'literal layout pair')
    _require(isinstance(layout['tail_padding'], dict) and
             set(layout['tail_padding']) == {'control', 'candidate'}, 'padding sides')
    for side in ('control', 'candidate'):
        item = layout['tail_padding'][side]
        _require(isinstance(item, dict) and set(item) == {'offset', 'hex'} and
                 _integer(item['offset']) and isinstance(item['hex'], str) and
                 len(item['hex']) % 2 == 0, 'padding pin')
        padding = _hex(item['hex'], len(item['hex']) // 2, 'padding hex')
        _require(not any(padding), 'only literal zero alignment padding allowed')
    _require(isinstance(policy['build_id'], dict) and
             set(policy['build_id']) == {'control', 'candidate'}, 'build-ID sides')
    for value in policy['build_id'].values():
        _hex(value, 20, '20-byte GNU build-ID descriptor')
    _require(policy['build_id']['control'] != policy['build_id']['candidate'],
             'distinct literal build-IDs required')
    pairs = policy['symbol_name_pairs']
    _require(isinstance(pairs, dict) and len(pairs) == 19,
             '19 literal symbol pairs required')
    for old, new in pairs.items():
        _require(isinstance(old, str) and isinstance(new, str) and old and new and
                 old != new and '\0' not in old + new and
                 old.isascii() and new.isascii(), 'ASCII symbol pair')
    _require(len(set(pairs.values())) == 19, 'injective literal symbol pairs required')
    _require(not (set(pairs) & set(pairs.values())), 'symbol domains must be disjoint')
    _require(type(policy['symbol_count']) is int and policy['symbol_count'] > 19,
             'symbol count pin')


def _take(data, offset, size, label):
    _require(_integer(offset) and _integer(size) and offset <= len(data) and
             size <= len(data) - offset, 'out-of-bounds ' + label)
    return data[offset:offset + size]


def _string(data, offset, label):
    _require(_integer(offset) and offset < len(data), 'string offset: ' + label)
    end = data.find(b'\0', offset)
    _require(end >= 0, 'unterminated string: ' + label)
    try:
        return data[offset:end].decode('ascii')
    except UnicodeDecodeError as error:
        raise ValueError('non-ASCII string: ' + label) from error


def _parse(data):
    _require(type(data) is bytes and len(data) >= 64, 'immutable ELF bytes required')
    _require(data[:7] == b'\x7fELF\x02\x01\x01', 'ELF64 little-endian version 1 required')
    header = dict(zip(HEADER_KEYS, struct.unpack_from('<HHIQQQIHHHHHH', data, 16)))
    _require(header['type'] in (2, 3) and header['machine'] == 62 and
             header['version'] == 1 and header['ehsize'] == 64 and
             header['phentsize'] == 56 and header['shentsize'] == 64 and
             0 < header['phnum'] < 0xffff and 0 < header['shnum'] < 0xff00 and
             0 < header['shstrndx'] < header['shnum'], 'unsupported ELF header domain')
    ph = _take(data, header['phoff'], 56 * header['phnum'], 'program headers')
    programs = []
    for offset in range(0, len(ph), 56):
        program = dict(zip(PROGRAM_KEYS, struct.unpack_from('<IIQQQQQQ', ph, offset)))
        _take(data, program['offset'], program['filesz'], 'program file span')
        if program['type'] == 1:
            _require(program['filesz'] <= program['memsz'], 'PT_LOAD file/memory size')
        programs.append(program)
    sh = _take(data, header['shoff'], 64 * header['shnum'], 'section headers')
    sections = [dict(zip(SECTION_KEYS, struct.unpack_from('<IIQQQQIIQQ', sh, i * 64)))
                for i in range(header['shnum'])]
    _require(not any(sections[0].values()), 'section zero must be null')
    names = sections[header['shstrndx']]
    _require(names['type'] == 3, 'section name string table type')
    names = _take(data, names['offset'], names['size'], 'section name strings')
    _require(names[:1] == b'\0' and names[-1:] == b'\0', 'section name string bounds')
    by_name = {}
    for index, section in enumerate(sections):
        section['name'] = _string(names, section['name_offset'], 'section name')
        section['index'] = index
        section['payload'] = b'' if section['type'] == 8 else _take(
            data, section['offset'], section['size'], 'section ' + section['name'])
        _require(section['name'] not in by_name, 'duplicate section name')
        by_name[section['name']] = section
    _require(sections[header['shstrndx']]['name'] == '.shstrtab', 'named shstrtab')
    for name in (NOTE, '.symtab', '.strtab', '.shstrtab'):
        _require(name in by_name, 'required section ' + name)
    sym, strings = by_name['.symtab'], by_name['.strtab']
    _require(sym['type'] == 2 and sym['flags'] == 0 and sym['entry_size'] == 24 and
             sym['link'] == strings['index'] and strings['type'] == 3 and
             strings['flags'] == 0 and by_name['.shstrtab']['flags'] == 0,
             'nonallocated symbol/string table domain')
    _require(not any(s['link'] == sym['index'] for s in sections),
             'symbol-index consumer outside supported reorder domain')
    return {'bytes': data, 'header': header, 'program_raw': ph, 'programs': programs,
            'section_raw': sh, 'sections': sections, 'by_name': by_name}


def _symbols(image, count):
    section = image['by_name']['.symtab']
    table = image['by_name']['.strtab']['payload']
    _require(table[:1] == b'\0' and table[-1:] == b'\0', 'symbol string table bounds')
    _require(len(section['payload']) == 24 * count and
             0 < section['info'] <= count, 'symbol count/local boundary')
    _require(section['payload'][:24] == b'\0' * 24, 'raw null symbol must be all zero')
    records, offsets = [], set()
    for index in range(count):
        name, info, other, shndx, value, size = struct.unpack_from(
            '<IBBHQQ', section['payload'], index * 24)
        _require(shndx != 0xffff and
                 (shndx < len(image['sections']) or shndx >= 0xff00), 'symbol section index')
        _require((info >> 4 == 0) == (index < section['info']), 'symbol local/global boundary')
        offsets.add(name)
        records.append((_string(table, name, 'symbol'), info, other, shndx, value, size))
    _require(records[0] == ('', 0, 0, 0, 0, 0), 'null symbol')
    stored, offset = [], 0
    while offset < len(table):
        text = _string(table, offset, 'stored symbol string')
        _require(offset in offsets, 'unreferenced symbol string bytes')
        stored.append(text)
        offset += len(text) + 1
    return records, stored


def _gaps(image):
    header = image['header']
    blocks = [('ELF header', 0, 64),
              ('program headers', header['phoff'], len(image['program_raw'])),
              ('section headers', header['shoff'], len(image['section_raw']))]
    blocks.extend(('section ' + s['name'], s['offset'], len(s['payload']))
                  for s in image['sections'] if s['payload'])
    blocks.sort(key=lambda x: (x[1], x[0]))
    gaps, end, previous = [], 0, 'file start'
    for name, offset, size in blocks:
        _require(offset >= end, 'overlapping file regions')
        gaps.append({'between': (previous, name), 'offset': end,
                     'payload': image['bytes'][end:offset]})
        end, previous = offset + size, name
    _require(end <= len(image['bytes']), 'file region end')
    gaps.append({'between': (previous, 'file end'), 'offset': end,
                 'payload': image['bytes'][end:]})
    return gaps


def qualify(control, candidate, literalpolicy):
    """Return a descriptive fixed-profile receipt, or raise ValueError.

    Full hashes are mandatory. Tests may repin mutated fixture bytes to show that
    the structural and whole-file accounting checks reject independently of SHA.
    Neither a successful receipt nor its symbol multiset creates a new native
    identity or changes the original full-file identity failure.
    """
    _policy(literalpolicy)
    for side, data in (('control', control), ('candidate', candidate)):
        pin = literalpolicy[side]
        _require(type(data) is bytes and len(data) == pin['bytes'] and
                 _sha(data) == pin['sha256'], side + ' full-file pin')
    _require(control != candidate, 'original full-file mismatch must remain')
    old, new = _parse(control), _parse(candidate)
    layout = literalpolicy['allowed_layout']
    _require([old['header']['shoff'], new['header']['shoff']] == layout['e_shoff'],
             'literal section-header offset pair')
    _require(control[:40] + control[48:64] == candidate[:40] + candidate[48:64],
             'ELF header change beyond e_shoff')
    _require(old['program_raw'] == new['program_raw'], 'program header bytes differ')
    _require([s['name'] for s in old['sections']] == [s['name'] for s in new['sections']],
             'section names/order differ')
    exceptions = {'.strtab': {'size'}, '.shstrtab': {'offset'}}
    for a, b in zip(old['sections'], new['sections']):
        for key in SECTION_KEYS:
            if key not in exceptions.get(a['name'], set()):
                _require(a[key] == b[key], 'section header ' + a['name'] + ':' + key)
        if a['name'] not in (NOTE, '.symtab', '.strtab'):
            _require(a['payload'] == b['payload'], 'section payload ' + a['name'])
    _require([old['by_name']['.strtab']['size'], new['by_name']['.strtab']['size']] ==
             layout['strtab_size'], 'literal strtab size pair')
    _require([old['by_name']['.shstrtab']['offset'], new['by_name']['.shstrtab']['offset']] ==
             layout['shstrtab_offset'], 'literal shstrtab offset pair')
    for side, image in (('control', old), ('candidate', new)):
        note = image['by_name'][NOTE]
        _require(note['type'] == 7 and note['flags'] == 2 and note['size'] == 36 and
                 note['payload'][:16] == struct.pack('<III', 4, 20, 3) + b'GNU\0',
                 'exact GNU type-3 build-ID note header/name')
        _require(note['payload'][16:] == bytes.fromhex(literalpolicy['build_id'][side]),
                 'literal build-ID descriptor')
    pairs = literalpolicy['symbol_name_pairs']
    a, stored_a = _symbols(old, literalpolicy['symbol_count'])
    b, stored_b = _symbols(new, literalpolicy['symbol_count'])
    old_names = Counter(row[0] for row in a)
    _require(all(old_names[name] == 1 for name in pairs), 'one occurrence per renamed object')
    _require(not (set(pairs.values()) & set(old_names)), 'fresh symbol aliases')
    _require(all(row[1] & 15 == 1 for row in a if row[0] in pairs), 'renamed symbols are objects')
    renamed = [(pairs.get(row[0], row[0]),) + row[1:] for row in a]
    local = old['by_name']['.symtab']['info']
    _require(renamed[:local] == b[:local], 'local symbol record order/metadata')
    _require(Counter(renamed[local:]) == Counter(b[local:]),
             'global symbol record multiset')
    _require(Counter(pairs.get(name, name) for name in stored_a) == Counter(stored_b),
             'complete stored string multiset')
    ga, gb = _gaps(old), _gaps(new)
    _require([g['between'] for g in ga] == [g['between'] for g in gb], 'file region order')
    gap_report, tail_count = [], 0
    for a_gap, b_gap in zip(ga, gb):
        tail = a_gap['between'] == ('section .shstrtab', 'section headers')
        if tail:
            tail_count += 1
            for side, gap in (('control', a_gap), ('candidate', b_gap)):
                pin = layout['tail_padding'][side]
                _require(gap['offset'] == pin['offset'] and
                         gap['payload'] == bytes.fromhex(pin['hex']), 'literal tail padding')
        else:
            _require(a_gap['payload'] == b_gap['payload'], 'unclaimed file bytes differ')
        gap_report.append({'between': list(a_gap['between']),
                           'control': {'offset': a_gap['offset'], 'bytes': len(a_gap['payload']),
                                       'sha256': _sha(a_gap['payload'])},
                           'candidate': {'offset': b_gap['offset'], 'bytes': len(b_gap['payload']),
                                         'sha256': _sha(b_gap['payload'])},
                           'literal_tail_exception': tail})
    _require(tail_count == 1, 'exactly one literal tail alignment region')
    allocated = [s for s in old['sections'] if s['flags'] & 2]
    return {
        'metadata_representation_accepted': True,
        'original_full_native_identity_failure_preserved': True,
        'full_native_equal': False, 'semantic_or_ABI_qualification': False,
        'strip_or_byte_normalization': False, 'all_file_bytes_accounted': True,
        'control': {'bytes': len(control), 'sha256': _sha(control)},
        'candidate': {'bytes': len(candidate), 'sha256': _sha(candidate)},
        'ELF_header_only_e_shoff_differs': True,
        'program_headers_raw_exact': True, 'program_header_count': len(old['programs']),
        'PT_LOAD_placements': [p for p in old['programs'] if p['type'] == 1],
        'section_count': len(old['sections']), 'allocated_section_count': len(allocated),
        'all_allocated_section_headers_exact': True,
        'allocated_payload_exception': {'section': NOTE, 'offset': old['by_name'][NOTE]['offset'],
                                        'bytes': 36, 'descriptor_offset_in_note': 16,
                                        'descriptor_bytes': 20,
                                        'control': literalpolicy['build_id']['control'],
                                        'candidate': literalpolicy['build_id']['candidate']},
        'other_allocated_section_payloads_exact': len(allocated) - 1,
        'symbol_count': len(renamed), 'renamed_object_symbol_count': len(pairs),
        'local_symbol_order_and_metadata_preserved': True,
        'global_symbol_multiset_preserved_under_literal_pairs': True,
        'complete_string_table_multiset_preserved_under_literal_pairs': True,
        'all_gaps_checked': gap_report,
    }
