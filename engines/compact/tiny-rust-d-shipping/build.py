#!/usr/bin/env python3
"""Build the separate finite Rust D shipping entry; never execute an image."""
import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import resource
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CANONICAL = HERE.parent/'tiny-rust-d'
HELPERS = ('engines/compact/tiny-entry-d/verify.py', 'engines/compact/tiny-rust-d/verify_runtime.py')
BODY_CLASS = 'tiny-rust-d-finite-shipping-result-body232-data8-v3'
LEGACY_CLASS = 'tiny-rust-d-finite-shipping-result-data8-v2'
IMAGE_POLICIES = {
    'body232': {'id': 'tiny-rust-d-result-data8-body232-zero-prefix-v1', 'decode_prefix': 232},
    'legacy-full': {'id': 'tiny-rust-d-result-data8-full-image-v2', 'decode_prefix': 0},
}


def sha(data): return hashlib.sha256(data).hexdigest()
def require(value, message):
    if not value: raise ValueError(message)
def save(path, value): path.write_text(json.dumps(value, indent=2)+'\n')
def identity(path):
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': sha(data)}
def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def select_recipe(base, name):
    """Explicit build selection; legacy image bytes never stand in for body232."""
    require(base['class'] == BODY_CLASS and base['image_policies'] == IMAGE_POLICIES,
            'unknown Rust restoration class/policy')
    require(name in IMAGE_POLICIES, 'unknown selected Rust image policy')
    recipe = json.loads(json.dumps(base))
    if name == 'legacy-full':
        legacy = base['legacy_full_image']
        require(legacy['class'] == LEGACY_CLASS and legacy['codec'] == base['codec'],
                'legacy full-image contract differs')
        recipe['class'] = LEGACY_CLASS
        recipe['forms'] = json.loads(json.dumps(legacy['forms']))
        for form in recipe['forms'].values():
            form['restored'] = dict(form['load'])
    return recipe, dict(IMAGE_POLICIES[name])

def source_closure():
    """All build and selected positive-validator inputs, with no external reports."""
    names = ['build.py', 'recipe.json', 'README.md', 'verify.py', 'generator/specialize.py',
             'packaging/packer.py', 'packaging/loader/codec.py', 'packaging/loader/loader.c', 'packaging/loader/image.ld']
    paths = [HERE/n for n in names]
    paths += [CANONICAL/n for n in ('main.rs','board.rs','search.rs','runtime.rs','os.rs','link.ld','build.py')]
    paths += [ROOT/n for n in HELPERS]
    return {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in paths}

def sections(data):
    at = struct.unpack_from('<Q',data,40)[0]
    stride,count,index = struct.unpack_from('<HHH',data,58)
    require(stride==64 and 0<count<64 and index<count and at+count*stride<=len(data),'section extent')
    headers = [struct.unpack_from('<IIQQQQIIQQ',data,at+i*stride) for i in range(count)]
    h = headers[index]; names = data[h[4]:h[4]+h[5]]
    return [{'name':names[h[0]:names.index(b'\0',h[0])].decode(),'type':h[1],'flags':h[2],
             'address':h[3],'offset':h[4],'bytes':h[5],'align':h[8],
             'content':data[h[4]:h[4]+h[5]] if h[1]!=8 else b''} for h in headers]

def allocated(data):
    return {(s['name'],s['address']):(s['type'],s['bytes'],s['content']) for s in sections(data) if s['flags']&2}

owned = {}


def exited_unreaped(child):
    # Retain the original leader's PID/group identity until its members settle.
    return os.waitid(os.P_PID, child.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None


def group_absent(child):
    try: os.killpg(child.pid, 0); return False
    except ProcessLookupError: return True


def group_others(child):
    rows=[]
    for path in Path('/proc').iterdir():
        if not path.name.isdecimal() or int(path.name)==child.pid:continue
        try:
            fields=(path/'stat').read_text().rsplit(')',1)[1].split()
            if int(fields[2])==child.pid:rows.append({'pid':int(path.name),'state':fields[0]})
        except (FileNotFoundError,ProcessLookupError,PermissionError):pass
    return rows


def settle(child, row, force=False):
    if not row.get('reaped'):
        extras=group_others(child)
        if force or not exited_unreaped(child) or extras:
            row['forced_cleanup']=True
            row['other_group_members_before_cleanup']=extras
            for sig in (signal.SIGTERM,signal.SIGKILL):
                # Destructive signals are sent only while this leader is unreaped.
                try:os.killpg(child.pid,sig)
                except ProcessLookupError:pass
                end=time.monotonic()+2
                while time.monotonic()<end:
                    if exited_unreaped(child) and not group_others(child):break
                    time.sleep(.025)
                if exited_unreaped(child) and not group_others(child):break
        extras=group_others(child)
        row['other_group_members_before_reap']=extras
        if not exited_unreaped(child) or extras:
            row['unsettled_before_reap']=True
            raise RuntimeError('Owned original group did not settle while leader identity retained')
        row['original_identity_retained_until_other_members_absent']=True
        child.wait(timeout=3)
        row.update(returncode=child.returncode,terminal=True,reaped=True)
    row['group_absent_at_settlement']=group_absent(child)
    row['owned_group_absent']=row['group_absent_at_settlement']
    if row['group_absent_at_settlement']:owned.pop(child,None)


def admit(data, mode, recipe, packer):
    """New literal Rust shipping class; existing packer C class remains unchanged."""
    expected = recipe['forms'][mode]; native = expected['native']; layout=recipe['layout']
    require(len(data)==native['bytes']==16816 and sha(data)==native['sha256'],'unknown finite Rust shipping native')
    parsed=packer.elf(data); rx=expected['rx_bytes']
    wanted=[dict(type=1,flags=5,offset=0,vaddr=0x400000,paddr=0x400000,filesz=rx,memsz=rx,align=4096),
            dict(type=1,flags=6,offset=0x4000,vaddr=0x404000,paddr=0x404000,filesz=8,memsz=12,align=4096),
            dict(type=0x6474e551,flags=6,offset=0,vaddr=0,paddr=0,filesz=0,memsz=0,align=0)]
    require(parsed['entry']==0x4000f0 and parsed['segments']==wanted and 0xf0<rx<=0x4000,'literal PHDR/entry/RX mismatch')
    require(data[0x4000:0x4008]==bytes.fromhex(recipe['data_hex'])==bytes.fromhex('4601400000000000'),'initialized memcpy pointer')
    require(0x4000f0<=0x400146<0x400000+rx and not any(data[rx:0x4000]),'RX pointer or file gap')
    rows=sections(data); by_name={s['name']:s for s in rows}
    require((by_name['.data']['type'],by_name['.data']['flags'],by_name['.data']['address'],by_name['.data']['offset'],by_name['.data']['bytes'])==(1,3,0x404000,0x4000,8),'data8 section')
    require((by_name['.bss']['type'],by_name['.bss']['flags'],by_name['.bss']['address'],by_name['.bss']['offset'],by_name['.bss']['bytes'])==(8,3,0x404008,0x4008,4),'OUTPUT BSS4 section')
    require(all(s['name'] in ('.text','.rodata','.data','.bss') and not s['flags']&0x400 for s in rows if s['flags']&2),'unexpected allocatable section')
    require(not any(s['name'].startswith(('.eh_frame','.gcc_except_table')) for s in rows),'unwind section')
    require(layout=={'image_base':0x400000,'image_size':16392,'image_pages':0x5000,'final_rx_pages':0x4000,
        'entry':0x4000f0,'bss_base':0x404000,'bss_pages':0x1000,'rw_filesz':8,'rw_memsz':12,
        'actual_bss_base':0x404008,'actual_bss_size':4,'guard_base':0x3ff000,'upper_guard':0x405000,
        'reserve_size':0x7000,'loader_base':0x10000000},'fixed guarded data8 mapping differs')
    load=packer.strip_native(data); transformed=packer.elf(load); permitted=set(range(40,48))|set(range(58,64))
    changed=[i for i,(a,b) in enumerate(zip(data,load)) if a!=b]
    require(len(load)==expected['load']['bytes']==16392 and sha(load)==expected['load']['sha256'],'literal sectionless span')
    require(transformed['entry']==parsed['entry'] and transformed['segments']==wanted,'strip changed PHDR/entry')
    require(set(changed)<=permitted and all(load[i]==0 for i in permitted) and data[0xf0:0x4008]==load[0xf0:0x4008],'strip changed retained load bytes')
    return load, {'literal_native_and_load':True,'entry':parsed['entry'],'segments':wanted,
        'section_header_offsets_changed':changed,'data8_and_BSS4':True,'guarded_mapping_unchanged':True,
        'existing_C_class_guard_modified':False,'runtime_observed':False}


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--rustc',default='rustc')
    ap.add_argument('--image-policy',choices=tuple(IMAGE_POLICIES),default='body232',
                    help='build-time restoration policy; no engine/UCI selector')
    a=ap.parse_args();out=a.out.resolve()
    if sys.platform!='linux' or platform.machine()!='x86_64':ap.error('Linux x86-64 required')
    if not a.out.is_absolute() or out.exists() or out==ROOT or ROOT in out.parents:ap.error('new absolute external output required')
    rustc=shutil.which(a.rustc)
    if not rustc:ap.error('Rust compiler unavailable')
    recipe,image_policy=select_recipe(json.loads((HERE/'recipe.json').read_bytes()),a.image_policy);limits=recipe['limits']
    require(recipe['profile']=={'workers':2,'tt_bits':18,'ply':128,'shipping_cfg':'tiny_shipping'},'selected profile only')
    require(all(recipe['forms'].get(mode) is not None for mode in ('scalar','hq')),'Both literal Result-projection forms require discovery before an ordinary build')
    closure=source_closure();out.mkdir()
    report={'complete':False,'class':recipe['class'],'selected_image_policy':a.image_policy,'image_policy':image_policy,
        'source_closure':closure,'recipe_sha256':sha((HERE/'recipe.json').read_bytes()),
        'profile':recipe['profile'],'forms':[],'commands':[],'limits':limits,'counts':{'native_links':0,'audit_links':0,'whole_encodes':0,'loader_links':0,'ELF_execution':0},
        'runtime_qualified':False,'rules_eligibility':'unproven'}
    deadline=time.monotonic()+limits['parent_wall_seconds'];fixed={'LC_ALL':'C','TZ':'UTC','SOURCE_DATE_EPOCH':'0'}
    env=os.environ.copy();env.update(fixed);report['fixed_environment']=fixed
    def record():save(out/'build.json',report)
    def stop(signum,frame):raise InterruptedError('builder signal '+str(signum))
    handled=(signal.SIGTERM,signal.SIGINT,signal.SIGALRM,signal.SIGXCPU)
    saved_signal_handlers={}
    previous_chld=signal.getsignal(signal.SIGCHLD)
    def run(command,cwd=out,environment=env):
        remaining=min(limits['child_wall_seconds'],deadline-time.monotonic())
        if remaining<=0:raise TimeoutError('aggregate fixed-build deadline')
        row={'command':[str(x) for x in command],'cwd':str(cwd),'started':False,'forced_cleanup':False}
        report['commands'].append(row);record()
        process=None;begin=time.monotonic()
        with tempfile.TemporaryFile() as stdout_file,tempfile.TemporaryFile() as stderr_file:
            try:
                mask=signal.pthread_sigmask(signal.SIG_BLOCK,set(handled))
                def setup():
                    resource.setrlimit(resource.RLIMIT_AS,(limits['child_as_bytes'],)*2)
                    resource.setrlimit(resource.RLIMIT_CPU,(limits['child_cpu_seconds'],)*2)
                    signal.pthread_sigmask(signal.SIG_SETMASK,mask)
                try:
                    process=subprocess.Popen(row['command'],cwd=cwd,env=environment,stdin=subprocess.DEVNULL,
                        stdout=stdout_file,stderr=stderr_file,start_new_session=True,preexec_fn=setup)
                    owned[process]=row
                    row.update(started=True,pid=process.pid,pgid=process.pid);record()
                finally:signal.pthread_sigmask(signal.SIG_SETMASK,mask)
                while not exited_unreaped(process):
                    if time.monotonic()-begin>remaining:raise TimeoutError('fixed child wall deadline')
                    if os.fstat(stdout_file.fileno()).st_size+os.fstat(stderr_file.fileno()).st_size>limits['output_bytes']:
                        raise RuntimeError('fixed child output budget')
                    time.sleep(.025)
            finally:
                if process is not None:
                    mask=signal.pthread_sigmask(signal.SIG_BLOCK,set(handled))
                    try:
                        settle(process,row,force=not exited_unreaped(process))
                    finally:
                        try:
                            row['output_bytes']=os.fstat(stdout_file.fileno()).st_size+os.fstat(stderr_file.fileno()).st_size
                            stdout_file.seek(0);stderr_file.seek(0)
                            row['stdout']=stdout_file.read(limits['output_bytes']+1).decode(errors='replace')
                            row['stderr']=stderr_file.read(limits['output_bytes']+1).decode(errors='replace')
                            row['elapsed_diagnostic_seconds']=time.monotonic()-begin;record()
                        finally:signal.pthread_sigmask(signal.SIG_SETMASK,mask)
        require(row['output_bytes']<=limits['output_bytes'],'final tool output cap')
        require(row['returncode']==0 and not row['forced_cleanup'] and row['owned_group_absent'],'tool failed: '+str(command[0]))
        return row
    try:
        for sig in handled:
            saved_signal_handlers[sig]=signal.getsignal(sig)
            signal.signal(sig,stop)
        signal.signal(signal.SIGCHLD,signal.SIG_DFL)
        resource.setrlimit(resource.RLIMIT_AS,(limits['parent_as_bytes'],)*2)
        resource.setrlimit(resource.RLIMIT_CPU,(limits['parent_cpu_seconds'],)*2)
        signal.alarm(limits['parent_wall_seconds'])
        frozen=out/'source'
        for name,pinned in closure.items():
            raw=(ROOT/name).read_bytes();require(sha(raw)==pinned,'source changed during freeze: '+name)
            target=frozen/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
        own=frozen/HERE.relative_to(ROOT);canonical=frozen/CANONICAL.relative_to(ROOT)
        generator=module('rust_shipping_generator',own/'generator/specialize.py')
        require(sha((own/'generator/specialize.py').read_bytes())==recipe['generator_sha256'],'selected generator differs')
        source={n:(canonical/n).read_bytes() for n in generator.FILES}
        require({n:{'bytes':len(v),'sha256':sha(v)} for n,v in source.items()}==recipe['canonical7'],'canonical7 differs')
        generated,proof=generator.produce(source);save(out/'source-proof.json',proof)
        require({n:{'bytes':len(v),'sha256':sha(v)} for n,v in generated.items()}==recipe['generated7'],'generated7 differs')
        for name,pinned in recipe['packaging_sha256'].items():require(sha((own/name).read_bytes())==pinned,'packaging source differs')
        flags=next(ast.literal_eval(n.value) for n in ast.walk(ast.parse(generated['build.py'])) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='flags' for t in n.targets))
        report['native_flags']=flags
        packer=module('rust_shipping_packer',own/'packaging/packer.py');codec=module('rust_shipping_codec',own/'packaging/loader/codec.py')
        require(recipe['codec']=={'bcj_version':codec.BCJ_VERSION,'fixed_version':codec.FIXED_VERSION},'fixed codec version differs')
        tools={'rustc':run([rustc,'--version','--verbose'])['stdout'],'cc':run(['cc','--version'])['stdout'],'ld':run(['ld','--version'])['stdout']}
        require(tools['rustc'].splitlines()[0]==recipe['rustc'],'selected Rust toolchain differs');report['tools']=tools
        for mode in ('scalar','hq'):
            row={'form':mode,'attempts':[],'artifact_gates':{}};report['forms'].append(row);form_env=env.copy()
            form_env.update(ROVE_WORKERS='2',ROVE_TT_BITS='18',ROVE_HQ=str(int(mode=='hq')))
            for label in ('first','repeat'):
                local=out/mode/label;local.mkdir(parents=True)
                for name,raw in generated.items():(local/name).write_bytes(raw)
                command=[rustc,'--remap-path-prefix',str(local)+'=.',*flags];report['counts']['native_links']+=1
                compile_record=run(command,local,form_env);native=(local/'x').read_bytes();load,geometry=admit(native,mode,recipe,packer)
                (local/'load.bin').write_bytes(load)
                prefix=image_policy['decode_prefix'];restored,image_proof=codec.restoration_image(load,prefix)
                (local/'restored-image.bin').write_bytes(restored)
                require({'bytes':len(restored),'sha256':sha(restored)}==recipe['forms'][mode]['restored'],'literal restored image differs')
                report['counts']['whole_encodes']+=1;payload=codec.fixed_compress(codec.bcj(restored)[prefix:])
                decoded=bytes(prefix)+codec.fixed_decompress(payload,len(restored)-prefix)
                require(codec.bcj(decoded,inverse=True)==restored,'strict fixed body decode/whole-offset inverse BCJ mismatch')
                expected=recipe['forms'][mode];require(len(payload)==expected['payload']['bytes'] and sha(payload)==expected['payload']['sha256'],'literal fixed payload differs')
                report['counts']['loader_links']+=1
                whole=packer.compile_loader(local/'whole',own/'packaging/loader',payload,recipe['layout'],recipe['loader_flags'],lambda c:run(c),sha,decode_prefix=prefix)
                require(whole['bytes']==expected['whole']['bytes'] and whole['sha256']==expected['whole']['sha256'] and whole['loader_and_headers_bytes']==expected['loader_header_bytes'],'literal whole image differs')
                row['attempts'].append({'native':identity(local/'x'),'load':identity(local/'load.bin'),
                    'restored':identity(local/'restored-image.bin'),'restoration':image_proof,
                    'whole':whole,'compile':compile_record,'geometry':geometry});record()
            first,repeat=row['attempts'];require(all(Path(first[k]['path']).read_bytes()==Path(repeat[k]['path']).read_bytes() for k in ('native','load','restored','whole')),'independent native/load/restored/whole bytes differ')
            audit_command=['strip=none' if x=='strip=symbols' else x for x in first['compile']['command']];audit_command[-1]='x.unstripped'
            report['counts']['audit_links']+=1;audit=run(audit_command,out/mode/'first',form_env);unstripped=out/mode/'first/x.unstripped'
            undefined=run(['nm','-u',str(unstripped)])['stdout'];audit.update(identity(unstripped));audit['undefined_symbols']=undefined
            audit['allocatable_sections_identical']=allocated(Path(first['native']['path']).read_bytes())==allocated(unstripped.read_bytes());row['unstripped_audit']=audit
            checks={}
            for name,command in (('program_headers',['readelf','-lW',first['native']['path']]),('dynamic',['readelf','-dW',first['native']['path']]),('sections',['readelf','-SW',first['native']['path']]),('disassembly',['objdump','-d',first['native']['path']])):
                text=run(command)['stdout'];(out/mode/(name+'.txt')).write_text(text);checks[name]=text
            gates={'native_and_whole_reproduced':True,'literal_native_model_whole':True,'strict_restore':True,
                'no_interpreter':'INTERP' not in checks['program_headers'],'no_TLS_segment':' TLS ' not in checks['program_headers'],
                'no_dynamic_dependencies':'NEEDED' not in checks['dynamic'],'no_undefined_symbols':not undefined.strip(),
                'unstripped_allocatable_identical':audit['allocatable_sections_identical'],
                'no_unwind_sections':not re.search(r'\.(eh_frame|gcc_except_table)',checks['sections']),
                'no_fs_gs_memory_operands':not re.search(r'%[fg]s:',checks['disassembly']),
                'non_executable_stack':bool(re.search(r'GNU_STACK.* RW ',checks['program_headers']))}
            row['artifact_gates']=gates;record();require(all(gates.values()),'static artifact gate failed')
        require(source_closure()==closure,'source closure changed during ordinary build')
        require(all(c.get('owned_group_absent',False) for c in report['commands']),'owned tool group remains')
        report['complete']=True
    except BaseException as error:
        report['first_failure']={'type':type(error).__name__,'message':str(error)}
        raise
    finally:
        mask=signal.pthread_sigmask(signal.SIG_BLOCK,set(handled))
        try:
            signal.alarm(0)
            for child,row in list(owned.items()):
                try:settle(child,row,force=not row.get('reaped',False))
                except BaseException as error:
                    report.setdefault('cleanup_errors',[]).append({'type':type(error).__name__,'message':str(error)})
            report['owned_tool_handles']=len(owned)
            if owned or report.get('cleanup_errors'):report['complete']=False
            report['SIGCHLD_restored_after_settlement']=not owned
            record()
        finally:
            if not owned:signal.signal(signal.SIGCHLD,previous_chld)
            for sig,handler in saved_signal_handlers.items():signal.signal(sig,handler)
            signal.pthread_sigmask(signal.SIG_SETMASK,mask)
        print(json.dumps({'out':str(out),'complete':report['complete'],'counts':report['counts'],'first_failure':report.get('first_failure')}))

if __name__=='__main__':main()
