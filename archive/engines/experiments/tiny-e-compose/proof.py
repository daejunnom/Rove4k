#!/usr/bin/env python3
"""Bind historical ordered-core activity through exact composed source bodies."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

RECEIPT=Path('/home/stemxstudio/rove4k-tiny-e-order-20261020/freeze-receipt.json')
RECEIPT_SHA='ee0d1015fb2090a5fd52349dfa5a09518fa5d5adb99a69a96b4743459f286332'
POSITIVE_SHA='d8ed7f4c1086559daf8a17480736b4ab49168b86138b8fa1c3d775ccfe19d15a'
def sha(data):return hashlib.sha256(data).hexdigest()
def require(ok,message):
    if not ok:raise ValueError(message)
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    require(args.out.is_absolute(),'new absolute external output required');out=args.out.resolve()
    require(not out.exists() and not any((p/'.git').exists() for p in (out,*out.parents)),'fresh output outside Git required')
    out.mkdir(parents=True);frozen=out/'frozen';frozen.mkdir()
    report={'passed':False,'fresh_core_matrix_run':False,'scope':'exact unchanged ordered readable bodies; historical activity stays historical',
        'build_sha256':sha(args.build.read_bytes()),'input_sha256':{}}
    def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    def freeze(path,name,expected=None):
        data=Path(path).read_bytes();require(expected is None or sha(data)==expected,'historical input changed: '+str(path))
        target=frozen/name;require(not target.exists(),'duplicate frozen input');target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        report['input_sha256'][name]=sha(data);return data
    save()
    try:
        freeze(Path(__file__),'proof.py')
        build=json.loads(args.build.read_bytes());require(build['complete'],'incomplete producer');recipe=args.build.parent/'recipe'
        for name,digest in build['input_sha256'].items():require(sha((recipe/name).read_bytes())==digest,'producer input changed: '+name)
        uci=load('compose_proof_uci',recipe/'engines/experiments/tiny-uci-portfolio/transform.py')
        order=load('compose_proof_order',recipe/'engines/experiments/tiny-e-order/generate.py')
        generate=load('compose_proof_generate',recipe/'engines/experiments/tiny-e-compose/generate.py')
        state=(recipe/'family-E/original/main.c').read_bytes();ordered=(recipe/'components/order-readable.c').read_bytes();minimal=(recipe/'components/minimal-readable.c').read_bytes()
        expected,composition=generate.compose(state,ordered,minimal,order,uci)
        selected=next(e for e in build['engines'] if e['id']=='minimal');actual=freeze(selected['readable'],'composed-readable.c',selected['readable_sha256'])
        require(actual==expected and composition==build['composition'],'composition source/proof changed')
        protected=uci.protected_bytes(ordered);require(uci.protected_bytes(actual)==protected,'ordered core complement changed')
        report['same_ordered_core']={'bytes':len(protected),'sha256':sha(protected),'all_bytes_outside_go_main_identical':True}
        receipt=json.loads(freeze(RECEIPT,'order-freeze-receipt.json',RECEIPT_SHA));require(receipt['passed'],'historical freeze incomplete')
        history=receipt['forms']['model'];old_build_path=Path(history['manifest']);old_build=json.loads(freeze(old_build_path,'order-final-build.json',history['manifest_sha256']))
        old_readable=freeze(old_build_path.parent/'original/main.c','order-readable.c',old_build['engines'][1]['source_sha256']);require(old_readable==ordered,'historical ordered source differs')
        consumer_path=Path(history['consumer_report']);consumer=json.loads(freeze(consumer_path,'order-consumers.json',history['consumer_report_sha256']))
        require(consumer['passed'] and len(consumer['runs'])==6,'historical consumer proof incomplete')
        old_v3=consumer_path.parent.parent/'model-v3/build.json';v3=json.loads(freeze(old_v3,'order-v3-build.json',consumer['build_sha256']))
        for name,digest in v3['input_sha256'].items():freeze(old_v3.parent/'recipe'/name,'old-recipe/'+name,digest)
        for form in ('dev','original','compact'):
            old_source=old_v3.parent/form/'main.c';record=next(e for e in v3['engines'] if e['id']=='tiny-E-'+form)
            freeze(old_source,'old-'+form+'.c',record['source_sha256'])
            require(record['source_sha256']==old_build['engines'][('dev','original','compact').index(form)]['source_sha256'],'final historical source differs')
        for run in consumer['runs']:
            source_record=next(e for e in v3['engines'] if e['id']=='tiny-E-'+run['form'])
            require(run['source_sha256']==source_record['source_sha256'],'consumer source link differs')
            binary=consumer_path.parent/(run['form']+'-'+run['kind']);freeze(binary,'old-binaries/'+binary.name,run['program_sha256'])
            require(run['results']['observed_priorities']>0 and run['results']['observed_ep']>0 and run['results']['tt_context_abort'],'historical actual production-priority/context proof absent')
        positive_path=consumer_path.parent/'model/results.json';positive=json.loads(freeze(positive_path,'order-positive-search.json',POSITIVE_SHA))
        require(positive['passed'] and positive['program_sha256']==v3['engines'][0]['native_sha256'],'positive search/image link differs')
        stats=positive['actual_search'];require(stats['completed_depth']>=4 and stats['workers']==2 and stats['total_threads']==3,'historical completed fixed-worker activity missing')
        for key in ('leaf_calls','ordering_calls','pvs','qs','history_updates','continuation_updates','correction_updates','correction_uses'):
            require(stats[key]>0,'historical positive counter missing: '+key)
        require(positive['coefficients']==old_build['features']['model']['weights'] and len(positive['coefficients'])==21,'21 coefficient identity differs')
        # DEV identity is independently regenerated/compiled by the producer;
        # compare the actual files again, without equating old file compilation.
        order_record=next(e for e in build['engines'] if e['id']=='order-control')
        for key,digest_key in (('dev_source','dev_source_sha256'),('dev','dev_native_sha256')):
            a=Path(order_record[key]).read_bytes();b=Path(selected[key]).read_bytes()
            require(a==b and sha(a)==order_record[digest_key]==selected[digest_key],'composed ordered DEV changed')
        report['historical_positive_search']=stats;report['historical_consumer_runs']=len(consumer['runs'])
        report['reuse_limits']=['actual historical source/image activity, not new composed core executions',
            'halfmove/path fixture proves context-key separation, not a newly forced cutoff/miss',
            'fresh selected-file minimal UCI runtime is a separate report',
            'no strength, high-worker scaling or 4096-byte eligibility claim']
        report['ordered_DEV_source_stdin_native_exactly_equal']=True;report['passed']=True
    except Exception as error:report['failure']=repr(error);raise
    finally:save()
    print(json.dumps({'passed':True,'historical_consumer_runs':6,'same_ordered_core_bytes':len(protected)}))

if __name__=='__main__':main()
