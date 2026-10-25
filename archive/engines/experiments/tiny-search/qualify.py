#!/usr/bin/env python3
"""Compare actual deterministic search state for frozen readable candidates."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--candidate',action='append',type=Path,required=True)
    parser.add_argument('--sanitize',action='store_true')
    args=parser.parse_args()
    if not args.out.is_absolute() or args.out.exists():parser.error('new absolute evidence directory required')
    args.out.mkdir(parents=True)
    fixture=(HERE/'equivalence.c.in').read_bytes()
    (args.out/'equivalence.c.in').write_bytes(fixture)
    reference=None
    results=[]
    for index,candidate in enumerate(args.candidate):
        directory=args.out/str(index);directory.mkdir()
        source=candidate.read_bytes()
        (directory/'subject.c').write_bytes(source)
        combined=b'#define main tiny_application_main\n#include "subject.c"\n#undef main\n'+fixture
        (directory/'check.c').write_bytes(combined)
        command=['cc','-std=c11','-O1' if args.sanitize else '-O2','-pthread','-DWORKERS=1','-DTT_BITS=18','-DDEV=1']
        if args.sanitize:command+=['-g','-fsanitize=address,undefined','-fno-omit-frame-pointer']
        command+=['check.c','-o','check']
        built=subprocess.run(command,cwd=directory,capture_output=True,text=True,timeout=60)
        result={'candidate':str(candidate),'source_sha256':hashlib.sha256(source).hexdigest(),
                'fixture_sha256':hashlib.sha256(fixture).hexdigest(),'compile':command,
                'compile_code':built.returncode,'stderr':built.stderr}
        if not built.returncode:
            run=subprocess.run([str(directory/'check')],cwd=directory,capture_output=True,text=True,timeout=30)
            result.update({'exit':run.returncode,'stdout':run.stdout,'runtime_stderr':run.stderr})
            rows=[json.loads(line) for line in run.stdout.splitlines()]
            result['cases']=len(rows)
            if reference is None:reference=rows
            result['exact_reference']=rows==reference
            result['pass']=not run.returncode and len(rows)==12 and rows==reference
        else:result['pass']=False
        results.append(result)
        (args.out/'results.json').write_text(json.dumps({'results':results,'passed':all(r['pass'] for r in results)},indent=2)+'\n')
        print(json.dumps({'candidate':str(candidate),'pass':result['pass'],'cases':result.get('cases')}),flush=True)
    if not all(r['pass'] for r in results):raise SystemExit(1)


if __name__=='__main__':main()
