"""Synthetic transport fixtures and fake S3; never engine or CI acceptance."""
from dataclasses import replace
import base64
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

try:
    from . import aws, ledger, seed
    from .test_aws import plan as base_plan
except ImportError:
    import aws
    import ledger
    import seed
    from test_aws import plan as base_plan


def git(root, *args):
    row = subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-C", str(root), *args], capture_output=True, timeout=10)
    if row.returncode:
        raise AssertionError(row.stderr.decode())
    return row.stdout


class Fixture:
    def __init__(self, root):
        self.root = root
        self.repo = root / "source-checkout"
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        names = {"engines/experiments/strength/" + name + ".py" for name in seed.HOST_MODULES} | set(seed.CORE_R)
        for name in names:
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# synthetic source transport fixture\n")
        (self.repo / "engines/experiments/strength/seed.py").write_bytes(Path(seed.__file__).read_bytes())
        (self.repo / seed.CORE_R[0]).write_text("INPUT_READER='engines/scripts/production_input.py'\n")
        (self.repo / seed.CORE_R[1]).write_text("INPUT_PATH='engines/scripts/production_input.py'\n")
        patch_path = self.repo / "engines/experiments/strength/patches/fastchess-rove.patch"
        patch_path.parent.mkdir()
        patch_path.write_text("synthetic patch; never a runner build\n")
        git(self.repo, "add", "--", "engines")
        git(self.repo, "-c", "user.name=Transport Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "synthetic fixture")
        commit = git(self.repo, "rev-parse", "HEAD").decode().strip()
        self.inputs = {}

        def add(name, raw):
            path = root / "downloaded" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            self.inputs[name] = {"path": str(path), **seed.pin(raw)}

        origin = {"repository": "fixture/Rove4k", "head_sha": commit, "run_id": "123", "run_attempt": "1"}
        members = {"artifact/build.json": b"{}\n", "artifact/main.c": b"/* synthetic input, never executed */\n"}
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            for name, raw in members.items():
                archive.writestr(name, raw)
        bundle = stream.getvalue()
        original = "/home/runner/work/_temp/export-A"
        seal = {"format": "rove4k.source-bundle-seal.v1", "ci_context": origin,
            "producer": {"ID": "ubuntu", "VERSION_ID": "24.04"}, "bundle_format": "zip", "bundle": seed.pin(bundle),
            "members": {name: seed.pin(raw) for name, raw in members.items()}, "profiles": [{"family": "A",
                "profile": "test-p4", "full": True, "representation": "source-jit", "archive_prefix": "artifact",
                "build_root": original + "/artifact", "input_manifest": seed.pin(members["artifact/build.json"])}],
            "restore_layout": {"runner_temp_root": "/home/runner/work/_temp", "output_root": original,
                               "builds": {"artifact": original + "/artifact"}}}
        add("origin/A/source-bundle.zip", bundle)
        add("origin/A/source-seal.json", ledger.canonical(seal))
        add("metadata/A-artifact.json", ledger.canonical({"id": 11, "workflow_run": {"id": 123, "head_sha": commit}}))
        reader = "engines/scripts/production_input.py"
        add("origin/rules/A/probe/rules.json", ledger.canonical({"family": "A", "complete": True,
            "verifier_inputs": {reader: seed.pin((self.repo / reader).read_bytes())}}))
        add("origin/rules/A/probe/cases.json", b"[]")
        add("origin/rules/A/probe/fixture.c", b"/* synthetic fixture */")
        add("origin/rules/A/commands.json", b"{}")
        add("runner/fastchess.bundle", b"synthetic bundle validated in a separate negative Git test")
        add("runner/patch.diff", patch_path.read_bytes())
        add("runner/LICENSE", b"synthetic license fixture")
        add("bank/bank.json", b"{}")
        add("bank/broad.pgn", b'[Result "*"]\n\n1. e4 e5 *\n')
        add("bank/high.pgn", b'[Result "*"]\n\n1. d4 d5 *\n')
        self.config = {"format": "rove4k-seed-prepare-v1", "source_origin": origin,
            "checkout": {"path": str(self.repo), "commit": commit, "paths": ["engines"]}, "source_tree": "source",
            "inputs": self.inputs, "rove": [{"family": "A", "profile": "test-p4", "build": "origin/A/artifact",
                "source_bundle": "origin/A/source-bundle.zip", "source_seal": "origin/A/source-seal.json",
                "artifact_metadata": "metadata/A-artifact.json", "rules": "origin/rules/A/probe/rules.json"}], "peers": [],
            "runner": {"checkout": "external/fastchess", "revision": seed.FASTCHESS, "transport": "external-git-bundle",
                       "bundle": "runner/fastchess.bundle", "patch": "runner/patch.diff", "license": "runner/LICENSE"},
            "bank": "bank/bank.json", "bank_pgns": {"broad": "bank/broad.pgn", "high": "bank/high.pgn"},
            "original_layout": {"roots": [{"original_root": original, "seed_prefix": "origin/A"},
                {"original_root": "/home/runner/work/_temp/rules-A", "seed_prefix": "origin/rules/A"}]}}

    def rewrite(self, name, value):
        raw = ledger.canonical(value)
        path = Path(self.inputs[name]["path"])
        path.write_bytes(raw)
        self.inputs[name] = {"path": str(path), **seed.pin(raw)}

    def prepare(self, out):
        # The exact advertised Fastchess revision is a fake Git service boundary
        # here. Real local Git source collection and runner patch checks still
        # run; no successful intake of the actual upstream PIN is claimed.
        original = seed.git

        def local_git(checkout, *args, **kw):
            if args[:2] == ("bundle", "verify"):
                return b""
            if args[:2] == ("bundle", "list-heads"):
                return (seed.FASTCHESS + " refs/heads/main\n").encode()
            return original(checkout, *args, **kw)

        with patch.object(seed, "git", side_effect=local_git):
            return seed.prepare(self.config, out)


class FakeS3:
    def __init__(self, plan, journal):
        self.region, self.plan, self.journal = plan.region, plan, journal
        self.objects, self.calls = {}, []
        self.puts, self.lose_response, self.version = 0, False, "version-one"
        self.store_on_put = True

    def account_plan_state(self):
        return {"accountId": self.plan.account_id, "accountPlanType": "PAID", "accountPlanStatus": "ACTIVE"}

    def call(self, service, operation, request):
        self.calls.append((service, operation, copy.deepcopy(request)))
        if service == "sts":
            return {"Account": self.plan.account_id, "Arn": "arn:aws:sts::" + self.plan.account_id + ":assumed-role/rove-controller/test"}
        if (service, operation) == ("s3api", "head-object"):
            key = request["Key"]
            if key not in self.objects:
                raise aws.AwsError("NoSuchKey", "s3api.head-object")
            raw = self.objects[key]
            sha = hashlib.sha256(raw).hexdigest()
            return {"ContentLength": len(raw), "Metadata": {"sha256": sha},
                "ChecksumSHA256": base64.b64encode(bytes.fromhex(sha)).decode(), "VersionId": self.version}
        raise AssertionError((service, operation))

    def put_file(self, bucket, key, path, sha):
        self.puts += 1
        rows = ledger.read_journal(self.journal.path, self.plan.campaign_id)
        assert any(row["event"] == "seed.upload_requested" for row in rows)
        if key in self.objects:
            raise aws.AwsError("PreconditionFailed", "s3api.put-object")
        if self.store_on_put:
            self.objects[key] = path.read_bytes()
        if self.lose_response:
            raise aws.AwsError("ObservationTimeout", "s3api.put-object")
        return {"ChecksumSHA256": base64.b64encode(bytes.fromhex(sha)).decode()}


class SeedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="rove-seed-test-")
        self.root = Path(self.temp.name)
        self.fixture = Fixture(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_exact_zip_origin_and_original_layout_without_source_mutation(self):
        before = Path(self.fixture.inputs["origin/A/source-seal.json"]["path"]).read_bytes()
        receipt = self.fixture.prepare(self.root / "prepared")
        raw = Path(receipt["archive"]["path"]).read_bytes()
        summary = seed.inspect_archive(raw)
        self.assertEqual(summary["manifest_sha256"], receipt["seed_manifest"]["sha256"])
        manifest = json.loads(Path(receipt["seed_manifest"]["path"]).read_bytes())
        self.assertIn("source/engines/scripts/production_input.py", manifest["members"])
        self.assertIn("source/engines/experiments/strength/seed.py", manifest["members"])
        self.assertFalse(any(".git/" in name for name in manifest["members"]))
        root = manifest["original_layout"]["roots"][0]
        self.assertEqual(set(root["files"]), {name[len("origin/A/"):] for name in manifest["members"] if name.startswith("origin/A/")})
        self.assertEqual(before, Path(self.fixture.inputs["origin/A/source-seal.json"]["path"]).read_bytes())
        self.assertFalse(receipt["native_qualified"] or receipt["aws_calls_performed"])
        for name in ("engines/scripts/source_composition.py", "engines/experiments/tiny-d-submission/source_inputs.py",
                     "engines/experiments/tcec-next/profile_dependencies.py", "engines/common/board.c",
                     "engines/common/move.c", "engines/common/protocol.c", "engines/common/search.c"):
            self.assertIn("source/" + name, manifest["members"])

    def test_zip_bytes_are_deterministic_across_staging_directories(self):
        first = self.fixture.prepare(self.root / "first")
        second = self.fixture.prepare(self.root / "second")
        self.assertEqual(Path(first["archive"]["path"]).read_bytes(), Path(second["archive"]["path"]).read_bytes())

    def test_published_descriptor_is_accepted_by_actual_seed_consumer_class(self):
        prepared = self.fixture.prepare(self.root / "prepared")
        archive = Path(prepared["archive"]["path"])
        p = base_plan()
        p = replace(p, region="ap-southeast-2", project_region="ap-southeast-2",
                    watchdog_arn=p.watchdog_arn.replace("us-east-2", "ap-southeast-2"))
        key = p.campaign_id + "/seed/" + prepared["archive"]["sha256"] + ".zip"
        plan_path = self.root / "plan.json"
        plan_path.write_bytes(ledger.canonical(p.as_dict()))
        with ledger.Journal(self.root / "publication.jsonl", p.campaign_id) as journal:
            client = FakeS3(p, journal)
        with patch.object(seed.aws, "AWSCLI", return_value=client):
            code = seed.main(["publish", "--aws-plan", str(plan_path), "--archive", str(archive),
                "--journal", str(journal.path), "--out", str(self.root / "publication.json"),
                "--seed-out", str(self.root / "seed-object.json"), "--key", key])
        self.assertEqual(code, 0)
        descriptor = json.loads((self.root / "seed-object.json").read_bytes())
        consumer = seed.runtime().SeedObject(**descriptor)
        self.assertEqual(consumer.sha256, prepared["archive"]["sha256"])
        self.assertEqual(consumer.version_id, "version-one")

    def test_final_dependency_gate_is_carried_byte_exact_through_zip_and_layout(self):
        gate_content, build, record = DependencyTransportTests.fixture(None)
        bundle_path = Path(self.fixture.inputs["origin/A/source-bundle.zip"]["path"])
        original = seed.archive_members(bundle_path.read_bytes())
        files = {name: raw for name, (raw, _) in original.items()}
        for name, (raw, _) in gate_content.items():
            files["artifact/" + name[len(build) + 1:]] = raw
        files["artifact/build.json"] = ledger.canonical(record)
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            for name, raw in sorted(files.items()):
                archive.writestr(name, raw)
        bundle_path.write_bytes(stream.getvalue())
        self.fixture.inputs["origin/A/source-bundle.zip"] = {"path": str(bundle_path), **seed.pin(stream.getvalue())}
        seal = json.loads(Path(self.fixture.inputs["origin/A/source-seal.json"]["path"]).read_bytes())
        seal["bundle"] = seed.pin(stream.getvalue())
        seal["members"] = {name: seed.pin(raw) for name, raw in files.items()}
        seal["profiles"][0]["input_manifest"] = seed.pin(files["artifact/build.json"])
        self.fixture.rewrite("origin/A/source-seal.json", seal)
        receipt = self.fixture.prepare(self.root / "gate-prepared")
        manifest = json.loads(Path(receipt["seed_manifest"]["path"]).read_bytes())
        layout = manifest["original_layout"]["roots"][0]
        with zipfile.ZipFile(receipt["archive"]["path"]) as archive:
            for name, (raw, _) in gate_content.items():
                self.assertEqual(archive.read(name), raw)
                relative = name[len("origin/A/"):]
                self.assertEqual(layout["files"][relative], seed.pin(raw))
            self.assertEqual(archive.read(build + "/build.json"), ledger.canonical(record))

    def test_old_seal_with_current_checkout_is_rejected_before_staging(self):
        seal = json.loads(Path(self.fixture.inputs["origin/A/source-seal.json"]["path"]).read_bytes())
        seal["ci_context"]["head_sha"] = "a" * 40
        self.fixture.rewrite("origin/A/source-seal.json", seal)
        out = self.root / "failed"
        with self.assertRaisesRegex(ValueError, "exact CI seal"):
            self.fixture.prepare(out)
        self.assertFalse(out.exists())

    def test_dirty_or_unlisted_source_never_enters_seed(self):
        reader = self.fixture.repo / "engines/scripts/production_input.py"
        reader.write_text("changed\n")
        with self.assertRaisesRegex(ValueError, "dirty"):
            self.fixture.prepare(self.root / "dirty")
        git(self.fixture.repo, "checkout", "--", "engines/scripts/production_input.py")
        (self.fixture.repo / "engines/unlisted.py").write_text("not committed\n")
        with self.assertRaisesRegex(ValueError, "unlisted"):
            self.fixture.prepare(self.root / "unlisted")

    def test_protected_directory_is_rejected_without_descending(self):
        (self.fixture.repo / "engines/.env.testing").mkdir()
        with self.assertRaisesRegex(ValueError, "protected"):
            self.fixture.prepare(self.root / "protected")

    def test_missing_rule_closure_and_wrong_original_root_reject(self):
        descriptor = self.fixture.inputs.pop("origin/rules/A/probe/fixture.c")
        with self.assertRaisesRegex(ValueError, "closure is incomplete"):
            self.fixture.prepare(self.root / "missing")
        self.fixture.inputs["origin/rules/A/probe/fixture.c"] = descriptor
        self.fixture.config["original_layout"]["roots"][0]["original_root"] += "-wrong"
        with self.assertRaisesRegex(ValueError, "build_root"):
            self.fixture.prepare(self.root / "wrong")

    def test_artifact_metadata_does_not_invent_server_authenticity(self):
        self.fixture.rewrite("metadata/A-artifact.json", {"id": 11, "workflow_run": {"id": 999, "head_sha": "a" * 40}})
        with self.assertRaisesRegex(ValueError, "artifact metadata"):
            self.fixture.prepare(self.root / "metadata")

    def test_actual_git_bundle_rejects_other_revision(self):
        path = self.root / "runner.bundle"
        git(self.fixture.repo, "bundle", "create", str(path), "HEAD")
        runner = self.fixture.config["runner"]
        self.fixture.inputs[runner["bundle"]] = {"path": str(path), **seed.pin(path.read_bytes())}
        content = {name: (Path(value["path"]).read_bytes(), 0o600) for name, value in self.fixture.inputs.items()}
        content["source/engines/experiments/strength/patches/fastchess-rove.patch"] = (content[runner["patch"]][0], 0o600)
        with self.assertRaisesRegex(ValueError, "exact pinned revision"):
            seed.validate_runner(self.fixture.config, content, "source", self.fixture.repo)

    def test_upload_uncertainty_reconciles_without_second_put(self):
        prepared = self.fixture.prepare(self.root / "prepared")
        archive = Path(prepared["archive"]["path"])
        p = base_plan()
        p = replace(p, region="ap-southeast-2", project_region="ap-southeast-2",
                    watchdog_arn=p.watchdog_arn.replace("us-east-2", "ap-southeast-2"))
        key = p.campaign_id + "/seed/" + prepared["archive"]["sha256"] + ".zip"
        with ledger.Journal(self.root / "upload.jsonl", p.campaign_id) as journal:
            client = FakeS3(p, journal)
            client.lose_response = True
            with self.assertRaises(aws.AwsError):
                seed.publish(client, p, archive, key, journal)
            result = seed.publish(client, p, archive, key, journal)
            self.assertTrue(result["verified"])
            self.assertEqual(result["seed"]["version_id"], "version-one")
            self.assertEqual(client.puts, 1)
            client.version = "null"
            with self.assertRaisesRegex(ValueError, "VersionId"):
                seed.reconcile(client, p, archive, key)
            client.version = "v2"
            client.objects[key] = b"conflicting current bytes"
            with self.assertRaisesRegex(ValueError, "conflicts"):
                seed.reconcile(client, p, archive, key)
            self.assertEqual(client.puts, 1)


class PublisherTests(unittest.TestCase):
    """Only the S3 lifecycle port is faked; no real service is contacted."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="rove-seed-publisher-")
        self.root = Path(self.tmp.name)
        self.archive = self.root / "seed.zip"
        self.archive.write_bytes(b"synthetic sealed archive boundary for publisher tests")
        p = base_plan()
        self.plan = replace(p, region="ap-southeast-2", project_region="ap-southeast-2",
                            watchdog_arn=p.watchdog_arn.replace("us-east-2", "ap-southeast-2"))
        self.key = self.plan.campaign_id + "/seed/" + seed.pin(self.archive.read_bytes())["sha256"] + ".zip"
        self.journal = ledger.Journal(self.root / "upload.jsonl", self.plan.campaign_id)
        self.client = FakeS3(self.plan, self.journal)
        self.boundary = patch.object(seed, "inspect_archive", return_value={"synthetic_boundary": True})
        self.boundary.start()

    def tearDown(self):
        self.boundary.stop()
        self.journal.close()
        self.tmp.cleanup()

    def test_normal_ack_and_confirmed_version_are_idempotent(self):
        result = seed.publish(self.client, self.plan, self.archive, self.key, self.journal)
        self.assertTrue(result["verified"] and result["upload_performed"])
        self.assertEqual(result["seed"]["version_id"], "version-one")
        events = [row["event"] for row in self.journal.rows]
        self.assertEqual(events, ["seed.upload_requested", "seed.upload_confirmed"])
        again = seed.publish(self.client, self.plan, self.archive, self.key, self.journal)
        self.assertTrue(again["verified"])
        self.assertFalse(again["upload_performed"])
        self.assertEqual(self.client.puts, 1)
        self.client.version = "different-version-same-bytes"
        with self.assertRaisesRegex(ValueError, "VersionId changed"):
            seed.publish(self.client, self.plan, self.archive, self.key, self.journal)
        self.assertEqual(self.client.puts, 1)

    def test_unknown_not_observed_never_resends(self):
        self.client.lose_response = True
        self.client.store_on_put = False
        with self.assertRaises(aws.AwsError):
            seed.publish(self.client, self.plan, self.archive, self.key, self.journal)
        result = seed.publish(self.client, self.plan, self.archive, self.key, self.journal)
        self.assertEqual(result["state"], "not_observed")
        self.assertNotIn("seed", result)
        self.assertEqual(self.client.puts, 1)
        self.assertEqual([row["event"] for row in self.journal.rows], ["seed.upload_requested", "seed.upload_uncertain"])

    def test_existing_exact_object_binds_first_observed_version_without_put(self):
        self.client.objects[self.key] = self.archive.read_bytes()
        result = seed.publish(self.client, self.plan, self.archive, self.key, self.journal)
        self.assertEqual(result["seed"]["version_id"], "version-one")
        self.assertEqual(self.client.puts, 0)
        self.assertEqual([row["event"] for row in self.journal.rows], ["seed.upload_confirmed"])
        self.client.version = "another-current-version-same-bytes"
        with self.assertRaisesRegex(ValueError, "VersionId changed"):
            seed.publish(self.client, self.plan, self.archive, self.key, self.journal)
        self.assertEqual(self.client.puts, 0)

    def test_missing_current_after_existing_confirmation_never_creates_replacement(self):
        self.client.objects[self.key] = self.archive.read_bytes()
        seed.publish(self.client, self.plan, self.archive, self.key, self.journal)
        del self.client.objects[self.key]
        result = seed.publish(self.client, self.plan, self.archive, self.key, self.journal)
        self.assertEqual(result["state"], "not_observed")
        self.assertEqual(self.client.puts, 0)
        self.assertEqual([row["event"] for row in self.journal.rows], ["seed.upload_confirmed"])

    def test_recovered_unknown_object_also_binds_confirmed_version(self):
        self.client.lose_response = True
        with self.assertRaises(aws.AwsError):
            seed.publish(self.client, self.plan, self.archive, self.key, self.journal)
        seed.publish(self.client, self.plan, self.archive, self.key, self.journal)
        self.assertEqual(self.journal.rows[-1]["event"], "seed.upload_confirmed")
        self.client.version = "another-current-version"
        with self.assertRaisesRegex(ValueError, "VersionId changed"):
            seed.publish(self.client, self.plan, self.archive, self.key, self.journal)
        self.assertEqual(self.client.puts, 1)

    def test_conflicting_current_object_is_not_overwritten(self):
        self.client.objects[self.key] = b"a different current object"
        with self.assertRaisesRegex(ValueError, "conflicts"):
            seed.publish(self.client, self.plan, self.archive, self.key, self.journal)
        self.assertEqual(self.client.puts, 0)
        self.assertEqual(self.journal.rows, [])

    def test_reconcile_cli_has_nonzero_exit_for_not_observed(self):
        plan_path = self.root / "plan.json"
        plan_path.write_bytes(ledger.canonical(self.plan.as_dict()))
        self.journal.close()
        with patch.object(seed.aws, "AWSCLI", return_value=self.client):
            code = seed.main(["reconcile", "--aws-plan", str(plan_path), "--archive", str(self.archive),
                "--journal", str(self.journal.path), "--out", str(self.root / "reconciled.json"),
                "--seed-out", str(self.root / "seed-object.json"), "--key", self.key])
        self.assertEqual(code, 2)
        self.assertEqual(self.client.puts, 0)
        self.assertFalse((self.root / "seed-object.json").exists())

    def test_verified_cli_writes_exact_descriptor_separately(self):
        plan_path = self.root / "plan.json"
        plan_path.write_bytes(ledger.canonical(self.plan.as_dict()))
        self.journal.close()
        with patch.object(seed.aws, "AWSCLI", return_value=self.client):
            code = seed.main(["publish", "--aws-plan", str(plan_path), "--archive", str(self.archive),
                "--journal", str(self.journal.path), "--out", str(self.root / "publication.json"),
                "--seed-out", str(self.root / "seed-object.json"), "--key", self.key])
        self.assertEqual(code, 0)
        descriptor = json.loads((self.root / "seed-object.json").read_bytes())
        report = json.loads((self.root / "publication.json").read_bytes())
        self.assertEqual(set(descriptor), {"bucket", "key", "version_id", "sha256", "bytes"})
        self.assertEqual(descriptor, report["seed"])
        self.assertEqual(report["seed_descriptor_path"], str(self.root / "seed-object.json"))

    def test_same_destination_is_rejected_before_any_api(self):
        plan_path = self.root / "plan.json"
        plan_path.write_bytes(ledger.canonical(self.plan.as_dict()))
        with patch.object(seed.aws, "AWSCLI", side_effect=AssertionError("API transport created")):
            with self.assertRaisesRegex(ValueError, "destinations must differ"):
                seed.main(["publish", "--aws-plan", str(plan_path), "--archive", str(self.archive),
                    "--journal", str(self.journal.path), "--out", str(self.root / "same.json"),
                    "--seed-out", str(self.root / "same.json"), "--key", self.key])


class DependencyTransportTests(unittest.TestCase):
    def fixture(self):
        build, directory = "origin/A/artifact", "attempt-one"
        before, after, expanded, native = b"#include<limits.h>\nint x;\n", b"int x;\n", b"int x;\n", b"native-image"
        values = {directory + "/dependency-gate/before.c": before, directory + "/dependency-gate/after.c": after,
            directory + "/dependency-gate/before.i": expanded, directory + "/dependency-gate/after.i": expanded,
            directory + "/dependency-gate/x": native, directory + "/native/x": native}
        commands = []
        for number, (label, stdin) in enumerate((("before", before), ("after", after), ("native", before), ("shipping", after)), 1):
            kind = directory + ("-compile" if label == "shipping" else "-dependencies-" + label)
            stem = "tool-" + str(number) + "-" + kind
            stdout = expanded if label in ("before", "after") else b""
            values[stem + ".stdin"], values[stem + ".stdout"], values[stem + ".stderr"] = stdin, stdout, b""
            old = "/home/runner/work/_temp/export-A/artifact/"
            commands.append({"kind": kind, "tool_proof": {"path": "frozen/compiler-proof.json", "bytes": 2, "sha256": seed.pin(b"{}")["sha256"]},
                "stdout": {"path": old + stem + ".stdout", **seed.pin(stdout)},
                "stderr": {"path": old + stem + ".stderr", **seed.pin(b"")}})
        values["frozen/compiler-proof.json"] = b"{}"
        content = {build + "/" + name: (raw, 0o600) for name, raw in values.items()}
        record = {"source_dependencies": {"path": "engines/experiments/tcec-next/profile_dependencies.py", "variant": "unused-includes"},
            "attempts": [{"directory": directory, "native_bytes": len(native), "native_sha256": seed.pin(native)["sha256"],
                "dependency_gate": {"input": seed.pin(before), "output": seed.pin(after), "expanded": seed.pin(expanded), "native": seed.pin(native)}}],
            "commands": commands}
        return content, build, record

    def test_final_dependency_full_bytes_and_streams_are_preserved(self):
        content, build, record = self.fixture()
        original = copy.deepcopy(content)
        seed.dependency_evidence(content, build, record)
        self.assertEqual(content, original)
        stdin = next(name for name in content if name.endswith(".stdin"))
        del content[stdin]
        with self.assertRaisesRegex(ValueError, "missing or changed"):
            seed.dependency_evidence(content, build, record)

    def test_expanded_hash_flag_cannot_replace_full_bytes(self):
        content, build, record = self.fixture()
        path = build + "/attempt-one/dependency-gate/after.i"
        content[path] = (b"changed expanded input", 0o600)
        with self.assertRaisesRegex(ValueError, "missing or changed"):
            seed.dependency_evidence(content, build, record)

    def test_tool_proof_file_is_required_without_rewriting_receipt(self):
        content, build, record = self.fixture()
        original = copy.deepcopy(record)
        seed.dependency_evidence(content, build, record)
        self.assertEqual(record, original)
        del content[build + "/frozen/compiler-proof.json"]
        with self.assertRaisesRegex(ValueError, "missing or changed"):
            seed.dependency_evidence(content, build, record)

    def test_default_and_isolated_entrypoints_have_no_bytecode_side_effect(self):
        with tempfile.TemporaryDirectory(prefix="rove-seed-entry-") as directory:
            root = Path(directory)
            for name in ("seed.py", "aws.py", "budget.py", "ledger.py"):
                (root / name).write_bytes((Path(seed.__file__).parent / name).read_bytes())
            for flags in ([], ["-I"]):
                # Intentionally omit -B here to test the CLI's own early flag;
                # the outer test runner remains isolated with -B.
                row = subprocess.run([sys.executable, *flags, str(root / "seed.py"), "example"],
                                     capture_output=True, timeout=10)
                self.assertEqual(row.returncode, 0, row.stderr.decode())
                self.assertEqual(json.loads(row.stdout)["format"], "rove4k-seed-prepare-v1")
                self.assertFalse((root / "__pycache__").exists())


if __name__ == "__main__":
    unittest.main()
