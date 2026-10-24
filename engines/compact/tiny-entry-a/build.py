#!/usr/bin/env python3
"""Build the maintained minimal A entry from Git source and fixed decisions.

There are no experiment-directory, old build.json or executable inputs. The
single shipping profile and LZMA-alone transport are fixed; --dev adds the
qualified ownership-source diagnostic form. The optional root-hint/leader-Repair
and direct NORMAL-slot policies have separate descriptors and keep the same
default Loose/DEV forms.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
import lzma
import os
from pathlib import Path
import platform
import subprocess
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]


def sha(data):return hashlib.sha256(data).hexdigest()


def normalized(path):
    data=path.read_bytes().replace(b'\r\n',b'\n')
    if b'\r' in data:raise ValueError('lone CR in owned text input: '+str(path))
    return data


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


def compile_c(command,source,directory):
    directory.mkdir()
    result=subprocess.run(command,input=source,cwd=directory,capture_output=True,timeout=90)
    (directory/'compiler.stderr').write_bytes(result.stderr)
    if result.returncode:raise RuntimeError('compiler failed; stderr preserved in '+str(directory))
    return (directory/'x').read_bytes()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--dev',action='store_true',help='also reproduce the qualified diagnostic C and ELF')
    parser.add_argument('--policy',choices=('loose','root-hint-leader-repair','root-normal-slots','root-pals-feedback'),default='loose',help='build-time shipping policy; DEV remains the qualified Loose control')
    args=parser.parse_args();out=args.out.resolve()
    if not args.out.is_absolute() or out.exists() or out==REPO or REPO in out.parents or any((p/'.git').exists() for p in (out,*out.parents)):
        parser.error('a new absolute output outside any Git checkout is required')
    if platform.system()!='Linux' or platform.machine() not in ('x86_64','amd64'):
        parser.error('the qualified fixed target is Linux x86-64')
    recipe=json.loads((HERE/'recipe.json').read_text())
    if recipe['format']!=1 or recipe['profile']!={'workers':2,'tt_bits':18,'ply':128,'dev_default':False}:
        raise ValueError('unsupported entry recipe/profile')
    if recipe['compression']!={'format':'lzma-alone','filter':'LZMA1','preset':6,'extreme':False,'lc':2,'lp':0,'pb':0,
                              'check':'NONE','mf':'BT2','dictionary_bytes':16384,'nice_len':24,'header_hex':'0200400000ffffffffffffffff'}:
        raise ValueError('unsupported fixed LZMA-alone recipe')
    policy=args.policy;root_policy=policy!='loose'
    decision=recipe['policies'][policy] if root_policy else None
    if root_policy and decision['profile']!=recipe['profile']:raise ValueError('optional policy resource profile differs')
    receipt=decision['qualified_receipt'] if root_policy else recipe['qualified_receipt']
    out.mkdir(parents=True);frozen=out/'inputs';frozen.mkdir()
    report={'complete':False,'scope':'canonical minimal A regeneration; fixed composed bytes, not 4KiB acceptance',
            'policy':policy,'resources':recipe['profile'],'inputs':{},'attempts':[],
            'qualified_receipt_reuse':receipt,
            'tools':{name:subprocess.check_output(command,text=True).splitlines()[0] for name,command in
                     {'cc':['cc','--version'],'ld':['ld','--version'],'python':['python3','--version'],
                      'xz':['xz','--version'],'lzma':['lzma','--version']}.items()}}
    def save():(out/'build.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        for name,expected in recipe['local_input_sha256'].items():
            data=normalized(HERE/name)
            if sha(data)!=expected:raise ValueError('entry input differs from qualified recipe: '+name)
            (frozen/name).write_bytes(data);report['inputs'][name]={'bytes':len(data),'sha256':sha(data)}
        for name in ('recipe.json','build.py'):
            data=normalized(HERE/name);(frozen/name).write_bytes(data)
            report['inputs'][name]={'bytes':len(data),'sha256':sha(data)}
        for relative,expected in recipe['helper_sha256'].items():
            path=REPO/relative;raw=path.read_bytes();data=normalized(path)
            if sha(data)!=expected:raise ValueError('tracked helper version changed: '+relative)
            (frozen/path.name).write_bytes(data)
            report['inputs'][relative]={'bytes':len(data),'sha256':sha(data),'working_bytes_sha256':sha(raw),'LF_normalization':raw!=data}
        specialize=module('entry_specialize',frozen/'specialize.py').specialize_c
        compact=module('entry_minify',frozen/'minify.py').compact_source
        strip=module('entry_counter_strip',frozen/'stitch.py').strip_dev_counters
        lexer=module('entry_fixed_tokens',frozen/'rename_c.py');replace=lexer._replace
        literal=module('entry_literal',frozen/'pack_stream.py').source_literal
        source_package=module('entry_source_package',frozen/'source_package.py')
        readonly_template=module('entry_readonly_template',frozen/'shipping_readonly.py').transform_template
        alpha=module('entry_fixed_A_alpha',frozen/'shipping_alpha.py').transform_source
        storage=module('entry_fixed_storage',frozen/'fixed_shipping_storage.py').transform_source
        scope=module('entry_bound_A_scope',frozen/'shipping_scope.py').transform_source
        input_profile=module('entry_fixed_A_input',frozen/'shipping_input.py')
        declarations=module('entry_fixed_A_declarations',frozen/'shipping_declarations.py').transform_source
        types=module('entry_fixed_A_types',frozen/'shipping_types.py').transform_source
        lexical=module('entry_fixed_A_lexical_scope',frozen/'shipping_lexical_scope.py').transform_source
        capture=module('entry_fixed_A_capture',frozen/'shipping_capture.py').transform_source
        startup=module('entry_fixed_A_startup',frozen/'shipping_startup.py').transform_source
        global_names=module('entry_fixed_A_global_names',frozen/'shipping_global_names.py').transform_source
        continuation=module('entry_fixed_A_continuation',frozen/'shipping_continuation.py').transform_source
        common=module('entry_fixed_common',frozen/'shipping_common.py')
        refine=module('entry_shipping_refinements',frozen/'shipping_refinements.py')
        dead_state=module('entry_material_state',frozen/'shipping_material_state.py')
        integer_forms=module('entry_integer_forms',frozen/'shipping_integer_forms.py')
        mixer_forms=module('entry_mixer_literals',frozen/'shipping_mixer_literals.py')
        clock_form=module('entry_clock_sentinel',frozen/'shipping_clock.py')
        history_depth=module('entry_history_depth',frozen/'shipping_history_depth.py').transform_source
        lazy_fallback=module('entry_lazy_fallback',frozen/'shipping_lazy_fallback.py')
        evaluation_cache=module('entry_evaluation_cache',frozen/'shipping_evaluation.py')
        worker_epilogue=module('entry_worker_epilogue',frozen/'shipping_worker_epilogue.py')
        terminal_loop=module('entry_terminal_loop',frozen/'shipping_terminal.py')
        fixed_names=module('entry_A_private_names',frozen/'shipping_names.py')
        condition_form=module('entry_A_one_condition',frozen/'shipping_condition.py')
        output_form=module('entry_A_fixed_output',frozen/'shipping_output.py')
        keyword_form=module('entry_A_keyword_scope',frozen/'shipping_keyword_scope.py')
        pool_state=module('entry_A_pool_state',frozen/'shipping_pool_state.py')
        frequency=module('entry_A_frequency',frozen/'shipping_frequency.py')
        ep_form=module('entry_A_EP_make',frozen/'shipping_ep.py')
        root_hint=module('entry_A_root_hint',frozen/'shipping_root_hint.py')
        root_normal=module('entry_A_root_normal',frozen/'shipping_root_normal.py')
        root_pals=module('entry_A_root_pals',frozen/'shipping_root_pals.py')
        root_form=root_normal if policy in ('root-normal-slots','root-pals-feedback') else root_hint
        canonical=(frozen/'engine.c').read_bytes();reference=evaluation_cache.reference_readable(canonical)
        template=(frozen/'bootstrap.py.in').read_bytes();prefix=(frozen/'launcher.sh').read_bytes()
        marker=b'__ROVE_SOURCE_LITERAL__'
        if template.count(marker)!=1 or len(prefix)!=77:raise ValueError('bootstrap recipe changed')
        prefix=source_package.XZ_STDIN_HEADER
        template,readonly_metadata=readonly_template(template,family='A')
        report['readonly_template']=readonly_metadata
        expected=decision['expected'] if root_policy else recipe['expected']
        def generate(directory,dev=False):
            preprocess_source=reference;input_metadata=None
            if dev:
                preprocess_source,input_metadata=input_profile.transform_readable(reference)
                preprocess_source,cache_metadata=evaluation_cache.reuse_readable(preprocess_source)
                input_metadata['evaluation_cache']=cache_metadata
            active,observations=specialize({'main.c':preprocess_source},directory,recipe['preprocessor']+['-DDEV='+str(int(dev))],os.environ.copy())
            data=compact(active['main.c'],'c');alpha_metadata=None;storage_metadata=None;scope_metadata=None;declaration_metadata=None;type_metadata=None;lexical_metadata=None;capture_metadata=None;startup_metadata=None;global_names_metadata=None;continuation_metadata=None;common_metadata=None
            if not dev:
                data,_=strip(data);files={'main.c':data}
                for old,new in recipe['fixed_renames']+recipe['resource_literals']+recipe['function_spellings']:
                    files=replace(files,old,new)
                data=files['main.c']
                data,alpha_metadata=alpha(data,family='A',lexer=lexer,readable=reference)
                data,storage_metadata=storage(data,family='A',readable=reference)
                data,scope_metadata=scope(data)
                data,input_metadata=input_profile.transform_source(data,readable=reference)
                data,declaration_metadata=declarations(data,readable=reference)
                data,type_metadata=types(data,readable=reference,lexer=lexer)
                data,lexical_metadata=lexical(data,readable=reference,lexer=lexer)
                data,capture_metadata=capture(data,readable=reference)
                data,startup_metadata=startup(data,readable=reference)
                data,global_names_metadata=global_names(data)
                data,continuation_metadata=continuation(data)
                data,common_metadata=common.transform_source(data,family='A')
                data,refinement=refine.transform_source(data,family='A')
                common_metadata['refinements']=refinement
                data,dead_state_metadata=dead_state.transform_source(data,family='A')
                common_metadata['material_state']=dead_state_metadata
                data,integer_metadata=integer_forms.transform_source(data,family='A')
                common_metadata['integer_forms']=integer_metadata
                data,final_metadata=mixer_forms.transform_source(data,family='A')
                common_metadata['mixer_literals']=final_metadata
                data,clock_metadata=clock_form.transform_source(data,family='A')
                common_metadata['clock_presence']=clock_metadata
                data,history_metadata=history_depth(data)
                common_metadata['history_depth']=history_metadata
                data,lazy_fallback_metadata=lazy_fallback.transform_source(data,family='A')
                common_metadata['lazy_fallback']=lazy_fallback_metadata
                data,cache_metadata=evaluation_cache.transform_source(data)
                common_metadata['evaluation_cache']=cache_metadata
                data,worker_metadata=worker_epilogue.transform_source(data)
                common_metadata['worker_epilogue']=worker_metadata
                data,terminal_metadata=terminal_loop.transform_source(data)
                common_metadata['terminal_shared_legal_loop']=terminal_metadata
                data,name_metadata=fixed_names.transform_source(data)
                common_metadata['private_destination_binding']=name_metadata
                data,condition_metadata=condition_form.transform_source(data)
                common_metadata['shared_condition']=condition_metadata
                data,output_metadata=output_form.transform_source(data)
                common_metadata['fixed_output']=output_metadata
                if not root_policy:
                    data,keyword_metadata=keyword_form.transform_source(data)
                    common_metadata['keyword_scope']=keyword_metadata
                    data,pool_metadata=pool_state.transform_source(data)
                    common_metadata['pool_state']=pool_metadata
                    data,frequency_metadata=frequency.transform_source(data)
                    common_metadata['frequency']=frequency_metadata
                    data,ep_metadata=ep_form.transform_source(data)
                    common_metadata['ep_make']=ep_metadata
                if root_policy:
                    if policy=='root-pals-feedback':
                        data,root_metadata=root_pals.transform_source(data,root_normal.transform_source)
                        common_metadata['root_pals_feedback']=root_metadata
                    else:
                        data,root_metadata=root_form.transform_source(data)
                        common_metadata['root_normal_slots' if policy=='root-normal-slots' else 'root_hint_leader_repair']=root_metadata
            return data,observations,alpha_metadata,storage_metadata,scope_metadata,input_metadata,declaration_metadata,type_metadata,lexical_metadata,capture_metadata,startup_metadata,global_names_metadata,continuation_metadata,common_metadata
        def package(source):
            expression,_=common.source_literal(source,literal)
            if root_policy:
                previous=lambda current:output_form.transform_literal(current,lambda original:condition_form.transform_literal(original,fixed_names.transform_literal))
                if policy=='root-pals-feedback':
                    expression=root_pals.transform_literal(expression,lambda current:root_normal.transform_literal(current,previous))
                else:
                    expression=root_form.transform_literal(expression,previous)
            else:
                previous=lambda current:frequency.transform_literal(current,lambda current:pool_state.transform_literal(current,lambda original:keyword_form.transform_literal(original,lambda restored:output_form.transform_literal(restored,lambda before:condition_form.transform_literal(before,fixed_names.transform_literal)))))
                expression=ep_form.transform_literal(expression,previous)
            script=template.replace(marker,expression.encode())
            ast.parse(script)
            whole=source_package.package(script,recipe['compression'],prefix=prefix)
            payload=whole[len(prefix):]
            if payload[:13]!=bytes.fromhex(recipe['compression']['header_hex']):
                raise ValueError('fixed LZMA-alone header changed')
            decoder=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
            if decoder.decompress(payload)!=script or not decoder.eof or decoder.unused_data:
                raise ValueError('strict LZMA-alone restoration mismatch')
            cli=subprocess.run(['lzma','-dc'],input=payload,capture_output=True,timeout=15)
            if cli.returncode or cli.stderr or cli.stdout!=script:
                raise ValueError('CLI LZMA-alone restoration mismatch')
            return prefix+payload,script
        first=None;first_dev=None
        for index in (1,2):
            directory=out/('attempt-'+str(index));directory.mkdir()
            source,observations,alpha_metadata,storage_metadata,scope_metadata,input_metadata,declaration_metadata,type_metadata,lexical_metadata,capture_metadata,startup_metadata,global_names_metadata,continuation_metadata,common_metadata=generate(directory/'preprocess')
            if len(source)!=expected['source_bytes'] or sha(source)!=expected['source_sha256']:raise ValueError('compact C identity mismatch')
            (directory/'main.c').write_bytes(source)
            native=compile_c(recipe['compiler'],source,directory/'native')
            if len(native)!=expected['native_bytes'] or sha(native)!=expected['native_sha256']:raise ValueError('native ELF identity mismatch')
            whole,script=package(source)
            if len(whole)!=expected['whole_bytes'] or sha(whole)!=expected['whole_sha256'] or sha(script)!=expected['bootstrap_sha256']:
                raise ValueError('complete launcher identity mismatch')
            (directory/'x').write_bytes(whole);(directory/'x').chmod(0o755);(directory/'bootstrap.py').write_bytes(script)
            current=(source,native,whole,script)
            if first is None:first=current
            elif current!=first:raise ValueError('independent generation did not reproduce bytes')
            row={'attempt':index,'source_bytes':len(source),'source_sha256':sha(source),'native_bytes':len(native),'native_sha256':sha(native),
                 'whole_bytes':len(whole),'whole_sha256':sha(whole),'bootstrap_sha256':sha(script),'preprocessor':observations,
                 'shipping_alpha':alpha_metadata,'shipping_storage':storage_metadata,'shipping_scope':scope_metadata,'shipping_input':input_metadata,'shipping_declarations':declaration_metadata,'shipping_types':type_metadata,'shipping_lexical_scope':lexical_metadata,'shipping_capture':capture_metadata,'shipping_startup':startup_metadata,'shipping_global_names':global_names_metadata,'shipping_continuation':continuation_metadata,'shipping_common':common_metadata}
            if args.dev:
                dev,dev_observations,dev_alpha,dev_storage,dev_scope,dev_input,dev_declarations,dev_types,dev_lexical,dev_capture,dev_startup,dev_global_names,dev_continuation,dev_common=generate(directory/'preprocess-dev',True)
                if dev_alpha is not None or dev_storage is not None or dev_scope is not None or dev_declarations is not None or dev_types is not None or dev_lexical is not None or dev_capture is not None or dev_startup is not None or dev_global_names is not None or dev_continuation is not None or dev_common is not None:raise ValueError('diagnostic source entered shipping spelling stage')
                if dev_input is None or dev_input['stage']!='readable-before-DEV-specialization' or dev_input['shipping_relation_checked']:
                    raise ValueError('diagnostic input-profile stage differs')
                if sha(dev)!=expected['dev_source_sha256']:raise ValueError('diagnostic C differs from qualified control')
                dev_command=['cc','-Os','-pthread','-DWORKERS=2','-DTT_BITS=18','-x','c','-','-o','x']
                dev_native=compile_c(dev_command,dev,directory/'dev');(directory/'dev/main.c').write_bytes(dev)
                if sha(dev_native)!=expected['dev_native_sha256']:raise ValueError('diagnostic ELF differs from qualified control')
                if first_dev is None:first_dev=(dev,dev_native)
                elif first_dev!=(dev,dev_native):raise ValueError('diagnostic bytes did not reproduce')
                row['dev']={'source_sha256':sha(dev),'native_sha256':sha(dev_native),'command':dev_command,'preprocessor':dev_observations,
                            'exact_qualified_control_bytes':True,'input_profile':dev_input}
            report['attempts'].append(row);save()
        (out/'main.c').write_bytes(first[0]);(out/'native').mkdir();(out/'native/x').write_bytes(first[1]);(out/'native/x').chmod(0o755)
        (out/'x').write_bytes(first[2]);(out/'x').chmod(0o755);(out/'bootstrap.py').write_bytes(first[3])
        if first_dev:
            (out/'dev').mkdir();(out/'dev/main.c').write_bytes(first_dev[0]);(out/'dev/x').write_bytes(first_dev[1]);(out/'dev/x').chmod(0o755)
        report.update(complete=True,source_reproduced=True,native_reproduced=True,whole_reproduced=True,
                      actual={'command':[str(out/'x')],'native':str(out/'native/x'),'source':str(out/'main.c'),
                              'whole_sha256':sha(first[2]),'native_sha256':sha(first[1]),'source_sha256':sha(first[0])},
                      diagnostic_exact_control=bool(first_dev),under_4096_bytes=False)
        save();print(json.dumps({'complete':True,'policy':policy,'out':str(out),'whole_bytes':len(first[2]),'source_sha256':sha(first[0]),
                                'native_sha256':sha(first[1]),'whole_sha256':sha(first[2]),'diagnostic_exact_control':bool(first_dev)}),flush=True)
    except Exception as error:
        report['error']=repr(error);save();raise


if __name__=='__main__':main()
