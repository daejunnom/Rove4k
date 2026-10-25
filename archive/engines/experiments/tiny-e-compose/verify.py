#!/usr/bin/env python3
"""Fresh selected-whole-file minimal-UCI and strict ordered-DEV qualification."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

def sha(data):return hashlib.sha256(data).hexdigest()
def require(ok,message):
    if not ok:raise ValueError(message)
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module;spec.loader.exec_module(module);return module

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',required=True,type=Path);p.add_argument('--out',required=True,type=Path);args=p.parse_args()
    require(sys.platform=='linux' and args.out.is_absolute(),'Linux and new absolute external output required')
    out=args.out.resolve();require(not out.exists() and not any((x/'.git').exists() for x in (out,*out.parents)),'fresh output outside Git required')
    build=json.loads(args.build.read_bytes());require(build['complete'] and build['ordered_DEV_source_native_exactly_unchanged'],'incomplete producer')
    recipe=args.build.parent/'recipe'
    for name,digest in build['input_sha256'].items():require(sha((recipe/name).read_bytes())==digest,'frozen producer input changed: '+name)
    record=next(e for e in build['engines'] if e['id']=='minimal')
    require(record['workers']==2 and record['startup_threads']==3,'unknown worker resources')
    for key,digest_key in (('readable','readable_sha256'),('source','source_sha256'),('native','native_sha256'),('dev','dev_native_sha256')):
        require(sha(Path(record[key]).read_bytes())==record[digest_key],'actual artifact changed: '+key)
    require(sha(Path(record['command'][0]).read_bytes())==record['whole_sha256'],'whole artifact changed')
    out.mkdir(parents=True);frozen=out/'recipe';frozen.mkdir()
    portfolio=load('compose_policy_inputs',recipe/'engines/experiments/tiny-uci-portfolio/verify.py')
    report={'complete':False,'scope':'one selected composed whole file, policy and active EOF plus strict DEV',
        'build_sha256':sha(args.build.read_bytes()),'helpers':{},'shipping_runs':[]}
    def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        for name,(source,expected) in portfolio.INPUTS.items():
            data=source.read_bytes();require(sha(data)==expected,'qualified policy helper changed: '+name)
            target=frozen/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);report['helpers'][name]=expected
        (frozen/'verify.py').write_bytes(Path(__file__).read_bytes())
        uci=load('compose_runtime_transform',recipe/'engines/experiments/tiny-uci-portfolio/transform.py')
        a=(frozen/'A-minimal-readable.c').read_bytes();actual=Path(record['readable']).read_bytes()
        ab,ae=uci.region(a.decode(),'static void go(char *s){');cb,ce=uci.region(actual.decode(),'static void go(char *s){')
        require(a[ab:ae]==actual[cb:ce],'composed go differs from qualified arithmetic body')
        report['qualified_A_go_sha256']=sha(actual[cb:ce]);report['A_reuse_scope']='same go arithmetic only; no new whole-TT snapshot proof'
        policy=load('compose_frozen_policy',frozen/'policy-check.py')
        raw=load('compose_frozen_raw',frozen/'engines/experiments/tiny-protocol/edges.py');oracle=sys.modules['chess_oracle']
        report['oracle_self_check']=oracle.self_check()
        for eof in (False,True):
            report['shipping_runs'].append(policy.run_shipping(record,'wrapper',out,raw,oracle,eof_only=eof));save()
        report['DEV']=policy.run_dev(record,out,raw,oracle);report['complete']=True
    except Exception as error:report['failure']=repr(error);raise
    finally:save()
    print(json.dumps({'complete':True,'shipping_sessions':2,'DEV':True}))

if __name__=='__main__':main()
