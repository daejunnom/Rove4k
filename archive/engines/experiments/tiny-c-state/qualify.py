#!/usr/bin/env python3
"""Focused new DEV0-layout/state/core proof after the one source-cost gain."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args();out=args.out.resolve()
    if not args.out.is_absolute() or out.exists() or out==ROOT or ROOT in out.parents or any((p/'.git').exists() for p in (out,*out.parents)):
        parser.error('new absolute external output required')
    report_data=args.build.read_bytes();built=json.loads(report_data)
    if not built['complete'] or not built['strict_source_cost_gain'] or built['delta']['whole_bytes']!=-8:
        raise ValueError('the one measured 5947-byte cache candidate gain is required')
    out.mkdir(parents=True);frozen=out/'inputs';frozen.mkdir()
    report={'passed':False,'scope':'actual DEV0 normalized layout/state and shipping core; no broad engine matrix',
            'cost_build_sha256':sha(report_data),'input_sha256':{},'runs':[],
            'reuse':'exact DEV source/native and unchanged PSQT/SIMD/math source; old native execution is not called a new shipping run'}
    def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        for name in ('qualify.py','adapter.c.in','state_contract.h','state_contract.c','core_main.c'):
            data=(HERE/name).read_bytes().replace(b'\r\n',b'\n');(frozen/name).write_bytes(data)
            report['input_sha256'][name]=sha(data)
        adapters=[]
        control_readable=None
        for row in built['forms']:
            label=row['id'];readable=Path(row['readable']).read_bytes();shipping=Path(row['source']).read_bytes()
            if sha(readable)!=row['readable_sha256'] or sha(shipping)!=row['source_sha256']:
                raise ValueError('cost producer source changed')
            if sha(Path(row['native']).read_bytes())!=row['native_sha256'] or sha(Path(row['whole']).read_bytes())!=row['whole_sha256']:
                raise ValueError('cost producer actual artifact changed')
            (frozen/(label+'-readable.c')).write_bytes(readable)
            engine=frozen/(label+'-shipping.c');engine.write_bytes(shipping)
            report['input_sha256'][engine.name]=sha(shipping)
            report['input_sha256'][label+'-readable.c']=sha(readable)
            if label=='control':control_readable=readable
            text=readable.decode();begin=text.index('int fen(Board *p,const char *s){');end=text.index('\nint verify_board(',begin)
            fen=text[begin:end].replace('int fen(Board *p,const char *s){','static int fixture_fen_board(Board *p,const char *s){',1)
            public=('table','workers','stopped','deadline','game_keys','game_length','position','now','mix','value','attacked','dead','make','gen','start','think','main')
            prefix='rove_fixture_'+label+'_'
            namespace='\n'.join('#define '+name+' '+prefix+name for name in public)
            api_label='baseline' if label=='control' else 'candidate'
            replacements={'@NAMESPACE@':namespace,'@PRODUCTION_SOURCE@':json.dumps(str(engine)),
                '@FIXTURE_FEN@':fen,'@CACHE_GETTER@':'static int api_cache(const void *input){return ((const Board *)input)->v;}' if label=='control' else '',
                '@API_NAME@':'rove_state_'+api_label,'@LABEL@':api_label,'@CACHE_CALLBACK@':'api_cache' if label=='control' else 'NULL',
                '@CORE_NAME@':'rove_state_'+api_label+'_core'}
            template=(frozen/'adapter.c.in').read_text()
            for marker,value in replacements.items():
                if not template.count(marker):raise ValueError('adapter marker absent: '+marker)
                template=template.replace(marker,value)
            if re.search(r'@[A-Z_]+@',template):raise ValueError('unexpanded adapter marker')
            adapter=frozen/(label+'-adapter.c');adapter.write_text(template);adapters.append(adapter)
            report['input_sha256'][adapter.name]=sha(adapter.read_bytes())
            assembly=subprocess.check_output(['objdump','-d',row['native']],text=True)
            instructions={name:len(re.findall(r'\b'+name+r'\b',assembly)) for name in ('vpgatherdd','vphaddd')}
            if not all(instructions.values()):raise ValueError('production SIMD kernel absent')
            search_assembly=subprocess.check_output(['objdump','-d','--disassemble=search',row['native']],text=True)
            called=bool(re.search(r'call[^\n]*<tiny_raw>',search_assembly))
            inlined=all(re.search(r'\b'+name+r'\b',search_assembly) for name in ('vpgatherdd','vphaddd'))
            if not (called or inlined):raise ValueError('actual production search does not consume SIMD leaf')
            report.setdefault('actual_shipping_SIMD',{})[label]={'native_sha256':row['native_sha256'],
                'instructions':instructions,'actual_search_calls_tiny_raw':called,'actual_search_inlines_gather_reduction':bool(inlined)}
        source_flags=['cc','-std=c11','-pthread','-DDEV=0','-DWORKERS=2','-DTT_BITS=18','-mavx2','-I',str(frozen)]
        for name,flags in (('optimized',['-O2']),('asan-ubsan',['-O1','-fsanitize=address,undefined','-fno-omit-frame-pointer'])):
            directory=out/name;directory.mkdir()
            objects=[];commands=[]
            for adapter in adapters:
                target=directory/(adapter.stem+'.o')
                command=source_flags+flags+['-c',str(adapter),'-o',str(target)]
                result=subprocess.run(command,capture_output=True,text=True,timeout=90)
                if result.returncode:raise RuntimeError(result.stderr)
                objects.append(target);commands.append(command)
            tests={}
            for kind,driver in (('state','state_contract.c'),('core','core_main.c')):
                binary=directory/kind
                command=source_flags+flags+[str(frozen/driver),*map(str,objects),'-o',str(binary)]
                subprocess.run(command,check=True,timeout=90);commands.append(command)
                result=subprocess.run([str(binary)],capture_output=True,text=True,timeout=90)
                if result.returncode or result.stderr:raise RuntimeError(kind+' '+result.stdout+result.stderr)
                tests[kind]={'result':json.loads(result.stdout),'binary_sha256':sha(binary.read_bytes())}
            report['runs'].append({'kind':name,'commands':commands,'tests':tests});save()
        report['passed']=True;save();print(json.dumps({'passed':True,'runs':len(report['runs']),'whole_candidate_bytes':5947}))
    except Exception as error:
        report['error']=repr(error);save();raise


if __name__=='__main__':main()
