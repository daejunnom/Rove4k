#!/usr/bin/env python3
"""Two exact first-cost E5647 wrapper sessions via unchanged E verifier.

This is explicit QA admission of real cost bytes, with a new0755 byte copy.
The original0644 cost artifacts and original cost receipt stay unchanged.
No engine/DEV/native/codec build is performed by this adapter. Each wrapper
itself uses the original restoration compiler. DEV package identity is absent.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import stat
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
INPUTS='6c087b741124bc9ac5c311de1c19f6ad17ce341af10d13c5b1a5222251aa38f5'
COST='6857c539c7d881a7e6a897b27f694ac0d2e76634ae64fdda888209b326b35a28'
EXPECTED={'source_bytes':12339,'source_sha256':'549dfdf4f1f876e9a71b3df5ef07afb136d076257b057ca0df9788d4f360a938',
 'native_bytes':26376,'native_sha256':'557abd8381e593e247e3f90d59665b2ae982e81a840494dca43301cbebd37aa1',
 'whole_bytes':5647,'whole_sha256':'4ef55b410013832b8501ae2fa94dd06ffd381a540b4415b57d30f6c6d5decb69',
 'bootstrap_sha256':'512d4bcdba09e9150b55b6dc0dda703fc3715388ce74e3bd558d184fdc2788f6'}
READABLE='c5f005b107f5d3fa93a4043fece78de848e248e67c4e58831a688efae8f2941d'

def sha(data):return hashlib.sha256(data).hexdigest()
def identity(data):return {'bytes':len(data),'sha256':sha(data)}
def require(v,m):
    if not v:raise ValueError(m)
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args();out=args.out.resolve()
    require(args.out.is_absolute()and not out.exists()and not any((p/'.git').exists()for p in (out,*out.parents)),'new absolute output outside Git required')
    raw_inputs=(HERE/'inputs.json').read_bytes();require(sha(raw_inputs)==INPUTS,'proof input manifest differs')
    manifest=json.loads(raw_inputs);pins=json.loads((HERE/'runtime-pins.json').read_bytes())
    require(pins['cost_sha256']==COST and pins['expected']==EXPECTED,'runtime artifact admission differs')
    out.mkdir(parents=True);own=Path(__file__).read_bytes()
    report={'complete':False,'scope':__doc__,'actual_first_cost_reuse':True,'candidate_DEV_identity_admitted':False,
        'observed_wrappers':0,'planned_wrappers':2,'other_wrapper_launches':0,'owned_subprocess':None,
        'settled':False,'wrapper_settlement':'unproven until two physical sessions checked',
        'runtime_pins_sha256':sha((HERE/'runtime-pins.json').read_bytes()),'adapter_sha256':sha(own),
        'cancellation_causality':'unproven'}
    def save():(out/'runtime.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        def bind():
            values={}
            for prefix,key in (('control','control_files'),('reference','reference_files')):
                for name,pin in manifest[key].items():
                    data=(HERE/prefix/name).read_bytes();require(identity(data)==pin,'ordinary input changed: '+prefix+'/'+name)
                    values[prefix+'/'+name]=identity(data)
            require(sha((HERE/'control/candidate.c').read_bytes())==READABLE,'candidate readable differs')
            require(set(pins['functional_receipts'])=={'query','phase','epoch'},'three explicit risk gates required')
            for name,row in pins['functional_receipts'].items():
                data=Path(row['path']).read_bytes();require(sha(data)==row['sha256'],'functional receipt changed: '+name)
                r=json.loads(data);require(r.get('complete',True)and r.get('passed',True),'functional receipt incomplete: '+name)
                require('complete'in r or 'passed'in r,'functional receipt has no positive result: '+name)
                values['functional:'+name]=identity(data)
            cost=Path(pins['cost_directory']);raw=(cost/'cost.json').read_bytes();require(sha(raw)==COST,'raw first-cost receipt changed')
            r=json.loads(raw);require(r['complete']and r['mode']=='candidate'and len(r['attempts'])==2,'actual first-cost receipt incomplete')
            require(r['candidate_engine_executions']==r['DEV_qualification_executions']==0,'first-cost scope changed')
            values['cost']=identity(raw)
            for attempt in (1,2):
                folder=cost/('attempt-'+str(attempt))
                for name,key in (('main.c','source'),('native/x','native'),('x','whole'),('bootstrap.py','bootstrap')):
                    data=(folder/name).read_bytes();require(sha(data)==EXPECTED[key+'_sha256'],'physical cost artifact differs')
                    values['artifact:'+str(attempt)+'/'+name]=identity(data)
                require(stat.S_IMODE((folder/'x').stat().st_mode)==0o644,'original cost wrapper mode changed')
            require((HERE/'inputs.json').read_bytes()==raw_inputs and Path(__file__).read_bytes()==own,'adapter or manifest changed')
            require(sha((HERE/'runtime-pins.json').read_bytes())==report['runtime_pins_sha256'],'runtime pins changed')
            return values
        before=bind();report['prelaunch_bindings']=before;save()
        ref=HERE/'reference';mirror=out/'execution-mirror';entry=mirror/'engines/compact/tiny-entry-e';entry.mkdir(parents=True)
        for relative in ('engines/compact/tiny-entry-e/verify.py','engines/tests/verify.py','engines/tests/chess_oracle.py'):
            data=(ref/relative).read_bytes();target=mirror/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        verifier=entry/'verify.py';report['unchanged_verifier_sha256']=sha(verifier.read_bytes())
        recipe={'expected':EXPECTED,'qualified_receipt':{'scope':'E composition risk diagnostics plus exact unchanged18042-byte model/Board/search prefix; no old DEV identity or parser/startup execution inherited',
            'cost_sha256':COST,'functional_receipts':pins['functional_receipts'],'candidate_DEV_identity_admitted':False}}
        (entry/'recipe.json').write_text(json.dumps(recipe,indent=2)+'\n')
        cost=Path(pins['cost_directory']);qa=out/'admitted';qa.mkdir();(qa/'native').mkdir()
        for name,relative in (('x','x'),('main.c','main.c'),('native/x','native/x')):
            (qa/name).write_bytes((cost/'attempt-1'/relative).read_bytes())
        (qa/'x').chmod(0o755);cost_raw=(cost/'cost.json').read_bytes();(qa/'build.json').write_bytes(cost_raw)
        require(sha((qa/'x').read_bytes())==EXPECTED['whole_sha256']and stat.S_IMODE((qa/'x').stat().st_mode)==0o755,'new QA copy binding differs')
        report.update(actual_executable=str(qa/'x'),original_wrapper=str(cost/'attempt-1/x'),
            original_wrapper_mode='0644',QA_wrapper_mode='0755',QA_wrapper_bytes_equal_original=True,
            build_manifest='genuine cost.json byte-copy; explicit QA-only admission, not a normal maintained build',
            admitted_recipe_sha256=sha((entry/'recipe.json').read_bytes()))
        mirror_before={str(p.relative_to(mirror)):identity(p.read_bytes())for p in mirror.rglob('*')if p.is_file()}
        ownerpath=ref/'engines/experiments/tiny-c-entry-composition-proof/runtime_ownership.py'
        owner=module('E_owned_verifier',ownerpath)
        report['unchanged_C_ownership_helper_sha256']=sha(ownerpath.read_bytes());save()
        resource.setrlimit(resource.RLIMIT_CORE,(0,0))
        command=[sys.executable,'-I','-B',str(verifier),'--build',str(qa),'--out',str(out/'fresh')]
        status,pid=owner.run_owned_verifier(command,out,report,save)
        require(status==0,'unchanged E verifier failed')
        fresh=json.loads((out/'fresh/runtime.json').read_bytes())
        require(fresh['complete']and fresh['whole_sha256']==EXPECTED['whole_sha256']and fresh['native_sha256']==EXPECTED['native_sha256'],'actual shipping runtime identity differs')
        require(len(fresh['fresh_sessions'])==2 and [r['termination']for r in fresh['fresh_sessions']]==['quit','EOF'],'two-session inventory differs')
        for row in fresh['fresh_sessions']:
            require(row['returncode']==0 and row['process_absent']and row['readers_finished']and row['exactly_one_closing_bestmove']and row['stderr']==[],'physical session settlement failed')
            image=row['image']
            require(image['image_sha256']==EXPECTED['native_sha256']and len(image['startup_tids'])==3 and image['file_descriptors']==[0,1,2]and not any(image['children_by_tid'].values())and image['private_path_absent'],'actual restored image/startup differs')
            require(row['activity']['active_before_signal']and row['activity']['cancellation_causality']=='unproven','active closing scope differs')
        require(bind()==before,'cost or ordinary source changed during actual wrapper sessions')
        require((qa/'build.json').read_bytes()==cost_raw and (qa/'x').read_bytes()==(cost/'attempt-1/x').read_bytes(),'QA byte-copy admission changed')
        require(stat.S_IMODE((qa/'x').stat().st_mode)==0o755,'QA executable mode changed')
        for name,key in (('x','whole'),('native/x','native'),('main.c','source')):
            require(sha((qa/name).read_bytes())==EXPECTED[key+'_sha256'],'QA admitted artifact changed')
        require(mirror_before=={str(p.relative_to(mirror)):identity(p.read_bytes())for p in mirror.rglob('*')if p.is_file()},'execution mirror changed')
        require(not (Path('/proc')/str(pid)).exists(),'owned verifier remains')
        report.update(complete=True,observed_wrappers=2,GO_epochs=8,settled=True,wrapper_settlement='two physical sessions checked',owned_live_handles=0,
            original_verifier_runtime_sha256=sha((out/'fresh/runtime.json').read_bytes()),bindings_rechecked_after=True)
        save();print(json.dumps({'complete':True,'out':str(out),'wrappers':2,'runtime_sha256':sha((out/'runtime.json').read_bytes())}),flush=True)
    except BaseException as error:
        report['error']=repr(error);report['complete']=False
        try:save()
        except BaseException:pass
        raise

if __name__=='__main__':main()
