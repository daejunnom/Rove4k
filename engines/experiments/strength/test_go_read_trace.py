import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
TRACE = HERE / 'go_read_trace.py'


@unittest.skipUnless(sys.platform == 'linux' and platform.machine() in ('x86_64', 'amd64'),
                     'Linux x86-64 ptrace only')
class ReadTrace(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Distinguish an unavailable kernel/seccomp capability from a broken
        # tracer.  Only our explicit OS errno marker permits skipping; any
        # other probe failure remains a test failure.
        with tempfile.TemporaryDirectory(prefix='rove-go-capability-') as temp:
            fd = os.open(Path(temp) / 'events', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            try:
                p = subprocess.run([sys.executable, '-B', str(TRACE), str(fd), '/usr/bin/cat'],
                                   input=b'uci\n', stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   pass_fds=(fd,), timeout=30)
            finally:
                os.close(fd)
        if p.returncode and b'diagnostic-capability-unavailable:' in p.stderr:
            raise unittest.SkipTest('ptrace or kernel syscall-info unavailable: ' +
                                    p.stderr.decode('utf-8', 'replace').splitlines()[0])
        if p.returncode:
            raise RuntimeError('ptrace diagnostic probe failed: ' + p.stderr.decode('utf-8', 'replace'))
        if p.stdout != b'uci\n':
            raise RuntimeError('ptrace diagnostic probe altered engine input')

    def trace(self, argv, input_bytes):
        with tempfile.TemporaryDirectory(prefix='rove-go-trace-test-') as temp:
            evidence = Path(temp) / 'events.jsonl'
            fd = os.open(evidence, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            try:
                p = subprocess.run([sys.executable, '-B', str(TRACE), str(fd), *argv],
                    input=input_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    pass_fds=(fd,), timeout=30)
            finally:
                os.close(fd)
            events = [json.loads(line) for line in evidence.read_bytes().splitlines()]
            for event in events:
                self.assertFalse(event['engine_go_confirmed'])
                self.assertFalse(event['search_started_confirmed'])
                self.assertFalse(event['performance_eligible'])
                self.assertFalse(event['score_eligible'])
                self.assertFalse(event['operational_go_authorized'])
            return p, events

    def test_real_fd0_reads_and_line_reconstruction(self):
        # cat performs real kernel read(0) calls; two GO strings and a
        # substring inside another command must not be conflated.
        incoming = b'uci\ngo wtime 30 btime 40\nnotgo\ngo\nquit\n'
        p, events = self.trace(['/usr/bin/cat'], incoming)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout, incoming)
        goes = [e for e in events if e['event'] == 'stdin_read_buffer_go_candidate']
        self.assertEqual([e['line_sha256'] for e in goes],
                         [hashlib.sha256(x).hexdigest() for x in (b'go wtime 30 btime 40', b'go')])
        self.assertTrue(all(e['performance_eligible'] is False and e['engine_parsed'] is None
                            and e['search_started'] is None for e in goes))
        self.assertFalse(events[-1]['observation_complete'])

    def test_fragmented_kernel_reads_do_not_create_false_go(self):
        program = ('import os\n'
                   'while True:\n'
                   ' x=os.read(0,1)\n'
                   ' if not x: break\n'
                   ' os.write(1,x)\n')
        data = b'notgo\ngo wtime 1 btime 1\nquit\n'
        p, events = self.trace([sys.executable, '-u', '-c', program], data)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout, data)
        goes = [e for e in events if e['event'] == 'stdin_read_buffer_go_candidate']
        self.assertEqual([e['line_sha256'] for e in goes],
                         [hashlib.sha256(b'go wtime 1 btime 1').hexdigest()])

    def test_capability_denial_is_distinct_from_generic_failure(self):
        denied = subprocess.CompletedProcess([], 1, b'',
                    b'diagnostic-capability-unavailable: TRACEME errno=1\n')
        with mock.patch.object(subprocess, 'run', return_value=denied):
            with self.assertRaises(unittest.SkipTest):
                ReadTrace.setUpClass()
        failed = subprocess.CompletedProcess([], 1, b'', b'unexpected tracer bug\n')
        with mock.patch.object(subprocess, 'run', return_value=failed):
            with self.assertRaisesRegex(RuntimeError, 'unexpected tracer bug'):
                ReadTrace.setUpClass()

    @unittest.skipUnless(shutil.which('cc'), 'C compiler required')
    def test_page_end_read_and_uncaptured_readv(self):
        source = r'''
#include <sys/mman.h>
#include <sys/uio.h>
#include <unistd.h>
int main(int argc, char **argv) {
  long size = sysconf(_SC_PAGESIZE);
  char *p = mmap(0, size * 2, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  if (p == MAP_FAILED || mprotect(p + size, size, PROT_NONE)) return 2;
  char *q = p + size - 1;
  if (argc > 1) { struct iovec v = {q, 1}; if (readv(0, &v, 1) != 1) return 3; }
  while (read(0, q, 1) == 1) if (write(1, q, 1) != 1) return 4;
  return 0;
}
'''
        with tempfile.TemporaryDirectory(prefix='rove-go-trace-native-') as temp:
            binary = str(Path(temp) / 'reader')
            subprocess.run(['cc', '-x', 'c', '-o', binary, '-'], input=source.encode(),
                           check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            p, events = self.trace([binary], b'go first\n')
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual([e['line_sha256'] for e in events if e['event'] == 'stdin_read_buffer_go_candidate'],
                             [hashlib.sha256(b'go first').hexdigest()])
            # The first byte goes through unobserved readv, so its line is
            # discarded. Re-synchronization only happens after the newline.
            p, events = self.trace([binary, 'readv'], b'go hidden\ngo visible\n')
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual([e['line_sha256'] for e in events if e['event'] == 'stdin_read_buffer_go_candidate'],
                             [hashlib.sha256(b'go visible').hexdigest()])
            self.assertTrue(any(e.get('reason') == 'readv_not_observed' for e in events))

    def test_real_rove_engine_when_explicitly_supplied(self):
        # The build and its inputs are owned outside Git.  This is a small
        # 1-worker run, never a P16/P192 allocation or scored observation.
        engine = os.environ.get('ROVE_GO_TRACE_ENGINE')
        if not engine:
            self.skipTest('no external, explicitly selected engine build')
        data = b'uci\nisready\nposition startpos\ngo wtime 300 btime 300 winc 3 binc 3\nstop\nquit\n'
        p, events = self.trace([engine], data)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn(b'uciok', p.stdout)
        self.assertIn(b'readyok', p.stdout)
        self.assertIn(b'bestmove ', p.stdout)
        goes = [e for e in events if e['event'] == 'stdin_read_buffer_go_candidate']
        self.assertEqual([e['line_sha256'] for e in goes],
                         [hashlib.sha256(b'go wtime 300 btime 300 winc 3 binc 3').hexdigest()])

    def test_later_exec_and_real_signal_are_not_swallowed_or_injected(self):
        # An exec ptrace event is not SIGTRAP for the engine; the next real
        # image must survive and read its standard input normally.
        data = b'uci\ngo first\nquit\n'
        p, events = self.trace(['/bin/sh', '-c', 'exec /usr/bin/cat'], data)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout, data)
        self.assertTrue(any(e['event'] == 'trace_exec_changed' for e in events))
        self.assertEqual([e['line_sha256'] for e in events if e['event'] == 'stdin_read_buffer_go_candidate'],
                         [hashlib.sha256(b'go first').hexdigest()])
        program = ('import os,signal\n'
                   'signal.signal(signal.SIGUSR1, lambda n,f: os.write(1,b"SIGNAL\\n"))\n'
                   'os.kill(os.getpid(), signal.SIGUSR1)\n'
                   'os.write(1,os.read(0,4096))\n')
        p, _ = self.trace([sys.executable, '-u', '-c', program], b'go\n')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout, b'SIGNAL\ngo\n')


if __name__ == '__main__':
    unittest.main()
