"""Bounded standalone subreaper experiment; fixtures are not Rove4k engines."""
import argparse,ast,ctypes,hashlib,importlib.util,json,os,resource,shutil,signal,subprocess,sys,time
from pathlib import Path

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]


def pin(data):return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result);return result


PORT=r'''import builtins,ctypes,json,os,shutil,signal,subprocess,sys,time
from pathlib import Path
wrapper=Path(sys.argv[1]);mode=sys.argv[2];root=Path(sys.argv[3]);sys.argv=[str(wrapper),'engine','argument']
events=root/'events.jsonl';namespace={};children=[];latest={};patched=False;setup=False
def emit(event,**data):
 with events.open('a')as f:f.write(json.dumps({'event':event,**data})+'\n')
lib=ctypes.CDLL(None,use_errno=True);real_pr=lib.prctl
real_pr.argtypes=ctypes.c_int,ctypes.c_void_p,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_ulong
old=ctypes.c_int();assert real_pr(37,ctypes.byref(old),0,0,0)==0
if mode=='old1':assert real_pr(36,1,0,0,0)==0
real_cdll=ctypes.CDLL
def CDLL(*args,**kwargs):
 library=real_cdll(*args,**kwargs)
 class Proxy:pass
 result=Proxy()
 def pr(n,a,*rest):
  global setup
  if n==36 and a==1 and not setup:
   if mode=='setup_error':ctypes.set_errno(1);emit('prctl_refused',phase='setup');return -1
   setup=True
  elif n==36 and setup and mode=='restore_error':
   ctypes.set_errno(1);emit('prctl_refused',phase='restore');return -1
  value=real_pr(n,a,*rest);emit('prctl',option=n,result=value)
  return value
 result.prctl=pr;return result
ctypes.CDLL=CDLL
real_Popen=subprocess.Popen
def Popen(*args,**kwargs):
 emit('spawn_attempt',argv=args[0])
 child=real_Popen(*args,**kwargs);children.append(child);emit('compiler',pid=child.pid,pgid=os.getpgid(child.pid));return child
subprocess.Popen=Popen
real_waitpid=os.waitpid
def waitpid(pid,options):
 blocked={int(x)for x in signal.pthread_sigmask(signal.SIG_BLOCK,set())}
 if pid<0:assert {2,15}<=blocked
 try:result=real_waitpid(pid,options)
 except ChildProcessError:
  latest[-pid]='ECHILD';emit('raw_wait',group=-pid,result='ECHILD',blocked=sorted(blocked));raise
 latest[-pid]=result[0];emit('raw_wait',group=-pid,pid=result[0],status=result[1],blocked=sorted(blocked));return result
os.waitpid=waitpid
real_killpg=os.killpg
def killpg(pgid,sig):
 assert latest.get(pgid)==0,('signal without fresh owned-child0',pgid,latest)
 emit('signal_group',pgid=pgid,signal=int(sig),last_wait=latest[pgid]);return real_killpg(pgid,sig)
os.killpg=killpg
real_open=builtins.open
def open_source(path,*args,**kwargs):
 if mode=='prepare_error'and str(path).endswith('/c'):
  emit('source_refused',path=str(path));raise OSError('source prepare fixture')
 return real_open(path,*args,**kwargs)
builtins.open=open_source
real_rmtree=shutil.rmtree
def rmtree(path,*args,**kwargs):
 assert all(latest.get(child.pid)=='ECHILD'for child in children)
 emit('directory_cleanup',path=str(path),terminal_ECHILD_for_compilers=[child.pid for child in children])
 return real_rmtree(path,*args,**kwargs)
shutil.rmtree=rmtree
def trace(frame,event,arg):
 global patched
 if not patched and event=='line'and frame.f_code.co_filename==str(wrapper)and 'w'in frame.f_globals:
  patched=True;original=frame.f_globals['w']
  def w(n,g=0):
   if (mode=='leader125'and n==5 and not g)or(mode=='group125'and g):
    actual=original(0,g);emit('injected_deadline',requested=n,group=g,actual=actual);return 0
   return original(n,g)
  if mode in('leader125','group125'):frame.f_globals['w']=w
 return trace
sys.settrace(trace)
try:exec(compile(wrapper.read_bytes(),str(wrapper),'exec'),namespace)
except BaseException as error:
 p=namespace.get('p');d=namespace.get('d');flag=ctypes.c_int();assert real_pr(37,ctypes.byref(flag),0,0,0)==0
 emit('primary',kind=type(error).__name__,code=getattr(error,'code',None),compiler_status=None if p is None else p.returncode,
  d=d,workspace=[str(x)for x in Path(os.environ['TMPDIR']).iterdir()],subreaper=flag.value)
 raise
finally:
 sys.settrace(None);signal.pthread_sigmask(signal.SIG_BLOCK,{2,15})
 # Fault ports may intentionally decline settlement. The fixture owns any
 # remaining direct/adopted children; signal only after a fresh wait result0.
 end=time.monotonic()+5
 for child in children:
  while True:
   try:pid,status=real_waitpid(-child.pid,os.WNOHANG)
   except ChildProcessError:break
   if pid:
    if pid==child.pid:child.returncode=os.waitstatus_to_exitcode(status)
    continue
   emit('fixture_cleanup_signal',pgid=child.pid)
   try:real_killpg(child.pid,9)
   except ProcessLookupError:pass
   if time.monotonic()>end:raise TimeoutError('fixture settlement')
   time.sleep(.005)
 assert real_pr(36,old.value,0,0,0)==0
 emit('fixture_done',owned_remaining=0)
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve()
    if sys.platform!='linux' or not args.out.is_absolute() or out.exists() or REPO in out.parents:
        parser.error('new absolute Linux output outside the checkout required')
    if len(os.sched_getaffinity(0))>2:parser.error('pin the whole campaign to at most two CPUs')
    out.mkdir();frozen=out/'inputs';frozen.mkdir()
    for name,path in {'subreaper.py':HERE/'subreaper.py','compiler_group.py':REPO/'engines/scripts/compiler_group.py',
                      'compiler_stdin.py':REPO/'engines/scripts/compiler_stdin.py',
                      'compiler_seek.py':REPO/'engines/scripts/compiler_seek.py',
                      'test_compiler_group.py':REPO/'engines/scripts/test_compiler_group.py',
                      'test_compiler_stdin.py':REPO/'engines/scripts/test_compiler_stdin.py'}.items():
        (frozen/name).write_bytes(path.read_bytes().replace(b'\r\n',b'\n'))
    sys.path.insert(0,str(frozen))
    import compiler_group as group
    import test_compiler_group as existing
    exp=module('experimental_subreaper',frozen/'subreaper.py')
    run_owned=existing.RuntimeContracts.run_owned
    engine=out/'engine';source=out/'engine.c'
    source.write_text('#include <stdio.h>\n#include <stdlib.h>\n#include <sys/prctl.h>\nint main(int n,char**v){char b[80];int r=-1;if(prctl(PR_GET_CHILD_SUBREAPER,&r,0L,0L,0L))return 71;fgets(b,sizeof b,stdin);printf("%s:%s:%s:%d",v[1],getenv("R4_OWNER_TEST"),b,r);return 17;}\n')
    report={'complete':False,'scope':'experimental subreaper ownership fixtures; no Rove4k engine execution',
        'affinity':sorted(os.sched_getaffinity(0)),'inputs':{p.name:pin(p.read_bytes())for p in frozen.iterdir()},
        'direct_FFI':[],'fixtures':[]}
    def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    save();run_owned(['cc',str(source),'-o',str(engine)],out/'compile')
    # Exercise each emitted ctypes declaration without the event/fault proxy.
    # The observed native program reads the real kernel subreaper flag.
    for abi in ('pointer','ulong'):
        root=out/('direct-'+abi);root.mkdir();scratch=root/'scratch';scratch.mkdir()
        compiler=root/'compiler.py';compiler.write_text('import shutil,os\nshutil.copyfile('+repr(str(engine))+',"x");os.chmod("x",0o700)\n')
        before=existing.prepared([sys.executable,str(compiler)])
        before,_=group.compact_cleanup(before);before,_=group.compact_private_owner(before)
        product,meta=exp.transform_bootstrap(before,owner=group,abi=abi)
        wrapper=root/'bootstrap.py';wrapper.write_bytes(product)
        output=run_owned([sys.executable,'-B',str(wrapper),'engine','argument'],root/'run',
            env={**os.environ,'TMPDIR':str(scratch),'R4_OWNER_TEST':'env'},expected=17)
        assert output==b'argument:env:input\n:0' and not list(scratch.iterdir())
        report['direct_FFI'].append({'abi':abi,'passed':True,'engine_observed_subreaper':0,
            'whole_fixture_bootstrap':pin(product),'metadata':meta,'owned_remaining':0})
        save()
    cases=[('normal','normal',17),('old1','old1',17),('grandchild','normal',17),('cancel','normal',143),
           ('compiler-error','normal',7),('compiler-signal','normal',241),('prepare-error','prepare_error',1),
           ('spawn-error','normal',1),('setup-error','setup_error',1),('restore-error','restore_error',1),
           ('leader125','leader125',125),('group125','group125',125)]
    try:
        for label,mode,status in cases:
            root=out/label;root.mkdir();scratch=root/'scratch';scratch.mkdir()
            compiler=root/'compiler.py';ready=root/'ready';term=root/'term';grandchild=root/'grandchild'
            body='shutil.copyfile('+repr(str(engine))+',"x");os.chmod("x",0o700)\n'
            if label=='grandchild':
                child=root/'child.py';child.write_text('import os,time\nfrom pathlib import Path\nPath('+repr(str(grandchild))+').write_text(str(os.getpid()))\nwhile True:time.sleep(30)\n')
                body+='subprocess.Popen([sys.executable,'+repr(str(child))+'])\nwhile not Path('+repr(str(grandchild))+').exists():time.sleep(.005)\n'
            if label=='cancel':
                body+='def stop(s,f):\n Path('+repr(str(term))+').write_text(str(s))\n raise SystemExit(0)\nsignal.signal(15,stop)\nPath('+repr(str(ready))+').write_text("ready")\nwhile True:time.sleep(30)\n'
            if label=='compiler-error':body+='raise SystemExit(7)\n'
            if label=='compiler-signal':body+='os.kill(os.getpid(),15)\n'
            compiler.write_text('import os,signal,subprocess,sys,time,shutil\nfrom pathlib import Path\n'+body)
            command=['/unavailable-subreaper-fixture/cc'] if label=='spawn-error' else [sys.executable,str(compiler)]
            prepared=existing.prepared(command)
            selected,_=group.compact_cleanup(prepared)
            selected,_=group.compact_private_owner(selected)
            product,meta=exp.transform_bootstrap(selected,owner=group)
            wrapper=root/'bootstrap.py';wrapper.write_bytes(product);port=root/'port.py';port.write_text(PORT)
            env={**os.environ,'TMPDIR':str(scratch),'R4_OWNER_TEST':'env'}
            output=run_owned([sys.executable,'-B',str(port),str(wrapper),mode,str(root)],root/'run',env=env,
                ready=ready if label=='cancel' else None,expected=status)
            rows=[json.loads(line)for line in (root/'events.jsonl').read_text().splitlines()]
            signals=[r for r in rows if r['event']=='signal_group'];raw=[r for r in rows if r['event']=='raw_wait']
            assert all(r['last_wait']==0 for r in signals)
            assert all({2,15}<=set(r['blocked'])for r in raw)
            if status==17:
                assert output==b'argument:env:input\n:'+str(int(label=='old1')).encode()
                assert not list(scratch.iterdir())
                assert any(r.get('result')=='ECHILD'for r in raw)
            else:
                primary=next(r for r in rows if r['event']=='primary')
                if status==125:
                    assert primary['code']==125 and primary['d'] is None and list(scratch.iterdir())
                else:assert not list(scratch.iterdir())
                kinds={'compiler-error':'SystemExit','compiler-signal':'SystemExit','cancel':'SystemExit',
                    'prepare-error':'OSError','spawn-error':'FileNotFoundError',
                    'setup-error':'PermissionError','restore-error':'PermissionError',
                    'leader125':'SystemExit','group125':'SystemExit'}
                assert primary['kind']==kinds[label]
                if label=='compiler-error':assert primary['code']==7 and primary['compiler_status']==7
                if label=='compiler-signal':assert primary['compiler_status']==-15 and primary['code']==-15
                if label=='cancel':assert primary['code']==143 and term.exists()
                if label in('setup-error','prepare-error','spawn-error'):assert not any(r['event']=='compiler'for r in rows)
                if label in('setup-error','prepare-error'):assert not any(r['event']=='spawn_attempt'for r in rows)
                if label=='prepare-error':
                    refused=[r for r in rows if r['event']=='source_refused']
                    assert len(refused)==1 and refused[0]['path'].startswith(str(scratch)+'/')
                if label=='spawn-error':assert [r['argv']for r in rows if r['event']=='spawn_attempt']==[command]
                if label in('setup-error','restore-error'):
                    assert [r['phase']for r in rows if r['event']=='prctl_refused']==[label.split('-')[0]]
                    assert primary['subreaper']==int(label=='restore-error')
                if label=='restore-error':assert primary['compiler_status']==0 and any(r['event']=='compiler'for r in rows)
            if grandchild.exists():assert not Path('/proc/'+grandchild.read_text()).exists()
            report['fixtures'].append({'label':label,'mode':mode,'returncode':status,'passed':True,
                'events':str(root/'events.jsonl'),'events_pin':pin((root/'events.jsonl').read_bytes()),
                'raw_wait_count':len(raw),'product_signal_count':len(signals),
                'directory_cleanup_calls':sum(r['event']=='directory_cleanup'for r in rows),
                'external_fault_cleanup_signals':sum(r['event']=='fixture_cleanup_signal'for r in rows),
                'owned_remaining':0,'whole_fixture_bootstrap':pin(product),'metadata':meta})
            save()
        report['complete']=True
    except BaseException as error:
        report['error']={'type':type(error).__name__,'message':str(error)};raise
    finally:save()
    print(json.dumps({'complete':report['complete'],'fixtures':len(report['fixtures']),
        'external_fault_cleanup_signals':sum(r['external_fault_cleanup_signals']for r in report['fixtures'])}),flush=True)


if __name__=='__main__':
    resource.setrlimit(resource.RLIMIT_AS,(2147483648,)*2)
    resource.setrlimit(resource.RLIMIT_CPU,(90,)*2)
    main()
