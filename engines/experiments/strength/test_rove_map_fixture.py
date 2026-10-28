import unittest
import struct
from pathlib import Path
from unittest.mock import patch

import rove_map_fixture as fixture


class FixtureMapTest(unittest.TestCase):
    def test_stripped_pie_and_nonpie_link(self):
        for pie in (True, False):
            with self.subTest(pie=pie):
                report = fixture.inspect(pie=pie)
                self.assertEqual(report['type'], 'PIE' if pie else 'EXEC')
                self.assertTrue(report['same_link_native_map'])
                self.assertTrue(report['identical_to_no_map_link'])
                self.assertFalse(report['executed'])
                self.assertFalse(report['tt_semantics_proven'])
                self.assertFalse(report['runtime_address_observed'])

    def test_map_missing_ambiguous_and_wrong_section_rejected(self):
        good = b' .bss  0x4018  0x8 /tmp/f.o\n  0x4018 qq\n'
        self.assertEqual(fixture.map_candidate(good), 0x4018)
        for bad in (b'', good + b'  0x4020 qq\n',
                    good.replace(b'.bss', b'.data'),
                    good.replace(b'0x8 ', b'0x10 '),
                    good.replace(b'0x4018 qq', b'0x4020 qq')):
            with self.subTest(map=bad), self.assertRaises(ValueError):
                fixture.map_candidate(bad)

    def test_malformed_native_rejected(self):
        with self.assertRaises(ValueError):
            fixture.elf_candidate(b'not an ELF', 0x4018)

    def test_modified_same_link_native_is_rejected(self):
        real_run = fixture.subprocess.run
        def mutate(command, **kwargs):
            result = real_run(command, **kwargs)
            if '-Wl,-Map=fixture.map' in command and result.returncode == 0:
                output = Path(kwargs['cwd'], 'x')
                output.write_bytes(output.read_bytes() + b'changed')
            return result
        with patch.object(fixture.subprocess, 'run', side_effect=mutate):
            with self.assertRaisesRegex(ValueError, 'changed executable bytes'):
                fixture.inspect()

    def test_relocation_collision_and_relr_are_rejected(self):
        real_run = fixture.subprocess.run
        saved = []
        def capture(command, **kwargs):
            result = real_run(command, **kwargs)
            if '-Wl,-Map=fixture.map' in command and result.returncode == 0:
                saved.append(Path(kwargs['cwd'], 'x').read_bytes())
            return result
        with patch.object(fixture.subprocess, 'run', side_effect=capture):
            report = fixture.inspect()
        raw = bytearray(saved[0])
        shoff = struct.unpack_from('<Q', raw, 40)[0]
        shnum = struct.unpack_from('<H', raw, 60)[0]
        entries = [shoff + 64*i for i in range(shnum)]
        relocation = next(s for s in entries if struct.unpack_from('<I', raw, s + 4)[0] == 4
                          and struct.unpack_from('<Q', raw, s + 32)[0])
        offset = struct.unpack_from('<Q', raw, relocation + 24)[0]
        collision = raw.copy()
        struct.pack_into('<Q', collision, offset, report['elf_value'])
        with self.assertRaisesRegex(ValueError, 'candidate has a dynamic relocation'):
            fixture.elf_candidate(collision, report['elf_value'])
        relr = raw.copy()
        struct.pack_into('<I', relr, relocation + 4, 19)
        with self.assertRaisesRegex(ValueError, 'RELR relocations are unsupported'):
            fixture.elf_candidate(relr, report['elf_value'])


if __name__ == '__main__':
    unittest.main()
