#!/usr/bin/env python3
"""Metadata-only whole cost with the unchanged fixed codec/loader; never run."""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import zlib
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent

def sha(data):return hashlib.sha256(data).hexdigest()

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve()
    if sys.platform!='linux' or not args.out.is_absolute() or out.exists() or any((p/'.git').exists() for p in (out,*out.parents)) or SOURCE in out.parents:
        parser.error('Linux and a new absolute output outside any Git checkout required')
    recipe=json.loads((HERE/'recipe.json').read_text())
    if recipe['format']!=1 or recipe['runtime_authorized'] is not False or len(recipe['source22'])!=22:
        raise ValueError('fixed native22 and cost-only policy required')
    out.mkdir(parents=True);frozen=out/'source';frozen.mkdir()
    report={'complete':False,'scope':'actual metadata-only whole cost; one existing fixed codec/loader, original control first',
        'source22':{},'engines':[],'engine_execution':False,'old_production_admission_modified':False,
        'native_only_freeze_receipt_metadata':'7fbb3d041e4f695bf370b5342201b6bd8d67c1af445108175c7a8b5878005906',
        'original_whole_expected':recipe['expected_control_whole'],'cost_only_mapping':recipe['mapping']}
    deadline=time.monotonic()+180
    def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    def run(command):
        remaining=min(90,deadline-time.monotonic())
        if remaining<=0:raise TimeoutError('bounded whole-cost deadline')
        process=None;failed=None
        try:
            mask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGTERM,signal.SIGINT})
            try:process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,
                preexec_fn=lambda:signal.pthread_sigmask(signal.SIG_SETMASK,mask))
            finally:signal.pthread_sigmask(signal.SIG_SETMASK,mask)
            stdout,stderr=process.communicate(timeout=remaining)
            record={'command':command,'returncode':process.returncode,'stdout':stdout.decode(errors='replace'),'stderr':stderr.decode(errors='replace')}
            if process.returncode:
                (out/'failed-command.json').write_text(json.dumps(record,indent=2)+'\n');raise RuntimeError('cost command failed')
            return record
        except BaseException as error:failed={'type':type(error).__name__,'message':str(error)};raise
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
                if failed is not None:
                    stdout,stderr=process.communicate(timeout=3)
                    (out/'failed-command.json').write_text(json.dumps({'command':command,'returncode':process.returncode,
                        'stdout':stdout.decode(errors='replace'),'stderr':stderr.decode(errors='replace'),'failure':failed},indent=2)+'\n')
    def cancelled(signum,frame):raise TimeoutError('parent cancelled whole cost')
    handlers={n:signal.signal(n,cancelled) for n in (signal.SIGTERM,signal.SIGINT)}
    save()
    try:
        for relative,pin in recipe['source22'].items():
            path=Path(relative)
            if path.is_absolute() or '..' in path.parts:raise ValueError('unsafe source path')
            raw=(SOURCE/path).read_bytes()
            if b'\r' in raw or (len(raw),sha(raw))!=(pin['bytes'],pin['sha256']):raise ValueError('native-first source drift: '+relative)
            target=frozen/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
            report['source22'][relative]=pin
        for name in ('build.py','recipe.json'):
            raw=(HERE/name).read_bytes();target=frozen/'whole'/name;target.parent.mkdir(exist_ok=True);target.write_bytes(raw)
            report.setdefault('whole_producer',{})[name]={'bytes':len(raw),'sha256':sha(raw)}
        native_out=out/'native-first'
        produced=run([sys.executable,'-B',str(frozen/'build.py'),'--out',str(native_out)])
        (out/'native-command.json').write_text(json.dumps(produced,indent=2)+'\n')
        native_report=json.loads((native_out/'results.json').read_text())
        if not native_report['complete'] or native_report['engine_execution'] or native_report['codec_executed']:raise ValueError('native producer scope changed')
        report['tools']={'native':native_report['tools'],'python':sys.version,'zlib_build':zlib.ZLIB_VERSION,'zlib_runtime':zlib.ZLIB_RUNTIME_VERSION}
        control=json.loads((frozen/'control/recipe.json').read_text())
        packer=module('frozen_metadata_cost_packer',frozen/'control/packer.py')
        codec=module('frozen_metadata_cost_codec',frozen/'control/loader/codec.py')
        report['native_report_sha256']=sha((native_out/'results.json').read_bytes())
        for flavor in ('control','candidate'):
            for form,old_expected in control['expected'].items():
                attempts=native_report['cases'][flavor+'/'+form]['attempts']
                native=Path(attempts[0]['path']).read_bytes()
                if native!=Path(attempts[1]['path']).read_bytes():raise ValueError('native repeat drift')
                if flavor=='control':
                    layout=packer.admit(native,old_expected,sha)
                    expected=recipe['expected_control_whole'][form]
                    if (expected['bytes'],expected['sha256'])!=(old_expected['whole_bytes'],old_expected['whole_sha256']):raise ValueError('old whole literal changed')
                    admission='unmodified production admission accepts exact original control'
                else:
                    fixed=recipe['candidate_native'][form]
                    if (len(native),sha(native))!=(fixed['bytes'],fixed['sha256']):raise ValueError('unknown metadata-only native image')
                    # New cost-only declaration is exact and does not replace production admission.
                    try:packer.admit(native,old_expected,sha)
                    except ValueError as error:old_rejection=str(error)
                    else:raise ValueError('production guard unexpectedly accepted candidate')
                    layout=copy.deepcopy(old_expected['layout'])
                    layout['entry']=fixed['entry'];layout['image_size']=fixed['bytes']
                    layout['segments'][0]['filesz']=layout['segments'][0]['memsz']=fixed['bytes']
                    if any(layout[key]!=value for key,value in recipe['mapping'].items()):raise ValueError('old mapping class changed')
                    parsed=packer.elf(native)
                    if any(parsed[key]!=layout[key] for key in parsed):raise ValueError('candidate differs from explicit metadata-only ELF layout')
                    if not all(not row['original_admission']['accepted'] for row in attempts):raise ValueError('missing original native rejection')
                    expected=None;admission={'new_scope':'exact metadata-only cost admission','old_production_rejection':old_rejection}
                row={'flavor':flavor,'form':form,'native_bytes':len(native),'native_sha256':sha(native),
                    'layout':layout,'admission':admission,'whole_rebuilds':[]}
                report['engines'].append(row);save()
                first=None
                for number in (1,2):
                    payload=codec.fixed_compress(codec.bcj(native))
                    if codec.bcj(codec.fixed_decompress(payload,len(native)),inverse=True)!=native:raise ValueError('old codec roundtrip differs')
                    result=packer.compile_loader(out/flavor/form/str(number),frozen/'control/loader',payload,layout,control['loader_flags'],run,sha)
                    whole=Path(result['path']).read_bytes()
                    if first is not None and first!=(payload,whole):raise ValueError('independent complete repeats differ')
                    first=(payload,whole)
                    if expected and (len(whole),sha(whole))!=(expected['bytes'],expected['sha256']):raise ValueError('original whole control not reproduced')
                    row['whole_rebuilds'].append(result);save()
                row.update(whole_reproduced=True,whole_bytes=len(first[1]),whole_sha256=sha(first[1]),
                    payload_bytes=len(first[0]),overhead_bytes=len(first[1])-len(first[0]))
                print(json.dumps({'flavor':flavor,'form':form,'whole_bytes':len(first[1]),'payload_bytes':len(first[0]),'sha256':sha(first[1])}),flush=True)
        for relative,pin in recipe['source22'].items():
            if sha((SOURCE/relative).read_bytes())!=pin['sha256']:raise ValueError('native-first source changed during cost')
        report.update(complete=True,whole_compilations=8,whole_and_payload_reproduced=True,production_runtime_sessions=0,all_commands_terminal=True)
        save();print(json.dumps({'complete':True,'out':str(out),'results_sha256':sha((out/'results.json').read_bytes())}),flush=True)
    except BaseException as error:
        report['failure']={'type':type(error).__name__,'message':str(error)};save();raise
    finally:
        for number,handler in handlers.items():signal.signal(number,handler)

if __name__=='__main__':main()
