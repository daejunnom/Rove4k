"""Compare current D bytes in the existing three standalone ELF decoder forms.

This is a new source-owned cost experiment. Historical dedicated-loader input
identities and selected mappings are not extended or weakened. The maintained
dynamic-TT kernel geometry admits the fresh native, and all loader/header bytes
count. Direct entry retains the existing loader's auxv/brk/self-image limits;
building a smaller file does not grant runtime or event qualification.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode=True
D=Path(__file__).resolve().parent
_spec=importlib.util.spec_from_file_location('structural_elf_cost',D/'structural_size.py')
h=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(h)


def compare(case,out):
    case,out=Path(case),Path(out)
    if not out.is_absolute() or out.exists() or any((p/'.git').exists() for p in (out,*out.parents)):
        raise ValueError('new absolute external output required')
    record=json.loads((case/'result.json').read_text())
    native=(case/'native/native').read_bytes()
    files={name:(case/'generated-readable'/name).read_bytes() for name in h.FILES}
    if (not record['complete'] or h.pin(native)!=record['native_runs'][0]['native'] or
            h.inventory(files)!=record['input']):
        raise ValueError('complete measured source-owned native required')
    m=h.modules()
    geometry=m['build'].kernel_geometry(m['packer'],native,record['workers'])
    rx,rw,_=geometry['segments']
    image_pages=(rx['filesz']+4095)&-4096
    bss_pages=(rw['memsz']+4095)&-4096
    layout={'IMAGE_BASE':rx['vaddr'],'IMAGE_SIZE':len(native),'IMAGE_PAGES':image_pages,
            'IMAGE_ENTRY':geometry['entry'],'BSS_BASE':rw['vaddr'],'BSS_PAGES':bss_pages,
            'GUARD_BASE':rx['vaddr']-4096,
            'RESERVE_SIZE':4096+image_pages+bss_pages+4096,'CHECKPOINT':0}
    if rw['vaddr']!=rx['vaddr']+image_pages:
        raise ValueError('direct-loader images must have consecutive RX/RW page extents')
    out.mkdir(parents=True)
    source=out/'loader-source';source.mkdir()
    paths={'small-loader.c':'engines/experiments/tiny-d-loader/loader.c',
           'small-image.ld':'engines/experiments/tiny-d-loader/image.ld',
           'context-loader.c':'engines/compact/tiny-entry-d/loader/loader.c',
           'context-image.ld':'engines/compact/tiny-entry-d/loader/image.ld',
           'decoder.h':'engines/compact/tiny-entry-d/loader/decoder.h',
           'models.json':'engines/compact/tiny-entry-d/loader/models.json'}
    for target,path in paths.items():(source/target).write_bytes((h.ROOT/path).read_bytes())
    small=h.load('structural_existing_small_codec',h.ROOT/'engines/experiments/tiny-d-loader/codec.py')
    context=h.load('structural_existing_context_codec',h.ROOT/'engines/compact/tiny-entry-d/loader/codec.py')
    report={'complete':False,'source_cost':h.pin((case/'result.json').read_bytes()),
            'native':h.pin(native),'source':h.inventory(files),'profile':record['profile'],
            'layout':layout,'commands':[],'candidates':[],
            'tools':{str(Path(t.__file__).relative_to(h.ROOT)):h.pin(Path(t.__file__).read_bytes())
                     for t in (h,small,context,m['build'],m['packer'],m['host'])},
            'loader_inputs':{path:h.pin((source/name).read_bytes()) for name,path in paths.items()},
            'observer':h.pin(Path(__file__).read_bytes()),'engine_executed':False,
            'runtime_qualified':False,'selected':False,
            'direct_entry_limits':['auxv and self-image identify the loader','initial brk identifies the loader',
                                   'requires the current libc/TLS/auxv/brk-independent raw-syscall D']}
    def save():(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    hostmod=m['host']
    hostmod.LIMITS={**hostmod.LIMITS,'aggregate_wall':180,'per_command_wall':40,
                   'parent_CPU':240,'parent_CPU_hard':270,'child_CPU':30,'tool_output_bytes':8<<20}
    host=hostmod.Host(out,report,save)
    try:
        filtered=small.bcj(native)
        if small.bcj(filtered,inverse=True)!=native:raise ValueError('small codec BCJ inverse differs')
        payloads={}
        for name,encode,decode in (('lz',small.lz_compress,small.lz_decompress),
                                   ('fixed',small.fixed_compress,small.fixed_decompress)):
            payload=encode(filtered)
            if decode(payload,len(native))!=filtered:raise ValueError('small codec inverse differs')
            payloads[name]=payload
        model=context.load_models((source/'models.json').read_bytes(),'scalar-shipping')
        payloads['context'],context_proof=context.encode_native(native,model)
        report['context_encoder']=context_proof
        for name,payload in payloads.items():
            (source/(name+'.bin')).write_bytes(payload)
            assembly=('.section .payload,"a",@progbits\n.global payload,payload_end\npayload:\n'
                      '.incbin "'+str(source/(name+'.bin'))+'"\npayload_end:\n'
                      '.section .note.GNU-stack,"",@progbits\n')
            (source/(name+'.S')).write_text(assembly)
        # Decode the context packet with the actual C decoder and independently
        # compare every output byte. This does not enter the engine or inspect
        # the standalone loader's runtime mappings.
        probe='''#include <stdlib.h>
#include <stdio.h>
#include <stdint.h>
#include "decoder.h"
extern const unsigned char payload[],payload_end[];
int main(void){
 unsigned char *out=malloc(IMAGE_SIZE),*table=calloc(1,33554432);
 if(!out||!table)return 2;
 if(context_decode(out,IMAGE_SIZE,payload,payload_end,table))return 3;
 for(unsigned i=0;i+4<IMAGE_SIZE;){
  if((out[i]&254)==232){uint32_t n;__builtin_memcpy(&n,out+i+1,4);n-=i+5;
   __builtin_memcpy(out+i+1,&n,4);i+=5;}else i++;
 }
 return fwrite(out,1,IMAGE_SIZE,stdout)==IMAGE_SIZE?0:4;
}
'''
        (source/'context-probe.c').write_text(probe)
        probe_path=source/'context-probe'
        host.run(['cc','-std=c11','-O2','-msse4.2',f'-DIMAGE_SIZE={len(native)}',
                  f'-DMODEL_WMASK={model[0]}',str(source/'context-probe.c'),str(source/'context.S'),
                  '-o',str(probe_path)],cwd=source,kind='context-decoder-compile')
        decoded=host.run([str(probe_path)],cwd=source,kind='context-decoder-run')
        if decoded!=native:raise ValueError('actual context C decoder native inverse differs')
        report['context_C_inverse']={'source':h.pin(probe.encode()),'binary':h.pin(probe_path.read_bytes()),
                                    'decoded':h.pin(decoded),'exact':True}
        for name,payload in payloads.items():
            for optimize in ('s','z'):
                directory=out/(name+'-O'+optimize);directory.mkdir()
                definitions={**layout,**({'MODEL_WMASK':model[0]} if name=='context' else {'CODEC_FIXED':int(name=='fixed')})}
                flags=m['build'].native_flags(m['source'].production().resource_profile(record['profile']),optimize)
                prefix='context' if name=='context' else 'small'
                command=['cc',*flags,*[f'-D{k}={v}UL' for k,v in definitions.items()],
                         str(source/(prefix+'-loader.c')),str(source/(name+'.S')),
                         '-Wl,-T,'+str(source/(prefix+'-image.ld')),'-o',str(directory/'linked')]
                host.run(command,cwd=directory,kind='loader-'+name+'-O'+optimize)
                if report['commands'][-1]['stderr']['bytes']:raise ValueError('loader compile diagnostics')
                whole=m['packer'].stripped_loader((directory/'linked').read_bytes())
                (directory/'x').write_bytes(whole)
                report['candidates'].append({'mode':name,'optimize':optimize,'path':str(directory/'x'),
                    **h.pin(whole),'payload':h.pin(payload),'loader_and_headers_bytes':len(whole)-len(payload),
                    'definitions':definitions,'flags':flags,'runtime_qualified':False})
                save()
        report['minimum_measured']=min(report['candidates'],key=lambda row:row['bytes'])
        report['complete']=True
    except BaseException as error:
        report['failure']={'type':type(error).__name__,'message':str(error)}
        raise
    finally:
        host.close();save()
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    report=compare(args.case,args.out)
    print(json.dumps({'complete':report['complete'],'native':report['native'],
        'candidates':[{k:row[k] for k in ('mode','optimize','bytes','loader_and_headers_bytes')} for row in report['candidates']]}))
