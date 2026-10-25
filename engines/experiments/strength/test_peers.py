"""Peer intake rejects incorrect identity/resources before any engine execution."""
import importlib.util
import json
import lzma
from pathlib import Path
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
SPEC = importlib.util.spec_from_file_location("strength_peer_test_subject", Path(__file__).with_name("peers.py"))
PEERS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PEERS
SPEC.loader.exec_module(PEERS)


class PeerInputs(unittest.TestCase):
    def test_resource_shift_and_bytes_match_actual_indexing(self):
        # c4ke indexes hash >> TT_SHIFT. The high hash must fit every table.
        for profile, workers, bits, cap in (("test-p4", 4, 24, 128 << 20),
                                             ("test-p28", 28, 26, 512 << 20)):
            layout = PEERS.resource_layout(profile)
            self.assertEqual(layout["workers"], workers)
            self.assertEqual(layout["tt_bits"], bits)
            self.assertEqual(layout["tt_bytes"], cap)
            self.assertEqual(((1 << 64) - 1) >> layout["tt_shift"], layout["tt_entries"] - 1)
        with self.assertRaisesRegex(ValueError, "test-p4 or test-p28"):
            PEERS.resource_layout("tcec-provisional")

    def test_official_wrong_bytes_do_not_create_artifact(self):
        requested = []
        def wrong(url, limit):
            requested.append((url, limit))
            return b"not the official file"
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "bad"
            with self.assertRaisesRegex(ValueError, "release bytes differ"):
                PEERS.intake_official("ice4", out, fetch=wrong)
            self.assertFalse(out.exists())
            self.assertEqual(requested[0][1], 4087)

    def test_source_failure_preserves_incomplete_record(self):
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "source"
            with self.assertRaisesRegex(ValueError, "pinned peer source differs"):
                PEERS.intake_source("c4ke", out, fetch=lambda url, bound: b"tampered")
            record = json.loads((out / "source.json").read_text())
            self.assertFalse(record["complete"])
            self.assertEqual(record["inputs"], {})

    def test_production_patch_requires_pinned_source(self):
        for name in ("ice4", "c4ke"):
            with self.assertRaisesRegex(ValueError, "pinned peer source differs"):
                PEERS.resource_patch(name, b'"THREADS" if tcec => "256"', "test-p4")

    def test_exact_edit_inverse_preserves_all_unedited_bytes(self):
        original = b"prefix resource=256 middle bits=35 suffix\0unrelated=256"
        changed, proof = PEERS.exact_edits(original, [
            ("workers", b"resource=256", b"resource=4"),
            ("bits", b"bits=35", b"bits=24"),
        ])
        self.assertEqual(changed, b"prefix resource=4 middle bits=24 suffix\0unrelated=256")
        self.assertEqual(PEERS.restore_resources(changed, proof), original)
        with self.assertRaisesRegex(ValueError, "differs from its proof"):
            PEERS.restore_resources(changed + b"!", proof)
        with self.assertRaisesRegex(ValueError, "exactly once"):
            PEERS.exact_edits(b"bad=256 bad=256", [("workers", b"bad=256", b"bad=4")])

    def test_outside_git_and_existing_output_guards(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            (base / ".git").mkdir()
            with self.assertRaisesRegex(ValueError, "outside any Git"):
                PEERS.external_new(base / "peer")
            with self.assertRaisesRegex(ValueError, "new absolute"):
                PEERS.external_new(base)
        with self.assertRaisesRegex(ValueError, "new absolute"):
            PEERS.external_new(Path("relative"))

    def test_commands_build_minifier_not_engine_and_do_not_run_shell(self):
        for name in ("ice4", "c4ke"):
            commands, emit = PEERS.minifier_commands(name, Path("/external/source"), Path("/external/out"))
            self.assertEqual(emit[-1], "tcec")
            self.assertNotIn("sh", commands[0])
            self.assertNotIn("compress.sh", " ".join(commands[0]))
            self.assertNotIn("src/main.cpp", " ".join(commands[0]))
        self.assertIn("--locked", PEERS.minifier_commands("ice4", Path("/s"), Path("/o"))[0][0])

    def test_bounded_codec_roundtrip_and_trial_scope(self):
        source = b"#include<bits/stdc++.h>\nint main(){return 0;}\n"
        rows = PEERS.codec_grid(source)
        self.assertEqual(len(rows), 20)
        self.assertEqual(rows[0]["payload_bytes"], min(row["payload_bytes"] for row in rows))
        self.assertTrue(all(lzma.decompress(row["payload"], format=lzma.FORMAT_ALONE) == source for row in rows))
        with self.assertRaisesRegex(ValueError, "unknown bounded"):
            PEERS.codec_grid(source, search="unbounded-upstream")

    @unittest.skipUnless(sys.platform == "linux", "actual process ownership test requires Linux")
    def test_failed_command_preserves_diagnostic_and_timeout_settles(self):
        import os
        cpu = min(os.sched_getaffinity(0))
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            cwd = base / "source"
            cwd.mkdir()
            with self.assertRaisesRegex(RuntimeError, "minifier command failed"):
                PEERS.bounded_run([sys.executable, "-B", "-c", "import sys;sys.stderr.write('fixture failure');sys.exit(7)"],
                                  cwd, timeout=5, cpu=cpu)
            logs = [json.loads(path.read_text()) for path in (base / "command-logs").glob("*.json")]
            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0]["exit_code"], 7)
            self.assertEqual(Path(logs[0]["stderr"]["path"]).read_bytes(), b"fixture failure")
            self.assertTrue(logs[0]["group_absent"])
            with self.assertRaisesRegex(RuntimeError, "minifier command failed"):
                PEERS.bounded_run([sys.executable, "-B", "-c", "import time;time.sleep(5)"],
                                  cwd, timeout=1, cpu=cpu)
            logs = [json.loads(path.read_text()) for path in (base / "command-logs").glob("*.json")]
            self.assertEqual(len(logs), 2)
            timed_out = next(row for row in logs if row["forced_cleanup"])
            self.assertTrue(timed_out["leader_reaped"])
            self.assertTrue(timed_out["group_absent"])


if __name__ == "__main__":
    unittest.main()
