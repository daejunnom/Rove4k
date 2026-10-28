"""Synthetic transport fixtures and fake S3; never engine or CI acceptance."""
from dataclasses import replace
import ast
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
    from .test_aws import plan as base_plan, advanced_plan as base_advanced_plan
except ImportError:
    import aws
    import ledger
    import seed
    from test_aws import plan as base_plan, advanced_plan as base_advanced_plan


def git(root, *args):
    env = os.environ.copy()
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
    row = subprocess.run(["git", "-c", "core.hooksPath=" + os.devnull, "-C", str(root), *args],
                         capture_output=True, timeout=10, env=env)
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
            path.write_bytes(b"# synthetic source transport fixture\n")
        (self.repo / "engines/experiments/strength/seed.py").write_bytes(Path(seed.__file__).read_bytes())
        (self.repo / seed.CORE_R[0]).write_bytes(b"INPUT_READER='engines/scripts/production_input.py'\n")
        (self.repo / seed.CORE_R[1]).write_bytes(b"INPUT_PATH='engines/scripts/production_input.py'\n")
        patch_path = self.repo / "engines/experiments/strength/patches/fastchess-rove.patch"
        patch_path.parent.mkdir()
        patch_path.write_bytes(b"synthetic patch; never a runner build\n")
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


class AdvancedFakeS3(FakeS3):
    """Fresh project metadata and immutable S3 remain fake service ports."""
    def __init__(self, plan, journal):
        super().__init__(plan, journal)
        configured = plan.account_readiness
        self.caller_account = plan.account_id
        self.account_information = {"AccountId": plan.account_id, "AccountState": "ACTIVE"}
        self.organization = {"Organization": {"Id": configured.organization_id,
            "MasterAccountId": configured.management_account_id,
            "Arn": "arn:aws:organizations::" + configured.management_account_id + ":organization/" + configured.organization_id,
            "FeatureSet": "ALL"}}
        self.metadata_errors = {}
        self.account_plan_reads = 0

    def own_account_information(self):
        return self.call("account", "get-account-information", {})

    def organization_information(self):
        return self.call("organizations", "describe-organization", {})

    def account_plan_state(self):
        self.account_plan_reads += 1
        raise AssertionError("Advanced publishing must not infer or require observed PAID status")

    def call(self, service, operation, request):
        selected = (service, operation)
        if selected in (("sts", "get-caller-identity"), ("account", "get-account-information"),
                        ("organizations", "describe-organization")):
            self.calls.append((service, operation, copy.deepcopy(request)))
            if selected in self.metadata_errors:
                raise self.metadata_errors[selected]
            if service == "sts":
                return {"Account": self.caller_account,
                    "Arn": "arn:aws:sts::" + self.caller_account + ":assumed-role/rove-controller/test"}
            return copy.deepcopy(self.account_information if service == "account" else self.organization)
        return super().call(service, operation, request)


class ExecutionBaseAncestorFixture(Fixture):
    """Real local R->E and R->H graph; API/proof transport stays synthetic."""
    def __init__(self, root):
        super().__init__(root)
        self.reported_base = git(self.repo, "rev-parse", "HEAD").decode().strip()
        self.tree = git(self.repo, "rev-parse", "HEAD^{tree}").decode().strip()
        self.execution_base = self.commit_object(self.tree, [self.reported_base], "execution base advanced from reported snapshot")
        self.head = self.commit_object(self.tree, [self.reported_base], "PR head diverged from reported snapshot")
        self.merge = self.commit_object(self.tree, [self.execution_base, self.head], "execution merge uses advanced base")
        git(self.repo, "checkout", "--detach", "-q", self.merge)
        origin = self.config["source_origin"]
        origin["head_sha"] = self.merge
        self.config["checkout"]["commit"] = self.merge
        seal = json.loads(Path(self.inputs["origin/A/source-seal.json"]["path"]).read_bytes())
        seal["ci_context"] = origin
        self.rewrite("origin/A/source-seal.json", seal)
        repository = {"id": 17, "full_name": origin["repository"]}
        self.pr = {"number": 12, "merge_commit_sha": self.merge,
            "base": {"sha": self.reported_base, "ref": "develop", "repo": repository},
            "head": {"sha": self.head, "ref": "feature/fixture", "repo": repository}}
        self.run = {"id": 123, "run_attempt": 1, "repository": repository, "head_repository": repository,
            "event": "pull_request", "head_sha": self.head, "head_branch": "feature/fixture",
            "status": "completed", "conclusion": "success", "pull_requests": [copy.deepcopy(self.pr)]}
        self.commit = {"sha": self.merge, "tree": {"sha": self.tree},
            "parents": [{"sha": self.execution_base}, {"sha": self.head}]}
        self.proof = {"format": "rove4k-execution-base-ancestor-v1", "base_ref": "refs/heads/develop",
            "reported_base_sha": self.reported_base, "execution_base_sha": self.execution_base,
            "execution_commit_base64": self.encoded_object("commit", self.merge),
            "execution_tree_base64": self.encoded_object("tree", self.tree),
            "ancestry": [self.commit_row(self.execution_base), self.commit_row(self.reported_base)]}
        self.documents = {key: "metadata/" + key + ".json"
            for key in ("run", "pull_request", "commit", "execution_base_proof")}
        self.config["workflow_provenance"] = self.documents
        self.reset_documents()
        self.rewrite("metadata/A-artifact.json", {"id": 11, "workflow_run": {"id": 123,
            "head_sha": self.head, "repository_id": 17, "head_repository_id": 17, "head_branch": "feature/fixture"}})

    def commit_object(self, tree, parents, message):
        arguments = ["-c", "user.name=Transport Fixture", "-c", "user.email=fixture@example.invalid", "commit-tree", tree]
        for parent in parents:
            arguments.extend(("-p", parent))
        return git(self.repo, *arguments, "-m", message).decode().strip()

    def encoded_object(self, kind, sha):
        return base64.b64encode(git(self.repo, "cat-file", kind, sha)).decode("ascii")

    def commit_row(self, sha):
        return {"sha": sha, "raw_base64": self.encoded_object("commit", sha)}

    def set_document(self, role, value=None, *, raw=None):
        raw = ledger.canonical(value) if raw is None else raw
        path = self.root / "ancestry-originals" / (role + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        self.inputs[self.documents[role]] = {"path": str(path), **seed.pin(raw)}

    def reset_documents(self):
        for role, value in (("run", self.run), ("pull_request", self.pr), ("commit", self.commit), ("execution_base_proof", self.proof)):
            self.set_document(role, value)

    def content(self):
        return {name: (Path(value["path"]).read_bytes(), 0o600) for name, value in self.inputs.items()}

    def reader(self, name):
        return Path(self.inputs[name]["path"]).read_bytes()

    def binding(self):
        return seed.workflow_binding(self.config, self.content(), self.config["source_origin"], self.head)


class WorkflowProvenanceTests(unittest.TestCase):
    """Actual local commit DAGs; API JSON remains an explicit transport fixture."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="rove-pr-origin-test-")
        self.root = Path(self.temp.name)
        self.fixture = Fixture(self.root)
        repo = self.fixture.repo
        self.base = git(repo, "rev-parse", "HEAD").decode().strip()
        git(repo, "-c", "user.name=Transport Fixture", "-c", "user.email=fixture@example.invalid",
            "commit", "--allow-empty", "-qm", "head")
        self.head = git(repo, "rev-parse", "HEAD").decode().strip()
        self.tree = git(repo, "rev-parse", "HEAD^{tree}").decode().strip()
        self.merge = git(repo, "-c", "user.name=Transport Fixture", "-c", "user.email=fixture@example.invalid",
            "commit-tree", self.tree, "-p", self.base, "-p", self.head, "-m", "execution merge").decode().strip()
        git(repo, "checkout", "--detach", "-q", self.merge)
        origin = self.fixture.config["source_origin"]
        origin["head_sha"] = self.merge
        self.fixture.config["checkout"]["commit"] = self.merge
        seal = json.loads(Path(self.fixture.inputs["origin/A/source-seal.json"]["path"]).read_bytes())
        seal["ci_context"] = origin
        self.fixture.rewrite("origin/A/source-seal.json", seal)
        repository = {"id": 17, "full_name": origin["repository"]}
        self.pr = {"number": 12, "merge_commit_sha": self.merge,
                   "base": {"sha": self.base, "ref": "develop", "repo": repository},
                   "head": {"sha": self.head, "ref": "feature/fixture", "repo": repository}}
        self.run = {"id": 123, "run_attempt": 1, "repository": repository, "head_repository": repository,
                    "event": "pull_request", "head_sha": self.head, "head_branch": "feature/fixture",
                    "status": "completed", "conclusion": "success", "pull_requests": [copy.deepcopy(self.pr)]}
        self.commit = {"sha": self.merge, "tree": {"sha": self.tree},
                       "parents": [{"sha": self.base}, {"sha": self.head}]}
        for name, value in (("run", self.run), ("pull_request", self.pr), ("commit", self.commit)):
            path = self.root / (name + ".json")
            raw = ledger.canonical(value)
            path.write_bytes(raw)
            self.fixture.inputs["metadata/" + name + ".json"] = {"path": str(path), **seed.pin(raw)}
        self.fixture.config["workflow_provenance"] = {key: "metadata/" + key + ".json"
                                                     for key in ("run", "pull_request", "commit")}
        self.fixture.rewrite("metadata/A-artifact.json", {"id": 11, "workflow_run": {"id": 123,
            "head_sha": self.head, "repository_id": 17, "head_repository_id": 17, "head_branch": "feature/fixture"}})

    def tearDown(self):
        self.temp.cleanup()

    def binding(self, *, run=None, pr=None, commit=None, config=None, head=None):
        content = {name: (Path(value["path"]).read_bytes(), 0o600)
                   for name, value in self.fixture.inputs.items()}
        for key, value in (("run", run), ("pull_request", pr), ("commit", commit)):
            if value is not None:
                content["metadata/" + key + ".json"] = (ledger.canonical(value), 0o600)
        return seed.workflow_binding(config or self.fixture.config, content,
                                     self.fixture.config["source_origin"], head or self.head)

    def test_real_ordered_merge_and_raw_api_head_are_separate_in_actual_seed(self):
        receipt = self.fixture.prepare(self.root / "prepared")
        value = json.loads(Path(receipt["seed_manifest"]["path"]).read_bytes())["workflow_provenance"]
        self.assertEqual(value["api_head_sha"], self.head)
        self.assertEqual(value["checkout_sha"], self.merge)
        self.assertEqual(value["execution_parents"], [self.base, self.head])
        self.assertEqual(value["execution_tree"], self.tree)
        self.assertEqual(value["ref"], "refs/pull/12/merge")
        self.assertEqual(set(value["inputs"]), {"metadata/run.json", "metadata/pull_request.json", "metadata/commit.json"})
        self.assertEqual(set(value["artifact_metadata"]), {"metadata/A-artifact.json"})
        self.assertEqual(receipt["workflow_provenance"], value)
        # The API original was not rebound to the execution merge.
        original = json.loads(Path(self.fixture.inputs["metadata/A-artifact.json"]["path"]).read_bytes())
        self.assertEqual(original["workflow_run"]["head_sha"], self.head)

    def test_legacy_equal_base_binding_retains_its_exact_result_shape(self):
        names = self.fixture.config["workflow_provenance"].values()
        expected = {"kind": "pull-request-merge", "event": "pull_request", "repository": "fixture/Rove4k",
            "repository_id": 17, "run_id": "123", "run_attempt": "1", "api_head_sha": self.head,
            "checkout_sha": self.merge, "execution_tree": self.tree, "execution_parents": [self.base, self.head],
            "inputs": {name: seed.pin(Path(self.fixture.inputs[name]["path"]).read_bytes()) for name in names},
            "pull_request": 12, "ref": "refs/pull/12/merge", "head_branch": "feature/fixture", "head_repository_id": 17}
        self.assertEqual(self.binding(), expected)

    def test_ordinary_head_equality_never_accepts_an_unexplained_different_sha(self):
        config = copy.deepcopy(self.fixture.config)
        config.pop("workflow_provenance")
        with self.assertRaisesRegex(ValueError, "explicit PR provenance"):
            self.binding(config=config)
        equal = self.binding(config=config, head=self.merge)
        self.assertEqual(equal["kind"], "artifact-head-equality")
        config["workflow_provenance"] = {"run": "metadata/run.json", "commit": "metadata/commit.json"}
        run = {**self.run, "event": "push"}
        with self.assertRaisesRegex(ValueError, "ordinary workflow head"):
            self.binding(config=config, run=run)
        self.assertEqual(self.binding(config=config, run={**run, "head_sha": self.merge}, head=self.merge)["kind"],
                         "workflow-head-equality")

    def test_wrong_run_repo_ref_parent_tree_and_snapshot_do_not_become_pr_waivers(self):
        cases = [
            {"run": {**self.run, "run_attempt": 2}},
            {"run": {**self.run, "id": 999}},
            {"run": {**self.run, "repository": {"id": 17, "full_name": "other/repository"}}},
            {"run": {**self.run, "head_branch": "other/ref"}},
            {"run": {**self.run, "conclusion": "failure"}},
            {"run": {**self.run, "pull_requests": [self.pr, self.pr]}},
            {"run": {**self.run, "repository": None}},
            {"run": {**self.run, "pull_requests": [None]}},
            {"run": {**self.run, "head_repository": []}},
            {"pr": {**self.pr, "number": 13}},
            {"pr": {**self.pr, "base": None}},
            {"pr": {**self.pr, "head": {**self.pr["head"], "repo": []}}},
            {"pr": {**self.pr, "merge_commit_sha": self.head}},
            {"pr": {**self.pr, "base": {**self.pr["base"], "sha": self.head}}},
            {"pr": {**self.pr, "head": {**self.pr["head"], "ref": "other/ref"}}},
            {"commit": {**self.commit, "tree": {"sha": "0" * 40}}},
            {"commit": {**self.commit, "tree": []}},
            {"commit": {**self.commit, "parents": list(reversed(self.commit["parents"]))}},
        ]
        for change in cases:
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.binding(**change)

    def test_duplicate_or_reused_provenance_documents_reject(self):
        raw = ledger.canonical(self.run)[:-1] + b',"id":123}'
        name = "metadata/run.json"
        Path(self.fixture.inputs[name]["path"]).write_bytes(raw)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.binding()
        config = copy.deepcopy(self.fixture.config)
        config["workflow_provenance"]["commit"] = name
        with self.assertRaisesRegex(ValueError, "distinct"):
            self.binding(config=config)

    def test_local_replace_ref_cannot_change_the_execution_commit(self):
        git(self.fixture.repo, "replace", self.merge, self.head)
        self.assertEqual(self.binding()["execution_parents"], [self.base, self.head])
        changed = {**self.commit, "parents": [{"sha": self.base}]}
        with self.assertRaisesRegex(ValueError, "actual local Git object"):
            self.binding(commit=changed)

    def test_local_git_never_lazy_fetches_or_enables_transports(self):
        original = subprocess.run
        captured = []
        def invoke(*args, **kwargs):
            captured.append((args[0], kwargs["env"]))
            return original(*args, **kwargs)
        with patch.object(seed.subprocess, "run", side_effect=invoke):
            self.binding()
        self.assertTrue(captured)
        for argv, env in captured:
            self.assertIn("protocol.allow=never", argv)
            self.assertEqual(env["GIT_NO_REPLACE_OBJECTS"], "1")
            self.assertEqual(env["GIT_NO_LAZY_FETCH"], "1")
            self.assertEqual(env["GIT_ALLOW_PROTOCOL"], "")
            self.assertFalse(any(arg in ("fetch", "clone", "pull", "push") for arg in argv))

    def test_inherited_git_repository_index_and_config_cannot_redirect_checkout(self):
        injected = {"GIT_DIR": str(self.root / "unrelated-absent-repository"),
                    "GIT_WORK_TREE": str(self.root / "unrelated-tree"),
                    "GIT_INDEX_FILE": str(self.root / "unrelated-index"),
                    "GIT_OBJECT_DIRECTORY": str(self.root / "unrelated-objects"),
                    "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(self.root / "unrelated-alternates"),
                    "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "protocol.allow", "GIT_CONFIG_VALUE_0": "always",
                    "GIT_CONFIG_PARAMETERS": "'protocol.allow'='always'"}
        original, captured = subprocess.run, []
        def invoke(*args, **kwargs):
            captured.append(kwargs["env"])
            return original(*args, **kwargs)
        with patch.dict(os.environ, injected), patch.object(seed.subprocess, "run", side_effect=invoke):
            result = self.binding()
        self.assertEqual(result["execution_parents"], [self.base, self.head])
        for env in captured:
            self.assertFalse(set(injected) & set(env))


class ExecutionBaseAncestorTests(unittest.TestCase):
    """Actual local Git ancestry, never authenticated CI or engine acceptance."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="rove-execution-base-ancestor-")
        self.root = Path(self.temp.name)
        self.fixture = ExecutionBaseAncestorFixture(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def refused_prepare(self, label, *, proof=None, raw=None, documents=None):
        self.fixture.reset_documents()
        if proof is not None or raw is not None:
            self.fixture.set_document("execution_base_proof", proof, raw=raw)
        for role, value in (documents or {}).items():
            self.fixture.set_document(role, value)
        out = self.root / ("rejected-" + label)
        with self.assertRaises(ValueError):
            self.fixture.prepare(out)
        self.assertFalse(out.exists())

    def test_actual_ancestor_binding_keeps_reported_and_execution_bases_separate(self):
        fixture = self.fixture
        value = fixture.binding()
        self.assertEqual(value["kind"], "execution-base-ancestor-v1")
        self.assertEqual(value["reported_base_sha"], fixture.reported_base)
        self.assertEqual(value["execution_base_sha"], fixture.execution_base)
        self.assertEqual(value["base_ref"], "refs/heads/develop")
        self.assertEqual(value["execution_parents"], [fixture.execution_base, fixture.head])
        self.assertEqual(value["execution_tree"], fixture.tree)
        self.assertEqual(value["documents"], fixture.documents)
        self.assertEqual(set(value["inputs"]), set(fixture.documents.values()))
        self.assertEqual(json.loads(fixture.reader(fixture.documents["pull_request"]))["base"]["sha"], fixture.reported_base)
        self.assertEqual(json.loads(fixture.reader("metadata/A-artifact.json"))["workflow_run"]["head_sha"], fixture.head)

    def test_actual_producer_inspector_roundtrip_retains_original_proof_and_result(self):
        fixture = self.fixture
        receipt = fixture.prepare(self.root / "prepared-ancestor")
        archive = Path(receipt["archive"]["path"]).read_bytes()
        inspected = seed.inspect_archive(archive)
        self.assertEqual(inspected["manifest_sha256"], receipt["seed_manifest"]["sha256"])
        manifest = json.loads(Path(receipt["seed_manifest"]["path"]).read_bytes())
        value = manifest["workflow_provenance"]
        self.assertEqual(value["kind"], "execution-base-ancestor-v1")
        self.assertEqual(value["documents"], fixture.documents)
        self.assertEqual(value["reported_base_sha"], fixture.reported_base)
        self.assertEqual(value["execution_base_sha"], fixture.execution_base)
        self.assertEqual(receipt["workflow_provenance"], value)
        with zipfile.ZipFile(io.BytesIO(archive)) as source:
            self.assertEqual(source.read(fixture.documents["execution_base_proof"]), fixture.reader(fixture.documents["execution_base_proof"]))
        self.assertFalse(receipt["native_qualified"] or receipt["engine_executed"] or receipt["aws_calls_performed"])

    def test_unequal_base_without_explicit_proof_is_not_an_implicit_ancestry_exception(self):
        self.fixture.config["workflow_provenance"] = {key: value for key, value in self.fixture.documents.items()
            if key != "execution_base_proof"}
        self.refused_prepare("missing-proof")

    def test_forged_or_ambiguous_proof_fields_reject_before_output(self):
        original = self.fixture.proof
        cases = {}
        for field, value in (("format", "another-proof"), ("base_ref", "refs/heads/other"),
                             ("reported_base_sha", self.fixture.head), ("execution_base_sha", self.fixture.reported_base)):
            cases[field] = {**copy.deepcopy(original), field: value}
        cases["extra-field"] = {**copy.deepcopy(original), "allowed": True}
        missing = copy.deepcopy(original); del missing["execution_tree_base64"]; cases["missing-field"] = missing
        for field in ("execution_commit_base64", "execution_tree_base64"):
            raw = base64.b64decode(original[field]) + b"\n"
            cases[field] = {**copy.deepcopy(original), field: base64.b64encode(raw).decode("ascii")}
        changed = copy.deepcopy(original)
        changed["ancestry"][0]["raw_base64"] = base64.b64encode(base64.b64decode(changed["ancestry"][0]["raw_base64"]) + b"\n").decode("ascii")
        cases["forged-commit-row"] = changed
        changed = copy.deepcopy(original)
        changed["ancestry"][0]["allowed"] = True
        cases["extra-row-field"] = changed
        cases["invalid-base64"] = {**copy.deepcopy(original), "execution_commit_base64": "invalid!!"}
        cases["single-row"] = {**copy.deepcopy(original), "ancestry": original["ancestry"][:1]}
        cases["reversed-path"] = {**copy.deepcopy(original), "ancestry": list(reversed(original["ancestry"]))}
        cases["duplicate-row"] = {**copy.deepcopy(original), "ancestry": [original["ancestry"][0], original["ancestry"][0], original["ancestry"][1]]}
        cases["too-many-rows"] = {**copy.deepcopy(original), "ancestry": [original["ancestry"][0]] * 1024 + [original["ancestry"][1]]}
        for label, proof in cases.items():
            with self.subTest(label=label):
                self.refused_prepare(label, proof=proof)
        duplicate = ledger.canonical(original)[:-1] + b',"base_ref":"refs/heads/develop"}'
        self.refused_prepare("duplicate-json", raw=duplicate)
        raw = ledger.canonical(original)
        selected = b'"sha":"' + self.fixture.execution_base.encode() + b'"}'
        duplicated = b'"sha":"' + self.fixture.execution_base.encode() + b'","sha":"' + self.fixture.execution_base.encode() + b'"}'
        nested = raw.replace(selected, duplicated, 1)
        self.assertNotEqual(nested, raw)
        self.refused_prepare("duplicate-nested-json", raw=nested)
        self.refused_prepare("oversize-proof", raw=ledger.canonical(original) + b" " * (4 << 20))

    def test_real_diverged_or_unrelated_commit_rows_do_not_establish_parent_edges(self):
        unrelated = self.fixture.commit_object(self.fixture.tree, [], "unrelated root with same tree")
        for label, middle in (("diverged", self.fixture.head), ("unrelated", unrelated)):
            with self.subTest(label=label):
                proof = copy.deepcopy(self.fixture.proof)
                proof["ancestry"] = [self.fixture.commit_row(self.fixture.execution_base),
                    self.fixture.commit_row(middle), self.fixture.commit_row(self.fixture.reported_base)]
                self.refused_prepare(label, proof=proof)

    def test_merge_tree_parents_and_original_refs_stay_bound_to_raw_objects(self):
        for label, changed in (("tree", {**self.fixture.commit, "tree": {"sha": "0" * 40}}),
                               ("parents", {**self.fixture.commit, "parents": list(reversed(self.fixture.commit["parents"]))})):
            with self.subTest(label=label):
                self.refused_prepare(label, documents={"commit": changed})
        pr, run = copy.deepcopy(self.fixture.pr), copy.deepcopy(self.fixture.run)
        pr["base"]["ref"] = "another-base"
        run["pull_requests"] = [copy.deepcopy(pr)]
        self.refused_prepare("raw-base-ref", documents={"pull_request": pr, "run": run})
        self.refused_prepare("different-event", documents={"run": {**self.fixture.run, "event": "push"}})


class SeedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="rove-seed-test-")
        self.root = Path(self.temp.name)
        self.fixture = Fixture(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_new_league_closure_is_explicit_while_legacy_source_is_unchanged(self):
        checkout, origin = self.fixture.config["checkout"], self.fixture.config["source_origin"]
        # The old source fixture deliberately contains no league files.
        legacy = seed.checkout_files(checkout, origin)
        league_names = tuple("engines/experiments/strength/" + name + ".py" for name in
            ("memory_observation", "overhead", "league_probe", "diagnostic_candidates", "peak_capacity", "peak_probe_session", "peak_ready_probe", "peak_receipt",
             "peak_supervisor", "rove_runtime_observation", "rove_worker_observer", "rove_vma_observer", "functional_uci_probe", "functional_probe_session")) + (
            "engines/scripts/league_resource_profiles.py", "engines/experiments/tcec-scope/verify.py",
            "engines/compact/tiny-entry-d/verify.py", "engines/tests/chess_oracle.py")
        self.assertTrue(all(name not in legacy for name in league_names))
        with self.assertRaisesRegex(ValueError, "omitted the host/R production code closure"):
            seed.checkout_files(checkout, origin, league_required=True)
        for name in league_names:
            path = self.fixture.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"# synthetic league transport source, never executed\n")
        git(self.fixture.repo, "add", "--", *league_names)
        git(self.fixture.repo, "-c", "user.name=Transport Fixture", "-c", "user.email=fixture@example.invalid",
            "commit", "-qm", "add league closure fixture")
        head = git(self.fixture.repo, "rev-parse", "HEAD").decode().strip()
        checkout = {**checkout, "commit": head}
        origin = {**origin, "head_sha": head}
        admitted = seed.checkout_files(checkout, origin, league_required=True)
        self.assertTrue(all(name in admitted for name in league_names))
        for missing in league_names:
            prefixes = [name for name in admitted if name != missing]
            with self.subTest(missing=missing), self.assertRaisesRegex(ValueError, "omitted the host/R production code closure"):
                seed.checkout_files({**checkout, "paths": prefixes}, origin, league_required=True)

    def test_only_reviewed_declarations_are_exempt_in_legacy_closure(self):
        owner = seed.LEAGUE_CAMPAIGN_CI
        metadata = Path(seed.__file__).read_bytes()
        own = "engines/experiments/strength/seed.py"
        target = "engines/scripts/league_resource_profiles.py"
        # The inventory, and the exact lazy declaration for legacy profiles,
        # are exempt. An executable reference in that same owner is not.
        self.assertNotIn(owner, seed.named_python_dependencies(metadata, source_name=own))
        self.assertNotIn(target, seed.named_python_dependencies(metadata, source_name=own, league_required=False))
        source_with_reference = metadata + ("module_path = " + repr(target) + "\n").encode()
        self.assertIn(target, seed.named_python_dependencies(source_with_reference, source_name=own, league_required=False))
        self.assertIn(owner, seed.named_python_dependencies(metadata, source_name="engines/experiments/strength/other.py"))
        campaign = Path(seed.__file__).with_name("campaign_ci.py").read_bytes()
        self.assertNotIn(target, seed.named_python_dependencies(campaign, source_name=owner, league_required=False))
        self.assertIn(target, seed.named_python_dependencies(campaign + ("\nopen(" + repr(target) + ")\n").encode(),
                                                             source_name=owner, league_required=False))

        for source_name in ("engines/experiments/strength/registry.py", "engines/experiments/strength/peer_runtime.py"):
            symbol, value = seed.LEAGUE_DEPENDENCY_DECLARATIONS[source_name]
            declaration = (symbol + " = " + repr(value) + "\n").encode()
            with self.subTest(source=source_name):
                self.assertNotIn(target, seed.named_python_dependencies(declaration, source_name=source_name, league_required=False))
                self.assertIn(target, seed.named_python_dependencies(declaration + ("open(" + repr(target) + ")\n").encode(),
                    source_name=source_name, league_required=False))
                self.assertIn(target, seed.named_python_dependencies(declaration, source_name=source_name, league_required=True))

        source_name = "engines/experiments/strength/cloud_runtime.py"
        source = self.fixture.repo / source_name
        declaration = "LEAGUE_HOST_SOURCE_FILES = " + repr(seed.LEAGUE_DEPENDENCY_DECLARATIONS[source_name][1]) + "\n"
        source.write_text(declaration + "open(" + repr(target) + ")\n", encoding="utf-8")
        git(self.fixture.repo, "add", "--", source_name)
        git(self.fixture.repo, "-c", "user.name=Transport Fixture", "-c", "user.email=fixture@example.invalid",
            "commit", "-qm", "actual named dependency fixture")
        head = git(self.fixture.repo, "rev-parse", "HEAD").decode().strip()
        checkout = {**self.fixture.config["checkout"], "commit": head}
        origin = {**self.fixture.config["source_origin"], "head_sha": head}
        with self.assertRaisesRegex(ValueError, "named production Python dependency omitted: .*league_resource_profiles.py"):
            seed.checkout_files(checkout, origin)

    def test_league_experiment_inventories_are_exact_legacy_exceptions(self):
        root = Path(seed.__file__).resolve().parents[3]
        targets = tuple("engines/experiments/tcec-next/" + name for name in
                        ("profile_acef_league_atomic.py", "profile_league_square.py", "league_ep.py",
                         "profile_league_compound.py"))
        for owner, declarations in seed.LEAGUE_EXPERIMENT_DECLARATIONS.items():
            raw = (root / owner).read_bytes()
            text = raw.decode("utf-8")
            tree = ast.parse(text)
            names = {name for name, _ in declarations}
            nodes = [node for node in tree.body if isinstance(node, ast.Assign)
                     and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                     and node.targets[0].id in names]
            self.assertEqual(len(nodes), len(names))
            minimal = ("\n".join(ast.get_source_segment(text, node) for node in nodes) + "\n").encode()
            with self.subTest(owner=owner):
                # Exact metadata is lazy only for legacy; it becomes named
                # source dependencies when the league source is selected.
                legacy = seed.named_python_dependencies(minimal, source_name=owner, league_required=False)
                league = seed.named_python_dependencies(minimal, source_name=owner, league_required=True)
                for target in targets:
                    self.assertNotIn(target, legacy)
                    self.assertIn(target, league)
                    self.assertIn(target, seed.named_python_dependencies(
                        minimal + ("open(" + repr(target) + ")\n").encode(), source_name=owner, league_required=False))
                damaged = minimal.replace(targets[0].encode(), b"engines/experiments/tcec-next/changed.py", 1)
                with self.assertRaisesRegex(ValueError, "league experiment dependency declaration differs"):
                    seed.named_python_dependencies(damaged, source_name=owner, league_required=False)

    def test_experiment_inventory_fails_closed_on_actual_reference_and_league_missing_helper(self):
        owner = "engines/experiments/tcec-next/profile_build.py"
        source_path = Path(seed.__file__).resolve().parents[3] / owner
        text = source_path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        symbols = {name for name, _ in seed.LEAGUE_EXPERIMENT_DECLARATIONS[owner]}
        nodes = [node for node in tree.body if isinstance(node, ast.Assign)
                 and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                 and node.targets[0].id in symbols]
        declarations = "\n".join(ast.get_source_segment(text, node) for node in nodes) + "\n"
        path = self.fixture.repo / owner
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(declarations, encoding="utf-8")
        league_names = ["engines/experiments/strength/" + name + ".py" for name in seed.LEAGUE_HOST_MODULES]
        league_names += list(seed.LEAGUE_CORE_R)
        for name in league_names:
            target_path = self.fixture.repo / name
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_bytes(b"# synthetic league transport source\n")
        git(self.fixture.repo, "add", "--", owner, *league_names)
        git(self.fixture.repo, "-c", "user.name=Transport Fixture", "-c", "user.email=fixture@example.invalid",
            "commit", "-qm", "synthetic lazy experiment declarations")

        def checkout():
            head = git(self.fixture.repo, "rev-parse", "HEAD").decode().strip()
            return ({**self.fixture.config["checkout"], "commit": head},
                    {**self.fixture.config["source_origin"], "head_sha": head})

        selected, origin = checkout()
        seed.checkout_files(selected, origin)
        with self.assertRaisesRegex(ValueError, "named production Python dependency omitted"):
            seed.checkout_files(selected, origin, league_required=True)

        dependencies = set(seed.named_python_dependencies(declarations.encode(), source_name=owner,
                                                          league_required=True))
        self.assertIn("engines/experiments/tcec-next/profile_league_compound.py", dependencies)
        for name in dependencies:
            dependency = self.fixture.repo / name
            dependency.parent.mkdir(parents=True, exist_ok=True)
            dependency.write_bytes(b"# synthetic optional profile dependency\n")
        git(self.fixture.repo, "add", "--", *sorted(dependencies))
        git(self.fixture.repo, "-c", "user.name=Transport Fixture", "-c", "user.email=fixture@example.invalid",
            "commit", "-qm", "complete synthetic league experiment closure")
        selected, origin = checkout()
        league = seed.checkout_files(selected, origin, league_required=True)
        self.assertTrue(dependencies <= set(league))

        compound = "engines/experiments/tcec-next/profile_league_compound.py"
        incomplete = {**selected, "paths": [name for name in league if name != compound]}
        with self.assertRaisesRegex(ValueError, "named production Python dependency omitted: .*profile_league_compound.py"):
            seed.checkout_files(incomplete, origin, league_required=True)
        # Its reviewed inventory alone is not a requirement for older seeds.
        seed.checkout_files(incomplete, origin, league_required=False)

        # Legacy cannot bypass the actual same-file dependency using the
        # otherwise-exempt inventory path.
        missing = "engines/experiments/tcec-next/profile_acef_league_atomic.py"
        path.write_text(declarations + "open(" + repr(missing) + ")\n", encoding="utf-8")
        git(self.fixture.repo, "add", "--", owner)
        git(self.fixture.repo, "-c", "user.name=Transport Fixture", "-c", "user.email=fixture@example.invalid",
            "commit", "-qm", "actual reference outside inventory")
        selected, origin = checkout()
        selected = {**selected, "paths": [name for name in league if name != missing]}
        with self.assertRaisesRegex(ValueError, "named production Python dependency omitted: .*profile_acef_league_atomic.py"):
            seed.checkout_files(selected, origin)

    def test_compound_owner_files_are_lazy_only_within_exact_reviewed_declarations(self):
        root = Path(seed.__file__).resolve().parents[3]
        target = "engines/experiments/tcec-next/profile_league_compound.py"
        for owner in ("engines/experiments/tcec-next/profile_build.py",
                      "engines/experiments/tcec-next/profile_rules.py",
                      "engines/experiments/tcec-next/profile_verify.py"):
            raw = (root / owner).read_bytes()
            with self.subTest(owner=owner):
                self.assertNotIn(target, seed.named_python_dependencies(raw, source_name=owner, league_required=False))
                self.assertIn(target, seed.named_python_dependencies(raw, source_name=owner, league_required=True))
                self.assertIn(target, seed.named_python_dependencies(raw + ("\nopen(" + repr(target) + ")\n").encode(),
                                                                    source_name=owner, league_required=False))

    def test_p16_p192_source_seed_fixture_round_trips_without_admission(self):
        """Synthetic source/CI evidence only; no host, engine or AWS operation."""
        names = ["engines/experiments/strength/" + name + ".py" for name in seed.LEAGUE_HOST_MODULES]
        names += list(seed.LEAGUE_CORE_R)
        for name in names:
            path = self.fixture.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"# synthetic league transport source\n")
        git(self.fixture.repo, "add", "--", *names)
        git(self.fixture.repo, "-c", "user.name=Transport Fixture", "-c", "user.email=fixture@example.invalid",
            "commit", "-qm", "add league transport closure")
        head = git(self.fixture.repo, "rev-parse", "HEAD").decode().strip()
        self.fixture.config["checkout"]["commit"] = head
        self.fixture.config["source_origin"]["head_sha"] = head
        metadata = json.loads(Path(self.fixture.inputs["metadata/A-artifact.json"]["path"]).read_bytes())
        metadata["workflow_run"]["head_sha"] = head
        self.fixture.rewrite("metadata/A-artifact.json", metadata)
        seal = json.loads(Path(self.fixture.inputs["origin/A/source-seal.json"]["path"]).read_bytes())
        seal["ci_context"]["head_sha"] = head
        for profile in ("test-p16", "test-p192"):
            with self.subTest(profile=profile):
                self.fixture.config["rove"][0]["profile"] = profile
                seal["profiles"][0]["profile"] = profile
                self.fixture.rewrite("origin/A/source-seal.json", seal)
                out = self.root / ("synthetic-" + profile)
                self.fixture.prepare(out)
                manifest = json.loads((out / "seed.json").read_bytes())
                self.assertEqual(manifest["rove"][0]["profile"], profile)
                self.assertTrue(all("source/" + name in manifest["members"] for name in names))
                self.assertFalse(any(key in manifest for key in ("qualified", "complete", "scoring")))
                with zipfile.ZipFile(out / "seed.zip") as archive:
                    self.assertTrue(all(archive.read("source/" + name) == b"# synthetic league transport source\n"
                                        for name in names))

    def joint_fixture(self):
        """Twelve distinct synthetic sealed rows; never source/runtime admission."""
        fixture = self.fixture
        original_seal = json.loads(Path(fixture.inputs["origin/A/source-seal.json"]["path"]).read_bytes())
        bundle = Path(fixture.inputs["origin/A/source-bundle.zip"]["path"]).read_bytes()
        fixture.inputs = {name: value for name, value in fixture.inputs.items()
                          if not name.startswith(("origin/", "metadata/"))}
        fixture.config["inputs"] = fixture.inputs
        fixture.config["rove"], roots = [], []
        def add(name, raw):
            path = self.root / "joint-downloaded" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            fixture.inputs[name] = {"path": str(path), **seed.pin(raw)}
        reader = "engines/scripts/production_input.py"
        for number, (family, profile) in enumerate((f, p) for f in "ABCDEF" for p in ("test-p4", "test-p28")):
            key, prefix = family + "-" + profile, "origin/" + family + "-" + profile
            original = "/home/runner/work/_temp/export-" + key
            seal = copy.deepcopy(original_seal)
            seal["profiles"][0].update(family=family, profile=profile, build_root=original + "/artifact")
            seal["restore_layout"] = {"runner_temp_root": "/home/runner/work/_temp", "output_root": original,
                                      "builds": {"artifact": original + "/artifact"}}
            add(prefix + "/source-bundle.zip", bundle)
            add(prefix + "/source-seal.json", ledger.canonical(seal))
            metadata = "metadata/" + key + ".json"
            add(metadata, ledger.canonical({"id": 100 + number, "workflow_run": {
                "id": 123, "head_sha": fixture.config["source_origin"]["head_sha"]}}))
            rules = "origin/rules/" + key
            add(rules + "/probe/rules.json", ledger.canonical({"family": family, "profile": profile,
                "complete": True, "verifier_inputs": {reader: seed.pin((fixture.repo / reader).read_bytes())}}))
            add(rules + "/probe/cases.json", b"[]")
            add(rules + "/probe/fixture.c", b"/* unit fixture; never executed */")
            add(rules + "/commands.json", b"{}")
            fixture.config["rove"].append({"family": family, "profile": profile, "build": prefix + "/artifact",
                "source_bundle": prefix + "/source-bundle.zip", "source_seal": prefix + "/source-seal.json",
                "artifact_metadata": metadata, "rules": rules + "/probe/rules.json"})
            roots += [{"original_root": original, "seed_prefix": prefix},
                      {"original_root": "/home/runner/work/_temp/rules-" + key, "seed_prefix": rules}]
        fixture.config["original_layout"] = {"roots": roots}
        add("unit/filler", b"x" * (300 << 10))
        return fixture

    def test_real_producer_and_inspector_grant_joint_capacity_only_to_twelve_rows(self):
        fixture, consumer = self.joint_fixture(), seed.runtime()
        # Scale only fixed test constants; no configurable numeric limit is
        # introduced. The real archive is small and no engine is executed.
        with patch.object(seed, "MAX_SEED", 256 << 10), patch.object(consumer, "MAX_SEED", 256 << 10), \
             patch.object(consumer, "JOINT_EXPANDED_SEED", 512 << 10):
            receipt = fixture.prepare(self.root / "joint")
            raw = Path(receipt["archive"]["path"]).read_bytes()
            self.assertLess(len(raw), 256 << 10)
            self.assertEqual(seed.inspect_archive(raw)["manifest_sha256"], receipt["seed_manifest"]["sha256"])
            manifest_raw = Path(receipt["seed_manifest"]["path"]).read_bytes()
            manifest = json.loads(manifest_raw)
            expanded = sum(row["bytes"] for row in manifest["members"].values()) + len(manifest_raw)
            self.assertGreater(expanded, 256 << 10)
            with patch.object(consumer, "JOINT_EXPANDED_SEED", expanded):
                fixture.prepare(self.root / "exact-joint-boundary")
                seed.inspect_archive(raw)
            with patch.object(consumer, "JOINT_EXPANDED_SEED", expanded - 1):
                with self.assertRaisesRegex(ValueError, "expan|bound"):
                    fixture.prepare(self.root / "over-joint-boundary")
                self.assertFalse((self.root / "over-joint-boundary").exists())
            fixture.config["rove"].pop()
            fixture.config["expanded_limit"] = 512 << 10  # Ignored untrusted extra data, never authority.
            with self.assertRaisesRegex(ValueError, "expanded"):
                fixture.prepare(self.root / "missing-one-row")
            self.assertFalse((self.root / "missing-one-row").exists())
            self.assertFalse(receipt["native_qualified"] or receipt["engine_executed"])

    def test_p4_plus_peer_p28_and_duplicate_joint_reject_before_source_collection(self):
        consumer = seed.runtime()
        self.fixture.config["peers"] = [{"family": "ice4", "profile": "test-p28"}]
        self.assertEqual(consumer.seed_expansion_limit(self.fixture.config), 128 << 20)
        self.fixture.config["rove"].append(copy.deepcopy(self.fixture.config["rove"][0]))
        with patch.object(seed, "checkout_files", side_effect=AssertionError("no source collection for invalid cohort")), \
             self.assertRaisesRegex(ValueError, "duplicate"):
            self.fixture.prepare(self.root / "duplicate")
        self.assertFalse((self.root / "duplicate").exists())

    def test_external_input_metadata_rejects_count_size_and_identity_before_payload_reads(self):
        good = {"path": str(self.root / "absent-input"), "bytes": seed.MAX_MEMBER, "sha256": "0" * 64}
        variants = [
            {"unit/" + str(i): dict(good) for i in range(5)},
            {"unit/" + str(i): {**good, "bytes": 0} for i in range(20000)},
            {"unit/numeric-sha": {**good, "bytes": 0, "sha256": int("1" * 64)}},
        ]
        for number, inputs in enumerate(variants):
            self.fixture.config["inputs"] = inputs
            out = self.root / ("invalid-metadata-" + str(number))
            with patch.object(seed, "checkout_files", side_effect=AssertionError("source bytes must not be read")), \
                 patch.object(seed, "checked_input", side_effect=AssertionError("input bytes must not be read")), \
                 self.assertRaises(ValueError):
                seed.prepare(self.fixture.config, out)
            self.assertFalse(out.exists())

    def test_git_source_sizes_reserve_external_budget_before_reading_any_blob(self):
        identity = {"path": str(self.root / "absent-input"), "bytes": seed.MAX_MEMBER, "sha256": "0" * 64}
        self.fixture.config["inputs"] = {"unit/" + str(i): dict(identity) for i in range(4)}
        self.fixture.config["inputs"]["unit/3"]["bytes"] -= 1  # Leave one byte for the entire real source checkout.
        original, calls = seed.git, []
        def observed(checkout, *args, **kwargs):
            calls.append(args)
            return original(checkout, *args, **kwargs)
        with patch.object(seed, "git", side_effect=observed), \
             patch.object(seed, "checked_input", side_effect=AssertionError("external bytes must not be read")), \
             self.assertRaisesRegex(ValueError, "source metadata.*expanded"):
            seed.prepare(self.fixture.config, self.root / "source-budget")
        self.assertTrue(any(args[:1] == ("cat-file",) and args[1].startswith("--batch-check") for args in calls))
        self.assertFalse(any(args[:2] == ("cat-file", "blob") for args in calls))
        self.assertFalse((self.root / "source-budget").exists())

    def test_source_zip_preflights_all_metadata_before_any_member_read(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr("first", b"1234")
            archive.writestr("last", b"5678")
        with patch.object(zipfile.ZipFile, "read", side_effect=AssertionError("no payload before aggregate guard")), \
             self.assertRaisesRegex(ValueError, "excessive"):
            seed.archive_members(stream.getvalue(), expanded_limit=7)

    def test_source_member_size_is_rejected_from_git_metadata_before_blob_read(self):
        original, calls = seed.git, []
        def oversized_metadata(checkout, *args, **kwargs):
            calls.append(args)
            if args[:1] == ("cat-file",) and args[1].startswith("--batch-check"):
                rows = original(checkout, *args, **kwargs).decode().splitlines()
                fields = rows[0].split()
                rows[0] = " ".join(fields[:2] + [str(seed.MAX_MEMBER + 1)])
                return ("\n".join(rows) + "\n").encode()
            return original(checkout, *args, **kwargs)
        with patch.object(seed, "git", side_effect=oversized_metadata), \
             self.assertRaisesRegex(ValueError, "per-member bound"):
            seed.prepare(self.fixture.config, self.root / "oversized-source")
        self.assertFalse(any(args[:2] == ("cat-file", "blob") for args in calls))
        self.assertFalse((self.root / "oversized-source").exists())

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


class OriginalReferenceTests(unittest.TestCase):
    """Real producer record shape; synthetic bytes are never CI authority."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="rove-seed-reference-")
        self.root = Path(self.temp.name)
        self.fixture = Fixture(self.root)
        self.original = "/home/runner/work/_temp/export-A/artifact"
        self.reference = {"format": "rove4k.target-runtime-reference.v1", "family": "A", "profile": "test-p4",
            "ci_context": copy.deepcopy(self.fixture.config["source_origin"]),
            "consumer_scope": "github-actions-ubuntu22-system", "representation": "source-jit", "full": True,
            "runtime_eligible": True, "factory_replayed_on_target": False,
            "runtime_executed": False, "runtime_qualified": False, "event_target_confirmed": False,
            "source_build": {"path": self.original, **seed.pin(b"{}\n")}}
        self.name = "origin/rules/A/target-runtime.json"

    def tearDown(self):
        self.temp.cleanup()

    def put(self, value):
        path = self.root / "downloaded" / self.name
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = ledger.canonical(value)
        path.write_bytes(raw)
        self.fixture.inputs[self.name] = {"path": str(path), **seed.pin(raw)}
        return raw

    def test_actual_directory_manifest_contract_survives_prepare_without_rewriting(self):
        value = {"stages": [{"target_runtime_reference": copy.deepcopy(self.reference)}],
                 "target_runtime_reference": copy.deepcopy(self.reference)}
        original = self.put(value)
        prepared = self.fixture.prepare(self.root / "prepared")
        with zipfile.ZipFile(prepared["archive"]["path"]) as archive:
            self.assertEqual(archive.read(self.name), original)
            self.assertEqual(json.loads(archive.read(self.name))["target_runtime_reference"]["source_build"],
                             self.reference["source_build"])
        self.assertEqual(seed.inspect_archive(Path(prepared["archive"]["path"]).read_bytes())["manifest_sha256"],
                         prepared["seed_manifest"]["sha256"])

    def test_unbound_reference_shapes_reject_before_any_output(self):
        changes = [
            {"format": "another.reference.v1"}, {"family": "B"}, {"family": ["A"]},
            {"profile": "test-p28"}, {"profile": None},
            {"ci_context": {**self.reference["ci_context"], "run_attempt": "2"}},
            {"ci_context": {}}, {"consumer_scope": "ec2"}, {"representation": "native"},
            {"full": 1}, {"runtime_eligible": 1}, {"factory_replayed_on_target": 0},
            {"source_build": {**self.reference["source_build"], "path": self.original + "-other"}},
            {"source_build": {**self.reference["source_build"], "path": self.original + "/build.json"}},
            {"source_build": {**self.reference["source_build"], "sha256": "0" * 64}},
            {"source_build": {**self.reference["source_build"], "bytes": True}},
            {"source_build": {**self.reference["source_build"], "extra": "not the record contract"}},
            {"source_build": None},
        ]
        for field in ("runtime_executed", "runtime_qualified", "event_target_confirmed"):
            changes.extend({field: value} for value in (None, True, 0))
        for index, change in enumerate(changes):
            self.put({**copy.deepcopy(self.reference), **change})
            out = self.root / ("rejected-" + str(index))
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.fixture.prepare(out)
            self.assertFalse(out.exists())

    def pure(self, value, *, build=b"{}\n", include_manifest=True, source_builds=None):
        content = {"origin/A/artifact/main.c": (b"x", 0o600),
                   self.name: (ledger.canonical(value), 0o600)}
        if include_manifest:
            content["origin/A/artifact/build.json"] = (build, 0o600)
        mappings = self.fixture.config["original_layout"]["roots"]
        sources = source_builds if source_builds is not None else {
            ("A", "test-p4"): {"path": self.original, "member": "origin/A/artifact/build.json"}}
        return seed.original_references(content, mappings, sources, self.fixture.config["source_origin"])

    def test_missing_or_ambiguous_selected_manifest_is_not_a_directory_exception(self):
        with self.assertRaisesRegex(ValueError, "omitted its exact build.json"):
            self.pure(self.reference, include_manifest=False)
        sources = {(family, "test-p4"): {"path": self.original, "member": "origin/A/artifact/build.json"}
                   for family in "AB"}
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            self.pure(self.reference, source_builds=sources)

    def test_ordinary_file_pins_remain_strict_and_boolean_lengths_are_not_integers(self):
        ordinary = {"path": self.original + "/main.c", **seed.pin(b"x")}
        counts = self.pure({"reference": self.reference, "ordinary": ordinary})
        self.assertEqual(counts, {"source_build_references": 1, "file_references": 1})
        for change in ({"sha256": "0" * 64}, {"path": self.original}, {"bytes": True}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.pure({"reference": self.reference, "ordinary": {**ordinary, **change}})
        value = copy.deepcopy(self.reference)
        value["source_build"].update(seed.pin(b"1"), bytes=True)
        with self.assertRaisesRegex(ValueError, "exact typed file pin"):
            self.pure(value, build=b"1")


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

    def advanced_client(self):
        # Construct through the exact namespace used by the actual publisher;
        # a structurally similar dataclass from another loader is not authority.
        self.plan = seed.aws.AWSPlan.from_dict(base_advanced_plan().as_dict())
        self.client = AdvancedFakeS3(self.plan, self.journal)
        return self.client

    def assert_no_publication_intent(self):
        self.assertEqual(self.client.puts, 0)
        self.assertEqual(self.client.objects, {})
        self.assertEqual(self.journal.rows, [])
        self.assertEqual(self.client.account_plan_reads, 0)

    def test_advanced_first_publish_uses_fresh_metadata_without_getplan(self):
        client = self.advanced_client()
        result = seed.publish(client, self.plan, self.archive, self.key, self.journal)
        self.assertTrue(result["verified"] and result["upload_performed"])
        self.assertEqual(result["seed"]["version_id"], "version-one")
        self.assertEqual(client.puts, 1)
        self.assertEqual(client.account_plan_reads, 0)
        operations = [(service, operation) for service, operation, _ in client.calls]
        self.assertIn(("account", "get-account-information"), operations)
        self.assertIn(("organizations", "describe-organization"), operations)
        self.assertFalse(any(service == "freetier" for service, _, _ in client.calls))
        self.assertEqual([row["event"] for row in self.journal.rows], ["seed.upload_requested", "seed.upload_confirmed"])

    def test_advanced_unknown_account_or_organization_blocks_before_put_or_intent(self):
        for unknown in ("account", "organization"):
            with self.subTest(unknown=unknown):
                client = self.advanced_client()
                if unknown == "account":
                    client.account_information = None
                else:
                    client.organization = {}
                with self.assertRaisesRegex(ValueError, "fresh own-account|fresh organization"):
                    seed.publish(client, self.plan, self.archive, self.key, self.journal)
                self.assert_no_publication_intent()

    def test_advanced_wrong_caller_account_metadata_or_state_blocks_before_put(self):
        for changed in ("caller", "account-id", "account-state", "organization"):
            with self.subTest(changed=changed):
                client = self.advanced_client()
                if changed == "caller":
                    client.caller_account = "814650855198"
                elif changed == "account-id":
                    client.account_information["AccountId"] = "814650855198"
                elif changed == "account-state":
                    client.account_information["AccountState"] = "SUSPENDED"
                else:
                    client.organization["Organization"]["Id"] = "o-unreviewed"
                with self.assertRaises(ValueError):
                    seed.publish(client, self.plan, self.archive, self.key, self.journal)
                self.assert_no_publication_intent()

    def test_advanced_read_api_errors_never_create_publication_intent(self):
        for service, operation in (("account", "get-account-information"), ("organizations", "describe-organization")):
            for code in ("AccessDeniedException", "ResourceNotFoundException", "ObservationTimeout"):
                with self.subTest(service=service, code=code):
                    client = self.advanced_client()
                    client.metadata_errors[service, operation] = seed.aws.AwsError(code, service + "." + operation)
                    with self.assertRaisesRegex(ValueError, code):
                        seed.publish(client, self.plan, self.archive, self.key, self.journal)
                    self.assert_no_publication_intent()

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
