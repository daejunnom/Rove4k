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
        # Full Fastchess Git input is outside this synthetic transport fixture.
        # Its real verifier is exercised independently and never claimed here.
        with patch.object(seed, "validate_runner"):
            return seed.prepare(self.config, out)


class FakeS3:
    def __init__(self, plan, journal):
        self.region, self.plan, self.journal = plan.region, plan, journal
        self.objects, self.calls = {}, []
        self.puts, self.lose_response, self.version = 0, False, "version-one"

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


if __name__ == "__main__":
    unittest.main()
