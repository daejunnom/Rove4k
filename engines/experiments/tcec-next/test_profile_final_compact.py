import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("profile_final_compact_verify", HERE / "profile_verify.py")
verify = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = verify
spec.loader.exec_module(verify)


class FinalCompactAdmissionTests(unittest.TestCase):
    def stage_inputs(self, family, profile="test-p4"):
        post = ({"path": "engines/experiments/tcec-next/profile_b.py", "variant": "tcec-final-lf"}
                if family == "B" else {"path": "engines/experiments/tcec-next/profile_phase.py", "variant": "phase-init"})
        spelling = ({"path": verify.SPELLING, "selection": "best", "variant": verify.BEST_SPELLING["B"]}
                    if family == "B" else verify.F_COMPOUND_DECLARATION if family == "F"
                    else verify.COMPOUND_DECLARATION)
        scan = verify.SCAN_DECLARATION if family in "AC" else None
        schemas = ["rove4k.c-resource-projection.v1", "rove4k.profile-b-source.v1" if family == "B"
                   else "rove4k.portable-phase-source.v1",
                   verify.SPELLING_SCHEMA if family == "B" else verify.F_COMPOUND_SCHEMA if family == "F"
                   else verify.COMPOUND_SCHEMA]
        if family == "E":
            schemas.insert(2, "canonical-e19-physical-binding")
        if scan:
            schemas.append(verify.SCAN_SCHEMA)
        if family in "CE":
            schemas.append(verify.EP_SCHEMA)
        schemas.extend(["rove4k.profile-dependencies.v1", verify.FINAL_COMPACT[family]["schema"]])
        compact = {key: verify.FINAL_COMPACT[family][key] for key in ("path", "variant")}
        return dict(family=family, post=post, proofs=[{"schema": value} for value in schemas],
                    post_spelling=spelling, post_scan=scan, post_ep=verify.EP_DECLARATION if family in "CE" else None,
                    post_compact=compact,
                    source_dependencies={"path": "engines/experiments/tcec-next/profile_dependencies.py",
                                         "variant": "unused-includes"},
                    representation="source-jit", entry_cleanup="private-path", profile_id=profile)

    def test_named_full_routes_and_missing_extra_stages(self):
        for family in "ABCEF":
            values = self.stage_inputs(family)
            with self.subTest(family=family):
                verify.source_stages(**values)
                altered = dict(values, proofs=values["proofs"][:-1])
                with self.assertRaisesRegex(ValueError, "missing, extra, or out of order"):
                    verify.source_stages(**altered)
                altered = dict(values, profile_id="test-p192")
                with self.assertRaisesRegex(ValueError, "named full profile"):
                    verify.source_stages(**altered)
                altered = dict(values, post_compact={"path": "unexpected.py", "variant": "x"})
                with self.assertRaisesRegex(ValueError, "named full profile"):
                    verify.source_stages(**altered)

    def test_control_native_equality_is_checked_for_both_attempts(self):
        before, final, native = b"original source", b"final source", b"native bytes"
        gate = {"directory": "final-compact-control", "source": verify.pin(before),
                "native": verify.pin(native), "image_identical": True}
        manifest = {"compiler": ["cc"], "attempts": [
            {"directory": "first", "final_compact_gate": dict(gate)},
            {"directory": "repeat", "final_compact_gate": dict(gate)}]}
        with patch.object(verify, "checked_artifact", return_value=native) as artifacts, \
             patch.object(verify, "_compound_owned_command", return_value=({}, {})) as commands:
            result = verify.final_compact_evidence(manifest, Path("/tmp/build"), before, final, native)
            self.assertEqual(len(result["attempts"]), 2)
            self.assertEqual(artifacts.call_count, 4)
            self.assertEqual(commands.call_count, 4)
            self.assertEqual(commands.call_args_list[0].args[2], "first-final-compact-control")
            self.assertEqual(commands.call_args_list[1].args[2], "first-compile")
            self.assertEqual(commands.call_args_list[1].args[4], final)
            self.assertEqual(commands.call_args_list[2].args[2], "repeat-final-compact-control")
            self.assertEqual(commands.call_args_list[3].args[2], "repeat-compile")
        manifest["attempts"][1]["final_compact_gate"]["image_identical"] = False
        with patch.object(verify, "checked_artifact", return_value=native), \
             patch.object(verify, "_compound_owned_command", return_value=({}, {})):
            with self.assertRaisesRegex(ValueError, "control gate differs"):
                verify.final_compact_evidence(manifest, Path("/tmp/build"), before, final, native)

    def test_control_compiled_bytes_cannot_be_forged_by_pin(self):
        before, final, native = b"source", b"final", b"native"
        gate = {"directory": "final-compact-control", "source": verify.pin(before),
                "native": verify.pin(native), "image_identical": True}
        manifest = {"compiler": ["cc"], "attempts": [
            {"directory": "first", "final_compact_gate": gate},
            {"directory": "repeat", "final_compact_gate": gate}]}
        with patch.object(verify, "checked_artifact", return_value=b"other"):
            with self.assertRaisesRegex(ValueError, "native differs"):
                verify.final_compact_evidence(manifest, Path("/tmp/build"), before, final, native)


if __name__ == "__main__":
    unittest.main()
