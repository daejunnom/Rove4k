"""One structural C/E candidate, one native and fixed codec per family."""
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

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def need(ok, message):
    if not ok:
        raise ValueError(message)


def save(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n')


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve()
    need(args.out.is_absolute() and not out.exists() and
         not any((p/'.git').exists() for p in (out,*out.parents)), 'new absolute output outside Git required')
    need(sys.platform=='linux' and platform.machine()=='x86_64','fixed Linux AMD64 target')
    recipe=json.loads((HERE/'recipe.json').read_bytes());out.mkdir();frozen=out/'inputs';frozen.mkdir()
    report={'complete':False,'scope':recipe['scope'],'native_compiles':0,'codec_compressions':0,
            'baseline_compiles':0,'baseline_artifact_copies':0,'preprocessor_commands':0,
            'C_AST_runs':0,'engine_runs':0,'games':0,'benchmarks':0,'inputs':{},'families':{}}
    save(out/'cost.json',report);deadline=time.monotonic()+150

    def cancelled(signum,frame):
        raise TimeoutError('parent cancelled bounded C/E cost')

    previous=signal.signal(signal.SIGTERM,cancelled)

    def run(command,directory=None,source=None):
        process=None
        try:
            timeout=min(60,deadline-time.monotonic());need(timeout>0,'aggregate deadline')
            mask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGTERM})
            try:
                process=subprocess.Popen(command,cwd=directory,stdin=subprocess.PIPE if source is not None else None,
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,
                    preexec_fn=lambda:signal.pthread_sigmask(signal.SIG_SETMASK,mask))
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK,mask)
            stdout,stderr=process.communicate(source,timeout=timeout)
            row={'command':command,'cwd':str(directory) if directory else None,'returncode':process.returncode,
                 'stdout':stdout.decode(errors='replace'),'stderr':stderr.decode(errors='replace')}
            if directory is not None:
                (directory/'compiler.stderr').write_bytes(stderr);save(directory/'compile.json',row)
            need(process.returncode==0,'fixed command failed: '+json.dumps(row))
            return row
        finally:
            if process is not None:
                try:os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                if process.poll() is None:process.wait(timeout=3)

    try:
        for name in ('build.py','transform.py','recipe.json'):
            data=(HERE/name).read_bytes();(frozen/name).write_bytes(data)
            report['inputs'][name]={'bytes':len(data),'sha256':sha(data)}
        ordinary={}
        for name,pin in recipe['tracked_inputs'].items():
            raw=(REPO/name).read_bytes();data=raw.replace(b'\r\n',b'\n')
            need(b'\r' not in data and sha(data)==pin,'tracked input drift: '+name)
            ordinary[name]=data;report['inputs'][name]={'bytes':len(data),'sha256':sha(data),'raw_sha256':sha(raw)}
            # Baseline artifacts/canonical controls are never copied. Freeze only actual pure helpers/templates.
            if name in ('engines/scripts/minify.py','engines/scripts/rename_c.py',
                        'engines/compact/tiny-a/pack_stream.py','engines/experiments/tiny-source-codec/decode.py') or name.endswith(('/bootstrap.py.in','/launcher.sh')):
                target=frozen/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        mutate=module('fixed_paired_transform',frozen/'transform.py').transform
        lexical=module('fixed_existing_tokens',frozen/'engines/scripts/minify.py')
        keywords=module('fixed_existing_keyword_domain',frozen/'engines/scripts/rename_c.py')._KEYWORDS
        literal=module('fixed_source_literal',frozen/'engines/compact/tiny-a/pack_stream.py').source_literal
        decoder=module('fixed_strict_decode',frozen/'engines/experiments/tiny-source-codec/decode.py')
        prepared={}
        # Verify every exact control and source relation before any compiler starts.
        for family,case in recipe['families'].items():
            baseline={}
            for role,item in case['baseline_files'].items():
                data=Path(item['path']).read_bytes()
                need((len(data),sha(data))==(item['bytes'],item['sha256']),'current control differs: '+family+'/'+role)
                baseline[role]=data
            canonical=ordinary[case['canonical_path']]
            need(case['semantic_domain']['PLY']==128 and case['semantic_domain']['MATE']==30000 and
                 b'#define PLY 128\n' in canonical and b'#define MATE 30000\n' in canonical,'fixed score/profile domain differs')
            readable,source,proof=mutate(canonical,baseline['source'],case,lexical._tokens,keywords)
            directory=out/family;directory.mkdir();(directory/'readable.c').write_bytes(readable)
            (directory/'main.c').write_bytes(source);save(directory/'source.json',proof)
            template=ordinary[case['template']];prefix=ordinary[case['prefix']];marker=b'__ROVE_SOURCE_LITERAL__'
            need(template.count(marker)==1 and len(prefix)==77,'fixed bootstrap boundary differs')
            old_expression,_=literal(baseline['source'])
            need(template.replace(marker,old_expression.encode())==baseline['bootstrap'],
                 'current source/template does not reproduce exact baseline bootstrap')
            need(baseline['whole'].startswith(prefix),'fixed launcher differs')
            prepared[family]=(source,template,prefix,directory)
            report['families'][family]={'source':proof,'baseline':case['baseline_files'],
                'C_AST_runs':0,'native_compiles':0,'codec_compressions':0,'runtime_qualified':False}
        save(out/'cost.json',report)
        for family,case in recipe['families'].items():
            source,template,prefix,directory=prepared[family];row=report['families'][family]
            native_dir=directory/'native';native_dir.mkdir();report['native_compiles']+=1;row['native_compiles']=1
            save(out/'cost.json',report);compiled=run(case['compiler'],native_dir,source)
            native=(native_dir/'x').read_bytes()
            row['native']={'bytes':len(native),'sha256':sha(native),'command':compiled['command'],
                           'full_equal_to_control':sha(native)==case['expected']['native_sha256'],
                           'metadata_difference_exception':False}
            if family=='C':
                dis=run(['objdump','-d','-M','intel',str(native_dir/'x')])['stdout']
                (directory/'disassembly.txt').write_text(dis)
                need('vpgatherdd' in dis and dis.count('vphaddd')>=2,'actual C SIMD instructions missing')
                row['actual_AVX2_disassembly']={'vpgatherdd':dis.count('vpgatherdd'),'vphaddd':dis.count('vphaddd')}
            expression,_=literal(source);script=template.replace(b'__ROVE_SOURCE_LITERAL__',expression.encode())
            settings=case['compression'];need(settings['format']=='lzma-alone','fixed ALONE recipe required')
            report['codec_compressions']+=1;row['codec_compressions']=1;save(out/'cost.json',report)
            payload=lzma.compress(script,format=lzma.FORMAT_ALONE,check=lzma.CHECK_NONE,
                filters=[{'id':lzma.FILTER_LZMA1,'preset':9|lzma.PRESET_EXTREME,'lc':2,'lp':0,'pb':0,
                          'mf':lzma.MF_BT4,'dict_size':67108864,'nice_len':settings['nice_len']}])
            whole=prefix+payload;(directory/'bootstrap.py').write_bytes(script);(directory/'x').write_bytes(whole)
            proof=decoder.verify(whole,prefix,source,case['compiler'],script,expected_format='alone')
            save(directory/'decode.json',proof)
            row.update(whole={'bytes':len(whole),'sha256':sha(whole)},
                bootstrap={'bytes':len(script),'sha256':sha(script)},source_bytes=len(source),source_sha256=sha(source),
                whole_delta=len(whole)-case['expected']['whole_bytes'],
                native_delta=len(native)-case['expected']['native_bytes'],strict_decode=True,
                next_action='await root functional follow-up' if len(whole)<case['expected']['whole_bytes'] else 'tie/loss; stop')
            save(out/'cost.json',report)
            print(json.dumps({'family':family,'source_bytes':len(source),'native':row['native'],
                              'whole':row['whole'],'whole_delta':row['whole_delta']}),flush=True)
        report['complete']=True;save(out/'cost.json',report)
    except BaseException as error:
        report['failure']={'type':type(error).__name__,'message':str(error)};save(out/'cost.json',report);raise
    finally:
        signal.signal(signal.SIGTERM,previous)


if __name__=='__main__':main()
