#!/usr/bin/env python3
"""Compare whole files for a shared streaming walk/picker with frozen inputs."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent


def sha(data):return hashlib.sha256(data).hexdigest()


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',type=Path,required=True,help='immutable readable 5615 B structural winner')
    parser.add_argument('--reference',type=Path,required=True,help='tiny-search clean measure.json')
    parser.add_argument('--rename',type=Path,required=True,help='immutable existing rename results.json; no new search')
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if not args.out.is_absolute() or args.out.exists():parser.error('new absolute external directory required')
    args.out.mkdir(parents=True)
    frozen=args.out/'frozen';frozen.mkdir()
    source=args.baseline.read_bytes();(frozen/'baseline.c').write_bytes(source)
    for name in ('pack.py','pack_single.py','pack_stream.py','specialize.py','minify.py','stitch.py'):
        (frozen/name).write_bytes((args.reference.parent/'frozen'/name).read_bytes())
    compiler_kwargs={}
    reference=json.loads(args.reference.read_text())
    owner_hash=reference.get('recipe_sha256',{}).get('engines/scripts/compiler_group.py')
    if owner_hash is not None:
        owner_data=(args.reference.parent/'frozen/compiler_group.py').read_bytes()
        if sha(owner_data)!=owner_hash:raise ValueError('reference compiler owner changed')
        (frozen/'compiler_group.py').write_bytes(owner_data)
        compiler_kwargs['compiler_group']=module('stream_compiler_group',frozen/'compiler_group.py').transform_bootstrap
    (frozen/'rename_c.py').write_bytes((args.rename.parent/'frozen/rename_c.py').read_bytes())
    (frozen/'transform.py').write_bytes((HERE/'transform.py').read_bytes())
    transform=module('stream_transform',frozen/'transform.py').transform
    specialize=module('stream_specialize',frozen/'specialize.py').specialize_c
    compact=module('stream_minify',frozen/'minify.py').compact_source
    strip=module('stream_strip',frozen/'stitch.py').strip_dev_counters
    rename=module('stream_existing_rename',frozen/'rename_c.py')
    generic=module('stream_pack',frozen/'pack.py').write_launchers
    single=module('stream_single',frozen/'pack_single.py').write_single
    stream=module('stream_stream',frozen/'pack_stream.py').write_stream
    prior=json.loads(args.rename.read_text())
    spellings=[trial for trial in prior['rename']['trials'] if trial['status']=='accepted' and trial['trial']<=prior['selected']['trial']]
    report={'baseline':str(args.baseline),'baseline_sha256':sha(source),'frozen_recipe_sha256':{p.name:sha(p.read_bytes()) for p in frozen.iterdir() if p.is_file()},
            'compiler':subprocess.check_output(['cc','--version'],text=True).splitlines()[0],
            'existing_fixed_map_trials':len(spellings),'no_new_identifier_search':True,'records':[]}
    flags=['cc','-std=c11','-Os','-pthread','-DWORKERS=2','-DTT_BITS=18','-DDEV=0']
    file_command=flags+['main.c','-o','x'];stdin_command=flags+['-x','c','-','-o','x']
    changed,policy=transform(source)
    for name,combined in (('baseline',source),('stream',changed)):
        directory=args.out/name;directory.mkdir()
        (directory/'combined.c').write_bytes(combined)
        specialized,observations=specialize({'main.c':combined},directory/'preprocess',file_command,os.environ.copy())
        compacted=compact(specialized['main.c'],'c');compacted,counters=strip(compacted)
        renamed={'main.c':compacted}
        for trial in spellings:renamed=rename._replace(renamed,trial['identifier'],trial['replacement'])
        renamed=renamed['main.c']
        native={}
        for label,data in (('uncontracted',compacted),('fixed-map',renamed)):
            process=subprocess.run(stdin_command,input=data,cwd=directory,capture_output=True,timeout=30)
            if process.returncode:raise RuntimeError(process.stderr.decode())
            native[label]={'bytes':len((directory/'x').read_bytes()),'sha256':sha((directory/'x').read_bytes())}
        if native['uncontracted']!=native['fixed-map']:raise ValueError('existing spelling map changed candidate program identity')
        (directory/'main.c').write_bytes(renamed)
        (directory/'uncontracted.c').write_bytes(compacted)
        dev=directory/'dev';dev.mkdir();(dev/'main.c').write_bytes(combined)
        subprocess.run(['cc','-std=c11','-Os','-pthread','-DWORKERS=2','-DTT_BITS=18','-DDEV=1','main.c','-o','x'],cwd=dev,check=True,timeout=30)
        packages=generic({'main.c':renamed},directory/'generic',command=file_command,**compiler_kwargs)
        packages+=single(renamed,directory/'single',stdin_command,**compiler_kwargs)
        packages+=stream(renamed,directory/'stream',stdin_command,**compiler_kwargs)
        best=min(packages,key=lambda r:r['bytes'])
        if name=='baseline' and (sha(renamed)!=prior['selected']['source_sha256'] or best['sha256']!=prior['minimum_complete']['sha256']):
            raise ValueError('actual 5419 B reference did not reproduce')
        record={'name':name,'readable_sha256':sha(combined),'uncontracted_bytes':len(compacted),
                'source_bytes':len(renamed),'source_sha256':sha(renamed),'native':native,
                'compiler_stdin':stdin_command,'preprocessor':observations,'counters':counters,
                'policy':policy if name!='baseline' else 'frozen reference',
                'minimum_complete':best,'artifacts':packages}
        report['records'].append(record)
        (args.out/'measure.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({'name':name,'source':len(renamed),'complete':best['bytes'],'native':native}),flush=True)


if __name__=='__main__':main()
