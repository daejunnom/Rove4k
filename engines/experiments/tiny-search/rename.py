#!/usr/bin/env python3
"""Whole-file study of tiny-A identifier spellings behind native SHA equality.

Uses the repository's existing lexer/gate, independently of NVCompact. It runs
the actual source launcher's compiler-stdin recipe for every identity gate.
Only exact compiled program matches enter the compressed source comparison.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--measure',type=Path,required=True)
    parser.add_argument('--form',required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--trials',type=int,default=96)
    args=parser.parse_args()
    if not args.out.is_absolute() or args.out.exists() or ROOT in args.out.parents:parser.error('new external directory required')
    args.out.mkdir(parents=True)
    report=json.loads(args.measure.read_text())
    form=next(record for record in report['records'] if record['name']==args.form)
    source=(args.measure.parent/args.form/'main.c').read_bytes()
    if sha(source)!=form['source_sha256']:raise ValueError('measured source changed')
    frozen=args.out/'frozen';frozen.mkdir()
    for name in ('pack_single.py','pack_stream.py','pack.py'):
        (frozen/name).write_bytes((args.measure.parent/'frozen'/name).read_bytes())
    rename_source=(ROOT/'engines/scripts/rename_c.py').read_bytes()
    (frozen/'rename_c.py').write_bytes(rename_source)
    rename=module('tiny_rename',frozen/'rename_c.py').compact_identifiers
    stream=module('tiny_rename_stream',frozen/'pack_stream.py')
    single=module('tiny_rename_single',frozen/'pack_single.py')
    generic=module('tiny_rename_pack',frozen/'pack.py')
    flags=['cc','-std=c11','-Os','-pthread','-DWORKERS=2','-DTT_BITS=18','-DDEV=0']
    command=flags+['-x','c','-','-o','x']
    gate=args.out/'gate';gate.mkdir()
    qualified=[];baseline=None;best=None
    def compile_digest(files,trial):
        nonlocal baseline,best
        data=files['main.c']
        built=subprocess.run(command,input=data,cwd=gate,capture_output=True,timeout=30)
        if built.returncode:
            raise subprocess.CalledProcessError(built.returncode,command,output=built.stdout,stderr=built.stderr)
        binary=(gate/'x').read_bytes();digest=sha(binary)
        if baseline is None:baseline=digest
        if digest==baseline:
            wrapper,record=stream.make_stream(data,command,'xz')
            path=args.out/f'trial-{trial}.c';path.write_bytes(data)
            qualified.append({'trial':trial,'source_bytes':len(data),'source_sha256':sha(data),
                              'complete_xz_bytes':len(wrapper),'native_sha256':digest,'source':str(path)})
            if best is None or len(wrapper)<best['complete_xz_bytes']:
                best=qualified[-1]
                (args.out/'best.c').write_bytes(data)
            print(json.dumps(qualified[-1]),flush=True)
        return digest
    accepted,metadata=rename({'main.c':source},compile_digest,max_trials=args.trials)
    (args.out/'all-accepted.c').write_bytes(accepted['main.c'])
    chosen=(args.out/'best.c').read_bytes()
    directory=args.out/'selected';directory.mkdir()
    (directory/'main.c').write_bytes(chosen)
    run=subprocess.run(command,input=chosen,cwd=directory,capture_output=True,timeout=30)
    if run.returncode or sha((directory/'x').read_bytes())!=baseline:raise ValueError('selected candidate changed program identity')
    packages=generic.write_launchers({'main.c':chosen},directory/'generic',command=flags+['main.c','-o','x'])
    packages+=single.write_single(chosen,directory/'single',command)
    packages+=stream.write_stream(chosen,directory/'stream',command)
    report={'input_measure':str(args.measure),'input_form':args.form,'rename_helper_sha256':sha(rename_source),
            'compiler_stdin':command,'baseline_program_sha256':baseline,'qualified':qualified,
            'rename':metadata,'selected':best,'artifacts':packages,'minimum_complete':min(packages,key=lambda p:p['bytes']),
            'no_NPS_comparison':True}
    (args.out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'selected':best,'minimum_complete':report['minimum_complete']}),flush=True)


if __name__=='__main__':main()
