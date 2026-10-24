#!/usr/bin/env python3
"""One candidate compile and fixed whole package; never execute an engine."""
import argparse
import ast
import hashlib
import importlib.util
import json
import lzma
import os
from pathlib import Path
import signal
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def need(ok, message):
    if not ok:
        raise ValueError(message)


def text(path):
    raw = path.read_bytes()
    normalized = raw.replace(b'\r\n', b'\n')
    need(b'\r' not in normalized, 'lone CR in text input')
    return raw, normalized


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def source_argument(expression):
    node = ast.parse(expression, mode='eval').body
    if isinstance(node, ast.Constant) and type(node.value) is bytes:
        return node.value
    need(isinstance(node, ast.Call) and not node.args and not node.keywords
         and isinstance(node.func, ast.Attribute) and node.func.attr == 'encode'
         and isinstance(node.func.value, ast.Constant) and type(node.func.value.value) is str,
         'unadmitted source literal')
    return node.func.value.value.encode()


def run(command, data, cwd, timeout):
    child = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, cwd=cwd, start_new_session=True)
    timed_out = False
    try:
        stdout, stderr = child.communicate(data, timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(child.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            stdout, stderr = child.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            stdout, stderr = child.communicate()
    try:
        os.killpg(child.pid, 0)
        absent = False
    except ProcessLookupError:
        absent = True
    return stdout, stderr, {'command': command, 'cwd': str(cwd), 'pid': child.pid,
                            'returncode': child.returncode, 'timeout': timed_out,
                            'reaped': True, 'owned_process_group_absent': absent}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    need(sys.platform == 'linux' and args.out.is_absolute() and not out.exists()
         and not any((p / '.git').exists() for p in (out, *out.parents)),
         'new absolute Linux output outside Git required')
    out.mkdir(parents=True)
    frozen = out / 'producer'
    frozen.mkdir()
    report = {'complete': False, 'scope': 'one F fixed unit-window predicate first cost',
              'native_compile_attempts': 0, 'candidate_compressions': 0,
              'control_compiles_compressions_copies': 0, 'engine_game_benchmark_normal_Git': 0,
              'inputs': {}, 'processes': []}
    save = lambda: (out / 'cost.json').write_text(json.dumps(report, indent=2) + '\n')
    save()
    try:
        for name in ('config.json', 'cost.py', 'transform.py', 'README.md'):
            raw, data = text(HERE / name)
            (frozen / name).write_bytes(data)
            report['inputs'][name] = {'bytes': len(data), 'sha256': sha(data), 'raw_sha256': sha(raw)}
        config = json.loads((frozen / 'config.json').read_bytes())
        need(config['format'] == 1 and config['family'] == 'F', 'configuration differs')
        need(sha((frozen / 'transform.py').read_bytes()) == config['transform_sha256'], 'fixed transformation differs')
        report['tools'] = {'python': sys.version, 'cc': subprocess.check_output(['cc', '--version'], text=True).splitlines()[0],
                           'lzma': subprocess.check_output(['lzma', '--version'], text=True).splitlines()[0]}
        report['environment'] = 'inherited unchanged'
        for name, pin in config['helper_sha256'].items():
            raw, data = text(REPO / name)
            need(sha(data) == pin, 'ordinary helper differs: ' + name)
            (frozen / Path(name).name).write_bytes(data)
            report['inputs'][name] = {'bytes': len(data), 'sha256': sha(data), 'raw_sha256': sha(raw)}
        _, recipe_bytes = text(REPO / 'engines/compact/tiny-entry-f/recipe.json')
        (frozen / 'normal-recipe.json').write_bytes(recipe_bytes)
        recipe = json.loads(recipe_bytes)
        for key in ('profile', 'compiler', 'compression'):
            need(recipe[key] == config[key], 'normal fixed setting differs: ' + key)
        expected = recipe['expected']
        for field, name in [('source', 'main.c'), ('native', 'native/x'), ('whole', 'x')]:
            need(expected[field + '_bytes'] == config['baseline'][name]['bytes']
                 and expected[field + '_sha256'] == config['baseline'][name]['sha256'],
                 'normal expected artifact differs: ' + name)
        need(expected['bootstrap_sha256'] == config['baseline']['bootstrap.py']['sha256'], 'normal bootstrap differs')
        control = {}
        for name, pin in config['baseline'].items():
            data = (Path(config['baseline_root']) / name).read_bytes()
            need(sha(data) == pin['sha256'] and ('bytes' not in pin or len(data) == pin['bytes']),
                 'raw qualified control differs: ' + name)
            control[name] = data
        need(json.loads(control['build.json'])['complete'], 'normal control build is incomplete')
        report['baseline'] = config['baseline']
        transform = load('fixed_F_unit_bound', frozen / 'transform.py').transform
        literal = load('fixed_source_literal', frozen / 'pack_stream.py').source_literal
        template = (frozen / 'bootstrap.py.in').read_bytes()
        prefix = (frozen / 'launcher.sh').read_bytes()
        marker = b'__ROVE_SOURCE_LITERAL__'
        need(len(prefix) == 77 and template.count(marker) == 1, 'bootstrap geometry differs')
        old_expression, _ = literal(control['main.c'])
        need(source_argument(old_expression) == control['main.c']
             and template.replace(marker, old_expression.encode()) == control['bootstrap.py'],
             'control source/bootstrap reconstruction differs')
        candidate, report['transformation'] = transform(control['main.c'])
        (out / 'main.c').write_bytes(candidate)
        expression, kind = literal(candidate)
        need(source_argument(expression) == candidate, 'candidate literal differs')
        script = template.replace(marker, expression.encode())
        ast.parse(script)
        (out / 'bootstrap.py').write_bytes(script)
        report.update(source_bytes=len(candidate), source_sha256=sha(candidate),
                      bootstrap_bytes=len(script), bootstrap_sha256=sha(script), literal_kind=kind,
                      compiler=config['compiler'], compression=config['compression'])
        native_dir = out / 'native'
        native_dir.mkdir()
        report['native_compile_attempts'] = 1
        save()
        stdout, stderr, process = run(config['compiler'], candidate, native_dir, 90)
        (native_dir / 'compiler.stdout').write_bytes(stdout)
        (native_dir / 'compiler.stderr').write_bytes(stderr)
        report['processes'].append(process)
        need(process['returncode'] == 0 and not process['timeout'] and process['owned_process_group_absent'],
             'candidate compiler failed or did not physically finish')
        native = (native_dir / 'x').read_bytes()
        report.update(native_bytes=len(native), native_sha256=sha(native),
                      entire_native_equal=native == control['native/x'])
        report['candidate_compressions'] = 1
        save()
        packed = lzma.compress(script, format=lzma.FORMAT_ALONE, check=lzma.CHECK_NONE,
                               filters=[{'id': lzma.FILTER_LZMA1, 'preset': 9 | lzma.PRESET_EXTREME,
                                         'lc': 2, 'lp': 0, 'pb': 0, 'mf': lzma.MF_BT4,
                                         'dict_size': 67108864, 'nice_len': 32}])
        need(packed[:13] == control['x'][77:90], 'fixed ALONE header differs')
        whole = prefix + packed
        (out / 'x').write_bytes(whole)
        report['decodes'] = []
        for label, image, bootstrap in [('control', control['x'], control['bootstrap.py']), ('candidate', whole, script)]:
            need(image[:77] == prefix, 'prefix differs')
            decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
            need(decoder.decompress(image[77:]) == bootstrap and decoder.eof and not decoder.unused_data,
                 'strict Python restoration differs')
            stdout, stderr, process = run(['lzma', '-dc'], image[77:], out, 15)
            report['processes'].append(process)
            need(process['returncode'] == 0 and not process['timeout'] and process['owned_process_group_absent']
                 and stdout == bootstrap and not stderr, 'independent CLI restoration differs')
            report['decodes'].append({'form': label, 'strict_python_eof': True, 'trailing_bytes': 0,
                                      'independent_cli_exact': True, 'bootstrap_sha256': sha(bootstrap)})
        report.update(whole_bytes=len(whole), whole_sha256=sha(whole),
                      whole_delta=len(whole) - len(control['x']), complete=True)
        save()
        print(json.dumps({key: report[key] for key in ('complete', 'source_bytes', 'source_sha256',
                         'native_bytes', 'native_sha256', 'entire_native_equal',
                         'whole_bytes', 'whole_sha256', 'whole_delta')}), flush=True)
    except BaseException as error:
        report['error'] = repr(error)
        save()
        raise


if __name__ == '__main__':
    main()
