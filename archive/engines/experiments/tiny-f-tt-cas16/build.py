"""One F CAS16 native, then one fixed whole only after codegen readback."""
import argparse
import hashlib
import importlib.util
import json
import lzma
from pathlib import Path
import platform
import re
import struct
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def need(condition, message):
    if not condition:
        raise ValueError(message)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def save(path, report):
    path.write_text(json.dumps(report, indent=2) + '\n')


def native(args):
    out = args.out.resolve()
    need(args.out.is_absolute() and not out.exists() and
         not any((p/'.git').exists() for p in (out, *out.parents)), 'new absolute output outside Git required')
    need(platform.system() == 'Linux' and platform.machine() == 'x86_64', 'fixed Linux x86-64 target only')
    flags = [line.split(':', 1)[1].split() for line in Path('/proc/cpuinfo').read_text().splitlines()
             if line.startswith('flags')]
    need(flags and all('cx16' in row for row in flags), 'all advertised local CPUs must have CX16')
    recipe = json.loads((HERE/'recipe.json').read_bytes())
    out.mkdir()
    report = {'complete': False, 'stage': 'one native; codegen inspection before separate cost',
              'native_compile_attempts': 0, 'baseline_compiles': 0, 'baseline_engine_copies': 0,
              'codec_compressions': 0, 'engine_executions': 0, 'native_executions': 0,
              'Clang_AST_parses': 0, 'inputs': {}, 'normal_main_calls': 0,
              'cx16_advertised_cpu_rows': len(flags), 'runtime_address_observation': False}
    save(out/'build.json', report)
    try:
        for name in ('build.py', 'recipe.json'):
            data = (HERE/name).read_bytes()
            folder = out/'producer';folder.mkdir(exist_ok=True)
            (folder/name).write_bytes(data)
            report['inputs'][name] = {'bytes': len(data), 'sha256': sha(data)}
        helpers = out/'helpers';helpers.mkdir()
        for relative, pin in recipe['helper_sha256'].items():
            raw = (REPO/relative).read_bytes();data = raw.replace(b'\r\n', b'\n')
            need(b'\r' not in data and sha(data) == pin, 'fixed ordinary helper changed: '+relative)
            target = helpers/relative
            target.parent.mkdir(parents=True, exist_ok=True);target.write_bytes(data)
            report['inputs'][relative] = {'bytes': len(data), 'sha256': sha(data), 'raw_sha256': sha(raw)}
        baseline = args.baseline.resolve()
        expected = recipe['baseline_expected']
        for name, key in (('main.c', 'source'), ('native/x', 'native'), ('x', 'whole'), ('bootstrap.py', 'bootstrap')):
            data = (baseline/name).read_bytes()
            need(sha(data) == expected[key+'_sha256'], 'current baseline differs: '+name)
        source = (baseline/'main.c').read_bytes()
        need(len(source) == recipe['baseline_source_bytes'], 'baseline length differs')
        candidate = source
        transformations = []
        for rule in recipe['rules']:
            before, after = rule['before'].encode(), rule['after'].encode()
            need(candidate.count(before) == rule['count'], 'literal transform boundary changed: '+rule['role'])
            candidate = candidate.replace(before, after)
            transformations.append({'role': rule['role'], 'before_sha256': sha(before), 'after_sha256': sha(after)})
        inverse = candidate
        for rule in reversed(recipe['rules']):
            before, after = rule['before'].encode(), rule['after'].encode()
            need(inverse.count(after) == rule['count'], 'ambiguous transform inverse')
            inverse = inverse.replace(after, before)
        need(inverse == source, 'source inverse differs')
        need(len(candidate) == recipe['candidate_source_bytes'] and sha(candidate) == recipe['candidate_source_sha256'],
             'fixed new candidate differs')
        (out/'main.c').write_bytes(candidate)
        report.update(candidate_source_bytes=len(candidate), candidate_source_sha256=sha(candidate),
                      exact_transform_inverse=True, transformations=transformations, baseline=str(baseline),
                      baseline_expected=expected, candidate_compiler=recipe['candidate_compiler'])
        save(out/'build.json', report)
        normal = module('frozen_normal_F', helpers/'engines/compact/tiny-entry-f/build.py')
        report['native_compile_attempts'] = 1
        save(out/'build.json', report)
        binary = normal.compile_c(recipe['candidate_compiler'], candidate, out/'native')
        report.update(native_bytes=len(binary), native_sha256=sha(binary), native_compile_complete=True)
        save(out/'build.json', report)
        tool_outputs = {}
        for label, command in {
            'headers': ['readelf', '-h', str(out/'native/x')],
            'symbols': ['readelf', '--dyn-syms', '--wide', str(out/'native/x')],
            'dynamic': ['readelf', '-d', str(out/'native/x')],
            'disassembly': ['objdump', '-d', '-M', 'intel', str(out/'native/x')],
            'baseline_dynamic': ['readelf', '-d', str(baseline/'native/x')],
        }.items():
            result = subprocess.run(command, capture_output=True, check=True, text=True, timeout=15)
            (out/(label+'.txt')).write_text(result.stdout)
            tool_outputs[label] = result.stdout
        text = tool_outputs['disassembly']
        cas_lines = [line for line in text.splitlines() if re.search(r'\block\s+cmpxchg16b\b', line)]
        need(len(cas_lines) == 3, 'three fixed inlined CMPXCHG16B sites required')
        need('ELF64' in tool_outputs['headers'] and 'X86-64' in tool_outputs['headers'], 'wrong ELF ABI')
        need(not re.search(r'__sync_\w*16\b|__atomic_\w*16\b', tool_outputs['symbols']+text), 'external128 atomic helper')
        needed = lambda data: re.findall(r'Shared library: \[([^]]+)\]', data)
        need(needed(tool_outputs['dynamic']) == needed(tool_outputs['baseline_dynamic']) and
             'libatomic' not in tool_outputs['dynamic'], 'new dynamic library dependency')
        report.update(complete=True, codegen_automatic_gates=True, inline_cmpxchg16b=cas_lines,
                      dynamic_needed=needed(tool_outputs['dynamic']), library_added=False,
                      source_compile_asserts='sizeof16, alignof16, GCC target CAS16 macro passed in sole compilation',
                      alignment_contract='C11 calloc fundamental alignment + AMD64 ABI16 + asserted Entry16 stride',
                      manual_address_codegen_review_required_before_cost=True,
                      no_contention_trace_equivalence=True, startup_duplicate_clear_removed=True,
                      quiescent_clear_function_retained=True)
        save(out/'build.json', report)
        print(json.dumps({'complete': True, 'native_bytes': len(binary), 'native_sha256': sha(binary),
                          'candidate_source_bytes': len(candidate), 'inline_CAS16_sites': len(cas_lines),
                          'cost_not_run': True}), flush=True)
    except BaseException as error:
        report['error'] = {'type': type(error).__name__, 'message': str(error)}
        save(out/'build.json', report)
        raise


def readback(args):
    """Admit the existing sole native; preserve the original failed checker receipt."""
    out = args.build.resolve()
    need(not (out/'codegen-readback.json').exists(), 'one existing-native readback only')
    build_raw = (out/'build.json').read_bytes()
    build = json.loads(build_raw)
    binary = (out/'native/x').read_bytes()
    need(build['native_compile_attempts'] == 1 and build['native_compile_complete'] and
         build['native_sha256'] == sha(binary) ==
         '78cfb7232c3bd90facc21c1e87ff5b953fe2a221b3877b77897107c6223570c6',
         'existing sole fixed native differs')
    need(not build['complete'] and build['error'] == {
         'type': 'ValueError', 'message': 'exactly two real inline CMPXCHG16B sites required'},
         'only the recorded checker-assumption failure is admitted')
    need(sha((out/'producer/build.py').read_bytes()) == build['inputs']['build.py']['sha256'] ==
         'd0bf7b0e556635a8106b975344fcee9d8a456224203db333c730f28b571c68f8',
         'original failed producer changed')
    review = json.loads(args.review.read_bytes())
    need(sha(args.review.read_bytes()) == 'a43a015f6c5955ce10c99e67a36691a0dd9e0555f1dec15bf45b7d5770c84d7f' and
         review['native_sha256'] == sha(binary) and review['slot_stride_16'] and
         review['calloc_element_size_16'] and review['CAS_addresses_from_table_base'] and
         review['result'] == 'PASS' and review['observed_sites'] == 3 and
         [review[name]['address'] for name in ('read_snapshot', 'write_snapshot', 'write_CAS')] ==
         ['0x26a5', '0x2ae3', '0x2b1a'] and review['full_key_low64_data_high64'] and
         review['write_CAS']['no_retry'] and review['write_snapshot']['returned_expected_for_store'],
         'fixed independent static codegen review missing')
    texts = {name: (out/(name+'.txt')).read_text() for name in
             ('headers', 'symbols', 'dynamic', 'disassembly', 'baseline_dynamic')}
    cas_lines = [line for line in texts['disassembly'].splitlines()
                 if re.search(r'\block\s+cmpxchg16b\b', line)]
    need([line.split(':', 1)[0].strip() for line in cas_lines] == ['26a5', '2ae3', '2b1a'],
         'fixed emitted CAS sites differ')
    need(all(sha((out/name).read_bytes()) == pin for name, pin in review['artifact_sha256'].items()),
         'independently reviewed tool output changed')
    need(binary[:6] == b'\x7fELF\x02\x01' and struct.unpack_from('<H', binary, 18)[0] == 62,
         'fixed ELF64 little-endian AMD64 ABI required')
    phoff = struct.unpack_from('<Q', binary, 32)[0]
    stride, count = struct.unpack_from('<HH', binary, 54)
    segments = [struct.unpack_from('<IIQQQQQQ', binary, phoff+i*stride) for i in range(count)]
    for address, opcode in ((0x26a5, 'f04a0fc70c17'), (0x2ae3, 'f0490fc708'), (0x2b1a, 'f0490fc708')):
        matches = [p for p in segments if p[0] == 1 and p[3] <= address and
                   address+len(bytes.fromhex(opcode)) <= p[3]+p[5] and p[1]&1]
        need(len(matches) == 1, 'CAS instruction must map to one executable load')
        p = matches[0];offset = p[2]+address-p[3]
        need(binary[offset:offset+len(bytes.fromhex(opcode))] == bytes.fromhex(opcode),
             'disassembly CAS bytes differ from actual native')
    need(not re.search(r'__sync_\w*16\b|__atomic_\w*16\b', texts['symbols']+texts['disassembly']),
         'external128 atomic helper')
    needed = lambda data: re.findall(r'Shared library: \[([^]]+)\]', data)
    need(needed(texts['dynamic']) == needed(texts['baseline_dynamic']) == ['libc.so.6'] and
         'libatomic' not in texts['dynamic'], 'dynamic dependency changed')
    producer = out/'reviewed-producer';producer.mkdir()
    for name in ('build.py', 'recipe.json'):
        (producer/name).write_bytes((HERE/name).read_bytes())
    (out/'independent-codegen-review.json').write_bytes(args.review.read_bytes())
    save(out/'codegen-readback.json', {
         'complete': True, 'native_sha256': sha(binary), 'initial_build_sha256': sha(build_raw),
         'original_failure_preserved': True, 'initial_build_complete': False,
         'checker_correction': 'read and write calls inline separately: one read snapshot, write snapshot plus store',
         'inline_cmpxchg16b': cas_lines, 'instruction_bytes_rebound_to_ELF_loads': True,
         'actual_address_review_sha256': sha(args.review.read_bytes()), 'review': review,
         'tool_text_sha256': {name: sha((out/(name+'.txt')).read_bytes()) for name in texts},
         'source_compile_asserts': 'sizeof16, alignof16, GCC target CAS16 macro passed in sole compile',
         'alignment_contract': 'C11 calloc fundamental alignment + AMD64 ABI16 + asserted Entry16 stride',
         'dynamic_needed': needed(texts['dynamic']), 'library_added': False,
         'runtime_address_observation': False, 'native_compiles': 0, 'native_executions': 0,
         'engine_executions': 0, 'codec_compressions': 0,
         'reviewed_producer_sha256': sha((producer/'build.py').read_bytes()),
         'recipe_sha256': sha((producer/'recipe.json').read_bytes())})
    need((out/'build.json').read_bytes() == build_raw, 'original failure receipt changed')
    print(json.dumps({'existing_native_codegen_readback': 'PASS', 'inline_CAS16_sites': 3,
                      'initial_failure_preserved': True, 'native_compiles': 0}), flush=True)


def cost(args):
    out = args.build.resolve()
    build = json.loads((out/'build.json').read_bytes())
    admission = json.loads((out/'codegen-readback.json').read_bytes())
    need(admission['complete'] and admission['native_sha256'] == build['native_sha256'] and
         admission['initial_build_sha256'] == sha((out/'build.json').read_bytes()),
         'existing-native codegen admission missing')
    need(not (out/'cost.json').exists(), 'one cost call only; no retry or sweep')
    need(args.native_sha256 == build['native_sha256'] == sha((out/'native/x').read_bytes()),
         'explicit reviewed native SHA differs')
    review = json.loads(args.review.read_bytes())
    need(sha(args.review.read_bytes()) == admission['actual_address_review_sha256'],
         'address review differs from admitted readback')
    need(review['native_sha256'] == args.native_sha256 and review['slot_stride_16'] and
         review['calloc_element_size_16'] and review['CAS_addresses_from_table_base'] and
         review['result'] == 'PASS', 'actual address/codegen review missing')
    recipe = json.loads((out/'producer/recipe.json').read_bytes())
    need(sha((HERE/'build.py').read_bytes()) == admission['reviewed_producer_sha256'] ==
         sha((out/'reviewed-producer/build.py').read_bytes()), 'reviewed cost producer changed')
    need(sha((HERE/'recipe.json').read_bytes()) == admission['recipe_sha256'] ==
         sha((out/'producer/recipe.json').read_bytes()), 'candidate recipe changed')
    candidate = (out/'main.c').read_bytes()
    need(sha(candidate) == recipe['candidate_source_sha256'], 'candidate source drift')
    helpers = out/'helpers'
    for relative, pin in recipe['helper_sha256'].items():
        need(sha((helpers/relative).read_bytes()) == pin, 'frozen helper drift: '+relative)
    literal = module('fixed_source_literal', helpers/'engines/compact/tiny-a/pack_stream.py').source_literal
    decoder = module('fixed_strict_decode', helpers/'engines/experiments/tiny-source-codec/decode.py')
    template = (helpers/'engines/compact/tiny-entry-f/bootstrap.py.in').read_bytes()
    prefix = (helpers/'engines/compact/tiny-entry-f/launcher.sh').read_bytes()
    old_command = ' '.join(recipe['baseline_compiler']).encode()
    new_command = ' '.join(recipe['candidate_compiler']).encode()
    need(len(prefix) == 77 and template.count(old_command) == 1 and
         template.count(b'__ROVE_SOURCE_LITERAL__') == 1, 'fixed prefix/compiler literal differs')
    template = template.replace(old_command, new_command)
    expression, kind = literal(candidate)
    script = template.replace(b'__ROVE_SOURCE_LITERAL__', expression.encode())
    save(out/'cost.json', {'complete': False, 'codec_compression_attempts': 1,
         'scope': 'one fixed candidate; incomplete retained on failure, no retry',
         'native_sha256': args.native_sha256, 'engine_executions': 0})
    payload = lzma.compress(script, format=lzma.FORMAT_ALONE, check=lzma.CHECK_NONE,
        filters=[{'id': lzma.FILTER_LZMA1, 'preset': 9|lzma.PRESET_EXTREME, 'lc': 2, 'lp': 0,
                  'pb': 0, 'mf': lzma.MF_BT4, 'dict_size': 67108864, 'nice_len': 32}])
    whole = prefix+payload
    (out/'x').write_bytes(whole);(out/'bootstrap.py').write_bytes(script)
    proof = decoder.verify(whole, prefix, candidate, recipe['candidate_compiler'], script, expected_format='alone')
    report = {'complete': True, 'stage': 'one fixed complete cost, no execution',
              'native_sha256': args.native_sha256, 'source_bytes': len(candidate), 'source_sha256': sha(candidate),
              'whole_bytes': len(whole), 'whole_sha256': sha(whole), 'bootstrap_bytes': len(script),
              'bootstrap_sha256': sha(script), 'payload_bytes': len(payload), 'prefix_bytes': len(prefix),
              'baseline_whole_bytes': recipe['baseline_expected']['whole_bytes'],
              'whole_gain': recipe['baseline_expected']['whole_bytes']-len(whole),
              'codec_compressions': 1, 'native_compiles': 0, 'engine_executions': 0,
              'strict_decode': proof, 'review_sha256': sha(args.review.read_bytes()),
              'producer_build_sha256': sha((out/'producer/build.py').read_bytes()),
              'reviewed_cost_producer_sha256': admission['reviewed_producer_sha256'],
              'initial_failure_preserved': True, 'codegen_readback_sha256': sha((out/'codegen-readback.json').read_bytes()),
              'recipe_sha256': sha((out/'producer/recipe.json').read_bytes()),
              'disposition': 'cost gain only; no runtime qualification' if len(whole)<recipe['baseline_expected']['whole_bytes'] else 'loss or tie; stop, no retry'}
    save(out/'cost.json', report)
    print(json.dumps({key: report[key] for key in ('complete', 'whole_bytes', 'whole_sha256', 'whole_gain', 'disposition')}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='stage', required=True)
    first = sub.add_parser('native');first.add_argument('--out', type=Path, required=True)
    first.add_argument('--baseline', type=Path, required=True)
    inspect = sub.add_parser('readback');inspect.add_argument('--build', type=Path, required=True)
    inspect.add_argument('--review', type=Path, required=True)
    second = sub.add_parser('cost');second.add_argument('--build', type=Path, required=True)
    second.add_argument('--native-sha256', required=True);second.add_argument('--review', type=Path, required=True)
    arguments = parser.parse_args()
    {'native': native, 'readback': readback, 'cost': cost}[arguments.stage](arguments)
