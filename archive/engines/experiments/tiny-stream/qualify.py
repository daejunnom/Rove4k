#!/usr/bin/env python3
"""Bounded board/search/lifecycle gates for the measured streaming prototype."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--measure',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if not args.out.is_absolute() or args.out.exists():parser.error('new absolute output required')
    args.out.mkdir(parents=True)
    report=json.loads(args.measure.read_text());candidate=next(r for r in report['records'] if r['name']=='stream')
    folder=args.measure.parent/'stream'
    manifest={'engines':[{'id':'stream-dev','command':[str(folder/'dev/x')],'profile':'dev','workers':2,'startup_threads':3},
                         {'id':'stream-whole','command':[candidate['minimum_complete']['path']],'profile':'shipping','workers':2,'startup_threads':3,
                          'expected_program_sha256':candidate['minimum_complete']['sha256']}]}
    (args.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    command=['python3',str(ROOT/'engines/tests/verify.py'),'--manifest',str(args.out/'manifest.json'),
             '--out',str(args.out/'blackbox'),'--plies','16']
    process=subprocess.run(command,capture_output=True,text=True,timeout=120)
    print(process.stdout,flush=True)
    (args.out/'blackbox-driver.json').write_text(json.dumps({'command':command,'code':process.returncode,'stdout':process.stdout,'stderr':process.stderr},indent=2)+'\n')
    if process.returncode:raise RuntimeError('actual black-box gate failed')
    fixture=(HERE/'picker_contract.c.in').read_bytes();source=(folder/'combined.c').read_bytes()
    (args.out/'subject.c').write_bytes(source)
    (args.out/'picker.c').write_bytes(b'#define main tiny_application_main\n#include "subject.c"\n#undef main\n'+fixture)
    results=[]
    for sanitize in (False,True):
        name='picker-san' if sanitize else 'picker'
        command=['cc','-std=c11','-O1' if sanitize else '-O2','-pthread','-DDEV=1','-DWORKERS=1','-DTT_BITS=18']
        if sanitize:command+=['-g','-fsanitize=address,undefined','-fno-omit-frame-pointer']
        command+=['picker.c','-o',name]
        built=subprocess.run(command,cwd=args.out,capture_output=True,text=True,timeout=30)
        result={'compile':command,'compile_code':built.returncode,'compile_stderr':built.stderr}
        if not built.returncode:
            process=subprocess.run([str(args.out/name)],capture_output=True,text=True,timeout=30)
            result.update({'code':process.returncode,'stdout':process.stdout,'stderr':process.stderr})
        results.append(result)
        if built.returncode or result.get('code'):raise RuntimeError('picker contract failed: '+json.dumps(result))
    cap=args.out/'cap';cap.mkdir();(cap/'main.c').write_bytes(source)
    subprocess.run(['cc','-std=c11','-Os','-pthread','-DDEV=1','-DWORKERS=2','-DTT_BITS=18','-DPLY=4','main.c','-o','x'],cwd=cap,check=True,capture_output=True,timeout=30)
    command=['python3',str(ROOT/'engines/compact/tiny-a/check.py'),'--engine',str(folder/'dev/x'),
             '--cap-engine',str(cap/'x'),'--out',str(args.out/'algorithms.json')]
    process=subprocess.run(command,capture_output=True,text=True,timeout=60)
    print(process.stdout,flush=True)
    (args.out/'algorithm-driver.json').write_text(json.dumps({'command':command,'code':process.returncode,'stdout':process.stdout,'stderr':process.stderr},indent=2)+'\n')
    if process.returncode:raise RuntimeError('search algorithm/cap gate failed')
    (args.out/'results.json').write_text(json.dumps({'passed':True,'source_sha256':hashlib.sha256(source).hexdigest(),
                     'picker_fixture_sha256':hashlib.sha256(fixture).hexdigest(),'picker':results,
                     'policy':'changed stable ties/live scoring; no exact node equality claim; no NPS comparison'},indent=2)+'\n')


if __name__=='__main__':main()
