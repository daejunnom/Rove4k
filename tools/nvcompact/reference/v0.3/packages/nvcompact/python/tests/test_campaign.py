"""Coordinator control tests with real output files and mocked engine/replay work.

The fake child result is a subprocess boundary, not UCI or chess evidence.
No real engine is launched by these focused acceptance/publication tests.
"""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_engines


class CampaignTests(unittest.TestCase):
    def run_fixture(self, root, *, same=False, failure=None, raises=False):
        manifests = root / "manifests"
        manifests.mkdir()
        (manifests / "fixture.json").write_text("{}\n")
        output = root / "campaign"
        smallest = b"measured minimum"
        accepted = smallest if same else b"larger verified fallback fixture"
        self.child_calls = []
        self.raw_summary = None

        def search(_manifest, directory, **_options):
            directory.mkdir()
            (directory / "original").write_bytes(b"original fixture" * 8)
            (directory / "smallest").write_bytes(smallest)
            (directory / "accepted").write_bytes(accepted)
            (directory / "accepted").chmod(0o755)
            report = {"original_bytes": 128, "saved_bytes": 128 - len(smallest),
                      "candidates": 2,
                      "winner": {"variant": "raw", "bytes": len(smallest),
                                 "sha256": run_engines.nvenvelope.sha(smallest)},
                      "accepted": {"variant": "raw", "bytes": len(accepted),
                                   "sha256": run_engines.nvenvelope.sha(accepted)},
                      "uci": {"baseline_strict_verdict": "pass",
                              "candidate_strict_verdict": "pass" if same else "fail"}}
            self.raw_summary = json.dumps(report, indent=2) + "\n"
            (directory / "summary.json").write_text(self.raw_summary)
            return report

        def child(argv, _stdin, cwd, **_options):
            self.child_calls.append(list(argv))
            selection = argv[argv.index("--selection") + 1]
            replay_directory = Path(argv[argv.index("--output") + 1])
            replay_directory.mkdir()
            self.assertEqual(Path(cwd), output / "fixture")
            if selection == failure:
                if raises:
                    raise OSError("fixture child launch failed")
                return {"returncode": 2, "stdout": b"", "stderr": b"fixture replay failed\n"}
            (replay_directory / "replay.json").write_text(json.dumps({
                "selection": selection, "byte_replay": "pass",
                "uci": {"verdict": "pass"} if "--uci" in argv else None,
            }))
            return {"returncode": 0, "stdout": b"fixture replay passed\n", "stderr": b""}

        argv = ["run_engines.py", "--manifests", str(manifests), "--output", str(output)]
        with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(run_engines.nvenvelope, "run", side_effect=search), \
                mock.patch.object(run_engines.nvenvelope, "bounded_command", side_effect=child), \
                redirect_stdout(io.StringIO()):
            code = run_engines.main()
        return code, output / "fixture", accepted

    def test_distinct_accepted_file_gets_its_own_replay_and_uci_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            code, directory, accepted = self.run_fixture(Path(temp))
            self.assertEqual(code, 0)
            self.assertEqual([args[args.index("--selection") + 1] for args in self.child_calls],
                             ["smallest", "accepted"])
            self.assertNotIn("--uci", self.child_calls[0])
            self.assertIn("--uci", self.child_calls[1])
            self.assertEqual((directory / "accepted").read_bytes(), accepted)
            self.assertEqual((directory / "summary.json").read_text(), self.raw_summary)
            validation = json.loads((directory / "coordinator-validation.json").read_text())
            self.assertEqual(validation["accepted_verdict"], "pass")
            self.assertEqual([entry["status"] for entry in validation["replays"]], ["pass", "pass"])
            self.assertTrue((directory / "independent-replay-accepted" / "replay.json").is_file())
            row = json.loads((directory.parent / "results.json").read_text())[0]
            self.assertEqual(row["accepted_bytes"], len(accepted))
            self.assertEqual(row["uci"], "fail")  # The measured minimum's failure remains evidence.

    def test_any_external_replay_failure_quarantines_accepted_and_preserves_search_evidence(self):
        for selection, raises in (("smallest", False), ("accepted", False), ("accepted", True)):
            with self.subTest(selection=selection, launch_error=raises), tempfile.TemporaryDirectory() as temp:
                code, directory, accepted = self.run_fixture(Path(temp), failure=selection, raises=raises)
                self.assertEqual(code, 2)
                self.assertFalse((directory / "accepted").exists())
                self.assertEqual((directory / "rejected-campaign").read_bytes(), accepted)
                self.assertEqual((directory / "summary.json").read_text(), self.raw_summary)
                self.assertTrue((directory / "original").is_file())
                self.assertTrue((directory / "smallest").is_file())
                error = json.loads((directory / "campaign-error.json").read_text())
                self.assertEqual(error["validation"]["status"], "error")
                self.assertEqual(error["validation"]["replays"][-1]["selection"], selection)
                self.assertEqual(error["validation"]["accepted_quarantine"]["status"], "quarantined")
                row = json.loads((directory.parent / "results.json").read_text())[0]
                self.assertIsNone(row["accepted_bytes"])
                self.assertEqual(row["independent_replay"], "error")

    def test_byte_identical_minimum_and_accepted_share_one_replay_with_uci(self):
        with tempfile.TemporaryDirectory() as temp:
            code, directory, _accepted = self.run_fixture(Path(temp), same=True)
            self.assertEqual(code, 0)
            self.assertEqual(len(self.child_calls), 1)
            self.assertIn("--uci", self.child_calls[0])
            validation = json.loads((directory / "coordinator-validation.json").read_text())
            self.assertTrue(validation["replays"][0]["also_verifies_accepted"])
            self.assertEqual(validation["accepted_verdict"], "pass")


if __name__ == "__main__":
    unittest.main()
