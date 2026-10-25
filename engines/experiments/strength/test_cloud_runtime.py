"""Local transport and authority rejection tests; no engines or AWS sessions."""
from dataclasses import dataclass, replace
import copy
import io
import json
import subprocess
from pathlib import Path, PurePosixPath
import tempfile
import unittest
from unittest.mock import Mock, patch
import zipfile

try:
    from . import cloud_runtime as cloud
except ImportError:
    import cloud_runtime as cloud


def seed_fixture():
    files = {
        "source/engines/experiments/strength/cloud_runtime.py": b"# source fixture, never imported\n",
        "rove/A/build.json": b"{}\n",
        "rove/source-bundle.zip": b"original sealed source bytes",
        "rove/source-seal.json": b"{}\n",
        "rove/rules.json": b"{}\n",
        "bank/bank.json": b"{}\n",
        "bank/broad.pgn": b"1. e4 e5 *\n",
        "bank/high.pgn": b"1. d4 d5 *\n",
        "external/fastchess.bundle": b"explicit transport fixture, never cloned",
    }
    seed = {"format": "rove4k-cloud-seed-v1",
            "source_origin": {"repository": "daejunnom/Rove4k", "head_sha": "a" * 40,
                              "run_id": "123", "run_attempt": "1"},
            "members": {name: {**cloud.pin(data), "mode": 0o600} for name, data in files.items()},
            "source_tree": "source", "rove": [{"family": "A", "profile": "test-p4", "build": "rove/A",
                "source_bundle": "rove/source-bundle.zip", "source_seal": "rove/source-seal.json", "rules": "rove/rules.json"}],
            "peers": [], "bank": "bank/bank.json", "bank_pgns": {"broad": "bank/broad.pgn", "high": "bank/high.pgn"},
            "runner": {"revision": "ebfd64cb7fac80d4822c50b07dca4fe934779d21",
                "checkout": "external/fastchess", "transport": "external-git-bundle", "bundle": "external/fastchess.bundle"}}
    seed["original_layout"] = {"format": "rove4k-original-layout-plan-v1", "roots": [{
        "original_root": "/home/runner/work/_temp/rove-seed-fixture", "seed_prefix": "rove",
        "files": {name[len("rove/"):]: cloud.pin(data) for name, data in files.items() if name.startswith("rove/")}}]}
    return seed, files


def archive_bytes(seed, files, extras=None):
    raw = cloud.ledger.canonical(seed) + b"\n"
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("seed.json", raw)
        for name, data in files.items():
            archive.writestr(name, data)
        for name, data in extras or []:
            archive.writestr(name, data)
    return output.getvalue(), cloud.pin(raw)["sha256"]


class TransportTests(unittest.TestCase):
    def test_exact_seed_roundtrip_is_prequalification_and_keeps_bytes(self):
        seed, files = seed_fixture()
        raw, sha = archive_bytes(seed, files)
        with tempfile.TemporaryDirectory(prefix="rove-cloud-transport-") as tmp:
            root = Path(tmp)
            (root / "input.zip").write_bytes(raw)
            actual = cloud.materialize_seed_archive(root / "input.zip", root / "restored", expected_manifest_sha256=sha)
            self.assertEqual(actual, seed)
            self.assertNotIn("qualified", actual)
            cloud.revalidate_seed(actual, root / "restored")
            for name, data in files.items():
                self.assertEqual((root / "restored" / name).read_bytes(), data)

    def reject_archive(self, seed, files, *, extras=None, sha_override=None):
        raw, sha = archive_bytes(seed, files, extras)
        with tempfile.TemporaryDirectory(prefix="rove-cloud-reject-") as tmp:
            root = Path(tmp)
            (root / "input.zip").write_bytes(raw)
            with self.assertRaises(ValueError):
                cloud.materialize_seed_archive(root / "input.zip", root / "restored",
                                               expected_manifest_sha256=sha_override or sha)
            self.assertFalse((root / "restored").exists())

    def test_manifest_sha_cannot_be_replaced_by_member_pins(self):
        seed, files = seed_fixture()
        self.reject_archive(seed, files, sha_override="f" * 64)

    def test_changed_member_rejected_before_extraction(self):
        seed, files = seed_fixture()
        files["rove/A/build.json"] += b"changed"
        self.reject_archive(seed, files)

    def test_extra_or_duplicate_archive_member_rejected(self):
        seed, files = seed_fixture()
        self.reject_archive(seed, files, extras=[("unexpected.txt", b"extra")])
        self.reject_archive(seed, files, extras=[("rove/A/build.json", b"{}\n")])

    def test_traversal_and_protected_paths_rejected_without_reading(self):
        for name in ("../escape", "/absolute", "foo\\bar", "x/.env", "x/.env.local", "x/credentials.json",
                     "x/inventory.json", "x/.aws/config", "x/package-lock.json", "x/node_modules/a"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                cloud.member(name)

    def test_seed_cannot_claim_qualification_or_submission_profile(self):
        seed, _ = seed_fixture()
        for field in ("qualified", "complete", "native_map", "registry"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                cloud.validate_seed_manifest({**seed, field: True})
        seed["rove"][0]["profile"] = "tcec-provisional"
        with self.assertRaises(ValueError):
            cloud.validate_seed_manifest(seed)

    def test_file_directory_collision_rejected(self):
        seed, _ = seed_fixture()
        seed["members"]["rove"] = {**cloud.pin(b"file"), "mode": 0o600}
        with self.assertRaises(ValueError):
            cloud.validate_seed_manifest(seed)

    def test_materialized_input_change_detected(self):
        seed, files = seed_fixture()
        raw, sha = archive_bytes(seed, files)
        with tempfile.TemporaryDirectory(prefix="rove-cloud-mutated-") as tmp:
            root = Path(tmp)
            (root / "input.zip").write_bytes(raw)
            cloud.materialize_seed_archive(root / "input.zip", root / "restored", expected_manifest_sha256=sha)
            (root / "restored/rove/A/build.json").write_bytes(b"changed")
            with self.assertRaises(ValueError):
                cloud.revalidate_seed(seed, root / "restored")

    def test_materialized_manifest_cannot_be_reencoded_after_transport(self):
        seed, files = seed_fixture()
        raw, sha = archive_bytes(seed, files)
        with tempfile.TemporaryDirectory(prefix="rove-cloud-manifest-mutated-") as tmp:
            root = Path(tmp)
            (root / "input.zip").write_bytes(raw)
            cloud.materialize_seed_archive(root / "input.zip", root / "restored", expected_manifest_sha256=sha)
            (root / "restored/seed.json").write_bytes(json.dumps(seed, indent=2).encode())
            with self.assertRaisesRegex(ValueError, "seed manifest changed"):
                cloud.revalidate_seed(seed, root / "restored")

    def test_s3_explicit_version_body_closed_and_hash_checked(self):
        raw = b"versioned immutable archive bytes"
        body = io.BytesIO(raw)
        s3 = Mock()
        s3.get_object.return_value = {"VersionId": "version-1", "ContentLength": len(raw), "Body": body}
        descriptor = cloud.SeedObject("rove-artifacts", "campaign/seed.zip", "version-1", cloud.pin(raw)["sha256"], len(raw))
        with tempfile.TemporaryDirectory(prefix="rove-cloud-s3-") as tmp:
            path = cloud.fetch_seed(descriptor, s3, Path(tmp) / "seed.zip")
            self.assertEqual(path.read_bytes(), raw)
        s3.get_object.assert_called_once_with(Bucket="rove-artifacts", Key="campaign/seed.zip", VersionId="version-1")
        self.assertTrue(body.closed)

    def test_wrong_s3_version_or_hash_does_not_create_output(self):
        for version, body in (("wrong", b"body"), ("version-1", b"evil")):
            with self.subTest(version=version), tempfile.TemporaryDirectory(prefix="rove-cloud-s3-fault-") as tmp:
                stream = io.BytesIO(body)
                s3 = Mock()
                s3.get_object.return_value = {"VersionId": version, "ContentLength": 4, "Body": stream}
                seed = cloud.SeedObject("rove-artifacts", "campaign/seed.zip", "version-1", cloud.pin(b"body")["sha256"], 4)
                with self.assertRaises(ValueError):
                    cloud.fetch_seed(seed, s3, Path(tmp) / "seed.zip")
                self.assertFalse((Path(tmp) / "seed.zip").exists())
                self.assertTrue(stream.closed)

    def test_unversioned_s3_seed_is_rejected(self):
        for version in ("", "null"):
            with self.subTest(version=version), self.assertRaises(ValueError):
                cloud.SeedObject("rove-artifacts", "campaign/seed.zip", version, "a" * 64, 4)


class SeedCapacityTests(unittest.TestCase):
    """Large expansion is declared as metadata; no large ZIP or payload is made."""
    @staticmethod
    def selection(*, joint=False):
        profiles = ("test-p4", "test-p28") if joint else ("test-p4",)
        return {"rove": [{"family": family, "profile": profile} for family in "ABCDEF" for profile in profiles],
                "peers": []}

    def manifest(self, *, joint=False, chunks=0):
        seed, files = seed_fixture()
        if joint:
            original = seed["rove"][0]
            seed["rove"] = [{**original, **row} for row in self.selection(joint=True)["rove"]]
        for index in range(chunks):
            name = "padding/chunk-" + str(index)
            seed["members"][name] = {"bytes": cloud.MAX_MEMBER, "sha256": "0" * 64, "mode": 0o600}
            files[name] = b""  # Metadata-only fixture, never actual payload admission.
        return seed, files

    def inspect_metadata(self, seed, files, expected=None):
        raw, sha = archive_bytes(seed, files)
        archive = zipfile.ZipFile(io.BytesIO(raw))
        for name, value in seed["members"].items():
            archive.getinfo(name).file_size = value["bytes"]
        return archive, sha

    def test_exact_joint_rove_keys_alone_grant_larger_capacity(self):
        self.assertEqual(cloud.MAX_SEED, 128 << 20)
        self.assertEqual(cloud.MAX_SEED_MANIFEST, 4 << 20)
        self.assertEqual(cloud.JOINT_EXPANDED_SEED, 256 << 20)
        self.assertEqual(cloud.MAX_MEMBER, 32 << 20)
        self.assertEqual(cloud.MAX_SEED_MEMBERS, 20000)
        cases = [(self.selection(), cloud.MAX_SEED), (self.selection(joint=True), cloud.JOINT_EXPANDED_SEED),
                 ({"rove": [], "peers": [{"family": "ice4", "profile": "test-p28"}]}, cloud.MAX_SEED)]
        joint = self.selection(joint=True)
        joint["peers"] = [{"family": family, "profile": profile} for family in ("ice4", "c4ke")
                          for profile in ("test-p4", "test-p28")]
        cases += [(joint, cloud.JOINT_EXPANDED_SEED),
                  ({**joint, "rove": joint["rove"][:-1]}, cloud.MAX_SEED),
                  ({**joint, "rove": [row for row in joint["rove"] if row["profile"] == "test-p28"]}, cloud.MAX_SEED)]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(cloud.seed_expansion_limit(value), expected)

    def test_capacity_predicate_rejects_malformed_unknown_empty_and_duplicate_rows(self):
        base = {"rove": [{"family": "A", "profile": "test-p4"}], "peers": []}
        bad = [None, [], {}, {"rove": [], "peers": []}, {"rove": None, "peers": []},
               {"rove": [], "peers": {}}, {"rove": [None], "peers": []},
               {"rove": [{"family": [], "profile": "test-p4"}], "peers": []},
               {"rove": [{"family": "A", "profile": ["test-p4"]}], "peers": []},
               {"rove": [{"family": "G", "profile": "test-p4"}], "peers": []},
               {"rove": [{"family": "A", "profile": "tcec-provisional"}], "peers": []},
               {**base, "rove": base["rove"] * 2},
               {**base, "peers": [{"family": "A", "profile": "test-p28"}]},
               {**base, "peers": [{"family": "ice4", "profile": "test-p28"}] * 2}]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(ValueError):
                cloud.seed_expansion_limit(value)

    def test_member_plus_canonical_manifest_exact_capacity_boundary(self):
        for joint, count in ((False, 4), (True, 8)):
            seed, _ = self.manifest(joint=joint, chunks=count)
            cap = cloud.seed_expansion_limit(seed)
            last = seed["members"]["padding/chunk-" + str(count - 1)]
            for _ in range(8):
                total = sum(row["bytes"] for row in seed["members"].values()) + len(cloud.ledger.canonical(seed) + b"\n")
                if total == cap:
                    break
                last["bytes"] += cap - total
            self.assertEqual(sum(row["bytes"] for row in seed["members"].values()) +
                             len(cloud.ledger.canonical(seed) + b"\n"), cap)
            self.assertEqual(cloud.validate_seed_manifest(seed), seed)
            last["bytes"] += 1
            with self.assertRaisesRegex(ValueError, "including manifest exceeds"):
                cloud.validate_seed_manifest(seed)

    def test_total_entry_count_includes_the_manifest_metadata_only(self):
        seed, _ = seed_fixture()
        count = cloud.MAX_SEED_MEMBERS - 1 - len(seed["members"])
        seed["members"].update({"padding/" + str(index): {**cloud.pin(b""), "mode": 0o600}
                                for index in range(count)})
        self.assertEqual(len(seed["members"]), 19999)
        cloud.validate_seed_manifest(seed)
        seed["members"]["padding/overflow"] = {**cloud.pin(b""), "mode": 0o600}
        with self.assertRaisesRegex(ValueError, "including seed.json"):
            cloud.validate_seed_manifest(seed)

    def test_zip_aggregate_is_decided_after_manifest_and_before_any_payload_read(self):
        for joint, chunks, allowed in ((False, 4, False), (True, 4, True), (True, 8, False)):
            seed, files = self.manifest(joint=joint, chunks=chunks)
            archive, sha = self.inspect_metadata(seed, files)
            with archive:
                opened = []
                actual_open = archive.open
                def recorded_open(info, *args, **kwargs):
                    opened.append(info.filename)
                    return actual_open(info, *args, **kwargs)
                with patch.object(archive, "open", side_effect=recorded_open):
                    if allowed:
                        manifest, raw, infos = cloud.seed_archive_manifest(archive, expected_manifest_sha256=sha)
                        self.assertEqual(manifest, seed)
                        self.assertEqual(raw, cloud.ledger.canonical(seed) + b"\n")
                        self.assertEqual(len(infos), len(files) + 1)
                    else:
                        with self.assertRaisesRegex(ValueError, "expansion bound|expansion exceeds"):
                            cloud.seed_archive_manifest(archive, expected_manifest_sha256=sha)
                self.assertEqual(opened, [] if joint and chunks == 8 else ["seed.json"])

    def test_unsafe_zip_metadata_is_rejected_before_even_manifest_read(self):
        seed, files = seed_fixture()
        raw, sha = archive_bytes(seed, files)
        for fault in ("encrypted", "link", "large-member", "large-manifest", "too-many", "protected"):
            with self.subTest(fault=fault), zipfile.ZipFile(io.BytesIO(raw)) as archive:
                info = archive.getinfo("bank/broad.pgn")
                if fault == "encrypted":
                    info.flag_bits |= 1
                elif fault == "link":
                    info.external_attr = (0o120777 << 16)
                elif fault == "large-member":
                    info.file_size = cloud.MAX_MEMBER + 1
                elif fault == "large-manifest":
                    archive.getinfo("seed.json").file_size = cloud.MAX_SEED_MANIFEST + 1
                elif fault == "protected":
                    info.filename = "protected/.env"
                else:
                    archive.filelist = [info] * (cloud.MAX_SEED_MEMBERS + 1)
                with patch.object(archive, "open", side_effect=AssertionError("unsafe metadata must not be read")), \
                     self.assertRaises(ValueError):
                    cloud.seed_archive_manifest(archive, expected_manifest_sha256=sha)

    def test_controller_sha_precedes_json_validation_and_member_lengths_precede_payload(self):
        seed, files = seed_fixture()
        raw, sha = archive_bytes(seed, files)
        with zipfile.ZipFile(io.BytesIO(raw)) as archive, \
             patch.object(cloud, "validate_seed_manifest", side_effect=AssertionError("untrusted manifest not parsed")):
            with self.assertRaisesRegex(ValueError, "controller pin"):
                cloud.seed_archive_manifest(archive, expected_manifest_sha256="f" * 64)
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            archive.getinfo("bank/broad.pgn").file_size += 1
            original, opened = archive.open, []
            def recorded_open(info, *args, **kwargs):
                opened.append(info.filename)
                return original(info, *args, **kwargs)
            with patch.object(archive, "open", side_effect=recorded_open), \
                 self.assertRaisesRegex(ValueError, "member differs in length"):
                cloud.seed_archive_manifest(archive, expected_manifest_sha256=sha)
            self.assertEqual(opened, ["seed.json"])

    def test_manifest_read_load_and_revalidate_use_the_separate_manifest_bound(self):
        seed, files = seed_fixture()
        raw, sha = archive_bytes(seed, files)
        manifest_raw = cloud.ledger.canonical(seed) + b"\n"
        with tempfile.TemporaryDirectory(prefix="rove-seed-manifest-bound-") as tmp:
            root = Path(tmp)
            (root / "input.zip").write_bytes(raw)
            cloud.materialize_seed_archive(root / "input.zip", root / "restored", expected_manifest_sha256=sha)
            self.assertEqual(cloud.load_seed_manifest(root / "restored/seed.json", sha), seed)
            with patch.object(cloud, "MAX_SEED_MANIFEST", len(manifest_raw) - 1):
                with self.assertRaisesRegex(ValueError, "manifest exceeds"):
                    cloud.validate_seed_manifest(seed)
                with self.assertRaises(ValueError):
                    cloud.load_seed_manifest(root / "restored/seed.json", sha)
                with self.assertRaises(ValueError):
                    cloud.revalidate_seed(seed, root / "restored")
                with self.assertRaises(ValueError):
                    cloud.materialize_seed_archive(root / "input.zip", root / "rejected", expected_manifest_sha256=sha)
            self.assertFalse((root / "rejected").exists())

    def test_member_schema_types_and_reserved_manifest_prefix_reject_before_payload_read(self):
        for fault in ("numeric-sha", "float-mode", "string-mode", "reserved-prefix"):
            with self.subTest(fault=fault):
                seed, files = seed_fixture()
                value = seed["members"]["bank/broad.pgn"]
                if fault == "numeric-sha":
                    value["sha256"] = int("1" * 64)
                elif fault == "float-mode":
                    value["mode"] = float(0o600)
                elif fault == "string-mode":
                    value["mode"] = str(0o600)
                else:
                    seed["members"]["seed.json/child"] = {**cloud.pin(b""), "mode": 0o600}
                    files["seed.json/child"] = b""
                with self.assertRaisesRegex(ValueError, "bounded seed member pin/mode"):
                    cloud.validate_seed_manifest(seed)
                raw, sha = archive_bytes(seed, files)
                with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                    actual_open, opened = archive.open, []
                    def manifest_only(info, *args, **kwargs):
                        opened.append(info.filename)
                        self.assertEqual(info.filename, "seed.json", "invalid schema must stop before payload")
                        return actual_open(info, *args, **kwargs)
                    with patch.object(archive, "open", side_effect=manifest_only), \
                         self.assertRaisesRegex(ValueError, "bounded seed member pin/mode"):
                        cloud.seed_archive_manifest(archive, expected_manifest_sha256=sha)
                    self.assertEqual(opened, ["seed.json"])

    def test_secondary_manifest_rereads_bound_a_mutation_before_reading_bytes(self):
        # Simulate a file growing after the earlier full validation.  The
        # ordinary-file port rejects its metadata without allocating the body.
        # Authority/restore checks are separate fake ports here; this test
        # stops at the subsequent seed read and never issues a reference.
        seed, _ = seed_fixture()
        manifest_raw = cloud.ledger.canonical(seed) + b"\n"
        with tempfile.TemporaryDirectory(prefix="rove-secondary-manifest-bound-") as tmp:
            root = Path(tmp) / "seed"
            build, native = root / "rove/A", root / "native"
            reads = []
            def ordinary_metadata(path, *, limit=cloud.MAX_MEMBER):
                path = Path(path)
                if path.name == "seed.json":
                    reads.append((path, limit))
                    if cloud.MAX_SEED_MANIFEST + 1 > limit:
                        raise ValueError("oversized manifest rejected by metadata before read")
                    self.fail("secondary seed read would admit the oversized manifest body")
                self.assertEqual(path, native)
                return b"native"
            layout = cloud.OriginalLayout(cloud._VALIDATED,
                {"seed_root": str(root), "seed_manifest": cloud.pin(manifest_raw), "roots": []}, seed)
            with patch.object(cloud, "ordinary", side_effect=ordinary_metadata), \
                 patch.object(cloud, "revalidate_seed"):
                with self.assertRaisesRegex(ValueError, "before read"):
                    layout.revalidate()
                without_roots = {**seed, "rove": [], "original_layout": {
                    "format": "rove4k-original-layout-plan-v1", "roots": []}}
                with patch.object(cloud.sys, "platform", "linux"), \
                     self.assertRaisesRegex(ValueError, "before read"):
                    cloud.restore_original_layout(without_roots, root)
                context = {"fixture": "bounded read port only"}
                consumer = cloud.CloudConsumer(cloud._VALIDATED, {"compiler_context": context}, ())
                admitted = cloud.types.SimpleNamespace(family="A", profile_id="test-p4",
                    representation="source-jit", expected={"unchanged": True})
                verify = Mock()
                verify.cloud_runtime_supported.return_value = True
                verify.cloud_compiler_binding.return_value = {"native_path": str(native),
                    "native": cloud.pin(b"native"), "compiler_context": context,
                    "compiler_inputs": {"fixture": True}, "evidence": {}}
                with patch.object(cloud.CloudConsumer, "revalidate"), \
                     patch.object(cloud.OriginalLayout, "revalidate"), \
                     patch.object(cloud.OriginalLayout, "execution_path", return_value=build), \
                     patch.object(cloud, "CloudRuntimeReference", side_effect=AssertionError("no fixture authority")), \
                     self.assertRaisesRegex(ValueError, "before read"):
                    cloud.validate_cloud_runtime(admitted, build, root / "compiler.json", seed=seed, root=root,
                        row=seed["rove"][0], consumer=consumer, verify=verify, restored_layout=layout)
            self.assertEqual(len(reads), 3)
            self.assertEqual({limit for _, limit in reads}, {cloud.MAX_SEED_MANIFEST})


class ProducerConsumerRoundTripTests(unittest.TestCase):
    """Real producer/consumer byte contract; synthetic transport is not CI admission.

    The existing producer fixture replaces only external Fastchess Git bundle
    verification/list-heads. All manifest, archive, member and restore checks
    remain the actual production functions. No engine or service is invoked.
    """
    def prepared(self, root):
        try:
            from . import seed as producer
            from .test_seed import Fixture
        except ImportError:
            import seed as producer
            from test_seed import Fixture
        fixture = Fixture(root)
        receipt = fixture.prepare(root / "prepared")
        raw = Path(receipt["archive"]["path"]).read_bytes()
        return producer, receipt, raw

    @staticmethod
    def rewritten(raw, *, seed_transform=None, member_transform=None):
        output = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(raw)) as original, zipfile.ZipFile(output, "w") as changed:
            for item in original.infolist():
                body = original.read(item)
                if item.filename == "seed.json" and seed_transform is not None:
                    body = seed_transform(body)
                elif item.filename != "seed.json" and member_transform is not None:
                    body = member_transform(item.filename, body)
                changed.writestr(copy.copy(item), body)
        return output.getvalue()

    def test_actual_prepare_inspect_materialize_revalidate_uses_one_canonical_lf(self):
        with tempfile.TemporaryDirectory(prefix="rove-producer-consumer-") as tmp:
            root = Path(tmp)
            producer, receipt, raw = self.prepared(root)
            inspection = producer.inspect_archive(raw)
            manifest_raw = Path(receipt["seed_manifest"]["path"]).read_bytes()
            manifest = json.loads(manifest_raw)
            self.assertEqual(manifest_raw, cloud.ledger.canonical(manifest) + b"\n")
            self.assertFalse(manifest_raw.endswith(b"\n\n"))
            self.assertEqual(inspection["manifest_sha256"], cloud.pin(manifest_raw)["sha256"])
            self.assertEqual(inspection["manifest_sha256"], receipt["seed_manifest"]["sha256"])
            restored = cloud.materialize_seed_archive(Path(receipt["archive"]["path"]), root / "restored",
                expected_manifest_sha256=inspection["manifest_sha256"])
            cloud.revalidate_seed(restored, root / "restored")
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                for name in archive.namelist():
                    self.assertEqual((root / "restored" / name).read_bytes(), archive.read(name))
            self.assertFalse(receipt["native_qualified"] or receipt["engine_executed"] or receipt["aws_calls_performed"])
            self.assertNotIn("qualified", restored)

    def test_actual_producer_archive_without_lf_or_with_double_lf_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="rove-producer-canonical-fault-") as tmp:
            root = Path(tmp)
            producer, receipt, raw = self.prepared(root)
            for label, transform in (("no-lf", lambda body: body[:-1]), ("double-lf", lambda body: body + b"\n")):
                with self.subTest(fault=label):
                    changed = self.rewritten(raw, seed_transform=transform)
                    with zipfile.ZipFile(io.BytesIO(changed)) as archive:
                        manifest_sha = cloud.pin(archive.read("seed.json"))["sha256"]
                    with self.assertRaisesRegex(ValueError, "canonical"):
                        producer.inspect_archive(changed)
                    path, destination = root / (label + ".zip"), root / label
                    path.write_bytes(changed)
                    with self.assertRaisesRegex(ValueError, "canonical"):
                        cloud.materialize_seed_archive(path, destination, expected_manifest_sha256=manifest_sha)
                    self.assertFalse(destination.exists())

    def test_changed_manifest_cannot_replace_the_original_controller_pin(self):
        with tempfile.TemporaryDirectory(prefix="rove-producer-manifest-fault-") as tmp:
            root = Path(tmp)
            producer, receipt, raw = self.prepared(root)
            def change(body):
                value = json.loads(body)
                value["source_origin"]["repository"] = "other/transport-fixture"
                return cloud.ledger.canonical(value) + b"\n"
            changed = self.rewritten(raw, seed_transform=change)
            inspected = producer.inspect_archive(changed)
            self.assertNotEqual(inspected["manifest_sha256"], receipt["seed_manifest"]["sha256"])
            path = root / "changed.zip"
            path.write_bytes(changed)
            with self.assertRaisesRegex(ValueError, "controller pin"):
                cloud.materialize_seed_archive(path, root / "restored",
                    expected_manifest_sha256=receipt["seed_manifest"]["sha256"])
            self.assertFalse((root / "restored").exists())

    def test_changed_actual_archive_member_and_materialized_bytes_fail_real_validation(self):
        with tempfile.TemporaryDirectory(prefix="rove-producer-member-fault-") as tmp:
            root = Path(tmp)
            producer, receipt, raw = self.prepared(root)
            changed = self.rewritten(raw, member_transform=lambda name, body: body + b"changed" if name == "bank/broad.pgn" else body)
            with self.assertRaisesRegex(ValueError, "member differs"):
                producer.inspect_archive(changed)
            path = root / "changed.zip"
            path.write_bytes(changed)
            with self.assertRaisesRegex(ValueError, "seed member changed"):
                cloud.materialize_seed_archive(path, root / "rejected", expected_manifest_sha256=receipt["seed_manifest"]["sha256"])
            self.assertFalse((root / "rejected").exists())
            manifest = cloud.materialize_seed_archive(Path(receipt["archive"]["path"]), root / "restored",
                expected_manifest_sha256=receipt["seed_manifest"]["sha256"])
            (root / "restored/bank/broad.pgn").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "materialized seed changed"):
                cloud.revalidate_seed(manifest, root / "restored")
            (root / "restored/bank/broad.pgn").write_bytes(b'[Result "*"]\n\n1. e4 e5 *\n')
            cloud.revalidate_seed(manifest, root / "restored")
            (root / "restored/seed.json").write_bytes(cloud.ledger.canonical(manifest))
            with self.assertRaisesRegex(ValueError, "seed manifest changed"):
                cloud.revalidate_seed(manifest, root / "restored")


class PeerPreparationAdapterTests(unittest.TestCase):
    @unittest.skipUnless(cloud.sys.platform == "linux", "Linux reference and qualification boundary")
    def test_real_peer_producer_and_runtime_accept_owned_peer_build_path_without_engine_execution(self):
        """Only fixture source pins and bounded compilation are simulated.

        Actual source inverse/build validation, reference generation, ELF
        validation and qualify_peer's pre-execution revalidation all run. A
        topology sentinel stops before placement, artifact or engine creation;
        no successful runtime/league qualification is manufactured.
        """
        try:
            from .test_peer_runtime import elf_fixture
        except ImportError:
            from test_peer_runtime import elf_fixture
        class EngineExecutionBlocked(RuntimeError):
            pass
        names = ("rove_cloud_peers", "rove_cloud_peer_runtime")
        saved = {name: cloud.sys.modules.pop(name, None) for name in names}
        try:
            with tempfile.TemporaryDirectory(prefix="rove-cloud-peer-port-") as tmp:
                root = Path(tmp)
                source = root / "source"
                # These exact files are the real peer runtime's frozen helper
                # closure. No source tree or generated directory is globbed.
                source_files = (
                    "engines/experiments/strength/peer_runtime.py",
                    "engines/experiments/strength/peers.py",
                    "engines/experiments/strength/registry.py",
                    "engines/experiments/strength/placement.py",
                    "engines/experiments/strength/topology.py",
                    "engines/scripts/production.py",
                    "engines/compact/tiny-entry-d/verify.py",
                    "engines/experiments/tcec-scope/verify.py",
                    "engines/tests/chess_oracle.py",
                )
                for relative in source_files:
                    destination = source / relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes((cloud.ROOT / relative).read_bytes())
                peers = cloud.load_module(names[0], source / "engines/experiments/strength/peers.py")
                runtime = cloud.load_module(names[1], source / "engines/experiments/strength/peer_runtime.py")
                original = {
                    "launcher.sh": b"#!/bin/sh\n# synthetic upstream source fixture only\n",
                    "minifier/preprocess.rs": b'"THREADS" if tcec => "256"\n"DEFAULT_TT_BITS" if tcec => "35"\n',
                }
                upstream = root / "external/ice4"
                for relative, data in original.items():
                    path = upstream / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
                payload = (b"#include<bits/stdc++.h>\nusing namespace std;struct E{long long x;};\n"
                           b"E*table=(E*)calloc(1ull<<24,8);\n"
                           b"int main(){thread c[4];for(thread&f:c)f=thread([]{});for(auto&f:c)f.join();}\n")
                commands = []
                def bounded_compile(argv, cwd, **kwargs):
                    argv = list(map(str, argv))
                    commands.append((argv, Path(cwd), dict(kwargs)))
                    if argv in (["cargo", "--version"], ["c++", "--version"]):
                        stdout = b"synthetic bounded compiler port; no program invoked\n"
                    elif len(argv) == 2 and argv[-1] == "tcec" and argv[0].endswith("/release/minifier"):
                        stdout = payload
                    elif argv[:2] == ["cargo", "build"]:
                        stdout = b""
                    elif argv[0] == "c++" and "input_bytes" in kwargs:
                        self.assertIn(kwargs["input_bytes"], (payload, payload + b"\nstatic_assert(sizeof(*table) == 8);\n"))
                        target = Path(next(token[2:] for token in argv if token.startswith("-o")))
                        target.write_bytes(elf_fixture(symbol_name=b"table"))
                        stdout = b""
                    else:
                        self.fail("unexpected bounded command, never execute: " + repr(argv))
                    return stdout, b"", {"exit_code": 0, "leader_reaped": True, "group_absent": True,
                        "forced_cleanup": False, "stdout_sha256": peers.sha(stdout)}
                class StopTopology:
                    @staticmethod
                    def snapshot():
                        raise EngineExecutionBlocked("stop before actual placement and engine execution")
                class TopologyPort:
                    Topology = StopTopology
                sibling = runtime.sibling
                def sibling_port(name, *args, **kwargs):
                    if name == "peers":
                        return peers
                    if name == "topology":
                        return TopologyPort
                    return sibling(name, *args, **kwargs)
                fixture_pins = {name: peers.git_blob(data) for name, data in original.items()}
                slot = cloud.topology.Slot("fixture-slot", (0, 1, 2, 3), ((0, 0), (0, 1), (0, 2), (0, 3)), (0,), 4, False)
                output = root / "prepared-peer"
                with patch.dict(peers.SOURCE_BLOBS, {"ice4": fixture_pins}), \
                     patch.object(peers, "bounded_run", side_effect=bounded_compile), \
                     patch.object(runtime, "sibling", side_effect=sibling_port), \
                     patch.object(cloud.registry, "admit_to_test_league", side_effect=AssertionError("fixture must never claim admission")):
                    with self.assertRaisesRegex(EngineExecutionBlocked, "before actual placement"):
                        cloud.prepare_peer({"family": "ice4", "profile": "test-p4", "source": "external/ice4"},
                            seed={"source_tree": "source"}, root=root, out=output, slot=slot)
                    manifest = output / "peer-build/peer.json"
                    admitted = runtime.validate_build(manifest)
                    self.assertEqual(admitted["source"], payload)
                    reference = json.loads((output / "reference/reference.json").read_bytes())
                    self.assertTrue(reference["complete"])
                    self.assertEqual(reference["engines_executed"], 0)
                    self.assertEqual(Path(reference["build"]["path"]), manifest)
                    self.assertEqual(len(reference["native_attempts"]), 3)
                    self.assertFalse((output / "runtime").exists())
                    self.assertFalse((output / "build").exists())
                    self.assertEqual(len(commands), 10)
                    self.assertEqual(sum("input_bytes" in kw for _, _, kw in commands), 3)
                    # The safety restriction remains strict: reverting the
                    # adapter to a literal build component must still reject.
                    with self.assertRaisesRegex(ValueError, "non-source or secret-like"):
                        runtime.ordinary(output / "build/peer.json")
        finally:
            for name, prior in saved.items():
                cloud.sys.modules.pop(name, None)
                if prior is not None:
                    cloud.sys.modules[name] = prior


class AuthorityTests(unittest.TestCase):
    def test_native_reference_and_consumer_cannot_be_constructed_from_passed_json(self):
        with self.assertRaisesRegex(ValueError, "live ownership"):
            cloud.CloudConsumer(object(), {"verified": True}, ())
        with self.assertRaisesRegex(ValueError, "sealed source"):
            cloud.CloudRuntimeReference(object(), None, None, None, {}, ())
        with self.assertRaisesRegex(ValueError, "restored and verified"):
            cloud.OriginalLayout(object(), {}, {})

    def test_canonical_provider_is_the_same_class_module(self):
        self.assertIs(cloud.canonical_provider().CloudRuntimeReference, cloud.CloudRuntimeReference)
        self.assertIs(cloud.sys.modules[cloud.CANONICAL_MODULE], cloud)

    def test_first_absolute_provider_import_works_without_strength_on_pythonpath(self):
        script = ("import importlib.util,sys; p=sys.argv[1]; "
                  "s=importlib.util.spec_from_file_location('rove4k_cloud_runtime',p); "
                  "m=importlib.util.module_from_spec(s); sys.modules[s.name]=m; s.loader.exec_module(m); "
                  "assert m.canonical_provider() is m and sys.dont_write_bytecode; print('canonical-ok')")
        with tempfile.TemporaryDirectory(prefix="rove-cloud-absolute-import-") as tmp:
            result = subprocess.run([cloud.sys.executable, "-I", "-B", "-c", script, str(Path(cloud.__file__).resolve())],
                                    cwd=tmp, capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(result.stdout.strip(), b"canonical-ok")

    def test_missing_r_hook_stops_before_any_compiler_or_runtime(self):
        verify = type("Missing", (), {})()
        with self.assertRaisesRegex(ValueError, "missing production R cloud bridge"):
            cloud.require_rove_bridge(verify)
        rejecting = type("Unregistered", (), {name: staticmethod(lambda *a, **k: False) for name in
            ("cloud_source_binding", "cloud_compiler_binding", "cloud_rules_receipt", "cloud_runtime_supported")})()
        with self.assertRaisesRegex(ValueError, "canonical CloudRuntimeReference"):
            cloud.require_rove_bridge(rejecting)

    def test_nested_mutation_of_admission_is_not_equal_authority(self):
        @dataclass(frozen=True)
        class Admission:
            expected: dict
        admitted = Admission({"native_sha256": "a" * 64})
        original = cloud.admission_snapshot(admitted)
        admitted.expected["native_sha256"] = "b" * 64
        self.assertNotEqual(cloud.admission_snapshot(admitted), original)

    def test_archive_requires_real_remote_ack_not_upload_return(self):
        with tempfile.TemporaryDirectory(prefix="rove-cloud-archive-") as tmp:
            path = Path(tmp) / "proof.json"
            path.write_bytes(b"proof")
            publisher = Mock()
            publisher.publish.return_value = {"verified": False, "sha256": cloud.pin(b"proof")["sha256"]}
            with self.assertRaisesRegex(ValueError, "remote acknowledgement"):
                cloud.archive_files(publisher, "campaign", {"proof.json": path})
            expected_key = "campaign/archive/" + cloud.pin(b"proof")["sha256"] + "/proof.json"
            publisher.publish.return_value = {"verified": True, "sha256": cloud.pin(b"proof")["sha256"], "object_key": expected_key}
            result = cloud.archive_files(publisher, "campaign", {"proof.json": path})
            self.assertEqual(result[0]["remote"]["object_key"], expected_key)

    def test_cli_inspect_never_runs_imports_or_transport(self):
        seed, _ = seed_fixture()
        with tempfile.TemporaryDirectory(prefix="rove-cloud-inspect-") as tmp:
            path = Path(tmp) / "seed.json"
            raw = cloud.ledger.canonical(seed) + b"\n"
            path.write_bytes(raw)
            with patch.object(cloud, "load_module", side_effect=AssertionError("no source imports")), \
                 patch.object(cloud, "observe_consumer", side_effect=AssertionError("no AWS")):
                self.assertEqual(cloud.main(["inspect", "--manifest", str(path), "--manifest-sha256", cloud.pin(raw)["sha256"]]), 0)


class DeploymentBindingTests(unittest.TestCase):
    def fixture(self):
        try:
            from . import aws_infrastructure as infrastructure, campaign
            from .test_campaign import plan
            from .test_aws import FakeAWS
        except ImportError:
            import aws_infrastructure as infrastructure
            import campaign
            from test_campaign import plan
            from test_aws import FakeAWS
        selected = replace(plan(), ami_id=cloud.CANONICAL_AMI)
        seed, _ = seed_fixture()
        for name in cloud.HOST_SOURCE_FILES:
            seed["members"][seed["source_tree"] + "/" + name] = {
                **cloud.pin((cloud.ROOT / name).read_bytes().replace(b"\r\n", b"\n")), "mode": 0o600}
        descriptor = {"bucket": selected.artifact_bucket, "key": selected.campaign_id + "/seed.zip",
                      "version_id": "v1", "sha256": "a" * 64, "bytes": 100}
        recipe = campaign.bootstrap_recipe()
        bootstrap = {"recipe_id": recipe["id"], "recipe_sha256": recipe["sha256"]}
        reviewed = {"template_sha256": cloud.ledger.digest(infrastructure.template(selected.region)),
            "watchdog_source_sha256": cloud.pin(infrastructure.WATCHDOG_SOURCE.encode())["sha256"],
            "function_code_sha256": "actual-deployed-zip-checksum", "function_revision_id": "immutable-revision"}
        permit = {"bootstrap": bootstrap, "reviewed_deployment": reviewed,
                  "deployment_receipt_sha256": cloud.ledger.digest({"deployment": reviewed, "bootstrap": bootstrap})}

        class Ports(FakeAWS):
            def __init__(self):
                super().__init__(selected)
                self.template = infrastructure.template(selected.region)
                self.code = reviewed["function_code_sha256"]
                self.arch = "x86_64"

            def call(self, service, operation, request):
                if (service, operation) == ("cloudformation", "get-template"):
                    self.calls.append((service, operation, request))
                    return {"TemplateBody": json.dumps(self.template)}
                if (service, operation) == ("lambda", "get-function-configuration"):
                    self.calls.append((service, operation, request))
                    return {"FunctionArn": selected.watchdog_arn, "State": "Active", "LastUpdateStatus": "Successful",
                            "CodeSha256": self.code, "RevisionId": reviewed["function_revision_id"]}
                if (service, operation) == ("ec2", "describe-images"):
                    self.calls.append((service, operation, request))
                    return {"Images": [{"ImageId": selected.ami_id, "OwnerId": cloud.CANONICAL_OWNER,
                        "Name": "ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-20260907",
                        "State": "available", "Architecture": self.arch, "RootDeviceType": "ebs"}]}
                return super().call(service, operation, request)
        return selected, seed, descriptor, permit, Ports()

    def validate(self, values):
        selected, seed, descriptor, permit, ports = values
        # The R bridge is a separate, explicitly fake service in this focused
        # deployed-template test. It grants no reference/runtime permission.
        with patch.object(cloud, "require_rove_bridge"):
            return cloud.validate_controller_inputs(plan=selected, seed=descriptor, manifest=seed,
                manifest_sha256="b" * 64, permit=permit, client=ports, now=1000)

    def test_actual_template_function_and_image_api_fields_are_all_consumed(self):
        values = self.fixture()
        result = self.validate(values)
        self.assertTrue(result["verified"])
        operations = [(s, o) for s, o, _ in values[-1].calls]
        self.assertIn(("cloudformation", "get-template"), operations)
        self.assertIn(("lambda", "get-function-configuration"), operations)
        self.assertIn(("ec2", "describe-images"), operations)
        self.assertNotIn(("ec2", "run-instances"), operations)

    def test_changed_lambda_code_is_not_accepted_from_unchanged_stack(self):
        values = self.fixture()
        values[-1].code = "changed-code"
        with self.assertRaisesRegex(ValueError, "watchdog code/revision"):
            self.validate(values)

    def test_changed_template_and_wrong_ami_are_rejected(self):
        values = self.fixture()
        values[-1].template["Description"] = "different reviewed source"
        with self.assertRaisesRegex(ValueError, "CloudFormation template"):
            self.validate(values)
        values = self.fixture()
        values[-1].arch = "arm64"
        with self.assertRaisesRegex(ValueError, "live image"):
            self.validate(values)

    def test_modified_bootstrap_recipe_never_becomes_pass(self):
        values = self.fixture()
        values[3]["bootstrap"]["recipe_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "receipt differs"):
            self.validate(values)

    def test_changed_host_controller_source_never_reaches_aws_ports(self):
        for source in (cloud.HOST_SOURCE_FILES[0], "engines/scripts/source_composition.py", "engines/common/board.c",
                       "engines/experiments/tcec-next/profile_dependencies.py",
                       "engines/experiments/tiny-d-submission/source_inputs.py"):
            with self.subTest(source=source):
                values = self.fixture()
                seed = values[1]
                seed["members"][seed["source_tree"] + "/" + source]["sha256"] = "f" * 64
                with self.assertRaisesRegex(ValueError, "differs from reviewed controller"):
                    self.validate(values)
                self.assertEqual(values[-1].calls, [])

    def test_host_does_not_promote_incomplete_or_commandless_bootstrap_receipt(self):
        try:
            from . import campaign
        except ImportError:
            import campaign
        recipe = campaign.bootstrap_recipe()
        approval = {"bootstrap": {"recipe_id": recipe["id"], "recipe_sha256": recipe["sha256"]}}
        for complete in (False, True):
            with self.subTest(complete=complete), tempfile.TemporaryDirectory(prefix="rove-cloud-bootstrap-proof-") as tmp:
                root = Path(tmp)
                receipt = {"format": "rove4k-bootstrap-receipt-v1", "recipe_id": recipe["id"],
                    "recipe_sha256": recipe["sha256"], "complete": complete, "started_at": 10,
                    "finished_at": 11, "deadline_epoch": 610, "commands": []}
                cloud.json_new(root / "bootstrap/receipt.json", receipt)
                with self.assertRaisesRegex(ValueError, "receipt differs|no actual command evidence"):
                    cloud.verify_host_tools(approval, root)


class RetentionTests(unittest.TestCase):
    def test_bank_transport_preserves_original_and_only_rebinds_explicit_pgn_paths(self):
        seed, files = seed_fixture()
        original = {"files": {stage: {"path": "/original/" + stage + ".pgn", **cloud.pin(files[logical])}
                              for stage, logical in seed["bank_pgns"].items()}, "bank_id": "stable-id", "moves": ["e2e4"]}
        files[seed["bank"]] = cloud.ledger.canonical(original)
        seed["members"][seed["bank"]] = {**cloud.pin(files[seed["bank"]]), "mode": 0o600}
        raw, sha = archive_bytes(seed, files)
        with tempfile.TemporaryDirectory(prefix="rove-cloud-bank-") as tmp:
            root = Path(tmp)
            (root / "input.zip").write_bytes(raw)
            cloud.materialize_seed_archive(root / "input.zip", root / "seed", expected_manifest_sha256=sha)
            path = cloud.rebase_bank(seed, root / "seed", root / "consumer-bank.json")
            derived = json.loads(path.read_bytes())
            self.assertEqual((root / "seed" / seed["bank"]).read_bytes(), files[seed["bank"]])
            self.assertEqual(derived["bank_id"], original["bank_id"])
            self.assertEqual(derived["moves"], original["moves"])
            self.assertFalse(derived["transport"]["moves_changed"])
            self.assertEqual(derived["files"]["broad"]["path"], str(root / "seed/bank/broad.pgn"))

    def terminal_fixture(self, root):
        try:
            from .test_campaign import plan
        except ImportError:
            from test_campaign import plan
        selected = plan()
        original = root / "original.jsonl"
        with cloud.ledger.Journal(original, selected.campaign_id) as journal:
            journal.append("campaign.handoff", {"explicit": True})
            prefix = {"rows": len(journal.rows), "last_sha256": journal.last,
                      "bytes": original.stat().st_size, "sha256": cloud.pin(original.read_bytes())["sha256"]}
            handoff = {"host_job_id": "host-test", "journal": prefix, "seed": {"sha256": "a" * 64}}
            journal.append("campaign.host_terminal", {"complete": False})
            rows = list(journal.rows)
        raw = original.read_bytes()
        descriptor = {"object_key": selected.campaign_id + "/host/host-test/journal.jsonl", **cloud.pin(raw),
                      "rows": len(rows), "last_sha256": rows[-1]["sha256"]}
        terminal = {"format": "rove4k-cloud-terminal-v1", "campaign_id": selected.campaign_id,
                    "host_job_id": "host-test", "handoff_sha256": cloud.ledger.digest(handoff),
                    "seed_sha256": "a" * 64, "complete": False, "archives": [], "journal": descriptor}
        objects = {selected.campaign_id + "/host/host-test/terminal.json": cloud.ledger.canonical(terminal),
                   descriptor["object_key"]: raw}

        class ReadPort:
            def __init__(self):
                self.root = root

            def read_verified(self, key, *, expected_sha=None, max_bytes=0):
                data = objects[key]
                if expected_sha is not None and cloud.pin(data)["sha256"] != expected_sha:
                    raise ValueError("fake service checksum mismatch")
                if len(data) > max_bytes:
                    raise ValueError("fake service bound exceeded")
                return data
        return selected, handoff, terminal, objects, ReadPort(), rows

    def test_collector_validates_original_branch_and_preserves_incomplete_terminal(self):
        with tempfile.TemporaryDirectory(prefix="rove-cloud-collect-") as tmp:
            selected, handoff, terminal, objects, port, rows = self.terminal_fixture(Path(tmp))
            collected = cloud.collect_host_result(plan=selected, handoff=handoff, publisher=port)
            self.assertFalse(collected["terminal"]["complete"])
            self.assertEqual(collected["rows"], rows)

    def test_collector_rejects_other_handoff_even_if_terminal_is_remote_verified(self):
        with tempfile.TemporaryDirectory(prefix="rove-cloud-collect-fault-") as tmp:
            selected, handoff, terminal, objects, port, rows = self.terminal_fixture(Path(tmp))
            handoff["journal"]["last_sha256"] = "f" * 64
            with self.assertRaisesRegex(ValueError, "exact handoff"):
                cloud.collect_host_result(plan=selected, handoff=handoff, publisher=port)

    def test_collector_rejects_rehashed_terminal_with_wrong_original_prefix(self):
        with tempfile.TemporaryDirectory(prefix="rove-cloud-prefix-fault-") as tmp:
            selected, handoff, terminal, objects, port, rows = self.terminal_fixture(Path(tmp))
            handoff["journal"]["last_sha256"] = "f" * 64
            terminal["handoff_sha256"] = cloud.ledger.digest(handoff)
            objects[selected.campaign_id + "/host/host-test/terminal.json"] = cloud.ledger.canonical(terminal)
            with self.assertRaisesRegex(ValueError, "original handoff branch"):
                cloud.collect_host_result(plan=selected, handoff=handoff, publisher=port)


class OriginalLayoutTests(unittest.TestCase):
    def fixture(self, root, *, wrong_sealed_root=False):
        seed, files = seed_fixture()
        base, destination = root / "allowed-ci-temp", root / "allowed-ci-temp/source24-run123"
        original_build = destination / "A"
        seal = {"format": "rove4k.source-bundle-seal.v1", "ci_context": seed["source_origin"],
                "producer": {"ID": "ubuntu", "VERSION_ID": "24.04"},
                "bundle": cloud.pin(files["rove/source-bundle.zip"]), "profiles": [{
                    "family": "A", "profile": "test-p4",
                    "build_root": str(original_build) + ("-wrong" if wrong_sealed_root else "")} ]}
        files["rove/source-seal.json"] = cloud.ledger.canonical(seal) + b"\n"
        seed["members"]["rove/source-seal.json"] = {**cloud.pin(files["rove/source-seal.json"]), "mode": 0o600}
        seed["original_layout"]["roots"] = [{"original_root": str(destination), "seed_prefix": "rove",
            "files": {name[len("rove/"):]: cloud.pin(data) for name, data in files.items() if name.startswith("rove/")}}]
        raw, sha = archive_bytes(seed, files)
        archive = root / "transport.zip"
        archive.write_bytes(raw)
        cloud.materialize_seed_archive(archive, root / "seed", expected_manifest_sha256=sha)
        return seed, files, base, destination

    def test_exact_original_copy_preserves_metadata_and_explicit_correspondence(self):
        with tempfile.TemporaryDirectory(prefix="rove-original-layout-") as tmp:
            root = Path(tmp)
            seed, files, base, destination = self.fixture(root)
            with patch.object(cloud, "ORIGINAL_LAYOUT_BASE", PurePosixPath(base)):
                restored = cloud.restore_original_layout(seed, root / "seed")
                self.assertIs(restored.revalidate(), restored)
            build = restored.execution_path("rove/A")
            self.assertEqual(build, destination / "A")
            self.assertEqual(restored.assert_member(build / "build.json"), "rove/A/build.json")
            self.assertEqual(restored.member_bytes(build / "build.json"), files["rove/A/build.json"])
            self.assertEqual((root / "seed/rove/A/build.json").read_bytes(), (build / "build.json").read_bytes())
            self.assertEqual(restored.assert_member(root / "seed/rove/rules.json"), "rove/rules.json")
            self.assertEqual(restored.execution_path("bank/high.pgn"), root / "seed/bank/high.pgn")
            record = restored.to_record()
            self.assertEqual(record["format"], "rove4k-original-layout-v1")
            self.assertEqual(record["seed_manifest"], cloud.pin((root / "seed/seed.json").read_bytes()))
            self.assertGreater(record["roots"][0]["inode"], 0)

    def test_existing_destination_is_preserved_and_never_merged(self):
        with tempfile.TemporaryDirectory(prefix="rove-original-conflict-") as tmp:
            root = Path(tmp)
            seed, files, base, destination = self.fixture(root)
            destination.mkdir(parents=True)
            sentinel = destination / "unrelated.txt"
            sentinel.write_bytes(b"preserve")
            with patch.object(cloud, "ORIGINAL_LAYOUT_BASE", PurePosixPath(base)), \
                 self.assertRaisesRegex(ValueError, "already exists"):
                cloud.restore_original_layout(seed, root / "seed")
            self.assertEqual(sentinel.read_bytes(), b"preserve")
            self.assertFalse((destination / "A").exists())

    def test_wrong_sealed_execution_root_fails_before_creating_any_destination(self):
        with tempfile.TemporaryDirectory(prefix="rove-original-seal-root-") as tmp:
            root = Path(tmp)
            seed, files, base, destination = self.fixture(root, wrong_sealed_root=True)
            with patch.object(cloud, "ORIGINAL_LAYOUT_BASE", PurePosixPath(base)), \
                 self.assertRaisesRegex(ValueError, "exact sealed original build root"):
                cloud.restore_original_layout(seed, root / "seed")
            self.assertFalse(destination.exists())

    def test_root_escape_and_overlap_are_rejected_without_filesystem_writes(self):
        with tempfile.TemporaryDirectory(prefix="rove-original-plan-") as tmp:
            root = Path(tmp)
            seed, files, base, destination = self.fixture(root)
            row = seed["original_layout"]["roots"][0]
            with patch.object(cloud, "ORIGINAL_LAYOUT_BASE", PurePosixPath(base)):
                row["original_root"] = "/etc/rove-outside"
                with self.assertRaisesRegex(ValueError, "escaped"):
                    cloud.original_layout_plan(seed)
                row["original_root"] = str(destination)
                seed["original_layout"]["roots"].append({"original_root": str(destination / "nested"),
                    "seed_prefix": "bank", "files": {name[len("bank/"):]: cloud.pin(data)
                        for name, data in files.items() if name.startswith("bank/")}})
                with self.assertRaisesRegex(ValueError, "overlap"):
                    cloud.original_layout_plan(seed)
            self.assertFalse(destination.exists())

    def test_tampered_restore_or_unknown_tree_member_invalidates_token(self):
        for fault in ("changed", "extra"):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory(prefix="rove-original-mutation-") as tmp:
                root = Path(tmp)
                seed, files, base, destination = self.fixture(root)
                with patch.object(cloud, "ORIGINAL_LAYOUT_BASE", PurePosixPath(base)):
                    restored = cloud.restore_original_layout(seed, root / "seed")
                path = destination / ("A/build.json" if fault == "changed" else "unexpected.txt")
                path.write_bytes(b"changed")
                with self.assertRaisesRegex(ValueError, "changed|unknown file"):
                    restored.revalidate()

    def test_restore_requires_all_declared_prefix_members_and_matching_pins(self):
        seed, _ = seed_fixture()
        row = seed["original_layout"]["roots"][0]
        del row["files"]["A/build.json"]
        with self.assertRaisesRegex(ValueError, "complete explicitly selected seed prefix"):
            cloud.original_layout_plan(seed)
        seed, _ = seed_fixture()
        seed["original_layout"]["roots"][0]["files"]["A/build.json"]["sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "pin differs"):
            cloud.original_layout_plan(seed)


class HostConsumerTests(unittest.TestCase):
    def host_path(self, *, fail_broad=False):
        try:
            from .test_campaign import plan
        except ImportError:
            from test_campaign import plan
        selected = plan()
        seed, files = seed_fixture()
        original_bank = {"files": {stage: {"path": "/original/" + stage + ".pgn", **cloud.pin(files[logical])}
                                    for stage, logical in seed["bank_pgns"].items()}}
        files[seed["bank"]] = cloud.ledger.canonical(original_bank)
        seed["members"][seed["bank"]] = {**cloud.pin(files[seed["bank"]]), "mode": 0o600}
        archive, sha = archive_bytes(seed, files)
        with tempfile.TemporaryDirectory(prefix="rove-cloud-host-port-") as tmp:
            root = Path(tmp) / "host"
            root.mkdir()
            (root / "seed.zip").write_bytes(archive)
            cloud.materialize_seed_archive(root / "seed.zip", root / "seed", expected_manifest_sha256=sha)
            source_journal = Path(tmp) / "source.jsonl"
            with cloud.ledger.Journal(source_journal, selected.campaign_id) as journal:
                journal.append("budget.launch_requested", {"launch_token": selected.launch_token,
                    "max_hourly_usd": selected.max_hourly_usd}, time_utc=cloud.aws.iso(1000))
                journal.append("budget.instance_bound", {"launch_token": selected.launch_token,
                    "instance_id": "i-1234567890abcdef0"}, time_utc=cloud.aws.iso(1001))
                branch = {"object_key": selected.campaign_id + "/handoff.jsonl", **cloud.pin(source_journal.read_bytes()),
                          "rows": len(journal.rows), "last_sha256": journal.last}
            handoff = {"format": "rove4k-cloud-handoff-v1", "campaign_id": selected.campaign_id,
                "aws_plan": selected.as_dict(), "root": str(root), "cgroup_root": "/explicit/fake-cgroup",
                "host_job_id": "host-port", "seed_manifest_sha256": sha, "journal": branch,
                "seed": {"bucket": selected.artifact_bucket, "key": selected.campaign_id + "/seed.zip",
                         "version_id": "v1", **cloud.pin(archive)}}
            objects = {branch["object_key"]: source_journal.read_bytes()}

            class Publisher:
                def __init__(self):
                    self.root = root

                def publish(self, path, key):
                    raw = path.read_bytes()
                    objects[key] = raw
                    return {"object_key": key, **cloud.pin(raw), "verified": True}

                def read_verified(self, key, *, expected_sha=None, max_bytes=0):
                    raw = objects[key]
                    if len(raw) > max_bytes or expected_sha is not None and cloud.pin(raw)["sha256"] != expected_sha:
                        raise ValueError("fake service checksum/bound mismatch")
                    return raw

            calls = []

            class Consumer:
                def to_record(self):
                    return {"topology": {"allowed_cpus": [0]}}

            def registry_builder(seed, source, out, consumer, profile, **kw):
                calls.append("qualify:" + profile)
                out.mkdir()
                cloud.json_new(out / "registry.json", {"format": "fake-service-output", "profile": profile})
                return out / "registry.json"

            def runner_builder(seed, source, out, **kw):
                out.mkdir()
                cloud.write_new(out / "runner", b"fake-port-not-executable")
                cloud.json_new(out / "runner.json", {"fake": True})
                return out / "runner", out / "runner.json"

            def freeze(campaign, profile, registry_path, bank, bank_sha, runner, runner_receipt, out, **kw):
                calls.append("freeze:" + kw["stage"])
                if kw["stage"] == "high":
                    self.assertEqual(kw["broad_plan"].name, "plan.json")
                    self.assertEqual(kw["broad_journal"], root / "host.jsonl")
                out.mkdir()
                cloud.json_new(out / "plan.json", {"stage": kw["stage"]})

            class StagePort:
                def __init__(self, plan_path, out, journal, publisher, state, **kw):
                    self.stage = json.loads(plan_path.read_bytes())["stage"]
                    self.out, self.journal = out, journal

                def execute(self, cgroup):
                    calls.append("execute:" + self.stage)
                    self.out.mkdir()
                    complete = not (fail_broad and self.stage == "broad")
                    report = {"complete": complete, "summary": {"standings": []}}
                    cloud.json_new(self.out / "actual-port-report.json", report)
                    self.journal.append("fake.evaluator_port_returned", {"stage": self.stage, "complete": complete})
                    return report

            port = Publisher()
            with patch.object(cloud, "verify_host_tools", return_value={}), patch.object(cloud, "delegate_controller", return_value={"fake": True}), \
                 patch.object(cloud, "observe_consumer", return_value=Consumer()), \
                 patch.object(cloud, "restore_original_layout", return_value=Mock(to_record=lambda: {})), \
                 patch.object(cloud.aws, "verify_owned_lease", return_value={"fake": True}), \
                 patch.object(cloud.run, "freeze_plan", side_effect=freeze), \
                 patch.object(cloud.topology.Topology, "from_record", return_value=None):
                terminal = cloud.run_host_session(handoff, {}, object(), port, clock=lambda: 1100,
                    registry_builder=registry_builder, runner_builder=runner_builder, stage_factory=StagePort)
            collected = cloud.collect_host_result(plan=selected, handoff=handoff, publisher=port)
            self.assertEqual(collected["terminal"], terminal)
            self.assertEqual(collected["rows"][-1]["event"], "campaign.host_terminal")
            self.assertGreater(len(terminal["archives"]), 5)
            self.assertFalse(terminal["termination_observed"])
            return terminal, calls

    def test_host_consumer_closes_transport_qualification_freeze_stage_retention_path(self):
        terminal, calls = self.host_path()
        self.assertTrue(terminal["complete"])
        self.assertEqual(calls, ["qualify:test-p4", "freeze:broad", "execute:broad",
                                 "qualify:test-p28", "freeze:high", "execute:high"])

    def test_incomplete_broad_is_retained_and_prevents_high_initialization(self):
        terminal, calls = self.host_path(fail_broad=True)
        self.assertFalse(terminal["complete"])
        self.assertEqual(calls, ["qualify:test-p4", "freeze:broad", "execute:broad"])
        self.assertIn("incomplete pairs", terminal["failure"]["message"])


if __name__ == "__main__":
    unittest.main()
