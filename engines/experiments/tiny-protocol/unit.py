#!/usr/bin/env python3
"""Headless actual parser units: counted make, rollback, boundaries and clocks.

No helper thread is started in this unit. After go's parser/dispatch runs, the
fixture manually settles its pending epoch before testing another clock case.
Physical completion/join is tested separately in actual runtime fault harnesses.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess

HERE=Path(__file__).resolve().parent


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def sha(data):return hashlib.sha256(data).hexdigest()


def counted(source,parser):
    text=source.decode();begin,end,body=parser.function(text,'make')
    changed=body.replace('int make(','int real_make(',1)
    if changed==body:raise ValueError('actual make declaration changed')
    wrapper='\nunsigned admission_calls;\nint make(const Board *p,Move m,Board *q){admission_calls++;return real_make(p,m,q);}\n'
    return (text[:begin]+changed+wrapper+text[end:]).encode()


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--build',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    if not args.out.is_absolute() or args.out.exists():ap.error('new absolute external directory required')
    args.out.mkdir(parents=True)
    parser=module('unit_parser',HERE/'transform.py');fixture=(HERE/'unit.c.in').read_bytes()
    report={'scope':'actual parsing/admission/budget unit; no worker physical-completion claim',
            'fixture_sha256':sha(fixture),'forms':[],'passed':False}
    manifest=json.loads(args.build.read_text());root=args.build.parent
    for name,dev,sanitize in (('A-shipping',0,False),('A-dev',1,False),('A-sanitized',1,True)):
        directory=args.out/name;directory.mkdir()
        original=(root/'A-protocol/combined.c').read_bytes();instrumented=counted(original,parser)
        (directory/'subject.c').write_bytes(instrumented)
        (directory/'unit.c').write_bytes(b'#define main original_application_main\n#include "subject.c"\n#undef main\n'+fixture)
        command=['cc','-std=c11','-Os','-pthread','-DWORKERS=2','-DTT_BITS=18',f'-DDEV={dev}','-DPROTOCOL_D=0']
        if sanitize:command+=['-g','-fsanitize=address,undefined','-fno-omit-frame-pointer']
        command+=['unit.c','-o','x']
        built=subprocess.run(command,cwd=directory,capture_output=True,text=True,timeout=30)
        row={'id':name,'original_sha256':sha(original),'instrumented_sha256':sha(instrumented),'compile':command,
             'compile_code':built.returncode,'compile_stderr':built.stderr}
        if not built.returncode:
            run=subprocess.run([str(directory/'x')],capture_output=True,text=True,timeout=15)
            row.update(exit=run.returncode,stdout=run.stdout,stderr=run.stderr)
        row['passed']=not row['compile_code'] and row.get('exit')==0
        report['forms'].append(row);(args.out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(row),flush=True)
        if not row['passed']:raise RuntimeError(name+' actual parser unit failed')
    for mode in ('scalar','hq'):
        for dev in (0,1):
            name=f'D-{mode}-'+('dev' if dev else 'shipping');directory=args.out/name;directory.mkdir();sources=directory/'sources';sources.mkdir()
            for path in (root/'D-protocol/sources').iterdir():
                if path.is_file():shutil.copyfile(path,sources/path.name)
            original=(sources/'board.c').read_bytes();instrumented=counted(original,parser)
            (sources/'board.c').write_bytes(instrumented)
            (sources/'runtime-unit.c').write_bytes(b'#define main original_application_main\n#include "runtime.c"\n#undef main\n'+fixture)
            record=next(x for x in manifest['D'] if x['form']=='protocol' and x['id']==f'tiny-D-{mode}-'+('dev' if dev else 'shipping'))
            command=[]
            for arg in record['compile'][:-1]:
                arg=arg.replace(str(root/'D-protocol/sources'),str(sources))
                if arg==str(sources/'runtime.c'):arg=str(sources/'runtime-unit.c')
                command.append(arg)
            command.insert(1,'-DPROTOCOL_D=1');command+=[str(directory/'linked')]
            built=subprocess.run(command,cwd=directory,capture_output=True,text=True,timeout=30)
            row={'id':name,'original_board_sha256':sha(original),'instrumented_board_sha256':sha(instrumented),
                 'compile':command,'compile_code':built.returncode,'compile_stderr':built.stderr}
            if not built.returncode:
                run=subprocess.run([str(directory/'linked')],capture_output=True,text=True,timeout=15)
                row.update(exit=run.returncode,stdout=run.stdout,stderr=run.stderr)
            row['passed']=not row['compile_code'] and row.get('exit')==0
            report['forms'].append(row);(args.out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
            print(json.dumps(row),flush=True)
            if not row['passed']:raise RuntimeError(name+' actual parser unit failed')
    report['passed']=True;(args.out/'results.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
