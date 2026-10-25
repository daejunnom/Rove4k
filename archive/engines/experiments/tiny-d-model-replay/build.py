#!/usr/bin/env python3
"""One fixed21 replay source freeze and sequential bounded positive first cost."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import struct
import subprocess
import sys
import time

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
FILES=('.gitattributes','README.md','build.py','recipe.json','decoder.h','diagnostic.c')

def sha(b):return hashlib.sha256(b).hexdigest()
def ident(p):
    b=p.read_bytes();return {'bytes':len(b),'sha256':sha(b)}
def save(p,d):
    temporary=p.with_suffix(p.suffix+'.tmp')
    temporary.write_text(json.dumps(d,indent=2)+'\n');temporary.replace(p)
def module(p):
    spec=importlib.util.spec_from_file_location('fixed_d_source_packer',p)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

def outside(p,new=False):
    if not p.is_absolute() or any((x/'.git').exists()for x in (p,*p.parents)):
        raise ValueError('absolute output outside Git required')
    if new and p.exists():raise ValueError('new output required')

def normal_map(normal,recipe):
    actual={n:ident(normal/n)for n in recipe['normal21']}
    if actual!=recipe['normal21']:raise ValueError('normal21 differs')
    return actual

def prepare(out):
    outside(out,True)
    if sys.platform!='linux':raise ValueError('Linux preparation required')
    recipe=json.loads((HERE/'recipe.json').read_bytes())
    normal=HERE.parents[1]/'compact/tiny-entry-d'
    normal_map(normal,recipe)
    out.mkdir(parents=True)
    report={'complete':False,'phase':'source_prepare_only','source_import_compile_codec_target':0,'normal_root':str(normal),'own_source':{},'frozen_source':{},'native_inputs':{}}
    try:
        (out/'owned').mkdir();loader=out/'sources/loader';loader.mkdir(parents=True)
        for n in FILES:
            b=(HERE/n).read_bytes()
            if b'\r'in b:raise ValueError('LF source required: '+n)
            (out/'owned'/n).write_bytes(b);report['own_source'][n]=ident(HERE/n)
        for n in ('loader.c','image.ld','range_bits.py','models.json'):
            (loader/n).write_bytes((normal/'loader'/n).read_bytes())
        (loader/'decoder.h').write_bytes((HERE/'decoder.h').read_bytes())
        codec=(normal/'loader/codec.py').read_text()
        replacements=[
          ("FORMAT='rove4k-context-h24-base10-u32-zero4-v1'", "FORMAT='rove4k-context-h24-base10-u32-zero4-v1'\nPACKET_FORMAT='rove4k-context-h24-base10-fixed21-replay-zero4-v2'"),
          ("header=struct.pack('<II',len(data)*8+1,weightmask)+masks",'header=masks'),
          ("return payload,{'format':FORMAT,", "return payload,{'format':PACKET_FORMAT,")]
        for old,new in replacements:
            if codec.count(old)!=1:raise ValueError('exact codec fragment differs')
            codec=codec.replace(old,new)
        (loader/'codec.py').write_text(codec)
        (out/'sources/packer.py').write_bytes((normal/'packer.py').read_bytes())
        for form,f in recipe['forms'].items():
            p=Path(f['native_input']);e=recipe['expected_native_and_old_controls'][form]
            if ident(p)!={'bytes':e['native_bytes'],'sha256':e['native_sha256']}:raise ValueError('native input identity differs')
            d=out/'native-inputs'/form;d.mkdir(parents=True);(d/'x').write_bytes(p.read_bytes())
            report['native_inputs'][form]={'source':str(p),'copy':str(d/'x'),**ident(d/'x')}
        for p in sorted((out/'sources').rglob('*')):
            if p.is_file():report['frozen_source'][str(p.relative_to(out))]=ident(p)
        report['normal21']=normal_map(normal,recipe);report['complete']=True
    except BaseException as e:
        report['failure']={'type':type(e).__name__,'message':str(e)};raise
    finally:save(out/'prepare.json',report)
    print(json.dumps({'complete':True,'prepare':ident(out/'prepare.json'),'own_source':report['own_source'],'frozen_source':report['frozen_source'],'native_inputs':report['native_inputs']}),flush=True)

def sections(b):
    off=struct.unpack_from('<Q',b,40)[0];stride,count,names=struct.unpack_from('<HHH',b,58)
    if not off or stride!=64 or not 0<names<count or off+stride*count>len(b):raise ValueError('linked section bounds')
    entries=[struct.unpack_from('<IIQQQQIIQQ',b,off+i*stride)for i in range(count)]
    if any(e[5] and e[1] in (4,6,9,11)for e in entries):raise ValueError('unexpected relocation/dynamic section')
    s=entries[names];strings=b[s[4]:s[4]+s[5]]
    return {strings[s[0]:].split(b'\0',1)[0].decode():{'type':s[1],'flags':s[2],'address':s[3],'offset':s[4],'bytes':s[5],'alignment':s[8]}for s in entries}

def execute(out):
    outside(out)
    if sys.platform!='linux':raise ValueError('Linux execution required')
    import resource
    prep=json.loads((out/'prepare.json').read_bytes())
    if not prep['complete']:raise ValueError('incomplete source freeze')
    for n,e in prep['own_source'].items():
        if ident(HERE/n)!=e or ident(out/'owned'/n)!=e:raise ValueError('ordinary source changed after freeze: '+n)
    for n,e in prep['frozen_source'].items():
        if ident(out/n)!=e:raise ValueError('frozen source changed: '+n)
    recipe=json.loads((out/'owned/recipe.json').read_bytes());normal=Path(prep['normal_root']);normal_map(normal,recipe)
    marker=out/'run-started.json'
    with marker.open('x')as f:json.dump({'source_prepare_sha256':sha((out/'prepare.json').read_bytes())},f)
    start=time.monotonic();deadline=start+recipe['limits']['aggregate_wall_seconds']
    report={'complete':False,'status':'RUNNING','prepare':ident(out/'prepare.json'),'normal21_before':prep['normal21'],'commands':[],'forms':[],
      'native_compiles':0,'control_compiles':0,'control_encodes':0,'audit_compiles':0,'shipping_or_audit_runs':0,'negative_cases':0,'sweeps':0,'sequential_max_children':1}
    def persist():save(out/'cost.json',report)
    def absent(pid):
        try:os.killpg(pid,0);return False
        except ProcessLookupError:return True
    def cancelled(signum,frame):raise TimeoutError('cost producer cancelled')
    prior=signal.signal(signal.SIGTERM,cancelled)
    owned={}
    def run(argv,kind,wall):
        p=None;failed=None;stdout=stderr=b'';forced=False;timed=False
        then=time.monotonic();cap=min(wall,deadline-then)
        try:
            if cap<=0:raise TimeoutError('aggregate deadline')
            mask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGTERM})
            def limits():
                signal.pthread_sigmask(signal.SIG_SETMASK,mask)
                resource.setrlimit(resource.RLIMIT_AS,(recipe['limits']['address_space_bytes'],)*2)
                resource.setrlimit(resource.RLIMIT_CPU,(max(1,int(cap)-2),max(2,int(cap)-1)))
                resource.setrlimit(resource.RLIMIT_FSIZE,(16777216,)*2)
            try:
                p=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,preexec_fn=limits,cwd=out)
                owned[p.pid]={'leader_reaped':False,'group_absent':False,'settled':False}
            finally:signal.pthread_sigmask(signal.SIG_SETMASK,mask)
            stdout,stderr=p.communicate(timeout=cap)
            if p.returncode:raise RuntimeError('first bounded child failure: '+kind)
        except BaseException as error:
            failed=error;timed=isinstance(error,(subprocess.TimeoutExpired,TimeoutError))
        finally:
            mask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGTERM})
            try:
                cleanup_error=None;leader_reaped=p is None;group_absent=p is None
                if p is not None:
                    try:
                        try:os.killpg(p.pid,signal.SIGKILL);forced=True
                        except ProcessLookupError:pass
                        if p.poll() is None:
                            more_out,more_err=p.communicate(timeout=5);stdout+=more_out;stderr+=more_err
                    except BaseException as error:
                        cleanup_error={'type':type(error).__name__,'message':str(error)}
                        failed=failed or error
                        if isinstance(error,subprocess.TimeoutExpired):
                            if isinstance(error.output,bytes):stdout=error.output
                            if isinstance(error.stderr,bytes):stderr=error.stderr
                    finally:
                        leader_reaped=p.poll()is not None
                        try:group_absent=absent(p.pid)
                        except BaseException as error:
                            group_absent=None;cleanup_error=cleanup_error or {'type':type(error).__name__,'message':str(error)}
                        owned[p.pid]={'leader_reaped':leader_reaped,'group_absent':group_absent,'settled':leader_reaped and group_absent is True}
                index=len(report['commands'])+1
                stdout_path=out/f'{index:02d}-{kind}.stdout';stderr_path=out/f'{index:02d}-{kind}.stderr'
                stdout_path.write_bytes(stdout);stderr_path.write_bytes(stderr)
                c={'argv':argv,'kind':kind,'pid_pgid':p.pid if p else None,'returncode':p.returncode if p else None,'wall_seconds':time.monotonic()-then,'timeout':timed,'killpg_sent':forced,'leader_reaped':leader_reaped,'owned_group_absent':group_absent,'settled':leader_reaped and group_absent is True,'cleanup_error':cleanup_error,'stdout_path':str(stdout_path),'stderr_path':str(stderr_path),'stdout_sha256':sha(stdout),'stderr_sha256':sha(stderr)}
                report['commands'].append(c);persist()
                if forced or not c['settled']:failed=failed or RuntimeError('owned child required cleanup or remains unsettled')
            finally:signal.pthread_sigmask(signal.SIG_SETMASK,mask)
        if failed is not None:raise failed
        return stdout
    try:
        packer=module(out/'sources/packer.py');loader=out/'sources/loader'
        for form,f in recipe['forms'].items():
            d=out/form;d.mkdir();e=recipe['expected_native_and_old_controls'][form];native_path=out/'native-inputs'/form/'x';native=native_path.read_bytes()
            if ident(native_path)!={'bytes':e['native_bytes'],'sha256':e['native_sha256']}:raise ValueError('native input changed')
            layout=packer.admit(native,e,sha)
            model_raw=(loader/'models.json').read_bytes();models=json.loads(model_raw)
            if int(models['profiles'][form]['weightmask'],16)!=f['wmask']:raise ValueError('wrong form WMASK')
            payload_path=d/'payload.bin'
            encoded=json.loads(run([sys.executable,'-I','-B',str(loader/'codec.py'),'--models',str(loader/'models.json'),'--model-sha256',sha(model_raw),'--profile',form,'--native',str(native_path),'--native-sha256',e['native_sha256'],'--out',str(payload_path)],'encoder',recipe['limits']['encoder_wall_seconds']))
            payload=payload_path.read_bytes()
            if not encoded['complete'] or encoded['format']!=recipe['packet_format'] or encoded['header_bytes']!=21 or encoded['zero_tail_bytes']!=4 or encoded['model_count']!=21 or encoded['coded_symbols']!=len(native)*8+1 or len(payload)!=e['payload_bytes']-8 or payload[-4:]!=bytes(4):raise ValueError('new fixed21 packet contract differs')
            diagnostic=d/'diagnostic'
            run(['cc',*recipe['diagnostic_flags'],f"-DMODEL_WMASK={f['wmask']}UL",f"-DIMAGE_SIZE={len(native)}UL",'-I',str(loader),str(out/'owned/diagnostic.c'),'-o',str(diagnostic)],'diagnostic-compile',recipe['limits']['compiler_wall_seconds'])
            bcj_path=d/'decoded-bcj.bin';restored_path=d/'restored-native.bin'
            diag=json.loads(run([str(diagnostic),str(native_path),str(payload_path),str(bcj_path),str(restored_path)],'diagnostic-run',recipe['limits']['diagnostic_wall_seconds']))
            if not all(diag.get(k)for k in ('complete','exact_BCJ','exact_native','canaries','context_unmapped')) or diag['negative_cases'] or restored_path.read_bytes()!=native or sha(bcj_path.read_bytes())!=encoded['bcj_sha256']:raise ValueError('actual positive decode differs')
            assembly=d/'payload.S';assembly.write_text('.section .payload,"a",@progbits\n.global payload,payload_end\npayload:\n.incbin "'+str(payload_path)+'"\npayload_end:\n.section .note.GNU-stack,"",@progbits\n')
            defs={'IMAGE_BASE':layout['image_base'],'IMAGE_SIZE':layout['image_size'],'IMAGE_PAGES':layout['image_pages'],'IMAGE_ENTRY':layout['entry'],'BSS_BASE':layout['bss_base'],'BSS_PAGES':layout['bss_pages'],'GUARD_BASE':layout['guard_base'],'RESERVE_SIZE':layout['reserve_size'],'CHECKPOINT':0,'MODEL_WMASK':f['wmask']}
            linked=d/'linked'
            run(['cc',*recipe['loader_flags'],*[f'-D{k}={v}UL'for k,v in defs.items()],str(loader/'loader.c'),str(assembly),'-Wl,-T,'+str(loader/'image.ld'),'-o',str(linked)],'shipping-loader-compile',recipe['limits']['compiler_wall_seconds'])
            whole=packer.stripped_loader(linked.read_bytes());target=d/'x';target.write_bytes(whole);target.chmod(0o755)
            geometry=packer.elf(whole);ph=geometry['segments']
            expected_ph=[{'type':1,'flags':5,'offset':0,'vaddr':0x10000000,'paddr':0x10000000,'filesz':len(whole),'memsz':len(whole),'align':4096},{'type':0x6474e551,'flags':6,'offset':0,'vaddr':0,'paddr':0,'filesz':0,'memsz':0,'align':8}]
            if ph!=expected_ph or geometry['entry']!=0x100000b0 or any(geometry[k]for k in ('section_offset','section_size','section_count','section_names')):raise ValueError('whole static geometry differs')
            if not whole.endswith(payload) or whole.find(payload)!=len(whole)-len(payload):raise ValueError('payload extent differs')
            sect=sections(linked.read_bytes());text=sect['.text']['bytes'];rodata=sect['.rodata']['bytes'];padding=len(whole)-176-text-rodata
            if padding<0 or rodata<len(payload):raise ValueError('component arithmetic differs')
            row={'form':form,'native':ident(native_path),'native_layout':layout,'native_ELF':packer.elf(native),'WMASK':f['wmask'],'encoding':encoded,'payload':ident(payload_path),'decoded_BCJ':ident(bcj_path),'restored_native':ident(restored_path),'diagnostic':diag,'whole':ident(target),'whole_path':str(target),'whole_ELF':geometry,'loader_definitions':defs,'linked_sections':sect,
             'components':{'ELF_header_PHDR':176,'text':text,'rodata_other_than_payload':rodata-len(payload),'padding':padding,'payload':len(payload),'nonpacket_overhead':len(whole)-len(payload)},'old_whole_bytes':e['whole_bytes'],'whole_delta_bytes':len(whole)-e['whole_bytes'],'old_packet_bytes':e['payload_bytes'],'packet_delta_bytes':len(payload)-e['payload_bytes'],'old_nonpacket_overhead':e['loader_and_headers_bytes'],'new_native_or_shipping_or_audit_execution':0}
            report['forms'].append(row);persist();print(json.dumps({'form':form,'native':len(native),'packet':len(payload),'whole':len(whole),'whole_delta':row['whole_delta_bytes'],'overhead':len(whole)-len(payload)}),flush=True)
            if len(whole)>=e['whole_bytes']:
                report['status']='COST_TIE_OR_LOSS_STOP';report['complete']=True;report['stop_after_form']=form;break
        else:report['status']='BOTH_FORMS_GAIN_FIRSTCOST_ONLY';report['complete']=True
    except BaseException as error:
        report['complete']=False;report['status']='FIRST_FAILURE_STOP';report['failure']={'type':type(error).__name__,'message':str(error)};raise
    finally:
        final_mask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGTERM})
        final_error=None
        try:
            try:
                report['normal21_after']=normal_map(normal,recipe)
                report['own_source_after']={n:ident(HERE/n)for n in FILES}
                if report['own_source_after']!=prep['own_source']:raise ValueError('ordinary source changed during cost')
            except BaseException as error:
                final_error=error;report['complete']=False;report['status']='FIRST_FAILURE_STOP'
                report['final_readback_failure']={'type':type(error).__name__,'message':str(error)}
            report['elapsed_seconds']=time.monotonic()-start;report['owned_children']=owned
            report['terminal_owned_handles']=sum(not x['settled']for x in owned.values())
            if report['terminal_owned_handles']:
                report['complete']=False;report['status']='FIRST_FAILURE_STOP'
                final_error=final_error or RuntimeError('owned child settlement unobserved')
            report['all_requested_forms_completed']=len(report['forms'])==2
            report['counts']={k:sum(c['kind']==k for c in report['commands'])for k in ('encoder','diagnostic-compile','diagnostic-run','shipping-loader-compile')}
            report['limits']='positive exact-byte diagnostic only; static whole cost, no new physical/audit/initial-BSS or engine qualification; no performance or4k claim'
            persist()
        finally:
            signal.signal(signal.SIGTERM,prior)
            signal.pthread_sigmask(signal.SIG_SETMASK,final_mask)
        if final_error is not None:raise final_error
    print(json.dumps({'complete':report['complete'],'status':report['status'],'cost':ident(out/'cost.json'),'counts':report['counts'],'terminal_handles':report['terminal_owned_handles']}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--prepare-only',type=Path);group.add_argument('--execute',type=Path);args=parser.parse_args()
    if args.prepare_only:prepare(args.prepare_only)
    else:execute(args.execute)