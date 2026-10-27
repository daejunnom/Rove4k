"""Test the exact A/C/E/F league spelling without running an engine."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


owner = load('league_acef_atomic_owner', HERE / 'profile_acef_league_atomic.py')


def check_actual_source(source, *, family, profile_id):
    """CI calls this with its actual resource projection, never a fixture."""
    candidate, proof = owner.transform_source(source, family=family, profile_id=profile_id,
                                               variant=owner.VARIANT)
    if owner.restore_source(candidate, proof) != source:
        raise ValueError('actual league atomic inverse differs')
    legacy = load('league_acef_legacy_comparison', HERE / 'profile_spelling.py')
    legacy.INPUTS = {**legacy.INPUTS, (family, profile_id): owner.INPUTS[(family, profile_id)]}
    old_candidate, old_proof = legacy.transform_source(source, family=family, profile_id=profile_id,
                                                        variant=owner.VARIANT)
    if candidate != old_candidate or dict(proof, schema=legacy.SCHEMA) != old_proof:
        raise ValueError('actual atomic candidate or protected gaps differ from canonical spelling')
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


class LeagueAtomicContracts(unittest.TestCase):
    def test_only_eight_named_ci_source_pins_are_admitted(self):
        self.assertEqual(set(owner.INPUTS), {(f, p) for f in 'ACEF' for p in ('test-p16', 'test-p192')})
        for family, profile in owner.INPUTS:
            with self.subTest(family=family, profile=profile), self.assertRaises(ValueError):
                owner.transform_source(b'wrong bytes', family=family, profile_id=profile, variant=owner.VARIANT)
        for family, profile, variant in (('B', 'test-p16', owner.VARIANT),
                                         ('D', 'test-p192', owner.VARIANT),
                                         ('A', 'test-p4', owner.VARIANT),
                                         ('A', 'test-p16', 'other')):
            with self.subTest(family=family, profile=profile), self.assertRaises(ValueError):
                owner.transform_source(b'', family=family, profile_id=profile, variant=variant)

    def test_all_standalone_atomic_stores_and_unchanged_gaps(self):
        for family, (name, count) in owner.TARGETS.items():
            source = ('atomic_int ' + name + ';\n' +
                      'work();'.join('atomic_store(&' + name + ',' + str(n % 2) + ');' for n in range(count)) +
                      'atomic_load_explicit(&' + name + ',memory_order_relaxed);').encode()
            candidate, edits, gaps = owner._rewrite(source, family=family)
            self.assertEqual(len(edits), count)
            self.assertEqual(len(gaps), count + 1)
            self.assertIn(('atomic_load_explicit(&' + name + ',memory_order_relaxed);').encode(), candidate)
            self.assertTrue(all(row['role'] == 'implicit-seq-cst-atomic-assignment' for row in edits))
            with self.assertRaises(ValueError):
                owner._rewrite(source + ('atomic_store(&' + name + ',1);').encode(), family=family)
            with self.assertRaises(ValueError):
                owner._rewrite(source.replace(('atomic_int ' + name + ';').encode(),
                                             ('int ' + name + ';').encode()), family=family)
            with self.assertRaises(ValueError):
                owner._rewrite(source + b'atomic_store(&other,1);', family=family)


if __name__ == '__main__':
    unittest.main()
