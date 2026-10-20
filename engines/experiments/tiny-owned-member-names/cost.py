#!/usr/bin/env python3
"""Later bounded cost of the frozen FINAL4 candidate: one native, one ALONE."""
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
INPUTS_SHA = 'fa2b904c6272525177b407b875384b8d8cb9b555e6b33713649b38aab87ab7a9'


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
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    need(sys.platform == 'linux' and args.out.is_absolute() and not out.exists() and
         not any((p/'.git').exists() for p in (out, *out.parents)), 'new Linux output outside Git required')
    out.mkdir(parents=True)
    report = {'complete': False, 'scope': 'one exact-field F native and one fixed ALONE whole cost',
              'native_compile_attempts': 0, 'native_compiles_completed': 0, 'baseline_compiles': 0,
              'candidate_codec_compressions': 0, 'baseline_codec_compressions': 0, 'strict_pure_decodes': 0,
              'engine_executions': 0, 'bootstrap_executions': 0, 'normal_builder_main_calls': 0,
              'control_source_or_artifact_copies': 0, 'native_metadata_exceptions': False,
              'candidate_input_path': str(args.candidate.resolve()), 'baseline_path': str(args.baseline.resolve()),
              'environment': 'unchanged inherited environment, exactly as normal compile_c; no values serialized',
              'cwd_mode': 'normal compile_c private native directory and relative -o x in new external output',
              'historical_FINAL4': 'unchanged earlier source-only checkpoint; this is the separate later cost'}

    def save():
        (out/'cost.json').write_text(json.dumps(report, indent=2)+'\n')

    save()
    try:
        raw_inputs = (HERE/'cost-inputs.json').read_bytes()
        need(sha(raw_inputs) == INPUTS_SHA, 'fixed cost inputs differ')
        inputs = json.loads(raw_inputs)

        def check_source_inputs():
            for name, pin in inputs['source4_sha256'].items():
                need(sha((HERE/name).read_bytes()) == pin, 'frozen FINAL4 source differs: '+name)
            for name, pin in inputs['helper_sha256'].items():
                need(sha((REPO/name).read_bytes()) == pin, 'normal F/helper source differs: '+name)

        check_source_inputs()
        candidate = args.candidate.read_bytes()
        need(len(candidate) == inputs['candidate']['bytes'] and sha(candidate) == inputs['candidate']['sha256'], 'exact 9954 candidate required')
        baseline = {}
        for name, expected in inputs['baseline'].items():
            data = (args.baseline/name).read_bytes()
            need(len(data) == expected['bytes'] and sha(data) == expected['sha256'], 'existing baseline differs: '+name)
            baseline[name] = data
        need(json.loads(baseline['build.json'])['complete'], 'baseline normal receipt incomplete')
        build = module('unchanged_normal_F_build', REPO/'engines/compact/tiny-entry-f/build.py')
        literal = module('unchanged_source_literal', REPO/'engines/compact/tiny-a/pack_stream.py').source_literal
        decode = module('unchanged_strict_decode', REPO/'engines/experiments/tiny-source-codec/decode.py').verify
        recipe = json.loads((REPO/'engines/compact/tiny-entry-f/recipe.json').read_bytes())
        need(recipe['compiler'] == inputs['compiler'] and recipe['compression'] == inputs['compression'], 'normal compiler or codec differs')
        template = (REPO/'engines/compact/tiny-entry-f/bootstrap.py.in').read_bytes()
        prefix = (REPO/'engines/compact/tiny-entry-f/launcher.sh').read_bytes()
        marker = b'__ROVE_SOURCE_LITERAL__'
        need(template.count(marker) == 1 and len(prefix) == 77, 'normal bootstrap/prefix geometry differs')

        def bootstrap(source):
            expression, kind = literal(source)
            script = template.replace(marker, expression.encode())
            ast.parse(script)
            return script, kind

        original_script, _ = bootstrap(baseline['main.c'])
        need(original_script == baseline['bootstrap.py'], 'recovered original bootstrap differs')
        report['baseline_decode'] = decode(baseline['x'], prefix, baseline['main.c'], inputs['compiler'],
                                           original_script, expected_format='alone')
        report['strict_pure_decodes'] += 1
        report.update(cost_inputs_sha256=sha(raw_inputs), helper_sha256=inputs['helper_sha256'],
                      baseline_reused_not_rebuilt=inputs['baseline'], candidate_source_bytes=len(candidate),
                      candidate_source_sha256=sha(candidate), compiler=inputs['compiler'], compression=inputs['compression'])
        report['native_compile_attempts'] = 1
        report['native_cwd'] = str(out/'native')
        save()
        # The existing normal F function performs exactly one stdin compilation,
        # inherits the environment and writes compiler.stderr in this directory.
        native = build.compile_c(inputs['compiler'], candidate, out/'native')
        report['native_compiles_completed'] = 1
        report.update(native_bytes=len(native), native_sha256=sha(native), native_path=str(out/'native/x'),
                      compiler_stderr_sha256=sha((out/'native/compiler.stderr').read_bytes()))
        need(native == baseline['native/x'], 'full original native bytes differ; no metadata exception permitted')
        report['full_old_native_bytes_equal'] = True
        save()
        script, kind = bootstrap(candidate)
        report['candidate_codec_compressions'] = 1
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
        report['strict_pure_decodes'] += 1
        check_source_inputs()
        report.update(complete=True, whole_bytes=len(whole), whole_sha256=sha(whole), whole_path=str(out/'x'),
                      bootstrap_bytes=len(script), bootstrap_sha256=sha(script), bootstrap_path=str(out/'bootstrap.py'),
                      source_literal_kind=kind, payload_bytes=len(payload), prefix_bytes=len(prefix),
                      baseline_whole_bytes=len(baseline['x']), whole_delta=len(whole)-len(baseline['x']),
                      whole_gain=len(baseline['x'])-len(whole),
                      disposition='gain; root decides any normal promotion' if len(whole)<len(baseline['x']) else 'no gain; stop',
                      compiler_helper_returned=True, compiler_descendant_group_absence='not observed by unchanged normal helper',
                      runtime_qualification=False, under_4096_bytes=len(whole)<=4096)
        save()
        print(json.dumps({k: report[k] for k in ('complete', 'native_bytes', 'native_sha256', 'full_old_native_bytes_equal',
                                                'whole_bytes', 'whole_sha256', 'whole_delta', 'bootstrap_sha256')}))
    except BaseException as error:
        report['complete'] = False
        report['error'] = {'type': type(error).__name__, 'message': str(error)}
        report['failure_policy'] = 'preserve and stop; no alias/flag/codec variant or retry'
        raise
    finally:
        save()


if __name__ == '__main__':
    main()
