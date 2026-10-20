#!/usr/bin/env python3
"""CurrentCE fixed storage18 native-first observation; candidate codecs/engines0."""
import argparse
import importlib.util
import json
from pathlib import Path
import platform
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
_spec=importlib.util.spec_from_file_location('ce_build_support',HERE/'support.py')
support=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(support)
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();out=args.out.resolve()
    if not args.out.is_absolute() or out.exists() or any((p/'.git').exists() for p in (out,*out.parents)):parser.error('newexternalabsoluteout required')
    if platform.system()!='Linux' or platform.machine() not in ('x86_64','amd64'):parser.error('fixed Linux x86-64 target required')
    out.mkdir(parents=True);inputs=out/'inputs';recipe,rows=support.closure(inputs)
    report={'complete':False,'scope':'currentC5687/E5679 baselineeach2shipping then fixedstorage18 candidate nativefirst+repeat only',
        'comparison_class':'distinct unstripped image observations; original full-native identity is not equated or normalized',
        'inputs':rows,'families':{f:{'status':'control_pending','candidate_native_compiles':0,'candidate_codec_calls':0,'engine_runs':0} for f in ('C','E')},
        'source_checkpoint':recipe['source_checkpoint'],'candidate_codec_calls':0,'candidate_whole_measurements':0,'engine_runs':0,
        'old_B_qualifier_imported_or_modified':False,'new_class_admission':'pending root review; no general semantic/ABI/runtime/promotion claim'}
    def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        if set(recipe['producer_files'])!={'policy.py','policy.json','ownership.json','support.py','observe.py'}:raise ValueError('fixedproducerclosure changed')
        for name,pin in recipe['producer_files'].items():
            data=support.read(HERE/name)
            if support.sha(data)!=pin:raise ValueError('reviewedproducerinput changed: '+name)
            (inputs/name).write_bytes(data);report['inputs'][name]={'bytes':len(data),'sha256':support.sha(data)}
        data=support.read(HERE/'build.py');(inputs/'build.py').write_bytes(data);report['inputs']['build.py']={'bytes':len(data),'sha256':support.sha(data)}
        if len(report['inputs'])!=recipe['producer_input_file_count']:raise ValueError('closedinputcount differs')
        policy=support.module('ce_build_policy',inputs/'policy.py');fixed=json.loads(policy.POLICY_BYTES)
        lexer=support.module('ce_build_lexer',inputs/'control/engines/scripts/rename_c.py');observe=support.module('ce_build_observe',inputs/'observe.py')
        report['policy_sha256']=policy.POLICY_SHA256;save()
        # Complete BOTH original two-attempt baselines before either candidate native.
        for family in ('C','E'):
            row=report['families'][family];selected=support.entry(inputs,family);original=json.loads((selected/'recipe.json').read_text());expected=original['expected']
            if expected!=recipe['control_expected'][family]:raise ValueError('literalcurrentcontrol expected changed')
            control=out/('control-'+family);command=[sys.executable,'-I','-B',str(selected/'build.py'),'--out',str(control)]
            process=support.run(command,out,timeout=180)
            (out/('control-'+family+'.stdout')).write_bytes(process.stdout);(out/('control-'+family+'.stderr')).write_bytes(process.stderr)
            if process.returncode:raise ValueError('originalcontrolbuilder failed: '+family)
            built=json.loads((control/'build.json').read_text())
            if not built['complete'] or len(built['attempts'])!=2 or built['diagnostic_exact_control']:raise ValueError('original2shipping baseline incomplete/unexpectedDEV')
            identities={}
            for key,path in [('source','main.c'),('native','native/x'),('whole','x'),('bootstrap','bootstrap.py')]:
                payload=(control/path).read_bytes()
                if support.sha(payload)!=expected[key+'_sha256']:raise ValueError('baselinefullidentity differs: '+family+'/'+key)
                if key+'_bytes' in expected and len(payload)!=expected[key+'_bytes']:raise ValueError('baselinebytes differ')
                identities[key+'_bytes']=len(payload);identities[key+'_sha256']=support.sha(payload)
            row.update(status='baseline_twice_exact_candidate_pending',control={'independent_shipping_attempts':2,'DEV':'unchangedordinarysource; no DEVcompile thisstudy',
                'receipt_sha256':support.sha((control/'build.json').read_bytes()),**identities});save()
            print(json.dumps({'family':family,'baseline':'twice_exact','whole_bytes':identities['whole_bytes']}),flush=True)
        for family in ('C','E'):
            row=report['families'][family];selected=support.entry(inputs,family);original=json.loads((selected/'recipe.json').read_text())
            source=(out/('control-'+family)/'main.c').read_bytes();old=(out/('control-'+family)/'native/x').read_bytes()
            candidate,source_proof=policy.transform_source(source,family=family,lexer=lexer);directory=out/('candidate-'+family);directory.mkdir()
            (directory/'main.c').write_bytes(candidate);row['source_proof']=source_proof
            row['header_gate']=support.header_gate(source,candidate,original['compiler'],fixed['mapping'],lexer,directory/'header',family=family,
                configured_preprocessor=original['preprocessor'],readable=(selected/'engine.c').read_bytes(),reference=policy.reference)
            pairs=fixed['families'][family]['literal_expected_symbol_pairs']
            if len(pairs)!=17 or fixed['families'][family]['symbol_pair_count']!=17:raise ValueError('CE-specificliteral17 symbol boundary changed')
            first=None;row['attempts']=[];save()
            for index in (1,2):
                repeated,proof=policy.transform_source(source,family=family,lexer=lexer)
                if repeated!=candidate or proof!=source_proof:raise ValueError('fixedsource transformation didnot reproduce')
                attempt=directory/('attempt-'+str(index));attempt.mkdir();(attempt/'main.c').write_bytes(repeated);native_dir=attempt/'native';native_dir.mkdir()
                row['candidate_native_compiles']+=1;save();process=support.run(original['compiler'],native_dir,repeated)
                (native_dir/'compiler.stdout').write_bytes(process.stdout);(native_dir/'compiler.stderr').write_bytes(process.stderr)
                item={'attempt':index,'compiler':original['compiler'],'compiler_returncode':process.returncode,'source_bytes':len(repeated),'source_sha256':support.sha(repeated)}
                row['attempts'].append(item);save()
                if process.returncode:raise ValueError('candidatecompiler failed')
                actual=(native_dir/'x').read_bytes();item.update(native_bytes=len(actual),new_full_native_sha256=support.sha(actual),
                    old_full_native_sha256=support.sha(old),old_full_native_equal=actual==old,
                    first_difference=next((i for i,(a,b) in enumerate(zip(old,actual)) if a!=b),min(len(old),len(actual))))
                save()
                observation=observe.compare(old,actual,symbol_pairs=pairs)
                raw=(json.dumps(observation,indent=2)+'\n').encode();(attempt/'observation.json').write_bytes(raw)
                item.update(observation_sha256=support.sha(raw),observation_boundary_matched=True,new_class_qualified=False)
                if first is None:first=actual
                elif actual!=first:raise ValueError('independentcomplete candidate native bytes differ')
                save()
            (directory/'native').mkdir();(directory/'native/x').write_bytes(first)
            row.update(status='new_native_reproduced_observation_pending_root',candidate={'source_bytes':len(candidate),'source_sha256':support.sha(candidate),
                'source_saved_bytes':len(source)-len(candidate),'native_bytes':len(first),'new_full_native_sha256':support.sha(first),'old_full_native_sha256':support.sha(old),
                'old_full_native_equal':first==old,'independent_native_attempts':2,'metadata_qualified':False,'whole':'not measured; authorization withheld'})
            save();print(json.dumps({'family':family,'status':row['status'],'source_saved_bytes':len(source)-len(candidate),'native_bytes':len(first),
                'new_full_native_sha256':support.sha(first),'old_full_native_equal':first==old,'candidate_codec_calls':0,'engine_runs':0}),flush=True)
        report.update(complete=True,all_baselines_twice_exact=True,all_candidates_two_native_reproduced=True,all_candidate_classes_pending_root=True)
        save();print(json.dumps({'complete':True,'results_sha256':support.sha((out/'results.json').read_bytes()),'candidate_codec_calls':0,'engine_runs':0}),flush=True)
        return 0
    except BaseException as error:
        report['error']=repr(error);report['stop']='no furthercandidatecompile/codec/engine after this failure';save();raise
if __name__=='__main__':raise SystemExit(main())
