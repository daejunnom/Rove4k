"""Assembly contract tests only; no live engines or cgroups."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

try:
    from . import peak_probe_session as session, topology
except ImportError:
    import peak_probe_session as session
    import topology


class ProbeSessionTests(unittest.TestCase):
    def run_case(self, *, mismatch=False, missing_node=False, topology_mismatch=False, tt_mismatch=False):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            slot = topology.Slot("slot-000", tuple(range(192)), tuple((0, i) for i in range(96)),
                                 (0, 1), 192, True, "default")
            commands = [{"id": "a", "path": "/a", "whole_sha256": "c" * 64, "native_sha256": "a" * 64, "tt_bytes": 12 << 30},
                        {"id": "b", "path": "/b", "whole_sha256": "d" * 64, "native_sha256": "b" * 64, "tt_bytes": 12 << 30}]
            pair = [{"id": c["id"], "native_sha256": c["native_sha256"],
                     "whole_sha256": c["whole_sha256"], "tt_bytes": 12 << 30} for c in commands]
            if mismatch:
                pair.reverse()
            if tt_mismatch:
                pair[0]["tt_bytes"] -= 1
            manifest = {"profile": "test-p192", "entries": [{"slot": slot, "engines": commands}], "topology": {"synthetic": True, "cpus": [1, 2]},
                        "runner_sha256": "d" * 64}
            game = {"path": str(root / "game"), "cpus": list(slot.cpus), "memory_nodes": list(slot.memory_nodes)}
            controller = {"path": str(root / "controller"), "cpus": list(slot.cpus), "memory_nodes": list(slot.memory_nodes)}
            (root / "game").mkdir()
            (root / "controller").mkdir()
            if missing_node:
                controller["memory_nodes"] = [0]
            with patch.object(session.peak_ready_probe, "load_controller_manifest", return_value=manifest), \
                 patch.object(session.topology.Topology, "snapshot_target", return_value=type("Snapshot", (), {"to_record": lambda self: {"synthetic": not topology_mismatch, "cpus": (1, 2)}})()), \
                 patch.object(session.placement, "verify_cgroup_live", side_effect=lambda record: record), \
                 patch.object(session.overhead, "_sha_file", return_value="e" * 64), \
                 patch.object(Path, "read_text", return_value="12345678-1234-1234-1234-123456789abc"), \
                 patch.object(session.peak_ready_probe, "observe_and_record", return_value=("receipt", "owner")) as observe:
                kwargs = dict(manifest_path=root / "manifest.json", manifest_sha256="f" * 64, root=root,
                              games={slot.id: game}, controller=controller, artifacts={slot.id: pair},
                              report_path=root / "report.json", append=lambda *_: None,
                              per_game_headroom_bytes=1, controller_headroom_bytes=1)
                if mismatch or missing_node or topology_mismatch or tt_mismatch:
                    message = "topology" if topology_mismatch else "memory nodes" if missing_node else "colour order"
                    with self.assertRaisesRegex(ValueError, message):
                        session.observe_ready(**kwargs)
                    observe.assert_not_called()
                    return
                self.assertEqual(session.observe_ready(**kwargs), ("receipt", "owner"))
                args = observe.call_args.kwargs["observe_args"]
                self.assertEqual(args["games"][0]["artifacts"], pair)
                self.assertIn("--manifest-sha256", args["argv"])
                expected = observe.call_args.kwargs["expected_context"]()
                self.assertEqual(expected["plan"][0]["artifacts"], pair)
                self.assertEqual(expected["controller_cgroup_path"], controller["path"])

    def test_builds_pinned_diagnostic_and_independent_context(self):
        self.run_case()

    def test_reversed_artifact_identity_fails_before_supervision(self):
        self.run_case(mismatch=True)

    def test_controller_must_cover_game_nodes_before_supervision(self):
        self.run_case(missing_node=True)

    def test_current_host_topology_must_match_frozen_plan_before_launch(self):
        self.run_case(topology_mismatch=True)

    def test_tt_extent_must_match_frozen_manifest_before_launch(self):
        self.run_case(tt_mismatch=True)


if __name__ == "__main__":
    unittest.main()
