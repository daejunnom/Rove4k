"""One C residual-dot native, then one fixed whole after explicit codegen review."""
import argparse,hashlib,importlib.util,json,lzma,os,platform,re,signal,subprocess,sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
def sha(data):return hashlib.sha256(data).hexdigest()
def save(path,obj):path.write_text(json.dumps(obj,indent=2)+'\n')
def need(value,message):
    if not value:raise ValueError(message)
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,type=Path);parser.add_argument('--pack',action='store_true');args=parser.parse_args();out=args.out.resolve()
    need(args.out.is_absolute() and not any((p/'.git').exists() for p in (out,*out.parents)),'absolute output outside Git required')
    need(sys.platform=='linux' and platform.machine()=='x86_64','qualified Linux x86-64 target')
    if args.pack:return pack(out)
    need(not out.exists(),'new native output required');out.mkdir();frozen=out/'inputs';frozen.mkdir()
    recipe=json.loads((HERE/'recipe.json').read_bytes())
    report={'complete':False,'scope':recipe['scope'],'native_compiles':0,'codec_compressions':0,'baseline_compiles':0,'baseline_copies':0,'C_AST':0,'preprocessor_commands':0,'engine_runs':0,'games':0,'benchmarks':0,'inputs':{},'control':{},'stage':'preparation'}
    save(out/'cost.json',report)
    try:
        for name in ('build.py','transform.py','recipe.json'):
            data=(HERE/name).read_bytes();(frozen/name).write_bytes(data);report['inputs'][name]={'bytes':len(data),'sha256':sha(data)}
        ordinary={}
        for relative,pin in recipe['tracked_inputs'].items():
            raw=(REPO/relative).read_bytes();data=raw.replace(b'\r\n',b'\n')
            need(b'\r' not in data and sha(data)==pin,'tracked input drift: '+relative);ordinary[relative]=data
            report['inputs'][relative]={'bytes':len(data),'sha256':sha(data),'raw_sha256':sha(raw)}
            if relative not in ('engines/compact/tiny-entry-c/engine.c','engines/compact/tiny-entry-c/recipe.json'):
                target=frozen/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        control={}
        for name,row in recipe['control'].items():
            data=Path(row['path']).read_bytes();need(len(data)==row['bytes'] and sha(data)==row['sha256'],'exact control drift: '+name)
            control[name]=data;report['control'][name]=row
        lex=module('dot_existing_tokens',frozen/'engines/scripts/minify.py');keywords=module('dot_existing_keywords',frozen/'engines/scripts/rename_c.py')._KEYWORDS
        transform=module('dot_fixed_transform',frozen/'transform.py').transform
        readable,source,proof=transform(ordinary['engines/compact/tiny-entry-c/engine.c'],control['source'],recipe,lex._tokens,keywords)
        (out/'readable.c').write_bytes(readable);(out/'main.c').write_bytes(source);save(out/'source.json',proof)
        report.update(source_bytes=len(source),source_sha256=sha(source),readable_sha256=sha(readable),source_proof_sha256=sha((out/'source.json').read_bytes()),stage='native')
        save(out/'cost.json',report)
        directory=out/'native';directory.mkdir();process=None
        def cancelled(signum,frame):raise TimeoutError('bounded native cost cancelled')
        previous=signal.signal(signal.SIGTERM,cancelled)
        try:
            mask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGTERM})
            try:
                process=subprocess.Popen(recipe['compiler'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=directory,start_new_session=True,preexec_fn=lambda:signal.pthread_sigmask(signal.SIG_SETMASK,mask))
            finally:signal.pthread_sigmask(signal.SIG_SETMASK,mask)
            report['native_compiles']=1;save(out/'cost.json',report)
            stdout,stderr=process.communicate(source,timeout=60)
            (directory/'compiler.stdout').write_bytes(stdout);(directory/'compiler.stderr').write_bytes(stderr)
            save(directory/'compile.json',{'command':recipe['compiler'],'cwd':str(directory),'returncode':process.returncode,'stdin_sha256':sha(source)})
            need(process.returncode==0,'candidate compiler failed; no retry')
        finally:
            if process is not None:
                try:os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                if process.poll() is None:process.wait(timeout=3)
            signal.signal(signal.SIGTERM,previous)
        native=(directory/'x').read_bytes();report['native']={'bytes':len(native),'sha256':sha(native),'equal_to_control':native==control['native'],'metadata_exception':False}
        disassembled=subprocess.run(['objdump','-drw','-Mintel',str(directory/'x')],capture_output=True,timeout=10)
        need(disassembled.returncode==0,'objdump failed');(out/'disassembly.txt').write_bytes(disassembled.stdout)
        text=disassembled.stdout.decode();function='';sites=[]
        for line in text.splitlines():
            label=re.match(r'^[0-9a-f]+ <([^>]+)>:',line)
            if label:function=label.group(1)
            if re.search(r'\bvpmaddwd\s+ymm',line):sites.append({'function':function,'instruction':line.strip()})
        report['codegen']={'disassembly_sha256':sha(disassembled.stdout),'YMM_vpmaddwd_sites':sites,'return_path_review_pending':True}
        need(sites,'actual YMM signed madd absent; fixed candidate stops without packing')
        report.update(stage='awaiting explicit codegen return-path review',native_stage_complete=True)
        save(out/'cost.json',report);print(json.dumps({'native_stage_complete':True,'out':str(out),'source_bytes':len(source),'native':report['native'],'codegen':report['codegen']}),flush=True)
    except Exception as error:
        report['error']=repr(error);save(out/'cost.json',report);raise

def pack(out):
    frozen=out/'inputs';report=json.loads((out/'cost.json').read_bytes());recipe=json.loads((frozen/'recipe.json').read_bytes())
    try:
        need(report.get('native_stage_complete') and report['native_compiles']==1 and report['codec_compressions']==0 and not report.get('error'),'single completed native awaiting pack required')
        for name in ('build.py','transform.py','recipe.json'):
            need(sha((HERE/name).read_bytes())==report['inputs'][name]['sha256'],'producer source changed before single pack')
        unused_at_pack={'engines/compact/tiny-entry-c/engine.c','engines/compact/tiny-entry-c/recipe.json'}
        for name,row in report['inputs'].items():
            if name in unused_at_pack:continue
            data=(frozen/name).read_bytes()
            need(len(data)==row['bytes'] and sha(data)==row['sha256'],'frozen pack input drift: '+name)
        source=(out/'main.c').read_bytes();native=(out/'native/x').read_bytes();assembly=(out/'disassembly.txt').read_bytes()
        need(sha(source)==recipe['candidate']['source_sha256'] and sha(native)==report['native']['sha256'] and sha(assembly)==report['codegen']['disassembly_sha256'],'measured inputs drifted')
        admission=json.loads((out/'codegen-admission.json').read_bytes())
        need(admission['clear'] is True and admission['native_sha256']==sha(native) and admission['disassembly_sha256']==sha(assembly) and admission['actual_YMM_return_path'] is True,'explicit exact native return-path admission missing')
        literal=module('dot_fixed_literal',frozen/'engines/compact/tiny-a/pack_stream.py').source_literal
        decode=module('dot_fixed_decode',frozen/'engines/experiments/tiny-source-codec/decode.py').verify
        template=(frozen/'engines/compact/tiny-entry-c/bootstrap.py.in').read_bytes();prefix=(frozen/'engines/compact/tiny-entry-c/launcher.sh').read_bytes()
        need(template.count(b'__ROVE_SOURCE_LITERAL__')==1 and len(prefix)==77,'fixed transport changed')
        expression,_=literal(source);script=template.replace(b'__ROVE_SOURCE_LITERAL__',expression.encode())
        report['codec_compressions']=1;save(out/'cost.json',report)
        whole=prefix+lzma.compress(script,format=lzma.FORMAT_ALONE,check=lzma.CHECK_NONE,filters=[{'id':lzma.FILTER_LZMA1,'preset':9|lzma.PRESET_EXTREME,'lc':2,'lp':0,'pb':0,'mf':lzma.MF_BT4,'dict_size':67108864,'nice_len':64}])
        proof=decode(whole,prefix,source,recipe['compiler'],script,expected_format='alone')
        (out/'x').write_bytes(whole);(out/'bootstrap.py').write_bytes(script);save(out/'decode.json',proof)
        report.update(complete=True,stage='first cost terminal; no functional qualification',whole={'bytes':len(whole),'sha256':sha(whole)},bootstrap={'bytes':len(script),'sha256':sha(script)},whole_delta=len(whole)-recipe['control']['whole']['bytes'],native_delta=len(native)-recipe['control']['native']['bytes'],codegen_admission_sha256=sha((out/'codegen-admission.json').read_bytes()),strict_decode_sha256=sha((out/'decode.json').read_bytes()),runtime_qualified=False,normal_promotion=False,under_4096_bytes=len(whole)<=4096)
        report['codegen']['return_path_review_pending']=False
        report['next_action']='stop on tie/loss; otherwise await separate root functional GO'
        save(out/'cost.json',report);print(json.dumps({'complete':True,'out':str(out),'source_bytes':len(source),'native':report['native'],'whole':report['whole'],'whole_delta':report['whole_delta'],'native_delta':report['native_delta'],'cost_sha256':sha((out/'cost.json').read_bytes())}),flush=True)
    except Exception as error:
        report['error']=repr(error);save(out/'cost.json',report);raise

if __name__=='__main__':main()