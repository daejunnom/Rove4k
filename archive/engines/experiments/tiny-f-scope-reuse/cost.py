"""One exact validated-best-so-far F alias cost; no producer or engine run."""
import argparse
import hashlib
import importlib.util
import json
import lzma
from pathlib import Path
import platform
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SOURCE4 = {
    '.gitattributes': 'a79691a93b46e49ce460c26ef22afcc03d6eca1e63bf2edbc20e96159510f6c9',
    'README.md': 'fbe0231122d38cde2aa3a72f0c3855d936ff4ce7ecab60087cc5f4de82cc2cb1',
    'inputs.json': '13bdfd750f2cafbc67bc46d1ae57f723ed8331eefb1d13ceaf84aba6e5e0061a',
    'reuse.py': '60c157b84f100a4691b1d4dc11f819519d947a63d2a7ebf273654b5059ba0b5f',
}
HELPERS = {
    'engines/compact/tiny-entry-f/build.py': 'b7a86aa2f773c68bba14e33489f11db06177698aa0bbe21d143e5b0855ce8a4f',
    'engines/compact/tiny-entry-f/recipe.json': 'a1b6926707576c70fcfb0218d206c1d4015ea4b39c0c582b25423754f9e88546',
    'engines/compact/tiny-entry-f/bootstrap.py.in': '84608782831299a6f7b1010dea89501eb10e6e34ee1cdc8f3804d448354cf4c6',
    'engines/compact/tiny-entry-f/launcher.sh': '78c5b572036e14ed33098fa4fb10fd10f4e061305e158f1609bae95d41e60301',
    'engines/compact/tiny-a/pack_stream.py': 'b4addefbb1233881e85707aa525ca4af7f8210d9d27f56fbb52e4440a966b99e',
    'engines/experiments/tiny-source-codec/decode.py': 'c43303b6524321b24dfba069afc9a135998e408503740ea8d9fbcfb9bb5e9f5a',
}
BASELINE = {
    'main.c': (9728, '845f731a0f1fabd62bae629ad191aadd39525d0db7d59628224e315f09c0519d'),
    'native/x': (18576, 'a0b1f736b25467957aa991775877a62639818c7464bfa984efc6240577fe66d1'),
    'bootstrap.py': (10727, '87724bc9e73df6dbb3da221bef0e1f4f0f8edc027206706084b5f373235e888e'),
    'x': (4735, '81e1d7129c2aedfe96d53d8e1fb6db8613b22b4c21dfcaf4d1c3ac25a7b1fc71'),
}
CANDIDATE = (9728, 'b4b39300f92d4769987c8f14303623a0812c95729e052063e76d82271b4444da')
COMPILER = ['cc', '-Os', '-pthread', '-x', 'c', '-', '-o', 'x', '-s']
COMPRESSION = {'format': 'lzma-alone', 'filter': 'LZMA1', 'preset': 9, 'extreme': True,
               'lc': 2, 'lp': 0, 'pb': 0, 'check': 'NONE', 'mf': 'BT4',
               'dictionary_bytes': 67108864, 'nice_len': 32}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def need(test, message):
    if not test:
        raise ValueError(message)


def module(name, path, raw):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    exec(compile(raw, str(path), 'exec'), result.__dict__)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    need(platform.system() == 'Linux' and platform.machine() == 'x86_64' and args.out.is_absolute() and
         not out.exists() and not any((p/'.git').exists() for p in (out, *out.parents)), 'new Linux output outside Git required')
    out.mkdir(parents=True)
    report = {'complete': False, 'scope': 'one fixed F source alias cost; validated best-so-far only',
              'source_greedy_complete': False, 'source_declarations_done': 102, 'source_declarations_eligible': 169,
              'native_compile_attempts': 0, 'native_compiles_completed': 0, 'candidate_codec_compressions': 0,
              'baseline_compiles': 0, 'baseline_codec_compressions': 0, 'baseline_copies': 0,
              'pure_strict_decodes': 0, 'C_AST_PP_DEV_engine_wrapper_normal_game_benchmark_executions': 0,
              'native_metadata_exceptions': False, 'source4_frozen': SOURCE4, 'helper_pins': HELPERS,
              'compiler': COMPILER, 'compression': COMPRESSION,
              'environment': 'unchanged inherited environment; values not serialized',
              'cwd': 'new private external native directory, same normal stdin compile helper'}
    def save():
        (out/'cost.json').write_text(json.dumps(report, indent=2)+'\n')
    save()
    try:
        def owned_inputs():
            for name, pin in SOURCE4.items():
                need(sha((HERE/name).read_bytes()) == pin, 'frozen source4 changed: '+name)
            result = {}
            for name, pin in HELPERS.items():
                raw = (args.repo/name).read_bytes()
                need(sha(raw) == pin, 'actual normal F/helper changed: '+name)
                result[name] = raw
            return result
        helper = owned_inputs()
        source = args.candidate.read_bytes()
        need((len(source), sha(source)) == CANDIDATE, 'only exact validated v2 best-so-far admitted')
        baseline = {}
        for name, pin in BASELINE.items():
            raw = (args.baseline/name).read_bytes()
            need((len(raw), sha(raw)) == pin, 'actual baseline artifact changed: '+name)
            baseline[name] = raw
        recipe = json.loads(helper['engines/compact/tiny-entry-f/recipe.json'])
        need(recipe['compiler'] == COMPILER and recipe['compression'] == COMPRESSION and
             recipe['profile'] == {'workers': 2, 'tt_bits': 18, 'ply': 128, 'dev_default': False}, 'actual normal F profile/argv/codec changed')
        def imported(name, relative):
            return module(name, args.repo/relative, helper[relative])
        build = imported('fixed_normal_F_compile_helper', 'engines/compact/tiny-entry-f/build.py')
        literal = imported('fixed_source_literal', 'engines/compact/tiny-a/pack_stream.py').source_literal
        decode = imported('fixed_strict_decoder', 'engines/experiments/tiny-source-codec/decode.py').verify
        template = helper['engines/compact/tiny-entry-f/bootstrap.py.in']
        prefix = helper['engines/compact/tiny-entry-f/launcher.sh']
        marker = b'__ROVE_SOURCE_LITERAL__'
        need(template.count(marker) == 1 and len(prefix) == 77, 'normal source marker/prefix changed')
        def bootstrap(raw):
            expression, kind = literal(raw)
            return template.replace(marker, expression.encode()), kind
        oldscript, _ = bootstrap(baseline['main.c'])
        need(oldscript == baseline['bootstrap.py'], 'literal/template inverse differs from actual baseline bootstrap')
        report['baseline_decode'] = decode(baseline['x'], prefix, baseline['main.c'], COMPILER, oldscript, expected_format='alone')
        report['pure_strict_decodes'] += 1
        report.update(candidate_input_path=str(args.candidate.resolve()), baseline_path=str(args.baseline.resolve()),
                      candidate_source_bytes=len(source), candidate_source_sha256=sha(source),
                      baseline_reused_read_only={name: {'bytes': pin[0], 'sha256': pin[1]} for name, pin in BASELINE.items()})
        (out/'main.c').write_bytes(source)
        report['native_compile_attempts'] = 1
        save()
        # Exactly one unchanged normal helper call: stdin bytes/private cwd/env/argv.
        native = build.compile_c(COMPILER, source, out/'native')
        report.update(native_compiles_completed=1, native_bytes=len(native), native_sha256=sha(native),
                      native_path=str(out/'native/x'), compiler_stderr_sha256=sha((out/'native/compiler.stderr').read_bytes()))
        save()
        need(native == baseline['native/x'], 'full baseline native differs; stop before codec; no metadata exceptions')
        report['full_old_native_bytes_equal'] = True
        script, kind = bootstrap(source)
        report['candidate_codec_compressions'] = 1
        save()
        payload = lzma.compress(script, format=lzma.FORMAT_ALONE, check=lzma.CHECK_NONE,
            filters=[{'id': lzma.FILTER_LZMA1, 'preset': 9|lzma.PRESET_EXTREME, 'lc': 2, 'lp': 0, 'pb': 0,
                      'mf': lzma.MF_BT4, 'dict_size': 67108864, 'nice_len': 32}])
        whole = prefix+payload
        (out/'bootstrap.py').write_bytes(script)
        (out/'x').write_bytes(whole)
        (out/'x').chmod(0o755)
        report['candidate_decode'] = decode(whole, prefix, source, COMPILER, script, expected_format='alone')
        report['pure_strict_decodes'] += 1
        owned_inputs()
        need(all((len((args.baseline/name).read_bytes()), sha((args.baseline/name).read_bytes())) == pin
                 for name, pin in BASELINE.items()), 'actual baseline changed during cost')
        report.update(complete=True, whole_bytes=len(whole), whole_sha256=sha(whole), whole_path=str(out/'x'),
                      bootstrap_bytes=len(script), bootstrap_sha256=sha(script), bootstrap_path=str(out/'bootstrap.py'),
                      source_literal_kind=kind, prefix_bytes=len(prefix), payload_bytes=len(payload),
                      baseline_whole_bytes=len(baseline['x']), whole_delta=len(whole)-len(baseline['x']),
                      actual_whole_gain=len(baseline['x'])-len(whole),
                      disposition='gain; root decides next step' if len(whole)<len(baseline['x']) else 'tie/loss; stop',
                      compiler_helper_returned=True, compiler_descendant_group_absence='not observed by unchanged helper',
                      source4_unchanged=True, baseline4_unchanged=True, runtime_qualification=False,
                      under_4096_bytes=len(whole)<=4096)
        print(json.dumps({k: report[k] for k in ('complete', 'native_bytes', 'native_sha256', 'full_old_native_bytes_equal',
              'whole_bytes', 'whole_sha256', 'whole_delta', 'bootstrap_sha256')}))
    except BaseException as error:
        report.update(complete=False, error={'type': type(error).__name__, 'message': str(error)},
                      failure_policy='preserve and stop; no variant, retry or metadata exception')
        raise
    finally:
        save()


if __name__ == '__main__':
    main()
