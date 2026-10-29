"""Focused source-contract and pre-spawn preparation-failure checks."""
import ast
import builtins
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import compiler_group
import compiler_stdin


SOURCE = b'int main(void){return 0;}\n'
COMMAND = ['cc', '-x', 'c', '-', '-o', 'x']
STOP = 'def stop(s,f):\n global q\n q=s\n signal.pthread_sigmask(signal.SIG_BLOCK,{2,15})\n raise SystemExit(128+s)\n'
REGISTER = 'signal.signal(2,stop);signal.signal(15,stop)\n'
RESET = 'signal.signal(2,signal.SIG_DFL);signal.signal(15,signal.SIG_DFL)\n'
MASK = 'signal.pthread_sigmask(signal.SIG_BLOCK,{2,15})'
UNMASK = 'signal.pthread_sigmask(signal.SIG_SETMASK,m)'
CLEANUP = (' finally:\n  if p is not None and p.poll() is None:\n'
           '   try:os.killpg(p.pid,q)\n   except ProcessLookupError:pass\n'
           '   try:p.wait(timeout=5)\n'
           '   except subprocess.TimeoutExpired:os.killpg(p.pid,9);p.wait()\n')


def legacy_stdin(zipped=False):
    source = "zipfile.ZipFile(sys.argv[0]).read('c')" if zipped else repr(SOURCE)
    return (('import os,signal,subprocess,sys,tempfile' + (',zipfile' if zipped else '') + '\n') +
        'p=None;q=15\n' + STOP + REGISTER + "with tempfile.TemporaryDirectory(prefix='r4-') as d:\n" +
        ' try:\n  m=' + MASK + '\n  try:p=subprocess.Popen(' + repr(COMMAND) +
        ',cwd=d,env=dict(os.environ,TMPDIR=d),stdin=subprocess.PIPE,start_new_session=True,preexec_fn=lambda:' + UNMASK + ')\n' +
        '  finally:' + UNMASK + '\n  p.communicate(' + source + ')\n' + CLEANUP +
        " if p.returncode:sys.exit(p.returncode)\n fd=os.open(d+'/x',0)\n" + RESET +
        'os.execve(fd,sys.argv[1:],os.environ)\n').encode('utf-8')


def legacy_restored():
    # Source-only fixture: the opaque archive is never decoded or executed.
    restore = " a=4\n for _ in range(struct.unpack_from('<I',b)[0]):\n  n,s=struct.unpack_from('<HI',b,a);a+=6;f=d+'/'+b[a:a+n].decode();a+=n\n  os.makedirs(os.path.dirname(f),exist_ok=True)\n  with open(f,'wb') as o:o.write(b[a:a+s])\n  a+=s\n"
    return ('#!/usr/bin/python3\nimport base64,os,signal,struct,subprocess,sys,tempfile,zlib\n' +
        'p=None;q=15\n' + STOP + REGISTER + "b=zlib.decompress(base64.b85decode(b''))\n" +
        "with tempfile.TemporaryDirectory(prefix='r4-') as d:\n" + restore +
        " e=os.environ.copy();e.update({});e['TMPDIR']=d\n" +
        ' try:\n  m=' + MASK + '\n  try:p=subprocess.Popen(' + repr(COMMAND) +
        ',cwd=d,env=e,start_new_session=True,preexec_fn=lambda:' + UNMASK + ')\n' +
        '  finally:' + UNMASK + '\n  r=p.wait()\n' + CLEANUP +
        " if r:sys.exit(r)\n f=d+'/x';os.chmod(f,448)\n fd=os.open(f,os.O_RDONLY)\n" +
        RESET + 'os.execve(fd,sys.argv,os.environ)\n').encode('utf-8')


def corrected(legacy):
    return compiler_group.transform_bootstrap(legacy)[0]


class SourceContractTests(unittest.TestCase):
    def test_stream_and_zip_share_closed_stages_and_restore_exact_owner(self):
        for zipped in (False, True):
            with self.subTest(zipped=zipped):
                before = corrected(legacy_stdin(zipped))
                data, record = compiler_stdin.transform_bootstrap(before)
                self.assertTrue(record['W1']['applied'])
                self.assertTrue(record['W2']['applied'])
                self.assertTrue(record['shared_wait'])
                self.assertEqual(compiler_stdin.restore_bootstrap(data, record), before)
                self.assertNotIn(b'os.write(p.stdin.fileno()', data)
                self.assertIn(b'f.flush();f.seek(0)', data)
                self.assertIn(b'stdin=f,start_new_session=True', data)
                self.assertIn(repr(COMMAND).encode(), data)
                self.assertFalse(record['W1']['parent_FD0_modified'])
                self.assertFalse(record['W1']['prepare_cancel_compiler0_guarantee'])

    def test_restored_files_explicitly_skips_W1_but_applies_W2(self):
        before = corrected(legacy_restored())
        data, record = compiler_stdin.transform_bootstrap(before)
        self.assertFalse(record['W1']['applied'])
        self.assertEqual(record['W1']['input'], record['W1']['output'])
        self.assertTrue(record['W2']['applied'])
        self.assertNotIn(b"open(d+'/c'", data)
        self.assertEqual(compiler_stdin.restore_bootstrap(data, record), before)

    def test_explicit_previous_wait_policy_and_restored_identity(self):
        before = corrected(legacy_stdin())
        data, record = compiler_stdin.transform_bootstrap(before, shared_wait=False)
        self.assertTrue(record['W1']['applied'])
        self.assertFalse(record['W2']['applied'])
        self.assertEqual(data.count(b'time.monotonic()'), 4)
        restored = corrected(legacy_restored())
        same, record = compiler_stdin.transform_bootstrap(restored, shared_wait=False)
        self.assertEqual(same, restored)
        self.assertFalse(record['W1']['applied'])
        self.assertFalse(record['W2']['applied'])

    def test_unknown_owner_mutation_and_nonbool_policy_fail_closed(self):
        before = corrected(legacy_stdin())
        with self.assertRaises(ValueError):
            compiler_stdin.transform_bootstrap(before + b'pass\n')
        with self.assertRaises(ValueError):
            compiler_stdin.transform_bootstrap(before.replace(b'clean=False', b'clean=True', 1))
        with self.assertRaises(ValueError):
            compiler_stdin.transform_bootstrap(before, shared_wait=1)

    def test_inverse_rejects_candidate_tampering(self):
        data, record = compiler_stdin.transform_bootstrap(corrected(legacy_stdin()))
        with self.assertRaises(ValueError):
            compiler_stdin.restore_bootstrap(data + b'\n', record)


@unittest.skipUnless(sys.platform == 'linux', 'Linux signal-mask and regular-file preparation contract')
class PreparationFailureTests(unittest.TestCase):
    def test_open_write_flush_seek_fail_before_spawn_and_preserve_primary_error(self):
        data, _ = compiler_stdin.transform_bootstrap(corrected(legacy_stdin()))
        for phase in ('open', 'write', 'flush', 'seek'):
            with self.subTest(phase=phase):
                primary = OSError('W1 preparation ' + phase)
                directories, files = [], []
                real_open, real_mkdtemp = builtins.open, tempfile.mkdtemp

                class PreparedFile:
                    def __init__(self, stream):
                        self.stream = stream
                    def __enter__(self):
                        return self
                    def __exit__(self, kind, value, traceback):
                        self.stream.close()
                        return False
                    def write(self, value):
                        if phase == 'write':
                            raise primary
                        return self.stream.write(value)
                    def flush(self):
                        if phase == 'flush':
                            raise primary
                        return self.stream.flush()
                    def seek(self, offset):
                        if phase == 'seek':
                            raise primary
                        return self.stream.seek(offset)
                    def fileno(self):
                        return self.stream.fileno()

                def open_source(path, *args, **kwargs):
                    if isinstance(path, str) and path.endswith('/c'):
                        if phase == 'open':
                            raise primary
                        stream = real_open(path, *args, **kwargs)
                        self.assertTrue(stat.S_ISREG(os.fstat(stream.fileno()).st_mode))
                        self.assertFalse(os.get_inheritable(stream.fileno()))
                        files.append(stream)
                        return PreparedFile(stream)
                    return real_open(path, *args, **kwargs)

                def make_directory(*args, **kwargs):
                    directory = real_mkdtemp(*args, **kwargs)
                    directories.append(Path(directory))
                    return directory

                old_mask = signal.pthread_sigmask(signal.SIG_BLOCK, set())
                old_handlers = {sig: signal.getsignal(sig) for sig in (2, 15, signal.SIGCHLD)}
                stdin_before = os.fstat(0)
                try:
                    with mock.patch('builtins.open', side_effect=open_source), \
                         mock.patch('tempfile.mkdtemp', side_effect=make_directory), \
                         mock.patch.object(subprocess, 'Popen') as spawn:
                        with self.assertRaises(OSError) as raised:
                            exec(compile(data, '<W1-preparation-fixture>', 'exec'), {})
                        self.assertIs(raised.exception, primary)
                        spawn.assert_not_called()
                finally:
                    for sig, handler in old_handlers.items():
                        signal.signal(sig, handler)
                    signal.pthread_sigmask(signal.SIG_SETMASK, old_mask)
                self.assertTrue(directories)
                self.assertTrue(all(not directory.exists() for directory in directories))
                self.assertTrue(all(stream.closed for stream in files))
                stdin_after = os.fstat(0)
                self.assertEqual((stdin_before.st_dev, stdin_before.st_ino, stdin_before.st_mode),
                                 (stdin_after.st_dev, stdin_after.st_ino, stdin_after.st_mode))


if __name__ == '__main__':
    unittest.main()
