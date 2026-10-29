"""Exercise the exact B-league atomic helper without running an engine.

``check_actual_source`` is called on actual CI-generated B source only. The
legacy spelling module is separately loaded and augmented in this test process
to compare bytes and proof gaps; its production input map is never changed.
"""
from copy import deepcopy
from contextlib import redirect_stderr
import importlib.util
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


owner = load('league_b_atomic_owner', HERE / 'profile_b_league_spelling.py')
builder = load('league_b_atomic_builder', HERE / 'profile_build.py')
INPUTS = {
    'test-p16': (8010, 'e8f8a5f63ea74b25398dd381b1850a2f72285821fb9a50144760989b574fdd6e'),
    'test-p192': (8038, '665e7a02f9f1c15543ecec4b5bb7b757dc9150af5dd4a366f16e5a8d7d494e06'),
}


def check_actual_source(source, *, profile_id):
    """Check the actual source, inverse, typed proof and legacy byte equality."""
    if owner.INPUTS != INPUTS:
        raise ValueError('actual named CI source pins differ')
    candidate, proof = owner.transform_source(source, family='B', profile_id=profile_id,
                                               variant='atomic-assignment')
    if owner.restore_source(candidate, proof) != source:
        raise ValueError('actual league B atomic inverse differs')
    # The canonical helper is instantiated separately and its test-only map is
    # extended for this comparison. No production module or source is changed.
    legacy = load('league_b_atomic_legacy_comparison', HERE / 'profile_spelling.py')
    legacy.INPUTS = {**legacy.INPUTS, ('B', profile_id): INPUTS[profile_id]}
    old_candidate, old_proof = legacy.transform_source(source, family='B', profile_id=profile_id,
                                                        variant='atomic-assignment')
    comparable = dict(proof, schema=legacy.SCHEMA)
    if candidate != old_candidate or comparable != old_proof:
        raise ValueError('actual atomic candidate/protected gaps differ from canonical spelling')
    if legacy.restore_source(old_candidate, old_proof) != source:
        raise ValueError('canonical atomic inverse differs')
    corrupted = deepcopy(proof)
    corrupted['full_inverse'] = 1
    try:
        owner.restore_source(candidate, corrupted)
    except ValueError:
        pass
    else:
        raise ValueError('typed proof substitution must be rejected')
    try:
        owner.restore_source(candidate + b' ', proof)
    except ValueError:
        pass
    else:
        raise ValueError('changed atomic output must be rejected')
    return candidate, proof


class LeagueBAtomicContracts(unittest.TestCase):
    def test_builder_selects_only_named_full_b_league_atomic_route(self):
        declaration = {'path': 'engines/experiments/tcec-next/profile_b_league_spelling.py',
                       'selection': 'league-atomic', 'variant': 'atomic-assignment'}
        for profile in INPUTS:
            with self.subTest(profile=profile):
                self.assertEqual(builder.spelling_selection('B', 'source-jit', 'tcec-final-lf',
                    'control', 'league-atomic', profile_id=profile), declaration)
        wrong = (('A', 'source-jit', 'tcec-final-lf', 'control', 'test-p16'),
                 ('B', 'source-jit', 'control', 'control', 'test-p16'),
                 ('B', 'source-jit', 'tcec-final-lf', 'control', 'test-p4'),
                 ('B', 'packed-native', 'tcec-final-lf', 'control', 'test-p16'),
                 ('B', 'source-jit', 'tcec-final-lf', 'phase-init', 'test-p192'))
        for family, representation, b_variant, phase, profile in wrong:
            with self.subTest(family=family, profile=profile, representation=representation), self.assertRaises(ValueError):
                builder.spelling_selection(family, representation, b_variant, phase,
                                           'league-atomic', profile_id=profile)

    def test_builder_requires_final_dependency_gate_before_loading_source(self):
        for profile in INPUTS:
            argv = ['profile_build.py', '--entry', 'B', '--profile', profile,
                    '--b-variant', 'tcec-final-lf', '--spelling-variant', 'league-atomic',
                    '--source-dependencies', 'control', '--out', '/not-created-by-rejection']
            with self.subTest(profile=profile), patch.object(sys, 'argv', argv), patch.object(builder, 'load') as loader:
                with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exit_code:
                    builder.main()
                self.assertEqual(exit_code.exception.code, 2)
                loader.assert_not_called()

    def test_builder_executes_only_the_exact_reviewed_helper_bytes(self):
        path = HERE / 'profile_b_league_spelling.py'
        data = path.read_bytes().replace(b'\r\n', b'\n')
        module = builder.load_reviewed_b_league_spelling(data, path)
        self.assertEqual(module.SCHEMA, owner.SCHEMA)
        self.assertEqual(module.INPUTS, INPUTS)
        with self.assertRaises(ValueError):
            builder.load_reviewed_b_league_spelling(data + b'\nraise RuntimeError("must not execute")\n', path)
        with self.assertRaises(ValueError):
            builder.load_reviewed_b_league_spelling(bytearray(data), path)

    def test_only_two_actual_ci_source_pins_are_admitted(self):
        self.assertEqual(owner.INPUTS, INPUTS)
        for profile in INPUTS:
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                owner.transform_source(b'not an admitted input', family='B', profile_id=profile,
                                       variant='atomic-assignment')
        for family, profile, variant in (('A', 'test-p16', 'atomic-assignment'),
                                         ('B', 'test-p4', 'atomic-assignment'),
                                         ('B', 'test-p192', 'other')):
            with self.subTest(family=family, profile=profile, variant=variant), self.assertRaises(ValueError):
                owner.transform_source(b'', family=family, profile_id=profile, variant=variant)

    def test_exactly_five_standalone_atomic_stores_and_protected_gaps(self):
        source = (b'atomic_int qp;\n'
                  b'atomic_store(&qp,0); x(); atomic_store(&qp,1);\n'
                  b'atomic_store(&qp,1); y(); atomic_store(&qp,0); atomic_store(&qp,1);')
        candidate, edits, gaps = owner._rewrite(source)
        self.assertEqual(candidate, b'atomic_int qp;\nqp=0; x(); qp=1;\nqp=1; y(); qp=0; qp=1;')
        self.assertEqual(len(edits), 5)
        self.assertEqual(len(gaps), 6)
        self.assertTrue(all(row['role'] == 'implicit-seq-cst-atomic-assignment' for row in edits))
        with self.assertRaises(ValueError):
            owner._rewrite(source + b'atomic_store(&qp,1);')
        with self.assertRaises(ValueError):
            owner._rewrite(source.replace(b'atomic_int qp;', b'int qp;'))


if __name__ == '__main__':
    unittest.main()
