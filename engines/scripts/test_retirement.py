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
        self.assertIn('default="c"', SCRIPT.read_text(encoding='utf-8'))

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
            requests += [['--languages','c,rust'], ['--rust-structural-compact']]
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
