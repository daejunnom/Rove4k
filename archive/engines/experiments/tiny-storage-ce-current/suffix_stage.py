#!/usr/bin/env python3
"""Explicit prior-stage reuse for one C suffix class; native only, no codec."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
def sha(data):return hashlib.sha256(data).hexdigest()
def read(path):
    data=Path(path).read_bytes().replace(b'\r\n',b'\n')
    if b'\r' in data:raise ValueError('lone CR in owned ordinary source')
    return data
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result
def bound(data,pin,label):
    if {'bytes':len(data),'sha256':sha(data)}!=pin:raise ValueError('literal input changed: '+label)
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--prior',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();prior=args.prior.resolve();out=args.out.resolve()
    if not args.prior.is_absolute() or not prior.is_dir():parser.error('explicit existingabsolute prior-stage output required')
    if not args.out.is_absolute() or out.exists() or prior==out or prior in out.parents or out in prior.parents or any((p/'.git').exists() for p in (out,*out.parents)):
        parser.error('newabsoluteout outsideGit and prior-stage directory required')
    if platform.system()!='Linux' or platform.machine() not in ('x86_64','amd64'):parser.error('fixed Linux x86-64 target required')
    fixed_raw=read(HERE/'suffix_recipe.json');fixed=json.loads(fixed_raw)
    if fixed['class']!='current-C5687-storage18-tiny_table-suffix-qq-1' or fixed['new_native_compile_limits']!={'C':1,'E':2} or fixed['candidate_codec_engine_limit']!=0:
        raise ValueError('fixedsuffix reuse scope changed')
    if len(fixed['original_source_files'])!=38:raise ValueError('original38 inventory changed')
    if set(fixed['new_input_sha256'])!={'observe_suffix.py','suffix_stage.py'} or fixed['prior_reuse_file_count']!=23 or len(fixed['prior_reuse_files'])!=23:
        raise ValueError('literal newsource/priorreuse closure changed')
    # Verify complete raw ordinary helper bytes BEFORE importing any helper.
    ordinary={}
    for name,pin in fixed['original_source_files'].items():
        data=read(HERE/name);bound(data,pin,'original38/'+name);ordinary[name]=data
    for name,pin in fixed['new_input_sha256'].items():
        data=read(HERE/name)
        if sha(data)!=pin:raise ValueError('newsourcepinchanged: '+name)
        ordinary[name]=data
    for name in ('suffix_recipe.json','suffix_stage.py'):ordinary[name]=read(HERE/name)
    if len(ordinary)!=fixed['ordinary_input_file_count']:raise ValueError('closedordinarysourcecount')
    out.mkdir(parents=True);inputs=out/'inputs';inputs.mkdir()
    rows={}
    for name,data in ordinary.items():
        target=inputs/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);rows[name]={'bytes':len(data),'sha256':sha(data)}
    report={'complete':False,'mode':'explicit prior-stage reuse, not artifact-free normalgeneration','class':fixed['class'],'ordinary_inputs':rows,'reused_inputs':{},
        'original_failure_unchanged':True,'original_source_files_unchanged':38,'new_native_compiles':{'C':0,'E':0},'cumulative_candidate_native_compiles':{'C':1,'E':0},
        'candidate_codec_calls':0,'candidate_whole_measurements':0,'engine_runs':0,'families':{},'new_class_qualified':False,'new_E_class_pending_root':True}
    def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        # Reuse is bounded to explicitly authorized, literal prior bytes.
        for relative,pin in fixed['prior_reuse_files'].items():
            data=(prior/relative).read_bytes();bound(data,pin,'prior/'+relative)
            target=out/'reused'/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            report['reused_inputs'][relative]={'bytes':len(data),'sha256':sha(data)}
        reused=out/'reused';old_report=json.loads((reused/'results.json').read_text())
        if old_report['complete'] or old_report.get('error')!="ValueError('complete stored symbol string multiset')" or old_report['families']['C']['candidate_native_compiles']!=1 or old_report['families']['E']['candidate_native_compiles']!=0:
            raise ValueError('originalhardstopstate changed')
        support=module('suffix_reuse_support',inputs/'support.py');policy=module('suffix_reuse_policy',inputs/'policy.py')
        direct=module('suffix_reuse_direct_observer',inputs/'observe.py');suffix=module('suffix_reuse_C_observer',inputs/'observe_suffix.py')
        lexer=module('suffix_reuse_lexer',inputs/'control/engines/scripts/rename_c.py');source_fixed=json.loads(policy.POLICY_BYTES)
        for family in ('C','E'):
            expected=json.loads((inputs/f'control/engines/compact/tiny-entry-{family.lower()}/recipe.json').read_text())['expected']
            built=json.loads((reused/f'control-{family}/build.json').read_text())
            if not built['complete'] or len(built['attempts'])!=2 or built['diagnostic_exact_control']:raise ValueError('prior2shippingcontrol incomplete')
            for attempt in (1,2):
                row=built['attempts'][attempt-1]
                for key,path in [('source','main.c'),('native','native/x')]:
                    payload=(reused/f'control-{family}/attempt-{attempt}'/path).read_bytes()
                    if len(payload)!=expected[key+'_bytes'] or sha(payload)!=expected[key+'_sha256'] or row[key+'_sha256']!=expected[key+'_sha256']:
                        raise ValueError('exact2baseline/source/native reuse failed')
            report['families'][family]={'baseline_reused_shipping_attempts':2,'baseline_native_sha256':expected['native_sha256'],'baseline_source_sha256':expected['source_sha256']}
        save()
        # C first image and PP gate are explicitly reused; the failed Counter is not rerun or accepted.
        C=report['families']['C'];old_C=(reused/'control-C/native/x').read_bytes();first_C=(reused/'candidate-C/attempt-1/native/x').read_bytes()
        bound(old_C,fixed['C_images']['control'],'C oldimage');bound(first_C,fixed['C_images']['candidate'],'C reusedfirstimage')
        source_C=(reused/'control-C/main.c').read_bytes();candidate_C,proof=policy.transform_source(source_C,family='C',lexer=lexer)
        if candidate_C!=(reused/'candidate-C/attempt-1/main.c').read_bytes():raise ValueError('C reusedsource differs')
        old_gate=old_report['families']['C']['header_gate']
        if not old_gate['pass'] or not old_gate['full_preprocessed_bytes_inverse_equal'] or old_gate['numeric_inverse_replacements']!=0:
            raise ValueError('priorC strictPP proof missing')
        raw_expanded=(reused/'candidate-C/header/control-expanded.txt').read_bytes();raw_inverse=(reused/'candidate-C/header/candidate-expanded-inverse.txt').read_bytes()
        if raw_expanded!=raw_inverse or sha(raw_expanded)!=old_gate['expanded_sha256']:raise ValueError('priorCrawPPbytes notexact')
        C.update(source_proof=proof,header_gate_reused=old_gate,old_full_native_equal=False,first_native_reused=True)
        Cdir=out/'C';Cdir.mkdir();(Cdir/'main.c').write_bytes(candidate_C)
        observations=[]
        def C_observation(image,label):
            result=suffix.compare(old_C,image,symbol_pairs=source_fixed['families']['C']['literal_expected_symbol_pairs'])
            raw=(json.dumps(result,indent=2)+'\n').encode();(Cdir/(label+'-observation.json')).write_bytes(raw)
            observations.append({'label':label,'bytes':len(raw),'sha256':sha(raw)});C['observations']=observations
        C_observation(first_C,'first-reused');save()
        original_C=json.loads((inputs/'control/engines/compact/tiny-entry-c/recipe.json').read_text())
        if original_C['compiler']!=fixed['compiler']['C']:raise ValueError('originalCcompiler changed')
        native_dir=Cdir/'repeat/native';native_dir.mkdir(parents=True);report['new_native_compiles']['C']=1;report['cumulative_candidate_native_compiles']['C']=2;save()
        process=support.run(original_C['compiler'],native_dir,candidate_C);(native_dir/'compiler.stdout').write_bytes(process.stdout);(native_dir/'compiler.stderr').write_bytes(process.stderr)
        if process.returncode:raise ValueError('C repeatcompiler failed')
        repeat_C=(native_dir/'x').read_bytes();bound(repeat_C,fixed['C_images']['candidate'],'C independentrepeat')
        if repeat_C!=first_C:raise ValueError('C complete repeatimage differs')
        C_observation(repeat_C,'repeat');C.update(new_full_native_sha256=sha(repeat_C),native_bytes=len(repeat_C),two_native_bytes_exact=True,new_compiles=1,prior_compiles_reused=1,status='suffix_boundary_observed_native_reproduced_pending_root');save()
        print(json.dumps({'family':'C','native_reproduced':True,'new_compiles':1,'first_reused':True,'new_full_sha256':sha(repeat_C)}),flush=True)
        # E retains the ORIGINAL direct17 stored-Counter boundary without the C suffix exception.
        E=report['families']['E'];old_E=(reused/'control-E/native/x').read_bytes();source_E=(reused/'control-E/main.c').read_bytes()
        candidate_E,proof=policy.transform_source(source_E,family='E',lexer=lexer);Edir=out/'E';Edir.mkdir();(Edir/'main.c').write_bytes(candidate_E)
        original_E=json.loads((inputs/'control/engines/compact/tiny-entry-e/recipe.json').read_text())
        if original_E['compiler']!=fixed['compiler']['E']:raise ValueError('originalEcompiler changed')
        E['source_proof']=proof;E['header_gate']=support.header_gate(source_E,candidate_E,original_E['compiler'],source_fixed['mapping'],lexer,Edir/'header',family='E',
            configured_preprocessor=original_E['preprocessor'],readable=(inputs/'control/engines/compact/tiny-entry-e/engine.c').read_bytes(),reference=policy.reference)
        E['attempts']=[];first_E=None;save()
        for index in (1,2):
            directory=Edir/('attempt-'+str(index));directory.mkdir();(directory/'main.c').write_bytes(candidate_E);native_dir=directory/'native';native_dir.mkdir()
            report['new_native_compiles']['E']+=1;report['cumulative_candidate_native_compiles']['E']+=1;save()
            process=support.run(original_E['compiler'],native_dir,candidate_E);(native_dir/'compiler.stdout').write_bytes(process.stdout);(native_dir/'compiler.stderr').write_bytes(process.stderr)
            if process.returncode:raise ValueError('E candidatecompiler failed')
            image=(native_dir/'x').read_bytes();item={'attempt':index,'native_bytes':len(image),'new_full_native_sha256':sha(image),'old_full_native_equal':image==old_E};E['attempts'].append(item);save()
            result=direct.compare(old_E,image,symbol_pairs=source_fixed['families']['E']['literal_expected_symbol_pairs'])
            raw=(json.dumps(result,indent=2)+'\n').encode();(directory/'observation.json').write_bytes(raw);item['observation_sha256']=sha(raw)
            if first_E is None:first_E=image
            elif image!=first_E:raise ValueError('E complete native repeat differs')
            save()
        E.update(status='original_direct_boundary_observed_native_reproduced_pending_root',native_bytes=len(first_E),new_full_native_sha256=sha(first_E),two_native_bytes_exact=True)
        report.update(complete=True,original_failure_still_preserved=True,new_C_source_or_policy_variant=False,new_E_class_pending_root=True)
        save();print(json.dumps({'complete':True,'C_new_compiles':1,'E_new_compiles':2,'candidate_codec_calls':0,'engine_runs':0,'results_sha256':sha((out/'results.json').read_bytes())}),flush=True)
        return 0
    except BaseException as error:
        report['error']=repr(error);report['stop']='no furthernative/codec/engine after failure';save();raise
if __name__=='__main__':raise SystemExit(main())
