"""Small synthetic-only tests; mocked admission is not real artifact admission."""
import hashlib
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import rove_actual_map as target
import rove_map_fixture as fixture


def digest(data):
    return hashlib.sha256(data).hexdigest()


def make_source(family, profile):
    typ, symbol = target.NAMES[family]
    count = 'qN' if family == 'B' else 'RVN'
    return (f'''#include <stdlib.h>
#include <stdint.h>
#define {count} ((size_t)1<<{target.BITS[profile]})
typedef struct {{uint64_t a,b,c;}} {typ};
{typ}*{symbol};
void use(size_t a){{{symbol}=aligned_alloc(4096,{count}*sizeof*{symbol});
{typ}*p={symbol}+(a&({count}-1));p->a=1;}}
int main(void){{return {symbol}!=0;}}
''').encode()


class ActualMapSyntheticTests(unittest.TestCase):
    def test_per_family_source_contract_and_rejections(self):
        for family, (_, symbol) in target.NAMES.items():
            for profile in target.BITS:
                source = make_source(family, profile)
                self.assertEqual(target.source_contract(source, family, profile)[1], symbol)
                with self.assertRaises(ValueError):
                    target.source_contract(source.replace(b'aligned_alloc', b'malloc'), family, profile)
                with self.assertRaises(ValueError):
                    target.source_contract(source + source, family, profile)
        with self.assertRaises(ValueError):
            target.source_contract(make_source('A', 'test-p16'), 'D', 'test-p16')

    def test_map_bounds_and_ambiguity(self):
        good = b' .bss 0x4018 0x10 /tmp/obj.o\n 0x4020 qq\n'
        self.assertEqual(target.map_candidate(good, 'qq'), 0x4020)
        for bad in (b'', good + b' 0x4020 qq\n', good.replace(b'.bss', b'.data'),
                    good.replace(b'0x4020 qq', b'0x4028 qq')):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                target.map_candidate(bad, 'qq')

    @unittest.skipUnless(shutil.which('cc'), 'C compiler unavailable')
    def test_same_link_replay_and_input_tamper(self):
        family, profile = 'A', 'test-p16'
        source = make_source(family, profile)
        command = list(target.COMMON)
        cc = shutil.which('cc')
        linker_name = subprocess.check_output([cc, '-print-prog-name=ld']).decode().strip()
        linker = shutil.which(linker_name)
        compiler_sha, linker_sha = digest(Path(cc).read_bytes()), digest(Path(linker).read_bytes())
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            subprocess.run(command, input=source, cwd=directory, check=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
            native = (directory / 'x').read_bytes()
            (directory / 'synthetic.c').write_bytes(source)
            (directory / 'synthetic.native').write_bytes(native)
            bits = target.BITS[profile]
            admitted = SimpleNamespace(family=family, profile_id=profile, source='synthetic.c',
                native='synthetic.native', expected={'source_bytes': len(source),
                    'source_sha256': digest(source), 'native_bytes': len(native), 'native_sha256': digest(native)},
                resources={'tt_bits': bits, 'tt_entries': 1 << bits, 'tt_entry_bytes': 24,
                           'tt_bytes': 24 << bits, 'tt_mask': (1 << bits) - 1})
            verifier = SimpleNamespace(admit_c_build=lambda *_: admitted)
            with patch.object(target, '_verify_module', return_value=verifier):
                report = target.inspect({'compile_executor': command}, directory, compiler_sha, linker_sha)
                self.assertTrue(report['same_link_map'])
                self.assertTrue(report['native_bytes_match'])
                self.assertFalse(report['engine_executed'])
                self.assertFalse(report['tt_semantics_proven'])
                self.assertFalse(report['runtime_address_observed'])
                self.assertFalse(report['smt_qualified'])
                self.assertFalse(report['go'])
                with self.assertRaises(ValueError):
                    target.inspect({'compile_executor': command + ['-DOTHER']}, directory, compiler_sha, linker_sha)
                with self.assertRaises(ValueError):
                    target.inspect({'compile_executor': command}, directory, '0' * 64, linker_sha)
                (directory / 'synthetic.c').write_bytes(source + b' ')
                with self.assertRaisesRegex(ValueError, 'source differs'):
                    target.inspect({'compile_executor': command}, directory, compiler_sha, linker_sha)
                (directory / 'synthetic.c').write_bytes(source)
                (directory / 'synthetic.native').write_bytes(native + b' ')
                with self.assertRaisesRegex(ValueError, 'native differs'):
                    target.inspect({'compile_executor': command}, directory, compiler_sha, linker_sha)
                # Even a matching altered pin must not make a different native
                # look like the output of the same map-producing link.
                admitted.expected['native_bytes'] = len(native) + 1
                admitted.expected['native_sha256'] = digest(native + b' ')
                with self.assertRaisesRegex(ValueError, 'same-link map native differs'):
                    target.inspect({'compile_executor': command}, directory, compiler_sha, linker_sha)
                (directory / 'synthetic.native').write_bytes(native)
                admitted.expected['native_bytes'] = len(native)
                admitted.expected['native_sha256'] = digest(native)
                real_run = target.subprocess.run
                def remove_map_symbol(cmd, **kwargs):
                    result = real_run(cmd, **kwargs)
                    if '-Wl,-Map=fixture.map' in cmd and result.returncode == 0:
                        Path(kwargs['cwd'], 'fixture.map').write_bytes(b'')
                    return result
                with patch.object(target.subprocess, 'run', side_effect=remove_map_symbol):
                    with self.assertRaisesRegex(ValueError, 'map candidate missing'):
                        target.inspect({'compile_executor': command}, directory, compiler_sha, linker_sha)

    @unittest.skipUnless(shutil.which('cc'), 'C compiler unavailable')
    def test_actual_map_elf_relocation_and_relr_rejected(self):
        saved = []
        real_run = fixture.subprocess.run
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
        with self.assertRaises(ValueError):
            target.elf_candidate(bytes(collision), report['elf_value'])
        relr = raw.copy()
        struct.pack_into('<I', relr, relocation + 4, 19)
        with self.assertRaises(ValueError):
            target.elf_candidate(bytes(relr), report['elf_value'])

    @unittest.skipUnless(shutil.which('cc'), 'C compiler unavailable')
    def test_copy_relocation_uses_full_symbol_size(self):
        source = b'#include <stdio.h>\nvoid *N; int main(void){return stdout==N;}\n'
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run(['cc', '-x', 'c', '-', '-o', 'x', '-Wl,-Map=fixture.map'],
                           input=source, cwd=directory, check=True, capture_output=True)
            raw = bytearray(Path(directory, 'x').read_bytes())
            address = target.map_candidate(Path(directory, 'fixture.map').read_bytes(), 'N')
            self.assertIn(target.elf_candidate(raw, address), ('PIE', 'EXEC'))
            elf = target.peer_runtime.Elf64(raw)
            copy = None
            for section in elf.sections:
                if section[1] != 4:
                    continue
                for offset in range(section[4], section[4] + section[5], 24):
                    dest, info = elf.unpack('QQ', offset)
                    if info & 0xffffffff == 5:
                        copy = (section, offset, dest, info >> 32)
                        break
            self.assertIsNotNone(copy, 'fixture must contain a COPY relocation')
            section, offset, dest, index = copy
            symtab = elf.sections[section[6]]
            symbol_offset = symtab[4] + index * 24
            # Forging a copy large enough to reach the candidate must be denied,
            # including when its start is before the eight-byte candidate slot.
            self.assertLess(dest, address)
            collision = raw.copy()
            struct.pack_into('<Q', collision, symbol_offset + 16, address - dest + 1)
            with self.assertRaisesRegex(ValueError, 'intersects relocation'):
                target.elf_candidate(bytes(collision), address)
            wrong_symbol = raw.copy()
            struct.pack_into('<Q', wrong_symbol, symbol_offset + 8, dest + 8)
            with self.assertRaisesRegex(ValueError, 'invalid copy relocation symbol'):
                target.elf_candidate(bytes(wrong_symbol), address)
            bad_index = raw.copy()
            struct.pack_into('<Q', bad_index, offset + 8, (1 << 32) * (symtab[5] // 24) + 5)
            with self.assertRaisesRegex(ValueError, 'invalid copy relocation symbol table'):
                target.elf_candidate(bytes(bad_index), address)

    @unittest.skipUnless(shutil.which('cc'), 'C compiler unavailable')
    def test_elf_kind_uses_real_pie_and_nonpie_fixture(self):
        real_run = fixture.subprocess.run
        for pie in (True, False):
            saved = []
            def capture(command, **kwargs):
                result = real_run(command, **kwargs)
                if '-Wl,-Map=fixture.map' in command and result.returncode == 0:
                    saved.append(Path(kwargs['cwd'], 'x').read_bytes())
                return result
            with self.subTest(pie=pie), patch.object(fixture.subprocess, 'run', side_effect=capture):
                report = fixture.inspect(pie=pie)
                self.assertEqual(target.elf_candidate(saved[0], report['elf_value']),
                                 'PIE' if pie else 'EXEC')


if __name__ == '__main__':
    unittest.main()
