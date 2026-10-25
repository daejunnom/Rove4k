#!/usr/bin/env python3
"""Bounded functional qualification of the measured tiny search winner."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import queue
import subprocess
import threading

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--measure',type=Path,required=True)
    parser.add_argument('--rename',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if not args.out.is_absolute() or args.out.exists():parser.error('new external output required')
    args.out.mkdir(parents=True)
    renamed=json.loads(args.rename.read_text())
    wrapper=renamed['minimum_complete']
    manifest={'engines':[{'id':'tiny-search-selected','command':[wrapper['path']],
                         'profile':'shipping','workers':2,'startup_threads':3,
                         'expected_program_sha256':wrapper['sha256']} ]}
    (args.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    command=['python3',str(ROOT/'engines/tests/verify.py'),'--manifest',str(args.out/'manifest.json'),
             '--out',str(args.out/'shipping'),'--suite','shipping','--plies','16']
    process=subprocess.run(command,capture_output=True,text=True,timeout=90)
    (args.out/'shipping-driver.json').write_text(json.dumps({'command':command,'code':process.returncode,
                    'stdout':process.stdout,'stderr':process.stderr},indent=2)+'\n')
    print(process.stdout,flush=True)
    if process.returncode:raise RuntimeError('selected complete wrapper shipping gate failed')
    chosen=args.measure.parent/'winner-state'
    cap=args.out/'cap';cap.mkdir()
    (cap/'main.c').write_bytes((chosen/'combined.c').read_bytes())
    command=['cc','-std=c11','-Os','-pthread','-DWORKERS=2','-DTT_BITS=18','-DDEV=1','-DPLY=4','main.c','-o','x']
    subprocess.run(command,cwd=cap,capture_output=True,check=True,timeout=30)
    command=['python3',str(ROOT/'engines/compact/tiny-a/check.py'),'--engine',str(chosen/'dev/x'),
             '--cap-engine',str(cap/'x'),'--out',str(args.out/'algorithms.json')]
    process=subprocess.run(command,capture_output=True,text=True,timeout=45)
    (args.out/'algorithm-driver.json').write_text(json.dumps({'command':command,'code':process.returncode,
                      'stdout':process.stdout,'stderr':process.stderr},indent=2)+'\n')
    print(process.stdout,flush=True)
    if process.returncode:raise RuntimeError('actual algorithm/cap fixture failed')
    # The actual package compiles C on stdin and then fd-execs it at the same
    # PID. Compare /proc/exe once UCI readiness proves compiler completion.
    process=subprocess.Popen([wrapper['path']],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
    lines=queue.Queue()
    thread=threading.Thread(target=lambda:[lines.put(line.strip()) for line in process.stdout],daemon=True);thread.start()
    try:
        process.stdin.write('uci\nisready\n');process.stdin.flush()
        while lines.get(timeout=10)!='readyok':pass
        actual=hashlib.sha256(Path(f'/proc/{process.pid}/exe').read_bytes()).hexdigest()
        tasks=sorted(os.listdir(f'/proc/{process.pid}/task'))
        if actual!=renamed['baseline_program_sha256'] or len(tasks)!=3:raise ValueError('actual packaged program identity/resource mismatch')
        process.stdin.write('quit\n');process.stdin.flush();process.wait(timeout=3)
        if process.returncode:raise ValueError('packaged identity probe failed shutdown')
        (args.out/'identity.json').write_text(json.dumps({'passed':True,'package_sha256':wrapper['sha256'],
                          'actual_exe_sha256':actual,'same_as_all_accepted_native_gates':True,
                          'startup_tasks':tasks,'quit_code':process.returncode},indent=2)+'\n')
    finally:
        if process.poll() is None:process.kill();process.wait()
    print('selected wrapper algorithms/cap/identity passed',flush=True)


if __name__=='__main__':main()
