#!/usr/bin/env python3
"""Build the maintained minimal B entry from Git source and fixed decisions.

There are no experiment-directory, old build.json or executable inputs. The
single shipping profile is fixed; --dev adds the unchanged old full-minimax
reference model, which is distinct from production legal-LVA ordering.
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
    parser.add_argument('--dev',action='store_true',help='also reproduce the old full-minimax diagnostic reference C and ELF')
    args=parser.parse_args();out=args.out.resolve()
    if not args.out.is_absolute() or out.exists() or out==REPO or REPO in out.parents or any((p/'.git').exists() for p in (out,*out.parents)):
        parser.error('a new absolute output outside any Git checkout is required')
    if platform.system()!='Linux' or platform.machine() not in ('x86_64','amd64'):
        parser.error('the qualified fixed target is Linux x86-64')
    recipe=json.loads((HERE/'recipe.json').read_text())
    if recipe['format']!=1 or recipe['family']!='B' or recipe['profile']!={'workers':2,'tt_bits':18,'ply':128,'dev_default':False}:
        raise ValueError('unsupported entry recipe/profile')
    out.mkdir(parents=True);frozen=out/'inputs';frozen.mkdir()
    report={'complete':False,'scope':'minimal B legal-LVA ordering with shared forward geometry and generated tactical Move metadata after fixed shipping input; distinct old-minimax DEV reference; not 4KiB acceptance',
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
        compact=module('entry_minify',frozen/'minify.py').compact_source
        strip=module('entry_b_counter_strip',frozen/'generate.py').strip_counters
        literal=module('entry_literal',frozen/'pack_stream.py').source_literal
        reference=module('entry_fixed_shipping_alpha',frozen/'fixed_shipping_alpha.py')
        alpha=reference.transform_source
        storage=module('entry_B_storage_spelling',frozen/'shipping_storage.py').transform_source
        scope=module('entry_fixed_scope_names',frozen/'shipping_scope.py').transform_source
        core=module('entry_B_shipping_core',frozen/'shipping_core.py').transform_source
        lexer=module('entry_fixed_identifier_lexer',frozen/'rename_c.py')
        input_profile=module('entry_fixed_BCE_input_profile',frozen/'fixed_input_profile_bce.py')
        order=module('entry_B_shipping_order',frozen/'shipping_order.py').transform_source
        walk=module('entry_B_shipping_walk',frozen/'shipping_walk.py').transform_source
        tactical=module('entry_B_shipping_tactical',frozen/'shipping_tactical.py').transform_source
        types=module('entry_B_shipping_types',frozen/'shipping_types.py').transform_source
        global_names=module('entry_B_global_names',frozen/'shipping_global_names.py').transform_source
        recapture=module('entry_B_recapture_promotion',frozen/'shipping_recapture.py').transform_source
        common=module('entry_shipping_common',frozen/'shipping_common.py')
        refine=module('entry_shipping_refinements',frozen/'shipping_refinements.py')
        dead_state=module('entry_material_state',frozen/'shipping_material_state.py')
        integer_forms=module('entry_integer_forms',frozen/'shipping_integer_forms.py')
        late_forms=module('entry_late_forms',frozen/'shipping_compaction.py')
        include_forms=module('entry_include_forms',frozen/'shipping_includes.py')
        guard_form=module('entry_SEE_guard_clock_first',frozen/'shipping_guard.py')
        clock_form=module('entry_clock_sentinel',frozen/'shipping_clock.py')
        line_drain=module('entry_B_line_drain',frozen/'shipping_line_drain.py').transform_source
        search_context=module('entry_B_search_context',frozen/'shipping_search_context.py').transform_source
        lazy_fallback=module('entry_lazy_fallback',frozen/'shipping_lazy_fallback.py').transform_source
        history_depth=module('entry_history_depth',frozen/'shipping_history_depth.py').transform_source
        piece_index=module('entry_B_piece_index',frozen/'shipping_piece_index.py').transform_source
        singular_depth=module('entry_B_singular_depth',frozen/'shipping_singular_depth.py').transform_source
        cached_evaluation=module('entry_B_cached_evaluation',frozen/'shipping_cached_evaluation.py').transform_source
        hce_declarations=module('entry_B_HCE_declarations',frozen/'shipping_declarations.py').transform_source
        forwarders=module('entry_B_walker_forwarders',frozen/'shipping_forwarders.py').transform_source
        condition_sharing=module('entry_BCE_condition_sharing',frozen/'shipping_condition_bce.py').transform_source
        output_sharing=module('entry_BCE_output_sharing',frozen/'shipping_output_bce.py').transform_source
        source_package=module('entry_B_source_package',frozen/'source_package.py')
        readonly_template=module('entry_readonly_template',frozen/'shipping_readonly.py').transform_template
        canonical=(frozen/'engine.c').read_bytes();template=(frozen/'bootstrap.py.in').read_bytes();prefix=(frozen/'launcher.sh').read_bytes()
        marker=b'__ROVE_SOURCE_LITERAL__'
        if template.count(marker)!=1 or len(prefix)!=77:raise ValueError('bootstrap recipe changed')
        prefix=source_package.XZ_STDIN_HEADER
        compression={'format': 'lzma-alone', 'filter': 'LZMA1', 'preset': 9, 'extreme': True, 'lc': 2, 'lp': 0, 'pb': 0, 'check': 'NONE', 'mf': 'BT4', 'dictionary_bytes': 67108864, 'nice_len': 32}
        if recipe['compression']!=compression:raise ValueError('fixed LZMA1 recipe changed')
        template,readonly_metadata=readonly_template(template,family='B')
        report['readonly_template']=readonly_metadata
        expected=recipe['expected']
        def generate(directory,dev=False):
            preprocess_source=canonical;input_metadata=None
            if dev:preprocess_source,input_metadata=input_profile.transform_readable(canonical,family='B')
            active,observations=specialize({'main.c':preprocess_source},directory,recipe['preprocessor']+['-DDEV='+str(int(dev)),'main.c','-o','x'],os.environ.copy())
            data=compact(active['main.c'],'c')
            alpha_metadata=None;storage_metadata=None;scope_metadata=None;core_metadata=None;order_metadata=None;walk_metadata=None;tactical_metadata=None;type_metadata=None;global_names_metadata=None;recapture_metadata=None;common_metadata=None
            if not dev:
                data,_=strip(data)
                data,alpha_metadata=alpha(data,family='B',lexer=lexer)
                data,storage_metadata=storage(data,family='B',lexer=lexer,reference=reference,readable=canonical)
                data,scope_metadata=scope(data)
                data,core_metadata=core(data,readable=canonical)
                data,input_metadata=input_profile.transform_source(data,readable=canonical,family='B')
                data,order_metadata=order(data)
                data,walk_metadata=walk(data)
                data,tactical_metadata=tactical(data)
                data,type_metadata=types(data,readable=canonical,lexer=lexer)
                data,global_names_metadata=global_names(data)
                data,recapture_metadata=recapture(data)
                data,common_metadata=common.transform_source(data,family='B')
                data,refinement=refine.transform_source(data,family='B')
                common_metadata['refinements']=refinement
                data,dead_state_metadata=dead_state.transform_source(data,family='B')
                common_metadata['material_state']=dead_state_metadata
                data,integer_metadata=integer_forms.transform_source(data,family='B')
                common_metadata['integer_forms']=integer_metadata
                data,late_metadata=late_forms.transform_source(data,family='B')
                common_metadata['job_startup_SEE_forms']=late_metadata
                data,include_metadata=include_forms.transform_source(data,family='B')
                common_metadata['literal_include_forms']=include_metadata
                data,final_metadata=guard_form.transform_source(data,family='B')
                common_metadata['SEE_guard_clock_first']=final_metadata
                data,clock_metadata=clock_form.transform_source(data,family='B')
                common_metadata['clock_presence']=clock_metadata
                data,line_drain_metadata=line_drain(data)
                common_metadata['line_drain']=line_drain_metadata
                data,context_metadata=search_context(data,readable=canonical)
                common_metadata['search_context']=context_metadata
                data,fallback_metadata=lazy_fallback(data,family='B')
                common_metadata['lazy_fallback']=fallback_metadata
                data,history_metadata=history_depth(data,family='B')
                common_metadata['history_depth']=history_metadata
                data,piece_metadata=piece_index(data)
                common_metadata['piece_index']=piece_metadata
                data,singular_metadata=singular_depth(data)
                common_metadata['singular_depth']=singular_metadata
                data,evaluation_metadata=cached_evaluation(data)
                common_metadata['cached_evaluation']=evaluation_metadata
                data,declaration_metadata=hce_declarations(data)
                common_metadata['hce_declarations']=declaration_metadata
                data,forwarder_metadata=forwarders(data)
                common_metadata['walker_forwarders']=forwarder_metadata
                data,condition_metadata=condition_sharing(data,family='B')
                common_metadata['condition_sharing']=condition_metadata
                data,output_metadata=output_sharing(data,family='B')
                common_metadata['output_sharing']=output_metadata
            return data,observations,alpha_metadata,storage_metadata,scope_metadata,core_metadata,input_metadata,order_metadata,walk_metadata,tactical_metadata,type_metadata,global_names_metadata,recapture_metadata,common_metadata
        def package(source):
            expression,_=common.source_literal(source,literal);script=template.replace(marker,expression.encode())
            ast.parse(script)
            data=prefix+lzma.compress(script,format=lzma.FORMAT_ALONE,check=lzma.CHECK_NONE,
                                     filters=[{'id':lzma.FILTER_LZMA1,'preset':9|lzma.PRESET_EXTREME,
                                               'lc':2,'lp':0,'pb':0,'mf':lzma.MF_BT4,
                                               'dict_size':67108864,'nice_len':32}])
            return data,script
        first=None;first_dev=None
        for index in (1,2):
            directory=out/('attempt-'+str(index));directory.mkdir()
            source,observations,alpha_metadata,storage_metadata,scope_metadata,core_metadata,input_metadata,order_metadata,walk_metadata,tactical_metadata,type_metadata,global_names_metadata,recapture_metadata,common_metadata=generate(directory/'preprocess')
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
                 'shipping_alpha':alpha_metadata,'shipping_storage':storage_metadata,'shipping_scope':scope_metadata,'shipping_core':core_metadata,'shipping_input':input_metadata,'shipping_order':order_metadata,'shipping_walk':walk_metadata,'shipping_tactical':tactical_metadata,'shipping_types':type_metadata,'shipping_global_names':global_names_metadata,'shipping_recapture':recapture_metadata,'shipping_common':common_metadata}
            if args.dev:
                dev,dev_observations,dev_alpha,dev_storage,dev_scope,dev_core,dev_input,dev_order,dev_walk,dev_tactical,dev_types,dev_global_names,dev_recapture,dev_common=generate(directory/'preprocess-dev',True)
                if dev_alpha is not None or dev_storage is not None or dev_scope is not None or dev_core is not None or dev_order is not None or dev_walk is not None or dev_tactical is not None or dev_types is not None or dev_global_names is not None or dev_recapture is not None or dev_common is not None:raise ValueError('diagnostic source entered shipping spelling/core stage')
                if sha(dev)!=expected['dev_source_sha256']:raise ValueError('diagnostic C differs from qualified control')
                dev_command=recipe['dev_compiler']
                dev_native=compile_c(dev_command,dev,directory/'dev');(directory/'dev/main.c').write_bytes(dev)
                if sha(dev_native)!=expected['dev_native_sha256']:raise ValueError('diagnostic ELF differs from qualified control')
                if first_dev is None:first_dev=(dev,dev_native)
                elif first_dev!=(dev,dev_native):raise ValueError('diagnostic bytes did not reproduce')
                row['dev']={'source_sha256':sha(dev),'native_sha256':sha(dev_native),'command':dev_command,'preprocessor':dev_observations,
                            'exact_qualified_control_bytes':True,'shipping_input_readable':dev_input,
                            'model':'old full legal minimax reference; not production legal-LVA',
                            'shipping_model_equivalence':False}
            report['attempts'].append(row);save()
        (out/'main.c').write_bytes(first[0]);(out/'native').mkdir();(out/'native/x').write_bytes(first[1]);(out/'native/x').chmod(0o755)
        (out/'x').write_bytes(first[2]);(out/'x').chmod(0o755);(out/'bootstrap.py').write_bytes(first[3])
        if first_dev:
            (out/'dev').mkdir();(out/'dev/main.c').write_bytes(first_dev[0]);(out/'dev/x').write_bytes(first_dev[1]);(out/'dev/x').chmod(0o755)
        report.update(complete=True,source_reproduced=True,native_reproduced=True,whole_reproduced=True,
                      actual={'command':[str(out/'x')],'native':str(out/'native/x'),'source':str(out/'main.c'),
                              'whole_sha256':sha(first[2]),'native_sha256':sha(first[1]),'source_sha256':sha(first[0])},
                      diagnostic_exact_control=bool(first_dev),under_4096_bytes=False,
                      shipping_SEE_model='legal-LVA ordering; dominated internal recapture promotions composed; QS SEE pruning disabled',
                      shipping_SEE_checkpoint_schedule='fewer recursive calls; not identical cancellation timing',
                      diagnostic_model_equivalent_to_shipping=False,
                      shipping_geometry='shared forward occupied-BB source walker; full attacker masks',
                      shipping_Move_ABI='generated bit3 tactical, FROM119, unchanged TO/PROMO and17-bit TT',
                      shipping_ordering_policy='quiet promotions also receive capture tactical base tier')
        save();print(json.dumps({'complete':True,'out':str(out),'whole_bytes':len(first[2]),'source_sha256':sha(first[0]),
                                'native_sha256':sha(first[1]),'whole_sha256':sha(first[2]),'diagnostic_exact_control':bool(first_dev)}),flush=True)
    except Exception as error:
        report['error']=repr(error);save();raise


if __name__=='__main__':main()
