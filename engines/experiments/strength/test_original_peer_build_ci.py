"""Synthetic tests for the build-only CI receipt; no engine is launched."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

import original_peer_build as original
import original_peer_build_ci as subject
import peers


class OriginalPeerBuildCiTests(unittest.TestCase):
    def setUp(self):
        self.peer = "c4ke"
        source = {
            name: {"bytes": 123, "sha256": "a" * 64, "git_blob": peers.SOURCE_BLOBS[self.peer][name]}
            for name in original.source_names(self.peer)
        }
        command = {"exit_code": 0, "leader_reaped": True, "group_absent": True,
                   "original_group_empty_observed_before_reap": True,
                   "physical_group_settlement_proven": False,
                   "forced_cleanup": False, "anchor_home": "/dev/null", "fd_anchor_scope": subject._ANCHOR_SCOPE,
                   "argv": ["DO_NOT_EMIT_EXTERNAL_SOURCE"], "cwd": "/DO_NOT_EMIT_TEMP"}
        self.record = {
            "format": "rove4k-original-peer-build-v1", "purpose": "test-only",
            "peer": self.peer, "profile": "test-p192", "revision": peers.peer_spec(self.peer).revision,
            "source": source, "source_closure_sha256": peers.sha(peers.canonical(source)),
            "source_modified_by_builder": False, "concurrent_source_mutation_excluded": False,
            "complete": True, "same_host_native_reproduced": True, "engines_executed": 0,
            "requested_uci": dict(original._PROFILES["test-p192"]),
            "uci_setup_performed": False,
            "compiler": {"path": "/DO_NOT_EMIT_COMPILER_PATH", "bytes": 500,
                         "sha256": "b" * 64, "flags": list(original._FLAGS[self.peer]),
                         "home_policy": "/dev/null"},
            "attempts": [{"name": f"peer-native-{i}", "bytes": 456,
                          "sha256": "c" * 64, "command": copy.deepcopy(command)} for i in (1, 2)],
            "qualification": dict(subject._QUALIFICATION),
        }
        self.metadata = {"peer": self.peer, "profile": "test-p192", "repo": "daejunnom/Rove4k",
                         "checkout_sha": "d" * 40, "event_sha": "d" * 40, "head_sha": "e" * 40,
                         "event_name": "pull_request",
                         "workflow_ref": "daejunnom/Rove4k/.github/workflows/original-peer-build-trial.yml@refs/pull/12/merge",
                         "run_id": 123, "run_attempt": 2, "cpu": 0, "compiler_cli_version": "13.3.0"}

    def check(self, record=None, **changes):
        metadata = dict(self.metadata, **changes)
        return subject.receipt(self.record if record is None else record, **metadata)

    def test_receipt_excludes_paths_argv_and_runtime_authority(self):
        result = self.check()
        encoded = json.dumps(result, sort_keys=True)
        self.assertNotIn("DO_NOT_EMIT", encoded)
        self.assertIs(result["ci_origin_authenticated"], False)
        self.assertIs(result["physical_group_settlement_proven"], False)
        self.assertIs(result["qualification"]["runtime_qualified"], False)
        self.assertIs(result["qualification"]["scored_game_admitted"], False)
        self.assertIs(result["infrastructure_limits"]["tcec_size_limit_applied"], False)
        self.assertEqual(result["engines_executed"], 0)
        self.assertIs(result["uci_settings_observed"], False)
        self.assertEqual(result["requested_uci_plan"]["hash_mib"], 262144)
        self.assertEqual(result["ci"]["checkout_sha"], "d" * 40)
        self.assertEqual(result["ci"]["pull_request_head_sha"], "e" * 40)

    def test_native_mismatch_and_unsettled_observation_fail(self):
        changed = copy.deepcopy(self.record)
        changed["attempts"][1]["sha256"] = "f" * 64
        with self.assertRaises(ValueError):
            self.check(changed)
        changed = copy.deepcopy(self.record)
        changed["attempts"][0]["command"]["physical_group_settlement_proven"] = True
        with self.assertRaises(ValueError):
            self.check(changed)
        changed["attempts"][0]["command"]["physical_group_settlement_proven"] = False
        changed["attempts"][0]["command"]["leader_reaped"] = False
        with self.assertRaises(ValueError):
            self.check(changed)
        changed = copy.deepcopy(self.record)
        changed["attempts"][0]["command"]["forced_cleanup"] = True
        with self.assertRaises(ValueError):
            self.check(changed)
        changed = copy.deepcopy(self.record)
        del changed["attempts"][0]["command"]["fd_anchor_scope"]
        with self.assertRaises(ValueError):
            self.check(changed)

    def test_qualification_and_boolean_integer_substitution_fail(self):
        for field, value in (("runtime_qualified", True), ("source_blob_identity_checked", 1),
                             ("scored_game_admitted", 0)):
            changed = copy.deepcopy(self.record)
            changed["qualification"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.check(changed)
        changed = copy.deepcopy(self.record)
        changed["engines_executed"] = False
        with self.assertRaises(ValueError):
            self.check(changed)
        changed = copy.deepcopy(self.record)
        changed["uci_setup_performed"] = True
        with self.assertRaises(ValueError):
            self.check(changed)
        changed = copy.deepcopy(self.record)
        changed["requested_uci"]["hash_mib"] = 196608
        with self.assertRaises(ValueError):
            self.check(changed)
        changed = copy.deepcopy(self.record)
        changed["requested_uci"]["workers"] = True
        with self.assertRaises(ValueError):
            self.check(changed)

    def test_source_pin_and_closure_changes_fail(self):
        changed = copy.deepcopy(self.record)
        first = next(iter(changed["source"]))
        changed["source"][first]["git_blob"] = "0" * 40
        changed["source_closure_sha256"] = peers.sha(peers.canonical(changed["source"]))
        with self.assertRaises(ValueError):
            self.check(changed)
        changed = copy.deepcopy(self.record)
        changed["source"][first]["bytes"] = True
        with self.assertRaises(ValueError):
            self.check(changed)
        changed = copy.deepcopy(self.record)
        changed["source_closure_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            self.check(changed)

    def test_metadata_peer_profile_and_compiler_are_bound(self):
        for metadata in ({"event_sha": "f" * 40}, {"head_sha": "invalid"}, {"run_id": True},
                         {"repo": "bad repo"}, {"peer": "ice4"}, {"profile": "test-p16"},
                         {"compiler_cli_version": "13\n3"}, {"head_sha": None},
                         {"workflow_ref": "other/workflow@ref"}):
            with self.subTest(metadata=metadata), self.assertRaises(ValueError):
                self.check(**metadata)
        changed = copy.deepcopy(self.record)
        changed["compiler"]["flags"] = []
        with self.assertRaises(ValueError):
            self.check(changed)
        self.assertIsNone(self.check(head_sha=None, event_name="workflow_dispatch")["ci"]["pull_request_head_sha"])

    def test_failed_intake_neither_builds_nor_writes_a_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt_path = Path(tmp) / "receipt.json"
            argv = ["ci", "--peer", "c4ke", "--profile", "test-p192", "--source", tmp,
                    "--out", str(Path(tmp) / "unused"), "--receipt", str(receipt_path),
                    "--compiler-cli-version", "13.3.0"]
            with (mock.patch.object(sys, "argv", argv),
                  mock.patch.object(subject.os, "sched_getaffinity", return_value={0}, create=True),
                  mock.patch.object(subject, "verify_intake", side_effect=ValueError("intake failed")),
                  mock.patch.object(subject.original, "build") as build):
                with self.assertRaises(ValueError):
                    subject.main()
            build.assert_not_called()
            self.assertFalse(receipt_path.exists())

    def test_protected_source_path_is_rejected_before_opening(self):
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / ".env" / "foreign-input"
            with mock.patch.object(subject.runner, "_open_directory") as open_directory:
                with self.assertRaises(ValueError):
                    subject.verify_intake("c4ke", protected)
            open_directory.assert_not_called()

    def test_duplicate_intake_json_is_rejected_before_source_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            with (mock.patch.object(subject.original, "_outside_checkout", return_value=Path(tmp)),
                  mock.patch.object(subject.runner, "_open_directory", return_value=23),
                  mock.patch.object(subject.original, "_read_regular",
                                    return_value=b'{"peer":"c4ke","peer":"ice4"}') as read,
                  mock.patch.object(subject.os, "close")):
                with self.assertRaises(ValueError):
                    subject.verify_intake("c4ke", Path(tmp))
            self.assertEqual(read.call_count, 1)

    def test_protected_intake_leaf_is_rejected_without_reading_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in (".env", "credentials.json", "id_rsa"):
                manifest = {"peer": "c4ke", "revision": peers.peer_spec("c4ke").revision,
                            "complete": True, "inputs": {name: {}}}
                with (self.subTest(name=name), mock.patch.dict(peers.SOURCE_BLOBS, {"c4ke": {name: "a" * 40}}),
                      mock.patch.object(subject.original, "_outside_checkout", return_value=Path(tmp)),
                      mock.patch.object(subject.runner, "_open_directory", return_value=23),
                      mock.patch.object(subject.original, "_read_regular", return_value=peers.canonical(manifest)) as read,
                      mock.patch.object(subject.os, "close")):
                    with self.assertRaises(ValueError):
                        subject.verify_intake("c4ke", Path(tmp))
                self.assertEqual(read.call_count, 1)


@unittest.skipUnless(sys.platform == "linux" and hasattr(os, "O_NOFOLLOW"), "Linux no-follow required")
class OriginalPeerIntakeTreeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "source"
        (self.root / "src").mkdir(parents=True)
        data = {"src/main.cpp": b"synthetic source\n", "LICENSE": b"synthetic license\n"}
        for name, body in data.items():
            (self.root / name).write_bytes(body)
        pins = {name: peers.git_blob(body) for name, body in data.items()}
        patcher = mock.patch.dict(peers.SOURCE_BLOBS, {"c4ke": pins})
        patcher.start()
        self.addCleanup(patcher.stop)
        inputs = {name: {"bytes": len(body), "sha256": peers.sha(body), "git_blob": peers.git_blob(body)}
                  for name, body in data.items()}
        self.manifest = {"peer": "c4ke", "revision": peers.peer_spec("c4ke").revision,
                         "complete": True, "inputs": inputs,
                         "source_closure_sha256": peers.sha(peers.canonical(inputs))}
        self.write_manifest()

    def write_manifest(self):
        (self.root / "source.json").write_bytes(peers.canonical(self.manifest) + b"\n")

    def test_valid_tree_and_changed_closure(self):
        self.assertEqual(subject.verify_intake("c4ke", self.root), self.root)
        self.manifest["source_closure_sha256"] = "0" * 64
        self.write_manifest()
        with self.assertRaises(ValueError):
            subject.verify_intake("c4ke", self.root)

    def test_parent_symlink_is_rejected(self):
        os.rename(self.root / "src", self.root / "saved-src")
        os.symlink("saved-src", self.root / "src")
        with self.assertRaises((ValueError, OSError)):
            subject.verify_intake("c4ke", self.root)

    def test_hardlinked_leaf_is_rejected(self):
        os.rename(self.root / "src" / "main.cpp", self.root / "owned.cpp")
        os.link(self.root / "owned.cpp", self.root / "src" / "main.cpp")
        with self.assertRaises(ValueError):
            subject.verify_intake("c4ke", self.root)

    def test_duplicate_manifest_and_changed_blob_are_rejected(self):
        (self.root / "source.json").write_bytes(b'{"peer":"c4ke","peer":"c4ke"}')
        with self.assertRaises(ValueError):
            subject.verify_intake("c4ke", self.root)
        self.write_manifest()
        (self.root / "src" / "main.cpp").write_bytes(b"different synthetic source")
        with self.assertRaises(ValueError):
            subject.verify_intake("c4ke", self.root)


if __name__ == "__main__":
    unittest.main()
