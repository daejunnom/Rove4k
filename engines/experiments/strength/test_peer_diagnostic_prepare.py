"""Peer diagnostic handoff tests; fake producers never execute engines."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

try:
    from . import peer_diagnostic_prepare as prepare
except ImportError:
    import peer_diagnostic_prepare as prepare


@unittest.skipUnless(sys.platform == "linux", "Linux affinity required")
class PeerPreparationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="rove-peer-diagnostic-")
        self.root = Path(self.tmp.name)
        self.seed_root = self.root / "seed"
        self.seed_root.mkdir()
        (self.seed_root / "seed.json").write_text("{}\n")
        self.source_root = self.seed_root / "external" / "ice4"
        self.source_root.mkdir(parents=True)
        self.spec = prepare.peers.peer_spec("ice4")
        self.seed = {"peers": [{"family": "ice4", "profile": "test-p16", "source": "external/ice4",
                                "repository": self.spec.repository, "revision": self.spec.revision,
                                "license": "external/ice4/LICENSE"}],
                     "members": {"external/ice4/" + name: {} for name in prepare.peers.SOURCE_BLOBS["ice4"]}}
        self.cpu = min(os.sched_getaffinity(0))
        self.seed_sha = "a" * 64

    def tearDown(self):
        self.tmp.cleanup()

    def run_with_fixture(self, *, seed=None, family="ice4", profile="test-p16", out=None):
        seed = seed if seed is not None else self.seed
        calls = []
        def build(family, source_root, out, profile, *, run):
            calls.append((family, source_root, profile))
            out.mkdir()
            attempt = out / "attempt-1"
            attempt.mkdir()
            whole = attempt / self.spec.tiny_name
            whole.write_bytes(b"#!/bin/sh\nexit 0\n")
            manifest = out / "peer.json"
            manifest.write_text("{}\n")
            return {"path": str(manifest), "sha256": prepare.registry.file_sha(manifest)}
        def admit(build, digest):
            path = build.parent / "attempt-1" / self.spec.tiny_name
            return {"layout": prepare.peers.resource_layout(profile),
                    "record": {"whole": {"path": str(path), "bytes": path.stat().st_size,
                                          "sha256": prepare.registry.file_sha(path)}}}
        def reference(build, out, *, manifest_sha, cpu):
            out.mkdir()
            (out / "main.cpp").write_bytes(b"int main(){}\n")
            native = out / "reference-1"
            native.write_bytes(b"fake-native")
            path = out / "reference.json"
            path.write_text("{}\n")
            return {"path": str(path), "sha256": prepare.registry.file_sha(path),
                    "record": {"native": {"path": str(native), "bytes": native.stat().st_size,
                                          "sha256": prepare.registry.file_sha(native)}}}
        with patch.object(prepare.cloud_runtime, "load_seed_manifest", return_value=seed) as loaded, \
             patch.object(prepare.cloud_runtime, "revalidate_seed") as revalidated, \
             patch.object(prepare.cloud_runtime, "validate_host_source") as host_source, \
             patch.object(prepare.peers, "verify_source") as verify_source, \
             patch.object(prepare.peers, "build_resource_tiny", side_effect=build), \
             patch.object(prepare.peer_runtime, "validate_build", side_effect=admit), \
             patch.object(prepare.peer_runtime, "prepare_reference", side_effect=reference), \
             patch.object(prepare.diagnostic_candidates, "_source_evidence", return_value={"source_contract_verified": True}) as evidence:
            result = prepare.prepare(seed_root=self.seed_root, seed_sha256=self.seed_sha, family=family,
                                     profile=profile, cpu=self.cpu, out=out or self.root / "result")
            loaded.assert_called_once_with(self.seed_root / "seed.json", self.seed_sha)
            revalidated.assert_called_once_with(seed, self.seed_root)
            host_source.assert_called_once_with(seed)
            verify_source.assert_called_once_with(family, self.source_root)
            evidence.assert_called_once()
        return result, calls

    def test_candidate_is_replayed_by_existing_candidate_reader(self):
        result, calls = self.run_with_fixture()
        value = json.loads(Path(result["candidate"]["path"]).read_text())
        self.assertEqual(calls, [("ice4", self.source_root, "test-p16")])
        self.assertEqual(value["profile"], "test-p16")
        self.assertEqual(value["candidates"][0]["artifact"]["id"], result["artifact_id"])
        self.assertEqual(value["candidates"][0]["evidence"]["kind"], "peer-reference-v1")
        self.assertEqual(value["candidates"][0]["artifact"]["tt_bytes"], 16 << 30)
        self.assertIn("no engine execution", result["scope"])

    def test_c4ke_p192_preserves_128gib_upstream_profile(self):
        self.spec = prepare.peers.peer_spec("c4ke")
        self.source_root = self.seed_root / "external" / "c4ke"
        self.source_root.mkdir()
        self.seed = {"peers": [{"family": "c4ke", "profile": "test-p192", "source": "external/c4ke",
                                "repository": self.spec.repository, "revision": self.spec.revision,
                                "license": "external/c4ke/LICENSE"}],
                     "members": {"external/c4ke/" + name: {} for name in prepare.peers.SOURCE_BLOBS["c4ke"]}}
        result, _ = self.run_with_fixture(family="c4ke", profile="test-p192")
        value = json.loads(Path(result["candidate"]["path"]).read_text())
        artifact = value["candidates"][0]["artifact"]
        self.assertEqual((artifact["family"], artifact["workers"], artifact["tt_bytes"]),
                         ("c4ke", 192, 128 << 30))

    def test_rejects_changed_revision_license_and_inexact_source_closure_before_build(self):
        for field, value in (("revision", "0" * 40), ("license", "external/ice4/OTHER")):
            with self.subTest(field=field):
                seed = {**self.seed, "peers": [{**self.seed["peers"][0], field: value}]}
                with self.assertRaisesRegex(ValueError, "repository, upstream revision or license"):
                    self.run_with_fixture(seed=seed, out=self.root / ("bad-" + field))
        seed = {**self.seed, "members": {**self.seed["members"], "external/ice4/extra": {}}}
        with self.assertRaisesRegex(ValueError, "source closure"):
            self.run_with_fixture(seed=seed, out=self.root / "bad-closure")

    def test_rejects_duplicate_or_missing_selected_peer_before_build(self):
        for rows in ([], self.seed["peers"] * 2):
            with self.subTest(rows=len(rows)):
                with self.assertRaisesRegex(ValueError, "exactly one"):
                    self.run_with_fixture(seed={**self.seed, "peers": rows}, out=self.root / ("bad-" + str(len(rows))))

    def test_rejects_unsupported_family_profile_and_cpu(self):
        for family, profile, cpu in (("D", "test-p16", self.cpu), ("ice4", "test-p4", self.cpu),
                                     ("ice4", "test-p16", -1)):
            with self.subTest(family=family, profile=profile, cpu=cpu):
                with self.assertRaises(ValueError):
                    prepare.prepare(seed_root=self.seed_root, seed_sha256=self.seed_sha, family=family,
                                    profile=profile, cpu=cpu, out=self.root / "unused")

    def test_requires_a_well_formed_explicit_seed_pin(self):
        for digest in (None, "", "a" * 63, "A" * 64, "x" * 64):
            with self.subTest(digest=digest):
                with self.assertRaisesRegex(ValueError, "seed manifest SHA-256"):
                    prepare.prepare(seed_root=self.seed_root, seed_sha256=digest, family="ice4",
                                    profile="test-p16", cpu=self.cpu, out=self.root / "unused")

    def test_protected_members_are_refused_before_seed_member_reads(self):
        for forbidden in ("x/.env", "x/build/payload", "x/service-account.json", "x/token.json", "x/a.pem"):
            with self.subTest(member=forbidden):
                seed = {**self.seed, "members": {**self.seed["members"], forbidden: {}}}
                with patch.object(prepare.cloud_runtime, "load_seed_manifest", return_value=seed), \
                     patch.object(prepare.cloud_runtime, "revalidate_seed") as revalidated:
                    with self.assertRaises(ValueError):
                        prepare.prepare(seed_root=self.seed_root, seed_sha256=self.seed_sha,
                                        family="ice4", profile="test-p16", cpu=self.cpu,
                                        out=self.root / "unused")
                    revalidated.assert_not_called()

    def test_does_not_overwrite_existing_output(self):
        path = self.root / "existing"
        path.mkdir()
        marker = path / "keep"
        marker.write_text("untouched")
        with self.assertRaises(ValueError):
            self.run_with_fixture(out=path)
        self.assertEqual(marker.read_text(), "untouched")


if __name__ == "__main__":
    unittest.main()
