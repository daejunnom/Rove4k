#!/usr/bin/env python3
"""Focused std diagnostics for one pinned tiny_shipping candidate.

One tiny_dev unit image runs only three original exact tests. One separate std
image compares old default search with candidate tiny_shipping search. No raw
OS runtime, production ELF, launcher, codec, matrix or benchmark is executed.
"""

if __name__ == "__main__":
    raise SystemExit("Rove4k Rust engine paths are retired; use C A-F")

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
RUSTC='/home/stemxstudio/.cargo/bin/rustc'
MANIFEST_SHA='be5205eb39100b842c966f8458a5576e2c9f539c71c8c4aef8ef8be868f9b63a'
OLD_SEARCH_SHA='da2583806efea022b1b3b1337557b896a373a561f11d665b1ca747c29e3aed81'
NEW_SEARCH_SHA='a6c88062c503038a9f555ae0c1cec489743adc8ba34f7320354586862530b299'
VERIFY_SEARCH_SHA='f60619bbdadf4f2e1b50c6eb3327e1d658fbfb290a28b3b9c4bfc6d6099f7250'
TESTS_SHA='f2588bedcd61403ad1e014770fec44d62c03a429ae98daed853700b9540ba027'
DRIVER_SHA='9921fc2f3a3e69bff17b603f6ec94479b8e3c49472a3a332fc212e824e44bbf0'
UNIT_DRIVER_SHA='3faa68db851f9ba6210e68fc3c90d1aec51cfb74d16d51ffa049556ff92bb0fe'
FIXTURES={
    'finite-hook.rs':'df18006e190d519e9cae5e842e476de589dbe21747aa8c11c1094498f42e3825',
    'default-budget.rs':'b88d77b249867f0e854f145e682dd39638c4fa550e49c49b69965b5e4c9a0c32',
    'paired-driver.rs':'e6c2b1e02e87cfe80378f675537db032ae2df5c7f6ac03200d42151932464ad3',
}
TESTS=(
    'tt_context_includes_ordered_history_clock_and_frozen_epoch',
    'node_abort_does_not_publish_an_unfinished_root_or_replace_last_completion',
    'actual_search_updates_history_continuation_and_deferred_correction',
)
COMBO_GUARD=b'#[cfg(all(tiny_shipping,tiny_dev))]compile_error!("tiny_shipping and tiny_dev are separate build classes");'

def sha(data):return hashlib.sha256(data).hexdigest()
def need(value,message):
    if not value:raise AssertionError(message)
def lf(path):
    data=path.read_bytes();need(b'\r' not in data,'raw LF source required: '+str(path));return data
def literal_driver(source):
    need(sha(source)==VERIFY_SEARCH_SHA,'original verify_search source changed')
    tree=ast.parse(source.decode('utf-8'))
    values=[node.value for node in tree.body if isinstance(node,ast.Assign) and
        any(isinstance(target,ast.Name) and target.id=='DRIVER' for target in node.targets)]
    need(len(values)==1 and isinstance(values[0],ast.Constant) and isinstance(values[0].value,str),'one literal original DRIVER required')
    driver=ast.literal_eval(values[0]).encode('utf-8')
    need(len(driver)==1696 and sha(driver)==DRIVER_SHA,'original DRIVER literal differs')
    marker=b'\nfn main(){'
    need(driver.count(marker)==1 and driver.index(marker)==1380,'original DRIVER main boundary differs')
    need(sha(driver[1380:])=='5840dc593cc70401c81150e0f6caf45547884f36e860437cc2f30f09e3c06053','original main suffix differs')
    unit=driver[:1380]+b'\nfn main(){}\n'
    need(sha(unit)==UNIT_DRIVER_SHA,'unit-only main replacement differs')
    return driver,unit

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve()
    need(sys.platform=='linux' and args.out.is_absolute() and not out.exists() and
         not any((parent/'.git').exists() for parent in (out,*out.parents)),
         'new absolute Linux output outside Git required')
    out.mkdir(parents=True);inputs=out/'inputs';inputs.mkdir()
    report={'passed':False,'scope':'three exact tiny_dev units plus one old-default/new-shipping std diagnostic',
        'source_inputs':{},'commands':[],'selected_unit_runs':[],
        'raw_OS_runtime_executions':0,'production_ELF_executions':0,'launcher_executions':0,
        'codec_calls':0,'matrix_executions':0,'benchmarks':0,'std_fixture_attempts':0,'std_fixture_executions':0,
        'cfg_combo_rejection':'source compile_error guard only; no additional compile',
        'actual_clock_and_worker_pool_qualification':False,
        'process_scope':'subprocess.run waits direct child; descendant/group absence is not observed here'}
    def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    def run(command,directory,label,timeout=90):
        row={'label':label,'command':[str(part) for part in command],'returncode':None,
             'direct_child_terminal':False,'settlement':'not observed'}
        report['commands'].append(row);save()
        stdout=stderr=b''
        try:
            result=subprocess.run(row['command'],cwd=directory,env=environment,
                capture_output=True,timeout=timeout)
            stdout,stderr=result.stdout,result.stderr
            row.update(returncode=result.returncode,direct_child_terminal=True,
                       settlement='direct child returned; descendants not observed')
            need(result.returncode==0,'command failed: '+label)
            return result
        except BaseException as error:
            for field in ('stdout','stderr'):
                partial=getattr(error,field,None)
                if isinstance(partial,bytes):
                    if field=='stdout':stdout=partial
                    else:stderr=partial
            row['error']={'type':type(error).__name__,'message':str(error)}
            if isinstance(error,subprocess.TimeoutExpired):
                row['settlement']='unknown after timeout; subprocess.run cleans its direct child only'
            raise
        finally:
            (directory/(label+'.stdout')).write_bytes(stdout)
            (directory/(label+'.stderr')).write_bytes(stderr)
            row.update(stdout_bytes=len(stdout),stdout_sha256=sha(stdout),stderr_bytes=len(stderr),stderr_sha256=sha(stderr))
            save()
    environment={**os.environ,'ROVE_HQ':'1','LC_ALL':'C','TZ':'UTC','SOURCE_DATE_EPOCH':'0'}
    save()
    try:
        manifest=lf(HERE/'source-pins.json');need(sha(manifest)==MANIFEST_SHA,'literal source31 manifest changed')
        pins=json.loads(manifest)
        need(len(pins)==31 and all(sum(name.startswith(prefix+'/') for name in pins)==count
            for prefix,count in (('control',17),('candidate',7),('packaging',4),('reference',3))),
            'closed ordinary source31 shape changed')
        frozen={}
        for name,pin in pins.items():
            data=lf(HERE/name);need(sha(data)==pin,'frozen source differs: '+name)
            destination=inputs/name;destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(data)
            frozen[name]=data;report['source_inputs'][name]={'bytes':len(data),'sha256':sha(data)}
        for name,pin in FIXTURES.items():
            data=lf(HERE/name);need(sha(data)==pin,'focused fixture differs: '+name)
            (inputs/name).write_bytes(data);frozen[name]=data
            report['source_inputs'][name]={'bytes':len(data),'sha256':sha(data)}
        for name in ('verify.py','source-pins.json'):
            data=lf(HERE/name);(inputs/name).write_bytes(data);frozen[name]=data
            report['source_inputs'][name]={'bytes':len(data),'sha256':sha(data)}
        old=frozen['control/search.rs'];new=frozen['candidate/search.rs'];tests=frozen['control/tests/search.rs']
        need(sha(old)==OLD_SEARCH_SHA and sha(new)==NEW_SEARCH_SHA and sha(tests)==TESTS_SHA,'literal actual search/test identities differ')
        need(new.count(COMBO_GUARD)==1,'explicit tiny_shipping/tiny_dev compile_error guard absent')
        for name in ('main.rs','board.rs','os.rs','link.ld'):
            need(frozen['candidate/'+name]==frozen['control/'+name],'unchanged shipping dependency differs: '+name)
        driver,unit_driver=literal_driver(frozen['control/verify_search.py'])
        (inputs/'original-DRIVER.rs').write_bytes(driver)
        (inputs/'unit-DRIVER.rs').write_bytes(unit_driver)
        report['unit_driver_reuse']={'original_bytes':len(driver),'original_sha256':sha(driver),
            'retained_prefix_bytes':1380,'unit_bytes':len(unit_driver),'unit_sha256':sha(unit_driver),
            'transformation':'only final diagnostic main suffix replaced with empty main',
            'original_tests_sha256':sha(tests),'full_original_test_count':tests.count(b'#[test]')}
        version=run([RUSTC,'--version','--verbose'],out,'rustc-version',15)
        report['compiler_version']=version.stdout.decode('utf-8')
        need(report['compiler_version'].splitlines()[0].split()[1]=='1.97.0','fixed rustc 1.97.0 required')
        common=[RUSTC,'--edition=2024','-C','opt-level=z','-C','lto=fat','-C','codegen-units=1',
            '-C','force-unwind-tables=yes','--check-cfg','cfg(tiny_dev)',
            '--check-cfg','cfg(tiny_shipping)','--check-cfg','cfg(test)']
        unit=out/'selected-units';unit.mkdir();(unit/'tests').mkdir()
        (unit/'board.rs').write_bytes(frozen['candidate/board.rs'])
        (unit/'tests/search.rs').write_bytes(tests)
        appended=new+b'\n#[allow(dead_code)]pub mod qualification{include!("tests/search.rs");}\n'
        (unit/'search.rs').write_bytes(appended);(unit/'main.rs').write_bytes(unit_driver)
        need((unit/'search.rs').read_bytes()[:len(new)]==new,'candidate unit source prefix changed')
        binary=unit/'unit-tests'
        run([*common,'--crate-name','rove4k_d_search_contract','--test','--cfg','tiny_dev','main.rs','-o',str(binary)],unit,'unit-compile',120)
        filtered=tests.count(b'#[test]')-1
        for index,name in enumerate(TESTS):
            qualified='search::qualification::'+name
            report['std_fixture_attempts']+=1;save()
            result=run([str(binary),'--exact',qualified,'--test-threads=1','--nocapture'],unit,'unit-'+str(index+1),45)
            report['std_fixture_executions']+=1
            text=result.stdout.decode('utf-8')
            need(not result.stderr and 'running 1 test' in text and
                ('test '+qualified+' ... ok') in text,'exact selected unit did not report its one passing test')
            summary=re.search(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored; (\d+) measured; (\d+) filtered out;',text)
            need(summary is not None and tuple(map(int,summary.groups()))==(1,0,0,0,filtered),'zero/extra/ignored test execution is not admitted')
            report['selected_unit_runs'].append({'test':qualified,'passed':True,'stdout_sha256':sha(result.stdout),
                'selected_count':1,'filtered_count':filtered});save()
        report['unit_image']={'cfg':['tiny_dev'],'tiny_shipping':False,'hq':True,
            'binary_sha256':sha(binary.read_bytes()),'appended_search_sha256':sha(appended),
            'exact_search_prefix_sha256':sha(new),'full_original_fixture_sha256':sha(tests)}
        pair=out/'paired';pair.mkdir()
        (pair/'board.rs').write_bytes(frozen['candidate/board.rs'])
        for name in FIXTURES:(pair/name).write_bytes(frozen[name])
        old_appended=old+b'\n#[allow(dead_code)]pub mod finite_probe{include!("finite-hook.rs");include!("default-budget.rs");}\n'
        new_appended=new+b'\n#[allow(dead_code)]pub mod finite_probe{include!("finite-hook.rs");}\n'
        (pair/'old_search.rs').write_bytes(old_appended);(pair/'new_search.rs').write_bytes(new_appended)
        need((pair/'old_search.rs').read_bytes()[:len(old)]==old and
             (pair/'new_search.rs').read_bytes()[:len(new)]==new,'paired production source prefix changed')
        paired=pair/'paired-check'
        run([*common,'--crate-name','rove4k_d_finite_pair','--cfg','tiny_shipping','paired-driver.rs','-o',str(paired)],pair,'pair-compile',120)
        report['std_fixture_attempts']+=1;save()
        result=run([str(paired)],pair,'pair-run',30);report['std_fixture_executions']+=1
        need(not result.stderr,'paired std diagnostic wrote stderr')
        actual=json.loads(result.stdout)
        required={'passed':True,'hq':True,'fixed_depth':2,'completed_depth':2,
            'old_new_complete_result_equal':True,'correction_equal':True,'frozen_preserved':True,
            'default_budget_accepted':2,'default_budget_local':2,'default_budget_global':2,'default_budget_stopped':True,
            'shipping_budget_accepted':3,'shipping_budget_local':3,'shipping_budget_stopped':False,
            'pre_stopped_local':0,'pre_stopped_clock_reads':0,'pre_stopped_stop':True,
            'deadline_local':256,'deadline_reads_before_boundary':1,'deadline_reads_after_boundary':2,'deadline_stop':True}
        need(all(type(actual.get(key)) is type(value) and actual[key]==value for key,value in required.items()),'paired bounded contract differs')
        need(type(actual.get('result_nodes')) is int and actual['result_nodes']>0 and actual['result_nodes']==actual.get('worker_nodes'),'completed/local node witness differs')
        (pair/'fixture.json').write_bytes(result.stdout)
        report['paired_image']={'cfg':['tiny_shipping'],'tiny_dev':False,
            'old_module':'unmodified default source; it has no tiny_shipping branch',
            'new_module':'candidate explicit tiny_shipping source','diagnostic_clock':'controlled std fixture clock; not raw OS clock',
            'binary_sha256':sha(paired.read_bytes()),'old_prefix_sha256':sha(old),'new_prefix_sha256':sha(new),
            'old_appended_sha256':sha(old_appended),'new_appended_sha256':sha(new_appended),
            'fixture_sha256':sha(result.stdout),'actual':actual}
        need(len(report['selected_unit_runs'])==3 and report['std_fixture_attempts']==4 and report['std_fixture_executions']==4 and len(report['commands'])==7,
             'focused command/image count differs')
        need(all(row['returncode']==0 and row['direct_child_terminal'] for row in report['commands']),'direct child command incomplete')
        need(all(lf(HERE/name)==data for name,data in frozen.items()),'owned source changed during diagnostics')
        report.update(passed=True,unit_images=1,paired_images=1,extra_cfg_combo_compiles=0)
    except BaseException as error:
        report['passed']=False;report['error']={'type':type(error).__name__,'message':str(error)};raise
    finally:save()
    print(json.dumps({'passed':True,'out':str(out),'selected_units':3,'std_fixture_attempts':4,'std_fixture_executions':4,
        'raw_OS_runtime_executions':0,'results_sha256':sha((out/'results.json').read_bytes())}),flush=True)

if __name__=='__main__':main()
