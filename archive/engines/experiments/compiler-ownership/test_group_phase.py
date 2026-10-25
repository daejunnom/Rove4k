"""Focused real compiler fixtures for the separate two-phase group policy."""
import ast
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
SCRIPTS = Path(__file__).resolve().parents[2]/'scripts'
sys.path.insert(0, str(SCRIPTS))
import compiler_group as owner
import test_compiler_group as original
import group_phase as phase

PORT = original.PORT.replace("row={'event':event,**values}",
    "row={'event':event,'monotonic':time.monotonic(),**values}").replace(
    "return real_killpg(pid,sig)",
    "if mode=='signal_error' and sig==signal.SIGTERM:raise OSError('phase-signal-error')\n return real_killpg(pid,sig)")

THREAD_SOURCE = r'''#include <pthread.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
static void *worker(void *x){char b[4096];for(;;){FILE*f=fopen("/proc/self/stat","r");
if(f){char*r=fgets(b,sizeof b,f);fclose(f);char*p=r?strrchr(b,')'):0;if(p&&p[2]=='Z')break;}usleep(1000);}
FILE*f=fopen(x,"w");if(!f)_exit(8);fprintf(f,"%d",getpid());fclose(f);for(;;)pause();return x;}
int main(int n,char **v){pthread_t t;signal(SIGTERM,SIG_IGN);if(pthread_create(&t,0,worker,v[1]))return 9;pthread_exit(0);}
'''


@unittest.skipUnless(sys.platform == 'linux', 'Linux fixed-group fixtures')
class GroupPhaseContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(tempfile.mkdtemp(prefix='group-phase-', dir=os.environ.get('ROVE_GROUP_PHASE_OUT')))
        cls.engine = cls.root/'engine'
        source = cls.root/'engine.c'
        source.write_text('#include <stdio.h>\n#include <stdlib.h>\nint main(int n,char**v){char b[80];fgets(b,sizeof b,stdin);printf("%s:%s:%s",v[1],getenv("R4_OWNER_TEST"),b);return 17;}\n')
        original.RuntimeContracts.run_owned(['cc', str(source), '-o', str(cls.engine)], cls.root/'compile-engine')
        source = cls.root/'thread-leader.c';source.write_text(THREAD_SOURCE)
        cls.thread = cls.root/'thread-leader'
        original.RuntimeContracts.run_owned(['cc', '-pthread', str(source), '-o', str(cls.thread)], cls.root/'compile-thread')
        manifest = {'source': str(source), 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'binary': str(cls.thread), 'binary_sha256': hashlib.sha256(cls.thread.read_bytes()).hexdigest(),
            'contract': 'ignores TERM, main pthread_exit while another thread pauses; ready path argv1'}
        (cls.root/'thread-fixture.json').write_text(json.dumps(manifest, indent=2)+'\n')
        print('THREAD_FIXTURE='+json.dumps(manifest), flush=True)

    def fixture(self, label, body='', *, mode='normal', cancel=False, command=None, expected=None, variant='short'):
        root=self.root/label;root.mkdir();scratch=root/'scratch';scratch.mkdir();log=root/'events.jsonl';ready=root/'ready'
        compiler=root/'compiler.py'
        compiler.write_text('import os,signal,subprocess,sys,time,shutil\nfrom pathlib import Path\n'
            +'shutil.copyfile('+repr(str(self.engine))+',"x");os.chmod("x",0o700)\n'+body)
        base=original.prepared([sys.executable,str(compiler)] if command is None else command)
        selected,_=owner.compact_cleanup(base)
        selected,_=owner.compact_private_owner(selected)
        selected,proof=phase.transform_bootstrap(selected,owner=owner,variant=variant)
        wrapper=root/'bootstrap.py';wrapper.write_bytes(selected);(root/'proof.json').write_text(json.dumps(proof,indent=2)+'\n')
        port=root/'port.py';port.write_text(PORT)
        output=original.RuntimeContracts.run_owned([sys.executable,'-B',str(port),str(wrapper),mode,str(log),str(root),'w','l'],
            root/'run',env={**os.environ,'TMPDIR':str(scratch),'R4_OWNER_TEST':'env'},ready=ready if cancel else None,
            expected=expected if expected is not None else 143 if cancel else 125 if mode=='group125' else 17)
        rows=[json.loads(line) for line in log.read_text().splitlines()]
        return root,scratch,rows,output

    def test_normal_FD_exec_preserves_io_and_each_representation(self):
        for variant in phase.VARIANTS:
            root,scratch,rows,output=self.fixture('normal-'+variant,variant=variant)
            self.assertEqual(output,b'argument:env:input\n');self.assertEqual(list(scratch.iterdir()),[])
            reaped=next(r for r in rows if r['event']=='product_reap')
            self.assertTrue(reaped['waitable']);self.assertTrue(all(m['state']=='Z' for m in reaped['members']))

    def test_waitable_leader_skips_grace_and_drains_surviving_grandchild(self):
        root=self.root/'orphan';root.mkdir();child=root/'child.py';ready=root/'child-ready'
        child.write_text('import os,time\nfrom pathlib import Path\nPath('+repr(str(ready))+').write_text(str(os.getpid()))\nwhile True:time.sleep(30)\n')
        body='subprocess.Popen([sys.executable,'+repr(str(child))+'])\nwhile not Path('+repr(str(ready))+').exists():time.sleep(.005)\n'
        _,scratch,rows,output=self.fixture('orphan-run',body)
        self.assertEqual(output,b'argument:env:input\n');self.assertEqual(list(scratch.iterdir()),[])
        signals=[r for r in rows if r['event']=='signal_group']
        self.assertTrue(signals);self.assertEqual(signals[0]['signal'],9);self.assertTrue(signals[0]['waitable'])
        self.assertTrue(any(m['pid']==int(ready.read_text()) and m['state']!='Z' for m in signals[0]['members']))

    def test_live_group_gets_graceful_signal_and_parent_cancel_status(self):
        root=self.root/'term-run'
        body='def stop(s,f):\n Path('+repr(str(root/'term'))+').write_text(str(s))\n raise SystemExit(0)\nsignal.signal(signal.SIGTERM,stop)\nPath('+repr(str(root/'ready'))+').write_text("ready")\nwhile True:time.sleep(30)\n'
        _,scratch,rows,_=self.fixture('term-run',body,cancel=True)
        self.assertEqual((root/'term').read_text(),'15');self.assertEqual(list(scratch.iterdir()),[])
        self.assertTrue(any(r['event']=='primary' and r['code']==143 for r in rows))
        self.assertEqual(next(r for r in rows if r['event']=='signal_group')['signal'],15)

    def test_ignored_grace_reaches_KILL_after_its_own_deadline(self):
        root=self.root/'ignore-run'
        body='signal.signal(signal.SIGTERM,signal.SIG_IGN)\nPath('+repr(str(root/'ready'))+').write_text("ready")\nwhile True:time.sleep(30)\n'
        _,scratch,rows,_=self.fixture('ignore-run',body,cancel=True)
        signals=[r for r in rows if r['event']=='signal_group']
        self.assertEqual(signals[0]['signal'],15);kill=next(r for r in signals if r['signal']==9)
        self.assertGreaterEqual(kill['monotonic']-signals[0]['monotonic'],4.9)
        self.assertEqual(list(scratch.iterdir()),[])

    def test_zombie_main_thread_does_not_bypass_waitability_budget(self):
        root=self.root/'thread-run'
        body='os.execv('+repr(str(self.thread))+',['+repr(str(self.thread))+','+repr(str(root/'ready'))+'])\n'
        _,scratch,rows,_=self.fixture('thread-run',body,cancel=True)
        signals=[r for r in rows if r['event']=='signal_group'];term=signals[0];kill=next(r for r in signals if r['signal']==9)
        self.assertEqual(term['signal'],15);self.assertFalse(term['waitable'])
        self.assertTrue(any(m['pid']==term['pid'] and m['state']=='Z' for m in term['members']))
        self.assertGreaterEqual(kill['monotonic']-term['monotonic'],4.9)
        self.assertEqual(list(scratch.iterdir()),[])

    def test_prepare_spawn_and_compiler_failure_preserve_status(self):
        for label,mode,command,body,status,kind in (
            ('prepare','prepare_error',None,'',1,'OSError'),
            ('spawn','normal',['/unavailable-group-phase-fixture/cc'],'',1,'FileNotFoundError'),
            ('compile','normal',None,'raise SystemExit(7)\n',7,'SystemExit')):
            _,scratch,rows,_=self.fixture(label,body,mode=mode,command=command,expected=status)
            primary=next(r for r in rows if r['event']=='primary');self.assertEqual(primary['kind'],kind)
            self.assertEqual(list(scratch.iterdir()),[])

    def test_injected_KILL_phase_timeout_preserves_workspace_125(self):
        _,scratch,rows,_=self.fixture('timeout',mode='group125')
        primary=next(r for r in rows if r['event']=='primary');self.assertEqual(primary['code'],125)
        self.assertIsNone(primary['d']);self.assertEqual(primary['product_reaps'],0)
        self.assertTrue(list(scratch.iterdir()));self.assertTrue(any(r['event']=='fixture_reap' for r in rows))

    def test_cleanup_exception_preserves_workspace_and_finally_precedence(self):
        root=self.root/'signal-error'
        body='Path('+repr(str(root/'ready'))+').write_text("ready")\nwhile True:time.sleep(30)\n'
        _,scratch,rows,_=self.fixture('signal-error',body,mode='signal_error',cancel=True,expected=1)
        primary=next(r for r in rows if r['event']=='primary');self.assertEqual(primary['kind'],'OSError')
        self.assertIsNone(primary['d']);self.assertEqual(primary['product_reaps'],0)
        self.assertTrue(list(scratch.iterdir()));self.assertTrue(any(r['event']=='fixture_reap' for r in rows))

    def test_complete_owner_inverse_and_negative_admission(self):
        before=original.prepared();before,_=owner.compact_cleanup(before);before,_=owner.compact_private_owner(before)
        for variant in phase.VARIANTS:
            after,proof=phase.transform_bootstrap(before,owner=owner,variant=variant)
            self.assertEqual(phase.restore_bootstrap(after,proof),before)
            for invalid in (after,before+b'pass\n',before.replace(b'q=15',b'q=9',1)):
                with self.assertRaises(ValueError):phase.transform_bootstrap(invalid,owner=owner,variant=variant)
        with self.assertRaises(ValueError):phase.transform_bootstrap(before,owner=owner,variant='other')


if __name__=='__main__':
    unittest.main()
