#!/usr/bin/env python3
"""One fixed qA source stage; strict raw PP/native gates before fixed codec."""
import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time
import types

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
RECIPE_SHA256='a28a09c9551d923a9bde236fda698ce9fd5943e45fa71ac9589f55ab7747a5ce'
OWN=('.gitattributes','README.md','recipe.json','build.py','generate.py','policy.py','gate.py','package.py','tools.py')

def sha(data):return hashlib.sha256(data).hexdigest()
def need(v,m):
    if not v:raise ValueError(m)
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

def literal_value(node):
    if isinstance(node,ast.Constant)and isinstance(node.value,bytes):return node.value
    if (isinstance(node,ast.Call)and isinstance(node.func,ast.Attribute)and node.func.attr=='encode'
        and isinstance(node.func.value,ast.Constant)and isinstance(node.func.value.value,str)
        and not node.args and not node.keywords):return node.func.value.value.encode()
    raise ValueError('unexpected owned source literal')

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
    out=a.out.resolve()
    need(platform.system()=='Linux'and platform.machine()in('x86_64','amd64')and a.out.is_absolute()and not out.exists()
         and not any((p/'.git').exists()for p in(out,*out.parents)),'new absolute external Linux x86-64 output required')
    raw_recipe=(HERE/'recipe.json').read_bytes();need(sha(raw_recipe)==RECIPE_SHA256,'literal first-cost recipe differs')
    recipe=json.loads(raw_recipe);need(recipe['class']=='one-fixed-AF-qA-stop-expression-v1','unknown stage')
    out.mkdir();report={'complete':False,'scope':'one fixed qA actual first cost; no engine, semantic or game execution',
        'source_sha256':{},'commands':[],'families':{},'engine_runs':0,'semantic_proof_runs':0,'game_runs':0,
        'benchmark_runs':0,'runtime_qualified':False,'native_policy':'original complete literal native before codec; no exceptions'}
    def save():(out/'first-cost.json').write_text(json.dumps(report,indent=2)+'\n')
    save();tools=None;cleanup=None;handles=None
    old={s:signal.signal(s,lambda _s,_f:(_ for _ in()).throw(InterruptedError('parent signal')))
         for s in(signal.SIGTERM,signal.SIGINT)}
    try:
        frozen=out/'inputs';control=frozen/'control'
        names=['control/'+n for n in recipe['control_files_sha256']]+list(OWN)
        need(len(names)==37 and len(set(names))==37 and recipe['control_file_count']==28,'closed source count')
        for name in names:
            raw=(HERE/name).read_bytes();need(b'\r'not in raw,'owned sources must be LF: '+name)
            target=frozen/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
            report['source_sha256'][name]=sha(raw)
        for name,pin in recipe['control_files_sha256'].items():need(sha((control/name).read_bytes())==pin,'ordinary control drift: '+name)
        for name,pin in recipe['owned_helper_sha256'].items():need(sha((frozen/name).read_bytes())==pin,'owned helper drift: '+name)
        tools=module('qA_tools',frozen/'tools.py');run,cleanup,handles=tools.create(out,report,save,time.monotonic()+600)
        generate=module('qA_generate',frozen/'generate.py');policy=module('qA_policy',frozen/'policy.py')
        gate=module('qA_gate',frozen/'gate.py');package=module('qA_package',frozen/'package.py')
        literal=module('qA_source_literal',control/'engines/compact/tiny-a/pack_stream.py').source_literal
        # All original baseline reproduction precedes any candidate native generation.
        originals={}
        for family in('A','F'):
            row={'status':'baseline-started','candidate_attempts':[]};report['families'][family]=row;save()
            selected=control/'engines/compact'/('tiny-entry-'+family.lower());fixed=json.loads((selected/'recipe.json').read_text())
            recorded=recipe['families'][family]
            need(fixed['expected']==recorded['control_expected']and fixed['compiler']==recorded['compiler']and
                 fixed['preprocessor']==recorded['preprocessor']and fixed['compression']==recorded['compression'],
                 'closed baseline recipe decisions differ')
            need(fixed['profile']=={'workers':2,'tt_bits':18,'ply':128,'dev_default':False},'fixed resources changed')
            destination=out/('control-'+family)
            run([sys.executable,'-I','-B',str(selected/'build.py'),'--out',str(destination)],out/('baseline-tool-'+family),None,240)
            built=json.loads((destination/'build.json').read_text());need(built['complete']and len(built['attempts'])==2 and
                built['source_reproduced']and built['native_reproduced']and built['whole_reproduced'],'baseline reproduction incomplete')
            expected=fixed['expected'];source=(destination/'main.c').read_bytes();native=(destination/'native/x').read_bytes();whole=(destination/'x').read_bytes()
            for data,kind in((source,'source'),(native,'native'),(whole,'whole')):
                need(len(data)==expected[kind+'_bytes']and sha(data)==expected[kind+'_sha256'],'baseline literal identity: '+kind)
            row['control']={'source_bytes':len(source),'source_sha256':sha(source),'native_bytes':len(native),
                'native_sha256':sha(native),'whole_bytes':len(whole),'whole_sha256':sha(whole),
                'independent_attempts':2,'build_receipt_sha256':sha((destination/'build.json').read_bytes()),'DEV_built':False}
            row['status']='baseline-reproduced';originals[family]=(selected,fixed,source,native,whole);save()
        for family in('A','F'):
            row=report['families'][family];selected,fixed,baseline_source,baseline_native,baseline_whole=originals[family]
            compiled=[];first=None;row['status']='candidate-started';save()
            for attempt in(1,2):
                directory=out/('candidate-'+family)/('attempt-'+str(attempt));directory.mkdir(parents=True)
                item={'attempt':attempt,'status':'source-started','gate_file':str(directory/'gate/gate.json'),
                      'native_compile_started':False,'codec_started':False};row['candidate_attempts'].append(item);save()
                source,observations,readable,lexer=generate.source(control,family,directory/'preprocess',run)
                need(source==baseline_source,'independent ordinary shipping generation differs from literal baseline')
                candidate,meta=policy.transform(source,family=family,recipe=recipe,lexer=lexer,readable=readable)
                (directory/'original.c').write_bytes(source);(directory/'main.c').write_bytes(candidate)
                item.update(status='source-admitted',source_bytes=len(candidate),source_sha256=sha(candidate),stage=meta,preprocessor=observations);save()
                # Strict raw expansion equality and exact single-definition Counter delta.
                item['gate']=gate.check(source,candidate,fixed['compiler'],readable,directory/'gate',run);save()
                item['native_compile_started']=True;save()
                run(fixed['compiler'],directory/'native',candidate,90)
                native=(directory/'native/x').read_bytes();expected=fixed['expected']
                item.update(native_bytes=len(native),native_sha256=sha(native));save()
                need(native==baseline_native and len(native)==expected['native_bytes']and sha(native)==expected['native_sha256'],
                     'candidate COMPLETE native differs; stopped before codec with no exception')
                item.update(status='full-native-exact',full_original_native_exact=True);compiled.append((directory,candidate,native,item));save()
            need(len(compiled)==2 and all(item['full_original_native_exact']for d,c,n,item in compiled),
                 'both full-native gates must precede either codec')
            for directory,candidate,native,item in compiled:
                item['codec_started']=True;save()
                def decode(command,*,input,capture_output,timeout):
                    need(capture_output and command==({'A':['lzma','-dc'],'F':['xz','-dc']}[family]),'fixed codec CLI changed')
                    return run(command,directory/'independent-decode',input,timeout)
                package.subprocess=types.SimpleNamespace(run=decode)
                whole,script,kind=package.package(candidate,selected,fixed,literal)
                calls=[n for n in ast.walk(ast.parse(script))if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)
                    and isinstance(n.func.value,ast.Name)and n.func.value.id=='p'and n.func.attr=='communicate']
                need(len(calls)==1 and len(calls[0].args)==1 and literal_value(calls[0].args[0])==candidate,
                     'actual packaged compiler-stdin source differs')
                (directory/'x').write_bytes(whole);(directory/'x').chmod(0o755);(directory/'bootstrap.py').write_bytes(script)
                current=(candidate,native,whole,script)
                if first is None:first=current
                else:need(current==first,'independent candidate tuple does not reproduce')
                item.update(status='packaged',whole_bytes=len(whole),whole_sha256=sha(whole),bootstrap_sha256=sha(script),literal=kind);save()
            row.update(status='fixed-cost-complete',source_bytes=len(first[0]),source_sha256=sha(first[0]),
                native_bytes=len(first[1]),native_sha256=sha(first[1]),whole_bytes=len(first[2]),whole_sha256=sha(first[2]),
                bootstrap_sha256=sha(first[3]),independent_attempts=2,source_saved_bytes=len(baseline_source)-len(first[0]),
                whole_saved_bytes=len(baseline_whole)-len(first[2]),full_native_exact=True,under4096=len(first[2])<=4096)
            print(json.dumps({'family':family,'whole_bytes':row['whole_bytes'],'whole_saved_bytes':row['whole_saved_bytes'],
                'source_saved_bytes':row['source_saved_bytes'],'full_native_exact':True}),flush=True);save()
        need(not handles and all(c['returncode']==0 and c['terminal']and c['group_absent']and c['pipes_drained']and
            not c['forced_cleanup']and not c['cleanup_errors']for c in report['commands']),'owned tool settlement incomplete')
        report.update(complete=True,live_owned_handles=0)
    except BaseException as error:
        report['complete']=False;report['error']={'type':type(error).__name__,'message':str(error)};raise
    finally:
        if cleanup is not None:cleanup()
        else:report.update(outer_cleanup=[],live_owned_handles_after_cleanup=0)
        save()
        for s,h in old.items():signal.signal(s,h)
    print(json.dumps({'complete':report['complete'],'engine_runs':0,'out':str(out)}),flush=True)
    need(report['complete'],'first cost incomplete after cleanup')

if __name__=='__main__':main()
