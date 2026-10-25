#!/usr/bin/env python3
"""One fixed E feature/dead fusion: exact control and source/native/whole cost only."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent

def sha(data):return hashlib.sha256(data).hexdigest()

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve()
    if not args.out.is_absolute() or out.exists() or any((p/'.git').exists() for p in (out,*out.parents)) or HERE in out.parents:
        parser.error('a new absolute output outside any Git checkout required')
    if sys.platform!='linux' or platform.machine()!='x86_64':parser.error('fixed Linux x86-64 target required')
    recipe_raw=(HERE/'recipe.json').read_bytes();recipe=json.loads(recipe_raw)
    if recipe['format']!=1 or recipe['control_source_count']!=17 or len(recipe['control_sources'])!=17 or recipe['runtime_authorized'] is not False:
        raise ValueError('fixed17 control and first-cost-only policy required')
    out.mkdir(parents=True);frozen=out/'source';frozen.mkdir()
    report={'complete':False,'scope':'one E shipping feature/dead fusion; unchanged fixed89 map/flags/codec; no engine execution',
        'control_inputs':{},'producer_inputs':{},'candidate_attempts':[],'engine_runs':0,'semantic_qualification':False,
        'old_native_identity_claimed_for_structural_candidate':False,'whole_acceptance':'cost observation only, not runtime or chess acceptance'}
    def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    deadline=time.monotonic()+180
    def cancelled(signum,frame):raise TimeoutError('parent cancelled E first-cost measurement')
    handlers={number:signal.signal(number,cancelled) for number in (signal.SIGTERM,signal.SIGINT)}
    def fixed_run(command,directory,input_data=None,timeout=180):
        directory.mkdir(parents=True,exist_ok=True)
        remaining=min(timeout,deadline-time.monotonic())
        if remaining<=0:raise TimeoutError('aggregate first-cost deadline')
        process=None;failure=None
        try:
            mask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGTERM,signal.SIGINT})
            try:process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=directory,
                start_new_session=True,env={**os.environ,'LC_ALL':'C','TZ':'UTC','SOURCE_DATE_EPOCH':'0'},
                preexec_fn=lambda:signal.pthread_sigmask(signal.SIG_SETMASK,mask))
            finally:signal.pthread_sigmask(signal.SIG_SETMASK,mask)
            stdout,stderr=process.communicate(input_data,timeout=remaining)
            return subprocess.CompletedProcess(command,process.returncode,stdout,stderr)
        except BaseException as error:failure={'type':type(error).__name__,'message':str(error)};raise
        finally:
            if process is not None:
                if process.poll() is None:
                    try:os.killpg(process.pid,signal.SIGTERM)
                    except ProcessLookupError:pass
                    try:process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        try:os.killpg(process.pid,signal.SIGKILL)
                        except ProcessLookupError:pass
                        process.wait(timeout=3)
                if failure is not None:
                    stdout,stderr=process.communicate(timeout=3)
                    (directory/'failed-command.json').write_text(json.dumps({'command':command,'returncode':process.returncode,
                        'stdout':stdout.decode(errors='replace'),'stderr':stderr.decode(errors='replace'),'failure':failure},indent=2)+'\n')
    save()
    try:
        for relative,pin in recipe['control_sources'].items():
            path=Path(relative)
            if path.is_absolute() or '..' in path.parts:raise ValueError('unsafe control path')
            raw=(HERE/'control'/path).read_bytes()
            if b'\r' in raw or (len(raw),sha(raw))!=(pin['bytes'],pin['sha256']):raise ValueError('fixed control source drift: '+relative)
            target=frozen/'control'/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
            report['control_inputs'][relative]=pin
        for name,pin in recipe['producer_sha256'].items():
            data=(HERE/name).read_bytes()
            if b'\r' in data or sha(data)!=pin:raise ValueError('fixed producer/admission drift: '+name)
            target=frozen/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            report['producer_inputs'][name]={'bytes':len(data),'sha256':sha(data)}
        for name,data in [('recipe.json',recipe_raw),('build.py',(HERE/'build.py').read_bytes())]:
            (frozen/name).write_bytes(data);report['producer_inputs'][name]={'bytes':len(data),'sha256':sha(data)}
        reference=module('fixed_header_and_package_reference',frozen/'tools/alpha_reference.py')
        reference.run=fixed_run
        if sha((frozen/'tools/alpha_reference.py').read_bytes())!=recipe['reference_helper_sha256']:raise ValueError('header/package utility changed')
        control=frozen/'control';entry=control/recipe['control_entry']
        original=json.loads((entry/'recipe.json').read_text());expected=recipe['expected_control']
        if original['family']!='E' or original['profile']!={'workers':2,'tt_bits':18,'ply':128,'dev_default':False}:raise ValueError('fixed E profile changed')
        report['tools']={name:reference.run(command,out/('version-'+name)).stdout.decode().splitlines()[0] for name,command in
            {'cc':['cc','--version'],'ld':['ld','--version'],'python':['python3','--version'],'xz':['xz','--version']}.items()}
        # Original maintained builder retains its own complete literal identity gates.
        baseline=out/'control-build'
        process=reference.run([sys.executable,'-B',str(entry/'build.py'),'--out',str(baseline)],out/'control-command')
        (out/'control.stdout').write_bytes(process.stdout);(out/'control.stderr').write_bytes(process.stderr)
        if process.returncode:raise RuntimeError('original E5679 control failed; outputs preserved')
        baseline_report=json.loads((baseline/'build.json').read_text())
        if not baseline_report['complete'] or len(baseline_report['attempts'])!=2:raise ValueError('control not independently reproduced')
        for filename,key in [('main.c','source_sha256'),('native/x','native_sha256'),('x','whole_sha256')]:
            if sha((baseline/filename).read_bytes())!=expected[key]:raise ValueError('original control differs: '+filename)
        if (baseline/'x').stat().st_size!=expected['whole_bytes']:raise ValueError('old whole size changed')
        report['control']={'complete':True,'build':str(baseline/'build.json'),'sha256':sha((baseline/'build.json').read_bytes()),'expected':expected}
        save();print(json.dumps({'control_complete':True,'whole_bytes':expected['whole_bytes']}),flush=True)
        transformed=module('fixed_feature_dead_transform',frozen/'transform.py')
        alias=module('fixed_candidate_alpha_admission',frozen/'alias_policy.py')
        policy=module('fixed_original_alpha_policy',control/'engines/scripts/fixed_shipping_alpha.py')
        lexer=module('fixed_original_c_lexer',control/'engines/scripts/rename_c.py')
        specialize=module('fixed_original_conditional_generator',control/'engines/scripts/specialize.py').specialize_c
        compact=module('fixed_original_lexical_compactor',control/'engines/scripts/minify.py').compact_source
        strip=module('fixed_original_counter_strip',control/'engines/compact/tiny-a/stitch.py').strip_dev_counters
        literal=module('fixed_original_source_literal',control/'engines/compact/tiny-a/pack_stream.py').source_literal
        candidate,transform_meta=transformed.transform_sources((entry/'engine.c').read_bytes())
        (out/'candidate-readable.c').write_bytes(candidate);report['transformation']=transform_meta
        admission=json.loads((frozen/'candidate-alias-admission.json').read_text())
        mapping=json.loads(policy._POLICY_BYTES)['mapping']
        first=None
        for number in (1,2):
            directory=out/('candidate-'+str(number));directory.mkdir()
            active,observation=specialize({'main.c':candidate},directory/'conditional',original['preprocessor']+['-DDEV=0'],dict(reference.os.environ))
            plain,_=strip(compact(active['main.c'],'c'))
            selected,alias_meta=alias.apply(plain,admission=admission,lexer=lexer,policy_module=policy)
            (directory/'before-alpha.c').write_bytes(plain);(directory/'main.c').write_bytes(selected)
            gate=reference.header_gate(plain,selected,original['compiler'],mapping,lexer,directory/'header-gate')
            binaries=[]
            for label,source in [('before-alpha',plain),('selected',selected)]:
                location=directory/label
                process=reference.run(original['compiler'],location,source,90)
                (location/'compiler.stderr').write_bytes(process.stderr)
                (location/'compiler.stdout').write_bytes(process.stdout)
                (location/'compile.json').write_text(json.dumps({'command':process.args,'cwd':str(location),
                    'returncode':process.returncode,'input_sha256':sha(source),'input_bytes':len(source),
                    'stdout_sha256':sha(process.stdout),'stderr_sha256':sha(process.stderr)},indent=2)+'\n')
                if process.returncode:raise RuntimeError('candidate compiler failed: '+label)
                binaries.append((location/'x').read_bytes())
            if binaries[0]!=binaries[1]:raise ValueError('candidate alpha changed entire native ELF; no identity exception admitted')
            whole,bootstrap=reference.package(selected,(entry/'bootstrap.py.in').read_bytes(),(entry/'launcher.sh').read_bytes(),literal,original['compression'])
            (directory/'x').write_bytes(whole);(directory/'bootstrap.py').write_bytes(bootstrap)
            current=(plain,selected,binaries[1],whole,bootstrap)
            if first is None:first=current
            elif first!=current:raise ValueError('independent candidate source/native/whole differs')
            row={'attempt':number,'plain_source_bytes':len(plain),'source_bytes':len(selected),'source_sha256':sha(selected),
                'native_bytes':len(binaries[1]),'native_sha256':sha(binaries[1]),'whole_bytes':len(whole),'whole_sha256':sha(whole),
                'bootstrap_sha256':sha(bootstrap),'conditional':observation,'alias':alias_meta,'actual_header_gate':gate,
                'candidate_before_after_alpha_entire_native_equal':True,'selected_native_path':str(directory/'selected/x'),
                'whole_path':str(directory/'x'),'old_native_same':sha(binaries[1])==expected['native_sha256']}
            report['candidate_attempts'].append(row);save()
            print(json.dumps({'candidate_attempt':number,'source_bytes':len(selected),'native_bytes':len(binaries[1]),'whole_bytes':len(whole),'whole_sha256':sha(whole)}),flush=True)
        for name,pin in recipe['producer_sha256'].items():
            if sha((HERE/name).read_bytes())!=pin:raise ValueError('producer changed during measurement')
        report.update(complete=True,candidate_independent_repeats=2,source_native_whole_and_bootstrap_equal=True,
            candidate_alpha_full_native_equal=True,whole_saved_bytes=expected['whole_bytes']-len(first[3]),
            actual_candidate_whole_bytes=len(first[3]),candidate_gain=len(first[3])<expected['whole_bytes'],
            all_commands_terminal=True,engine_or_semantic_tests_executed=False)
        save();print(json.dumps({'complete':True,'out':str(out),'whole_bytes':len(first[3]),'whole_saved_bytes':report['whole_saved_bytes'],'results_sha256':sha((out/'results.json').read_bytes())}),flush=True)
    except BaseException as error:
        report['failure']={'type':type(error).__name__,'message':str(error)};save();raise
    finally:
        for number,handler in handlers.items():signal.signal(number,handler)

if __name__=='__main__':main()
