"""One focused actual E19 source fixture; no normal build or engine sessions."""
import argparse,hashlib,importlib.util,json,os,re,signal,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
def pin(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def need(value,message):
    if not value:raise ValueError(message)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cost',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    out=a.out.resolve();need(a.out.is_absolute()and not out.exists()and not any((x/'.git').exists()for x in(out,*out.parents)),'fresh absolute nonGit output required')
    cfg=json.loads((HERE/'recipe.json').read_text());base=Path(cfg['actual_cost_baseline']);cost=json.loads((a.cost/'cost.json').read_text())
    need(cost['complete']and cost['whole_delta_from_E5281']<0,'positive first cost required')
    candidate=(a.cost/'main.c').read_bytes();control=(base/'main.c').read_bytes();need(pin(candidate)==cfg['output_pin']and pin(control)==cfg['actual_cost_baseline_pins']['main.c'],'actual source identity differs')
    spec=importlib.util.spec_from_file_location('e19_check_transform',HERE/'transform.py');transform=importlib.util.module_from_spec(spec);spec.loader.exec_module(transform);need(transform.transform(control)[0]==candidate,'candidate regeneration differs')
    readable=(HERE/'model19.h').read_bytes()
    uncommented=re.sub(rb'/\*.*?\*/',b'',readable,flags=re.S)
    actual_fragment=transform.PAIRS[1][1]+transform.PAIRS[4][1]
    need(re.sub(rb'\s+',b'',uncommented)==re.sub(rb'\s+',b'',actual_fragment),'readable model bodies differ from actual shipping token bodies')
    watched={x:x.read_bytes()for x in HERE.iterdir()if x.is_file()}
    out.mkdir();report={'complete':False,'fixture_compiles':0,'fixture_runs':0,'active_processes':0,'full_engine_sessions':0,'codec_runs':0,'old_DEV_model_layout_proof_inherited':False,'model':cfg['model']}
    def save():(out/'focused.json').write_text(json.dumps(report,indent=2)+'\n')
    def run(argv,timeout=40):
        process=subprocess.Popen(argv,cwd=out,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True);report['active_processes']=1;save()
        try:stdout,stderr=process.communicate(timeout=timeout)
        except BaseException:
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            stdout,stderr=process.communicate();raise
        finally:report['active_processes']=int(process.poll()is None)
        try:os.killpg(process.pid,0);raise ValueError('owned process group remains')
        except ProcessLookupError:pass
        return process.returncode,stdout,stderr
    try:
        instrumented=candidate
        for name in ('S','R'):
            old=('static int '+name+'(const za*p'+(''if name=='S'else',Move m')+'){').encode()
            new=old[:-1]+b';'+old.replace(('int '+name+'(').encode(),('int shipping_'+name+'(').encode())
            need(instrumented.count(old)==1,'unique actual definition required');instrumented=instrumented.replace(old,new,1)
        (out/'candidate-check.c').write_bytes(instrumented);(out/'check.c').write_bytes((HERE/'check.c').read_bytes())
        report['source_pins']={name:pin(data)for name,data in [('candidate.c',candidate),('candidate-check.c',instrumented),('check.c',(HERE/'check.c').read_bytes()),('model19.h',(HERE/'model19.h').read_bytes())]}
        report['compiler_version']=subprocess.check_output(['cc','--version'],text=True).splitlines()[0]
        meta=json.loads((base/'build.json').read_text());need(report['compiler_version']==meta['tools']['cc'],'actual control compiler identity differs')
        report['native_frames']={}
        for label,binary in [('control',base/'native/x'),('candidate',a.cost/'native/x')]:
            asm=subprocess.check_output(['objdump','-d','--disassemble=M',str(binary)],text=True);(out/(label+'-M.asm')).write_text(asm)
            prefix=asm.split('>:',1)[-1].split('%fs:0x28',1)[0]
            allocation=re.findall(r'sub\s+\$(0x[0-9a-f]+),%rsp',prefix)
            total=sum(int(x,16)for x in allocation)
            release=re.findall(r'add\s+\$(0x[0-9a-f]+),%rsp',asm)
            known=bool(allocation)and all(int(x,16)==total for x in release)and bool(release)
            report['native_frames'][label]={'native':pin(binary.read_bytes()),'M_static_stack_allocation':total if known else None,'allocation_fragments':allocation,'matching_epilogue':known,'push_count':len(re.findall(r'\bpush\b',prefix))}
        argv=['cc','-std=c11','-O1','-g','-pthread','-DWORKERS=2','-DTT_BITS=18','-DDEV=0','-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer','-no-pie','check.c','-o','check']
        report['fixture_compiles']=1;report['compiler_argv']=argv;rc,stdout,stderr=run(argv);(out/'compile.stdout').write_bytes(stdout);(out/'compile.stderr').write_bytes(stderr);need(rc==0,'focused fixture compile failed')
        report['fixture_runs']=1;rc,stdout,stderr=run([str(out/'check')],30);(out/'check.stdout').write_bytes(stdout);(out/'check.stderr').write_bytes(stderr);need(rc==0,'focused fixture failed')
        lines=[json.loads(line)for line in stdout.decode().splitlines()];need(lines[-1]['pass']and lines[-1]['actual_leaf_calls']>0 and lines[-1]['actual_order_calls']>0,'actual model consumers absent')
        for path,data in watched.items():need(path.read_bytes()==data,'ordinary experiment input drift')
        need((a.cost/'main.c').read_bytes()==candidate and(base/'main.c').read_bytes()==control,'actual source input drift')
        report.update(complete=True,results=lines,actual_S_R_bodies_retained=True,actual_search_consumes_checked_model=True,independent_board_hash_model_order_oracles=True,private_state_and_special_moves=True,source_static_EP_scratch_non_escape_review=True,source_inputs_unchanged=True)
    except BaseException as error:report['error']=repr(error);raise
    finally:save()
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
