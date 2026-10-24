#!/usr/bin/env python3
"""One exact shipping-F TT predicate, one new native and one fixed-codec whole."""
import argparse
import hashlib
import importlib.util
import json
import lzma
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BASE = Path('/home/stemxstudio/rove4k-f-member-normal-20261020')
DECODE_HELPER = HERE.parents[2]/'engines/experiments/tiny-source-codec/decode.py'
DECODE_PIN = 'c43303b6524321b24dfba069afc9a135998e408503740ea8d9fbcfb9bb5e9f5a'
PINS = {
    'main.c': (9954, '00239e23500d41c45801cdb19c4e7c8cc8b22cf29bebd7e4fbc8fdd1e08c7916'),
    'native/x': (22672, '757b9a14cd5174dad55754196cce098fd89018a8b0d7adcf08bcddb2e1fc092b'),
    'x': (4814, '30240a27c0682519b1d2539c58d153ebaf7dcf4b9d9dde631f985f3c27261285'),
    'bootstrap.py': (10953, 'b43f24051ac613826e630ed211c3fd1528ee2f85638372c62c679254b55c8e32'),
    'build.json': (40630, '522f9c565914bf1fda1cd74cbb7e5133c6e74bdf90198fa4f26d1dbff222e26f')}
HELPERS = {'inputs/build.py': '153e8a1d8a99bc8791910099fcf771dbc634524a399f1cf0ece98c27068ef5d0',
           'inputs/pack_stream.py': 'b4addefbb1233881e85707aa525ca4af7f8210d9d27f56fbb52e4440a966b99e',
           'inputs/recipe.json': '8439ec8a7762608663310fcfceed4eb04489fdabeab0da41b2748c81bafad5eb'}
OLD = b'(I==1||(I==2&&H>=d)||(I==3&&H<d))'
NEW = b'(I==1||((H>=d)==(I==2)))'
OUTER = b'if(f&&I&&J==(a>0?a:0)&&'
COMPILER = ['cc', '-Os', '-pthread', '-x', 'c', '-', '-o', 'x', '-s']
CODEC = {'format': 'lzma-alone', 'filter': 'LZMA1', 'preset': 9, 'extreme': True,
         'lc': 2, 'lp': 0, 'pb': 0, 'check': 'NONE', 'mf': 'BT4',
         'dictionary_bytes': 67108864, 'nice_len': 32}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def info(data):
    return {'bytes': len(data), 'sha256': sha(data)}


def require(value, message):
    if not value:
        raise ValueError(message)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    require(args.out.is_absolute() and not out.exists() and not any((p/'.git').exists() for p in (out, *out.parents)), 'new absolute non-Git output required')
    controls = {name: (BASE/name).read_bytes() for name in PINS}
    for name, (size, pin) in PINS.items():
        require(info(controls[name]) == {'bytes': size, 'sha256': pin}, 'actual control input changed: '+name)
    for name, pin in HELPERS.items():
        require(sha((BASE/name).read_bytes()) == pin, 'pinned normal helper/recipe changed: '+name)
    require(sha(DECODE_HELPER.read_bytes()) == DECODE_PIN, 'pinned existing decode helper changed')
    verify = load('f_predicate_pinned_decode', DECODE_HELPER).verify
    recipe = json.loads((BASE/'inputs/recipe.json').read_bytes())
    require(recipe['compiler'] == COMPILER and recipe['compression'] == CODEC, 'fixed compiler/codec differs')
    require(json.loads(controls['build.json'])['complete'], 'actual control build incomplete')
    out.mkdir(parents=True)
    report = {'complete': False, 'scope': 'one TT predicate source-expression cost only',
        'inputs_reused_read_only': {str(BASE/name): info(raw) for name, raw in controls.items()},
        'helper_pins_reused_without_copy': HELPERS, 'compiler': COMPILER, 'compression': CODEC,
        'control_compile_runs': 0, 'control_copy_runs': 0, 'new_engine_or_Clang_AST_passes': 0, 'CPP_runs': 0,
        'decode_helper': {'path': str(DECODE_HELPER), 'sha256': DECODE_PIN},
        'restricted_bootstrap_AST_checks': 0, 'bootstrap_executions': 0,
        'candidate_native_compiles': 0, 'candidate_whole_packages': 0, 'engine_runs': 0,
        'matrix_game_benchmark_runs': 0, 'variant_flag_model_alias_codec_sweeps': 0,
        'runtime_qualified': False, 'metadata_exception_applied': False, 'promotion_claim': False}
    def save():
        (out/'cost.json').write_text(json.dumps(report, indent=2)+'\n')
    save()
    try:
        source = controls['main.c']
        require(source.count(OLD) == 1 and NEW not in source, 'sole exact old predicate required')
        require(source.count(OUTER+OLD+b')return H;') == 1 and source.count(b'I=(F>>41)&3') == 1,
                'actual outer gate or 2-bit bound decode changed')
        require(source.count(b'static int aj(zc*w,const za*p,int a,int d,int f,int g,Move*l)') == 1,
                'actual search role/signature context changed')
        start = source.index(OLD)
        before, after = source[:start], source[start+len(OLD):]
        candidate = before+NEW+after
        require(candidate.count(NEW) == 1 and candidate.replace(NEW, OLD, 1) == source and
                candidate.count(OUTER+NEW+b')return H;') == 1, 'exact source inverse/outer gate differs')
        truth = []
        for bound in range(4):
            for ge in (False, True):
                old_inner = bound == 1 or (bound == 2 and ge) or (bound == 3 and not ge)
                new_inner = bound == 1 or (ge == (bound == 2))
                old_value, new_value = bool(bound) and old_inner, bool(bound) and new_inner
                require(old_value == new_value, 'full outer-bound predicate truth differs')
                truth.append({'bound': bound, 'score_ge_beta': ge, 'old_inner': old_inner,
                    'new_inner': new_inner, 'old_with_bound_gate': old_value, 'new_with_bound_gate': new_value})
        report['source_change'] = {'byte_offset': start, 'line': source[:start].count(b'\n')+1,
            'role_binding': {'I': 'bound=(F>>41)&3', 'H': 'integer score after mate/ply restoration',
                             'd': 'integer beta parameter', 'f': 'ply', 'a': 'depth', 'J': 'TT depth'},
            'old': OLD.decode(), 'new': NEW.decode(), 'old_bytes': len(OLD), 'new_bytes': len(NEW),
            'source': info(candidate), 'source_delta': len(candidate)-len(source),
            'exact_inverse': True, 'outer_gate_unchanged': OUTER.decode(),
            'protected_complement': info(before+after), 'truth_rows': truth,
            'bound0_requires_retained_outer_guard': True, 'new_feature_policy_domain_changes': False}
        (out/'main.c').write_bytes(candidate)
        compile_c = load('f_predicate_pinned_compile', BASE/'inputs/build.py').compile_c
        literal = load('f_predicate_pinned_literal', BASE/'inputs/pack_stream.py').source_literal
        report['candidate_native_compiles'] = 1
        save()
        native = compile_c(COMPILER, candidate, out/'native')
        old_native = controls['native/x']
        report['native'] = info(native)
        report['full_old_new_native_equal'] = native == old_native
        report['first_native_difference'] = next((i for i, (old, new) in enumerate(zip(old_native, native)) if old != new),
                                                min(len(old_native), len(native)) if old_native != native else None)
        save()
        old_literal, old_kind = literal(source)
        new_literal, new_kind = literal(candidate)
        script = controls['bootstrap.py']
        require(script.count(old_literal.encode()) == 1 and old_kind == new_kind, 'original bootstrap/source representation changed')
        require(script.count(b"subprocess.Popen('cc -Os -pthread -x c - -o x -s'.split()") == 1, 'original bootstrap compiler argv differs')
        new_script = script.replace(old_literal.encode(), new_literal.encode(), 1)
        require(new_script.count(new_literal.encode()) == 1 and new_script.replace(new_literal.encode(), old_literal.encode(), 1) == script,
                'bootstrap exact literal-only inverse differs')
        prefix = controls['x'][:77]
        report['restricted_bootstrap_AST_checks'] += 1
        report['control_strict_decode'] = verify(controls['x'], prefix, source, COMPILER, script, expected_format='alone')
        report['candidate_whole_packages'] = 1
        payload = lzma.compress(new_script, format=lzma.FORMAT_ALONE, check=lzma.CHECK_NONE,
            filters=[{'id': lzma.FILTER_LZMA1, 'preset': 9 | lzma.PRESET_EXTREME, 'lc': 2, 'lp': 0, 'pb': 0,
                      'mf': lzma.MF_BT4, 'dict_size': 67108864, 'nice_len': 32}])
        require(payload[:13] == controls['x'][77:90] == bytes.fromhex('0200000004ffffffffffffffff'), 'fixed ALONE header changed')
        whole = prefix+payload
        report['restricted_bootstrap_AST_checks'] += 1
        report['candidate_strict_decode'] = verify(whole, prefix, candidate, COMPILER, new_script, expected_format='alone')
        cli = subprocess.run(['lzma', '-dc'], input=payload, capture_output=True, timeout=15)
        (out/'decode.stdout').write_bytes(cli.stdout)
        (out/'decode.stderr').write_bytes(cli.stderr)
        require(cli.returncode == 0 and not cli.stderr and cli.stdout == new_script, 'independent CLI restoration differs')
        (out/'x').write_bytes(whole)
        (out/'x').chmod(0o755)
        (out/'bootstrap.py').write_bytes(new_script)
        report.update(complete=True, whole=info(whole), bootstrap=info(new_script),
            whole_delta=len(whole)-len(controls['x']), bootstrap_literal_only_inverse=True,
            literal_kind=new_kind, strict_Python_and_CLI_decode=True,
            semantic_scope='integer score/beta and bound0..3 behind unchanged nonzero-bound gate',
            independent_repeat_claim=False, live_command_handles=0)
        save()
        print(json.dumps({'complete': True, 'source_delta': report['source_change']['source_delta'],
            'native': report['native'], 'full_native_equal': report['full_old_new_native_equal'],
            'whole': report['whole'], 'whole_delta': report['whole_delta'], 'engine_runs': 0}))
    except BaseException as error:
        report['failure'] = repr(error)
        save()
        raise


if __name__ == '__main__':
    main()
