#!/usr/bin/env python3
"""One E first cost: baseline2, input-only prepare, then frozen candidate2.

Only explicitly fixed compiler/PP tools and the fixed in-process codec run.
No output executable, DEV qualification, game or benchmark is ever launched.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
import lzma
import os
from pathlib import Path
import platform
import subprocess
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
def sha(data):return hashlib.sha256(data).hexdigest()
def need(v,m):
    if not v:raise ValueError(m)
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=('baseline','prepare','candidate'))
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--baseline-receipt',type=Path,help='completed baseline receipt; metadata gate only, never a source input')
    args=parser.parse_args();out=args.out.resolve()
    need(args.out.is_absolute()and not out.exists()and not any((p/'.git').exists()for p in (out,*out.parents)),'new external absolute output required')
    need(platform.system()=='Linux'and platform.machine()=='x86_64','fixed Linux x86-64 target required')
    recipe=json.loads((HERE/'recipe.json').read_bytes())
    need(recipe['class']=='E-source-composition-next-one'and recipe['fixed_policy_sha256']=='b3f08ba26b38dbce1e4b63d3eb98ab37f438295cfacff6037b1cfacbf7d5e5a0','unknown fixed experiment')
    out.mkdir(parents=True);frozen=out/'inputs';frozen.mkdir()
    report={'complete':False,'mode':args.mode,'class':recipe['class'],'commands':[],
        'candidate_engine_executions':0,'control_engine_executions':0,'DEV_qualification_executions':0,
        'games':0,'benchmarks':0,'training':0,'AWS':0,'attempts':[],'inputs':{},'old_new_native_equality_required':False}
    def save():(out/'cost.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    def run(command,directory,input_data=None,timeout=90):
        directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
        row={'command':command,'returncode':None};report['commands'].append(row);index=len(report['commands'])
        try:
            result=subprocess.run(command,cwd=directory,input=input_data,capture_output=True,timeout=timeout)
            row.update(returncode=result.returncode,stdout_sha256=sha(result.stdout),stderr_sha256=sha(result.stderr))
            logs=out/'tool-logs';logs.mkdir(exist_ok=True)
            (logs/(str(index)+'.stdout.bin')).write_bytes(result.stdout);(logs/(str(index)+'.stderr.bin')).write_bytes(result.stderr)
            need(result.returncode==0,'fixed tool failed; external stdout/stderr preserved')
            return result
        except BaseException as error:
            row['error']={'type':type(error).__name__,'message':str(error)};raise
        finally:save()
    try:
        for relative,pin in recipe['source_sha256'].items():
            data=(HERE/relative).read_bytes();need(sha(data)==pin,'owned source differs: '+relative)
            destination=frozen/relative;destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(data)
            report['inputs'][relative]={'bytes':len(data),'sha256':sha(data)}
        (frozen/'recipe.json').write_bytes((HERE/'recipe.json').read_bytes());report['recipe_sha256']=sha((frozen/'recipe.json').read_bytes());save()
        control=frozen/'control';entry=control/'engines/compact/tiny-entry-e'
        old=json.loads((entry/'recipe.json').read_bytes());expected=old['expected']
        flags=['cc','-std=c11','-Os','-pthread','-DWORKERS=2','-DTT_BITS=18']
        need(old['profile']=={'workers':2,'tt_bits':18,'ply':128,'dev_default':False}and old['preprocessor']==flags
            and old['compiler']==flags+['-DDEV=0','-x','c','-','-o','x'],'fixed E profile/compiler differs')
        need(old['compression']=={'format':'xz','filter':'LZMA2','preset':9,'extreme':True,'lc':3,'lp':0,'pb':2,'check':'CRC64'},'fixed codec differs')
        for relative,pin in old['local_input_sha256'].items():need(sha((entry/relative).read_bytes())==pin,'old local pin differs')
        for relative,pin in old['helper_sha256'].items():need(sha((control/relative).read_bytes())==pin,'old helper pin differs')
        if args.mode=='baseline':
            run([sys.executable,str(entry/'build.py'),'--out',str(out/'unchanged-builder')],out,timeout=300)
            baseline=json.loads((out/'unchanged-builder/build.json').read_bytes())
            need(baseline['complete']and len(baseline['attempts'])==2,'unchanged baseline builder did not reproduce twice')
            report.update(complete=True,attempts=baseline['attempts'],whole_bytes=expected['whole_bytes'],
                whole_delta_vs_E5679=0,baseline_pipeline='unchanged owned maintained builder',runtime_qualified=False)
            save();print(json.dumps({'complete':True,'mode':'baseline','whole_bytes':expected['whole_bytes']}),flush=True);return
        report['tools']={n:run(c,out/'versions',timeout=10).stdout.decode().splitlines()[0]for n,c in
            {'cc':['cc','--version'],'ld':['ld','--version'],'python':['python3','--version'],'xz':['xz','--version']}.items()}
        specialize=module('e_owned_specialize',control/'engines/scripts/specialize.py')
        compact=module('e_owned_minify',control/'engines/scripts/minify.py').compact_source
        strip=module('e_owned_strip',control/'engines/compact/tiny-a/stitch.py').strip_dev_counters
        literal=module('e_owned_literal',control/'engines/compact/tiny-a/pack_stream.py').source_literal
        reference=module('e_owned_fixed89',control/'engines/scripts/fixed_shipping_alpha.py')
        lexer=module('e_owned_lexer',control/'engines/scripts/rename_c.py')
        guard=module('e_local_guard',frozen/'alpha_guard.py')
        generate=module('e_local_generate',frozen/'generate.py')
        header=module('e_local_header',frozen/'header_gate.py');header.run=run
        canonical=(entry/'engine.c').read_bytes();candidate=(frozen/'engine.c').read_bytes()
        need(generate.readable(canonical)==candidate and sha(candidate)==recipe['candidate_readable_sha256'],'fixed readable composition differs')
        report['unchanged_model_Board_search_prefix']=canonical.split(b'void think(Worker *w,const Board *p)')[0]==candidate.split(b'void think(Worker *w,const Board *p)')[0]
        template=(entry/'bootstrap.py.in').read_bytes();prefix=(entry/'launcher.sh').read_bytes()
        need(template.count(b'__ROVE_SOURCE_LITERAL__')==1 and len(prefix)==75,'old bootstrap/launcher differs')
        def preprocess(readable,directory):
            active,obs=specialize.specialize_c({'main.c':readable},directory,flags+['-DDEV=0'],os.environ.copy())
            data,_=strip(compact(active['main.c'],'c'));return data,obs
        def compile_native(source,directory):
            result=run(old['compiler'],directory,source,90)
            (directory/'compiler.stderr').write_bytes(result.stderr)
            return (directory/'x').read_bytes()
        def package(source):
            expression,_=literal(source);script=template.replace(b'__ROVE_SOURCE_LITERAL__',expression.encode());ast.parse(script)
            whole=prefix+lzma.compress(script,format=lzma.FORMAT_XZ,check=lzma.CHECK_CRC64,
                filters=[{'id':lzma.FILTER_LZMA2,'preset':9|lzma.PRESET_EXTREME,'lc':3,'lp':0,'pb':2}])
            return whole,script
        if args.mode=='prepare':
            data,obs=preprocess(candidate,out/'preprocess')
            result,counts,mapping=guard.observe(data,reference,lexer)
            admission={'pre_alpha_bytes':len(data),'pre_alpha_sha256':sha(data),'alpha_bytes':len(result),'alpha_sha256':sha(result),'alpha':counts}
            (out/'pre-alpha.c').write_bytes(data);(out/'alpha.c').write_bytes(result)
            report.update(complete=True,candidate_admission=admission,preprocessor=obs,scope='input-only specialization/count observation; no native or codec')
        else:
            if args.mode=='candidate':
                need(args.baseline_receipt is not None,'completed baseline receipt required')
                baseline_raw=args.baseline_receipt.read_bytes();baseline=json.loads(baseline_raw)
                need(baseline['complete']and baseline['mode']=='baseline'and baseline['class']==recipe['class']
                    and len(baseline['attempts'])==2,'completed owned baseline2 required')
                for row in baseline['attempts']:
                    for kind in ('source','native','whole'):
                        need(row[kind+'_sha256']==expected[kind+'_sha256']and row[kind+'_bytes']==expected[kind+'_bytes'],'baseline literal image identity differs')
                report['baseline_receipt']={'path':str(args.baseline_receipt.resolve()),'sha256':sha(baseline_raw),'source_input':False}
            first=None
            for index in (1,2):
                directory=out/('attempt-'+str(index));directory.mkdir()
                data,obs=preprocess(canonical if args.mode=='baseline'else candidate,directory/'preprocess')
                if args.mode=='baseline':
                    source,meta=reference.transform_source(data,family='E',lexer=lexer)
                    need(len(source)==expected['source_bytes']and sha(source)==expected['source_sha256'],'baseline source identity differs')
                    native=compile_native(source,directory/'native')
                    need(len(native)==expected['native_bytes']and sha(native)==expected['native_sha256'],'baseline native identity differs')
                    row={'shipping_alpha':meta}
                else:
                    source,meta,mapping=guard.transform_source(data,recipe,reference,lexer)
                    canonical_words=set(reference._WORD.findall(candidate.decode()))|set(reference._WORD.findall(reference._logical(candidate.decode())[0]))
                    need(not set(mapping.values())&canonical_words,'alias already in candidate readable/raw logical source')
                    rawgate=header.header_gate(data,source,old['compiler'],mapping,lexer,directory/'headers')
                    pre_native=compile_native(data,directory/'pre-alpha-native')
                    native=compile_native(source,directory/'native')
                    need(native==pre_native,'candidate alpha/full native identity differs')
                    row={'shipping_alpha':meta,'raw_PP_gate':rawgate,'alpha_full_native_equal':True,'pre_alpha_native_sha256':sha(pre_native)}
                whole,script=package(source)
                if args.mode=='baseline':need(len(whole)==expected['whole_bytes']and sha(whole)==expected['whole_sha256']and sha(script)==expected['bootstrap_sha256'],'baseline whole/bootstrap identity differs')
                for name,value in (('pre-alpha.c',data),('main.c',source),('x',whole),('bootstrap.py',script)):(directory/name).write_bytes(value)
                current=(data,source,native,whole,script)
                if first is None:first=current
                else:need(current==first,'independent reproduction differs')
                row.update(attempt=index,preprocessor=obs,source_bytes=len(source),source_sha256=sha(source),native_bytes=len(native),native_sha256=sha(native),whole_bytes=len(whole),whole_sha256=sha(whole),bootstrap_sha256=sha(script))
                report['attempts'].append(row);save()
            report.update(complete=True,source_reproduced=True,native_reproduced=True,whole_reproduced=True,
                whole_bytes=len(first[3]),whole_delta_vs_E5679=len(first[3])-expected['whole_bytes'],native_delta_vs_control=len(first[2])-expected['native_bytes'],
                scope='first cost only; raw PP and native alpha identity are not runtime qualification',runtime_qualified=False,under_4096_bytes=len(first[3])<=4096)
        save()
    except BaseException as error:
        report['complete']=False;report['error']={'type':type(error).__name__,'message':str(error)};save();raise
    need(report['complete'],'operation did not settle complete')
    print(json.dumps({'complete':report['complete'],'mode':args.mode,'out':str(out),'whole_bytes':report.get('whole_bytes'),'delta':report.get('whole_delta_vs_E5679')}),flush=True)

if __name__=='__main__':main()
