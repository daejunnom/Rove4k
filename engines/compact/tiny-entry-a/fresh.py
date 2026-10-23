#!/usr/bin/env python3
"""Archive the complete named source closure through Git, then rebuild twice.

The temporary repository has no remote or commits. It never uses the calling
checkout's index. Its tree/archive are evidence of an isolated source payload,
not evidence that the payload has been committed in the project repository.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
ENTRY=HERE.relative_to(REPO)
LOCAL=('.gitattributes','README.md','engine.c','bootstrap.py.in','launcher.sh',
       'recipe.json','build.py','fresh.py','verify.py')
TESTS=('engines/tests/verify.py','engines/tests/chess_oracle.py')


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--policy',choices=('loose','root-hint-leader-repair','root-normal-slots','root-pals-feedback'),default='loose',help='forward the same build-time policy to both archived rebuilds')
    args=parser.parse_args();out=args.out.resolve()
    if not args.out.is_absolute() or out.exists() or out==REPO or REPO in out.parents or any((p/'.git').exists() for p in (out,*out.parents)):
        parser.error('a new absolute output outside any Git checkout is required')
    recipe=json.loads((HERE/'recipe.json').read_text())
    paths=sorted([str(ENTRY/name) for name in LOCAL]+list(recipe['helper_sha256'])+list(TESTS))
    if len(paths)!=len(set(paths)):raise ValueError('duplicate source path')
    out.mkdir(parents=True);raw=out/'raw-inputs';tree=out/'source-git';tree.mkdir()
    report={'complete':False,'scope':'isolated Git source archive; no project index, commits or remote used',
            'policy':args.policy,'source_paths':paths,'inputs':{},'builds':[]}
    def save():(out/'fresh.json').write_text(json.dumps(report,indent=2)+'\n')
    def run(command,cwd=None):
        result=subprocess.run(command,cwd=cwd,capture_output=True,text=True,timeout=180)
        if result.returncode:raise RuntimeError(repr(command)+'\n'+result.stdout+result.stderr)
        return result.stdout.strip()
    save()
    try:
        for relative in paths:
            source=REPO/relative
            if source.is_symlink() or not source.is_file():raise ValueError('nonregular source: '+relative)
            data=source.read_bytes();normalized=data.replace(b'\r\n',b'\n')
            if b'\r' in normalized:raise ValueError('lone CR source: '+relative)
            for base,content in ((raw,data),(tree,normalized)):
                target=base/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(content)
            report['inputs'][relative]={'raw_bytes':len(data),'raw_sha256':sha(data),
                                       'LF_sha256':sha(normalized),'LF_normalization':data!=normalized}
        run(['git','init','--quiet',str(tree)])
        run(['git','-c','core.autocrlf=false','add','--']+paths,tree)
        tree_id=run(['git','write-tree'],tree)
        archive=out/'source.tar'
        run(['git','archive','--format=tar','--output='+str(archive),tree_id],tree)
        report.update(tree=tree_id,archive_sha256=sha(archive.read_bytes()),archive_bytes=archive.stat().st_size,
                      git_version=run(['git','--version']),uncommitted_source_tree=True)
        first=None
        for index in (1,2):
            extracted=out/('checkout-'+str(index));extracted.mkdir()
            with tarfile.open(archive,'r') as stream:
                members=stream.getmembers()
                actual={m.name.rstrip('/') for m in members if m.isfile()}
                if actual!=set(paths) or any(not (m.isfile() or m.isdir()) or m.name.startswith('/') or '..' in Path(m.name).parts for m in members):
                    raise ValueError('archive closure contains unexpected path/type')
                stream.extractall(extracted,filter='data')
            for relative in paths:
                data=(extracted/relative).read_bytes()
                if sha(data)!=report['inputs'][relative]['LF_sha256']:raise ValueError('Git archive source changed: '+relative)
            build=out/('build-'+str(index))
            command=[sys.executable,'-B',str(extracted/ENTRY/'build.py'),'--out',str(build),'--dev']
            if args.policy!='loose':command+=['--policy',args.policy]
            output=run(command)
            result=json.loads((build/'build.json').read_text())
            if not result['complete'] or not result['diagnostic_exact_control'] or result.get('policy','loose')!=args.policy:raise ValueError('archived builder incomplete/policy differs')
            payload=tuple((build/name).read_bytes() for name in ('main.c','native/x','x','dev/main.c','dev/x','bootstrap.py'))
            if first is None:first=payload
            elif payload!=first:raise ValueError('independent archived checkouts produced different bytes')
            report['builds'].append({'command':command,'stdout':output,'complete':True,'actual':result['actual'],
                                     'entry_path':str(extracted/ENTRY),'builder_sha256':sha((extracted/ENTRY/'build.py').read_bytes())})
            save()
        report.update(complete=True,independent_archived_checkouts=2,attempts_per_checkout=2,
                      source_native_whole_and_DEV_identical=True)
        save();print(json.dumps({'complete':True,'out':str(out),'tree':tree_id,'archive_sha256':report['archive_sha256']}))
    except Exception as error:
        report['error']=repr(error);save();raise


if __name__=='__main__':main()
