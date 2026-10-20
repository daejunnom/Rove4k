#!/usr/bin/env python3
"""Reproduce three frozen controls twice, then ONE B full-native attempt and hold."""
import argparse
import importlib.util
import json
from pathlib import Path
import platform
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
_spec=importlib.util.spec_from_file_location('bce_build_support',HERE/'support.py')
support=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(support)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve()
    if not args.out.is_absolute() or out.exists() or any((p/'.git').exists() for p in (out,*out.parents)):
        parser.error('new absolute output outside Git required')
    if platform.system()!='Linux' or platform.machine() not in ('x86_64','amd64'):parser.error('fixed Linux x86-64 target required')
    out.mkdir(parents=True);inputs=out/'inputs';recipe,rows=support.closure(inputs)
    report={'complete':False,'scope':'original BCE controls twice shipping+DEV; one B full-native attempt only, unconditional hold afterwards',
        'inputs':rows,'families':{f:{'status':'control_pending','candidate_native_compiles':0,'candidate_codec_calls':0,'candidate_whole_measurements':0,'engine_runs':0} for f in ('B','C','E')},
        'source_checkpoint':recipe['source_checkpoint'],'candidate_native_compiles':0,'candidate_codec_calls':0,'candidate_whole_measurements':0,'engine_runs':0,
        'native_policy':'original complete native SHA including build-ID/nonallocated data; no normalization, strip, or identity exception',
        'hold':'even if B native matches, do not compile B again or C/E candidates and do not package/execute any candidate'}
    def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        if set(recipe['policy_files'])!={'policy.py','policy.json','ownership.json','support.py','elf_observe.py'}:
            raise ValueError('literal producer policy closure changed')
        for name,pin in recipe['policy_files'].items():
            data=support.read(HERE/name)
            if support.sha(data)!=pin:raise ValueError('literal reviewed input changed: '+name)
            (inputs/name).write_bytes(data);report['inputs'][name]={'bytes':len(data),'sha256':support.sha(data)}
        data=support.read(HERE/'build.py');(inputs/'build.py').write_bytes(data);report['inputs']['build.py']={'bytes':len(data),'sha256':support.sha(data)}
        policy=support.module('bce_literal_policy',inputs/'policy.py');fixed=json.loads((inputs/'policy.json').read_text())
        lexer=support.module('bce_fixed_lexer',inputs/'control/engines/scripts/rename_c.py')
        observe=support.module('bce_elf_observer',inputs/'elf_observe.py')
        report['policy_sha256']=support.sha((inputs/'policy.json').read_bytes());save()
        # All three unchanged two-attempt controls must finish before ANY candidate native compilation.
        for family in ('B','C','E'):
            row=report['families'][family];selected=support.entry(inputs,family);original=json.loads((selected/'recipe.json').read_text())
            expected=original['expected']
            if expected!=recipe['control_expected'][family]:raise ValueError('frozen expected identities changed')
            control=out/('control-'+family);command=[sys.executable,'-I','-B',str(selected/'build.py'),'--out',str(control),'--dev']
            process=support.run(command,out,timeout=240)
            (out/('control-'+family+'.stdout')).write_bytes(process.stdout);(out/('control-'+family+'.stderr')).write_bytes(process.stderr)
            if process.returncode:raise ValueError('unchanged control builder failed: '+family)
            built=json.loads((control/'build.json').read_text())
            if not built['complete'] or len(built['attempts'])!=2 or not built['diagnostic_exact_control']:
                raise ValueError('two-control shipping+DEV reproduction incomplete')
            identities={}
            for key,path in [('source','main.c'),('native','native/x'),('whole','x'),('dev_source','dev/main.c'),('dev_native','dev/x'),('bootstrap','bootstrap.py')]:
                payload=(control/path).read_bytes()
                if support.sha(payload)!=expected[key+'_sha256']:raise ValueError('frozen control identity differs: '+family+'/'+key)
                if key+'_bytes' in expected and len(payload)!=expected[key+'_bytes']:raise ValueError('frozen control size differs')
                identities[key+'_bytes']=len(payload);identities[key+'_sha256']=support.sha(payload)
            row.update(status='control_exact_candidate_held',control={'complete':True,'independent_attempts':2,
                'build_receipt_sha256':support.sha((control/'build.json').read_bytes()),'shipping_and_DEV_each_twice':True,**identities})
            print(json.dumps({'family':family,'control':'shipping_and_DEV_twice_exact','whole_bytes':identities['whole_bytes']}),flush=True);save()
        family='B';row=report['families'][family];selected=support.entry(inputs,family);original=json.loads((selected/'recipe.json').read_text())
        source=(out/'control-B/main.c').read_bytes();native=(out/'control-B/native/x').read_bytes()
        candidate,metadata=policy.transform_source(source,family=family,lexer=lexer)
        candidate_root=out/'candidate-B';candidate_root.mkdir();(candidate_root/'main.c').write_bytes(candidate)
        row['candidate']={'policy':metadata,'source_bytes':len(candidate),'source_sha256':support.sha(candidate),'source_saved_bytes':len(source)-len(candidate)}
        row['header_gate']=support.header_gate(source,candidate,original['compiler'],fixed['mapping'],lexer,candidate_root/'header',
            family=family,configured_preprocessor=original['preprocessor'],readable=(selected/'engine.c').read_bytes(),reference=policy.reference);save()
        native_dir=candidate_root/'native';native_dir.mkdir()
        row['candidate_native_compiles']=1;report['candidate_native_compiles']=1;save()
        process=support.run(original['compiler'],native_dir,candidate)
        (native_dir/'compiler.stdout').write_bytes(process.stdout);(native_dir/'compiler.stderr').write_bytes(process.stderr)
        row['candidate']['compiler']=original['compiler'];row['candidate']['compiler_returncode']=process.returncode
        if process.returncode:raise ValueError('sole B candidate compiler failed; all candidates held')
        actual=(native_dir/'x').read_bytes();exact=actual==native
        row['candidate'].update(native_bytes=len(actual),native_sha256=support.sha(actual),expected_full_native_sha256=original['expected']['native_sha256'],full_native_exact=exact)
        observation=observe.compare(native,actual);observation_raw=(json.dumps(observation,indent=2)+'\n').encode()
        (candidate_root/'elf-observation.json').write_bytes(observation_raw)
        row['elf_observation']={'path':'candidate-B/elf-observation.json','bytes':len(observation_raw),'sha256':support.sha(observation_raw)}
        row['status']='native_exact_single_attempt_hold' if exact else 'full_native_identity_failed'
        row['candidate'].update(first_difference=observation['first_difference'],guard_exception=False)
        for other in ('C','E'):report['families'][other]['status']='control_exact_candidate_held_after_first_B_attempt'
        report.update(complete=True,all_three_controls_exact_twice=True,hard_hold_after_first_B_native=True,
            full_native_gate_pass=exact,stop_reason='fullnative differs; preserve failure and descriptive ELF observation' if not exact else 'single native matched; explicit scope still requires hold before secondcompile/codec/runtime')
        save();print(json.dumps({'family':'B','status':row['status'],'native_expected':original['expected']['native_sha256'],'native_actual':support.sha(actual),
            'candidate_native_compiles':1,'candidate_codec_calls':0,'candidate_whole_measurements':0,'engine_runs':0,'results_sha256':support.sha((out/'results.json').read_bytes())}),flush=True)
        return 0 if exact else 2
    except BaseException as error:
        report['error']=repr(error);save();raise


if __name__=='__main__':raise SystemExit(main())
