"""Plan adapter tests using synthetic records; no live profile is admitted."""
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import tempfile
import unittest
from unittest.mock import patch

try:
    from . import league_probe, peak_ready_probe
except ImportError:
    import league_probe
    import peak_ready_probe


class LeagueProbeTests(unittest.TestCase):
    def fixture(self, root, profile):
        count = 11 if profile == "test-p16" else 1
        slots = [{"id": f"slot-{i:03d}", "cpus": [i], "physical_cores": [[0, i]],
                  "memory_nodes": [0], "workers": 16 if count == 11 else 192,
                  "smt": True, "policy": "default"} for i in range(count)]
        players = [SimpleNamespace(id=name, path=root / "players" / name,
                    sha256=whole * 64, native_sha256=native * 64, tt_bytes=tt << 30)
                   for name, whole, native, tt in (("A", "a", "b", 12), ("B", "c", "d", 12))]
        body = {"profile": profile, "slots": slots,
                "pairs": [{"players": ["A", "B"], "opening_index": 7}],
                "runner": {"path": "runner/fastchess", "sha256": "e" * 64},
                "opening_pgn": "openings.pgn", "opening_pgn_sha256": "9" * 64,
                "topology": {"ignored": True}}
        return {"sha256": "f" * 64, "content": body}, [{"artifact": player} for player in players]

    def execute(self, root, profile, *, write=False):
        plan = root / "plan.json"
        envelope, rows = self.fixture(root, profile)
        with patch.object(league_probe.run, "load_plan", return_value=(envelope, rows)) as load, \
             patch.object(league_probe.topology.Topology, "from_record", return_value=SimpleNamespace(allowed_cpus=tuple(range(192)))):
            output = root / "probe"
            function = league_probe.write_probe_inputs if write else league_probe.build_probe_inputs
            result = function(plan, output)
            load.assert_called_once_with(plan)
            return result

    def test_p16_uses_all_slots_and_repeated_pairs_swap_colours(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = self.execute(Path(tmp), "test-p16")
            entries = data["manifest"]["entries"]
            self.assertEqual(len(entries), 11)
            self.assertEqual(entries[0]["engines"][0]["id"], "A")
            self.assertEqual(entries[1]["engines"][0]["id"], "B")
            self.assertEqual(entries[0]["engines"][0]["whole_sha256"], "a" * 64)
            self.assertEqual(entries[0]["engines"][0]["native_sha256"], "b" * 64)
            self.assertEqual(data["artifacts"]["slot-000"][0]["whole_sha256"], "a" * 64)
            self.assertNotIn("source_sha256", data["artifacts"]["slot-000"][0])
            self.assertFalse(data["runtime_admission"])
            self.assertFalse(data["scored_qualification"])

    def test_p192_writes_pinned_external_manifest_without_game_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = self.execute(root, "test-p192", write=True)
            manifest_raw = Path(result["manifest_path"]).read_bytes()
            artifacts_raw = Path(result["artifacts_path"]).read_bytes()
            manifest = json.loads(manifest_raw)
            self.assertEqual(manifest["format"], "rove4k-pre-go-controller-v2")
            self.assertEqual(manifest["opening_sha256"], "9" * 64)
            self.assertEqual(len(manifest["entries"]), 1)
            self.assertEqual(hashlib.sha256(manifest_raw).hexdigest(), result["manifest_sha256"])
            self.assertEqual(hashlib.sha256(artifacts_raw).hexdigest(), result["artifacts_sha256"])
            self.assertFalse((root / "probe" / "jobs").exists())

    def test_p16_manifest_round_trips_through_actual_controller_parser(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = self.execute(root, "test-p16", write=True)
            loaded = peak_ready_probe.load_controller_manifest(result["manifest_path"], result["manifest_sha256"])
            self.assertEqual(loaded["profile"], "test-p16")
            self.assertEqual(len(loaded["entries"]), 11)
            self.assertEqual(loaded["entries"][0]["slot"].id, "slot-000")
            self.assertEqual(loaded["entries"][1]["engines"][0]["whole_sha256"], "c" * 64)
            self.assertEqual(loaded["opening_sha256"], "9" * 64)

    def test_invalid_profile_and_existing_output_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(ValueError, "complete named"):
                self.execute(root, "test-p4")
            (root / "probe").mkdir()
            with self.assertRaisesRegex(ValueError, "new absolute output"):
                self.execute(root, "test-p192")

    def test_duplicate_slots_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            envelope, rows = self.fixture(root, "test-p16")
            envelope["content"]["slots"][1]["id"] = "slot-000"
            with patch.object(league_probe.run, "load_plan", return_value=(envelope, rows)):
                with self.assertRaisesRegex(ValueError, "duplicate frozen slot"):
                    league_probe.build_probe_inputs(root / "plan.json", root / "probe")


if __name__ == "__main__":
    unittest.main()
