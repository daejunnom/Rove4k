"""Peer intake rejects incorrect identity/resources before any engine execution."""
import importlib.util
import json
import lzma
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
SPEC = importlib.util.spec_from_file_location("strength_peer_test_subject", Path(__file__).with_name("peers.py"))
PEERS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PEERS
SPEC.loader.exec_module(PEERS)


class PeerInputs(unittest.TestCase):
    def test_resource_shift_and_bytes_match_actual_indexing(self):
        # c4ke indexes hash >> TT_SHIFT. The high hash must fit every table.
        for profile, workers, bits, extent, cap in (("test-p4", 4, 24, 128 << 20, 128 << 20),
                ("test-p28", 28, 26, 512 << 20, 512 << 20),
                ("test-p16", 16, 31, 16 << 30, 16 << 30),
                ("test-p192", 192, 34, 128 << 30, 192 << 30)):
            layout = PEERS.resource_layout(profile)
            self.assertEqual(layout["workers"], workers)
            self.assertEqual(layout["tt_bits"], bits)
            self.assertEqual(layout["tt_bytes"], extent)
            self.assertLessEqual(layout["tt_bytes"], cap)
            self.assertEqual(((1 << 64) - 1) >> layout["tt_shift"], layout["tt_entries"] - 1)
        with self.assertRaisesRegex(ValueError, "peer score profiles"):
            PEERS.resource_layout("tcec-provisional")

    def test_new_profiles_make_only_resource_edits_and_roundtrip(self):
        # Synthetic minifier fragments test transformation structure only;
        # the production verify_blob boundary remains independently required.
        source = {
            "ice4": (b'prefix \'thread marker\' "THREADS" if tcec => "256"\n'
                     b'"DEFAULT_TT_BITS" if tcec => "35"\nprotected algorithm suffix'),
            "c4ke": (b'prefix\nif (is_tcec && name == "THREADS") {\n            value = "256";\n        }\n'
                     b'if (is_tcec && name == "TT_BITS") {\n            value = "35";\n        }\n'
                     b'if (is_tcec && name == "TT_SHIFT") {\n            value = "29";\n        }\nprotected algorithm suffix'),
        }
        for profile, workers, bits, shift in (("test-p16", 16, 31, 33), ("test-p192", 192, 34, 30)):
            for name, original in source.items():
                with self.subTest(profile=profile, peer=name), patch.object(PEERS, "verify_blob") as verified:
                    changed, proof = PEERS.resource_patch(name, original, profile)
                    verified.assert_called_once_with(name, PEERS.PEERS[name].resource_path, original)
                    self.assertEqual(PEERS.restore_resources(changed, proof), original)
                    self.assertEqual(proof["resources"], PEERS.resource_layout(profile))
                    self.assertEqual(proof["profile"], profile)
                    self.assertEqual({edit["role"] for edit in proof["edits"]},
                                     {"workers", "tt_bits"} if name == "ice4" else {"workers", "tt_bits", "tt_shift"})
                    for value in (workers, bits):
                        self.assertIn(('"' + str(value) + '"').encode(), changed)
                    if name == "c4ke":
                        self.assertIn(('"' + str(shift) + '"').encode(), changed)
                    self.assertTrue(changed.endswith(b"protected algorithm suffix"))
                    with self.assertRaisesRegex(ValueError, "differs from its proof"):
                        PEERS.restore_resources(changed + b"!", proof)

    def test_profile_cap_fails_closed_if_resource_constants_drift(self):
        with patch.dict(PEERS.RESOURCE_PROFILES, {"test-p16": (16, 32)}):
            with self.assertRaisesRegex(ValueError, "TT extent exceeds"):
                PEERS.resource_layout("test-p16")

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
        self.assertTrue(all("lc" not in row for row in rows))
        self.assertEqual(rows[0]["payload_bytes"], min(row["payload_bytes"] for row in rows))
        self.assertTrue(all(lzma.decompress(row["payload"], format=lzma.FORMAT_ALONE) == source for row in rows))
        with self.assertRaisesRegex(ValueError, "unknown bounded"):
            PEERS.codec_grid(source, search="unbounded-upstream")

    def test_literal_search_roundtrips_repeats_and_orders_ties(self):
        source = b"#include<bits/stdc++.h>\nint main(){return 0;}\n" * 3
        real_compress = lzma.compress
        seen = []

        def small_fixture(data, *, format, filters):
            # Keep the test bounded; production still uses the original preset dictionary.
            self.assertEqual(format, lzma.FORMAT_ALONE)
            self.assertEqual((filters[0]["lp"], filters[0]["pb"]), (0, 0))
            seen.append((filters[0]["lc"], filters[0]["mf"], filters[0]["nice_len"]))
            return real_compress(data, format=format, filters=[dict(filters[0], dict_size=65536)])

        with patch.object(PEERS.lzma, "compress", side_effect=small_fixture):
            rows = PEERS.codec_grid(source, search="literal-v1")
            repeated = PEERS.codec_grid(source, search="literal-v1")
        self.assertEqual(len(rows), 80)
        self.assertEqual(rows, repeated)
        self.assertEqual(len(set(seen)), 80)
        self.assertEqual(len(seen), 160)
        self.assertEqual({row["lc"] for row in rows}, {0, 1, 3, 4})
        for row in rows:
            self.assertEqual(row["payload"][0], row["lc"])
            self.assertEqual(lzma.decompress(row["payload"], format=lzma.FORMAT_ALONE), source)
            self.assertEqual(row["payload_sha256"], PEERS.sha(row["payload"]))
        keys = [(row["payload_bytes"], row["mf"], row["nice_len"], row["lc"]) for row in rows]
        self.assertEqual(keys, sorted(keys))
        self.assertLess(len({key[0] for key in keys}), len(keys))  # exercises tie ordering

    def test_existing_codec_profiles_retain_previous_rows(self):
        source = b"int main(){return 0;}\n" * 3
        real_compress = lzma.compress

        def small_fixture(data, *, format, filters):
            return real_compress(data, format=format, filters=[dict(filters[0], dict_size=65536)])

        for search in ("compact", "extended"):
            expected = []
            for finder in (lzma.MF_HC3, lzma.MF_HC4, lzma.MF_BT2, lzma.MF_BT3, lzma.MF_BT4):
                for nice in PEERS.CODEC_SEARCHES[search]:
                    payload = small_fixture(source, format=lzma.FORMAT_ALONE,
                        filters=[{"id": lzma.FILTER_LZMA1, "preset": 9 | lzma.PRESET_EXTREME,
                                  "lc": 2, "lp": 0, "pb": 0, "mf": finder, "nice_len": nice}])
                    expected.append({"mf": finder, "nice_len": nice, "payload": payload,
                                     "payload_bytes": len(payload), "payload_sha256": PEERS.sha(payload)})
            expected.sort(key=lambda row: (row["payload_bytes"], row["mf"], row["nice_len"]))
            with self.subTest(search=search), patch.object(PEERS.lzma, "compress", side_effect=small_fixture):
                self.assertEqual(PEERS.codec_grid(source, search=search), expected)

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
