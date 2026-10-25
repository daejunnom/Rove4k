"""Pure-byte boundary tests. Supply the two frozen images and literal policy.

Example: python3 test_metadata.py --old /absolute/control-B/native/x \
  --new /absolute/candidate-B/native/x --policy /absolute/metadata_recipe.json \
  --out /absolute/new-external-evidence

No ELF is executed. Mutation cases update only the candidate full-file pin, so
they test structural boundaries rather than merely tripping the SHA-256 gate.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import unittest

_spec = importlib.util.spec_from_file_location(
    'bce_metadata_fixture_target', Path(__file__).resolve().parent / 'metadata.py')
metadata = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(metadata)


FIXTURE = None


def sha(data):
    return hashlib.sha256(data).hexdigest()


def sections(data):
    """Small independent fixture locator, not the qualification implementation."""
    start = struct.unpack_from('<Q', data, 40)[0]
    count, strings = struct.unpack_from('<HH', data, 60)
    entries = [struct.unpack_from('<IIQQQQIIQQ', data, start + index * 64)
               for index in range(count)]
    s = entries[strings]
    names = data[s[4]:s[4] + s[5]]
    return {names[e[0]:names.index(0, e[0])].decode('ascii'):
            {'index': index, 'header': start + index * 64, 'offset': e[4],
             'size': e[5], 'type': e[1], 'info': e[7], 'link': e[6]}
            for index, e in enumerate(entries)}


class MetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if FIXTURE is None:
            raise unittest.SkipTest('explicit frozen byte fixtures required')
        cls.old, cls.new, cls.policy = FIXTURE
        cls.sec = sections(cls.new)
        cls.symbol = cls.sec['.symtab']['offset']
        cls.local = cls.sec['.symtab']['info']

    def mutated(self, offset, value=None, width=1, data=None):
        changed = bytearray(self.new)
        if data is not None:
            changed[offset:offset + len(data)] = data
        elif width == 1:
            changed[offset] = changed[offset] ^ 1 if value is None else value
        else:
            changed[offset:offset + width] = value.to_bytes(width, 'little')
        return bytes(changed)

    def repin(self, data):
        policy = copy.deepcopy(self.policy)
        policy['candidate'] = {'bytes': len(data), 'sha256': sha(data)}
        return policy

    def rejects(self, data, policy=None):
        with self.assertRaises(ValueError):
            metadata.qualify(self.old, data, self.repin(data) if policy is None else policy)

    def symbol_mutation(self, field_offset, width, value=None):
        entry = self.local
        return self.mutated(self.symbol + entry * 24 + field_offset, value, width)

    def test_measured_pair_accepted_as_distinct_representation(self):
        result = metadata.qualify(self.old, self.new, self.policy)
        self.assertTrue(result['metadata_representation_accepted'])
        self.assertTrue(result['original_full_native_identity_failure_preserved'])
        self.assertFalse(result['full_native_equal'])
        self.assertFalse(result['semantic_or_ABI_qualification'])
        self.assertFalse(result['strip_or_byte_normalization'])
        self.assertTrue(result['all_file_bytes_accounted'])
        self.assertEqual(result['symbol_count'], self.policy['symbol_count'])
        self.assertEqual(result['renamed_object_symbol_count'], 19)
        self.assertEqual(sum(g['literal_tail_exception'] for g in result['all_gaps_checked']), 1)
        self.assertEqual(result['allocated_payload_exception']['descriptor_bytes'], 20)

    def test_literal_hash_gate(self):
        self.rejects(self.mutated(self.sec['.text']['offset']), copy.deepcopy(self.policy))

    def test_policy_must_keep_distinct_full_identities(self):
        policy = copy.deepcopy(self.policy)
        policy['candidate'] = copy.deepcopy(policy['control'])
        self.rejects(self.old, policy)

    def test_alias_map_must_be_injective(self):
        policy = copy.deepcopy(self.policy)
        names = list(policy['symbol_name_pairs'])
        policy['symbol_name_pairs'][names[1]] = policy['symbol_name_pairs'][names[0]]
        self.rejects(self.new, policy)

    def test_extra_policy_permission_rejected(self):
        policy = copy.deepcopy(self.policy)
        policy['allow_other_changes'] = True
        self.rejects(self.new, policy)

    def test_ELF_identification(self):
        self.rejects(self.mutated(4, 1))

    def test_ELF_ident_padding(self):
        self.rejects(self.mutated(9))

    def test_ELF_header_other_field(self):
        self.rejects(self.mutated(48))

    def test_section_table_out_of_bounds(self):
        self.rejects(self.mutated(40, len(self.new) + 1, 8))

    def test_program_header_raw_change(self):
        phoff = struct.unpack_from('<Q', self.new, 32)[0]
        self.rejects(self.mutated(phoff + 4))

    def test_program_file_span_out_of_bounds(self):
        phoff = struct.unpack_from('<Q', self.new, 32)[0]
        self.rejects(self.mutated(phoff + 32, len(self.new) + 1, 8))

    def test_section_flags(self):
        self.rejects(self.mutated(self.sec['.text']['header'] + 8))

    def test_bss_memory_size(self):
        self.rejects(self.mutated(self.sec['.bss']['header'] + 32))

    def test_string_section_size_outside_literal_pair(self):
        self.rejects(self.mutated(self.sec['.strtab']['header'] + 32))

    def test_section_name_table_offset_outside_literal_pair(self):
        self.rejects(self.mutated(self.sec['.shstrtab']['header'] + 24))

    def test_section_name_payload(self):
        self.rejects(self.mutated(self.sec['.shstrtab']['offset'] + 1))

    def test_allocated_text_payload(self):
        self.rejects(self.mutated(self.sec['.text']['offset']))

    def test_nonallocated_unchanged_comment_payload(self):
        self.rejects(self.mutated(self.sec['.comment']['offset']))

    def test_note_namesz(self):
        self.rejects(self.mutated(self.sec[metadata.NOTE]['offset']))

    def test_note_descsz(self):
        self.rejects(self.mutated(self.sec[metadata.NOTE]['offset'] + 4))

    def test_note_type(self):
        self.rejects(self.mutated(self.sec[metadata.NOTE]['offset'] + 8))

    def test_note_GNU_name(self):
        self.rejects(self.mutated(self.sec[metadata.NOTE]['offset'] + 12))

    def test_note_descriptor_outside_literal_pin(self):
        self.rejects(self.mutated(self.sec[metadata.NOTE]['offset'] + 16))

    def test_symbol_name_out_of_bounds(self):
        self.rejects(self.symbol_mutation(0, 4, self.sec['.strtab']['size']))

    def test_symbol_info_binding_or_type(self):
        self.rejects(self.symbol_mutation(4, 1))

    def test_symbol_other_reserved_upper_bit(self):
        offset = self.symbol + self.local * 24 + 5
        self.rejects(self.mutated(offset, self.new[offset] ^ 0x80))

    def test_symbol_value(self):
        offset = self.symbol + self.local * 24 + 8
        self.rejects(self.mutated(offset))

    def test_symbol_size(self):
        self.rejects(self.mutated(self.symbol + self.local * 24 + 16))

    def test_symbol_section_index(self):
        self.rejects(self.symbol_mutation(6, 2, 0xffff))

    def test_null_symbol_record(self):
        self.rejects(self.mutated(self.symbol + 8))

    def test_null_symbol_name_offset_must_be_zero(self):
        self.rejects(self.mutated(self.symbol, self.sec['.strtab']['size'] - 1, 4))

    def test_symbol_multiset_duplicate_occurrence(self):
        start = self.symbol + self.local * 24
        self.rejects(self.mutated(start, data=self.new[start + 24:start + 48]))

    def test_local_symbol_order_cannot_change(self):
        data = bytearray(self.new)
        start = self.symbol + 24
        data[start:start + 48] = self.new[start + 24:start + 48] + self.new[start:start + 24]
        self.rejects(bytes(data))

    def test_local_global_boundary_cannot_change(self):
        data = bytearray(self.new)
        a, b = self.symbol + 24, self.symbol + self.local * 24
        data[a:a + 24], data[b:b + 24] = self.new[b:b + 24], self.new[a:a + 24]
        self.rejects(bytes(data))

    def test_global_symbol_order_may_change(self):
        start = self.symbol + self.local * 24
        data = bytearray(self.new)
        data[start:start + 48] = self.new[start + 24:start + 48] + self.new[start:start + 24]
        data = bytes(data)
        self.assertTrue(metadata.qualify(self.old, data, self.repin(data))[
            'global_symbol_multiset_preserved_under_literal_pairs'])

    def test_symbol_index_consumer_not_supported(self):
        self.rejects(self.mutated(self.sec['.comment']['header'] + 40,
                                  self.sec['.symtab']['index'], 4))

    def test_symbol_string_changed(self):
        self.rejects(self.mutated(self.sec['.strtab']['offset'] + 1))

    def test_symbol_string_unterminated(self):
        end = self.sec['.strtab']['offset'] + self.sec['.strtab']['size'] - 1
        self.rejects(self.mutated(end, ord('x')))

    def test_suffix_string_references_remain_supported(self):
        s = self.sec['.strtab']
        strings = self.new[s['offset']:s['offset'] + s['size']]
        starts = {0}
        starts.update(i + 1 for i, value in enumerate(strings[:-1]) if value == 0)
        referenced = {struct.unpack_from('<I', self.new, self.symbol + i * 24)[0]
                      for i in range(self.policy['symbol_count'])}
        self.assertTrue(referenced - starts)
        metadata.qualify(self.old, self.new, self.policy)

    def test_tail_padding_cannot_change(self):
        pin = self.policy['allowed_layout']['tail_padding']['candidate']
        self.assertTrue(pin['hex'])
        self.rejects(self.mutated(pin['offset']))

    def test_tail_padding_policy_is_zero_only(self):
        policy = copy.deepcopy(self.policy)
        policy['allowed_layout']['tail_padding']['candidate']['hex'] = '01'
        self.rejects(self.new, policy)

    def test_other_file_gap_cannot_change(self):
        # Derive unclaimed spans independently from ELF ranges.
        phoff = struct.unpack_from('<Q', self.new, 32)[0]
        phnum = struct.unpack_from('<H', self.new, 56)[0]
        shoff = struct.unpack_from('<Q', self.new, 40)[0]
        shnum = struct.unpack_from('<H', self.new, 60)[0]
        spans = [(0, 64), (phoff, phoff + phnum * 56),
                 (shoff, shoff + shnum * 64)]
        spans += [(s['offset'], s['offset'] + s['size']) for s in self.sec.values()
                  if s['type'] != 8 and s['size']]
        spans.sort()
        tail = self.policy['allowed_layout']['tail_padding']['candidate']['offset']
        gaps = [left[1] for left, right in zip(spans, spans[1:])
                if left[1] < right[0] and left[1] != tail]
        self.assertTrue(gaps)
        self.rejects(self.mutated(gaps[0]))

    def test_trailing_unclaimed_byte_cannot_appear(self):
        self.rejects(self.new + b'\0')

    def test_truncated_section_headers(self):
        self.rejects(self.new[:-1])


class RecordedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.records.append({'test': test.id(), 'status': 'pass'})

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.records.append({'test': test.id(), 'status': 'failure'})

    def addError(self, test, err):
        super().addError(test, err)
        self.records.append({'test': test.id(), 'status': 'error'})


def main():
    global FIXTURE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--old', type=Path, required=True)
    parser.add_argument('--new', type=Path, required=True)
    parser.add_argument('--policy', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    _inputs = (args.old, args.new, args.policy)
    if not all(p.is_absolute() for p in (*_inputs, args.out)):
        parser.error('all paths must be absolute')
    repo = Path(__file__).resolve().parents[3]
    if args.out.resolve().is_relative_to(repo):
        parser.error('evidence must remain outside the checkout')
    frozen = [p.read_bytes() for p in _inputs]
    loaded = json.loads(frozen[2])
    FIXTURE = frozen[0], frozen[1], loaded.get('qualification', loaded)
    source_paths = [Path(__file__).resolve(), Path(metadata.__file__).resolve()]
    source_bytes = [p.read_bytes() for p in source_paths]
    args.out.mkdir(parents=True, exist_ok=False)
    receipt = {'complete': False, 'scope': 'pure ELF byte fixtures; no target execution',
               'inputs': {str(p): {'bytes': len(d), 'sha256': sha(d)}
                          for p, d in zip(_inputs, frozen)},
               'helpers': {str(p): {'bytes': len(d), 'sha256': sha(d)}
                           for p, d in zip(source_paths, source_bytes)},
               'engine_runs': 0, 'compiler_runs': 0, 'codec_runs': 0}
    (args.out / 'inputs').mkdir()
    for name, data in zip(('control.elf', 'candidate.elf', 'policy.json'), frozen):
        (args.out / 'inputs' / name).write_bytes(data)
    for path, data in zip(source_paths, source_bytes):
        (args.out / 'inputs' / path.name).write_bytes(data)
    result = unittest.TextTestRunner(verbosity=2, resultclass=RecordedResult).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(MetadataTests))
    receipt.update(complete=result.wasSuccessful(), tests_run=result.testsRun,
                   failures=len(result.failures), errors=len(result.errors),
                   skipped=len(result.skipped), cases=result.records)
    (args.out / 'results.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'complete': receipt['complete'], 'tests': result.testsRun,
                      'receipt': str(args.out / 'results.json')}))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
