"""Actual Linux shell-policy boundaries; ordinary Python owner stays separate."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import tempfile
import time
import unittest

import elf_loader
import source_package


COMPRESSION = {'format': 'lzma-alone', 'filter': 'LZMA1', 'preset': 6,
    'extreme': False, 'lc': 2, 'lp': 0, 'pb': 0, 'check': 'NONE',
    'mf': 'BT2', 'dictionary_bytes': 16384, 'nice_len': 24}
SOURCE = b'''#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>
int main(int n,char**v){struct sigaction a;char b[512];
sigaction(SIGCHLD,0,&a);printf("chld %d\\n",a.sa_handler==SIG_IGN);
for(int i=1;i<n;i++)printf("arg %d %s\\n",i,v[i]);
printf("marker %s\\n",getenv("ROVE_SHELL_MARKER"));
printf("cwd %s\\n",getcwd(b,sizeof b));puts("ready");fflush(stdout);
while(fgets(b,sizeof b,stdin)){if(!strcmp(b,"quit\\n"))return 0;
if(!strcmp(b,"reap\\n")){int s,k=0;while(waitpid(-1,&s,WNOHANG)>0)k++;
printf("reaped %d\\n",k);fflush(stdout);}}
return 0;}
'''


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class SourceAdmissionTests(unittest.TestCase):
    def test_explicit_policy_and_closed_compiler(self):
        for kwargs in ({'kind': 'unknown'}, {'kind': 'source', 'compiler': ['cc', '-o']},
                       {'kind': 'source', 'compiler': ['cc', '-o', 'elsewhere', '-']},
                       {'kind': 'source', 'child_reaping': 'silently-default'},
                       {'kind': 'native', 'compiler': source_package.SHELL_COMPILER}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                source_package.shell_header(**kwargs)
        with self.assertRaises(ValueError):
            source_package.package_shell(b'not an ELF', COMPRESSION, kind='native')
        with self.assertRaises(ValueError):
            source_package.package_shell(b'not an ELF', COMPRESSION,
                kind='native', elf_admission=elf_loader._elf)

    def test_tcec_is_an_explicit_separate_source_contract(self):
        for kwargs in ({'mode': 'inherit'}, {'compiler': ['cc', '-o']},
                       {'compiler': ['cc', '-', '-o', 'elsewhere']},
                       {'compiler': ['cc', '-', '-', '-o', 'x']},
                       {'environment': {'bad-key': 'value'}},
                       {'environment': {'KEY': 'line\nbreak'}}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                source_package.tcec_header(**kwargs)
        with self.assertRaises(TypeError):
            source_package.package_tcec(b'', COMPRESSION)
        rust = ['rustc', '--edition=2024', '-', '-o', 'x']
        header = source_package.tcec_header(compiler=rust,
            environment={'LC_ALL': 'C'})
        self.assertIn(b'LC_ALL=C rustc --edition=2024 - -o "$f"', header)
        self.assertIn(b'tail -n+6 "$0"|xz -d|', header)
        contract = source_package.tcec_contract()
        self.assertEqual(contract['temp_strategy'], 'single-executable-file')
        self.assertFalse(contract['remove_parent'])
        self.assertFalse(contract['failure_temp_cleanup'])
        self.assertEqual(contract['cleanup_delay_seconds'], 1)
        self.assertEqual(contract['cleanup_seconds'], 60)


@unittest.skipUnless(sys.platform == 'linux' and shutil.which('cc') and shutil.which('xz')
                     and Path('/bin/bash').is_file(),
                     'Linux /proc, cc, xz, POSIX shell and explicit Bash policy required')
class ShellRuntimeTests(unittest.TestCase):
    observations = []

    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='r4-shell-tests-')
        cls.root = Path(cls.temp.name)
        cls.repo = Path(__file__).resolve().parents[2]
        path = cls.repo/'engines/compact/tiny-entry-d/verify.py'
        spec = importlib.util.spec_from_file_location('shell_test_owned', path)
        cls.helper = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.helper
        spec.loader.exec_module(cls.helper)
        cls.fixture = cls.root/'fixture'
        cls.fixture.mkdir()
        # One real tiny ELF compile. Source-wrapper boundary tests below use a
        # visible test compiler that records stdin/argv/cwd and copies this ELF.
        compiler = cls.root/'compile-fixture.py'
        compiler.write_text('#!/usr/bin/python3\nimport os\nos.chdir(' +
            repr(str(cls.fixture)) + ')\nos.execvp("cc",' +
            repr(list(source_package.SHELL_COMPILER)) + ')\n')
        compiler.chmod(0o755)
        owned = cls.helper.Owned(compiler, cls.fixture, cls.helper.Budget(30))
        try:
            owned.send(SOURCE)
            owned.close_input()
            settled = owned.finish()
            cleanup = owned.cleanup()
            cls.observations.append({'case': 'real-tiny-fixture-compile',
                                     'settled': settled, 'cleanup': cleanup})
        finally:
            owned.cleanup()
        cls.native = (cls.fixture/'x').read_bytes()

    @classmethod
    def tearDownClass(cls):
        errors = []
        for owned in tuple(cls.helper.OWNED):
            try:
                owned.cleanup()
            except BaseException as error:
                errors.append(repr(error))
        output = os.environ.get('ROVE_SHELL_TEST_OUT')
        if output:
            target = Path(output)
            if not target.is_absolute() or cls.repo == target or cls.repo in target.parents:
                raise ValueError('focused shell evidence must be absolute and outside Git')
            target.mkdir(parents=True, exist_ok=True)
            (target/'observations.json').write_text(json.dumps({'cases': cls.observations,
                'real_tiny_fixture_compiles': 1, 'owned_remaining': len(cls.helper.OWNED),
                'cleanup_errors': errors}, indent=2) + '\n')
        if errors:
            raise AssertionError(errors)
        cls.temp.cleanup()

    def start(self, name, *, kind='source', policy='inherit', fault=None):
        directory = self.root/name
        directory.mkdir()
        tmp = directory/'tmp'
        tmp.mkdir()
        binary = directory/'whole'
        raw = SOURCE if kind == 'source' else self.native
        whole = source_package.package_shell(raw, COMPRESSION, kind=kind,
            child_reaping=policy, elf_admission=elf_loader._elf if kind == 'native' else None)
        binary.write_bytes(whole)
        binary.chmod(0o755)
        bin_dir = directory/'bin'
        bin_dir.mkdir()
        log = directory/'stages.jsonl'
        shim = '''#!/usr/bin/python3
import hashlib,json,os,pathlib,shutil,sys,time
stage=pathlib.Path(sys.argv[0]).name
raw=sys.stdin.buffer.read() if stage=='cc' else b''
row={'stage':stage,'argv':sys.argv[1:],'cwd':os.getcwd(),'TMPDIR':os.environ.get('TMPDIR'),
     'stdin_sha256':hashlib.sha256(raw).hexdigest(),'pid':os.getpid()}
with open(os.environ['ROVE_SHELL_LOG'],'a') as f:f.write(json.dumps(row)+'\\n')
fault=os.environ.get('ROVE_SHELL_FAULT')
if fault==stage:sys.exit({'tail':31,'xz':32,'cc':33}[stage])
if fault=='hold':time.sleep(60)
if fault!='exec':
 shutil.copyfile(os.environ['ROVE_SHELL_ELF'],'x');os.chmod('x',0o755)
'''
        (bin_dir/'cc').write_text(shim)
        (bin_dir/'cc').chmod(0o755)
        if fault in ('tail', 'xz'):
            (bin_dir/fault).write_text(shim)
            (bin_dir/fault).chmod(0o755)
        overrides = {'PATH': str(bin_dir) + os.pathsep + os.environ['PATH'],
            'TMPDIR': str(tmp), 'ROVE_SHELL_MARKER': 'shell-marker',
            'ROVE_SHELL_ELF': str(self.fixture/'x'), 'ROVE_SHELL_LOG': str(log),
            'ROVE_SHELL_FAULT': fault or ''}
        proxy = directory/'proxy.py'
        proxy.write_text('#!/usr/bin/python3\nimport os\ne=os.environ.copy();e.update(' +
            repr(overrides) + ')\nos.execve(' + repr(str(binary)) + ',' +
            repr([str(binary), 'one two', '', '한글']) + ',e)\n')
        proxy.chmod(0o755)
        owned = self.helper.Owned(proxy, directory, self.helper.Budget(20))
        return directory, tmp, log, owned

    def settle(self, owned, *, allow_forced=False):
        deadline = time.monotonic() + owned.budget.left(5)
        while not (owned.exited() and not owned.group_others()):
            if time.monotonic() >= deadline:
                if allow_forced:
                    break
                raise TimeoutError('shell policy group did not naturally settle')
            time.sleep(.01)
        cleanup = owned.cleanup()
        if not allow_forced:
            self.assertFalse(cleanup['forced_cleanup'])
        return {'returncode': owned.process.returncode, 'cleanup': cleanup,
                'stdout': owned.stdout.bytes().decode(errors='replace'),
                'stderr': owned.stderr.bytes().decode(errors='replace')}

    def test_actual_tail_xz_cc_and_exec_failures_clean_the_private_directory(self):
        cases = [(policy, fault, status) for policy in ('inherit', 'ignore-after-compile')
                 for fault, status in (('tail', 31), ('xz', 32), ('cc', 33), ('exec', 127))]
        for policy, fault, status in cases:
            with self.subTest(policy=policy, fault=fault):
                directory, tmp, log, owned = self.start('failure-' + policy + '-' + fault,
                                                       policy=policy, fault=fault)
                try:
                    result = self.settle(owned)
                    rows = [json.loads(line) for line in log.read_text().splitlines()]
                    self.assertEqual(result['returncode'], status)
                    self.assertEqual(list(tmp.iterdir()), [])
                    self.assertEqual(rows[-1]['stage'], 'cc' if fault == 'exec' else fault)
                    if fault == 'tail':
                        self.assertEqual([r['stage'] for r in rows], ['tail'])
                    if fault in ('cc', 'exec'):
                        self.assertEqual(rows[-1]['stdin_sha256'], digest(SOURCE))
                    if fault == 'exec':
                        self.assertIn(str(Path(rows[-1]['cwd'])/'x'), result['stderr'])
                    self.observations.append({'case': fault, 'child_reaping': policy,
                                              'observed': result, 'stages': rows,
                                              'private_directory_absent': True})
                finally:
                    owned.cleanup()

    def check_success(self, name, kind, policy):
        directory, tmp, log, owned = self.start(name, kind=kind, policy=policy)
        succeeded = False
        try:
            owned.wait_line(b'ready')
            image = Path('/proc')/str(owned.process.pid)/'exe'
            self.assertEqual(image.read_bytes(), self.native)
            text = owned.stdout.bytes().decode()
            self.assertIn('arg 1 one two\narg 2 \narg 3 한글\n', text)
            self.assertIn('marker shell-marker\n', text)
            self.assertIn('cwd ' + os.getcwd() + '\n', text)
            self.assertIn('chld ' + ('1' if policy == 'ignore-after-compile' else '0') + '\n', text)
            deadline = time.monotonic() + 5
            while list(tmp.iterdir()):
                self.assertLess(time.monotonic(), deadline)
                time.sleep(.01)
            self.assertEqual(image.read_bytes(), self.native)
            children = []
            if policy == 'inherit':
                while not any(c['state'] == 'Z' for c in children):
                    self.assertLess(time.monotonic(), deadline)
                    children = owned.group_others()
                    time.sleep(.01)
                # This explicit observer command is test-only. The actual F
                # source has no such child-reaping command and is not modified.
                owned.send(b'reap\n')
                owned.stdout.until(lambda b: b'reaped ' in b, owned.budget)
            else:
                while owned.group_others():
                    self.assertLess(time.monotonic(), deadline)
                    time.sleep(.01)
                children = owned.group_others()
                self.assertEqual(children, [])
            owned.send(b'quit\n')
            result = self.settle(owned)
            self.assertEqual(result['returncode'], 0)
            self.observations.append({'case': name, 'kind': kind, 'child_reaping': policy,
                'decoded_ELF_exact': True, 'private_directory_absent': True,
                'children_after_cleanup': children, 'observed': result})
            succeeded = True
        finally:
            cleanup = owned.cleanup()
            if not succeeded:
                self.observations.append({'case': name, 'kind': kind,
                    'child_reaping': policy, 'success': False, 'cleanup': cleanup,
                    'stdout': owned.stdout.bytes().decode(errors='replace'),
                    'stderr': owned.stderr.bytes().decode(errors='replace')})

    def test_inherited_sigchld_can_leave_a_zombie_and_the_test_observer_reaps_it(self):
        self.check_success('source-inherit', 'source', 'inherit')

    def test_explicit_ignore_policy_reaps_cleanup_child_for_source_and_native(self):
        self.check_success('source-ignore', 'source', 'ignore-after-compile')
        self.check_success('native-ignore', 'native', 'ignore-after-compile')

    def test_parent_only_term_has_separate_compiler_group_semantics(self):
        directory, tmp, log, owned = self.start('cancel', fault='hold')
        try:
            deadline = time.monotonic() + 5
            while not log.exists():
                self.assertLess(time.monotonic(), deadline)
                time.sleep(.01)
            owned.process.send_signal(signal.SIGTERM)
            while not owned.exited():
                self.assertLess(time.monotonic(), deadline)
                time.sleep(.01)
            before = owned.group_others()
            # The shell policy promises no owner forwarding/grace contract.
            # Keep the waitable original leader until cleanup settles its group.
            cleanup = owned.cleanup()
            self.assertEqual(owned.process.returncode, -signal.SIGTERM)
            self.assertTrue(before)
            self.assertTrue(cleanup['forced_cleanup'])
            self.assertTrue(list(tmp.iterdir()))
            self.observations.append({'case': 'parent-only-TERM', 'returncode': owned.process.returncode,
                'other_members_while_original_leader_unreaped': before, 'cleanup': cleanup,
                'private_directory_left_by_product': True,
                'claim': 'weaker cancellation; forced test cleanup is not product success'})
        finally:
            owned.cleanup()


@unittest.skipUnless(sys.platform == 'linux' and shutil.which('cc') and shutil.which('xz')
                     and Path('/bin/bash').is_file(),
                     'Linux /proc, cc, xz and explicit Bash pipe policy required')
class TcecRuntimeTests(unittest.TestCase):
    """Normal TCEC startup and pipeline failure, without the old owner policy."""
    observations = []
    setUpClass = classmethod(ShellRuntimeTests.setUpClass.__func__)
    settle = ShellRuntimeTests.settle

    @classmethod
    def tearDownClass(cls):
        errors = []
        for owned in tuple(cls.helper.OWNED):
            try:
                owned.cleanup()
            except BaseException as error:
                errors.append(repr(error))
        output = os.environ.get('ROVE_TCEC_TEST_OUT')
        if output:
            target = Path(output)
            if not target.is_absolute() or cls.repo == target or cls.repo in target.parents:
                raise ValueError('focused TCEC evidence must be absolute and outside Git')
            target.mkdir(parents=True, exist_ok=True)
            (target/'observations.json').write_text(json.dumps({'cases': cls.observations,
                'real_tiny_fixture_compiles': 1, 'owned_remaining': len(cls.helper.OWNED),
                'cleanup_errors': errors}, indent=2) + '\n')
        try:
            if errors:
                raise AssertionError(errors)
        finally:
            cls.temp.cleanup()

    def start(self, name, *, fault=None, truncated=False):
        directory = self.root/name
        directory.mkdir()
        # Spaces and non-ASCII are valid paths; only CR/LF are outside the target.
        tmp = directory/'tmp space 한글'
        tmp.mkdir()
        binary = directory/'whole'
        whole = source_package.package_tcec(SOURCE, COMPRESSION)
        binary.write_bytes(whole[:-3] if truncated else whole)
        binary.chmod(0o755)
        log = directory/'stage.json'
        bin_dir = directory/'bin'
        bin_dir.mkdir()
        if fault:
            shim = '''#!/usr/bin/python3
import hashlib,json,os,pathlib,shutil,sys
stage=pathlib.Path(sys.argv[0]).name
if stage=='tail':
 raw=pathlib.Path(sys.argv[-1]).read_bytes().split(b'\\n',5)[5]
else:raw=sys.stdin.buffer.read()
pathlib.Path(os.environ['ROVE_TCEC_LOG']).write_text(json.dumps({
 'stage':stage,'argv':sys.argv[1:],'stdin_sha256':hashlib.sha256(raw).hexdigest()}))
if stage=='tail':sys.stdout.buffer.write(raw);sys.stdout.buffer.flush()
else:
 output=sys.argv[sys.argv.index('-o')+1]
 shutil.copyfile(os.environ['ROVE_TCEC_ELF'],output);os.chmod(output,0o755)
sys.exit(31 if stage=='tail' else 33)
'''
            (bin_dir/fault).write_text(shim)
            (bin_dir/fault).chmod(0o755)
        overrides = {'PATH': str(bin_dir) + os.pathsep + os.environ['PATH'],
            'TMPDIR': str(tmp), 'ROVE_SHELL_MARKER': 'tcec-marker',
            'ROVE_TCEC_LOG': str(log), 'ROVE_TCEC_ELF': str(self.fixture/'x')}
        proxy = directory/'proxy.py'
        proxy.write_text('#!/usr/bin/python3\nimport os\ne=os.environ.copy();e.update(' +
            repr(overrides) + ')\nos.execve(' + repr(str(binary)) + ',' +
            repr([str(binary)]) + ',e)\n')
        proxy.chmod(0o755)
        owned = self.helper.Owned(proxy, directory, self.helper.Budget(25))
        return directory, tmp, log, owned

    def test_actual_compiler_keeps_uci_stdin_and_unlinks_file_while_native_runs(self):
        directory, tmp, log, owned = self.start('normal')
        try:
            original_pipe = os.readlink('/proc/self/fd/' + str(owned.process.stdin.fileno()))
            owned.send(b'reap\n')  # Queued before the actual compiler has started.
            owned.wait_line(b'ready')
            owned.stdout.until(lambda data: b'reaped ' in data, owned.budget)
            image = Path('/proc')/str(owned.process.pid)/'exe'
            self.assertEqual(image.read_bytes(), self.native)
            self.assertEqual(os.readlink('/proc/' + str(owned.process.pid) + '/fd/0'),
                             original_pipe)
            executable = Path(os.readlink(image))
            self.assertEqual(executable.parent, tmp)
            self.assertTrue(executable.is_file())
            deadline = time.monotonic() + 5
            while executable.exists():
                self.assertLess(time.monotonic(), deadline)
                time.sleep(.01)
            self.assertFalse(owned.exited())
            self.assertEqual(image.read_bytes(), self.native)
            self.assertEqual(list(tmp.iterdir()), [])
            self.assertTrue(tmp.is_dir())
            self.assertIn(b'marker tcec-marker\n', owned.stdout.bytes())
            owned.send(b'quit\n')
            result = self.settle(owned)
            self.assertEqual(result['returncode'], 0)
            self.assertEqual(result['stderr'], '')
            self.observations.append({'case': 'actual-compiler-stdin-normal-unlink-quit',
                'native_sha256': digest(self.native), 'original_stdin_preserved': True,
                'file_unlinked_while_native_alive': True, 'parent_removed': False,
                'observed': result})
        finally:
            owned.cleanup()

    def test_eof_still_schedules_normal_unlink(self):
        directory, tmp, log, owned = self.start('eof')
        try:
            owned.close_input()
            owned.wait_line(b'ready')
            result = self.settle(owned)
            self.assertEqual(result['returncode'], 0)
            self.assertEqual(result['stderr'], '')
            self.assertEqual(list(tmp.iterdir()), [])
            self.observations.append({'case': 'actual-compiler-eof', 'observed': result,
                                      'normal_file_cleanup': True})
        finally:
            owned.cleanup()

    def test_pipeline_failure_cannot_run_a_successfully_produced_native(self):
        for fault in ('tail', 'truncated-xz', 'cc'):
            with self.subTest(fault=fault):
                directory, tmp, log, owned = self.start('failure-' + fault,
                    fault=None if fault == 'truncated-xz' else fault,
                    truncated=fault == 'truncated-xz')
                try:
                    result = self.settle(owned)
                    self.assertNotEqual(result['returncode'], 0)
                    self.assertEqual(result['stdout'], '')
                    paths = list(tmp.iterdir())
                    self.assertEqual(len(paths), 1)
                    # The decoder/producer may emit all valid C, and the compiler
                    # may even produce a valid native, before returning failure.
                    self.assertEqual(paths[0].read_bytes(), self.native)
                    self.observations.append({'case': fault, 'observed': result,
                        'valid_native_present_but_not_executed': True,
                        'failure_temp_cleanup_promised': False,
                        'compiler_input_sha256': json.loads(log.read_text())['stdin_sha256']
                            if fault == 'cc' else None})
                    if fault == 'cc':
                        self.assertEqual(json.loads(log.read_text())['stdin_sha256'], digest(SOURCE))
                    # Developer cleanup follows physical group settlement; the
                    # product deliberately promises normal-startup cleanup only.
                    paths[0].unlink()
                finally:
                    owned.cleanup()


if __name__ == '__main__':
    unittest.main()
