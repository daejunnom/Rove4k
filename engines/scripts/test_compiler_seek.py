"""Focused terminal-source admission and real BufferedRandom I/O checks."""
import ast
import copy
import errno
import io
import os
from pathlib import Path
import signal
import stat
import sys
import tempfile
import unittest

import compiler_seek
import compiler_stdin
from test_compiler_stdin import SOURCE, corrected, legacy_restored, legacy_stdin


def prepared(zipped=False, source=None, shared_wait=True):
    legacy = legacy_stdin(zipped)
    if source is not None:
        legacy = legacy.replace(repr(SOURCE).encode('utf-8'), source)
    return compiler_stdin.transform_bootstrap(corrected(legacy), shared_wait=shared_wait)


def transform(data, record, **callbacks):
    return compiler_seek.transform_bootstrap(data, owner_metadata=record,
        prepare_owner=callbacks.get('prepare_owner', compiler_stdin.transform_bootstrap),
        restore_owner=callbacks.get('restore_owner', compiler_stdin.restore_bootstrap))


class SourceContractTests(unittest.TestCase):
    def test_stream_zip_and_changed_utf8_source_preserve_only_owned_span(self):
        # Non-ASCII occurs before the edit. The opaque source also contains the
        # removed token, so a text index or global replacement is incorrect.
        source = "'/* 한글 f.flush(); */'.encode()".encode('utf-8')
        for before, owner_record in (prepared(), prepared(True), prepared(source=source)):
            with self.subTest(shape=owner_record['shape'], source=source in before):
                data, record = transform(before, owner_record)
                start = record['edit']['start']
                self.assertEqual(data, before[:start] + before[start + 10:])
                self.assertEqual(record['raw_delta'], -10)
                self.assertEqual(compiler_seek.restore_bootstrap(data, record), before)
                self.assertTrue(record['full_byte_inverse'])
                self.assertTrue(record['whole_AST_inverse_equal'])
                self.assertEqual(record['source_expression'], owner_record['W1']['source_expression'])
                if source in before:
                    self.assertIn(source, data)
                    self.assertGreater(start, len(before[:start].decode('utf-8')))
                for gap in record['protected_gaps']:
                    old = before[gap['old_start']:gap['old_start'] + gap['bytes']]
                    new = data[gap['new_start']:gap['new_start'] + gap['bytes']]
                    self.assertEqual(old, new)
                expected = ast.parse(before.decode('utf-8'))
                flush_owner = next(node for node in ast.walk(expected) if isinstance(node, ast.With)
                    and any(isinstance(child, ast.Expr) and isinstance(child.value, ast.Call)
                            and isinstance(child.value.func, ast.Attribute)
                            and child.value.func.attr == 'flush' for child in node.body))
                del flush_owner.body[1]
                self.assertEqual(ast.dump(ast.parse(data.decode('utf-8'))), ast.dump(expected))

    def test_exact_callbacks_replay_new_source_and_reject_stale_or_different_owner(self):
        first, old_record = prepared()
        second, new_record = prepared(source=b"b'int main(){return 1;}\\n'")
        calls = []

        def replay(previous, *, shared_wait):
            calls.append(shared_wait)
            return compiler_stdin.transform_bootstrap(previous, shared_wait=shared_wait)

        transform(second, new_record, prepare_owner=replay)
        self.assertEqual(calls, [True])
        with self.assertRaises(ValueError):
            transform(second, old_record)
        with self.assertRaises(ValueError):
            transform(first, old_record, restore_owner=lambda *_: compiler_stdin.restore_bootstrap(second, new_record))
        mutated = first.replace(b'clean=False', b'clean=True', 1)
        record = copy.deepcopy(old_record)
        record['output'] = compiler_seek._pin(mutated)
        with self.assertRaises(ValueError):
            transform(mutated, record)

    def test_inapplicable_policy_and_inverse_tampering_fail_closed(self):
        for before, record in (prepared(shared_wait=False),
                compiler_stdin.transform_bootstrap(corrected(legacy_restored()))):
            with self.assertRaises(ValueError):
                transform(before, record)
        before, owner_record = prepared()
        data, record = transform(before, owner_record)
        with self.assertRaises(ValueError):
            compiler_seek.restore_bootstrap(data + b'\n', record)
        bad = copy.deepcopy(record)
        bad['edit']['start'] = -1
        with self.assertRaises(ValueError):
            compiler_seek.restore_bootstrap(data, bad)


class RegularFileTests(unittest.TestCase):
    def test_real_buffered_random_seek_flushes_pending_write_and_rewinds(self):
        payload = b'seek-only\n'
        with tempfile.TemporaryDirectory(prefix='r4-seek-test-') as directory:
            path = Path(directory) / 'c'
            with open(path, 'w+b') as stream:
                self.assertIs(type(stream), io.BufferedRandom)
                self.assertTrue(stat.S_ISREG(os.fstat(stream.fileno()).st_mode))
                self.assertFalse(os.get_inheritable(stream.fileno()))
                self.assertEqual(stream.write(payload), len(payload))
                self.assertEqual(os.fstat(stream.fileno()).st_size, 0)
                stream.seek(0)
                self.assertEqual(os.fstat(stream.fileno()).st_size, len(payload))
                self.assertEqual(os.lseek(stream.fileno(), 0, os.SEEK_CUR), 0)
                descriptor = os.open(path, os.O_RDONLY)
                try:
                    self.assertEqual(os.read(descriptor, len(payload) + 1), payload)
                finally:
                    os.close(descriptor)
            self.assertTrue(stream.closed)

    @unittest.skipUnless(sys.platform == 'linux', 'Linux RLIMIT_FSIZE real write-error boundary')
    def test_real_seek_write_error_does_not_reach_the_following_boundary(self):
        import resource

        with tempfile.TemporaryDirectory(prefix='r4-seek-error-') as directory:
            with open(Path(directory) / 'c', 'w+b') as stream:
                self.assertIs(type(stream), io.BufferedRandom)
                stream.write(b'pending')
                self.assertEqual(os.fstat(stream.fileno()).st_size, 0)
                limits = resource.getrlimit(resource.RLIMIT_FSIZE)
                handler = signal.getsignal(signal.SIGXFSZ)
                passed_seek = False
                try:
                    signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
                    resource.setrlimit(resource.RLIMIT_FSIZE, (0, limits[1]))
                    with self.assertRaises(OSError) as raised:
                        stream.seek(0)
                        passed_seek = True
                finally:
                    resource.setrlimit(resource.RLIMIT_FSIZE, limits)
                    signal.signal(signal.SIGXFSZ, handler)
                self.assertEqual(raised.exception.errno, errno.EFBIG)
                self.assertFalse(passed_seek)
            self.assertTrue(stream.closed)


if __name__ == '__main__':
    unittest.main()
