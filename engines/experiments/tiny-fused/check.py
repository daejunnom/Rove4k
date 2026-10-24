#!/usr/bin/env python3
"""Two-configuration focused fixture for the frozen failed-size fused candidate."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

HERE=Path(__file__).resolve().parent
EXPECTED='60ae3c097b2337f6b7a260824c61c819a95f90c38a7512c52f8eb9bd5d76f5be'


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if not args.out.is_absolute() or args.out.exists():parser.error('new absolute external output required')
    if HERE.parents[2] in args.out.resolve().parents:parser.error('output must be outside checkout')
    source=args.source.read_bytes()
    if sha(source)!=EXPECTED:parser.error('unexpected frozen production source')
    marker=b'static int offer(Visit *x,Fact d){'
    hook=b'    Board q;if(!apply(p,d,&q))return 0;'
    if source.count(marker)!=1 or source.count(hook)!=1:parser.error('production offer shape changed')
    instrumented=source.replace(marker,b'static void observe(Visit *,Fact);\n'+marker,1).replace(hook,b'    Board q;observe(x,d);if(!apply(p,d,&q))return 0;',1)
    fixture=(HERE/'unit.c.in').read_bytes()
    unit=b'#define main original_application_main\n'+instrumented+b'\n#undef main\n'+fixture
    args.out.mkdir(parents=True)
    (args.out/'production.c').write_bytes(source)
    (args.out/'instrumented.c').write_bytes(instrumented)
    (args.out/'unit.c').write_bytes(unit)
    (args.out/'unit.c.in').write_bytes(fixture)
    (args.out/'check.py').write_bytes(Path(__file__).read_bytes())
    report={'scope':'focused actual-code correctness only; no size, equivalence, runtime-pool or performance acceptance',
            'production_sha256':sha(source),'instrumented_sha256':sha(instrumented),'fixture_sha256':sha(fixture),
            'instrumentation':'one observe immediately before offer apply; only root pointer and nonnull worker are recorded; no outcomes or counters forced',
            'compiler':subprocess.check_output(['cc','--version'],text=True).splitlines()[0],
            'configurations':[]}
    run_seconds=0.0
    for name,flags in (('Os',[]),('Os-asan-ubsan',['-fsanitize=address,undefined','-fno-omit-frame-pointer'])):
        command=['cc','-std=c11','-Os','-pthread','-DDEV=1',*flags,str(args.out/'unit.c'),'-o',str(args.out/name)]
        row={'id':name,'command':command};report['configurations'].append(row)
        compiled=subprocess.run(command,capture_output=True,timeout=40)
        row['compile_code']=compiled.returncode
        (args.out/(name+'-compile.stderr')).write_bytes(compiled.stderr)
        if compiled.returncode:
            (args.out/'results.json').write_text(json.dumps(report,indent=2)+'\n');raise SystemExit('compile failed: '+name)
        env=os.environ.copy();env['ASAN_OPTIONS']='detect_leaks=1:abort_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1:print_stacktrace=1'
        started=time.monotonic()
        try:
            result=subprocess.run([str(args.out/name)],capture_output=True,env=env,timeout=max(1,60-run_seconds))
            row.update({'exit_code':result.returncode,'stdout':name+'.jsonl','stderr':name+'.stderr'})
            (args.out/(name+'.jsonl')).write_bytes(result.stdout);(args.out/(name+'.stderr')).write_bytes(result.stderr)
            row['cases']=[json.loads(line) for line in result.stdout.splitlines()]
        except subprocess.TimeoutExpired as error:
            row['timeout']=True
            (args.out/(name+'.jsonl')).write_bytes(error.stdout or b'');(args.out/(name+'.stderr')).write_bytes(error.stderr or b'')
        elapsed=time.monotonic()-started;run_seconds+=elapsed;row['runtime_seconds']=elapsed
        report['total_runtime_seconds']=run_seconds
        (args.out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(row),flush=True)
        if row.get('exit_code')!=0:raise SystemExit('focused fixture failed: '+name)


if __name__=='__main__':main()
