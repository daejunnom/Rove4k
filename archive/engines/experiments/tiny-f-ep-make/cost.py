#!/usr/bin/env python3
"""One exact shipping F structural candidate, one native and one fixed ALONE."""
import argparse
import hashlib
import importlib.util
import json
import lzma
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OWNED = ('.gitattributes', 'inputs.json', 'transform.py', 'cost.py', 'README.md')


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
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--review', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    need(sys.platform == 'linux' and args.out.is_absolute() and not out.exists() and
         not any((p/'.git').exists() for p in (out, *out.parents)), 'new Linux output outside Git required')
    out.mkdir(parents=True)
    report = {'complete': False, 'scope': 'one F EP-to-make first cost; no target execution',
              'candidate_native_attempts': 0, 'candidate_native_completed': 0,
              'candidate_compressions': 0, 'control_compiles': 0, 'control_copies': 0,
              'AST_parses': 0, 'PP': 0, 'DEV': 0, 'engine': 0, 'bootstrap_runs': 0,
              'strict_pure_decodes': 0, 'normal_builder_main_calls': 0,
              'old_native_equality_required': False, 'runtime_qualified': False}

    def save():
        (out/'cost.json').write_text(json.dumps(report, indent=2)+'\n')

    save()
    try:
        review_bytes = args.review.read_bytes()
        review = json.loads(review_bytes)
        need(review['approved'] is True and set(review['owned_sha256']) == set(OWNED),
             'exact independent source review required')
        inputs = json.loads((HERE/'inputs.json').read_bytes())

        def check_inputs():
            for name, pin in review['owned_sha256'].items():
                need(sha((HERE/name).read_bytes()) == pin, 'reviewed source differs: '+name)
            for name, pin in inputs['helper_sha256'].items():
                need(sha((REPO/name).read_bytes()) == pin, 'pinned normal input differs: '+name)

        check_inputs()
        baseline_directory = Path(inputs['baseline_directory'])
        baseline = {}
        for name, expected in inputs['baseline'].items():
            data = (baseline_directory/name).read_bytes()
            need(len(data) == expected['bytes'] and sha(data) == expected['sha256'],
                 'pinned existing control differs: '+name)
            baseline[name] = data
        need(json.loads(baseline['build.json'])['complete'], 'existing control receipt incomplete')
        recipe = json.loads((REPO/'engines/compact/tiny-entry-f/recipe.json').read_bytes())
        need(recipe['compiler'] == inputs['compiler'] and recipe['compression'] == inputs['compression'],
             'current compiler/codec differs')
        need(recipe['profile'] == {'workers': 2, 'tt_bits': 18, 'ply': 128, 'dev_default': False},
             'resource profile differs')
        transform = module('owned_ep_make_transform', HERE/'transform.py').transform
        candidate, metadata = transform(baseline['main.c'], (REPO/'engines/compact/tiny-entry-f/engine.c').read_bytes())
        need(len(candidate) == inputs['candidate']['bytes'] and sha(candidate) == inputs['candidate']['sha256'],
             'candidate literal identity differs')
        (out/'main.c').write_bytes(candidate)
        report.update(review_sha256=sha(review_bytes), owned_sha256=review['owned_sha256'],
                      helper_sha256=inputs['helper_sha256'], baseline_reused_not_rebuilt=inputs['baseline'],
                      transform=metadata, source_bytes=len(candidate), source_sha256=sha(candidate),
                      compiler=inputs['compiler'], compression=inputs['compression'],
                      environment='unaltered inherited environment; no values serialized',
                      native_cwd=str(out/'native'), compiler_input='exact candidate bytes on stdin',
                      native_output='relative -o x in new private cwd')
        template = (REPO/'engines/compact/tiny-entry-f/bootstrap.py.in').read_bytes()
        prefix = (REPO/'engines/compact/tiny-entry-f/launcher.sh').read_bytes()
        literal = module('pinned_normal_source_literal', REPO/'engines/compact/tiny-a/pack_stream.py').source_literal
        build = module('pinned_normal_compile_function', REPO/'engines/compact/tiny-entry-f/build.py')
        marker = b'__ROVE_SOURCE_LITERAL__'
        need(template.count(marker) == 1 and len(prefix) == 77, 'bootstrap/prefix geometry differs')

        def script_for(source):
            expression, kind = literal(source)
            need(kind == 'raw-single' and expression ==
                 "r'''" + source.decode() + "'''.encode()", 'fixed known source-literal form differs')
            # No AST parse or bootstrap execution. Exact producer concatenation.
            return template.replace(marker, expression.encode()), kind

        def decode(whole, script):
            need(whole[:len(prefix)] == prefix, 'prefix differs')
            decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
            restored = decoder.decompress(whole[len(prefix):], max_length=len(script)+1)
            need(restored == script and decoder.eof and not decoder.unused_data,
                 'strict sole ALONE decode/exact bootstrap mismatch')
            report['strict_pure_decodes'] += 1

        baseline_script, _ = script_for(baseline['main.c'])
        need(baseline_script == baseline['bootstrap.py'], 'existing bootstrap differs from current exact template')
        decode(baseline['x'], baseline_script)
        report['candidate_native_attempts'] = 1
        save()
        native = build.compile_c(inputs['compiler'], candidate, out/'native')
        report['candidate_native_completed'] = 1
        report.update(native_bytes=len(native), native_sha256=sha(native),
                      full_old_native_equal=native == baseline['native/x'],
                      old_native_bytes=len(baseline['native/x']), old_native_sha256=sha(baseline['native/x']),
                      compiler_stderr_bytes=len((out/'native/compiler.stderr').read_bytes()),
                      compiler_stderr_sha256=sha((out/'native/compiler.stderr').read_bytes()),
                      compiler_helper_returned=True)
        save()
        script, kind = script_for(candidate)
        report['candidate_compressions'] = 1
        save()
        payload = lzma.compress(script, format=lzma.FORMAT_ALONE, check=lzma.CHECK_NONE,
                                filters=[{'id': lzma.FILTER_LZMA1, 'preset': 9|lzma.PRESET_EXTREME,
                                          'lc': 2, 'lp': 0, 'pb': 0, 'mf': lzma.MF_BT4,
                                          'dict_size': 67108864, 'nice_len': 32}])
        whole = prefix+payload
        (out/'bootstrap.py').write_bytes(script)
        (out/'x').write_bytes(whole)
        decode(whole, script)
        check_inputs()
        delta = len(whole)-len(baseline['x'])
        report.update(complete=True, bootstrap_bytes=len(script), bootstrap_sha256=sha(script),
                      source_literal_kind=kind, prefix_bytes=len(prefix), payload_bytes=len(payload),
                      whole_bytes=len(whole), whole_sha256=sha(whole),
                      baseline_whole_bytes=len(baseline['x']), whole_delta=delta, whole_gain=-delta,
                      disposition='gain; propose focused qualification to root' if delta < 0 else 'tie/loss; stop',
                      under_4096_bytes=len(whole) <= 4096,
                      compiler_descendant_group_absence='recorded separately by outer managed runner',
                      functional_evidence_inherited=False, normal_promotion=False)
        save()
        print(json.dumps({key: report[key] for key in
                         ('complete', 'source_bytes', 'source_sha256', 'native_bytes', 'native_sha256',
                          'full_old_native_equal', 'whole_bytes', 'whole_sha256', 'whole_delta')}), flush=True)
    except BaseException as error:
        report.update(complete=False, error={'type': type(error).__name__, 'message': str(error)},
                      failure_policy='preserve and stop; no variant, sweep or retry')
        raise
    finally:
        save()


if __name__ == '__main__':
    main()
