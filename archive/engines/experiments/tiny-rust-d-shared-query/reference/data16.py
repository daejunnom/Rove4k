#!/usr/bin/env python3
"""One fixed Rust D own-ELF first cost; compile tools only, never run an ELF."""

if __name__ == "__main__":
    raise SystemExit("Rove4k Rust engine paths are retired; use C A-F")

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import time
import zlib

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
NATIVE = {
    'hq': {'bytes': 16824, 'sha256': '2c84c684d840ad7e7f0567b2b76d9c28693a00f6f95779675fb45ff84c06d3b3',
           'rx_filesz': 16091, 'load_sha256': 'f149808a56b02a1a57fee53ab6305b50bc386a28f8e53bd6de785bcae923e724'},
    'scalar': {'bytes': 16824, 'sha256': '0c364208165b79d95f146650ec8ae144f1e4cb6427197b80f37f0e97a90a4eb3',
               'rx_filesz': 15643, 'load_sha256': 'dac2b625877692cfb9036d8788b8466495a78250d80029487225705a788bf2c4'},
}
LAYOUT = {'image_base': 0x400000, 'image_size': 16400, 'image_pages': 0x5000,
          'final_rx_pages': 0x4000, 'entry': 0x4000f0, 'bss_base': 0x404000,
          'bss_pages': 0x1000, 'rw_filesz': 16, 'rw_memsz': 20,
          'actual_bss_base': 0x404010, 'actual_bss_size': 4,
          'guard_base': 0x3ff000, 'upper_guard': 0x405000,
          'reserve_size': 0x7000, 'loader_base': 0x10000000}
INPUTS = {
    'native/main.rs': '8b72a5561b85ae87177198f08257ddfeca0fe954c6ca20ac74756b39c199723c',
    'native/board.rs': 'f27472ea055b67e61cdd82a3d7747feced50c899bef72365ffdc940043dedef3',
    'native/search.rs': 'da2583806efea022b1b3b1337557b896a373a561f11d665b1ca747c29e3aed81',
    'native/runtime.rs': '802b497371a409744ad231cd8f621ea3d8b7cd931627e0396f3ec92ad1345b2d',
    'native/os.rs': '892cc62e2c126ebcbc171eb6f8059aacf92cf255d85341487e46effe2b94986e',
    'native/link.ld': '1e8f17bb2f06a6ddabf1f56d155bd7bdcd8c4406d140c22770bcfda96d459bbc',
    'native/build.py': '08f28ebdc45ad49c2a23f7eb8e28b086612ea9a33dbc39cb8ccbd66bfcf68e89',
    'packaging/loader/loader.c': '8a6a9cb93ae484400056852c5bc406be1cc15dc7b8df6b0a57e6d6330a2e4094',
    'packaging/loader/image.ld': '93934099212b944b20c2f7840ee87e4817311c4f87fddbb2b3f91db28776cf99',
    'packaging/loader/codec.py': '17165d1cb16eaba8916833741bfa229d196c3ad07ca391c14b94288a3cdc0866',
    'packaging/packer.py': 'bde43a9bb1a7ec21f93f21071461d79570cf9ae4af8a7733c33e294ecac5291b',
}
LOADER_FLAGS = ['-Oz', '-flto', '-nostdlib', '-static', '-no-pie', '-fno-pie',
                '-fno-pic', '-fno-builtin', '-fno-stack-protector',
                '-fno-asynchronous-unwind-tables', '-fno-unwind-tables', '-fno-ident',
                '-fcf-protection=none', '-ffunction-sections', '-fdata-sections',
                '-Wl,--gc-sections,--build-id=none,-s,-z,noexecstack']
DATA = bytes.fromhex('46014000000000008801400000000000')
CLASS = 'tiny-rust-d-sectionless-load-v1'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def admit(native, form, packer):
    """A new literal class; the snapshot's existing C admit is never called."""
    expected = NATIVE[form]
    require(len(native) == expected['bytes'] and sha(native) == expected['sha256'],
            'unknown original qualified Rust D native')
    parsed = packer.elf(native)
    expected_segments = [
        {'type': 1, 'flags': 5, 'offset': 0, 'vaddr': 0x400000, 'paddr': 0x400000,
         'filesz': expected['rx_filesz'], 'memsz': expected['rx_filesz'], 'align': 4096},
        {'type': 1, 'flags': 6, 'offset': 0x4000, 'vaddr': 0x404000, 'paddr': 0x404000,
         'filesz': 16, 'memsz': 20, 'align': 4096},
        {'type': 0x6474e551, 'flags': 6, 'offset': 0, 'vaddr': 0, 'paddr': 0,
         'filesz': 0, 'memsz': 0, 'align': 0},
    ]
    require(parsed['entry'] == 0x4000f0 and parsed['segments'] == expected_segments,
            'literal original Rust segment or entry mismatch')
    require(native[0x4000:0x4010] == DATA, 'initialized memcpy/memcmp data pointers differ')
    require(not any(native[expected['rx_filesz']:0x4000]), 'unexpected nonzero file gap')
    load = packer.strip_native(native)
    require(len(load) == 16400 and sha(load) == expected['load_sha256'],
            'sectionless Rust load span differs')
    transformed = packer.elf(load)
    require(transformed['entry'] == parsed['entry'] and transformed['segments'] == parsed['segments'],
            'section stripping changed entry or program headers')
    require(all(transformed[name] == 0 for name in
                ('section_offset', 'section_size', 'section_count', 'section_names')),
            'section metadata not removed')
    permitted = set(range(40, 48)) | set(range(58, 64))
    changed = [i for i, (old, new) in enumerate(zip(native, load)) if old != new]
    require(set(changed) <= permitted and all(load[i] == 0 for i in permitted),
            'unexpected retained PT_LOAD change')
    require(native[0xf0:0x4010] == load[0xf0:0x4010], 'text/rodata/gap/data changed')
    for segment in expected_segments[:2]:
        require(segment['offset'] + segment['filesz'] <= len(load), 'truncated PT_LOAD bytes')
        require(segment['vaddr'] - 0x400000 == segment['offset'], 'noncontiguous virtual/file bias')
    require(0x400000 + 0x5000 == 0x405000 and 0x3ff000 + 0x7000 == 0x406000,
            'guard reservation mismatch')
    # The decoded stream ends BEFORE OUTPUT/BSS. Its four initial zero bytes
    # and all RW page padding remain anonymous untouched bytes. This is a
    # source/static proof; actual initial memory needs the later checkpoint.
    require(len(load) == 0x404010 - 0x400000, 'decoded data overlaps BSS')
    require(0x404010 + 4 <= 0x405000 and 0x406000 < 0x10000000, 'layout overlap')
    return load, {
        'class': CLASS, 'original_native_bytes': len(native), 'original_native_sha256': sha(native),
        'sectionless_bytes': len(load), 'sectionless_sha256': sha(load),
        'entry': parsed['entry'], 'program_headers_unchanged': True,
        'PT_LOAD_bytes_equal_except_declared_ELF_section_metadata': True,
        'changed_retained_header_offsets': changed, 'text_rodata_file_gap_data_identical': True,
        'initialized_data_hex': DATA.hex(), 'data_sha256': sha(DATA),
        'required_zero_BSS': {'address': 0x404010, 'bytes': 4, 'symbol': 'os::OUTPUT'},
        'static_zero_tail_source_proof_only': True,
        'original_rx_sha256': sha(native[:expected['rx_filesz']]),
        'sectionless_rx_sha256': sha(load[:expected['rx_filesz']]),
        'final_rx_pages': 0x4000, 'decode_protection_pages': 0x5000,
        'final_rw_pages': 0x1000, 'old_C_class_used_or_broadened': False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--rustc', default='rustc')
    args = parser.parse_args()
    out = args.out.resolve()
    repo = HERE.parents[2]
    if (sys.platform != 'linux' or platform.machine().lower() not in ('x86_64', 'amd64') or
            not args.out.is_absolute() or out.exists() or out == repo or repo in out.parents):
        parser.error('new absolute external Linux x86-64 output required')
    rustc = shutil.which(args.rustc)
    if not rustc:
        parser.error('Rust compiler unavailable')
    out.mkdir()
    report = {'complete': False, 'scope': 'one fixed self-restoring Rust D first cost; no ELF execution',
              'class': CLASS, 'executed_ELFs': 0, 'runtime_qualified': False,
              'old_C_class_broadened': False, 'forms': [], 'source_inputs': {}, 'commands': []}
    fixed_environment = {'LC_ALL': 'C', 'TZ': 'UTC', 'SOURCE_DATE_EPOCH': '0'}
    environment = os.environ.copy()
    environment.update(fixed_environment)
    report['compiler_environment'] = fixed_environment
    deadline = time.monotonic() + 600
    active = None

    def save():
        (out/'first-cost.json').write_text(json.dumps(report, indent=2)+'\n')

    def stop(_signum, _frame):
        raise InterruptedError('parent signal')

    def run(command):
        nonlocal active
        require(time.monotonic() < deadline, 'aggregate build deadline')
        active = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True, start_new_session=True,
                                  env=environment)
        row = {'command': command, 'pid': active.pid, 'returncode': None}
        report['commands'].append(row)
        failed = True
        try:
            stdout, stderr = active.communicate(timeout=min(180, max(.1, deadline-time.monotonic())))
            row.update(returncode=active.returncode, stdout=stdout, stderr=stderr)
            require(active.returncode == 0, 'tool command failed: '+str(command))
            failed = False
            return row
        except BaseException as error:
            row['tool_error'] = {'type': type(error).__name__, 'message': str(error)}
            raise
        finally:
            try:
                if failed:
                    # The group may still contain compiler grandchildren even
                    # after its Python leader exited. Do not gate this signal
                    # on leader poll(): inherited pipes can outlive that leader.
                    row['cleanup'] = 'owned tool group kill attempted independent of leader status'
                    try:
                        os.killpg(active.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    stdout, stderr = active.communicate(timeout=5)
                    row.update(returncode=active.returncode, stdout=stdout, stderr=stderr)
            except BaseException as cleanup_error:
                row['cleanup_error'] = {'type': type(cleanup_error).__name__, 'message': str(cleanup_error)}
                raise
            finally:
                row['terminal'] = active.poll() is not None
                active = None
                save()

    previous = {sig: signal.signal(sig, stop) for sig in (signal.SIGTERM, signal.SIGINT)}
    save()
    try:
        recipe_bytes = (HERE/'recipe.json').read_bytes()
        recipe = json.loads(recipe_bytes)
        require(recipe['format'] == 1 and recipe['class'] == CLASS and
                recipe['profile'] == {'workers': 2, 'tt_bits': 18, 'ply': 128} and
                recipe['source_sha256'] == INPUTS and recipe['native_expected'] == NATIVE and
                recipe['layout'] == LAYOUT and recipe['loader_flags'] == LOADER_FLAGS and
                recipe['data_hex'] == DATA.hex() and not recipe['runtime_execution_authorized'],
                'literal experiment recipe differs')
        require(recipe['codec'] == {'bcj_version': 'e8-e9-whole-image-add-next-offset-le32-v1',
                                    'fixed_version': 'rfc1951-one-final-fixed-zero-padding-v1'},
                'fixed codec identity differs')
        frozen = out/'source'
        native_root = frozen/'engines/compact/tiny-rust-d'
        packaging_root = frozen/'packaging'
        for name, pin in INPUTS.items():
            raw = (HERE/name).read_bytes()
            require(sha(raw) == pin and b'\r' not in raw, 'source pin/LF differs: '+name)
            target = native_root/name.removeprefix('native/') if name.startswith('native/') else frozen/name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            report['source_inputs'][name] = {'sha256': sha(raw), 'bytes': len(raw)}
        for name in ('build.py', 'recipe.json', 'README.md', '.gitattributes'):
            raw = (HERE/name).read_bytes()
            target = out/'producer-source'/name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            report['source_inputs'][name] = {'sha256': sha(raw), 'bytes': len(raw)}
        packer = module('frozen_original_d_packer', packaging_root/'packer.py')
        codec = module('frozen_original_d_codec', packaging_root/'loader/codec.py')
        require(codec.BCJ_VERSION == recipe['codec']['bcj_version'] and
                codec.FIXED_VERSION == recipe['codec']['fixed_version'], 'actual codec versions differ')
        report['tools'] = {'cc': run(['cc', '--version'])['stdout'],
                           'ld': run(['ld', '--version'])['stdout'], 'python': sys.version,
                           'zlib_build': zlib.ZLIB_VERSION, 'zlib_runtime': zlib.ZLIB_RUNTIME_VERSION}
        report['layout'] = LAYOUT
        for form in ('hq', 'scalar'):
            native_out = out/(form+'-native')
            run([sys.executable, '-I', '-B', str(native_root/'build.py'), '--out', str(native_out),
                 '--rustc', rustc, '--workers', '2', '--tt-bits', '18', '--hq', form, '--reproduce'])
            native_report = json.loads((native_out/'build.json').read_text())
            require(native_report['reproduced'] and all(native_report['artifact_gates'].values()),
                    'original native static/reproduction gate failed')
            expected = NATIVE[form]
            require(native_report['complete_native_bytes'] == expected['bytes'] and
                    native_report['complete_native_sha256'] == expected['sha256'],
                    'original complete native identity differs')
            require(native_report['source_sha256'] == {name.removeprefix('native/'): pin
                    for name, pin in INPUTS.items() if name.startswith('native/')},
                    'native compiler snapshot differs')
            costs = []
            row = {'form': form, 'original_native_build': str(native_out/'build.json'),
                   'native_reproduced': True, 'attempts': costs}
            report['forms'].append(row)
            for index, attempt in enumerate(('first', 'repeat')):
                native = Path(native_report['builds'][index]['path']).read_bytes()
                load, proof = admit(native, form, packer)
                payload = codec.fixed_compress(codec.bcj(load))
                require(codec.bcj(codec.fixed_decompress(payload, len(load)), inverse=True) == load,
                        'strict fixed decode/inverse BCJ mismatch')
                target = out/(form+'-'+attempt)
                target.mkdir()
                (target/'load-span.bin').write_bytes(load)
                candidate = packer.compile_loader(target/'whole', packaging_root/'loader', payload,
                                                   LAYOUT, LOADER_FLAGS, run, sha)
                whole = Path(candidate['path']).read_bytes()
                candidate.update(payload_sha256=sha(payload), load_proof=proof,
                                 whole_program_headers=packer.elf(whole), ELF_executed=False)
                costs.append(candidate)
                save()
            require(Path(costs[0]['path']).read_bytes() == Path(costs[1]['path']).read_bytes(),
                    'independent complete own-ELF bytes differ')
            require(Path(out/(form+'-first')/'whole/payload.bin').read_bytes() ==
                    Path(out/(form+'-repeat')/'whole/payload.bin').read_bytes(),
                    'independent fixed payload bytes differ')
            row.update(whole_reproduced=True, complete_bytes=costs[0]['bytes'],
                       complete_sha256=costs[0]['sha256'], payload_bytes=costs[0]['payload_bytes'],
                       loader_and_headers_bytes=costs[0]['loader_and_headers_bytes'],
                       under_4096=costs[0]['bytes'] <= 4096)
            print(json.dumps({'form': form, 'native': expected['bytes'], 'load_span': 16400,
                              'payload': row['payload_bytes'], 'whole': row['complete_bytes'],
                              'sha256': row['complete_sha256'], 'executed_ELFs': 0}), flush=True)
        report['complete'] = True
        report['next_gate'] = 'root review; no runtime admission from first cost'
    except BaseException as error:
        report['error'] = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        save()
        for sig, handler in previous.items():
            signal.signal(sig, handler)


if __name__ == '__main__':
    main()
