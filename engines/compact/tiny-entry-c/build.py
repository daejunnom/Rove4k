#!/usr/bin/env python3
"""Build the maintained minimal C entry from Git source and fixed decisions.

There are no experiment-directory, old build.json or executable inputs. The
single shipping profile is fixed; --dev adds the unchanged diagnostic form.
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
    args=parser.parse_args();out=args.out.resolve()
    if not args.out.is_absolute() or out.exists() or out==REPO or REPO in out.parents or any((p/'.git').exists() for p in (out,*out.parents)):
        parser.error('a new absolute output outside any Git checkout is required')
    if platform.system()!='Linux' or platform.machine() not in ('x86_64','amd64'):
        parser.error('the qualified fixed target is Linux x86-64')
    recipe=json.loads((HERE/'recipe.json').read_text())
    if recipe['format']!=1 or recipe['family']!='C' or recipe['profile']!={'workers':2,'tt_bits':18,'ply':128,'dev_default':False}:
        raise ValueError('unsupported entry recipe/profile')
    flags=['cc','-std=c11','-Os','-pthread','-DWORKERS=2','-DTT_BITS=18','-mavx2']
    if recipe['compiler']!=['cc','-Os','-mavx2','-x','c','-','-o','x','-s'] or recipe['dev_compiler']!=flags+['-DDEV=1','-x','c','-','-o','x'] or recipe['preprocessor']!=flags:
        raise ValueError('fixed C selected compiler or unchanged DEV/preprocessor changed')
    compression={'format': 'lzma-alone', 'filter': 'LZMA1', 'preset': 9, 'extreme': True, 'lc': 2, 'lp': 0, 'pb': 0, 'check': 'NONE', 'mf': 'BT4', 'dictionary_bytes': 67108864, 'nice_len': 64}
    if recipe['compression']!=compression:
        raise ValueError('unsupported fixed C compression recipe')
    out.mkdir(parents=True);frozen=out/'inputs';frozen.mkdir()
    report={'complete':False,'scope':'maintained C signed-net 8xint16 and 128-bit SIMD on selected common PVS/runtime; source+compiler policy variant, unchanged DEV ancestry',
            'resources':recipe['profile'],'inputs':{},'attempts':[],
            'qualified_receipt_reuse':recipe['qualified_receipt'],
            'tools':{name:subprocess.check_output(command,text=True).splitlines()[0] for name,command in
                     {'cc':['cc','--version'],'ld':['ld','--version'],'python':['python3','--version'],'lzma':['lzma','--version']}.items()}}
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
        minifier=module('entry_minify',frozen/'minify.py');compact=minifier.compact_source
        strip=module('entry_counter_strip',frozen/'stitch.py').strip_dev_counters
        literal=module('entry_literal',frozen/'pack_stream.py').source_literal
        compiler_group=module('entry_compiler_group',frozen/'compiler_group.py').transform_bootstrap
        stdin_owner=module('entry_compiler_stdin',frozen/'compiler_stdin.py')
        compiler_stdin=stdin_owner.transform_bootstrap
        compiler_seek=module('entry_compiler_seek',frozen/'compiler_seek.py').transform_bootstrap
        source_package=module('entry_source_package',frozen/'source_package.py')
        readonly_template=module('entry_readonly_template',frozen/'shipping_readonly.py').transform_template
        common=module('entry_shipping_common',frozen/'shipping_common.py')
        refine=module('entry_shipping_refinements',frozen/'shipping_refinements.py')
        dead_state=module('entry_material_state',frozen/'shipping_material_state.py')
        integer_forms=module('entry_integer_forms',frozen/'shipping_integer_forms.py')
        late_forms=module('entry_late_forms',frozen/'shipping_compaction.py')
        include_forms=module('entry_include_forms',frozen/'shipping_includes.py')
        mixer_forms=module('entry_mixer_literals',frozen/'shipping_mixer_literals.py')
        reference=module('entry_fixed_shipping_alpha_reference',frozen/'fixed_shipping_alpha.py')
        alpha=module('entry_composition_shipping_alpha',frozen/'shipping_alpha.py').transform_source
        scope=module('entry_fixed_scope_names',frozen/'shipping_scope.py').transform_source
        core=module('entry_fixed_shipping_core',frozen/'shipping_core.py').transform_source
        simd=module('entry_fixed_shipping_simd',frozen/'shipping_simd.py').transform_source
        lexer=module('entry_fixed_identifier_lexer',frozen/'rename_c.py')
        input_profile=module('entry_fixed_BCE_input_profile',frozen/'fixed_input_profile_bce.py')
        material=module('entry_fixed_C_material_vector',frozen/'shipping_material.py').transform_source
        incremental=module('entry_fixed_C_incremental_vector',frozen/'shipping_incremental.py').transform_source
        signed_vector=module('entry_fixed_C_signed_vector',frozen/'shipping_signed_vector.py').transform_source
        types=module('entry_C_shipping_types',frozen/'shipping_types.py').transform_source
        global_names=module('entry_C_global_names',frozen/'shipping_global_names.py').transform_source
        clock_form=module('entry_clock_sentinel',frozen/'shipping_clock.py')
        search_context=module('entry_C_search_context',frozen/'shipping_search_context.py')
        history_depth=module('entry_C_history_depth',frozen/'shipping_history_depth.py')
        lazy_fallback=module('entry_C_lazy_fallback',frozen/'shipping_lazy_fallback.py')
        capture_form=module('entry_C_capture',frozen/'shipping_capture.py')
        lane_sum=module('entry_C_lane_sum',frozen/'shipping_lane_sum.py')
        terminal_form=module('entry_C_terminal_shared',frozen/'shipping_terminal.py')
        condition_sharing=module('entry_BCE_condition_sharing',frozen/'shipping_condition_bce.py').transform_source
        output_sharing=module('entry_BCE_output_sharing',frozen/'shipping_output_bce.py').transform_source
        worker_epilogue=module('entry_BCE_worker_epilogue',frozen/'shipping_worker_epilogue_bce.py').transform_source
        setter_phase=module('entry_BCE_setter_phase',frozen/'shipping_setter_phase_bce.py').transform_source
        constants=module('entry_BCE_constants',frozen/'shipping_constants_bce.py').transform_source
        cross=module('entry_C_common_SIMD_cross',frozen/'shipping_cross_c.py')
        pool_state=module('entry_C_completed_depth_token',frozen/'shipping_pool_state.py')
        late_constants=module('entry_C_late_four_constants',frozen/'shipping_late_constants.py')
        dead_score=module('entry_C_dead_published_score',frozen/'shipping_dead_score.py')
        canonical=(frozen/'engine.c').read_bytes();template=(frozen/'bootstrap.py.in').read_bytes();prefix=(frozen/'launcher.sh').read_bytes()
        marker=b'__ROVE_SOURCE_LITERAL__'
        if template.count(marker)!=1 or len(prefix)!=77:raise ValueError('bootstrap recipe changed')
        prefix=source_package.XZ_STDIN_HEADER
        calls=[node for node in ast.walk(ast.parse(template)) if isinstance(node,ast.Call) and
               isinstance(node.func,ast.Attribute) and isinstance(node.func.value,ast.Name) and
               node.func.value.id=='subprocess' and node.func.attr=='Popen']
        if len(calls)!=1 or ast.literal_eval(calls[0].args[0])!=cross.PREVIOUS_COMPILER:
            raise ValueError('fixed C compiler argv differs between bootstrap and native recipe')
        template,readonly_metadata=readonly_template(template,family='C')
        report['readonly_template']=readonly_metadata
        expected=recipe['expected']
        def generate(directory,dev=False):
            preprocess_source=canonical;input_metadata=None
            if dev:preprocess_source,input_metadata=input_profile.transform_readable(canonical,family='C')
            active,observations=specialize({'main.c':preprocess_source},directory,recipe['preprocessor']+['-DDEV='+str(int(dev))],os.environ.copy())
            data=compact(active['main.c'],'c')
            alpha_metadata=None;scope_metadata=None;core_metadata=None;simd_metadata=None;material_metadata=None;incremental_metadata=None;signed_metadata=None;type_metadata=None;global_names_metadata=None;common_metadata=None
            if not dev:
                data,_=strip(data)
                data,alpha_metadata=alpha(data,family='C',lexer=lexer,reference=reference,readable=canonical)
                data,scope_metadata=scope(data)
                data,core_metadata=core(data,readable=canonical,profile=recipe['profile'],tokens=minifier._tokens,keywords=lexer._KEYWORDS)
                data,simd_metadata=simd(data,readable=canonical,profile=recipe['profile'],tokens=minifier._tokens,keywords=lexer._KEYWORDS)
                data,input_metadata=input_profile.transform_source(data,readable=canonical,family='C')
                data,material_metadata=material(data)
                data,incremental_metadata=incremental(data)
                data,signed_metadata=signed_vector(data)
                data,type_metadata=types(data,readable=canonical,lexer=lexer)
                data,global_names_metadata=global_names(data)
                data,common_metadata=common.transform_source(data,family='C')
                data,refinement=refine.transform_source(data,family='C')
                common_metadata['refinements']=refinement
                data,dead_state_metadata=dead_state.transform_source(data,family='C')
                common_metadata['material_state']=dead_state_metadata
                data,integer_metadata=integer_forms.transform_source(data,family='C')
                common_metadata['integer_forms']=integer_metadata
                data,late_metadata=late_forms.transform_source(data,family='C')
                common_metadata['job_startup_SEE_forms']=late_metadata
                data,include_metadata=include_forms.transform_source(data,family='C')
                common_metadata['literal_include_forms']=include_metadata
                data,final_metadata=mixer_forms.transform_source(data,family='C')
                common_metadata['mixer_literals']=final_metadata
                data,clock_metadata=clock_form.transform_source(data,family='C')
                common_metadata['clock_presence']=clock_metadata
                data,search_context_metadata=search_context.transform_source(data,readable=canonical)
                common_metadata['search_context']=search_context_metadata
                data,history_depth_metadata=history_depth.transform_source(data)
                common_metadata['history_depth']=history_depth_metadata
                data,lazy_fallback_metadata=lazy_fallback.transform_source(data,family='C')
                common_metadata['lazy_fallback']=lazy_fallback_metadata
                data,capture_metadata=capture_form.transform_source(data)
                common_metadata['capture_only_Move_bit3']=capture_metadata
                data,lane_metadata=lane_sum.transform_source(data)
                common_metadata['signed_lane_sum']=lane_metadata
                data,terminal_metadata=terminal_form.transform_source(data)
                common_metadata['shared_terminal']=terminal_metadata
                data,condition_metadata=condition_sharing(data,family='C')
                common_metadata['condition_sharing']=condition_metadata
                data,output_metadata=output_sharing(data,family='C')
                common_metadata['output_sharing']=output_metadata
                data,worker_metadata=worker_epilogue(data,family='C')
                common_metadata['worker_epilogue']=worker_metadata
                data,setter_metadata=setter_phase(data,family='C')
                common_metadata['setter_phase']=setter_metadata
                data,constants_metadata=constants(data,family='C')
                common_metadata['constants']=constants_metadata
                data,cross_metadata=cross.transform_source(data,compact=compact)
                common_metadata['cross']=cross_metadata
                data,pool_metadata=pool_state.transform_source(data)
                common_metadata['completed_depth_token']=pool_metadata
                data,late_constants_metadata=late_constants.transform_source(data)
                common_metadata['late_four_constants']=late_constants_metadata
                data,dead_score_metadata=dead_score.transform_source(data)
                common_metadata['dead_published_score']=dead_score_metadata
            return data,observations,alpha_metadata,scope_metadata,core_metadata,simd_metadata,input_metadata,material_metadata,incremental_metadata,signed_metadata,type_metadata,global_names_metadata,common_metadata
        def package(source):
            scored_source=dead_score.restore_source(source)
            pool_source=late_constants.restore_source(scored_source)
            selected=pool_state.restore_source(pool_source)
            before=cross.restore_source(selected,compact=compact)
            old_expression,_=common.source_literal(before,literal)
            previous=template.replace(marker,old_expression.encode())
            expression,_=common.source_literal(selected,literal)
            script,bootstrap_metadata=cross.transform_bootstrap(previous,before=before,source=selected,
                old_expression=old_expression,expression=expression,compact=compact)
            report['cross_bootstrap']=bootstrap_metadata
            script,pool_metadata=pool_state.transform_bootstrap(script,source=pool_source)
            report['pool_bootstrap']=pool_metadata
            script,constants_bootstrap=late_constants.transform_bootstrap(script,source=scored_source)
            report['late_constants_bootstrap']=constants_bootstrap
            script,group_metadata=compiler_group(script)
            report['compiler_group']=group_metadata
            script,dead_score_bootstrap=dead_score.transform_bootstrap(script,source=source)
            report['dead_score_bootstrap']=dead_score_bootstrap
            if len(script)!=10947 or sha(script)!='2f1dd8b4e6a12f0aa7f25705f63fea55c1775cc49c18b544ed5e0e211b2dc1b8':
                raise ValueError('C terminal compiler-owner predecessor differs')
            script,stdin_metadata=compiler_stdin(script,shared_wait=True)
            report['compiler_stdin']=stdin_metadata
            if len(script)!=10827 or sha(script)!='88ec75427939590684772ed534b754bc637fd52ca7d087a712ac5be7de40f0fc':
                raise ValueError('C W1W2 predecessor before seek stage differs')
            script,seek_metadata=compiler_seek(script,owner_metadata=stdin_metadata,
                prepare_owner=stdin_owner.transform_bootstrap,restore_owner=stdin_owner.restore_bootstrap)
            report['compiler_seek']=seek_metadata
            ast.parse(script)
            data=prefix+lzma.compress(script,format=lzma.FORMAT_ALONE,check=lzma.CHECK_NONE,
                                     filters=[{'id':lzma.FILTER_LZMA1,'preset':9|lzma.PRESET_EXTREME,
                                               'lc':2,'lp':0,'pb':0,'mf':lzma.MF_BT4,
                                               'dict_size':67108864,'nice_len':64}])
            return data,script
        first=None;first_dev=None
        for index in (1,2):
            directory=out/('attempt-'+str(index));directory.mkdir()
            source,observations,alpha_metadata,scope_metadata,core_metadata,simd_metadata,input_metadata,material_metadata,incremental_metadata,signed_metadata,type_metadata,global_names_metadata,common_metadata=generate(directory/'preprocess')
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
                 'shipping_alpha':alpha_metadata,'shipping_scope':scope_metadata,'shipping_core':core_metadata,'shipping_simd':simd_metadata,'shipping_input':input_metadata,'shipping_material':material_metadata,'shipping_incremental':incremental_metadata,'shipping_signed_vector':signed_metadata,'shipping_types':type_metadata,'shipping_global_names':global_names_metadata,'shipping_common':common_metadata}
            if args.dev:
                dev,dev_observations,dev_alpha,dev_scope,dev_core,dev_simd,dev_input,dev_material,dev_incremental,dev_signed,dev_types,dev_global_names,dev_common=generate(directory/'preprocess-dev',True)
                if dev_alpha is not None or dev_scope is not None or dev_core is not None or dev_simd is not None or dev_material is not None or dev_incremental is not None or dev_signed is not None or dev_types is not None or dev_global_names is not None or dev_common is not None:raise ValueError('diagnostic source entered a shipping-only stage')
                if sha(dev)!=expected['dev_source_sha256']:raise ValueError('diagnostic C differs from qualified control')
                dev_command=recipe['dev_compiler']
                dev_native=compile_c(dev_command,dev,directory/'dev');(directory/'dev/main.c').write_bytes(dev)
                if sha(dev_native)!=expected['dev_native_sha256']:raise ValueError('diagnostic ELF differs from qualified control')
                if first_dev is None:first_dev=(dev,dev_native)
                elif first_dev!=(dev,dev_native):raise ValueError('diagnostic bytes did not reproduce')
                row['dev']={'source_sha256':sha(dev),'native_sha256':sha(dev_native),'command':dev_command,'preprocessor':dev_observations,
                            'exact_qualified_control_bytes':True,'shipping_input_readable':dev_input}
            report['attempts'].append(row);save()
        (out/'main.c').write_bytes(first[0]);(out/'native').mkdir();(out/'native/x').write_bytes(first[1]);(out/'native/x').chmod(0o755)
        (out/'x').write_bytes(first[2]);(out/'x').chmod(0o755);(out/'bootstrap.py').write_bytes(first[3])
        if first_dev:
            (out/'dev').mkdir();(out/'dev/main.c').write_bytes(first_dev[0]);(out/'dev/x').write_bytes(first_dev[1]);(out/'dev/x').chmod(0o755)
        report.update(complete=True,source_reproduced=True,native_reproduced=True,whole_reproduced=True,
                      actual={'command':[str(out/'x')],'native':str(out/'native/x'),'source':str(out/'main.c'),
                              'whole_sha256':sha(first[2]),'native_sha256':sha(first[1]),'source_sha256':sha(first[0])},
                      diagnostic_exact_control=bool(first_dev),under_4096_bytes=False)
        save();print(json.dumps({'complete':True,'out':str(out),'whole_bytes':len(first[2]),'source_sha256':sha(first[0]),
                                'native_sha256':sha(first[1]),'whole_sha256':sha(first[2]),'diagnostic_exact_control':bool(first_dev)}),flush=True)
    except Exception as error:
        report['error']=repr(error);save();raise


if __name__=='__main__':main()
