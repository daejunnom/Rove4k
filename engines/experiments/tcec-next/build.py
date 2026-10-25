#!/usr/bin/env python3
"""Regenerate selected7f controls, then build the explicit next full profiles.

Old producers, old expectations and the shared verifier remain unchanged.
--measure labels a comparison and never writes the literal recipe. Default
admission requires manually reviewed complete-file and native identities.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import signal
import lzma

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
SELF='engines/experiments/tcec-next/build.py'
OLD='engines/experiments/tcec-scope/build.py'
VERIFIER='engines/experiments/tcec-scope/verify.py'
OLD_PIN='fc916e798952cff1c915a6846e758874bc2d858b3c59dec73870b95c7e3d4828'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);sys.modules[name]=result
    spec.loader.exec_module(result);return result


def text(path):
    data=path.read_bytes().replace(b'\r\n',b'\n')
    if b'\r' in data:raise ValueError('lone CR in source')
    return data


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--entry',choices=('A','B','C','E','F','F8'),required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--measure',action='store_true')
    args=parser.parse_args();out=args.out.resolve()
    old=load('next_control_tools',REPO/OLD)
    require,pin=old.require,old.pin
    require(pin(text(REPO/OLD))['sha256']==OLD_PIN,'maintained producer changed')
    require(sys.platform=='linux' and args.out.is_absolute() and not out.exists()
            and not any((p/'.git').exists() for p in (out,*out.parents)), 'new absolute external Linux output required')
    recipe_raw=text(HERE/'recipe.json');recipe=json.loads(recipe_raw);row=recipe['selected'][args.entry]
    require(args.measure or row['expected'],'unqualified literal selection; run explicit --measure comparison')
    out.mkdir(parents=True)
    report=dict(format=1,**{'class':'tcec-full-C-v1'},entry=args.entry,
                family='F' if args.entry=='F8' else args.entry,complete=False,reproducible=False,
                resources=dict(workers=8 if args.entry=='F8' else 2,tt_bits=18,ply=128,max_position_plies=4095),
                runtime_policy=old.runtime_policy('per-go','async',8 if args.entry=='F8' else 2),
                policy=row['policy'],commands=[],attempts=[],source_proofs=[],
                qualification=dict(selection='experimental-measurement' if args.measure else 'selected-literal-recipe',
                                   runtime=False,rules_eligibility='unproven',game_strength='unproven'),
                authority='fresh frozen maintained source producer, then independently composed next projections')
    def save():(out/'build.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    # Give nested source owners time to finish their own cooperative shutdown.
    class Host(old.Host):
        def settle(self,child,record,force=False):
            if record.get('kind')=='fresh-selected-control':record['cooperative_termination_seconds']=30
            return super().settle(child,record,force)
    old.LIMITS.update(aggregate_wall=1800,per_command_wall=600,parent_AS=4<<30,child_AS=4<<30,
                      parent_CPU=300,parent_CPU_hard=390,child_CPU=360)
    previous=signal.signal(signal.SIGCHLD,signal.SIG_DFL);host=Host(out,report,save)
    try:
        old_recipe=json.loads(text(REPO/'engines/experiments/tcec-scope/recipe.json'))
        prior=old_recipe['selected'][args.entry]
        names={**old_recipe['common_producer_sha256'],**prior['producer_sha256']}
        closure=old.producer_closure(args.entry)
        for name,expected in names.items():
            data=text(REPO/name);require(pin(data)['sha256']==expected,'control source drift: '+name);closure[name]=data
        closure['engines/experiments/tcec-scope/recipe.json']=text(REPO/'engines/experiments/tcec-scope/recipe.json')
        own={}
        for name,expected in recipe['producer_sha256'].items():
            data=text(REPO/name);require(pin(data)['sha256']==expected,'next source drift: '+name);own[name]=data
        own['engines/experiments/tcec-next/recipe.json']=recipe_raw
        own[SELF]=text(Path(__file__))
        for name in (VERIFIER,'engines/compact/tiny-entry-d/verify.py','engines/tests/chess_oracle.py','engines/scripts/source_package.py'):
            own[name]=text(REPO/name)
        for root,items in ((out/'producer-repo',closure),(out/'inputs',own)):
            for name,data in items.items():
                target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        report['control_source_closure']={k:pin(v) for k,v in sorted(closure.items())}
        report['inputs']={k:pin(v) for k,v in sorted(own.items())}
        report['selected_verifier']=dict(path=VERIFIER,inputs=report['inputs'])
        save()
        frozen=out/'producer-repo'
        host.run([sys.executable,'-I','-B',frozen/OLD,'--entry',args.entry,'--out',out/'control'],
                 cwd=out,kind='fresh-selected-control')
        control=json.loads((out/'control/build.json').read_bytes())
        require(control['complete'] and control['reproducible']
                and control['expected_contract']==prior['expected']
                and control['host_cleanup']=={'unsettled_commands':0,'errors':[]}
                and all(c['returncode']==0 and c['terminal'] and c['reaped'] and c['owned_group_absent']
                        and not c['forced_cleanup'] for c in control['commands']), 'fresh selected control failed')
        base=(out/'control/main.c').read_bytes()
        require(pin(base)=={'bytes':prior['expected']['source_bytes'],'sha256':prior['expected']['source_sha256']},'control source differs')
        report['control']=dict(source=pin(base),whole=dict(bytes=prior['expected']['whole_bytes'],sha256=prior['expected']['whole_sha256']),
                               report=pin((out/'control/build.json').read_bytes()))
        ownroot=out/'inputs'
        compose=load('next_frozen_compose',ownroot/'engines/experiments/tcec-next/compose.py')
        wrapper=load('next_frozen_wrapper',ownroot/'engines/experiments/tcec-next/wrapper.py')
        package=load('next_frozen_package',ownroot/'engines/scripts/source_package.py')
        unlink=compose.module('self_unlink')
        compiler,compression=control['compiler'],row['compression']
        report.update(compiler=compiler,compression=compression,
                      wrapper_contract=wrapper.contract(package,unlink,compiler))
        for attempt in ('first','repeat'):
            directory=out/attempt;directory.mkdir();native_dir=directory/'native';native_dir.mkdir()
            source,proof=compose.transform_source(base,family=args.entry,**row['policy'])
            require(compose.restore_source(source,proof)==base,'full composed inverse differs')
            host.run(compiler,cwd=native_dir,kind=attempt+'-compile',data=source)
            native=(native_dir/'x').read_bytes()
            whole=wrapper.package(package,unlink,source,compression,compiler)
            header=wrapper.header(package,unlink,compiler);payload=whole[len(header):]
            decoder=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
            require(decoder.decompress(payload)==source and decoder.eof and not decoder.unused_data,'strict decode differs')
            for name,data in (('main.c',source),('x',whole),('header.sh',header),('payload.lzma',payload)):
                (directory/name).write_bytes(data)
            (directory/'x').chmod(0o700)
            proofs=[proof];(directory/'source-proof.json').write_text(json.dumps(proofs,indent=2)+'\n')
            expected={kind+'_'+key:value for kind,data in (('source',source),('native',native),('whole',whole),('header',header),('payload',payload)) for key,value in pin(data).items()}
            report['attempts'].append(dict(directory=attempt,**expected,source_proofs=proofs));save()
        a,b=report['attempts']
        require({k:v for k,v in a.items() if k!='directory'}=={k:v for k,v in b.items() if k!='directory'},'independent reproduction differs')
        actual={k:v for k,v in a.items() if k not in ('directory','source_proofs')}
        require(args.measure or actual==row['expected'],'selected literal artifact differs')
        report.update(expected_contract=actual if args.measure else row['expected'],source_proofs=a['source_proofs'],
                      actual=dict(source='main.c',native='native/x',program='x'))
        for name in ('main.c','native/x','x','header.sh','payload.lzma','source-proof.json'):
            target=out/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(out/'first'/name,target)
        (out/'x').chmod(0o700)
        # Stored native is a baseline artifact: never execute it directly because it self-unlinks.
        report.update(complete=True,reproducible=True);save()
    except BaseException as error:
        report['failure']=dict(type=type(error).__name__,message=str(error));save();raise
    finally:
        try:host.close()
        finally:signal.signal(signal.SIGCHLD,previous)
    print(json.dumps(dict(entry=args.entry,whole=report['expected_contract']['whole_bytes'],complete=True)))


if __name__=='__main__':main()
