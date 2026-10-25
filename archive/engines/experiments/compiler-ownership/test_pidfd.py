"""Real process/FD observations for the optional pidfd experiment."""
import errno
import json
import os
from pathlib import Path
import select
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import types
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
import compiler_group as owner
import test_compiler_group as original
import pidfd as candidate


HOOK = r'''
import errno,fcntl,select
real_pidfd_open=os.pidfd_open;real_poll=select.poll;real_close=os.close;real_execve=os.execve
active_pidfds=set();all_pidfds=[];poll_error_used=False
def pidfd_open(pid,*args):
 emit('pidfd_request',pid=pid)
 if mode=='pidfd_open_error':
  emit('pidfd_setup_error',stage='open',errno=errno.EMFILE);raise OSError(errno.EMFILE,'pidfd fixture open')
 fd=real_pidfd_open(pid,*args)
 if mode=='pidfd_high':
  high=fcntl.fcntl(fd,fcntl.F_DUPFD_CLOEXEC,1100);real_close(fd);fd=high
 active_pidfds.add(fd);all_pidfds.append(fd);emit('pidfd_opened',pid=pid,fd=fd,inheritable=os.get_inheritable(fd))
 return fd
class Poll:
 def __init__(self):self.inner=real_poll()
 def register(self,fd,events):
  if mode=='pidfd_register_error':
   emit('pidfd_setup_error',stage='register',errno=errno.ENOMEM);raise OSError(errno.ENOMEM,'pidfd fixture register')
  return self.inner.register(fd,events)
 def poll(self,n):
  global poll_error_used
  if mode=='pidfd_poll_error' and not poll_error_used:
   poll_error_used=True;emit('pidfd_event_error',errno=errno.ENOMEM);raise OSError(errno.ENOMEM,'pidfd fixture poll')
  result=self.inner.poll(n);emit('pidfd_poll',milliseconds=n,events=result);return result
def close(fd):
 watched=fd in active_pidfds
 result=real_close(fd)
 if watched:
  active_pidfds.remove(fd)
  try:os.fstat(fd)
  except OSError as e:
   if e.errno!=errno.EBADF:raise
   emit('pidfd_closed',fd=fd,physical_EBADF=True)
  else:raise AssertionError('pidfd did not close')
 return result
def execute(fd,argv,env):
 emit('before_native_exec',active_pidfds=sorted(active_pidfds),opened_pidfds=all_pidfds)
 if active_pidfds:raise AssertionError('pidfd remains open before native exec')
 return real_execve(fd,argv,env)
os.pidfd_open=pidfd_open;select.poll=Poll;os.close=close;os.execve=execute
'''


@unittest.skipUnless(sys.platform == 'linux' and hasattr(os, 'pidfd_open')
                     and hasattr(select, 'poll') and shutil.which('cc'),
                     'Linux pidfd/poll and tiny C fixtures required')
class PidfdContracts(unittest.TestCase):
    private_owner = True
    run_owned = staticmethod(original.RuntimeContracts.run_owned)

    @classmethod
    def setUpClass(cls):
        parent = os.environ.get('ROVE_OWNER_TEST_OUT')
        cls.root = Path(tempfile.mkdtemp(prefix='r4-pidfd-', dir=parent))
        cls.keep = bool(parent)
        source = cls.root/'engine.c';cls.engine = cls.root/'engine'
        source.write_text('#include <stdio.h>\n#include <stdlib.h>\n#include <fcntl.h>\n'
            'int main(int n,char**v){for(int f=3;f<2048;f++)if(fcntl(f,F_GETFD)>=0)return 88;'
            'char b[80];fgets(b,sizeof b,stdin);printf("%s:%s:%s",v[1],getenv("R4_OWNER_TEST"),b);return 17;}\n')
        cls.run_owned(['cc', str(source), '-o', str(cls.engine)], cls.root/'compile', expected=0)

    @classmethod
    def tearDownClass(cls):
        if not cls.keep:
            shutil.rmtree(cls.root)

    def fixture(self, *args, **kwargs):
        previous, port = owner.compact_private_owner, original.PORT
        frozen_owner = types.SimpleNamespace(**vars(owner))
        frozen_owner.compact_private_owner = previous
        def transform(script, **options):
            data, _ = previous(script, **options)
            return candidate.transform_bootstrap(data, owner=frozen_owner)
        owner.compact_private_owner = transform
        original.PORT = port.replace('subprocess.Popen=Tracked;os.killpg=killpg;',
                                     HOOK+'\nsubprocess.Popen=Tracked;os.killpg=killpg;', 1)
        try:
            return original.RuntimeContracts.fixture(self, *args, **kwargs)
        finally:
            owner.compact_private_owner, original.PORT = previous, port

    def test_stdio_status_and_pidfd_close_before_actual_native_exec(self):
        _, scratch, rows, output, _, _ = self.fixture('normal', '')
        self.assertEqual(output, b'argument:env:input\n')
        self.assertEqual(list(scratch.iterdir()), [])
        self.assertTrue(any(r['event'] == 'pidfd_closed' and r['physical_EBADF'] for r in rows))
        self.assertTrue(any(r['event'] == 'before_native_exec' and r['active_pidfds'] == [] for r in rows))
        self.assertTrue(all(not r['inheritable'] for r in rows if r['event'] == 'pidfd_opened'))

    def test_high_descriptor_uses_poll_and_closes_before_exec(self):
        if resource.getrlimit(resource.RLIMIT_NOFILE)[0] <= 1100:
            self.skipTest('descriptor allowance does not include FD1100')
        _, _, rows, output, _, _ = self.fixture('high-fd', '', mode='pidfd_high')
        self.assertEqual(output, b'argument:env:input\n')
        self.assertTrue(any(r['event'] == 'pidfd_opened' and r['fd'] >= 1100 for r in rows))
        self.assertTrue(any(r['event'] == 'pidfd_poll' for r in rows))
        self.assertTrue(any(r['event'] == 'pidfd_closed' for r in rows))

    def test_cancel_preserves143_and_compiler_grace(self):
        target = self.root/'cancel'
        body = ('def stop(s,f):\n Path('+repr(str(target/'term'))+').write_text(str(s))\n'
                ' raise SystemExit(0)\nsignal.signal(signal.SIGTERM,stop)\n'
                'Path('+repr(str(target/'ready'))+').write_text("ready")\nwhile True:time.sleep(30)\n')
        _, scratch, rows, _, _, marker = self.fixture('cancel', body, cancel=True)
        self.assertTrue(marker.exists());self.assertEqual(list(scratch.iterdir()), [])
        self.assertTrue(any(r['event'] == 'primary' and r['code'] == 143 for r in rows))
        self.assertTrue(any(r['event'] == 'pidfd_closed' for r in rows))

    def test_open_register_and_poll_errors_settle_then_fail_without_exec(self):
        for mode in ('pidfd_open_error', 'pidfd_register_error', 'pidfd_poll_error'):
            with self.subTest(mode=mode):
                _, scratch, rows, _, _, _ = self.fixture(mode, '', mode=mode, expected=1)
                self.assertTrue(any(r['event'] == 'compiler' for r in rows))
                self.assertTrue(any(r['event'] == 'product_reaped' for r in rows))
                self.assertFalse(any(r['event'] == 'before_native_exec' for r in rows))
                self.assertTrue(any(r['event'] == 'primary' and r['kind'] == 'OSError' for r in rows))
                self.assertEqual(list(scratch.iterdir()), [])
                if mode != 'pidfd_open_error':
                    self.assertTrue(any(r['event'] == 'pidfd_closed' for r in rows))

    def test_waitable_leader_still_drains_surviving_grandchild(self):
        root = self.root/'grandchild';root.mkdir()
        child = root/'child.py';ready = root/'child-ready'
        child.write_text('import os,time\nfrom pathlib import Path\nPath('+repr(str(ready))+').write_text(str(os.getpid()))\nwhile True:time.sleep(30)\n')
        body = ('subprocess.Popen([sys.executable,'+repr(str(child))+'])\n'
                'while not Path('+repr(str(ready))+').exists():time.sleep(.005)\n')
        _, scratch, rows, output, _, _ = self.fixture('leader-first', body)
        self.assertEqual(output, b'argument:env:input\n');self.assertEqual(list(scratch.iterdir()), [])
        pid = int(ready.read_text())
        self.assertTrue(any(r['event'] == 'signal_group' and r['waitable']
            and any(m['pid'] == pid and m['state'] != 'Z' for m in r['members']) for r in rows))
        reap = next(r for r in rows if r['event'] == 'product_reap')
        self.assertTrue(reap['waitable'])
        self.assertTrue(all(m['pid'] == reap['pid'] or m['state'] == 'Z' for m in reap['members']))

    def test_injected_both125_deadlines_preserve_workspace_and_close_pidfd(self):
        for mode in ('leader125', 'group125'):
            with self.subTest(mode=mode):
                _, scratch, rows, _, _, _ = self.fixture(mode, '', mode=mode)
                primary = next(r for r in rows if r['event'] == 'primary')
                self.assertEqual(primary['code'], 125);self.assertIsNone(primary['d'])
                self.assertEqual(primary['product_reaps'], 0)
                self.assertTrue(list(scratch.iterdir()))
                self.assertTrue(any(r['event'] == 'pidfd_closed' for r in rows))
                self.assertTrue(any(r['event'] == 'fixture_reap' for r in rows))

    def test_main_thread_exit_is_not_flags0_pidfd_readiness(self):
        from test_group_phase import THREAD_SOURCE
        root = self.root/'thread';root.mkdir();source = root/'thread.c';binary = root/'thread'
        source.write_text(THREAD_SOURCE)
        self.run_owned(['cc', '-pthread', str(source), '-o', str(binary)], root/'compile', expected=0)
        ready = root/'ready';p = None;fd = None;reaped = False;record = {}
        try:
            p = subprocess.Popen([str(binary), str(ready)], start_new_session=True)
            fd = os.pidfd_open(p.pid, 0);poll = select.poll();poll.register(fd, select.POLLIN)
            end = time.monotonic()+5
            while not ready.exists():
                if time.monotonic() > end:
                    raise TimeoutError('main-thread fixture readiness')
                time.sleep(.005)
            record = {'pid': p.pid, 'state': Path('/proc/'+str(p.pid)+'/stat').read_text().rsplit(')',1)[1].split()[0],
                'tasks': len(list(Path('/proc/'+str(p.pid)+'/task').iterdir())), 'before_poll': poll.poll(0)}
            self.assertEqual(record['state'], 'Z');self.assertEqual(record['tasks'], 2)
            self.assertEqual(record['before_poll'], [])
            self.assertIsNone(os.waitid(os.P_PID, p.pid, os.WEXITED|os.WNOWAIT|os.WNOHANG))
            os.killpg(p.pid, signal.SIGKILL)
            record['after_poll'] = poll.poll(5000)
            one = os.waitid(os.P_PID, p.pid, os.WEXITED|os.WNOWAIT|os.WNOHANG)
            two = os.waitid(os.P_PID, p.pid, os.WEXITED|os.WNOWAIT|os.WNOHANG)
            self.assertIsNotNone(one);self.assertEqual(one, two);self.assertEqual(one.si_pid, p.pid)
            self.assertTrue(any(n == fd and mask & select.POLLIN for n,mask in record['after_poll']))
            self.assertEqual(p.wait(), -signal.SIGKILL);reaped = True
            record['passed'] = True
        finally:
            if p is not None and not reaped:
                if os.waitid(os.P_PID, p.pid, os.WEXITED|os.WNOWAIT|os.WNOHANG) is None:
                    os.killpg(p.pid, signal.SIGKILL)
                end = time.monotonic()+5
                while os.waitid(os.P_PID, p.pid, os.WEXITED|os.WNOWAIT|os.WNOHANG) is None:
                    if time.monotonic() > end:
                        raise TimeoutError('main-thread fixture physical exit')
                    time.sleep(.005)
                p.wait()
            if fd is not None:
                os.close(fd)
            (root/'observations.json').write_text(json.dumps(record, indent=2)+'\n')


if __name__ == '__main__':
    unittest.main()
