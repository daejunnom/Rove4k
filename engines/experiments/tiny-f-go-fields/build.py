#!/usr/bin/env python3
"""One fixed F go-field candidate, one native and one original ALONE package."""
import argparse
import ast
import hashlib
import importlib.util
import json
import lzma
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
INPUTS_SHA = 'a32f71732f90471a89d4ff89cdc267f0072352af924464ef73f12c1fe1f37c47'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def need(value, message):
    if not value:
        raise ValueError(message)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    need(sys.platform == 'linux' and args.out.is_absolute() and not out.exists() and
         not any((p/'.git').exists() for p in (out, *out.parents)), 'new Linux output outside Git required')
    out.mkdir(parents=True)
    report = {'complete': False, 'scope': 'one F parser source-sharing first cost only',
              'baseline_path': str(args.baseline.resolve()), 'native_compile_attempts': 0,
              'native_compiles_completed': 0, 'candidate_compressions': 0, 'strict_pure_decodes': 0,
              'control_compiles_copies_compressions': 0, 'C_AST_PP_engine_game_benchmark_runs': 0,
              'normal_builder_main_calls': 0, 'other_candidate_composition': False,
              'environment': 'unchanged inherited environment as existing normal compile_c',
              'cwd': str(out/'native'), 'compiler_descendant_group_absence': 'not observed by unchanged normal helper'}

    def save():
        (out/'cost.json').write_text(json.dumps(report, indent=2)+'\n')

    save()
    try:
        raw_inputs = (HERE/'inputs.json').read_bytes()
        need(sha(raw_inputs) == INPUTS_SHA, 'fixed first-cost inputs differ')
        inputs = json.loads(raw_inputs)

        def source_pins():
            need(sha((HERE/'producer.py').read_bytes()) == inputs['producer_sha256'], 'fixed producer differs')
            for name, pin in inputs['helper_sha256'].items():
                need(sha((REPO/name).read_bytes()) == pin, 'normal/helper source differs: '+name)

        source_pins()
        baseline = {}
        for name, expected in inputs['baseline'].items():
            data = (args.baseline/name).read_bytes()
            need(len(data) == expected['bytes'] and sha(data) == expected['sha256'], 'exact baseline differs: '+name)
            baseline[name] = data
        need(json.loads(baseline['build.json'])['complete'], 'baseline normal receipt incomplete')
        normal = module('unchanged_F_normal', REPO/'engines/compact/tiny-entry-f/build.py')
        producer = module('fixed_F_go_fields', HERE/'producer.py')
        compact = module('existing_minifier', REPO/'engines/scripts/minify.py').compact_source
        lexer = module('existing_token_lexer', REPO/'engines/scripts/rename_c.py')
        literal = module('existing_source_literal', REPO/'engines/compact/tiny-a/pack_stream.py').source_literal
        decode = module('existing_strict_decoder', REPO/'engines/experiments/tiny-source-codec/decode.py').verify
        canonical = (REPO/'engines/compact/tiny-entry-f/engine.c').read_bytes()
        candidate, transformation = producer.transform(baseline['main.c'], canonical, compact=compact, lexer=lexer)
        (out/'candidate.c').write_bytes(candidate)
        report.update(inputs_sha256=sha(raw_inputs), helper_sha256=inputs['helper_sha256'],
                      transformation=transformation, baseline_reused_not_rebuilt=inputs['baseline'])
        recipe = json.loads((REPO/'engines/compact/tiny-entry-f/recipe.json').read_bytes())
        need(recipe['compiler'] == inputs['compiler'] and recipe['compression'] == inputs['compression'], 'fixed normal recipe differs')
        template = (REPO/'engines/compact/tiny-entry-f/bootstrap.py.in').read_bytes()
        prefix = (REPO/'engines/compact/tiny-entry-f/launcher.sh').read_bytes()
        marker = b'__ROVE_SOURCE_LITERAL__'
        need(template.count(marker) == 1 and len(prefix) == 77, 'normal bootstrap/prefix geometry differs')

        def bootstrap(source):
            expression, kind = literal(source)
            script = template.replace(marker, expression.encode())
            ast.parse(script)
            return script, kind

        old_script, _ = bootstrap(baseline['main.c'])
        need(old_script == baseline['bootstrap.py'], 'baseline bootstrap reconstruction differs')
        report['baseline_decode'] = decode(baseline['x'], prefix, baseline['main.c'], inputs['compiler'], old_script, expected_format='alone')
        report['strict_pure_decodes'] = 1
        report['native_compile_attempts'] = 1
        report['compiler'] = inputs['compiler']
        save()
        native = normal.compile_c(inputs['compiler'], candidate, out/'native')
        report.update(native_compiles_completed=1, native_bytes=len(native), native_sha256=sha(native),
                      native_path=str(out/'native/x'), old_native_full_bytes_equal=native == baseline['native/x'],
                      native_metadata_normalization=False, compiler_helper_returned=True,
                      compiler_stderr_bytes=(out/'native/compiler.stderr').stat().st_size)
        save()
        script, kind = bootstrap(candidate)
        report['candidate_compressions'] = 1
        save()
        payload = lzma.compress(script, format=lzma.FORMAT_ALONE, check=lzma.CHECK_NONE,
                                filters=[{'id': lzma.FILTER_LZMA1, 'preset': 9|lzma.PRESET_EXTREME,
                                          'lc': 2, 'lp': 0, 'pb': 0, 'mf': lzma.MF_BT4,
                                          'dict_size': 67108864, 'nice_len': 32}])
        whole = prefix+payload
        (out/'bootstrap.py').write_bytes(script)
        (out/'x').write_bytes(whole)
        (out/'x').chmod(0o755)
        report['candidate_decode'] = decode(whole, prefix, candidate, inputs['compiler'], script, expected_format='alone')
        report['strict_pure_decodes'] = 2
        source_pins()
        report.update(complete=True, compression=inputs['compression'], whole_bytes=len(whole), whole_sha256=sha(whole),
                      whole_path=str(out/'x'), payload_bytes=len(payload), prefix_bytes=len(prefix),
                      bootstrap_bytes=len(script), bootstrap_sha256=sha(script), source_literal_kind=kind,
                      baseline_whole_bytes=len(baseline['x']), whole_delta=len(whole)-len(baseline['x']),
                      disposition='gain; root qualification decision required' if len(whole)<len(baseline['x']) else 'no gain; stop',
                      runtime_qualified=False, under_4096_bytes=len(whole)<=4096)
        save()
        print(json.dumps({k: report[k] for k in ('complete', 'native_bytes', 'native_sha256', 'old_native_full_bytes_equal',
                                                'whole_bytes', 'whole_sha256', 'whole_delta')}))
    except BaseException as error:
        report['complete'] = False
        report['error'] = {'type': type(error).__name__, 'message': str(error)}
        report['failure_policy'] = 'preserve and stop; no variant, sweep or retry'
        raise
    finally:
        save()


if __name__ == '__main__':
    main()
