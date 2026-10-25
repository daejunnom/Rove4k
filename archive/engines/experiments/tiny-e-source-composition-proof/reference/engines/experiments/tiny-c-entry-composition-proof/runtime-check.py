#!/usr/bin/env python3
"""Admit and run exactly two pinned C5687 wrappers after functional gates.

The existing C selected verifier is copied unchanged. Its new recipe is a
shipping-only QA admission, with no old DEV identity assigned to changed C.
build.json is the genuine cost receipt verbatim, not a new build-success
manifest. x resolves to the cost candidate-1/x mode0755, never selected/x0644.
No additional cost/native build, preprocessing or codec trial runs here.
Each wrapper uses its unchanged restoration compiler. No other candidate,
game or benchmark runs.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
PIN_SHA256='135cc4282cf31217cb1845e86b97047e2f54f92986d74ae1a7fb57e16fb462ad'
def sha(data):return hashlib.sha256(data).hexdigest()
def identity(data):return {'bytes':len(data),'sha256':sha(data)}
def require(value,message):
    if not value:raise ValueError(message)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args();out=args.out.resolve()
    require(args.out.is_absolute() and not out.exists(),'new absolute output required')
    require(not any((p/'.git').exists() for p in (out,*out.parents)),'outside Git required')
    raw_pins=(HERE/'runtime-pins.json').read_bytes()
    require(sha(raw_pins)==PIN_SHA256,'literal runtime admission changed')
    pins=json.loads(raw_pins);own=Path(__file__).read_bytes();out.mkdir(parents=True)
    report={'complete':False,'scope':__doc__,'planned_wrappers':2,'observed_wrappers':0,
        'other_wrapper_launches':0,'runtime_pins_sha256':PIN_SHA256,'adapter_sha256':sha(own),
        'candidate_DEV_identity_admitted':False,'owned_subprocess':None,'cancellation_causality':'unproven'}
    def save():(out/'runtime.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        def bind():
            values={}
            require(set(pins['functional_receipts'])=={'query','phase','epoch'},'exact three functional gates required')
            for name,row in pins['functional_receipts'].items():
                data=Path(row['path']).read_bytes()
                require(sha(data)==row['sha256'],'functional receipt changed: '+name)
                values['functional:'+name]=identity(data);r=json.loads(data)
                if name=='query':
                    require(r['passed'] and r['fixture_executions']==4 and len(r['runs'])==4 and all(x['passed'] for x in r['runs']),'query/SAN gate incomplete')
                elif name=='phase':
                    require(r['complete'] and r['passed_count']==5 and len(r['cases'])==5 and all(x['passed'] for x in r['cases']),'phase gate incomplete')
                elif name=='epoch':
                    require(r['complete'] and r['diagnostic_executions']==1 and r['assertions']['actual_unique_results']==4,'epoch gate incomplete')
            cost=Path(pins['cost_directory']);data=(cost/'cost.json').read_bytes()
            require(sha(data)==pins['cost_sha256'],'successful cost receipt changed')
            values['cost']=identity(data);r=json.loads(data);c=r['candidate']
            require(r['complete'] and r['engine_runs']==r['semantic_tests']==0 and c['independent_attempts']==2,'cost scope changed')
            require(c['source_transform']['candidate_sha256']==pins['readable_sha256'] and c['source_transform']['core_prefix_byte_identical'],'candidate source binding changed')
            require(all(c[k]==v for k,v in pins['expected'].items() if k!='readable_sha256'),'literal candidate shipping identity differs')
            for name,pin in pins['ordinary_inputs'].items():
                data=(HERE/name).read_bytes().replace(b'\r\n',b'\n')
                require(b'\r' not in data and identity(data)==pin,'ordinary verifier/helper changed: '+name)
                values['ordinary:'+name]=identity(data)
            for attempt in (1,2):
                folder=cost/('candidate-'+str(attempt))
                for name,key in (('main.c','source'),('after/x','native'),('x','whole'),('bootstrap.py','bootstrap')):
                    data=(folder/name).read_bytes()
                    require(sha(data)==pins['expected'][key+'_sha256'],'actual attempt artifact changed')
                    values['artifact:'+str(attempt)+'/'+name]=identity(data)
                require((folder/'x').stat().st_mode&0o111,'actual attempt is not executable')
                require((folder/'before/x').read_bytes()==(folder/'after/x').read_bytes(),'full-native spelling boundary changed')
            require((HERE/'runtime-pins.json').read_bytes()==raw_pins and Path(__file__).read_bytes()==own,'adapter source/pins changed')
            return values
        observed=bind();report['prelaunch_bindings']=observed;save()
        helper=(HERE/'runtime_ownership.py').read_bytes()
        function=helper[helper.index(b'def run_owned_verifier('):]
        require(sha(function)=='b9d830bfbe3fae4dec71826063f8e273641e807e75e0a21c5ded33f4838bc644','reviewed ownership function differs')
        spec=importlib.util.spec_from_file_location('C_owned_verifier',HERE/'runtime_ownership.py')
        owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
        cost=Path(pins['cost_directory']);mirror=out/'execution-mirror';entry=mirror/'engines/compact/tiny-entry-c'
        entry.mkdir(parents=True)
        for source,target in pins['mirror_files'].items():
            data=(HERE/source).read_bytes().replace(b'\r\n',b'\n')
            dest=mirror/target;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        verifier=entry/'verify.py'
        require(sha(verifier.read_bytes())=='930baa1794b486fca9dce8829fa808bb2cae08da80d1d8c3ccb5609d30d41310','selected C verifier changed')
        recipe={'expected':pins['expected'],'qualified_receipt':{
            'scope':'C composition functional receipts and unchanged C AVX2/search prefix; no old DEV equality or old parser/startup execution inherited',
            'cost_sha256':pins['cost_sha256'],'functional_receipts':pins['functional_receipts'],
            'candidate_DEV_identity_admitted':False}}
        (entry/'recipe.json').write_text(json.dumps(recipe,indent=2)+'\n')
        selected=out/'admitted';selected.mkdir();(selected/'native').mkdir()
        for name,target in (('x',cost/'candidate-1/x'),('native/x',cost/'candidate-1/after/x'),('main.c',cost/'candidate-1/main.c')):
            (selected/name).symlink_to(target)
        cost_raw=(cost/'cost.json').read_bytes();(selected/'build.json').write_bytes(cost_raw)
        report.update(actual_executable_target=str((selected/'x').resolve()),selected_x0644_used=False,
            build_manifest='genuine cost receipt byte-copy; explicit QA-only artifact admission',
            verifier_sha256=sha(verifier.read_bytes()),admitted_recipe_sha256=sha((entry/'recipe.json').read_bytes()),
            ownership_function_sha256=sha(function))
        before_mirror={str(p.relative_to(mirror)):identity(p.read_bytes()) for p in mirror.rglob('*') if p.is_file()}
        resource.setrlimit(resource.RLIMIT_CORE,(0,0));save()
        command=[sys.executable,'-I','-B',str(verifier),'--build',str(selected),'--out',str(out/'fresh')]
        status,pid=owner.run_owned_verifier(command,out,report,save)
        require(status==0,'unchanged selected C verifier failed')
        fresh=json.loads((out/'fresh/runtime.json').read_text())
        require(fresh['complete'] and fresh['whole_sha256']==pins['expected']['whole_sha256'] and fresh['native_sha256']==pins['expected']['native_sha256'],'actual runtime identity differs')
        require(len(fresh['fresh_sessions'])==2 and [r['termination'] for r in fresh['fresh_sessions']]==['quit','EOF'],'exact two-session inventory differs')
        for row in fresh['fresh_sessions']:
            require(row['returncode']==0 and row['process_absent'] and row['readers_finished'] and row['exactly_one_closing_bestmove'] and row['stderr']==[],'physical settlement failed')
            image=row['image']
            require(image['image_sha256']==pins['expected']['native_sha256'] and len(image['startup_tids'])==3 and image['file_descriptors']==[0,1,2] and not any(image['children_by_tid'].values()) and image['private_path_absent'],'actual restored image/startup differs')
            require(row['activity']['active_before_signal'] and row['activity']['cancellation_causality']=='unproven','active closing boundary differs')
        require(bind()==observed,'source/function/artifact bindings changed during runtime')
        require(before_mirror=={str(p.relative_to(mirror)):identity(p.read_bytes()) for p in mirror.rglob('*') if p.is_file()},'execution mirror changed')
        require((selected/'build.json').read_bytes()==cost_raw and (selected/'x').resolve()==cost/'candidate-1/x','actual artifact link/admission changed')
        require(not (Path('/proc')/str(pid)).exists(),'owned verifier remains')
        report.update(complete=True,observed_wrappers=2,GO_epochs=8,settled=True,owned_live_handles=0,
            original_verifier_runtime_sha256=sha((out/'fresh/runtime.json').read_bytes()),bindings_rechecked_after=True,
            actual_process_scope='unchanged verifier main/readers and observed compiler children; cancellation causality unproven')
        save();print(json.dumps({'complete':True,'out':str(out),'wrappers':2,'runtime_sha256':sha((out/'runtime.json').read_bytes())}),flush=True)
    except BaseException as error:
        report['error']=repr(error)
        try:save()
        except BaseException:pass
        raise

if __name__=='__main__':main()
