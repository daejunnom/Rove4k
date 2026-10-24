"""Compiler-stdin byte restoration only; the compiler is a Python capture stub."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


COMMON = load('test_shipping_common_api', Path(__file__).with_name('shipping_common.py'))
STREAM = load('test_shipping_previous_stream', ROOT / 'engines/compact/tiny-a/pack_stream.py')


class ShippingLiteralTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == 'linux', 'existing POSIX bootstrap target is Linux')
    def test_actual_compiler_stdin_and_unchanged_fallbacks(self):
        fixtures = (
            b'int main(void){return 0;}\n',
            b"/* ''' */\n", b'/* \'\'\' """ */\n',
            b'line\r\n', b'zero\0byte', b'invalid\xffutf8',
            b'ends\\', b'ends\\\\', b"quote'", b'quote"',
            '/* 한글 é */\n'.encode('utf-8'),
            b'const char*s="$(printf injected)";\n',
        )
        base = Path(tempfile.gettempdir()).resolve()
        if base == ROOT or ROOT in base.parents:
            base = Path.home().resolve()
        if base == ROOT or ROOT in base.parents:
            raise RuntimeError('compiler-stdin capture requires an external temporary directory')
        previous = STREAM.source_literal
        with tempfile.TemporaryDirectory(prefix='r4-common-literal-', dir=base) as temporary:
            directory = Path(temporary)
            captured = directory / 'compiler-stdin'
            compiler = directory / 'capture.py'
            compiler.write_text('import sys\nfrom pathlib import Path\n'
                                'Path(sys.argv[1]).write_bytes(sys.stdin.buffer.read())\n'
                                'raise SystemExit(23)\n', encoding='utf-8')
            scratch = directory / 'scratch'
            scratch.mkdir()
            environment = os.environ.copy()
            environment['TMPDIR'] = str(scratch)
            command = [sys.executable, str(compiler), str(captured)]
            with mock.patch.object(STREAM, 'source_literal', lambda data: COMMON.source_literal(data, previous)):
                for source in fixtures:
                    with self.subTest(source=repr(source)):
                        old_expression, old_kind = previous(source)
                        expression, kind = COMMON.source_literal(source, previous)
                        if source.isascii() and old_kind in ('raw-single', 'raw-double'):
                            self.assertEqual(expression, 'b' + old_expression[:-len('.encode()')])
                            self.assertEqual(kind, 'raw-bytes-' + old_kind[4:])
                            self.assertEqual(len(expression), len(old_expression) - 8)
                        else:
                            self.assertEqual((expression, kind), (old_expression, old_kind))
                        script, actual_kind = STREAM.bootstrap(source, command)
                        self.assertEqual(actual_kind, kind)
                        process = subprocess.run([sys.executable, '-c', script], env=environment,
                                                 stdin=subprocess.DEVNULL, capture_output=True, timeout=8)
                        self.assertEqual(process.returncode, 23, process.stderr)
                        self.assertEqual(process.stdout, b'')
                        self.assertEqual(process.stderr, b'')
                        self.assertEqual(captured.read_bytes(), source)
                        self.assertEqual(list(scratch.iterdir()), [])
            self.assertIs(STREAM.source_literal, previous)


if __name__ == '__main__':
    unittest.main()
