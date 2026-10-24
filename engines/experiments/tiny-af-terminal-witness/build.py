"""Single-family fixed first cost; never executes the produced engine/wrapper."""
import argparse
import hashlib
import importlib.util
import json
import lzma
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
OWNED=('.gitattributes','profile.py','recipe.json','build.py','README.md')


def sha(raw):return hashlib.sha256(raw).hexdigest()
def need(ok,message):
    if not ok:raise ValueError(message)
def write_json(path,value):path.write_bytes((json.dumps(value,indent=2)+'\n').encode())


def members(group):
    result=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdecimal():continue
        try:
            fields=(p/'stat').read_text().rsplit(')',1)[1].split()
            if int(fields[2])==group:result.append({'pid':int(p.name),'state':fields[0]})
        except (FileNotFoundError,ProcessLookupError,PermissionError):pass
    return result


def run(command,stdin,cwd,out,label,rows,timeout):
    def limits():
        resource.setrlimit(resource.RLIMIT_CORE,(0,0))
        resource.setrlimit(resource.RLIMIT_CPU,(60,60))
        resource.setrlimit(resource.RLIMIT_AS,(1073741824,1073741824))
    row={'label':label,'command':command,'cwd':str(cwd),'stdin_bytes':len(stdin),'stdin_sha256':sha(stdin),'terminal':False,'group_absent':False,'cleanup':[]};rows.append(row)
    p=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=cwd,start_new_session=True,preexec_fn=limits,env={**os.environ,'LC_ALL':'C','TZ':'UTC'})
    row['pid']=p.pid;stdout=stderr=b'';error=None
    try:stdout,stderr=p.communicate(stdin,timeout=timeout)
    except BaseException as caught:error=caught
    finally:
        # Process ownership settles before any fallible output/log writes.
        for sig,grace in ((signal.SIGTERM,3),(signal.SIGKILL,3)):
            if p.poll() is not None and not members(p.pid):break
            row['cleanup'].append(int(sig))
            if error is None:error=RuntimeError(label+' required owned descendant cleanup')
            try:os.killpg(p.pid,sig)
            except ProcessLookupError:pass
            except BaseException as caught:row.setdefault('cleanup_errors',[]).append(repr(caught))
            try:stdout,stderr=p.communicate(timeout=grace)
            except subprocess.TimeoutExpired:pass
            except BaseException as caught:row.setdefault('cleanup_errors',[]).append(repr(caught))
            until=time.monotonic()+grace
            while members(p.pid) and time.monotonic()<until:time.sleep(.02)
        row.update(returncode=p.poll(),terminal=p.poll() is not None,group_absent=not members(p.pid),stdout_sha256=sha(stdout),stderr_sha256=sha(stderr))
        for suffix,data in (('stdout',stdout),('stderr',stderr)):
            try:(out/(label+'.'+suffix)).write_bytes(data)
            except BaseException as caught:
                row.setdefault('logging_errors',[]).append(repr(caught))
                if error is None:error=caught
    if error is not None:raise error.with_traceback(error.__traceback__)
    need(row['returncode']==0 and row['terminal'] and row['group_absent'],label+' failed or live group')
    need(not stderr,label+' stderr')
    return stdout


def source_literal(source):
    # Exact existing pack_stream.source_literal algorithm; no AST/eval.
    try:text=source.decode('utf-8')
    except UnicodeDecodeError:return repr(source),'bytes-repr'
    trailing=len(text)-len(text.rstrip('\\'))
    if '\r' not in text and '\0' not in text and not trailing%2:
        for quote,kind in (("'"*3,'raw-single'),('"'*3,'raw-double')):
            if quote not in text and not text.endswith(quote[0]):return 'r'+quote+text+quote+'.encode()',kind
    return repr(source),'bytes-repr'


def script_for(source,template,command):
    marker=b'__ROVE_SOURCE_LITERAL__';need(template.count(marker)==1,'template marker')
    expression,kind=source_literal(source);need(kind=='raw-single','fixed current raw-single literal domain')
    script=template.replace(marker,expression.encode())
    left,right=template.split(marker);need(script.startswith(left) and script.endswith(right),'script exact template')
    body=script[len(left):len(script)-len(right)]
    quote=b"'"*3
    need(body.startswith(b'r'+quote) and body.endswith(quote+b'.encode()'),'literal delimiters')
    restored=body[4:-12];need(restored==source,'literal strict source restoration')
    argv=('p=subprocess.Popen('+repr(' '.join(command))+'.split(),cwd=d,').encode()
    need(template.count(argv)==1,'fixed compiler argv template relationship')
    return script,{'literal':kind,'source_recovered_exact':True,'compiler_argv_recovered_exact':True,'AST':0,'eval':0}


def main():
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('--family',choices=('A','F'),required=True);cli.add_argument('--out',type=Path,required=True)
    args=cli.parse_args();out=args.out
    need(sys.platform=='linux' and out.is_absolute() and not out.exists() and not any((p/'.git').exists() for p in (out,*out.parents)),'new absolute output outside Git required')
    out.mkdir(parents=True);frozen=out/'producer';frozen.mkdir()
    report={'complete':False,'family':args.family,'stage':'first cost only; produced native/wrapper not executed','commands':[],'native_compiles':0,'codec_encodes':0,'AST':0,'PP':0,'baseline_compiles':0,'baseline_copies':0,'engine_runs':0,'wrapper_runs':0,'functional_claim':False,'normal_promotion':False}
    def save():write_json(out/'results.json',report)
    save()
    try:
        own={}
        for n in OWNED:
            raw=(HERE/n).read_bytes();need(b'\r' not in raw,'owned source must be LF');(frozen/n).write_bytes(raw);own[n]={'bytes':len(raw),'sha256':sha(raw)}
        report['producer_inputs']=own
        full=json.loads((frozen/'recipe.json').read_bytes());config=full['families'][args.family]
        report['proposal_sha256']=full['proposal_sha256'];bindings={}
        for rel,expected in config['ordinary_bindings'].items():
            raw=(REPO/rel).read_bytes();need({'bytes':len(raw),'sha256':sha(raw)}==expected,'ordinary source binding '+rel);bindings[rel]=expected
        report['ordinary_source_bindings']=bindings
        current=json.loads((REPO/('engines/compact/tiny-entry-'+args.family.lower()+'/recipe.json')).read_bytes())
        need(current['compiler']==config['compiler'] and current['profile']==config['profile'] and current['compression']==config['compression'],'fixed current command/profile/codec')
        baseline=Path(config['baseline']);controls={}
        for n,expected in config['controls'].items():
            raw=(baseline/n).read_bytes();need({'bytes':len(raw),'sha256':sha(raw)}==expected,'actual baseline '+n);controls[n]=raw
        report['baseline']={'path':str(baseline),'controls':config['controls'],'copied':False,'recompiled':False}
        template=(REPO/('engines/compact/tiny-entry-'+args.family.lower()+'/bootstrap.py.in')).read_bytes()
        prefix=(REPO/('engines/compact/tiny-entry-'+args.family.lower()+'/launcher.sh')).read_bytes()
        need(len(prefix)==77 and controls['x'].startswith(prefix),'fixed77B prefix')
        baseline_script,_=script_for(controls['main.c'],template,config['compiler'])
        need(baseline_script==controls['bootstrap.py'],'same existing source-literal/template recipe')
        spec=importlib.util.spec_from_file_location('frozen_terminal_witness',frozen/'profile.py');profile=importlib.util.module_from_spec(spec);spec.loader.exec_module(profile)
        source,proof=profile.transform(controls['main.c'],config)
        need({'bytes':len(source),'sha256':sha(source)}==config['candidate_source'],'fixed sole candidate source')
        (out/'main.c').write_bytes(source);report['transform']=proof;report['source']={'bytes':len(source),'sha256':sha(source)};save()
        native_dir=out/'native';native_dir.mkdir();report['native_compiles']=1;save()
        run(config['compiler'],source,native_dir,out,'compiler',report['commands'],90)
        native=(native_dir/'x').read_bytes();report['native']={'bytes':len(native),'sha256':sha(native),'same_full_SHA_as_baseline':sha(native)==config['controls']['native/x']['sha256']};save()
        script,restoration=script_for(source,template,config['compiler']);(out/'bootstrap.py').write_bytes(script)
        filters={'id':lzma.FILTER_LZMA1,'preset':9|lzma.PRESET_EXTREME,'lc':2,'lp':0,'pb':0}
        if args.family=='F':filters.update(mf=lzma.MF_BT4,dict_size=67108864,nice_len=32)
        report['codec_encodes']=1;save();payload=lzma.compress(script,format=lzma.FORMAT_ALONE,check=lzma.CHECK_NONE,filters=[filters])
        need(payload[:13]==bytes.fromhex('0200000004ffffffffffffffff'),'same ALONE header')
        decode=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE);restored=decode.decompress(payload)
        need(restored==script and decode.eof and not decode.unused_data,'strict ALONE decode')
        cli_decoded=run(['lzma','-dc'],payload,out,out,'decode',report['commands'],15);need(cli_decoded==script,'independent CLI decode')
        whole=prefix+payload;(out/'x').write_bytes(whole);(out/'x').chmod(0o755)
        report.update(bootstrap={'bytes':len(script),'sha256':sha(script)},whole={'bytes':len(whole),'sha256':sha(whole)},restoration=restoration,prefix_bytes=len(prefix),payload_bytes=len(payload),source_delta=len(source)-config['controls']['main.c']['bytes'],native_delta=len(native)-config['controls']['native/x']['bytes'],whole_delta=len(whole)-config['controls']['x']['bytes'],complete=True,all_commands_terminal=True,live_handles=0)
        save();print(json.dumps({'family':args.family,'source':report['source'],'native':report['native'],'whole':report['whole'],'source_delta':report['source_delta'],'native_delta':report['native_delta'],'whole_delta':report['whole_delta'],'engine_runs':0,'live_handles':0}))
    except BaseException as error:
        report['complete']=False;report['error']={'type':type(error).__name__,'message':str(error)}
        try:save()
        except BaseException:pass
        raise

if __name__=='__main__':main()
