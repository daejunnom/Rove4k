"""One signed8 actual-state/SIMD fixture; frozen DEV receipt is ancestry only."""
import argparse,json,os,re,signal,subprocess
from pathlib import Path
from cost import HERE,ROOT,sha,identity,transform
REFERENCE=Path('/home/stemxstudio/rove4k-c-incremental-vector-focused-20261021/focused.json')
REFERENCE_SHA='2b52cd2d9ec912d3a74b90c61622eb886c616258c2bd0f9595e9ee5e78cb1046'
def need(good,message):
    if not good:raise ValueError(message)
def pin(data):return {'bytes':len(data),'sha256':sha(data)}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--control-dir',type=Path,required=True);p.add_argument('--cost',type=Path,required=True);a=p.parse_args()
    out=a.out.resolve();control=a.control_dir.resolve();first=a.cost.resolve()
    need(a.out.is_absolute()and not out.exists()and not any((q/'.git').exists()for q in(out,*out.parents)),'fresh absolute nonGit output required')
    cfg=json.loads((HERE/'config.json').read_text());receipt=json.loads((first/'cost.json').read_text())
    need(receipt['complete']and receipt['result']=='gain','positive first cost required')
    candidate=(first/'main.c').read_bytes();old=(control/'main.c').read_bytes();identity(candidate,cfg['candidate'],'source');identity(old,cfg['baseline'],'source');need(transform(old)==candidate,'candidate exact regeneration differs')
    reference_raw=REFERENCE.read_bytes();need(sha(reference_raw)==REFERENCE_SHA,'frozen DEV reference receipt changed');reference=json.loads(reference_raw)
    dev=(control/'dev/main.c').read_bytes();need(sha(dev)==reference['sources']['dev.c']['sha256']=='c6497c472b243b03cb19ab727b42a189a8be556d818e39d9bf7b74684daaa140','frozen unchanged DEV source identity differs')
    watched={q:q.read_bytes()for q in HERE.iterdir()if q.is_file()};out.mkdir()
    report={'complete':False,'fixture_compiles':0,'fixture_runs':0,'new_DEV_compiles_runs':0,'frozen_DEV_reference':{'path':str(REFERENCE),'sha256':REFERENCE_SHA,'scope':'old actual reference only; not a new execution or new layout proof'},'codec_runs':0,'full_engine_sessions':0,'active_processes':0,'old_layout_SIMD_proof_inherited':False}
    def save():(out/'focused.json').write_text(json.dumps(report,indent=2)+'\n')
    def run(argv,timeout=60):
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
        signature=b'static int U(const za*p){';need(candidate.count(signature)==1,'actual U unique definition required')
        replacement=b'static int U(const za*p);static int shipping_U(const za*p){';instrumented=candidate.replace(signature,replacement,1);need(instrumented.replace(replacement,signature,1)==candidate,'definition-name-only inverse differs')
        (out/'candidate-check.c').write_bytes(instrumented);(out/'fixture.c').write_bytes((HERE/'check.c').read_bytes())
        report['sources']={name:pin(data)for name,data in [('candidate.c',candidate),('candidate-check.c',instrumented),('fixture.c',(HERE/'check.c').read_bytes()),('executed-check.py',(HERE/'check.py').read_bytes())]}
        report['compiler_version']=subprocess.check_output(['cc','--version'],text=True).splitlines()[0];meta=json.loads((control/'build.json').read_text());need(report['compiler_version']==meta['tools']['cc'],'qualified compiler differs')
        report['production_native_observations']={}
        for label,binary in [('control',control/'native/x'),('candidate',first/'native/x')]:
            need(pin(binary.read_bytes())=={'bytes':receipt['baseline'if label=='control'else'candidate']['native_bytes'],'sha256':receipt['baseline'if label=='control'else'candidate']['native_sha256']},'actual native image identity differs')
            text=subprocess.check_output(['objdump','-d','--no-show-raw-insn','--disassemble=P',str(binary)],text=True);(out/(label+'-P.asm')).write_text(text)
            body=text.split('<P>:',1)[-1];prologue=body.split('call',1)[0];fragments=re.findall(r'sub\s+\$0x([0-9a-f]+),%rsp',prologue)
            row={'native':pin(binary.read_bytes()),'P_static_stack_allocation':sum(int(v,16)for v in fragments)if fragments else None,'allocation_fragments_hex':fragments,'prologue_push_count':len(re.findall(r'\bpush\b',prologue)),'alignment_masks':re.findall(r'and\s+\$([^,]+),%rsp',prologue)}
            if label=='candidate':
                vector=[line.strip()for line in body.splitlines()if any(op in line for op in('vpmaddwd','vphaddd','vmovdqu','vmovdqa'))]
                row['actual_vector_lines']=vector;row['XMM_madd_and_two_horizontal']=any('vpmaddwd'in s and'%xmm'in s and'%ymm'not in s for s in vector)and sum('vphaddd'in s for s in vector)>=2
                row['intrinsic_minimum_ISA']='SSE2 madd + SSSE3 hadd';row['fixed_compiler_flag']='-mavx2';row['leaf_width_bits']=128
            report['production_native_observations'][label]=row
        argv=['cc','-std=c11','-O1','-g','-pthread','-mavx2','-DWORKERS=2','-DTT_BITS=18','-DDEV=0','-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer','-no-pie','fixture.c','-o','fixture']
        report['fixture_compiles']=1;report['compiler_argv']=argv;rc,stdout,stderr=run(argv);(out/'compile.stdout').write_bytes(stdout);(out/'compile.stderr').write_bytes(stderr);need(rc==0,'signed8 fixture compile failed')
        report['fixture_runs']=1;rc,stdout,stderr=run([str(out/'fixture')],30);(out/'fixture.stdout').write_bytes(stdout);(out/'fixture.stderr').write_bytes(stderr);need(rc==0,'signed8 fixture run failed')
        results=[json.loads(line)for line in stdout.decode().splitlines()];need(results[-1]['pass'],'fixture result missing')
        for kind in('case','search'):
            need([q for q in results if q['kind']==kind]==[q for q in reference['results']['dev']if q['kind']==kind],'signed8/frozen exact DEV '+kind+' differs')
        need(report['production_native_observations']['candidate']['XMM_madd_and_two_horizontal'],'actual production SIMD observation incomplete')
        for q,data in watched.items():need(q.read_bytes()==data,'ordinary experiment input drift')
        need((first/'main.c').read_bytes()==candidate and(control/'main.c').read_bytes()==old,'actual source drift')
        report.update(complete=True,results=results,actual_U_body_retained=True,actual_H_K_state_used=True,actual_P_consumes_checked_U=True,independent_mailbox_hash_scalar_old16_signed8_oracles=True,all8_lanes_including_zero_king_and_padding_checked=True,frozen_DEV_case_search_score_best_nodes_equal=True,source_inputs_unchanged=True)
    except BaseException as error:report['error']=repr(error);raise
    finally:save()
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
