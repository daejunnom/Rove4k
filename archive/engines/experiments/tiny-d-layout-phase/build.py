#!/usr/bin/env python3
"""One fixed Board-layout plus search-phase composition; native cost only."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import signal
import struct
import subprocess
import sys
import time

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
RECIPE_SHA='2f8a83caeb73f5742507ee7cd4a6094c589002db010c6c24026abf68f4356760'
EXPECTED_NATIVE={
    'scalar-shipping':(8348,'0e21d39f5f294f496f2224595462661864b4a274f4c2238a38f47024f0c93bbf'),
    'hq-shipping':(8736,'6b987cc4f616ce9d835679c61d9aff8c0c16b59ec9a74db055c8ce826e14581f')}

def sha(data):return hashlib.sha256(data).hexdigest()

def module(path):
    spec=importlib.util.spec_from_file_location('frozen_layout_control_packer',path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve()
    if not args.out.is_absolute() or out.exists() or any((p/'.git').exists() for p in (out,*out.parents)) or HERE in out.parents:
        parser.error('a new absolute output outside any Git checkout is required')
    if sys.platform!='linux' or platform.machine()!='x86_64':parser.error('fixed Linux x86-64 target required')
    recipe_raw=(HERE/'recipe.json').read_bytes()
    if sha(recipe_raw)!=RECIPE_SHA:raise ValueError('fixed composition recipe changed')
    recipe=json.loads(recipe_raw)
    if recipe['format']!=1 or recipe['control_file_count']!=18 or len(recipe['control_files'])!=18:
        raise ValueError('exact raw18 source control required')
    transform=recipe['transformations']['board']
    if transform!={'file':'native/tiny.h','before':'typedef struct { int8_t b[128]; int s,c,e,k[2],half,v; uint64_t h,r; } Board;',
                   'after':'typedef struct { int s,c,e,k[2],half,v; uint64_t h,r; int8_t b[128]; } Board;','occurrences':1}:
        raise ValueError('only the one declared Board order is admitted')
    out.mkdir(parents=True);inputs=out/'inputs';inputs.mkdir()
    report={'complete':False,'scope':'one exact Board-order/search-phase composition; original full-image control then two combined native-only repeats per form',
        'source_checkpoint':recipe['source_checkpoint'],'inputs':{},'cases':{},'transformation_proofs':{},
        'packaging_executed':False,'codec_executed':False,'engine_execution':False,
        'original_admission_unchanged':True,'candidate_runtime_or_semantic_equivalence_qualified':False}
    deadline=time.monotonic()+150
    def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    def run(command,directory):
        remaining=min(60,deadline-time.monotonic())
        if remaining<=0:raise TimeoutError('bounded native comparison deadline')
        process=None;failed=None
        try:
            previous=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGTERM,signal.SIGINT})
            try:
                process=subprocess.Popen(command,cwd=directory,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                    start_new_session=True,preexec_fn=lambda:signal.pthread_sigmask(signal.SIG_SETMASK,previous))
            finally:signal.pthread_sigmask(signal.SIG_SETMASK,previous)
            stdout,stderr=process.communicate(timeout=remaining)
            record={'command':command,'returncode':process.returncode,'stdout':stdout.decode(errors='replace'),'stderr':stderr.decode(errors='replace')}
            (directory/'compile.json').write_text(json.dumps(record,indent=2)+'\n')
            if process.returncode:raise RuntimeError('compiler failed; original diagnostics preserved')
            return record
        except BaseException as error:
            failed={'type':type(error).__name__,'message':str(error)}
            raise
        finally:
            if process is not None:
                try:os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                if process.poll() is None:process.wait(timeout=3)
                if failed is not None:
                    stdout,stderr=process.communicate(timeout=3)
                    (directory/'failed-command.json').write_text(json.dumps({'command':command,'returncode':process.returncode,
                        'stdout':stdout.decode(errors='replace'),'stderr':stderr.decode(errors='replace'),'failure':failed},indent=2)+'\n')
    def cancelled(signum,frame):raise TimeoutError('parent cancelled native-only comparison')
    previous_handlers={number:signal.signal(number,cancelled) for number in (signal.SIGTERM,signal.SIGINT)}
    save()
    try:
        data_files={}
        for relative,pin in recipe['control_files'].items():
            path=Path(relative)
            if path.is_absolute() or '..' in path.parts:raise ValueError('unsafe control path')
            source=HERE/'control'/path
            if source.is_symlink() or not source.is_file():raise ValueError('nonregular control source')
            raw=source.read_bytes();data=raw.replace(b'\r\n',b'\n')
            if b'\r' in data or (len(raw),sha(raw))!=(pin['bytes'],pin['sha256']):raise ValueError('raw control changed: '+relative)
            target=inputs/'control'/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            data_files[relative]=data
            report['inputs'][relative]={'raw_bytes':len(raw),'raw_sha256':sha(raw),'LF_sha256':sha(data),'LF_normalized':data!=raw}
        for relative,pin in recipe['helper_files'].items():
            path=Path(relative)
            if path.is_absolute() or '..' in path.parts:raise ValueError('unsafe helper path')
            raw=(HERE/path).read_bytes()
            if (len(raw),sha(raw))!=(pin['bytes'],pin['sha256']):raise ValueError('frozen helper changed: '+relative)
            target=inputs/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
            report['inputs']['helper/'+relative]={'raw_bytes':len(raw),'raw_sha256':sha(raw)}
        phase_transform=module(inputs/'transform.py')
        phase=(inputs/'phase.c.in').read_bytes()
        for name in ('build.py','recipe.json'):
            raw=recipe_raw if name=='recipe.json' else (HERE/name).read_bytes()
            (inputs/name).write_bytes(raw)
            report['inputs']['producer/'+name]={'raw_bytes':len(raw),'raw_sha256':sha(raw)}
        original=json.loads(data_files['recipe.json'])
        if original['profile']!={'workers':2,'tt_bits':18,'ply':128,'dev':0}:raise ValueError('fixed control profile changed')
        if original['native_units']!=['board.c','search.c','runtime.c','hq.c','start.S']:raise ValueError('native unit order changed')
        for relative,pin in original['native_source_sha256'].items():
            if sha(data_files[relative])!=pin:raise ValueError('control native source does not match original recipe')
        for form,expected in original['expected'].items():
            if EXPECTED_NATIVE[form]!=(expected['native_bytes'],expected['native_sha256']):raise ValueError('old native literal changed')
        packer=module(inputs/'control/packer.py')
        for flavor in ('control','candidate'):
            sources=out/'sources'/flavor
            for relative,data in data_files.items():
                if not relative.startswith('native/'):continue
                if flavor=='candidate' and relative==transform['file']:
                    before,after=transform['before'].encode(),transform['after'].encode()
                    if data.count(before)!=1:raise ValueError('Board declaration shape/count changed')
                    changed=data.replace(before,after)
                    if changed.replace(after,b'__BOARD_DECL__')!=data.replace(before,b'__BOARD_DECL__'):raise ValueError('body complement changed')
                    data=changed
                if flavor=='candidate' and relative=='native/search.c':
                    data,proof=phase_transform.apply(data,phase)
                    fixed=recipe['transformations']['search']
                    if sha(data)!=fixed['candidate_sha256'] or len(data)!=fixed['candidate_bytes']:
                        raise ValueError('fixed search phase output differs')
                    report['transformation_proofs']['search']=proof
                if flavor=='candidate' and relative in recipe['candidate_sources']:
                    pin=recipe['candidate_sources'][relative]
                    if (len(data),sha(data))!=(pin['bytes'],pin['sha256']):raise ValueError('combined candidate source differs')
                target=sources/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            report.setdefault('source_forms',{})[flavor]={relative:sha((sources/relative).read_bytes()) for relative in original['native_source_sha256']}
        changed=[relative for relative in original['native_source_sha256']
            if report['source_forms']['control'][relative]!=report['source_forms']['candidate'][relative]]
        if changed!=['native/tiny.h','native/search.c']:raise ValueError('composition changed files outside exact two fragments')
        report['transformation_proofs']['board']={'file':'native/tiny.h','occurrences':1,'declaration':transform,
            'masked_source_complement_equal':True,'control_sha256':report['source_forms']['control']['native/tiny.h'],
            'candidate_sha256':report['source_forms']['candidate']['native/tiny.h']}
        report['transformation_proofs']['exact_changed_files']=changed
        report['transformation_proofs']['all_other_native_files_identical']=True
        report['tools']={}
        for name,command in {'cc':['cc','--version'],'ld':['ld','--version'],'python':['python3','--version']}.items():
            directory=out/'tool-versions'/name;directory.mkdir(parents=True)
            report['tools'][name]=run(command,directory)['stdout'].splitlines()[0]
        # Two original builds per form must pass unmodified admission before any candidate build.
        for flavor in ('control','candidate'):
            for form,expected in original['expected'].items():
                case={'attempts':[]};report['cases'][flavor+'/'+form]=case;save()
                first=None;sources=out/'sources'/flavor/'native'
                for number in (1,2):
                    directory=out/flavor/form/str(number);directory.mkdir(parents=True)
                    command=['cc',*original['native_flags'],f"-DD_HQ={expected['hq']}",'-DDEV=0',
                        *[str(sources/name) for name in original['native_units']],'-Wl,-T,'+str(sources/'image.ld'),'-o',str(directory/'linked')]
                    record=run(command,directory)
                    native=packer.strip_native((directory/'linked').read_bytes())
                    parsed=packer.elf(native);(directory/'x').write_bytes(native)
                    if first is not None and first!=native:raise ValueError('independent native repeats differ')
                    first=native
                    if flavor=='control':
                        packer.admit(native,expected,sha);admission={'accepted':True,'scope':'unchanged original full-image/layout guard'}
                    else:
                        try:packer.admit(native,expected,sha)
                        except ValueError as error:admission={'accepted':False,'error':str(error),'scope':'old production guard retained, no candidate expectation update'}
                        else:raise ValueError('changed candidate unexpectedly matched original admission')
                    image=next(segment for segment in parsed['segments'] if segment['type']==1 and segment['flags']==5)
                    bss=next(segment for segment in parsed['segments'] if segment['type']==1 and segment['flags']==6)
                    case['attempts'].append({'bytes':len(native),'sha256':sha(native),'path':str(directory/'x'),
                        'parsed_elf':parsed,'RX_pages':(image['memsz']+4095)&-4096,'bss':bss,
                        'original_admission':admission,'compile_record':str(directory/'compile.json')})
                    save()
                    if flavor=='candidate' and number==1:
                        print(json.dumps({'observation':'first_combined_native','form':form,'bytes':len(native),
                            'sha256':sha(native),'RX_pages':(image['memsz']+4095)&-4096,
                            'BSS_base':bss['vaddr'],'entry':parsed['entry'],'old_admission':admission}),flush=True)
                case['native_reproduced']=True
                print(json.dumps({'flavor':flavor,'form':form,'native_bytes':len(first),'sha256':sha(first),'original_admission':admission}),flush=True)
        for form in original['expected']:
            before=report['cases']['control/'+form]['attempts'][0];after=report['cases']['candidate/'+form]['attempts'][0]
            report.setdefault('comparison',{})[form]={'native_saved_bytes':before['bytes']-after['bytes'],
                'RX_pages_before':before['RX_pages'],'RX_pages_after':after['RX_pages'],
                'entry_before':before['parsed_elf']['entry'],'entry_after':after['parsed_elf']['entry'],
                'BSS_base_before':before['bss']['vaddr'],'BSS_base_after':after['bss']['vaddr'],
                'crossed_8192':before['bytes']>8192>=after['bytes'],'bss_segment_changed':before['bss']!=after['bss'],
                'old_production_guard_rejects_candidate':not after['original_admission']['accepted'],
                'packaging_or_runtime_authorized_or_run':False}
        for relative,pin in recipe['control_files'].items():
            if sha((HERE/'control'/relative).read_bytes())!=pin['sha256']:raise ValueError('frozen raw source drift during build')
        for relative,pin in recipe['helper_files'].items():
            if sha((HERE/relative).read_bytes())!=pin['sha256']:raise ValueError('frozen helper drift during build')
        report.update(complete=True,native_compilations=8,compiler_only_layout_probes=0,all_owned_commands_terminal=True,
            candidate_cost_is_actual_combined_not_additive=True)
        save();print(json.dumps({'complete':True,'out':str(out),'comparison':report['comparison']}),flush=True)
    except BaseException as error:
        report['failure']={'type':type(error).__name__,'message':str(error)};save();raise
    finally:
        for number,handler in previous_handlers.items():signal.signal(number,handler)

if __name__=='__main__':main()
