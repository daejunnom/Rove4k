#!/usr/bin/env python3
"""One first-cost LZMA-alone transport for the exact maintained A5207 control.

No engine/compiler execution, codec/preset sweep, source change or installation.
The original XZ whole file must re-encode exactly. One legacy LZMA1-alone
payload uses the same 9-extreme/lc2/lp0/pb0 intent; its entire shell prefix and
13-byte format header count. Both generated files and both independent decoder
outputs must repeat exactly. Runtime qualification is deliberately separate.
"""
import argparse
import ast
import ctypes
import hashlib
import json
import lzma
from pathlib import Path
import re
import shutil
import subprocess
import sys

PINS = {
    'build.json': 'a280b4dcb9220b10dd2c7bba79c34fe996f965562669c4cc2010e14f2a5cc3e1',
    'main.c': '5e0e77321110371aec3a7a06f93290e7581f08f721fc9bb07fcef26c406429b7',
    'bootstrap.py': '11679fb20e24e7cb777cb49e4bee5a7ee7ea999278651fbba6d622320e751d44',
    'x': '085fcf6bd411a59111aaebbdc6bd59e2687a5c38de2ce28f0ad9643882633e36',
    'native/x': 'd39167146236aafde21b59439b853bd10561f04e9186c18b839c2f84f2e16e12',
}
INPUT_NAMES = {'engine.c', 'bootstrap.py.in', 'launcher.sh', 'recipe.json', 'build.py',
               'engines/scripts/specialize.py', 'engines/scripts/minify.py', 'engines/scripts/rename_c.py',
               'engines/compact/tiny-a/stitch.py', 'engines/compact/tiny-a/pack_stream.py'}
PRESET = 9 | lzma.PRESET_EXTREME
COMPILER = ['cc', '-Os', '-x', 'c', '-', '-o', 'x', '-s']


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def bootstrap_source(script):
    tree = ast.parse(script)
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and isinstance(n.func.value, ast.Name) and n.func.value.id == 'p' and n.func.attr == 'communicate']
    require(len(calls) == 1 and len(calls[0].args) == 1, 'unknown compiler-stdin restoration shape')
    node = calls[0].args[0]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'encode' and not node.args and not node.keywords:
        value = ast.literal_eval(node.func.value)
        require(isinstance(value, str), 'unknown source literal type')
        source = value.encode()
    else:
        source = ast.literal_eval(node)
        require(isinstance(source, bytes), 'unknown source literal type')
    compilers = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                 and isinstance(n.func.value, ast.Name) and n.func.value.id == 'subprocess' and n.func.attr == 'Popen']
    require(len(compilers) == 1 and compilers[0].args, 'unknown compiler spawn shape')
    command = compilers[0].args[0]
    require(isinstance(command, ast.Call) and isinstance(command.func, ast.Attribute) and command.func.attr == 'split'
            and not command.args and not command.keywords, 'unknown fixed compiler command representation')
    require(ast.literal_eval(command.func.value).split() == COMPILER, 'compiler argv changed')
    return source


def candidate_prefix(prefix):
    require(prefix.count(b'|xz -dc') == 1, 'unknown qualified decoder launcher')
    result = prefix.replace(b'|xz -dc', b'|lzma -dc')
    require(len(re.findall(rb'tail -c\+(\d+)', result)) == 1, 'unknown payload offset shape')
    # Fixed point for one payload address, not an encoding or flag search.
    for _ in range(4):
        previous = result
        result = re.sub(rb'tail -c\+\d+', lambda _: b'tail -c+' + str(len(previous)+1).encode(), previous)
        offset = int(re.search(rb'tail -c\+(\d+)', result)[1])
        if offset == len(result)+1:
            return result
    raise ValueError('launcher address did not settle')


def decode(command, payload):
    process = subprocess.run(command, input=payload, capture_output=True, timeout=15)
    require(process.returncode == 0 and not process.stderr, 'independent decoder failed: ' + repr(process.stderr))
    return process.stdout


def strict_decode(payload, format):
    decoder = lzma.LZMADecompressor(format=format)
    result = decoder.decompress(payload)
    require(decoder.eof and not decoder.unused_data, 'incomplete or trailing-data compressed stream')
    return result


def linked_liblzma():
    paths = {line.split()[-1] for line in Path('/proc/self/maps').read_text().splitlines() if '/liblzma.so' in line}
    require(len(paths) == 1, 'unknown Python linked liblzma mapping')
    path = next(iter(paths))
    library = ctypes.CDLL(path)
    library.lzma_version_string.restype = ctypes.c_char_p
    return {'mapped_path': path, 'version': library.lzma_version_string().decode()}


def xz_accounting(payload):
    require(payload[:6] == b'\xfd7zXZ\0' and payload[6:8] == b'\0\4' and payload[-2:] == b'YZ', 'unknown pinned XZ shape/check')
    index_size = (int.from_bytes(payload[-8:-4], 'little')+1)*4
    index_start = len(payload)-12-index_size
    require(payload[index_start] == 0, 'unknown XZ index')
    def vli(at):
        value, shift = 0, 0
        while True:
            require(shift <= 56, 'invalid XZ VLI')
            octet = payload[at]
            at += 1
            value |= (octet & 127) << shift
            if octet < 128:
                return value, at
            shift += 7
    count, at = vli(index_start+1)
    require(count == 1, 'unknown multi-block control')
    unpadded, at = vli(at)
    uncompressed, at = vli(at)
    block_header = (payload[12]+1)*4
    padded = (unpadded+3)//4*4
    require(12+padded == index_start, 'XZ block/index boundary differs')
    parts = {'stream_header_bytes': 12, 'block_header_bytes': block_header, 'CRC64_bytes': 8,
             'block_padding_bytes': padded-unpadded, 'index_bytes': index_size, 'stream_footer_bytes': 12}
    return {**parts, 'total_container_bytes': sum(parts.values()),
            'compressed_block_data_bytes': unpadded-block_header-8, 'uncompressed_bytes': uncompressed}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--control', type=Path, required=True, help='exact qualified A5207 build-1 directory')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(sys.platform == 'linux', 'requires the recorded Linux decoder environment')
    require(args.out.is_absolute(), 'new absolute external output required')
    out = args.out.resolve()
    require(not out.exists() and not any((p/'.git').exists() for p in (out, *out.parents)), 'new output outside Git required')
    control = args.control.resolve(strict=True)
    out.mkdir(parents=True)
    recipe = out/'recipe'
    recipe.mkdir()
    report = {'complete': False, 'scope': 'first cost only, same exact bootstrap/source/compiler/native; no engine execution',
              'control': str(control), 'inputs': {}, 'records': [],
              'tools': {'python': sys.version.splitlines()[0],
                        'xz': subprocess.check_output(['xz', '--version'], text=True).splitlines(),
                        'lzma': subprocess.check_output(['lzma', '--version'], text=True).splitlines(),
                        'lzma_invoked_path': shutil.which('lzma'),
                        'lzma_resolved_path': str(Path(shutil.which('lzma')).resolve()),
                        'Python_linked_liblzma': linked_liblzma()},
              'engine_campaign_run': False, 'compiler_run': False, 'runtime_qualified': False}
    def save():
        (out/'results.json').write_text(json.dumps(report, indent=2)+'\n')
    def freeze(name, data):
        path = recipe/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        report['inputs'][name] = {'bytes': len(data), 'sha256': sha(data)}
    save()
    try:
        originals = {}
        for name, expected in PINS.items():
            data = (control/name).read_bytes()
            require(sha(data) == expected, 'unknown A5207 input: '+name)
            freeze('control/'+name, data)
            originals[name] = data
        manifest_raw = originals['build.json']
        manifest = json.loads(manifest_raw)
        require(manifest['complete'] and manifest['whole_reproduced'] and manifest['source_reproduced'] and manifest['native_reproduced'], 'unqualified/incomplete maintained control')
        require(manifest['actual']['whole_sha256'] == PINS['x'] and manifest['actual']['native_sha256'] == PINS['native/x']
                and manifest['actual']['source_sha256'] == PINS['main.c'], 'maintained manifest identity differs')
        require(set(manifest['inputs']) == INPUT_NAMES, 'unknown maintained input graph')
        freeze('control/build.json', manifest_raw)
        report['maintained_input_storage'] = {}
        for name, binding in manifest['inputs'].items():
            # The hash-pinned maintained builder records logical repository
            # names but writes these five helper inputs by path.name.
            stored = Path(name).name if name.startswith('engines/') else name
            data = (control/'inputs'/stored).read_bytes()
            require(sha(data) == binding['sha256'] and len(data) == binding['bytes'], 'maintained source recipe input changed: '+name)
            report['maintained_input_storage'][name] = 'inputs/'+stored
            freeze('control/inputs/'+name, data)
        freeze('build.py', Path(__file__).read_bytes())
        bootstrap, source, wrapper = originals['bootstrap.py'], originals['main.c'], originals['x']
        require(bootstrap_source(bootstrap) == source, 'bootstrap compiler stdin differs from pinned C')
        offset = wrapper.index(b'\xfd7zXZ\0')
        prefix, old_payload = wrapper[:offset], wrapper[offset:]
        require(prefix == (recipe/'control/inputs/launcher.sh').read_bytes() and len(prefix) == 75
                and len(wrapper) == 5207, 'qualified launcher/size changed')
        require(strict_decode(old_payload, lzma.FORMAT_XZ) == bootstrap, 'qualified XZ bootstrap differs')
        report['XZ_container_accounting'] = xz_accounting(old_payload)
        xz_filters = [{'id': lzma.FILTER_LZMA2, 'preset': PRESET, 'lc': 2, 'lp': 0, 'pb': 0}]
        xz_first = prefix + lzma.compress(bootstrap, format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64, filters=xz_filters)
        xz_second = prefix + lzma.compress(bootstrap, format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64, filters=xz_filters)
        require(xz_first == xz_second == wrapper, 'exact A5207 whole control did not reproduce')
        candidate_launcher = candidate_prefix(prefix)
        filters = [{'id': lzma.FILTER_LZMA1, 'preset': PRESET, 'lc': 2, 'lp': 0, 'pb': 0}]
        first = lzma.compress(bootstrap, format=lzma.FORMAT_ALONE, check=lzma.CHECK_NONE, filters=filters)
        second = lzma.compress(bootstrap, format=lzma.FORMAT_ALONE, check=lzma.CHECK_NONE, filters=filters)
        require(first == second, 'LZMA-alone payload did not independently repeat')
        require(first[0] == 2 and int.from_bytes(first[1:5], 'little') == 67108864
                and first[5:13] == b'\xff'*8, 'unexpected LZMA1 lc/lp/pb, dictionary or unknown-size header')
        for attempt, payload in enumerate((first, second), 1):
            require(strict_decode(payload, lzma.FORMAT_ALONE) == bootstrap, 'Python LZMA-alone decode differs')
            require(strict_decode(old_payload, lzma.FORMAT_XZ) == bootstrap, 'Python XZ control decode differs')
            require(decode(['lzma', '-dc'], payload) == bootstrap, 'CLI LZMA-alone decode differs')
            require(decode(['xz', '-dc'], old_payload) == bootstrap, 'CLI XZ control decode differs')
            target = out/('attempt-'+str(attempt))
            target.mkdir()
            packed = candidate_launcher+payload
            address = int(re.search(rb'tail -c\+(\d+)', candidate_launcher)[1])
            require(packed[address-1:] == payload, 'actual shell payload address differs')
            (target/'x').write_bytes(packed)
            (target/'x').chmod(0o755)
            (target/'bootstrap.py').write_bytes(bootstrap)
        candidate = candidate_launcher+first
        require((out/'attempt-1/x').read_bytes() == (out/'attempt-2/x').read_bytes(), 'whole LZMA-alone file did not repeat')
        for name, packed, launcher, payload, header in (('qualified-XZ', wrapper, prefix, old_payload, None),
                                                      ('one-LZMA-alone', candidate, candidate_launcher, first, 13)):
            report['records'].append({'format': name, 'whole_bytes': len(packed), 'whole_sha256': sha(packed),
                                      'launcher_bytes': len(launcher), 'launcher_sha256': sha(launcher),
                                      'payload_bytes': len(payload), 'payload_sha256': sha(payload),
                                      'container_header_bytes': header,
                                      'bootstrap_bytes': len(bootstrap), 'bootstrap_sha256': sha(bootstrap),
                                      'source_sha256': sha(source), 'original_native_sha256': PINS['native/x'],
                                      'whole_reproduced_twice': True, 'CLI_and_Python_decode_exact_twice': True})
        report['candidate'] = {'command': [str(out/'attempt-1/x')], 'decoder': ['lzma', '-dc'],
                               'preset': '9 extreme', 'filter': 'LZMA1', 'lc': 2, 'lp': 0, 'pb': 0,
                               'dictionary_bytes': 67108864, 'LZMA_alone_header_hex': first[:13].hex(),
                               'integrity_scope': 'legacy LZMA-alone has no XZ CRC64; no equivalent corruption-detection claim',
                               'bootstrap_runtime_argv_and_cleanup': 'exact original bytes; not executed at this cost stage'}
        report['delta_whole_bytes'] = len(candidate)-len(wrapper)
        report['gain'] = len(candidate) < len(wrapper)
        report['above_4096_bytes'] = len(candidate)-4096
        report['under_4096_bytes'] = len(candidate) <= 4096
        report['complete'] = True
    except Exception as error:
        report['failure'] = repr(error)
        raise
    finally:
        save()
    print(json.dumps({'complete': True, 'control_bytes': len(wrapper), 'candidate_bytes': len(candidate),
                      'delta_bytes': report['delta_whole_bytes'], 'gain': report['gain'],
                      'engine_campaign_run': False, 'out': str(out)}))


if __name__ == '__main__':
    main()
