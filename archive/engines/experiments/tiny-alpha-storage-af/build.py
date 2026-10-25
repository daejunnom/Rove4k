#!/usr/bin/env python3
"""One fixed storage18 policy, strict PP/full-native gates, first cost only."""
import argparse
import importlib.util
import json
from pathlib import Path
import platform
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
_spec=importlib.util.spec_from_file_location('af_build_support',HERE/'support.py')
support=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(support)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve()
    if not args.out.is_absolute() or out.exists() or any((p/'.git').exists() for p in (out,*out.parents)):
        parser.error('new absolute output outside Git required')
    if platform.system()!='Linux' or platform.machine() not in ('x86_64','amd64'):
        parser.error('qualified target is Linux x86-64')
    out.mkdir(parents=True);inputs=out/'inputs'
    recipe,rows=support.closure(inputs)
    report={'complete':False,'scope':'one fixed18 final storage alias stage after frozen A31/F73; first cost only, no engine execution or canonical promotion',
        'inputs':rows,'families':{},'engine_runs':0,'source_checkpoint':recipe['source_checkpoint'],
        'native_policy':'original complete native SHA including build-ID and nonallocated sections; no exceptions',
        'runtime_gate':'separate selected wrapper only after native exact and actual whole-file gain'}
    def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        if set(recipe['policy_files'])!={'policy.py','policy.json','ownership.json','support.py'}:raise ValueError('literal policy closure changed')
        for name,pin in recipe['policy_files'].items():
            data=support.read(HERE/name)
            if support.sha(data)!=pin:raise ValueError('literal reviewed policy input changed: '+name)
            (inputs/name).write_bytes(data);report['inputs'][name]={'bytes':len(data),'sha256':support.sha(data)}
        data=support.read(HERE/'build.py');(inputs/'build.py').write_bytes(data)
        report['inputs']['build.py']={'bytes':len(data),'sha256':support.sha(data)}
        policy=support.module('af_literal_policy',inputs/'policy.py')
        fixed=json.loads((inputs/'policy.json').read_text());mapping=fixed['mapping']
        lexer=support.module('af_fixed_lexer',inputs/'control/engines/scripts/rename_c.py')
        literal=support.module('af_fixed_literal',inputs/'control/engines/compact/tiny-a/pack_stream.py').source_literal
        report['policy_sha256']=support.sha((inputs/'policy.json').read_bytes());save()
        for family in ('A','F'):
            row={'status':'started','control':{},'candidate':{},'engine_runs':0};report['families'][family]=row;save()
            try:
                selected=support.entry(inputs,family);original=json.loads((selected/'recipe.json').read_text());expected=original['expected']
                if expected!=recipe['control_expected'][family]:raise ValueError('historical expected identities changed')
                control=out/('control-'+family)
                command=[sys.executable,'-I','-B',str(selected/'build.py'),'--out',str(control),'--dev']
                process=support.run(command,out,timeout=240)
                (out/('control-'+family+'.stdout')).write_bytes(process.stdout);(out/('control-'+family+'.stderr')).write_bytes(process.stderr)
                if process.returncode:raise ValueError('unchanged historical control builder failed')
                built=json.loads((control/'build.json').read_text())
                if not built['complete'] or len(built['attempts'])!=2 or not built['diagnostic_exact_control']:
                    raise ValueError('historical control reproduction incomplete')
                source=(control/'main.c').read_bytes();native=(control/'native/x').read_bytes();whole=(control/'x').read_bytes()
                for data,key in ((source,'source'),(native,'native'),(whole,'whole')):
                    if support.sha(data)!=expected[key+'_sha256']:raise ValueError('exact historical control changed: '+key)
                row['control']={'complete':True,'independent_attempts':2,'build_receipt_sha256':support.sha((control/'build.json').read_bytes()),
                    'source_bytes':len(source),'source_sha256':support.sha(source),'native_bytes':len(native),'native_sha256':support.sha(native),
                    'whole_bytes':len(whole),'whole_sha256':support.sha(whole),'DEV_unchanged_two_compiles':True,
                    'dev_source_sha256':expected['dev_source_sha256'],'dev_native_sha256':expected['dev_native_sha256']}
                candidate,metadata=policy.transform_source(source,family=family,lexer=lexer)
                candidate_root=out/('candidate-'+family);candidate_root.mkdir();row['candidate']['policy']=metadata
                row['header_gate']=support.header_gate(source,candidate,original['compiler'],mapping,lexer,candidate_root/'header',
                    family=family,configured_preprocessor=original['preprocessor'],readable=(selected/'engine.c').read_bytes());save()
                attempts=[];compiled=[];first=None
                for attempt in (1,2):
                    repeated,meta=policy.transform_source(source,family=family,lexer=lexer)
                    if repeated!=candidate or meta!=metadata:raise ValueError('fixed pure policy did not reproduce')
                    directory=candidate_root/('attempt-'+str(attempt));directory.mkdir();(directory/'main.c').write_bytes(repeated)
                    native_dir=directory/'native';native_dir.mkdir()
                    process=support.run(original['compiler'],native_dir,repeated)
                    (native_dir/'compiler.stderr').write_bytes(process.stderr)
                    if process.returncode:raise ValueError('candidate compiler failed')
                    actual=(native_dir/'x').read_bytes()
                    item={'attempt':attempt,'source_bytes':len(repeated),'source_sha256':support.sha(repeated),
                          'native_bytes':len(actual),'native_sha256':support.sha(actual),'compiler':original['compiler']}
                    attempts.append(item);row['candidate']['attempts']=attempts;save()
                    if support.sha(actual)!=expected['native_sha256']:
                        item['identity_failure']={'expected_full_sha256':expected['native_sha256'],
                            'first_difference':next((i for i,(a,b) in enumerate(zip(native,actual)) if a!=b),min(len(native),len(actual))),
                            'guard_exception':False}
                        raise ValueError('complete native SHA differs; stopped before candidate codec/runtime')
                    compiled.append((directory,repeated,actual,item))
                # Neither candidate codec is called before BOTH full ELF gates.
                for directory,repeated,actual,item in compiled:
                    packed,script,kind=support.package(repeated,selected,original,literal)
                    (directory/'x').write_bytes(packed);(directory/'x').chmod(0o755);(directory/'bootstrap.py').write_bytes(script)
                    item.update(whole_bytes=len(packed),whole_sha256=support.sha(packed),bootstrap_sha256=support.sha(script),literal=kind)
                    current=(repeated,actual,packed,script)
                    if first is None:first=current
                    elif current!=first:raise ValueError('candidate complete outputs did not reproduce')
                (candidate_root/'main.c').write_bytes(first[0]);(candidate_root/'native').mkdir()
                (candidate_root/'native/x').write_bytes(first[1]);(candidate_root/'native/x').chmod(0o755)
                (candidate_root/'x').write_bytes(first[2]);(candidate_root/'x').chmod(0o755);(candidate_root/'bootstrap.py').write_bytes(first[3])
                row['candidate'].update(independent_attempts=2,source_bytes=len(first[0]),source_sha256=support.sha(first[0]),
                    native_bytes=len(first[1]),native_sha256=support.sha(first[1]),whole_bytes=len(first[2]),whole_sha256=support.sha(first[2]),
                    bootstrap_sha256=support.sha(first[3]),full_native_exact=True,source_saved_bytes=len(source)-len(first[0]),
                    whole_saved_bytes=len(whole)-len(first[2]),under_4096_bytes=len(first[2])<=4096,DEV='not transformed')
                row['status']='gain_native_exact_runtime_pending' if len(first[2])<len(whole) else 'no_gain_stopped_without_runtime'
                print(json.dumps({'family':family,'status':row['status'],'source_saved_bytes':len(source)-len(first[0]),
                    'control_whole_bytes':len(whole),'candidate_whole_bytes':len(first[2]),'whole_saved_bytes':len(whole)-len(first[2]),
                    'native_full_exact':True}),flush=True)
            except Exception as error:
                row.update(status='stopped',error=repr(error),engine_runs=0)
                print(json.dumps({'family':family,'status':'stopped','error':repr(error)}),flush=True)
                report['hard_gate_stop_after_family']=family
                save()
                break
            save()
        report['complete']=True;save();print(json.dumps({'complete':True,'out':str(out),'results_sha256':support.sha((out/'results.json').read_bytes())}),flush=True)
        return 1 if any(row['status']=='stopped' for row in report['families'].values()) else 0
    except Exception as error:
        report['error']=repr(error);save();raise


if __name__=='__main__':raise SystemExit(main())
