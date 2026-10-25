#!/usr/bin/env python3
"""Compose the pinned TinyE capture-prior and minimal-UCI components once."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
DEFAULTS={
    "state":"/home/stemxstudio/rove4k-tiny-e-state-20261020-evidence/final2/state/build.json",
    "order":"/home/stemxstudio/rove4k-tiny-e-order-20261020/model-final/build.json",
    "uci":"/home/stemxstudio/rove4k-tiny-uci-portfolio-20261020/E/build.json"}
PINS={"state":"55e72d5c2ebf3644006d1aceb4c8c7be66082f62c994881798a0d55be3eb0b86",
      "order":"b78de0b178a75921354112a7ef60d171af5611473762f308f18238f1ff28de14",
      "uci":"df8af167e00fa85f4437ab22b5cac26a6a230f3976155b7ca38b6a1e820d5cd0"}

def sha(data):return hashlib.sha256(data).hexdigest()
def require(ok,message):
    if not ok:raise ValueError(message)
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module;spec.loader.exec_module(module);return module
def safe_relative(name):
    p=Path(name);require(not p.is_absolute() and '..' not in p.parts and '\\' not in name,'unsafe recipe path');return p

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,type=Path)
    for name,path in DEFAULTS.items():parser.add_argument('--'+name+'-build',type=Path,default=Path(path))
    args=parser.parse_args()
    require(sys.platform=='linux','Linux /proc toolchain required')
    require(args.out.is_absolute(),'new absolute external output required');out=args.out.resolve()
    require(not out.exists() and not any((p/'.git').exists() for p in (out,*out.parents)),'fresh output outside Git required')
    out.mkdir(parents=True);recipe=out/'recipe';recipe.mkdir()
    report={'complete':False,'family':'E','scope':'actual composition, not summed component deltas',
        'resources':{'workers':2,'startup_threads':3,'tt_bits':18},'input_sha256':{},'engines':[],
        'tools':{key:subprocess.check_output(command,text=True).splitlines()[0] for key,command in
            {'cc':['cc','--version'],'python3':['python3','--version']}.items()}}
    def save():(out/'build.json').write_text(json.dumps(report,indent=2)+'\n')
    def freeze(name,data,expected=None):
        require(expected is None or sha(data)==expected,'raw input hash changed: '+name)
        dest=recipe/safe_relative(name);require(not dest.exists(),'duplicate frozen input: '+name)
        dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);report['input_sha256'][name]=sha(data)
        return dest
    save()
    try:
        inputs=json.loads((HERE/'inputs.json').read_bytes())
        for name,identity in inputs.items():
            data=(ROOT/safe_relative(name)).read_bytes();require(len(data)==identity['bytes'],'input byte count changed: '+name)
            freeze(name,data,identity['sha256'])
        for name in ('build.py','generate.py','verify.py','proof.py','test_generate.py','inputs.json'):
            freeze(str((HERE/name).relative_to(ROOT)),(HERE/name).read_bytes())
        component={}
        for name in DEFAULTS:
            path=getattr(args,name+'_build').resolve(strict=True);data=path.read_bytes();freeze('components/'+name+'-build.json',data,PINS[name])
            component[name]=(path,json.loads(data))
        portfolio=load('e_compose_portfolio',recipe/'engines/experiments/tiny-uci-portfolio/build.py')
        adapter=load('e_compose_family',recipe/'engines/experiments/tiny-uci-portfolio/family_ce.py')
        uci=load('e_compose_uci',recipe/'engines/experiments/tiny-uci-portfolio/transform.py')
        order=load('e_compose_order',recipe/'engines/experiments/tiny-e-order/generate.py')
        composition=load('e_compose_generate',recipe/'engines/experiments/tiny-e-compose/generate.py')
        control,generate=adapter.prepare('E',{'E':str(component['state'][0])},recipe)
        report['input_sha256'].update(control['input_sha256'])
        ordered=component['order'][0].parent/'original/main.c';order_bytes=ordered.read_bytes()
        require(sha(order_bytes)==component['order'][1]['engines'][1]['source_sha256'],'ordered readable changed')
        freeze('components/order-readable.c',order_bytes)
        minimal_record=next(e for e in component['uci'][1]['engines'] if e['id']=='minimal')
        minimal_bytes=(component['uci'][0].parent/'minimal/combined.c').read_bytes()
        require(sha(minimal_bytes)==minimal_record['readable_sha256'],'minimal readable changed')
        freeze('components/minimal-readable.c',minimal_bytes)
        final,proof=composition.compose(control['readable'],order_bytes,minimal_bytes,order,uci)
        report['composition']=proof;package,pack_metadata=portfolio.packager(control);report['wrapper_recipe']=pack_metadata
        report['component_sources']={'state':sha(control['readable']),'order':sha(order_bytes),'minimal':sha(minimal_bytes)}
        expected={
            'order-control':{'source':component['order'][1]['engines'][2]['source_sha256'],
                'whole':component['order'][1]['selected']['sha256'],'native':component['order'][1]['selected']['restored_native_sha256']},
            'uci-control':{'source':minimal_record['source_sha256'],'whole':minimal_record['whole_sha256'],'native':minimal_record['native_sha256']}}
        order_dev=order_dev_native=None
        for label,readable in (('order-control',order_bytes),('uci-control',minimal_bytes),('minimal',final)):
            work=out/label;work.mkdir();(work/'combined.c').write_bytes(readable)
            source=generate(readable,work/'generate-first');repeat=generate(readable,work/'generate-second')
            require(source==repeat,'source generation did not reproduce');(work/'main.c').write_bytes(source)
            native=portfolio.compile_source(control['compiler_argv'],source,work/'native')
            require(native==portfolio.compile_source(control['compiler_argv'],repeat,work/'native-second'),'native compilation did not reproduce')
            packed,script=package(source);require(package(repeat)==(packed,script),'whole file did not reproduce')
            if label in expected:
                require({'source':sha(source),'whole':sha(packed),'native':sha(native)}==expected[label],'qualified component control did not reproduce')
            target=work/'wrapper/x';target.parent.mkdir();target.write_bytes(packed);target.chmod(0o755);(work/'bootstrap.py').write_bytes(script)
            dev=generate(readable,work/'generate-dev',dev=True);(work/'dev-source.c').write_bytes(dev)
            dev_native=portfolio.compile_source(control['dev_argv'],dev,work/'dev')
            if label=='order-control':order_dev,order_dev_native=dev,dev_native
            if label=='minimal':require(dev==order_dev and dev_native==order_dev_native,'composed DEV changed from ordered strong DEV')
            record={'id':label,'family':'E','profile':'shipping','workers':2,'startup_threads':3,'max_threads':3,'startup_timeout':60,
                'command':[str(target)],'readable':str(work/'combined.c'),'source':str(work/'main.c'),'native':str(work/'native/x'),
                'dev':str(work/'dev/x'),'dev_source':str(work/'dev-source.c'),
                'readable_sha256':sha(readable),'source_sha256':sha(source),'source_bytes':len(source),
                'native_sha256':sha(native),'native_bytes':len(native),'whole_sha256':sha(packed),'whole_bytes':len(packed),
                'dev_source_sha256':sha(dev),'dev_native_sha256':sha(dev_native),'expected_program_sha256':sha(packed),
                'compile':control['compiler_argv'],'dev_compile':control['dev_argv'],'source_reproduced':True,
                'native_reproduced':True,'whole_reproduced':True,'source_restored_exactly':True,'under_4096_bytes':len(packed)<=4096}
            report['engines'].append(record);save();print(json.dumps({'id':label,'source_bytes':len(source),'native_bytes':len(native),'whole_bytes':len(packed)}),flush=True)
        report['ordered_DEV_source_native_exactly_unchanged']=True
        report['complete']=True
    except Exception as error:report['failure']=repr(error);raise
    finally:save()

if __name__=='__main__':main()
