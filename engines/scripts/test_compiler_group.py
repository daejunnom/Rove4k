"""Closed owner source contracts and focused real group/125 test ports."""
import ast,json,os,shutil,signal,subprocess,sys,tempfile,time,unittest
from pathlib import Path

import compiler_group as group
import compiler_stdin
import compiler_seek
from test_compiler_stdin import COMMAND,SOURCE,legacy_stdin


def prepared(command=COMMAND, *, inline=False, loops=False):
    legacy=legacy_stdin().replace(repr(COMMAND).encode(),repr(command).encode())
    if not inline:
        legacy=legacy.replace(b' try:\n  m=',b' e=dict(os.environ,TMPDIR=d)\n try:\n  m=',1)
        legacy=legacy.replace(b'env=dict(os.environ,TMPDIR=d)',b'env=e',1)
    if loops:
        legacy=legacy.replace(group._REGISTER[0].encode(),group._REGISTER[1].encode())
        legacy=legacy.replace(group._RESET[0].encode(),group._RESET[1].encode())
    owner=group.transform_bootstrap(legacy)[0]
    owner,record=compiler_stdin.transform_bootstrap(owner,shared_wait=True)
    return compiler_seek.transform_bootstrap(owner,owner_metadata=record,
        prepare_owner=compiler_stdin.transform_bootstrap,restore_owner=compiler_stdin.restore_bootstrap)[0]


class SourceContracts(unittest.TestCase):
    def test_legacy_renderer_keeps_the_old_cleanup_bytes(self):
        initial,cleanup,directory=group.render_cleanup()
        self.assertEqual(initial,'p=None;q=15;d=None;clean=True\n')
        self.assertEqual(cleanup,' finally:\n  '+group._MASK+'\n  if p is not None:\n'
            '   if not wait(0):kill(q)\n   if not wait(5):\n    kill(9)\n'
            '    if not wait(5):clean=False;raise SystemExit(125)\n'
            '   kill(9);t=time.monotonic()+5\n   while live():\n'
            '    if time.monotonic()>t:clean=False;raise SystemExit(125)\n'
            '    kill(9);time.sleep(.01)\n   p.wait()\n')
        self.assertEqual(directory,'finally:\n if d is not None and clean:shutil.rmtree(d)\n')

    def test_cleanup_choices_restore_and_preserve_opaque_source(self):
        before=prepared()
        for state,wait,termination in ((True,False,'grace'),(False,True,'grace'),
                (True,True,'grace'),(True,False,'kill'),(False,False,'kill')):
            with self.subTest(state=state,wait=wait,termination=termination):
                after,record=group.compact_cleanup(before,state=state,wait=wait,termination=termination)
                self.assertEqual(group.restore_bootstrap(after,record),before)
                self.assertTrue(record['outside_owned_AST_equal'])
                self.assertIn(repr(SOURCE).encode(),after)
                self.assertIn(b'os.waitid(os.P_PID,p.pid,os.WEXITED|os.WNOWAIT)',after)
                self.assertIn(b'if not wait(5,1):',after)
                if termination=='kill':
                    self.assertNotIn(b'global q',after)
                    self.assertNotIn(b'kill(q)',after)
                    self.assertIn(b'raise SystemExit(128+s)',after)

    def test_normalization_exact_replay_identity_and_composition(self):
        for inline,loops in ((False,False),(False,True),(True,False),(True,True)):
            before=prepared(inline=inline,loops=loops)
            after,record=group.normalize_bootstrap(before)
            self.assertEqual(group.restore_bootstrap(after,record),before)
            self.assertEqual(record['identity'],inline and loops)
            self.assertIn(b'env=dict(os.environ,TMPDIR=d)',after)
            self.assertNotIn(b' e=dict(',after)
            again,identity=group.normalize_bootstrap(after)
            self.assertEqual(again,after);self.assertTrue(identity['identity'])
            compact,proof=group.compact_cleanup(after)
            self.assertEqual(group.restore_bootstrap(compact,proof),after)

    def test_unknown_scaffold_policy_and_inverse_mutation_are_rejected(self):
        before=prepared()
        for value in (before+b'pass\n',before.replace(b'q=15',b'q=9',1),
                      before.replace(b'f.seek(0)',b'f.seek(1)',1)):
            for transform in (group.compact_cleanup,group.normalize_bootstrap):
                with self.assertRaises(ValueError):transform(value)
        for kwargs in ({'state':1},{'wait':1},{'termination':'other'},{'termination':'kill','wait':True}):
            with self.assertRaises(ValueError):group.compact_cleanup(before,**kwargs)
        after,record=group.compact_cleanup(before)
        with self.assertRaises(ValueError):group.restore_bootstrap(after+b'\n',record)

    def test_private_owner_stage_has_complete_inverse_and_rejects_unknown_scaffolds(self):
        before=prepared()
        for termination,wait in (('grace',False),('grace',True),('kill',False)):
            selected,_=group.compact_cleanup(before,termination=termination,wait=wait)
            after,record=group.compact_private_owner(selected,termination=termination,wait=wait)
            self.assertEqual(group.restore_bootstrap(after,record),selected)
            self.assertTrue(record['outside_owned_AST_equal'])
            self.assertIn(repr(SOURCE).encode(),after)
            with self.assertRaises(ValueError):group.compact_private_owner(after,termination=termination,wait=wait)
            with self.assertRaises(ValueError):group.compact_private_owner(selected+b'pass\n',termination=termination,wait=wait)
        selected,_=group.compact_cleanup(before)
        for candidate in (before,selected.replace(b"'/proc'",b"'/tmp'")):
            with self.assertRaises(ValueError):group.compact_private_owner(candidate)
        for kwargs in ({'wait':1},{'wait':True,'termination':'kill'},{'termination':'other'}):
            with self.assertRaises(ValueError):group.compact_private_owner(before,**kwargs)


PORT=r'''import builtins,json,os,signal,subprocess,sys,time
from pathlib import Path
wrapper=Path(sys.argv[1]);mode=sys.argv[2];log=Path(sys.argv[3]);root=Path(sys.argv[4]);wait_name=sys.argv[5];live_name=sys.argv[6];sys.argv=[str(wrapper),'engine','argument']
real_waitid=os.waitid;real_killpg=os.killpg;real_wait=subprocess.Popen.wait;real_Popen=subprocess.Popen
children=[];observed=[];namespace={};patched=False
def emit(event,**values):
 row={'event':event,**values};observed.append(row)
 with log.open('a') as f:f.write(json.dumps(row)+'\n')
def members(pid):
 rows=[]
 for path in Path('/proc').iterdir():
  if not path.name.isdecimal():continue
  try:
   f=(path/'stat').read_text().rsplit(')',1)[1].split()
   if int(f[2])==pid:rows.append({'pid':int(path.name),'state':f[0]})
  except (FileNotFoundError,PermissionError,ProcessLookupError):pass
 return rows
class Tracked(real_Popen):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs);self.fixture_reaped=False;children.append(self);emit('compiler',pid=self.pid,tmpdir=kwargs['env']['TMPDIR'])
 def wait(self,*args,**kwargs):
  emit('product_reap',pid=self.pid,waitable=real_waitid(os.P_PID,self.pid,os.WEXITED|os.WNOWAIT|os.WNOHANG)is not None,members=members(self.pid))
  value=real_wait(self,*args,**kwargs);self.fixture_reaped=True;emit('product_reaped',pid=self.pid,status=value);return value
def killpg(pid,sig):
 emit('signal_group',pid=pid,signal=sig,waitable=real_waitid(os.P_PID,pid,os.WEXITED|os.WNOWAIT|os.WNOHANG)is not None,members=members(pid))
 return real_killpg(pid,sig)
def trace(frame,event,arg):
 global patched
 if not patched and event=='line' and frame.f_code.co_filename==str(wrapper) and live_name in frame.f_globals and wait_name in frame.f_globals:
  patched=True;original=frame.f_globals[wait_name]
  def wait(n,g=0):
   actual=original(0,g);emit('wait_port',seconds=n,group=g,actual_at_entry=actual)
   if mode=='leader125':return False
   if mode=='group125' and g:return False
   return original(n,g)
  if mode in ('leader125','group125'):frame.f_globals[wait_name]=wait
  if mode=='prepare_error':
   real_open=builtins.open
   def open_source(path,*args,**kwargs):
    if isinstance(path,str)and path.endswith('/c'):raise OSError('owner-source-preparation')
    return real_open(path,*args,**kwargs)
   builtins.open=open_source
  sys.settrace(None)
 return trace
subprocess.Popen=Tracked;os.killpg=killpg;sys.settrace(trace)
try:exec(compile(wrapper.read_bytes(),str(wrapper),'exec'),namespace)
except BaseException as error:
 emit('primary',kind=type(error).__name__,code=getattr(error,'code',None),workspace=[{'path':p,'exists':Path(p).is_dir()} for p in [c.args and next(row['tmpdir'] for row in observed if row['event']=='compiler' and row['pid']==c.pid) for c in children]],product_reaps=sum(r['event']=='product_reap' for r in observed),d=namespace.get('d'))
 raise
finally:
 sys.settrace(None)
 for child in children:
  if child.fixture_reaped:continue
  if real_waitid(os.P_PID,child.pid,os.WEXITED|os.WNOWAIT|os.WNOHANG)is None:
   real_killpg(child.pid,signal.SIGKILL)
  until=time.monotonic()+5
  while real_waitid(os.P_PID,child.pid,os.WEXITED|os.WNOWAIT|os.WNOHANG)is None:
   if time.monotonic()>until:raise RuntimeError('fixture compiler did not settle')
   time.sleep(.01)
  others=[r for r in members(child.pid) if r['pid']!=child.pid and r['state']!='Z']
  if others:raise RuntimeError('fixture live group unsettled')
  real_wait(child,timeout=3);child.fixture_reaped=True;emit('fixture_reap',pid=child.pid)
'''


@unittest.skipUnless(sys.platform=='linux' and shutil.which('cc'),'Linux tiny compiler fixture required')
class RuntimeContracts(unittest.TestCase):
    private_owner=False
    @classmethod
    def setUpClass(cls):
        parent=os.environ.get('ROVE_OWNER_TEST_OUT')
        cls.root=Path(tempfile.mkdtemp(prefix='r4-owner-',dir=parent));cls.keep=bool(parent)
        source=cls.root/'engine.c';cls.engine=cls.root/'engine'
        source.write_text('#include <stdio.h>\n#include <stdlib.h>\nint main(int n,char**v){char b[80];fgets(b,sizeof b,stdin);printf("%s:%s:%s",v[1],getenv("R4_OWNER_TEST"),b);return 17;}\n')
        cls.run_owned(['cc',str(source),'-o',str(cls.engine)],cls.root/'compile',expected=0)

    @classmethod
    def tearDownClass(cls):
        if not cls.keep:shutil.rmtree(cls.root)

    @staticmethod
    def run_owned(argv,out,*,env=None,ready=None,expected=0):
        out.mkdir();input_path=out/'stdin';input_path.write_bytes(b'input\n')
        with input_path.open('rb') as source,(out/'stdout').open('wb') as stdout,(out/'stderr').open('wb') as stderr:
            handled={signal.SIGINT,signal.SIGTERM,signal.SIGALRM,signal.SIGXCPU}
            mask=signal.pthread_sigmask(signal.SIG_BLOCK,handled);child=None
            available=sorted(os.sched_getaffinity(0))
            def setup():
                os.sched_setaffinity(0,set(available[:1 if argv[0]=='cc' else 2]))
                signal.pthread_sigmask(signal.SIG_SETMASK,mask)
            try:child=subprocess.Popen(argv,stdin=source,stdout=stdout,stderr=stderr,env=env,start_new_session=True,preexec_fn=setup)
            finally:signal.pthread_sigmask(signal.SIG_SETMASK,mask)
            end=time.monotonic()+30;sent=False
            try:
                while os.waitid(os.P_PID,child.pid,os.WEXITED|os.WNOWAIT|os.WNOHANG)is None:
                    if ready is not None and ready.exists() and not sent:
                        os.kill(child.pid,signal.SIGTERM);sent=True
                    if time.monotonic()>end:raise TimeoutError('owner fixture wall')
                    time.sleep(.005)
                # This leader is still unreaped while its original group is checked.
                extras=[]
                for path in Path('/proc').iterdir():
                    if not path.name.isdecimal()or int(path.name)==child.pid:continue
                    try:
                        f=(path/'stat').read_text().rsplit(')',1)[1].split()
                        if int(f[2])==child.pid:extras.append(int(path.name))
                    except (FileNotFoundError,ProcessLookupError,PermissionError):pass
                if extras:raise RuntimeError('fixture group still has members')
                child.wait(timeout=3)
            finally:
                if child.returncode is None:
                    # Original unreaped identity is retained here; no late PGID signal.
                    os.waitid(os.P_PID,child.pid,os.WEXITED|os.WNOWAIT|os.WNOHANG)
                    os.killpg(child.pid,signal.SIGKILL)
                    while os.waitid(os.P_PID,child.pid,os.WEXITED|os.WNOWAIT|os.WNOHANG)is None:time.sleep(.005)
                    child.wait(timeout=3)
            if child.returncode!=expected:raise AssertionError((argv,child.returncode,(out/'stderr').read_text()))
        return (out/'stdout').read_bytes()

    def fixture(self,label,compiler_body,*,termination='grace',mode='normal',cancel=False,wait=False,command=None,expected=None):
        root=self.root/label;root.mkdir();scratch=root/'scratch';scratch.mkdir()
        compiler=root/'compiler.py';ready=root/'ready';marker=root/'term';log=root/'events.jsonl'
        compiler.write_text('import os,signal,subprocess,sys,time,shutil\nfrom pathlib import Path\n'+
            'shutil.copyfile('+repr(str(self.engine))+',"x")\nos.chmod("x",0o700)\n'+compiler_body)
        before=prepared([sys.executable,str(compiler)] if command is None else command)
        selected,_=group.compact_cleanup(before,termination=termination,wait=wait)
        if self.private_owner:selected,_=group.compact_private_owner(selected,termination=termination,wait=wait)
        wrapper=root/'bootstrap.py';wrapper.write_bytes(selected);port=root/'port.py';port.write_text(PORT)
        env={**os.environ,'TMPDIR':str(scratch),'R4_OWNER_TEST':'env'}
        output=self.run_owned([sys.executable,'-B',str(port),str(wrapper),mode,str(log),str(root),
            'w' if self.private_owner else 'wait','l' if self.private_owner else 'live'],root/'run',
            env=env,ready=ready if cancel else None,expected=expected if expected is not None else 143 if cancel else 125 if mode.endswith('125') else 17)
        rows=[json.loads(line) for line in log.read_text().splitlines()]
        return root,scratch,rows,output,ready,marker

    def test_fd_exec_preserves_io_and_cleans_before_native(self):
        root,scratch,rows,output,_,_=self.fixture('fd','')
        self.assertEqual(output,b'argument:env:input\n');self.assertEqual(list(scratch.iterdir()),[])
        self.assertTrue(any(row['event']=='product_reaped' for row in rows))

    def test_waitable_leader_still_drains_its_surviving_grandchild_before_reap(self):
        for skip_waitable in (False,True):
            with self.subTest(skip_waitable=skip_waitable):
                label='grandchild-'+str(int(skip_waitable));root=self.root/label;root.mkdir()
                child=root/'child.py';ready=root/'child-ready';leader=root/'leader'
                child.write_text('import os,time\nfrom pathlib import Path\nPath('+repr(str(ready))+').write_text(str(os.getpid()))\nwhile True:time.sleep(30)\n')
                body='subprocess.Popen([sys.executable,'+repr(str(child))+'])\nwhile not Path('+repr(str(ready))+').exists():time.sleep(.005)\nPath('+repr(str(leader))+').write_text(str(os.getpid()))\n'
                _,scratch,rows,output,_,_=self.fixture('leader-first-'+str(int(skip_waitable)),body,wait=skip_waitable)
                self.assertEqual(output,b'argument:env:input\n');self.assertTrue(ready.exists())
                pid=int(ready.read_text());signals=[r for r in rows if r['event']=='signal_group']
                self.assertTrue(any(r['waitable'] and any(m['pid']==pid and m['state']!='Z' for m in r['members']) for r in signals))
                reap=next(r for r in rows if r['event']=='product_reap')
                self.assertTrue(reap['waitable']);self.assertTrue(all(m['pid']==reap['pid']or m['state']=='Z' for m in reap['members']))
                self.assertEqual(list(scratch.iterdir()),[])

    def test_prepare_spawn_and_compiler_errors_keep_their_original_status_and_cleanup(self):
        for label,mode,command,body,status,kind in (
                ('source-error','prepare_error',None,'',1,'OSError'),
                ('spawn-error','normal',['/unavailable-owner-fixture/cc'],'',1,'FileNotFoundError'),
                ('compiler-error','normal',None,'raise SystemExit(7)\n',7,'SystemExit')):
            with self.subTest(label=label):
                root,scratch,rows,_,_,_=self.fixture(label,body,mode=mode,command=command,expected=status)
                primary=next(r for r in rows if r['event']=='primary')
                self.assertEqual(primary['kind'],kind)
                self.assertEqual(list(scratch.iterdir()),[])
                if label!='compiler-error':self.assertFalse(any(r['event']=='compiler' for r in rows))

    def test_cancel_keeps_parent_status_and_distinguishes_grace_from_kill(self):
        for termination in ('grace','kill'):
            label='cancel-'+termination;root=self.root/label
            body='def stop(s,f):\n Path('+repr(str(root/'term'))+').write_text(str(s))\n raise SystemExit(0)\nsignal.signal(signal.SIGTERM,stop)\nPath('+repr(str(root/'ready'))+').write_text("ready")\nwhile True:time.sleep(30)\n'
            _,scratch,rows,_,_,marker=self.fixture(label,body,termination=termination,cancel=True)
            self.assertEqual(marker.exists(),termination=='grace')
            self.assertEqual(list(scratch.iterdir()),[])
            self.assertTrue(any(r['event']=='primary' and r['code']==143 for r in rows))

    def test_injected_deadline_outcomes_reach_both_125_branches_and_preserve_workspace(self):
        for mode in ('leader125','group125'):
            _,scratch,rows,_,_,_=self.fixture(mode,'',mode=mode)
            primary=next(r for r in rows if r['event']=='primary')
            self.assertEqual(primary['kind'],'SystemExit');self.assertEqual(primary['code'],125)
            self.assertIsNone(primary['d']);self.assertEqual(primary['product_reaps'],0)
            self.assertTrue(primary['workspace'] and all(row['exists'] for row in primary['workspace']))
            self.assertTrue(list(scratch.iterdir()))
            ports=[r for r in rows if r['event']=='wait_port']
            self.assertTrue(any(r['seconds']==5 and r['group']==(1 if mode=='group125' else 0) for r in ports))
            self.assertTrue(any(r['event']=='fixture_reap' for r in rows))


class PrivateRuntimeContracts(RuntimeContracts):
    """The same lifetime and error observations on the optional emitted owner."""
    private_owner=True


if __name__=='__main__':unittest.main()
