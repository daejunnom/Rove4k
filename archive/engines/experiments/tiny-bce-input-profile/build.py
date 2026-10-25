"""One native and the unchanged fixed ALONE whole per exact B/C/E proposal."""
import argparse
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

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]


def sha(data):return hashlib.sha256(data).hexdigest()


def need(condition,message):
    if not condition:raise ValueError(message)


def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n')


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve()
    need(args.out.is_absolute() and not out.exists() and
         not any((p/'.git').exists() for p in (out,*out.parents)),'new absolute output outside Git required')
    need(sys.platform=='linux' and platform.machine()=='x86_64','fixed Linux AMD64 target')
    recipe=json.loads((HERE/'recipe.json').read_bytes());out.mkdir();frozen=out/'inputs';frozen.mkdir()
    report={'complete':False,'scope':'one exact input-profile source candidate per B/C/E; cost only',
            'native_compiles':0,'codec_compressions':0,'baseline_compiles':0,'baseline_artifact_copies':0,
            'C_AST_runs':0,'preprocessor_commands':0,'DEV_generations':0,'engine_runs':0,
            'games':0,'benchmarks':0,'normal_builder_runs':0,'inputs':{},'families':{},
            'bootstrap_literal_decoder':'unchanged pinned restricted Python AST; no C AST',
            'python':sys.version,'platform':platform.platform()}
    save(out/'cost.json',report);deadline=time.monotonic()+150

    def cancelled(signum,frame):raise TimeoutError('bounded input-profile cost cancelled')

    previous={s:signal.signal(s,cancelled) for s in (signal.SIGINT,signal.SIGTERM)}

    def compile_one(command,source,directory):
        directory.mkdir();process=None
        try:
            timeout=min(60,deadline-time.monotonic());need(timeout>0,'aggregate cost deadline')
            mask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGINT,signal.SIGTERM})
            try:
                process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,cwd=directory,start_new_session=True,
                    preexec_fn=lambda:signal.pthread_sigmask(signal.SIG_SETMASK,mask))
            finally:signal.pthread_sigmask(signal.SIG_SETMASK,mask)
            stdout,stderr=process.communicate(source,timeout=timeout)
            (directory/'compiler.stdout').write_bytes(stdout);(directory/'compiler.stderr').write_bytes(stderr)
            row={'command':command,'cwd':str(directory),'returncode':process.returncode,
                 'stdin_bytes':len(source),'stdin_sha256':sha(source),'leader_pid':process.pid,
                 'compiler_group_cleanup':'finally sends killpg after communicate; no separate absence observer'}
            save(directory/'compile.json',row)
            need(process.returncode==0,'candidate compiler failed; first failure stops')
            return (directory/'x').read_bytes(),row
        finally:
            if process is not None:
                try:os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                if process.poll() is None:process.wait(timeout=3)

    try:
        for name in ('build.py','transform.py','recipe.json','README.md','.gitattributes'):
            data=(HERE/name).read_bytes();(frozen/name).write_bytes(data)
            report['inputs'][name]={'bytes':len(data),'sha256':sha(data)}
        need(report['inputs']['transform.py']==recipe['transform'],'exact source transform changed')
        ordinary={}
        for relative,pin in recipe['cost']['tracked_inputs'].items():
            raw=(REPO/relative).read_bytes();data=raw.replace(b'\r\n',b'\n')
            need(b'\r' not in data and sha(data)==pin,'tracked input drift: '+relative)
            ordinary[relative]=data
            report['inputs'][relative]={'bytes':len(data),'sha256':sha(data),'raw_sha256':sha(raw)}
            # Do not copy canonical controls or prior normal recipes/artifacts.
            if relative in recipe['cost']['frozen_pure_helpers'] or relative.endswith(('/bootstrap.py.in','/launcher.sh')):
                target=frozen/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        transform=module('fixed_bce_input_transform',frozen/'transform.py')
        literal=module('fixed_existing_source_literal',frozen/'engines/compact/tiny-a/pack_stream.py').source_literal
        decode=module('fixed_existing_literal_decode',frozen/'engines/experiments/tiny-source-codec/decode.py').verify
        prepared={}
        # Admit all controls and deterministic source roles before any compile.
        for family,case in recipe['families'].items():
            baseline={}
            for role,item in case['baseline_files'].items():
                data=Path(item['path']).read_bytes()
                need((len(data),sha(data))==(item['bytes'],item['sha256']),'current control drift: '+family+'/'+role)
                baseline[role]=data
            canonical=ordinary[case['canonical_path']]
            source,proof=transform.transform_source(baseline['source'],readable=canonical,family=family)
            dual,readable_proof=transform.transform_readable(canonical,family=family)
            directory=out/family;directory.mkdir();(directory/'main.c').write_bytes(source)
            (directory/'readable.c').write_bytes(dual);save(directory/'source.json',proof)
            template=ordinary[case['template']];prefix=ordinary[case['prefix']]
            need(template.count(b'__ROVE_SOURCE_LITERAL__')==1 and len(prefix)==77,'fixed transport boundary differs')
            old_expression,_=literal(baseline['source'])
            need(template.replace(b'__ROVE_SOURCE_LITERAL__',old_expression.encode())==baseline['bootstrap'],
                 'old source/template bootstrap identity differs')
            need(baseline['whole'].startswith(prefix),'current prefix identity differs')
            prepared[family]=(source,template,prefix,directory)
            report['families'][family]={'source':proof,'baseline_read_only':case['baseline_files'],
                'native_compiles':0,'codec_compressions':0,'runtime_qualified':False}
        save(out/'cost.json',report)
        for family,case in recipe['families'].items():
            source,template,prefix,directory=prepared[family];row=report['families'][family]
            report['native_compiles']+=1;row['native_compiles']=1;save(out/'cost.json',report)
            native,compiled=compile_one(case['compiler'],source,directory/'native')
            row['native']={'bytes':len(native),'sha256':sha(native),'command':compiled['command'],
                           'full_equal_to_control':sha(native)==case['normal_expected_reused_as_input_pin']['native_sha256'],
                           'metadata_difference_exception':False}
            expression,kind=literal(source);script=template.replace(b'__ROVE_SOURCE_LITERAL__',expression.encode())
            settings=case['compression']
            need(settings==dict(format='lzma-alone',filter='LZMA1',preset=9,extreme=True,
                 lc=2,lp=0,pb=0,check='NONE',mf='BT4',dictionary_bytes=67108864,
                 nice_len=64 if family=='C' else 32),'fixed codec input differs')
            report['codec_compressions']+=1;row['codec_compressions']=1;save(out/'cost.json',report)
            payload=lzma.compress(script,format=lzma.FORMAT_ALONE,check=lzma.CHECK_NONE,
                filters=[{'id':lzma.FILTER_LZMA1,'preset':9|lzma.PRESET_EXTREME,'lc':2,'lp':0,'pb':0,
                          'mf':lzma.MF_BT4,'dict_size':67108864,'nice_len':settings['nice_len']}])
            whole=prefix+payload;(directory/'bootstrap.py').write_bytes(script);(directory/'x').write_bytes(whole)
            decode_proof=decode(whole,prefix,source,case['compiler'],script,expected_format='alone')
            save(directory/'decode.json',decode_proof)
            old=case['normal_expected_reused_as_input_pin']
            row.update(whole={'bytes':len(whole),'sha256':sha(whole)},
                bootstrap={'bytes':len(script),'sha256':sha(script)},source_literal_kind=kind,
                source_bytes=len(source),source_sha256=sha(source),
                whole_delta=len(whole)-old['whole_bytes'],native_delta=len(native)-old['native_bytes'],
                strict_decode_sha256=sha((directory/'decode.json').read_bytes()),
                next_action='await separate functional follow-up' if len(whole)<old['whole_bytes'] else 'tie/loss; family stops')
            save(out/'cost.json',report)
            print(json.dumps({'family':family,'source_bytes':len(source),'native':row['native'],
                              'whole':row['whole'],'whole_delta':row['whole_delta']}),flush=True)
        report['complete']=True;save(out/'cost.json',report)
    except BaseException as error:
        report['failure']={'type':type(error).__name__,'message':str(error)};save(out/'cost.json',report);raise
    finally:
        for signum,handler in previous.items():signal.signal(signum,handler)


if __name__=='__main__':main()
