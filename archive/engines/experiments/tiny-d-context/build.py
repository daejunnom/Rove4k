#!/usr/bin/env python3
"""Fixed context own-ELF first cost from exact explicit external data inputs.

No upstream code/program dependency, native compilation or engine execution.
This experimental data-input tool is not a closed maintained encoder recipe.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import struct
import subprocess
import time

HERE=Path(__file__).resolve().parent
FILES=('.gitattributes','README.md','recipe.json','image.ld','decoder.h','diagnostic.c','loader.c','build.py')
ACTIVE=set()

def sha(raw):return hashlib.sha256(raw).hexdigest()
def need(condition,message):
    if not condition:raise ValueError(message)

def elf(raw):
    need(raw[:9]==b'\x7fELF\x02\x01\x01\0\0' and len(raw)>=64,'ELF64 LE header required')
    kind,machine,version=struct.unpack_from('<HHI',raw,16)
    entry,phoff,shoff=struct.unpack_from('<QQQ',raw,24)
    flags,ehsize,phsize,phnum,shsize,shnum,shstr=struct.unpack_from('<IHHHHHH',raw,48)
    need((kind,machine,version,flags,ehsize,phoff,phsize)==(2,62,1,0,64,64,56),'fixed x86-64 header required')
    need(1<=phnum<=3 and phoff+phsize*phnum<=len(raw),'PHDR extent')
    segments=[dict(zip(('type','flags','offset','vaddr','paddr','filesz','memsz','align'),
        struct.unpack_from('<IIQQQQQQ',raw,phoff+phsize*i))) for i in range(phnum)]
    return {'entry':entry,'section_offset':shoff,'section_size':shsize,'section_count':shnum,'section_names':shstr,'segments':segments}

def sections(raw):
    e=elf(raw);offset=e['section_offset'];width=e['section_size'];count=e['section_count'];strings=e['section_names']
    need(width==64 and strings<count and offset+width*count<=len(raw),'linked section extent')
    rows=[struct.unpack_from('<IIQQQQIIQQ',raw,offset+width*i) for i in range(count)]
    text=rows[strings];names=raw[text[4]:text[4]+text[5]];result=[]
    for row in rows:
        end=names.find(b'\0',row[0]);need(end>=0,'section name')
        result.append({'name':names[row[0]:end].decode(),'type':row[1],'flags':row[2],
            'address':row[3],'offset':row[4],'bytes':row[5],'alignment':row[8]})
    return result

def strip_loader(raw):
    e=elf(raw);need(len(e['segments'])==2,'one RX plus nonexec stack only')
    rx,stack=e['segments'];need(rx['type']==1 and rx['flags']==5 and rx['offset']==0 and rx['vaddr']==rx['paddr']==0x10000000,'fixed loader RX')
    need(rx['filesz']==rx['memsz']<=len(raw) and rx['align']==4096,'loader file/memory extent')
    need(stack=={'type':0x6474e551,'flags':6,'offset':0,'vaddr':0,'paddr':0,'filesz':0,'memsz':0,'align':8},'nonexec stack contract')
    need(rx['vaddr']+176<=e['entry']<rx['vaddr']+rx['filesz'],'entry inside RX')
    out=bytearray(raw[:rx['filesz']]);struct.pack_into('<Q',out,40,0);struct.pack_into('<HHH',out,58,0,0,0)
    return bytes(out)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs',type=Path,required=True,help='external directory with form/native and form/original.paq')
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve();inputs=args.inputs.resolve()
    need(args.out.is_absolute() and args.inputs.is_absolute() and not out.exists(),'absolute external inputs and new output required')
    need(not any((p/'.git').exists() for p in (out,*out.parents,inputs,*inputs.parents)),'inputs/output must be outside checkout')
    need(os.uname().machine=='x86_64','Linux x86-64 required')
    out.mkdir(parents=True);start=time.monotonic();deadline=start+150
    report={'complete':False,'scope':__doc__,'sources':{},'forms':[],'commands':[],'failures':[],'cleanup':[],
        'loader_compiles_planned':2,'whole_engine_executions':0,'native_compiles':0,'upstream_program_executions':0,
        'normal_closed_encoder_producer':False,'new_image_runtime_qualification':False}
    def cancelled(signum,frame):raise TimeoutError('context first cost terminated')
    prior=signal.signal(signal.SIGTERM,cancelled)
    def run(command,directory):
        item={'command':command,'cwd':str(directory)};report['commands'].append(item)
        process=None;stdout=stderr=b'';error=None;begin=time.monotonic()
        def limits():
            signal.pthread_sigmask(signal.SIG_SETMASK,mask)
            resource.setrlimit(resource.RLIMIT_AS,(512<<20,512<<20))
            resource.setrlimit(resource.RLIMIT_CPU,(50,50))
        try:
            need(time.monotonic()<deadline,'aggregate deadline')
            mask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGTERM})
            try:
                process=subprocess.Popen(command,cwd=directory,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                    start_new_session=True,preexec_fn=limits);ACTIVE.add(process)
            finally:signal.pthread_sigmask(signal.SIG_SETMASK,mask)
            stdout,stderr=process.communicate(timeout=min(55,deadline-time.monotonic()))
            need(process.returncode==0,'loader compiler failed')
        except BaseException as problem:
            error=problem;item['failure']={'type':type(problem).__name__,'message':str(problem)}
            if isinstance(problem,subprocess.TimeoutExpired):
                stdout=problem.output or stdout;stderr=problem.stderr or stderr
        finally:
            mask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGTERM})
            try:
                item['cleanup_errors']=[]
                if process is not None:
                    try:
                        try:os.killpg(process.pid,signal.SIGKILL);item['forced_cleanup']=True
                        except ProcessLookupError:item['forced_cleanup']=False
                        tailout,tailerr=process.communicate(timeout=5)
                        stdout=tailout or stdout;stderr=tailerr or stderr;item['returncode']=process.returncode;ACTIVE.discard(process)
                    except BaseException as cleanup:item['cleanup_errors'].append({'type':type(cleanup).__name__,'message':str(cleanup)})
                item.update(elapsed_seconds=time.monotonic()-begin,stdout_sha256=sha(stdout),stderr_sha256=sha(stderr))
                (directory/'stdout').write_bytes(stdout);(directory/'stderr').write_bytes(stderr)
                (directory/'command.json').write_text(json.dumps(item,indent=2)+'\n')
            finally:signal.pthread_sigmask(signal.SIG_SETMASK,mask)
        if error is not None:raise error
        need(not item['forced_cleanup'] and not item['cleanup_errors'],'unexpected compiler descendant/cleanup')
        return item
    try:
        frozen=out/'source';frozen.mkdir()
        for name in FILES:
            raw=(HERE/name).read_bytes();need(b'\r' not in raw,'raw LF source required')
            (frozen/name).write_bytes(raw);report['sources'][name]={'bytes':len(raw),'sha256':sha(raw)}
        recipe=json.loads((frozen/'recipe.json').read_bytes())
        need(recipe['hash_bits']==24 and recipe['base_probability']==10 and recipe['table_bytes']==33554432 and recipe['physical_zero_tail_bytes']==4,'fixed context ABI')
        need(sha((frozen/'image.ld').read_bytes())==recipe['linker_sha256'],'unchanged linker')
        admitted=[]
        for form,expected in recipe['expected'].items():
            native=(inputs/form/'native').read_bytes();original=(inputs/form/'original.paq').read_bytes()
            need((len(native),sha(native))==(expected['native_bytes'],expected['native_sha256']),'exact qualified native identity')
            parsed=elf(native);need(all(parsed[k]==expected['layout'][k] for k in parsed),'exact native PHDR/entry identity')
            need((len(original),sha(original))==(expected['original_stream_bytes'],expected['original_stream_sha256']),'exact frozen reference stream identity')
            width=expected['original_length_bytes'];bits=int.from_bytes(original[:width],'little')
            need(bits==8*len(native)+1,'exact output bit length')
            payload=bits.to_bytes(4,'little')+original[width:]+b'\0'*4
            need((len(payload),sha(payload))==(expected['prepared_payload_bytes'],expected['prepared_payload_sha256']),'u32/zero4 payload identity')
            admitted.append((form,expected,native,original,payload))
        report['all_exact_native_and_stream_inputs_admitted_before_compile']=True
        for form,expected,native,original,payload in admitted:
            directory=out/form;directory.mkdir();payloadpath=directory/'payload.bin';payloadpath.write_bytes(payload)
            need('"' not in str(payloadpath) and '\\' not in str(payloadpath),'assembly path requires literal Linux path')
            assembly=directory/'payload.S';assembly.write_text('.section .payload,"a",@progbits\n.global payload,payload_end\npayload:\n.incbin "'+str(payloadpath)+'"\npayload_end:\n.section .note.GNU-stack,"",@progbits\n')
            layout=expected['layout'];defines={key.upper():layout[value] for key,value in (
                ('image_base','image_base'),('image_size','image_size'),('image_pages','image_pages'),('image_entry','entry'),
                ('bss_base','bss_base'),('bss_pages','bss_pages'),('guard_base','guard_base'),('reserve_size','reserve_size'))}
            command=['cc',*recipe['loader_flags'],*[f'-D{k}={v}UL' for k,v in defines.items()],
                str(frozen/'loader.c'),str(assembly),'-Wl,-T,'+str(frozen/'image.ld'),'-o',str(directory/'linked')]
            compile=run(command,directory)
            linked=(directory/'linked').read_bytes();rows=sections(linked);whole=strip_loader(linked)
            target=directory/'x';target.write_bytes(whole);target.chmod(0o755)
            need(whole.count(payload)==1,'entire exact payload occurs once')
            need(all(not(s['flags']&2) or s['name'] in ('.text','.rodata') for s in rows if s['bytes']),'unexpected allocated section')
            text=sum(s['bytes'] for s in rows if s['name']=='.text');rodata=sum(s['bytes'] for s in rows if s['name']=='.rodata')
            padding=len(whole)-176-text-rodata;need(padding>=0 and rodata>=len(payload),'whole byte accounting')
            row={'id':form,'native_input':{'path':str(inputs/form/'native'),'bytes':len(native),'sha256':sha(native)},
                'original_stream':{'path':str(inputs/form/'original.paq'),'bytes':len(original),'sha256':sha(original)},
                'native_layout':layout,'payload':{'path':str(payloadpath),'bytes':len(payload),'sha256':sha(payload),'u32_header_and_models_bytes':29,'real_zero_tail_bytes':4,'arithmetic_body_bytes':len(payload)-33},
                'whole':{'path':str(target),'bytes':len(whole),'sha256':sha(whole),'ELF':elf(whole)},
                'linked':{'path':str(directory/'linked'),'bytes':len(linked),'sha256':sha(linked),'sections':rows},
                'actual_cost':{'ELF_header_and_PHDR_bytes':176,'text_bytes':text,'nonpayload_rodata_bytes':rodata-len(payload),
                    'alignment_bytes':padding,'payload_bytes':len(payload),'all_nonpayload_bytes':len(whole)-len(payload),
                    'old_complete_whole_bytes':expected['old_whole_bytes_metadata'],'whole_byte_change':len(whole)-expected['old_whole_bytes_metadata']},
                'compile':compile,'whole_executed':False}
            report['forms'].append(row)
        report['complete']=True
    except BaseException as error:
        report['complete']=False
        report['failures'].append({'type':type(error).__name__,'message':str(error)})
    finally:
        mask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGTERM})
        try:
            for process in list(ACTIVE):
                report['complete']=False;entry={'pid':process.pid};report['cleanup'].append(entry)
                try:
                    try:os.killpg(process.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                    process.communicate(timeout=5);entry['returncode']=process.returncode
                except BaseException as error:entry['error']=str(error)
            report['elapsed_seconds']=time.monotonic()-start
            path=out/'build.json';path.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
        finally:signal.signal(signal.SIGTERM,prior);signal.pthread_sigmask(signal.SIG_SETMASK,mask)
    print(json.dumps({'complete':report['complete'],'report':str(path),'sha256':sha(path.read_bytes()),'failures':report['failures'],
        'forms':[{k:r[k] for k in ('id','whole','actual_cost')} for r in report['forms']]}))
    return 0 if report['complete'] else 1

if __name__=='__main__':raise SystemExit(main())
