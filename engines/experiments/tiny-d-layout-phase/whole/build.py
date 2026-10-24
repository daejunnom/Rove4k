#!/usr/bin/env python3
"""Combined layout/phase whole cost with the unchanged fixed codec/loader; never run."""
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
RECIPE_SHA='af5fe72489a7b34c320f00ce943e5d30af0a72cc34c27afab63f2d68a2511397'
CLASS_KEYS=('image_pages','bss_base','bss_size','bss_pages','guard_base','reserve_size','upper_guard')
EXPLICIT_CLASSES={'scalar-shipping':(0x2000,0x402000,175092,0x2b000,0x3ff000,0x2f000,0x42d000),
    'hq-shipping':(0x3000,0x403000,175092,0x2b000,0x3ff000,0x30000,0x42e000)}

def sha(data):return hashlib.sha256(data).hexdigest()

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve()
    if sys.platform!='linux' or not args.out.is_absolute() or out.exists() or any((p/'.git').exists() for p in (out,*out.parents)) or SOURCE in out.parents:
        parser.error('Linux and a new absolute output outside any Git checkout required')
    recipe_raw=(HERE/'recipe.json').read_bytes()
    if sha(recipe_raw)!=RECIPE_SHA:raise ValueError('fixed whole-cost recipe changed')
    recipe=json.loads(recipe_raw)
    if (recipe['format']!=1 or recipe['runtime_authorized'] is not False or len(recipe['source25'])!=25
            or recipe['codec_fixed']!=1 or recipe['checkpoint']!=0):
        raise ValueError('fixed native25 and cost-only policy required')
    out.mkdir(parents=True);frozen=out/'source';frozen.mkdir()
    report={'complete':False,'scope':'actual combined Board-layout/search-phase whole cost; unchanged fixed codec/loader, original control first',
        'source25':{},'engines':[],'engine_execution':False,'old_production_admission_modified':False,
        'source25_freeze_metadata':'5c1f3c43f60b95f5b8ad381a6dad2d39b83656c1f0ec944d4f5bed0a0cde79fe',
        'native_only_provenance_metadata':'139d211714b139fae995633136a8b3caf6e4aec958060b8f827143460317d0f3',
        'original_whole_expected':recipe['expected_control_whole'],
        'cost_only_mapping':{form:fixed['layout'] for form,fixed in recipe['candidate_native'].items()},
        'mapping_scope':'literal root-reviewed cost declarations; guards/reserve are not native ELF segments or observed runtime mappings',
        'checkpoint':0,'codec_fixed':1}
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
        for relative,pin in recipe['source25'].items():
            path=Path(relative)
            if path.is_absolute() or '..' in path.parts:raise ValueError('unsafe source path')
            raw=(SOURCE/path).read_bytes()
            if b'\r' in raw or (len(raw),sha(raw))!=(pin['bytes'],pin['sha256']):raise ValueError('native-first source drift: '+relative)
            target=frozen/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
            report['source25'][relative]=pin
        for name in ('build.py','recipe.json','README.md'):
            raw=recipe_raw if name=='recipe.json' else (HERE/name).read_bytes()
            target=frozen/'whole'/name;target.parent.mkdir(exist_ok=True);target.write_bytes(raw)
            report.setdefault('whole_producer',{})[name]={'bytes':len(raw),'sha256':sha(raw)}
        native_out=out/'native-first'
        produced=run([sys.executable,'-B',str(frozen/'build.py'),'--out',str(native_out)])
        (out/'native-command.json').write_text(json.dumps(produced,indent=2)+'\n')
        native_report=json.loads((native_out/'results.json').read_text())
        if (not native_report['complete'] or native_report['engine_execution'] or native_report['codec_executed']
                or native_report['native_compilations']!=8 or native_report['compiler_only_layout_probes']!=0
                or native_report['transformation_proofs']['exact_changed_files']!=['native/tiny.h','native/search.c']):
            raise ValueError('native producer scope changed')
        if recipe['source_only_native_producer_sha256']!=recipe['source25']['build.py']['sha256']:
            raise ValueError('native producer pin differs')
        report['tools']={'native':native_report['tools'],'python':sys.version,'zlib_build':zlib.ZLIB_VERSION,'zlib_runtime':zlib.ZLIB_RUNTIME_VERSION}
        control=json.loads((frozen/'control/recipe.json').read_text())
        packer=module('frozen_combined_cost_packer',frozen/'control/packer.py')
        codec=module('frozen_combined_cost_codec',frozen/'control/loader/codec.py')
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
                    if (len(native),sha(native))!=(fixed['bytes'],fixed['sha256']):raise ValueError('unknown combined-layout-phase native image')
                    # New cost-only declaration is exact and does not replace production admission.
                    try:packer.admit(native,old_expected,sha)
                    except ValueError as error:old_rejection=str(error)
                    else:raise ValueError('production guard unexpectedly accepted candidate')
                    layout=copy.deepcopy(fixed['layout'])
                    if tuple(layout[key] for key in CLASS_KEYS)!=EXPLICIT_CLASSES[form]:
                        raise ValueError('candidate cost mapping differs from the two literal classes')
                    if (layout['image_base']!=0x400000 or layout['entry']!=fixed['entry']
                            or layout['image_size']!=fixed['bytes']
                            or layout['image_pages']!=(len(native)+4095)//4096*4096
                            or layout['bss_pages']!=(layout['bss_size']+4095)//4096*4096
                            or layout['bss_base']!=layout['image_base']+layout['image_pages']
                            or layout['guard_base']!=layout['image_base']-4096
                            or layout['upper_guard']!=layout['bss_base']+layout['bss_pages']
                            or layout['reserve_size']!=layout['upper_guard']+4096-layout['guard_base']):
                        raise ValueError('root-declared cost-only geometry is inconsistent')
                    parsed=packer.elf(native)
                    if any(parsed[key]!=layout[key] for key in parsed):
                        raise ValueError('candidate differs from explicit full literal ELF layout')
                    if not all(not row['original_admission']['accepted'] for row in attempts):raise ValueError('missing original native rejection')
                    expected=None;admission={'new_scope':'exact combined native/ELF cost admission only; root-declared loader macro geometry, no observed physical mapping',
                        'old_production_rejection':old_rejection,'production_admission_replaced':False}
                row={'flavor':flavor,'form':form,'native_bytes':len(native),'native_sha256':sha(native),
                    'layout':layout,'admission':admission,'whole_rebuilds':[]}
                report['engines'].append(row);save()
                first=None
                for number in (1,2):
                    payload=codec.fixed_compress(codec.bcj(native))
                    if codec.bcj(codec.fixed_decompress(payload,len(native)),inverse=True)!=native:raise ValueError('old codec roundtrip differs')
                    result=packer.compile_loader(out/flavor/form/str(number),frozen/'control/loader',payload,layout,control['loader_flags'],run,sha,checkpoint=False)
                    if result['definitions']['CODEC_FIXED']!=1 or result['definitions']['CHECKPOINT']!=0:
                        raise ValueError('fixed codec/checkpoint macros changed')
                    whole=Path(result['path']).read_bytes()
                    if first is not None and first!=(payload,whole):raise ValueError('independent complete repeats differ')
                    first=(payload,whole)
                    if expected and (len(whole),sha(whole))!=(expected['bytes'],expected['sha256']):raise ValueError('original whole control not reproduced')
                    row['whole_rebuilds'].append(result);save()
                    if flavor=='candidate' and number==1:
                        print(json.dumps({'observation':'first_actual_combined_whole','form':form,
                            'bytes':len(whole),'sha256':sha(whole),'payload_bytes':len(payload),
                            'loader_and_headers_bytes':result['loader_and_headers_bytes']}),flush=True)
                row.update(whole_reproduced=True,whole_bytes=len(first[1]),whole_sha256=sha(first[1]),
                    payload_bytes=len(first[0]),overhead_bytes=len(first[1])-len(first[0]))
                print(json.dumps({'flavor':flavor,'form':form,'whole_bytes':len(first[1]),'payload_bytes':len(first[0]),'sha256':sha(first[1])}),flush=True)
        for relative,pin in recipe['source25'].items():
            if sha((SOURCE/relative).read_bytes())!=pin['sha256']:raise ValueError('native-first source changed during cost')
        report.update(complete=True,whole_compilations=8,whole_and_payload_reproduced=True,production_runtime_sessions=0,all_commands_terminal=True)
        save();print(json.dumps({'complete':True,'out':str(out),'results_sha256':sha((out/'results.json').read_bytes())}),flush=True)
    except BaseException as error:
        report['failure']={'type':type(error).__name__,'message':str(error)};save();raise
    finally:
        for number,handler in handlers.items():signal.signal(number,handler)

if __name__=='__main__':main()
