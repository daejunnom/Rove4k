"""Separate descriptive C-only tiny_table suffix-packing boundary.

The caller must freeze its literal 17 compiler-symbol pairs before compilation
and bind the control image independently.  This module discovers no rename map,
accepts no artifact/report inputs, normalizes no ELF bytes, and executes nothing.
Different full-file identities and the allocated build-ID exception stay explicit.
The original observer's stored-entry Counter rejection remains unchanged there.
Here exactly one previously suffix-shared table name becomes a stored qq entry,
under fixed C witness records and complete actual symbol-consumer byte coverage.
"""
from collections import Counter
import hashlib
import struct


HEADER = ('type', 'machine', 'version', 'entry', 'phoff', 'shoff', 'flags',
          'ehsize', 'phentsize', 'phnum', 'shentsize', 'shnum', 'shstrndx')
SECTION = ('name_offset', 'type', 'flags', 'address', 'offset', 'size',
           'link', 'info', 'alignment', 'entry_size')
PROGRAM = ('type', 'flags', 'offset', 'vaddr', 'paddr', 'filesz', 'memsz', 'alignment')
NOTE = '.note.gnu.build-id'


def _check(condition, message):
    if not condition:
        raise ValueError(message)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _span(data, start, size, label):
    _check(type(start) is int and type(size) is int and start >= 0 and size >= 0 and
           start <= len(data) and size <= len(data) - start, 'out-of-bounds ' + label)
    return data[start:start + size]


def _string(data, offset, label):
    _check(type(offset) is int and 0 <= offset < len(data), 'string offset: ' + label)
    end = data.find(b'\0', offset)
    _check(end >= 0, 'unterminated string: ' + label)
    try:
        return data[offset:end].decode('ascii')
    except UnicodeDecodeError as error:
        raise ValueError('non-ASCII string: ' + label) from error


def _parse(data):
    _check(type(data) is bytes and len(data) >= 64, 'immutable ELF bytes required')
    _check(data[:7] == b'\x7fELF\x02\x01\x01', 'ELF64 little-endian version 1 required')
    header = dict(zip(HEADER, struct.unpack_from('<HHIQQQIHHHHHH', data, 16)))
    _check(header['type'] in (2, 3) and header['machine'] == 62 and
           header['version'] == 1 and header['ehsize'] == 64 and
           header['phentsize'] == 56 and header['shentsize'] == 64 and
           0 < header['phnum'] < 0xffff and 0 < header['shnum'] < 0xff00 and
           0 < header['shstrndx'] < header['shnum'], 'unsupported ELF header domain')
    ph = _span(data, header['phoff'], header['phnum'] * 56, 'program headers')
    programs = []
    for offset in range(0, len(ph), 56):
        item = dict(zip(PROGRAM, struct.unpack_from('<IIQQQQQQ', ph, offset)))
        _span(data, item['offset'], item['filesz'], 'program file range')
        if item['type'] == 1:
            _check(item['filesz'] <= item['memsz'], 'PT_LOAD file/memory size')
        programs.append(item)
    raw = _span(data, header['shoff'], header['shnum'] * 64, 'section headers')
    sections = [dict(zip(SECTION, struct.unpack_from('<IIQQQQIIQQ', raw, index * 64)))
                for index in range(header['shnum'])]
    _check(not any(sections[0].values()), 'raw null section header')
    name_section = sections[header['shstrndx']]
    _check(name_section['type'] == 3, 'section name table type')
    names = _span(data, name_section['offset'], name_section['size'], 'section name strings')
    _check(names[:1] == b'\0' and names[-1:] == b'\0', 'section name string bounds')
    named = {}
    for index, section in enumerate(sections):
        section['index'] = index
        section['name'] = _string(names, section['name_offset'], 'section name')
        _check(section['offset'] <= len(data), 'section file offset')
        section['payload'] = b'' if section['type'] == 8 else _span(
            data, section['offset'], section['size'], 'section ' + section['name'])
        _check(section['name'] not in named, 'duplicate section name')
        named[section['name']] = section
    _check(sections[header['shstrndx']]['name'] == '.shstrtab', 'named section string table')
    for name in (NOTE, '.symtab', '.strtab', '.shstrtab'):
        _check(name in named, 'required section ' + name)
    symbols, strings = named['.symtab'], named['.strtab']
    _check(symbols['type'] == 2 and symbols['flags'] == 0 and
           symbols['entry_size'] == 24 and symbols['link'] == strings['index'] and
           strings['type'] == 3 and strings['flags'] == 0 and
           named['.shstrtab']['flags'] == 0, 'nonallocated symbol/string table domain')
    _check(not any(s['link'] == symbols['index'] for s in sections),
           'symbol-index consumer outside reorder domain')
    _check(not any(s['link'] == strings['index'] and s['index'] != symbols['index']
                   for s in sections), 'other consumer of mutable symbol strings')
    return {'data': data, 'header': header, 'program_raw': ph, 'programs': programs,
            'section_raw': raw, 'sections': sections, 'named': named}


def _symbols(image):
    section, strings = image['named']['.symtab'], image['named']['.strtab']['payload']
    raw = section['payload']
    _check(len(raw) % 24 == 0 and len(raw) >= 24 and
           0 < section['info'] <= len(raw) // 24, 'symbol count/local boundary')
    _check(raw[:24] == b'\0' * 24, 'raw null symbol must be all zero')
    _check(strings[:1] == b'\0' and strings[-1:] == b'\0', 'symbol string bounds')
    records = []
    for index in range(len(raw) // 24):
        name, info, other, shndx, value, size = struct.unpack_from('<IBBHQQ', raw, index * 24)
        _check(shndx != 0xffff and
               (shndx < len(image['sections']) or shndx >= 0xff00), 'symbol section index')
        _check((info >> 4 == 0) == (index < section['info']), 'symbol local/global boundary')
        records.append((_string(strings, name, 'symbol'), info, other, shndx, value, size))
    # Full stored entries include unreferenced bytes; individual st_name references
    # may legally begin at suffixes rather than at these NUL-entry boundaries.
    stored, offset = [], 0
    while offset < len(strings):
        text = _string(strings, offset, 'stored symbol string')
        stored.append(text)
        offset += len(text) + 1
    return records, stored


def _gaps(image):
    h = image['header']
    blocks = [('ELF header', 0, 64),
              ('program headers', h['phoff'], len(image['program_raw'])),
              ('section headers', h['shoff'], len(image['section_raw']))]
    blocks += [('section ' + s['name'], s['offset'], len(s['payload']))
               for s in image['sections'] if s['payload']]
    blocks.sort(key=lambda item: (item[1], item[0]))
    end, previous, result = 0, 'file start', []
    for name, offset, size in blocks:
        _check(offset >= end, 'overlapping file regions')
        result.append({'between': (previous, name), 'offset': end,
                       'payload': image['data'][end:offset]})
        end, previous = offset + size, name
    _check(end <= len(image['data']), 'file region end')
    result.append({'between': (previous, 'file end'), 'offset': end,
                   'payload': image['data'][end:]})
    return result


def _geometry(image):
    strings, names, h = image['named']['.strtab'], image['named']['.shstrtab'], image['header']
    _check(names['offset'] == strings['offset'] + strings['size'],
           'strtab/shstrtab must be contiguous')
    end = names['offset'] + names['size']
    _check(h['shoff'] == (end + 7) // 8 * 8, 'section table must use exact 8-byte alignment')
    padding = _span(image['data'], end, h['shoff'] - end, 'tail alignment')
    _check(len(padding) <= 7 and not any(padding), 'tail alignment must be 0..7 zero bytes')
    _check(h['shoff'] + len(image['section_raw']) == len(image['data']),
           'section table must end at EOF')
    return {'e_shoff': h['shoff'], 'strtab_offset': strings['offset'],
            'strtab_size': strings['size'], 'shstrtab_offset': names['offset'],
            'shstrtab_size': names['size'],
            'tail_padding': {'offset': end, 'bytes': len(padding), 'hex': padding.hex()}}


def _pairs(symbol_pairs):
    _check(type(symbol_pairs) is dict and len(symbol_pairs) == 17,
           'exactly 17 predeclared symbol pairs required')
    for old, new in symbol_pairs.items():
        _check(type(old) is str and type(new) is str and old and new and
               old != new and old.isascii() and new.isascii() and '\0' not in old + new,
               'literal ASCII symbol pair')
    _check(len(set(symbol_pairs.values())) == 17 and
           not (set(symbol_pairs) & set(symbol_pairs.values())), 'injective disjoint symbol pairs')


def _suffix_consumers(image, records, witnesses):
    """Account for every stored string byte through actual symbol references."""
    strings = image['named']['.strtab']['payload']
    raw = image['named']['.symtab']['payload']
    _check(len(records) == 98 and image['named']['.symtab']['info'] == 42,
           'fixed C 98-symbol/42-local witness')
    entries, offset = [], 0
    while offset < len(strings):
        name = _string(strings, offset, 'suffix-class stored entry')
        entries.append({'offset': offset, 'nul_offset': offset + len(name),
                        'name': name, 'bytes_including_NUL_hex':
                        strings[offset:offset + len(name) + 1].hex()})
        offset += len(name) + 1
    coverage, consumers = [0] * len(strings), []
    for ordinal, row in enumerate(records):
        start = struct.unpack_from('<I', raw, ordinal * 24)[0]
        end = strings.find(b'\0', start)
        _check(0 <= start <= end < len(strings), 'bounded actual suffix consumer')
        _check(_string(strings, start, 'suffix consumer') == row[0], 'consumer decoded name')
        containing = [entry for entry in entries if entry['offset'] <= start <= entry['nul_offset']]
        _check(len(containing) == 1, 'unique containing stored string')
        entry = containing[0]
        for index in range(start, end + 1):
            coverage[index] += 1
        consumers.append({'symbol_ordinal': ordinal, 'st_name': start, 'decoded_name': row[0],
                          'st_info': row[1], 'st_other': row[2], 'st_shndx': row[3],
                          'st_value': row[4], 'st_size': row[5],
                          'consumer_byte_range': [start, end + 1], 'nul_offset': end,
                          'stored_entry_offset': entry['offset'], 'stored_entry_name': entry['name'],
                          'suffix_offset': start - entry['offset']})
    unowned = [index for index, count in enumerate(coverage) if not count]
    _check(not unowned, 'unowned mutable symbol-string bytes')
    for entry in entries:
        entry['consumer_ordinals'] = [c['symbol_ordinal'] for c in consumers
                                      if c['stored_entry_offset'] == entry['offset']]
        entry['byte_consumer_counts'] = coverage[entry['offset']:entry['nul_offset'] + 1]
    for ordinal, expected in witnesses.items():
        expected_row, expected_name_offset, expected_entry, expected_range = expected
        _check(records[ordinal] == expected_row, 'exact C suffix witness raw attributes')
        consumer = consumers[ordinal]
        _check(consumer['st_name'] == expected_name_offset and
               consumer['stored_entry_name'] == expected_entry and
               [consumer['stored_entry_offset'], consumer['nul_offset']] == expected_range,
               'exact C suffix witness offsets/stored entry')
    return {'symbol_count': len(records), 'local_count': 42, 'table_bytes': len(strings),
            'table_sha256': _sha(strings), 'stored_entries': entries,
            'actual_symbol_consumers': consumers, 'byte_consumer_counts': coverage,
            'coverage_counts_sha256': _sha(b''.join(struct.pack('<I', n) for n in coverage)),
            'covered_bytes': sum(n > 0 for n in coverage),
            'covered_byte_ranges': [[0, len(strings)]], 'unowned_byte_offsets': unowned,
            'all_table_bytes_owned_by_actual_symbol_consumers': True}


def _suffix_boundary(old, new, a, b, stored_a, stored_b, symbol_pairs):
    expected_pairs = {
        'back.0': 'qa.0', 'command': 'qb', 'deadline': 'qc', 'epoch': 'qd',
        'fallback': 'qe', 'finished': 'qf', 'game_keys': 'qg', 'game_length': 'qh',
        'material.1': 'qi.1', 'mutex': 'qj', 'pending': 'qk', 'position': 'ql',
        'quitting': 'qm', 'steps': 'qo', 'stopped': 'qp', 'table': 'qq', 'workers': 'qr'}
    _check(symbol_pairs == expected_pairs, 'literal C-only 17 symbol pairs')
    old_count, new_count = Counter(stored_a), Counter(stored_b)
    _check(old_count['table'] == 0 and old_count['qq'] == 0 and
           old_count['tiny_table'] == 1 and new_count['tiny_table'] == 1 and
           new_count['qq'] == 1, 'fixed standalone/suffix string occurrence witness')
    mapped = Counter(symbol_pairs.get(s, s) for s in stored_a)
    expected = mapped + Counter({'qq': 1})
    _check(expected == new_count, 'stored string multiset plus exactly one literal qq')
    control = _suffix_consumers(old, a, {
        19: (('tiny_table', 1, 0, 26, 195808, 3328), 125, 'tiny_table', [125, 135]),
        66: (('table', 17, 0, 26, 195584, 8), 130, 'tiny_table', [125, 135])})
    candidate = _suffix_consumers(new, b, {
        19: (('tiny_table', 1, 0, 26, 195808, 3328), 102, 'tiny_table', [102, 112]),
        67: (('qq', 17, 0, 26, 195584, 8), 818, 'qq', [818, 820])})
    return {'comparison_class': 'C-literal-tiny_table-suffix-materialized-qq-v1',
            'original_stored_string_counter_would_reject': True,
            'original_observer_rejection_unchanged': True,
            'extra_candidate_stored_entries': {'qq': 1},
            'candidate_minus_mapped_control': dict(new_count - mapped),
            'mapped_control_minus_candidate': dict(mapped - new_count),
            'complete_stored_counter_with_literal_extra_entry_preserved': True,
            'control': control, 'candidate': candidate}


def compare(control, candidate, *, symbol_pairs):
    """Describe one pair or reject a change outside the fixed metadata boundary.

    `symbol_pairs` is supplied literally by the caller, not inferred from these
    images. No candidate SHA, build-ID, or layout is known in advance; observations
    are returned without qualifying the new identity or altering the old failure.
    """
    _pairs(symbol_pairs)
    _check(type(control) is bytes and type(candidate) is bytes and control != candidate,
           'two immutable, distinct full-file images required')
    control_sha, candidate_sha = _sha(control), _sha(candidate)
    _check(control_sha != candidate_sha, 'distinct full-file SHA-256 identities required')
    old, new = _parse(control), _parse(candidate)
    _check(control[:40] + control[48:64] == candidate[:40] + candidate[48:64],
           'ELF header change beyond e_shoff')
    _check(old['program_raw'] == new['program_raw'], 'program header bytes differ')
    _check([s['name'] for s in old['sections']] == [s['name'] for s in new['sections']],
           'section names/order differ')
    header_exceptions = {'.strtab': {'size'}, '.shstrtab': {'offset'}}
    for a, b in zip(old['sections'], new['sections']):
        for field in SECTION:
            if field not in header_exceptions.get(a['name'], set()):
                _check(a[field] == b[field], 'section header ' + a['name'] + ':' + field)
        # Nonallocated .comment and any other sections are checked too, not
        # silently claimed and omitted from subsequent file-gap comparisons.
        if a['name'] not in (NOTE, '.symtab', '.strtab'):
            _check(a['payload'] == b['payload'], 'section payload ' + a['name'])
    layouts = {'control': _geometry(old), 'candidate': _geometry(new)}
    build_ids = {}
    for side, image in (('control', old), ('candidate', new)):
        note = image['named'][NOTE]
        _check(note['type'] == 7 and note['flags'] == 2 and note['size'] == 36 and
               note['payload'][:16] == struct.pack('<III', 4, 20, 3) + b'GNU\0',
               'exact 36-byte GNU type-3 build-ID note shape')
        build_ids[side] = note['payload'][16:].hex()
    a, stored_a = _symbols(old)
    b, stored_b = _symbols(new)
    names = Counter(row[0] for row in a)
    _check(all(names[name] == 1 for name in symbol_pairs),
           'unexpected baseline compiler symbol names/counts')
    _check(not (set(symbol_pairs.values()) & set(names)), 'fresh symbol aliases required')
    _check(all(row[1] & 15 == 1 for row in a if row[0] in symbol_pairs),
           'all explicitly renamed symbols must be objects')
    renamed = [(symbol_pairs.get(row[0], row[0]),) + row[1:] for row in a]
    local = old['named']['.symtab']['info']
    _check(renamed[:local] == b[:local], 'local symbol order/raw attributes')
    _check(Counter(renamed[local:]) == Counter(b[local:]), 'global symbol record multiset')
    suffix_evidence = _suffix_boundary(old, new, a, b, stored_a, stored_b, symbol_pairs)
    ga, gb = _gaps(old), _gaps(new)
    _check([g['between'] for g in ga] == [g['between'] for g in gb], 'file region order')
    gaps, tail_count = [], 0
    for x, y in zip(ga, gb):
        tail = x['between'] == ('section .shstrtab', 'section headers')
        if tail:
            tail_count += 1
            for side, gap in (('control', x), ('candidate', y)):
                expected = layouts[side]['tail_padding']
                _check(gap['offset'] == expected['offset'] and
                       gap['payload'].hex() == expected['hex'], 'tail alignment region')
        else:
            _check(x['payload'] == y['payload'], 'unclaimed file bytes differ')
        gaps.append({'between': list(x['between']), 'tail_alignment_region': tail,
                     'control': {'offset': x['offset'], 'bytes': len(x['payload']),
                                 'sha256': _sha(x['payload'])},
                     'candidate': {'offset': y['offset'], 'bytes': len(y['payload']),
                                   'sha256': _sha(y['payload'])}})
    _check(tail_count == 1, 'one bounded tail alignment region required')
    allocated = [s for s in old['sections'] if s['flags'] & 2]
    section_changes, section_inventory = [], []
    for x, y in zip(old['sections'], new['sections']):
        fields = {key: [x[key], y[key]] for key in SECTION if x[key] != y[key]}
        section_inventory.append({
            'index': x['index'], 'name': x['name'], 'payload_equal': x['payload'] == y['payload'],
            'control': {**{key: x[key] for key in SECTION},
                        'allocated': bool(x['flags'] & 2), 'NOBITS': x['type'] == 8,
                        'file_bytes': len(x['payload']), 'payload_sha256': _sha(x['payload'])},
            'candidate': {**{key: y[key] for key in SECTION},
                          'allocated': bool(y['flags'] & 2), 'NOBITS': y['type'] == 8,
                          'file_bytes': len(y['payload']), 'payload_sha256': _sha(y['payload'])}})
        if fields or x['payload'] != y['payload']:
            section_changes.append({'name': x['name'], 'allocated': bool(x['flags'] & 2),
                                    'header_fields': fields,
                                    'payload_equal': x['payload'] == y['payload'],
                                    'control_payload_sha256': _sha(x['payload']),
                                    'candidate_payload_sha256': _sha(y['payload'])})
    def symbol_record(row, ordinal, image):
        return {'ordinal': ordinal, 'name': row[0],
                'st_name': struct.unpack_from('<I', image['named']['.symtab']['payload'], ordinal * 24)[0],
                'st_info': row[1], 'st_other': row[2], 'st_shndx': row[3],
                'st_value': row[4], 'st_size': row[5], 'binding': row[1] >> 4,
                'type': row[1] & 15, 'visibility': row[2] & 3, 'multiplicity': 1}
    renamed_records = []
    for name, alias in symbol_pairs.items():
        oi, ni = next(i for i, row in enumerate(a) if row[0] == name), next(
            i for i, row in enumerate(b) if row[0] == alias)
        renamed_records.append({'control': symbol_record(a[oi], oi, old),
                                'candidate': symbol_record(b[ni], ni, new)})
    return {'descriptive_observation_only': True, 'boundary_checks_complete': True,
            'metadata_qualified': False, 'new_native_qualification': False,
            'semantic_or_ABI_qualification': False,
            'strip_or_byte_normalization': False, 'full_native_identity_equal': False,
            'full_sha256_equal': False, 'original_full_native_identity_failure_preserved': True,
            'control': {'bytes': len(control), 'sha256': control_sha},
            'candidate': {'bytes': len(candidate), 'sha256': candidate_sha},
            'first_difference': next((i for i, (x, y) in enumerate(zip(control, candidate))
                                      if x != y), min(len(control), len(candidate))),
            'caller_must_bind_control_identity_and_predeclared_pairs': True,
            'ELF_headers': {
                'control': {**old['header'], 'raw_bytes': 64, 'raw_hex': control[:64].hex(),
                            'sha256': _sha(control[:64])},
                'candidate': {**new['header'], 'raw_bytes': 64, 'raw_hex': candidate[:64].hex(),
                              'sha256': _sha(candidate[:64])},
                'field_changes': {key: [old['header'][key], new['header'][key]]
                                  for key in HEADER if old['header'][key] != new['header'][key]}},
            'program_headers_raw_exact': True, 'program_header_count': len(old['programs']),
            'program_headers': {
                'control': {'raw_bytes': len(old['program_raw']),
                            'raw_hex': old['program_raw'].hex(), 'sha256': _sha(old['program_raw'])},
                'candidate': {'raw_bytes': len(new['program_raw']),
                              'raw_hex': new['program_raw'].hex(), 'sha256': _sha(new['program_raw'])},
                'records': old['programs']},
            'PT_LOAD_placements': [p for p in old['programs'] if p['type'] == 1],
            'observed_layout': layouts, 'section_count': len(old['sections']),
            'section_inventory': section_inventory, 'section_changes': section_changes,
            'allocated_section_count': len(allocated),
            'all_allocated_section_headers_exact': True,
            'allocated_payload_exception': {'section': NOTE,
                                            'offset': old['named'][NOTE]['offset'],
                                            'note_bytes': 36, 'descriptor_offset_in_note': 16,
                                            'descriptor_bytes': 20, 'observed_build_ids': build_ids,
                                            'descriptor_equal': build_ids['control'] == build_ids['candidate']},
            'other_allocated_section_payloads_exact': len(allocated) - 1,
            'all_other_section_payloads_exact_except_symtab_strtab': True,
            'symbol_count': len(a), 'local_symbol_count': local,
            'predeclared_symbol_pairs': dict(symbol_pairs), 'renamed_object_count': len(symbol_pairs),
            'renamed_object_records': renamed_records,
            'full_raw_symbol_attributes_preserved': True,
            'local_order_and_global_multiset_preserved': True,
            'complete_stored_string_multiset_preserved': False,
            'literal_C_suffix_string_boundary': suffix_evidence,
            'all_file_bytes_accounted': True, 'all_gaps_checked': gaps}
