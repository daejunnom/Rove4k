"""Check named league B resource boundaries; full source input comes from CI.

The optional ``check_actual_source`` consumer accepts an actual frozen P16 or
P192 resource projection, not a fixture or a native-image eligibility claim.
Neither the unit tests nor that consumer execute an engine or allocate its TT.
"""
import importlib.util
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from contextlib import redirect_stderr


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('league_b_source', HERE / 'profile_b.py')
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
builder_spec = importlib.util.spec_from_file_location('league_b_builder', HERE / 'profile_build.py')
builder = importlib.util.module_from_spec(builder_spec)
builder_spec.loader.exec_module(builder)

GEOMETRY = {'test-p16': (1 << 29, 16), 'test-p192': (1 << 33, 192)}
OBSERVED_INPUTS = {
    ('test-p16', 'private-path'): (8665, '87093b6f8b13dc028d7fdaddee92064f3186c12a0e0faafba4c033985c445dfa'),
    ('test-p192', 'private-path'): (8666, 'e8d486dd31c999baaadb6c302ceb4f9ebf80f7a88c69e29d6f0c32670dfecabd'),
}


def boundaries(profile_id):
    if profile_id not in GEOMETRY:
        raise ValueError('explicit P16 or P192 profile required')
    entries, workers = GEOMETRY[profile_id]
    page = 512
    result = [(entries // page * n // workers * page,
               entries // page * (n + 1) // workers * page)
              for n in range(workers)]
    if (result[0][0] != 0 or result[-1][1] != entries or
            any(begin % page or end % page or begin >= end for begin, end in result) or
            any(left[1] != right[0] for left, right in zip(result, result[1:]))):
        raise ValueError('page partition must cover every entry exactly once')
    return result


def check_actual_source(source, *, profile_id):
    """Transform the actual pinned resource projection and prove its inverse."""
    if profile_id not in GEOMETRY or type(source) is not bytes:
        raise ValueError('named actual league B resource projection required')
    if b.INPUTS.get((profile_id, 'private-path')) != OBSERVED_INPUTS[(profile_id, 'private-path')]:
        raise ValueError('reviewed CI resource source pin differs')
    regions = boundaries(profile_id)
    candidate, proof = b.transform_source(source, profile_id=profile_id,
                                          entry_cleanup='private-path', variant='tcec-final-lf')
    if b.restore_source(candidate, proof) != source or proof.get('full_inverse') is not True:
        raise ValueError('actual B transformation inverse differs')
    init = [stage for stage in proof['stages'] if stage['role'] == 'same page-owned TT initialization']
    bound = [stage for stage in proof['stages'] if stage['role'] == 'pure invariant end bound']
    removed = [stage for stage in proof['stages'] if stage['role'] == 'unused unit constant']
    if len(init) != 1 or len(bound) != 1:
        raise ValueError('actual initialization and bound stages required')
    init_after = init[0]['edits'][0]['after']
    bound_after = bound[0]['edits'][0]['after']
    if profile_id == 'test-p192':
        if ('RVN/RVU*n/RVW*RVU' not in init_after or
                'RVN/RVU*(n+1)/RVW*RVU' not in bound_after or removed):
            raise ValueError('P192 must preserve its original page-floor endpoints')
        if regions[0][1] != 44739072 or regions[0][1] == GEOMETRY[profile_id][0] // GEOMETRY[profile_id][1]:
            raise ValueError('P192 must not substitute per-entry division')
    else:
        if ('RVN*n/RVW' not in init_after or 'RVN*(n+1)/RVW' not in bound_after or len(removed) != 1):
            raise ValueError('P16 uses the exact divisible page-boundary simplification')
        entries, workers = GEOMETRY[profile_id]
        if any(begin != entries*n//workers or end != entries*(n+1)//workers
               for n, (begin, end) in enumerate(regions)):
            raise ValueError('P16 simplified endpoints differ from page boundaries')
    return candidate, proof


class LeagueBResourceProof(unittest.TestCase):
    def test_exact_named_input_domain_and_old_profiles_remain(self):
        for key, pin in OBSERVED_INPUTS.items():
            self.assertEqual(b.INPUTS[key], pin)
        for profile in ('test-p4', 'test-p28', 'tcec-provisional'):
            self.assertIn((profile, 'private-path'), b.INPUTS)
            self.assertIn((profile, 'none'), b.INPUTS)
        self.assertNotIn(('test-p16', 'none'), b.INPUTS)
        self.assertNotIn(('test-p192', 'none'), b.INPUTS)

    def test_page_partition_covers_both_complete_tables(self):
        for profile, (_, workers) in GEOMETRY.items():
            with self.subTest(profile=profile):
                self.assertEqual(len(boundaries(profile)), workers)

    def test_p16_divides_exactly_but_p192_direct_division_changes_boundaries(self):
        for profile, (entries, workers) in GEOMETRY.items():
            old = boundaries(profile)
            differences = [index for index, (begin, _) in enumerate(old)
                           if begin != entries * index // workers]
            if profile == 'test-p16':
                self.assertEqual(differences, [])
            else:
                self.assertEqual(len(differences), 128)
                self.assertEqual(old[0][1], 44739072)
                self.assertEqual(entries // workers, 44739242)

    def test_unreviewed_or_mutated_sources_are_rejected(self):
        for profile in GEOMETRY:
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                check_actual_source(b'mutated source', profile_id=profile)
        with self.assertRaises(ValueError):
            check_actual_source(b'', profile_id='test-p4')
        with self.assertRaises(ValueError):
            boundaries('tcec-provisional')

    def test_builder_rejects_other_league_variants_before_loading_or_building(self):
        rejected = (
            ('B', ('--b-variant', 'gain')),
            ('A', ('--b-variant', 'tcec-final-lf')),
            ('B', ('--spelling-variant', 'best')),
            ('B', ('--phase-variant', 'phase-init')),
            ('B', ('--representation', 'packed-native')),
            ('B', ('--representation', 'self-contained-elf')),
        )
        for profile in GEOMETRY:
            for family, extra in rejected:
                argv = ('profile_build.py', '--entry', family, '--profile', profile,
                        '--out', '/not-created-by-rejection', *extra)
                with self.subTest(profile=profile, family=family, extra=extra):
                    with patch.object(sys, 'argv', list(argv)), patch.object(builder, 'load') as loader:
                        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exit_code:
                            builder.main()
                        self.assertEqual(exit_code.exception.code, 2)
                        loader.assert_not_called()


if __name__ == '__main__':
    unittest.main()
