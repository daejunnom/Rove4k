#!/usr/bin/env python3
"""Actual complete-file, retained-search and raw-runtime parser qualification."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command,out,timeout):
    process=subprocess.run(command,capture_output=True,text=True,timeout=timeout)
    out.write_text(json.dumps({'command':command,'returncode':process.returncode,'stdout':process.stdout,'stderr':process.stderr},indent=2)+'\n')
    print(process.stdout,flush=True)
    if process.returncode:raise RuntimeError('qualification failed: '+str(out))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if not args.out.is_absolute() or args.out.exists():parser.error('new external output directory required')
    args.out.mkdir(parents=True)
    source=args.build.parent;build=json.loads(args.build.read_text())
    validation=args.out/'validation/engines/tests';validation.mkdir(parents=True)
    for name in ('verify.py','chess_oracle.py'):
        shutil.copyfile(ROOT/'engines/tests'/name,validation/name)
    shutil.copyfile(ROOT/'engines/compact/tiny-a/check.py',validation/'check.py')
    specs=[]
    a=next(r for r in build['A'] if r['form']=='protocol')
    for name,path,profile in (('A-protocol-dev',a['dev'],'dev'),('A-protocol-source',a['wrapper'],'shipping')):
        specs.append({'id':name,'command':[path],'profile':profile,'workers':2,'startup_threads':3,'max_threads':3,'startup_timeout':60,'expected_program_sha256':sha(Path(path))})
    records=[]
    for record in build['D']:
        if record['form']!='protocol':continue
        spec={'id':record['id'],'command':record['command'],'profile':record['profile'],'workers':2,
              'startup_threads':3,'max_threads':3,'expected_program_sha256':record['native_sha256']}
        specs.append(spec)
        launchers=[]
        if record['packing']:
            p=record['packing'];specs.append({**spec,'id':spec['id']+'-self','command':[p['output']],'expected_program_sha256':p['output_sha256']})
            launchers=[{'path':p['output'],'sha256':p['output_sha256']}]
        records.append({**record,'startup_threads':3,'launchers':launchers})
    manifest=args.out/'manifest.json';manifest.write_text(json.dumps({'engines':specs},indent=2)+'\n')
    run(['python3',str(validation/'verify.py'),'--manifest',str(manifest),'--out',str(args.out/'common'),'--plies','16'],
        args.out/'common-driver.json',180)
    cap=args.out/'A-cap';cap.mkdir();shutil.copyfile(source/'A-protocol/combined.c',cap/'main.c')
    command=['cc','-std=c11','-Os','-pthread','-DWORKERS=2','-DTT_BITS=18','-DDEV=1','-DPLY=4','main.c','-o','x']
    compiled=subprocess.run(command,cwd=cap,capture_output=True,text=True,timeout=30)
    if compiled.returncode:raise RuntimeError(compiled.stderr)
    run(['python3',str(validation/'check.py'),'--engine',a['dev'],'--cap-engine',str(cap/'x'),'--out',str(args.out/'A-retained.json')],
        args.out/'A-retained-driver.json',60)
    dmanifest=args.out/'D-build.json';dmanifest.write_text(json.dumps({'engines':records},indent=2)+'\n')
    run(['python3',str(ROOT/'engines/compact/tiny-d/algorithms.py'),'--build',str(dmanifest),'--out',str(args.out/'D-retained'),'--timeout','180'],
        args.out/'D-retained-driver.json',190)
    run(['python3',str(ROOT/'engines/compact/tiny-d/test_runtime.py'),'--source-root',str(source/'D-protocol/sources'),'--out',str(args.out/'raw-runtime')],
        args.out/'raw-runtime-driver.json',90)
    (args.out/'results.json').write_text(json.dumps({'passed':True,'build_sha256':sha(args.build),'validator_sha256':{p.name:sha(p) for p in validation.iterdir() if p.is_file()},
             'manifest':str(manifest),'common':str(args.out/'common/results.json'),'retained_A':str(args.out/'A-retained.json'),
             'retained_D':str(args.out/'D-retained/results.json'),'raw_runtime':str(args.out/'raw-runtime/results.json')},indent=2)+'\n')


if __name__=='__main__':main()
