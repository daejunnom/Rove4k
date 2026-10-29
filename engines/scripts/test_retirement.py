"""C-only engine admission; never build or execute a retired Rust engine."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT/'engines/scripts/build.py'
spec = importlib.util.spec_from_file_location('retained_engine_builder', SCRIPT)
BUILD = importlib.util.module_from_spec(spec)
spec.loader.exec_module(BUILD)

class EngineRetirement(unittest.TestCase):
    def test_default_c_portfolio_is_six(self):
        selected, exclusions = BUILD.select_implementations(['c'], list('ABCDEF'), explicit_variants=False)
        self.assertEqual(selected, {'c': list('ABCDEF')})
        self.assertEqual(len(exclusions), 6)
        self.assertEqual({row['variant'] for row in exclusions}, set('ABCDEF'))
        self.assertEqual(BUILD.select_implementations(['c'], ['A'], explicit_variants=True)[0], {'c': ['A']})

    def test_source_snapshot_uses_c_and_model_headers_only(self):
        with tempfile.TemporaryDirectory(prefix='rove4k-source-selection-') as temporary:
            root = Path(temporary)
            files = {'c/main.c': b'int main(void){return 0;}\n',
                     'c/board.h': b'#define BOARD 1\n',
                     'c/notes.json': b'{}',
                     'rust/main.rs': b'fn main() {}\n',
                     'model/frozen.h': b'#define MODEL 1\n',
                     'model/frozen.rs': b'const MODEL:u8=1;\n',
                     'model/test.c': b'int fixture(void){return 0;}\n'}
            for name, data in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            self.assertEqual(BUILD.source_files('c', root),
                             {name: files[name] for name in ('c/board.h', 'c/main.c', 'model/frozen.h')})
            with self.assertRaisesRegex(ValueError, 'Rust engine paths are retired'):
                BUILD.source_files('rust', root)

    def test_all_rust_backend_recipes_reject_before_profile_or_compiler(self):
        for variant in 'ABCDEF':
            with self.subTest(variant=variant), self.assertRaisesRegex(ValueError, 'Rust engine paths are retired'):
                BUILD.compiler_recipe('rust', variant, {}, 'size', compiler='not-a-compiler', files={})
        for languages in (['rust'], ['c','rust']):
            with self.subTest(languages=languages), self.assertRaisesRegex(ValueError, 'Rust engine paths are retired'):
                BUILD.select_implementations(languages, list('ABCDEF'), explicit_variants=False)

    def test_cli_rejects_before_output_or_compiler(self):
        base=Path(tempfile.gettempdir()).resolve()
        self.assertFalse(base==ROOT or ROOT in base.parents)
        with tempfile.TemporaryDirectory(prefix='rove4k-c-only-admission-',dir=base) as temporary:
            requests=[['--languages','rust','--variant',v] for v in 'ABCDEF']
            requests += [['--languages','c,rust'], ['--rust-structural-compact'], ['--rustc','not-a-compiler']]
            for index,args in enumerate(requests):
                out=Path(temporary)/str(index)
                with self.subTest(args=args):
                    result=subprocess.run([sys.executable,'-B',str(SCRIPT),'--out',str(out),*args],capture_output=True,timeout=20)
                    self.assertNotEqual(result.returncode,0)
                    self.assertIn(b'Rust engine paths are retired',result.stderr)
                    self.assertEqual(result.stdout,b'')
                    self.assertFalse(out.exists())

if __name__=='__main__':
    unittest.main()
