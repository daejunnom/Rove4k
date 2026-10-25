#!/usr/bin/env python3
"""One fixed incoming-move SEE composition; native1/ALONE1, no target run."""
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


def info(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


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
    args = parser.parse_args()
    out = args.out.resolve()
    need(args.out.is_absolute() and not out.exists() and not any((p/'.git').exists() for p in (out, *out.parents)), 'fresh absolute non-Git output required')
    recipe_raw = (HERE/'recipe.json').read_bytes()
    recipe = json.loads(recipe_raw)
    base = Path(recipe['baseline'])

    def check_inputs():
        for relative, pin in recipe['owned_executable_pins'].items():
            need(info((HERE/relative).read_bytes()) == pin, 'owned executable changed: '+relative)
        for relative, pin in recipe['normal_input_pins'].items():
            need(info((base/relative).read_bytes()) == pin, 'normal input changed: '+relative)
        need(info((REPO/recipe['canonical']).read_bytes()) == recipe['canonical_pin'], 'canonical changed')

    check_inputs()
    normal = json.loads((base/'inputs/recipe.json').read_bytes())
    need(normal['compiler'] == recipe['compiler'] and normal['compression'] == recipe['compression'] and normal['profile'] == recipe['profile'], 'fixed normal compiler/codec/profile differs')
    need(json.loads((base/'build.json').read_bytes())['complete'], 'control receipt incomplete')
    out.mkdir(parents=True)
    report = {'complete': False, 'scope': 'one fixed exact SEE composition first cost',
        'producer': info(Path(__file__).read_bytes()), 'recipe': info(recipe_raw),
        'control_inputs_reused_read_only': recipe['normal_input_pins'],
        'canonical_pin': recipe['canonical_pin'], 'compiler': recipe['compiler'],
        'profile': recipe['profile'], 'compression': recipe['compression'],
        'control_compile': 0, 'control_copy': 0, 'candidate_compile': 0, 'candidate_ALONE': 0,
        'strict_pure_decodes': 0, 'AST': 0, 'CPP': 0, 'bootstrap_execution': 0, 'engine_execution': 0,
        'game_benchmark': 0, 'sweep_retry': 0, 'runtime_qualified': False, 'repeat_claim': False,
        'normal_promotion': False, 'metadata_exception_applied': False}

    def save():
        (out/'cost.json').write_text(json.dumps(report, indent=2)+'\n')

    save()
    try:
        source = (base/'main.c').read_bytes()
        transform = module('fixed_incoming_transform', HERE/'transform.py').transform
        candidate, metadata = transform(source, (REPO/recipe['canonical']).read_bytes(), recipe['fragment_domain'])
        need(info(candidate) == recipe['candidate'], 'sole candidate differs')
        report['transform'] = metadata
        report['source'] = info(candidate)
        (out/'main.c').write_bytes(candidate)
        literal = module('pinned_normal_literal', base/'inputs/pack_stream.py').source_literal
        old_literal, old_kind = literal(source)
        new_literal, new_kind = literal(candidate)
        need(old_kind == new_kind == 'raw-single' and old_literal == "r'''"+source.decode()+"'''.encode()" and new_literal == "r'''"+candidate.decode()+"'''.encode()", 'fixed source-literal binding differs')
        old_script = (base/'bootstrap.py').read_bytes()
        need(old_script.count(old_literal.encode()) == 1, 'old bootstrap literal count differs')
        script = old_script.replace(old_literal.encode(), new_literal.encode(), 1)
        need(script.replace(new_literal.encode(), old_literal.encode(), 1) == old_script, 'bootstrap literal inverse failed')
        compiler_literal = ('subprocess.Popen('+repr(recipe['compiler'])+',').encode()
        need(old_script.count(compiler_literal) == script.count(compiler_literal) == 1, 'original literal compiler argv differs')
        old_whole = (base/'x').read_bytes()
        prefix = old_whole[:77]

        def decode(whole, expected):
            need(whole[:77] == prefix and len(prefix) == 77, 'fixed prefix differs')
            dec = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
            need(dec.decompress(whole[77:], max_length=len(expected)+1) == expected and dec.eof and not dec.unused_data and dec.check == lzma.CHECK_NONE, 'strict sole ALONE decode differs')
            report['strict_pure_decodes'] += 1

        decode(old_whole, old_script)
        build = module('pinned_normal_compile', base/'inputs/build.py')
        report['candidate_compile'] = 1
        report['native_private_cwd'] = str(out/'native')
        report['compiler_stdin'] = info(candidate)
        save()
        native = build.compile_c(recipe['compiler'], candidate, out/'native')
        old_native = (base/'native/x').read_bytes()
        report.update(native=info(native), full_old_native_equal=native == old_native,
            first_native_difference=next((i for i,(a,b) in enumerate(zip(native, old_native)) if a != b), None))
        report['candidate_ALONE'] = 1
        save()
        payload = lzma.compress(script,format=lzma.FORMAT_ALONE,check=lzma.CHECK_NONE,
            filters=[{'id':lzma.FILTER_LZMA1,'preset':9|lzma.PRESET_EXTREME,'lc':2,'lp':0,'pb':0,
                      'mf':lzma.MF_BT4,'dict_size':67108864,'nice_len':32}])
        need(payload[:13] == old_whole[77:90] == bytes.fromhex('0200000004ffffffffffffffff'), 'fixed ALONE header differs')
        whole = prefix+payload
        decode(whole, script)
        (out/'bootstrap.py').write_bytes(script)
        (out/'x').write_bytes(whole)
        check_inputs()
        delta = len(whole)-len(old_whole)
        report.update(complete=True, bootstrap=info(script), whole=info(whole), whole_delta=delta,
            disposition='positive; report before functional' if delta < 0 else 'tie/loss; stop',
            argv_source_literal_exact=True, bootstrap_literal_inverse=True, live_command_handles=0)
        save()
        print(json.dumps({k:report[k] for k in ('complete','source','native','full_old_native_equal','whole','whole_delta','disposition')}), flush=True)
    except BaseException as error:
        report['failure'] = repr(error)
        save()
        raise


if __name__ == '__main__':
    main()
