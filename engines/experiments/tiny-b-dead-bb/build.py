#!/usr/bin/env python3
"""One B dead-bb first cost; compiler tools only, no engine/proof execution."""
import argparse
import ast
import hashlib
import importlib.util
import json
import lzma
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
RECIPE_SHA256='ec0aaee758273cee5b21e4d4b6b7633c26029d6cc39db9bcd38f80b5ec8f2d99'
RAW=set()

def sha(data):return hashlib.sha256(data).hexdigest()
def need(value,message):
    if not value:raise ValueError(message)
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result
def absent(pid):
    try:os.killpg(pid,0);return False
    except ProcessLookupError:return True

def candidate_source(original,body,recipe):
    text=original.decode();marker='int dead(const Board *p){'
    need(text.count(marker)==1,'dead function count')
    a=text.index(marker);b=text.index('\n/* Canonicalize EP',a)
    need(sha(text[a:b].encode())==recipe['dead_original_sha256'],'original dead body')
    need(sha(body)==recipe['dead_candidate_sha256'],'candidate dead body')
    result=original[:a]+body+original[b:]
    need(sha(result)==recipe['candidate_readable_sha256'],'candidate readable input')
    need(result[:a]==original[:a]and result[a+len(body):]==original[b:],'outside dead changed')
    return result

def literal_value(node):
    if isinstance(node,ast.Constant)and isinstance(node.value,bytes):return node.value
    if (isinstance(node,ast.Call)and isinstance(node.func,ast.Attribute)and node.func.attr=='encode'
        and isinstance(node.func.value,ast.Constant)and isinstance(node.func.value.value,str)
        and not node.args and not node.keywords):return node.func.value.value.encode()
    raise ValueError('unexpected fixed source-literal AST')

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    out=args.out.resolve()
    need(platform.system()=='Linux'and platform.machine()in('x86_64','amd64')and args.out.is_absolute()
         and not out.exists()and not any((p/'.git').exists()for p in(out,*out.parents)),
         'new absolute external Linux x86-64 output required')
    need(sha((HERE/'recipe.json').read_bytes())==RECIPE_SHA256,'literal first-cost recipe')
    recipe=json.loads((HERE/'recipe.json').read_text())
    need(recipe['class']=='tiny-b-dead-bb-one-candidate-v1','unknown candidate class')
    out.mkdir();report={'complete':False,'scope':'one fixed dead-bb first cost only; no engine or proof execution',
        'class':recipe['class'],'source_sha256':{},'commands':[],'candidate_attempts':[],
        'engine_executions':0,'board_search_runtime_proof_executions':0,'benchmark_executions':0,
        'runtime_qualified':False,'bb_mailbox_consistency_required':True,
        'old_B_target5899_not_input_or_added_prediction':True}
    deadline=time.monotonic()+600
    def save():(out/'first-cost.json').write_text(json.dumps(report,indent=2)+'\n')
    def run(command,directory,input_data=None,timeout=180):
        directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
        row={'command':command,'pid':None,'returncode':None,'forced_cleanup':False,'cleanup_errors':[]}
        report['commands'].append(row);index=len(report['commands']);remaining=min(timeout,deadline-time.monotonic())
        need(remaining>0,'aggregate build deadline')
        mask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGTERM,signal.SIGINT})
        try:
            p=subprocess.Popen(command,cwd=directory,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                start_new_session=True,preexec_fn=lambda:signal.pthread_sigmask(signal.SIG_SETMASK,mask),
                env={**os.environ,'LC_ALL':'C','TZ':'UTC','SOURCE_DATE_EPOCH':'0'})
            RAW.add(p);row['pid']=p.pid
        finally:signal.pthread_sigmask(signal.SIG_SETMASK,mask)
        stdout=stderr=b'';failure=None;drained=False
        try:
            stdout,stderr=p.communicate(input_data,timeout=remaining);drained=True
            row.update(returncode=p.returncode,input_bytes=len(input_data)if input_data is not None else 0,
                       input_sha256=sha(input_data)if input_data is not None else None)
            need(p.returncode==0,'tool failed; see external logs')
        except BaseException as error:
            failure=sys.exc_info();row['tool_error']={'type':type(error).__name__,'message':str(error)}
            stdout=getattr(error,'output',None)or stdout;stderr=getattr(error,'stderr',None)or stderr
        finally:
            if p.poll()is None or not absent(p.pid):
                try:os.killpg(p.pid,signal.SIGKILL);row['forced_cleanup']=True
                except ProcessLookupError:pass
                except BaseException as error:row['cleanup_errors'].append({'action':'kill','error':repr(error)})
            if not drained:
                try:stdout,stderr=p.communicate(timeout=3);drained=True
                except BaseException as error:
                    row['cleanup_errors'].append({'action':'drain','error':repr(error)})
                    stdout=getattr(error,'output',None)or stdout;stderr=getattr(error,'stderr',None)or stderr
            logs=out/'tool-logs';logs.mkdir(exist_ok=True)
            (logs/(str(index)+'.stdout.bin')).write_bytes(stdout);(logs/(str(index)+'.stderr.bin')).write_bytes(stderr)
            row.update(returncode=p.returncode,group_absent=absent(p.pid),terminal=p.returncode is not None,
                       pipes_drained=drained,stdout_sha256=sha(stdout),stderr_sha256=sha(stderr))
            if row['group_absent']and row['terminal']and drained:RAW.discard(p)
            save()
        # Preserve the original operation failure; cleanup status never overwrites it.
        if failure is not None:raise failure[1].with_traceback(failure[2])
        need(row['group_absent']and row['terminal']and drained and not row['forced_cleanup']and not row['cleanup_errors'],
             'tool cleanup intervention or incomplete settlement; see command receipt')
        return subprocess.CompletedProcess(command,p.returncode,stdout,stderr)
    previous={s:signal.signal(s,lambda _s,_f:(_ for _ in()).throw(InterruptedError('parent signal')))
              for s in(signal.SIGTERM,signal.SIGINT)}
    try:
        frozen=out/'inputs';control=frozen/'control'
        own=('dead.c.in','alpha_guard.py','header_gate.py','recipe.json','build.py','README.md','.gitattributes')
        names=['control/'+p for p in recipe['control_paths_sha256']]+list(own)
        need(len(names)==24 and len(set(names))==24,'source closure count')
        for name in names:
            raw=(HERE/name).read_bytes();need(b'\r'not in raw,'source must be LF')
            path=frozen/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
            report['source_sha256'][name]=sha(raw)
        for name,pin in recipe['control_paths_sha256'].items():need(sha((control/name).read_bytes())==pin,'control snapshot drift: '+name)
        for name,key in(('dead.c.in','dead_candidate_sha256'),('alpha_guard.py','alpha_guard_sha256'),('header_gate.py','header_gate_sha256')):
            need(sha((frozen/name).read_bytes())==recipe[key],'new source literal drift: '+name)
        entry=control/'engines/compact/tiny-entry-b';fixed=json.loads((entry/'recipe.json').read_text())
        need(sha((entry/'recipe.json').read_bytes())==recipe['control_recipe_sha256'],'fixed original recipe')
        # The unchanged original builder performs its own two independent literal generations.
        original=run([sys.executable,'-B',str(entry/'build.py'),'--out',str(out/'control-cost')],out/'control-tool')
        baseline=json.loads((out/'control-cost/build.json').read_text())
        need(baseline['complete']and len(baseline['attempts'])==2 and baseline['whole_reproduced']and baseline['native_reproduced'],
             'control two-attempt generation incomplete')
        expected=fixed['expected'];control_native=(out/'control-cost/native/x').read_bytes()
        need(len(control_native)==26592 and sha(control_native)==expected['native_sha256'],'control whole native')
        need((out/'control-cost/x').stat().st_size==5955 and sha((out/'control-cost/x').read_bytes())==expected['whole_sha256'],
             'control whole launcher')
        report['control']={'attempts':2,'source_bytes':expected['source_bytes'],'source_sha256':expected['source_sha256'],
            'native_bytes':len(control_native),'native_sha256':sha(control_native),
            'whole_bytes':5955,'whole_sha256':expected['whole_sha256'],'builder_report':str(out/'control-cost/build.json')}
        save()
        specialize=module('dead_bb_specialize',control/'engines/scripts/specialize.py')
        def special_run(command,*,cwd,env,check,stdout,stderr,timeout):
            need(check and stdout==subprocess.PIPE and stderr==subprocess.PIPE,'specialization I/O contract')
            return run(command,cwd,None,timeout)
        # Only inject managed I/O; the frozen helper source and command logic stay exact.
        specialize.subprocess=types.SimpleNamespace(run=special_run,PIPE=subprocess.PIPE)
        compact=module('dead_bb_minify',control/'engines/scripts/minify.py').compact_source
        strip=module('dead_bb_strip',control/'engines/compact/tiny-b/generate.py').strip_counters
        alpha=module('dead_bb_alpha',control/'engines/scripts/fixed_shipping_alpha.py')
        lexer=module('dead_bb_lexer',control/'engines/scripts/rename_c.py')
        guard=module('dead_bb_guard',frozen/'alpha_guard.py')
        gate=module('dead_bb_header',frozen/'header_gate.py');gate.run=run
        literal=module('dead_bb_literal',control/'engines/compact/tiny-a/pack_stream.py').source_literal
        policy=json.loads(alpha._POLICY_BYTES);mapping=policy['mapping']
        source=candidate_source((entry/'engine.c').read_bytes(),(frozen/'dead.c.in').read_bytes(),recipe)
        template=(entry/'bootstrap.py.in').read_bytes();prefix=(entry/'launcher.sh').read_bytes();marker=b'__ROVE_SOURCE_LITERAL__'
        need(len(prefix)==75 and template.count(marker)==1,'fixed package structure')
        need(fixed['compression']=={'format':'xz','filter':'LZMA2','preset':9,'extreme':True,'lc':3,'lp':0,'pb':2,'check':'CRC64'},'fixed codec changed')
        first=None
        for index in(1,2):
            directory=out/('candidate-'+str(index));directory.mkdir();(directory/'engine.c').write_bytes(source)
            active,observations=specialize.specialize_c({'main.c':source},directory/'preprocess',
                fixed['preprocessor']+['-DDEV=0','main.c','-o','x'],os.environ.copy())
            pre,strip_meta=strip(compact(active['main.c'],'c'));aliased,alpha_meta=guard.transform_source(pre,recipe,alpha,lexer)
            (directory/'pre-alpha.c').write_bytes(pre);(directory/'main.c').write_bytes(aliased)
            header=gate.header_gate(pre,aliased,fixed['compiler'],mapping,lexer,directory/'header')
            run(fixed['compiler'],directory/'pre-alpha-native',pre,90)
            run(fixed['compiler'],directory/'native',aliased,90)
            before=(directory/'pre-alpha-native/x').read_bytes();native=(directory/'native/x').read_bytes()
            need(native==before,'candidate full native changed across unchanged alias policy')
            expression,kind=literal(aliased);script=template.replace(marker,expression.encode());parsed=ast.parse(script)
            calls=[n for n in ast.walk(parsed)if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)
                   and isinstance(n.func.value,ast.Name)and n.func.value.id=='p'and n.func.attr=='communicate']
            need(len(calls)==1 and len(calls[0].args)==1 and literal_value(calls[0].args[0])==aliased,'actual compiler-stdin literal differs')
            payload=lzma.compress(script,format=lzma.FORMAT_XZ,check=lzma.CHECK_CRC64,
                filters=[{'id':lzma.FILTER_LZMA2,'preset':9|lzma.PRESET_EXTREME,'lc':3,'lp':0,'pb':2}])
            need(lzma.decompress(payload,format=lzma.FORMAT_XZ)==script,'fixed payload roundtrip')
            whole=prefix+payload;(directory/'bootstrap.py').write_bytes(script);(directory/'x').write_bytes(whole);(directory/'x').chmod(0o755)
            current=(pre,aliased,before,native,script,whole)
            if first is None:first=current
            else:need(current==first,'independent candidate generation differs')
            report['candidate_attempts'].append({'attempt':index,'readable_bytes':len(source),'readable_sha256':sha(source),
                'pre_alpha_bytes':len(pre),'pre_alpha_sha256':sha(pre),'source_bytes':len(aliased),'source_sha256':sha(aliased),
                'native_bytes':len(native),'native_sha256':sha(native),'pre_alpha_native_sha256':sha(before),
                'full_native_alias_before_after_identical':True,'candidate_native_equals_old_control':native==control_native,
                'whole_bytes':len(whole),'whole_sha256':sha(whole),'payload_bytes':len(payload),'launcher_bytes':len(prefix),
                'bootstrap_sha256':sha(script),'source_literal_kind':kind,'header_gate':header,'alpha':alpha_meta,
                'preprocessor':observations,'counter_strip':strip_meta,'no_material_or_search_proof_run':True})
            save()
        need(not RAW and all(c['terminal']and c['group_absent']and not c['forced_cleanup']for c in report['commands']),
             'tool settlement incomplete')
        report.update(complete=True,ordinary_source_delta=-77,pre_alpha_delta=len(first[0])-15566,
            shipping_source_delta=len(first[1])-13606,native_delta=len(first[3])-26592,
            actual_whole_delta=len(first[5])-5955,actual_whole_bytes=len(first[5]),under4096=len(first[5])<=4096,
            source_native_whole_independently_reproduced=True,live_owned_handles=0)
    except BaseException as error:
        report['complete']=False;report['error']={'type':type(error).__name__,'message':str(error)};raise
    finally:
        report['outer_cleanup']=[]
        for p in list(RAW):
            report['complete']=False;cleanup={'pid':p.pid,'errors':[]};stdout=stderr=b'';drained=False
            try:os.killpg(p.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            except BaseException as error:cleanup['errors'].append({'action':'kill','error':repr(error)})
            try:stdout,stderr=p.communicate(timeout=3);drained=True
            except BaseException as error:
                cleanup['errors'].append({'action':'drain','error':repr(error)})
                stdout=getattr(error,'output',None)or b'';stderr=getattr(error,'stderr',None)or b''
            logs=out/'tool-logs';logs.mkdir(exist_ok=True)
            (logs/('outer-'+str(p.pid)+'.stdout.bin')).write_bytes(stdout)
            (logs/('outer-'+str(p.pid)+'.stderr.bin')).write_bytes(stderr)
            cleanup.update(returncode=p.returncode,group_absent=absent(p.pid),pipes_drained=drained,
                           stdout_sha256=sha(stdout),stderr_sha256=sha(stderr))
            report['outer_cleanup'].append(cleanup)
            if cleanup['group_absent']and p.returncode is not None and drained:RAW.discard(p)
        report['live_owned_handles_after_cleanup']=len(RAW)
        if RAW or report['outer_cleanup']:report['complete']=False
        save()
        for s,h in previous.items():signal.signal(s,h)
    print(json.dumps({'complete':report['complete'],'actual_whole_bytes':report.get('actual_whole_bytes'),
        'actual_whole_delta':report.get('actual_whole_delta'),'engine_executions':0,'out':str(out)}))
    need(report['complete'],'first-cost incomplete after cleanup')

if __name__=='__main__':main()
