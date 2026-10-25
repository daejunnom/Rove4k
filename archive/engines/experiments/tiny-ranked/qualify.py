#!/usr/bin/env python3
"""Qualify both real packed-priority source launchers and retained contracts."""
import argparse
import hashlib
import importlib.util
import json
import lzma
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def sha(data):return hashlib.sha256(data).hexdigest()


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def run(command,path,timeout):
    p=subprocess.run(command,capture_output=True,text=True,timeout=timeout)
    path.write_text(json.dumps({'command':command,'code':p.returncode,'stdout':p.stdout,'stderr':p.stderr},indent=2)+'\n')
    print(p.stdout,flush=True)
    if p.returncode:raise RuntimeError('qualification failed: '+str(path))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--reuse-common',type=Path,help='reuse an exact manifest-matched completed common report')
    args=parser.parse_args()
    if not args.out.is_absolute() or args.out.exists() or ROOT in args.out.parents:parser.error('new external output required')
    args.out.mkdir(parents=True)
    validation=args.out/'validation/engines/tests';validation.mkdir(parents=True)
    for name in ('verify.py','chess_oracle.py'):shutil.copyfile(ROOT/'engines/tests'/name,validation/name)
    shutil.copyfile(ROOT/'engines/compact/tiny-a/check.py',validation/'check.py')
    build=json.loads(args.build.read_text());specs=[]
    for record in build['forms']:
        if record['id']=='baseline':continue
        for profile,path in (('dev',record['dev']),('shipping',record['wrapper'])):
            specs.append({'id':record['id']+'-'+profile,'command':[path],'profile':profile,'workers':2,
                          'startup_threads':3,'max_threads':3,'startup_timeout':60,
                          'expected_program_sha256':sha(Path(path).read_bytes())})
    manifest=args.out/'manifest.json';manifest.write_text(json.dumps({'engines':specs},indent=2)+'\n')
    common=args.out/'common/results.json'
    if args.reuse_common:
        previous=json.loads((args.reuse_common.parent/'manifest.json').read_text())
        completed=json.loads((args.reuse_common/'results.json').read_text())
        for name in ('verify.py','chess_oracle.py'):
            if (args.reuse_common.parent/'validation/engines/tests'/name).read_bytes()!=(validation/name).read_bytes():raise ValueError('reused validator differs')
        if previous!={'engines':specs}:raise ValueError('reused common manifest differs')
        if len(completed['engines'])!=len(specs) or any(any(c['status']!='pass' for c in x['checks']) for x in completed['engines']):
            raise ValueError('reused common result incomplete')
        for spec,row in zip(specs,completed['engines']):
            if row['id']!=spec['id'] or len(row['checks'])!=(8 if spec['profile']=='dev' else 5):raise ValueError('reused group coverage differs')
        common=args.reuse_common/'results.json'
        (args.out/'common-reuse.json').write_text(json.dumps({'path':str(common),'sha256':sha(common.read_bytes()),'exact_manifest_match':True},indent=2)+'\n')
    else:
        run(['python3',str(validation/'verify.py'),'--manifest',str(manifest),'--out',str(args.out/'common'),'--plies','16'],args.out/'common-driver.json',180)
    sys.path.insert(0,str(validation))
    from verify import Engine
    producer=module('ranked_producer',args.build.parent/'recipe/campaign.py')
    literal=module('ranked_literal',args.build.parent/'recipe/pack_stream.py').source_literal
    baseline=(args.build.parent/'baseline/bootstrap.py').read_bytes()
    begin,end=producer.argument(baseline);skeleton=baseline[:begin]+b"b'SOURCE'"+baseline[end:]
    identities=[];retained=[]
    for record in build['forms']:
        if record['id']=='baseline':continue
        directory=args.build.parent/record['id'];source=(directory/'main.c').read_bytes()
        wrapper=Path(record['wrapper']).read_bytes();script=lzma.decompress(wrapper[wrapper.index(b'\xfd7zXZ\0'):])
        if script!=(directory/'bootstrap.py').read_bytes():raise ValueError('actual wrapper bootstrap mismatch')
        begin,end=producer.argument(script)
        if script[:begin]+b"b'SOURCE'"+script[end:]!=skeleton:raise ValueError('runtime bootstrap changed')
        if script[begin:end]!=literal(source)[0].encode():raise ValueError('source expression changed')
        spec=next(s for s in specs if s['id']==record['id']+'-shipping')
        engine=Engine(spec,args.out,record['id']+'-identity',10)
        try:
            engine.initialize();engine.assert_threads_stable()
            proc=Path('/proc')/str(engine.process.pid);image=(proc/'exe').read_bytes()
            if sha(image)!=record['native_sha256']:raise ValueError('actual restored native mismatch')
            link=os.readlink(proc/'exe')
            if not link.endswith(' (deleted)') or Path(link.removesuffix(' (deleted)')).parent.exists():raise ValueError('restoration temporary files remain')
            if any((task/'children').read_text().strip() for task in (proc/'task').iterdir()):raise ValueError('restoration child remains')
            engine.send('quit\0isready');engine.ready()
            engine.send('x'*32768+'quit');engine.ready()
            engine.assert_threads_stable();tids=sorted(engine.startup_task_ids)
            engine.close()
            if proc.exists() or any(r.is_alive() for r in engine.readers):raise ValueError('runtime not physically reaped')
            identities.append({'id':record['id'],'wrapper_sha256':sha(wrapper),'restored_native_sha256':sha(image),
                               'matched_expected_native':True,'startup_threads':len(tids),'fixed_tids':tids,
                               'bootstrap_skeleton_unchanged':True,'source_expression_exact':True,
                               'temporary_removed_before_input':True,'no_restoration_children':True,
                               'NUL_and_oversized_line_drained':True,'runtime_absent':True,'readers_joined':True})
        finally:
            if engine.process.poll() is None:engine.terminate()
        cap=args.out/(record['id']+'-cap');cap.mkdir();shutil.copyfile(directory/'combined.c',cap/'main.c')
        command=['cc','-std=c11','-Os','-pthread','-DWORKERS=2','-DTT_BITS=18','-DDEV=1','-DPLY=4','main.c','-o','x']
        compiled=subprocess.run(command,cwd=cap,capture_output=True,text=True,timeout=30)
        if compiled.returncode:raise RuntimeError(compiled.stderr)
        report=args.out/(record['id']+'-retained.json')
        run(['python3',str(validation/'check.py'),'--engine',record['dev'],'--cap-engine',str(cap/'x'),'--out',str(report)],args.out/(record['id']+'-retained-driver.json'),60)
        retained.append({'id':record['id'],'report':str(report),'report_sha256':sha(report.read_bytes()),'cap_compile':command})
    result={'passed':True,'build_sha256':sha(args.build.read_bytes()),'common':str(common),
            'runtime_identities':identities,'retained':retained,
            'validators_sha256':{p.name:sha(p.read_bytes()) for p in validation.iterdir() if p.is_file()}}
    (args.out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'passed':True,'actual_wrappers':len(identities),'retained':len(retained)}),flush=True)


if __name__=='__main__':main()
