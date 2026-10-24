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


if __name__ == '__main__':
    unittest.main()
