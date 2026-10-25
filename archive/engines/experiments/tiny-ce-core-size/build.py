#!/usr/bin/env python3
"""One C/E old/new core-size cost pair at the unchanged maintained recipes."""
import argparse
import ast
import hashlib
import importlib.util
import json
import lzma
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PINS_SHA = '8204096c59a1e7367aa5ef683402aafd5f065181716e5eccf485bf09ced7a7a3'
DOMAIN_SHA = 'f9a6414be782a8ed7393bea18039dd462f087f327dd2e456b8e3bd98d42e2d15'
SHARED_POLICY = 'b3f08ba26b38dbce1e4b63d3eb98ab37f438295cfacff6037b1cfacbf7d5e5a0'


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


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n')


def normalize(data):
    data = data.replace(b'\r\n', b'\n')
    require(b'\r' not in data, 'lone CR in ordinary source')
    return data


def pinned_inputs(base, pins):
    for name, expected in pins['files'].items():
        require(name.startswith('engines/') and '..' not in Path(name).parts, 'unsafe ordinary input path')
        require(info(normalize((base/name).read_bytes())) == {k: expected[k] for k in ('bytes', 'sha256')}, 'tracked input changed: '+name)


def mapped(source, readable, reference, lexer):
    require(sha(reference._POLICY_BYTES) == SHARED_POLICY, 'shared original89 policy changed')
    policy = json.loads(reference._POLICY_BYTES)
    mapping, resources = policy['mapping'], policy['resource_literals']
    require(len(mapping) == len(set(mapping.values())) == 89 and resources == {'WORKERS': '2', 'TT_BITS': '18'}, 'original map/resources changed')
    require(not set(mapping) & set(policy['symbol_bearing_spellings_retained']) and 'PLY' not in mapping and 'PLY' not in resources,
            'protected spelling/resource boundary changed')
    words = set(reference._WORD.findall(readable.decode())) | set(reference._WORD.findall(reference._logical(readable.decode())[0]))
    require(not set(mapping.values()) & words, 'alias capture in exact new readable')
    candidate, counts, opaque = reference._rewrite(source, {**mapping, **resources}, lexer=lexer)
    ply = sum(token == 'PLY' for _, _, token in lexer._identifier_spans(source.decode()))
    require(sum(token == 'PLY' for _, _, token in lexer._identifier_spans(candidate.decode())) == ply, 'PLY use changed')
    return candidate, {'source': info(source), 'candidate': info(candidate), 'readable': info(readable),
        'alpha_counts': {name: counts[name] for name in mapping}, 'resource_counts': {name: counts[name] for name in resources},
        'mapping_used': sum(counts[name] > 0 for name in mapping), 'source_edits_count': sum(counts.values()),
        'alpha_saved_bytes': sum((len(name)-len(alias))*counts[name] for name, alias in mapping.items()),
        'resource_saved_bytes': sum((len(name)-len(alias))*counts[name] for name, alias in resources.items()),
        'source_saved_bytes': len(source)-len(candidate), 'opaque_regions_preserved': len(opaque),
        'retained_directive_bytes': sum(len(text.encode()) for kind, text in opaque if kind == 'directive'),
        'retained_PLY_code_uses': ply, 'all_original89_aliases_reserved': True, 'numeric_inverse_replacements': 0}


def pp_checks(before, after, directory, recipe, reference, lexer):
    directory.mkdir()
    mapping = json.loads(reference._POLICY_BYTES)['mapping']
    inverse = {alias: name for name, alias in mapping.items()}
    outputs, commands = {}, []
    for label, source in (('before', before), ('after', after)):
        for kind, flags in (('pp', ['-E', '-P']), ('macros', ['-E', '-dM'])):
            command = recipe['preprocessor']+['-DDEV=0', *flags, '-x', 'c', '-']
            process = subprocess.run(command, input=source, capture_output=True, timeout=30)
            (directory/(label+'.'+kind)).write_bytes(process.stdout)
            (directory/(label+'.'+kind+'.stderr')).write_bytes(process.stderr)
            commands.append({'argv': command, 'returncode': process.returncode, 'output': info(process.stdout), 'stderr': info(process.stderr)})
            write_json(directory/'commands.json', commands)
            require(process.returncode == 0 and not process.stderr, 'actual PP/macro command failed')
            outputs[label, kind] = process.stdout
    conflicts = {kind: sorted(set(inverse) & set(reference._WORD.findall(outputs['before', kind].decode()))) for kind in ('pp', 'macros')}
    require(not any(conflicts.values()), 'alias conflicts in actual PP/header/macro environment')
    text, parts, offset = outputs['after', 'pp'].decode(), [], 0
    for start, end, word in lexer._identifier_spans(text):
        if word in inverse:
            parts.extend((text[offset:start], inverse[word]))
            offset = end
    restored = ''.join(parts+[text[offset:]]).encode()
    (directory/'inverse.pp').write_bytes(restored)
    require(restored == outputs['before', 'pp'], 'actual raw PP inverse differs')
    macro_before = outputs['before', 'macros'].splitlines()
    macro_after = outputs['after', 'macros'].splitlines()
    require(sorted(macro_before) == sorted(macro_after), 'full actual macro definitions changed')
    result = {'complete': True, 'actual_raw_PP_inverse_exact': True, 'actual_macro_definitions_identical': True,
        'actual_raw_macro_dump_byte_equal': outputs['before', 'macros'] == outputs['after', 'macros'],
        'macro_comparison': 'sorted complete definition lines, including multiplicity; GCC dump iteration order is not a definition',
        'macro_definition_lines': len(macro_before),
        'all89_alias_PP_header_macro_conflicts': conflicts, 'numeric_inverse_replacements': 0,
        'inverse_sha256': sha(restored), 'commands': commands, 'native_compilations': 0, 'engine_runs': 0}
    write_json(directory/'checks.json', result)
    return result


def prepare(out, pins):
    report = {'complete': False, 'input_pins_sha256': PINS_SHA, 'families': {}, 'native_compilations': 0, 'engine_runs': 0}
    def save():
        write_json(out/'prepare.json', report)
    save()
    try:
        pinned_inputs(REPO, pins)
        frozen = out/'inputs'
        for name in pins['files']:
            target = frozen/name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(normalize((REPO/name).read_bytes()))
        for name in ('transform.py', 'checks.py', 'input-pins.json', 'build.py'):
            (out/name).write_bytes((HERE/name).read_bytes())
        report['pure_checks'] = load('ce_pure_checks', out/'checks.py').run()
        transform = load('ce_exact_transform', out/'transform.py').transform
        specialize = load('ce_specialize', frozen/'engines/scripts/specialize.py').specialize_c
        compact = load('ce_compact', frozen/'engines/scripts/minify.py').compact_source
        strip = load('ce_counter_strip', frozen/'engines/compact/tiny-a/stitch.py').strip_dev_counters
        reference = load('ce_original_reference', frozen/'engines/scripts/fixed_shipping_alpha.py')
        lexer = load('ce_original_lexer', frozen/'engines/scripts/rename_c.py')
        domain = {'format': 1, 'original_policy_sha256': SHARED_POLICY, 'scope': 'sole C/E three-decision core composition; unchanged original89 maps/resources', 'families': {}}
        for family in ('C', 'E'):
            entry = frozen/pins['families'][family]['entry']
            recipe = json.loads((entry/'recipe.json').read_bytes())
            readable = (entry/'engine.c').read_bytes()
            candidate, mutation = transform(readable, family)
            public = load('ce_local_'+family, entry/'shipping_alpha.py') if family == 'C' else reference
            rows = {}
            for variant, raw in (('old', readable), ('new', candidate)):
                directory = out/family/variant
                directory.mkdir(parents=True)
                (directory/'readable.c').write_bytes(raw)
                active, observations = specialize({'main.c': raw}, directory/'preprocess', recipe['preprocessor']+['-DDEV=0'], os.environ.copy())
                source, stripped = strip(compact(active['main.c'], 'c'))
                (directory/'pre-alpha.c').write_bytes(source)
                kwargs = {'family': family, 'lexer': lexer}
                if family == 'C':
                    kwargs.update(reference=reference, readable=raw)
                if variant == 'old':
                    result, meta = public.transform_source(source, **kwargs)
                    require(info(result) == {'bytes': recipe['expected']['source_bytes'], 'sha256': recipe['expected']['source_sha256']}, 'current old shipping pin differs')
                else:
                    try:
                        public.transform_source(source, **kwargs)
                    except ValueError as error:
                        rejected = str(error)
                    else:
                        raise ValueError('original public domain unexpectedly admitted changed source')
                    result, meta = mapped(source, raw, reference, lexer)
                    domain['families'][family] = meta
                    rows['original_public_policy_rejection'] = rejected
                    rows['actual_PP_checks'] = pp_checks(source, result, directory/'raw-pp', recipe, reference, lexer)
                (directory/'main.c').write_bytes(result)
                write_json(directory/'source.json', {'specialization': observations, 'counter_strip': stripped, 'alpha': meta})
                rows[variant] = {'readable': info(raw), 'shipping': info(result)}
            rows['source_change'] = mutation
            report['families'][family] = rows
            save()
        write_json(out/'candidate-domain-proposal.json', domain)
        report.update(complete=True, domain_proposal_sha256=sha((out/'candidate-domain-proposal.json').read_bytes()),
            whole_packages=0, pre_alpha_native_compilations=0)
        save()
        print(json.dumps({'complete': True, 'phase': 'source preparation only', 'domain_sha256': report['domain_proposal_sha256'],
            'source_bytes': {family: row['new']['shipping']['bytes'] for family, row in report['families'].items()}, 'native_compilations': 0}))
    except BaseException as error:
        report['failure'] = repr(error)
        save()
        raise


def cost(out, prepared, pins):
    report = {'complete': False, 'scope': 'one old/new cost pair per family; no repeat or runtime claim',
        'input_pins_sha256': PINS_SHA, 'literal_domain_sha256': DOMAIN_SHA, 'families': {},
        'native_compilations': 0, 'whole_packages': 0, 'pre_alpha_native_compilations': 0,
        'engine_runs': 0, 'runtime_qualified': False, 'new_codec_or_name_trials': 0}
    def save():
        write_json(out/'cost.json', report)
    save()
    try:
        pinned_inputs(REPO, pins)
        pinned_inputs(prepared/'inputs', pins)
        preparation = json.loads((prepared/'prepare.json').read_bytes())
        require(preparation['complete'] and preparation['input_pins_sha256'] == PINS_SHA, 'source preparation incomplete')
        domain_raw = (HERE/'candidate-domain.json').read_bytes()
        require(sha(domain_raw) == DOMAIN_SHA == preparation['domain_proposal_sha256'], 'new literal domain identity changed')
        require(domain_raw == (prepared/'candidate-domain-proposal.json').read_bytes(), 'literal source/count domain differs')
        domain = json.loads(domain_raw)
        require(domain['original_policy_sha256'] == SHARED_POLICY, 'original policy drift')
        for name in ('transform.py', 'checks.py', 'input-pins.json'):
            require((HERE/name).read_bytes() == (prepared/name).read_bytes(), 'source producer changed since preparation')
        producer = out/'producer-source'
        shutil.copytree(HERE, producer)
        report['producer_files'] = {p.relative_to(producer).as_posix(): info(p.read_bytes()) for p in sorted(producer.rglob('*')) if p.is_file()}
        frozen = prepared/'inputs'
        reference = load('ce_cost_reference', frozen/'engines/scripts/fixed_shipping_alpha.py')
        lexer = load('ce_cost_lexer', frozen/'engines/scripts/rename_c.py')
        literal = load('ce_cost_literal', frozen/'engines/compact/tiny-a/pack_stream.py').source_literal
        transform = load('ce_cost_transform', producer/'transform.py').transform
        for family in ('C', 'E'):
            entry = frozen/pins['families'][family]['entry']
            recipe = json.loads((entry/'recipe.json').read_bytes())
            require(recipe['compiler'] == pins['families'][family]['compiler'] and recipe['compression'] == pins['families'][family]['compression'], 'fixed recipe changed')
            require(recipe['compression'] == {'format': 'xz', 'filter': 'LZMA2', 'preset': 9, 'extreme': True, 'lc': 3, 'lp': 0, 'pb': 2, 'check': 'CRC64'}, 'original codec differs')
            expected = recipe['expected']
            raw = (entry/'engine.c').read_bytes()
            candidate, mutation = transform(raw, family)
            require(raw == (prepared/family/'old/readable.c').read_bytes() and candidate == (prepared/family/'new/readable.c').read_bytes(), 'prepared readable changed')
            new_pre = (prepared/family/'new/pre-alpha.c').read_bytes()
            mapped_new, metadata = mapped(new_pre, candidate, reference, lexer)
            require(metadata == domain['families'][family], 'literal candidate counts/arithmetic/bytes differ')
            require(mapped_new == (prepared/family/'new/main.c').read_bytes(), 'prepared candidate shipping changed')
            public = load('ce_cost_local_'+family, entry/'shipping_alpha.py') if family == 'C' else reference
            kwargs = {'family': family, 'lexer': lexer}
            if family == 'C':
                kwargs.update(reference=reference, readable=raw)
            old_source, _ = public.transform_source((prepared/family/'old/pre-alpha.c').read_bytes(), **kwargs)
            require(old_source == (prepared/family/'old/main.c').read_bytes(), 'prepared control shipping changed')
            compile_c = load('ce_cost_builder_'+family, entry/'build.py').compile_c
            template, prefix = (entry/'bootstrap.py.in').read_bytes(), (entry/'launcher.sh').read_bytes()
            require(len(prefix) == 75 and template.count(b'__ROVE_SOURCE_LITERAL__') == 1, 'unchanged prefix/bootstrap shape differs')
            family_rows, natives = {}, {}
            report['families'][family] = {'source_change': mutation, 'artifacts': family_rows}
            for variant, source in (('old', old_source), ('new', mapped_new)):
                directory = out/family/variant
                directory.mkdir(parents=True)
                (directory/'main.c').write_bytes(source)
                report['native_compilations'] += 1
                save()
                native = compile_c(recipe['compiler'], source, directory/'native')
                natives[variant] = native
                require(native[:6] == b'\x7fELF\x02\x01', 'native is not ELF64 little-endian')
                if variant == 'old':
                    require(info(source) == {'bytes': expected['source_bytes'], 'sha256': expected['source_sha256']} and
                            info(native) == {'bytes': expected['native_bytes'], 'sha256': expected['native_sha256']}, 'actual current control source/native pin differs')
                expression, _ = literal(source)
                script = template.replace(b'__ROVE_SOURCE_LITERAL__', expression.encode())
                ast.parse(script)
                payload = lzma.compress(script, format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64,
                    filters=[{'id': lzma.FILTER_LZMA2, 'preset': 9 | lzma.PRESET_EXTREME, 'lc': 3, 'lp': 0, 'pb': 2}])
                decoder = lzma.LZMADecompressor(format=lzma.FORMAT_XZ)
                require(decoder.decompress(payload) == script and decoder.eof and not decoder.unused_data and decoder.check == lzma.CHECK_CRC64, 'strict original-codec restoration failed')
                cli = subprocess.run(['xz', '-dc'], input=payload, capture_output=True, timeout=15)
                require(cli.returncode == 0 and not cli.stderr and cli.stdout == script, 'independent CLI restoration differs')
                whole = prefix+payload
                (directory/'x').write_bytes(whole)
                (directory/'x').chmod(0o755)
                (directory/'bootstrap.py').write_bytes(script)
                report['whole_packages'] += 1
                if variant == 'old':
                    require(info(whole) == {'bytes': expected['whole_bytes'], 'sha256': expected['whole_sha256']} and
                            sha(script) == expected['bootstrap_sha256'], 'actual current control whole/bootstrap pin differs')
                family_rows[variant] = {'source': info(source), 'native': info(native), 'whole': info(whole), 'bootstrap': info(script),
                    'compiler': recipe['compiler'], 'compression': recipe['compression'], 'strict_Python_and_CLI_decode': True}
                save()
            report['families'][family].update(full_old_new_native_equal=natives['old'] == natives['new'],
                whole_delta=family_rows['new']['whole']['bytes']-family_rows['old']['whole']['bytes'],
                source_delta=family_rows['new']['source']['bytes']-family_rows['old']['source']['bytes'])
            save()
        report.update(complete=True, independent_repeat_claim=False, promotion_claim=False,
            next_action='root decides targeted follow-up only for actual whole gains; no further candidate here')
        save()
        print(json.dumps({'complete': True, 'native_compilations': report['native_compilations'], 'whole_packages': report['whole_packages'],
            'results': {family: {k: row[k] for k in ('source_delta', 'whole_delta', 'full_old_new_native_equal')} for family, row in report['families'].items()},
            'engine_runs': 0}))
    except BaseException as error:
        report['failure'] = repr(error)
        save()
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'cost'))
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--prepared', type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    require(args.out.is_absolute() and not out.exists() and not any((p/'.git').exists() for p in (out, *out.parents)), 'new absolute non-Git output required')
    pins_raw = (HERE/'input-pins.json').read_bytes()
    require(sha(pins_raw) == PINS_SHA, 'fixed tracked input manifest changed')
    pins = json.loads(pins_raw)
    out.mkdir(parents=True)
    if args.phase == 'prepare':
        prepare(out, pins)
    else:
        require(args.prepared is not None and args.prepared.is_absolute(), 'absolute prepared source output required')
        cost(out, args.prepared.resolve(), pins)


if __name__ == '__main__':
    main()
