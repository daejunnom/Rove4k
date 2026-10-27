"""Selection is a producer recipe, not runtime or event qualification."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("league_b_selection", Path(__file__).with_name("league_b_selection.py"))
selection = importlib.util.module_from_spec(spec)
spec.loader.exec_module(selection)


def manifest(profile):
    return {"entry": "B", "family": "B", "resources": {"id": profile, "workers": selection.WORKERS[profile]},
            "plan": {"representation": "source-jit", "entry_cleanup": "private-path", "full": True},
            "complete": True, "reproducible": True, "post_profile": dict(selection.POST_PROFILE),
            "post_spelling": dict(selection.POST_SPELLING), "source_dependencies": dict(selection.DEPENDENCIES)}


class LeagueBSelection(unittest.TestCase):
    def test_recipe_names_exact_profile_and_finite_source_stages(self):
        for profile in selection.WORKERS:
            args = selection.arguments(profile)
            self.assertEqual(args[args.index("--profile") + 1], profile)
            self.assertEqual(args[args.index("--spelling-variant") + 1], "league-atomic")
            self.assertEqual(args[args.index("--source-dependencies") + 1], "unused-includes")
            self.assertEqual(selection.check_manifest(manifest(profile), profile)["runtime_qualified"], False)
        for profile in ("test-p4", "test-p28", "tcec-provisional", "D", None):
            with self.assertRaises(ValueError):
                selection.arguments(profile)

    def test_rejects_wrong_or_reduced_producer(self):
        original = manifest("test-p192")
        changes = [("family", "A"), ("entry", "D"), ("complete", False), ("reproducible", False),
                   ("post_profile", None), ("post_spelling", None), ("source_dependencies", None),
                   ("post_scan", {"variant": "other"}), ("post_ep", {"variant": "other"})]
        for key, value in changes:
            changed = deepcopy(original)
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                selection.check_manifest(changed, "test-p192")
        for field, value in (("id", "test-p16"), ("workers", True), ("workers", 16)):
            changed = deepcopy(original)
            changed["resources"][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                selection.check_manifest(changed, "test-p192")
        changed = deepcopy(original)
        changed["plan"]["full"] = False
        with self.assertRaises(ValueError):
            selection.check_manifest(changed, "test-p192")


if __name__ == "__main__":
    unittest.main()
