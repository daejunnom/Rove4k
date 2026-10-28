"""Offline CI input/context fault tests; no cloud or engine qualification."""
from dataclasses import asdict, replace
from datetime import datetime, timezone
import ast
import base64
import copy
import hashlib
import importlib.util
import os
from pathlib import Path
import py_compile
import re
import signal
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

try:
    from . import campaign_ci as ci
    from . import aws, budget, ledger
    from .test_aws import plan as base_plan
except ImportError:
    import campaign_ci as ci
    import aws
    import budget
    import ledger
    from test_aws import plan as base_plan


ACCOUNT = "292341339363"
REGION = "ap-southeast-2"
ROLE = "arn:aws:iam::" + ACCOUNT + ":role/rove-controller"
BUCKET = "rove-ci-artifacts"
START = 2_000_000_000
NOW = START + 100
HEAD = "c" * 40


def iso(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def request():
    plan = replace(base_plan(), account_id=ACCOUNT, region=REGION, project_region=REGION,
        launch_token="launch-token-0001", artifact_bucket=BUCKET,
        instance_profile_arn="arn:aws:iam::" + ACCOUNT + ":instance-profile/rove-instance",
        controller_role_arn=ROLE,
        watchdog_arn="arn:aws:lambda:" + REGION + ":" + ACCOUNT + ":function:rove-watchdog",
        deadline_epoch=START + 20700)
    return {"format": "rove4k-campaign-ci-v1", "aws_plan": asdict(plan),
        "seed": {"bucket": BUCKET, "key": "campaign-a/seed/" + "a" * 64 + ".zip",
                 "version_id": "original-version-1", "sha256": "a" * 64, "bytes": 100},
        "seed_manifest_sha256": "b" * 64,
        "source_origin": {"repository": "daejunnom/Rove4k", "head_sha": "a" * 40,
                          "run_id": "40228534420", "run_attempt": "1"},
        "workflow_provenance": {"run": "metadata/run.completed.original.json",
                                "commit": "metadata/execution-commit.original.json",
                                "pull_request": "metadata/pull-request.original.json"},
        "reviewed_deployment": {"template_sha256": "d" * 64, "watchdog_source_sha256": "e" * 64,
            "function_code_sha256": base64.b64encode(hashlib.sha256(b"unit deployment identity").digest()).decode(),
            "function_revision_id": "unit-revision-1"},
        "bootstrap": {"recipe_id": "rove4k-ubuntu22-ssm-bootstrap-v1", "recipe_sha256": "f" * 64},
        "journal": None}


def context_inputs():
    env = {"GITHUB_ACTIONS": "true", "GITHUB_REPOSITORY": "daejunnom/Rove4k",
           "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_RUN_ID": "77",
           "GITHUB_RUN_ATTEMPT": "2", "GITHUB_SHA": HEAD,
           "GITHUB_WORKFLOW_REF": "daejunnom/Rove4k/.github/workflows/aws-evaluation.yml@refs/heads/main"}
    run = {"id": 77, "run_attempt": 2, "repository": {"id": 100, "full_name": "daejunnom/Rove4k"},
           "head_repository": {"id": 100, "full_name": "daejunnom/Rove4k"}, "head_branch": "main",
           "event": "workflow_dispatch", "status": "in_progress", "head_sha": HEAD,
           "path": ".github/workflows/aws-evaluation.yml", "run_started_at": iso(START)}
    jobs = {"total_count": 1, "jobs": [{"id": 88, "run_id": 77, "run_attempt": 2,
        "head_sha": HEAD,
        "name": "Rove4k AWS evaluation", "status": "in_progress", "started_at": iso(START + 20),
        "steps": [{"number": 3, "name": "Configure AWS controller OIDC", "status": "completed",
                   "conclusion": "success", "started_at": iso(START + 30), "completed_at": iso(START + 40)}]}]}
    return run, jobs, env


class RequestTests(unittest.TestCase):
    def parse(self, value):
        # These ports must remain pure; an accidental service access is a failure.
        with patch("urllib.request.urlopen", side_effect=AssertionError("no network in request parser")):
            return ci.parse_request(value, campaign_id="campaign-a", role_arn=ROLE, bucket=BUCKET)

    def test_real_plan_record_and_immutable_seed_are_preserved(self):
        value = request()
        before = copy.deepcopy(value)
        result = self.parse(value)
        self.assertEqual(result, before)
        self.assertEqual(value, before)
        self.assertNotEqual(result["source_origin"]["head_sha"], HEAD)

    def test_ordinary_source_workflow_can_bind_run_and_commit_without_a_pr(self):
        value = request(); value["workflow_provenance"].pop("pull_request")
        self.assertEqual(self.parse(value)["workflow_provenance"], value["workflow_provenance"])

    def test_execution_base_proof_is_an_explicit_fourth_original_member_role(self):
        value = request()
        value["workflow_provenance"]["execution_base_proof"] = "metadata/execution-base-proof.json"
        before = copy.deepcopy(value)
        self.assertEqual(self.parse(value), before)
        self.assertEqual(value, before)

    def test_execution_base_proof_never_replaces_a_required_original_or_adds_unknown_roles(self):
        original = {**request()["workflow_provenance"], "execution_base_proof": "metadata/execution-base-proof.json"}
        invalid = [{key: value for key, value in original.items() if key != removed}
                   for removed in ("run", "commit", "pull_request")]
        invalid += [{**original, "ancestor": True}, {"execution_base_proof": "metadata/proof.json"},
                    {**original, "execution_base_proof": True},
                    {**original, "execution_base_proof": original["run"]},
                    {**original, "execution_base_proof": "../proof.json"},
                    {**original, "execution_base_proof": "metadata/.env.proof"},
                    {**original, "execution_base_proof": "metadata/credential.json"}]
        for roles in invalid:
            with self.subTest(roles=roles), self.assertRaises(ValueError):
                value = request(); value["workflow_provenance"] = roles
                self.parse(value)

    def test_seed_version_must_be_explicit_not_latest_or_null(self):
        for version in (None, "", "null"):
            with self.subTest(version=version):
                value = request(); value["seed"]["version_id"] = version
                with self.assertRaises(ValueError):
                    self.parse(value)

    def test_seed_transfer_bound_accepts_128mib_and_rejects_excess(self):
        value = request(); value["seed"]["bytes"] = 128 << 20
        self.assertEqual(self.parse(value)["seed"]["bytes"], 128 << 20)
        for size in ((128 << 20) + 1, 0, -1, True):
            with self.subTest(size=size):
                value = request(); value["seed"]["bytes"] = size
                with self.assertRaises(ValueError):
                    self.parse(value)

    def test_seed_namespace_and_bucket_cannot_change_campaign(self):
        for key, bad in (("bucket", "different-bucket"), ("key", "other-campaign/seed.zip"),
                         ("key", "campaign-a/../seed.zip")):
            with self.subTest(key=key, bad=bad):
                value = request(); value["seed"][key] = bad
                with self.assertRaises(ValueError):
                    self.parse(value)

    def test_source_ci_repository_commit_and_attempt_are_exact(self):
        for key, bad in (("repository", "other/Rove4k"), ("head_sha", "refs/heads/main"),
                         ("run_id", "0"), ("run_attempt", "0")):
            with self.subTest(key=key, bad=bad):
                value = request(); value["source_origin"][key] = bad
                with self.assertRaises(ValueError):
                    self.parse(value)

    def test_plan_account_region_and_controller_role_are_fixed(self):
        for key, bad in (("account_id", "000000000000"), ("region", "us-east-1"),
                         ("project_region", "us-east-1"),
                         ("controller_role_arn", "arn:aws:iam::" + ACCOUNT + ":role/another-controller"),
                         ("campaign_id", "other-campaign")):
            with self.subTest(key=key, bad=bad):
                value = request(); value["aws_plan"][key] = bad
                with self.assertRaises(ValueError):
                    self.parse(value)

    def test_passing_flags_are_not_accepted_as_input_authority(self):
        for key in ("passed", "qualified", "complete"):
            with self.subTest(key=key):
                value = request(); value[key] = True
                with self.assertRaises(ValueError):
                    self.parse(value)

    def test_reviewed_deployment_requires_every_actual_identity(self):
        for key in tuple(request()["reviewed_deployment"]):
            with self.subTest(key=key):
                value = request(); value["reviewed_deployment"].pop(key)
                with self.assertRaises(ValueError):
                    self.parse(value)

    def test_provenance_roles_must_name_distinct_normalized_members(self):
        for proof in ({"run": "metadata/same.json", "commit": "metadata/same.json"},
                      {"run": "../outside.json", "commit": "metadata/commit.json"},
                      {"run": "metadata/run.json"}):
            with self.subTest(proof=proof):
                value = request(); value["workflow_provenance"] = proof
                with self.assertRaises(ValueError):
                    self.parse(value)

    def test_journal_is_an_explicit_full_hash_chain_descriptor(self):
        value = request()
        value["journal"] = {"object_key": "campaign-a/controller-journals/" + "1" * 64 + ".jsonl",
                            "sha256": "1" * 64, "bytes": 1200, "rows": 3, "last_sha256": "2" * 64}
        self.assertEqual(self.parse(value)["journal"], value["journal"])
        for key in ("sha256", "last_sha256", "rows"):
            with self.subTest(key=key):
                changed = copy.deepcopy(value); changed["journal"].pop(key)
                with self.assertRaises(ValueError):
                    self.parse(changed)


class WorkflowProvenancePassThroughTests(unittest.TestCase):
    """Exercise the registered caller boundary, with the frozen worker as a port.

    Git/object semantics are tested by the actual common worker's own suites.
    These tests establish that this independent stdlib transport retains all
    four roles and compares its complete result before any service access.
    """
    def fixture(self, root):
        value = request()
        value["workflow_provenance"]["execution_base_proof"] = "metadata/execution-base-proof.json"
        ci.parse_request(value, campaign_id="campaign-a", role_arn=ROLE, bucket=BUCKET)
        files = {name: ci.canonical({"fixture_role": role}) + b"\n"
                 for role, name in value["workflow_provenance"].items()}
        for name, body in files.items():
            path = root / "seed" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
        computed = {"kind": "execution-base-ancestor-v1", "event": "pull_request",
            "repository": value["source_origin"]["repository"], "repository_id": 100,
            "run_id": value["source_origin"]["run_id"], "run_attempt": value["source_origin"]["run_attempt"],
            "api_head_sha": "d" * 40, "checkout_sha": value["source_origin"]["head_sha"],
            "execution_tree": "e" * 40, "execution_parents": ["f" * 40, "d" * 40],
            "inputs": {name: ci.pin(body) for name, body in files.items()}, "pull_request": 12,
            "ref": "refs/pull/12/merge", "head_branch": "feature/fixture", "head_repository_id": 100,
            "documents": copy.deepcopy(value["workflow_provenance"]), "reported_base_sha": "b" * 40,
            "execution_base_sha": "f" * 40, "base_ref": "refs/heads/develop"}
        manifest = {"source_origin": value["source_origin"],
            "members": {name: {**ci.pin(body), "mode": 0o600} for name, body in files.items()},
            "workflow_provenance": {**copy.deepcopy(computed), "artifact_metadata": {"transport-only": {"sha256": "0" * 64}}}}
        source_root = root / "original-source"
        source = SimpleNamespace(__file__=str(source_root / "engines/experiments/strength/seed.py"))
        def bind(config, members, origin, api_head):
            self.assertEqual(config["workflow_provenance"], value["workflow_provenance"])
            self.assertEqual(config["checkout"], {"path": str(root / "origin"), "commit": value["source_origin"]["head_sha"]})
            self.assertEqual(origin, value["source_origin"])
            self.assertEqual(api_head, computed["api_head_sha"])
            self.assertEqual({name: body for name, (body, mode) in members.items()}, files)
            self.assertTrue(all(mode == 0o600 for body, mode in members.values()))
            return copy.deepcopy(computed)
        source.workflow_binding = Mock(side_effect=bind)
        identity = Mock(return_value={"caller_arn": "arn:aws:sts::" + ACCOUNT + ":assumed-role/rove-controller/rove4k-77-2"})
        cloud = SimpleNamespace(_SIBLING_PACKAGE="fixture_frozen", ROOT=source_root,
            HERE=source_root / "engines/experiments/strength",
            load_module=Mock(return_value=SimpleNamespace(template=Mock(return_value={
                "Resources": {"ControllerRole": {"Properties": {"MaxSessionDuration": ci.DURATION}}}}))),
            aws=SimpleNamespace(AWSPlan=aws.AWSPlan, AWSCLI=Mock(return_value=SimpleNamespace(region=REGION)), verify_caller=identity))
        return value, computed, manifest, source, cloud

    def invoke(self, root, value, manifest, source, cloud):
        # Resolve the network target before the import mock also affects mock's resolver.
        with patch.object(ci, "load_stage", return_value=({"root": str(root)}, value, {"run_id": "77", "run_attempt": "2"})), \
             patch.object(ci, "load_frozen", return_value=(cloud, manifest)) as load, \
             patch("urllib.request.urlopen", side_effect=AssertionError("no network in caller test")), \
             patch.object(ci.importlib, "import_module", return_value=source) as imported, \
             patch.object(ci, "aws_call", side_effect=AssertionError("no service call in caller test")):
            result = ci.frozen_inputs(root / "stage.json", root / "origin")
        load.assert_called_once_with(root / "seed", value["seed_manifest_sha256"], origin=root / "origin",
                                     expected_source_origin=value["source_origin"])
        imported.assert_called_once_with("fixture_frozen.seed")
        return result

    def test_four_roles_and_full_new_worker_result_pass_unchanged(self):
        with tempfile.TemporaryDirectory(prefix="rove-ci-proof-pass-") as temporary:
            root = Path(temporary)
            value, computed, manifest, source, cloud = self.fixture(root)
            before = copy.deepcopy((value, manifest))
            result = self.invoke(root, value, manifest, source, cloud)
            self.assertEqual((value, manifest), before)
            self.assertIs(result[1], value)
            self.assertIs(result[4], manifest)
            self.assertEqual(source.workflow_binding.call_count, 1)
            cloud.aws.verify_caller.assert_called_once()

    def test_every_new_provenance_field_remains_in_the_exact_comparison(self):
        for field in ("documents", "reported_base_sha", "execution_base_sha", "base_ref", "inputs", "execution_parents"):
            with self.subTest(field=field), tempfile.TemporaryDirectory(prefix="rove-ci-proof-compare-") as temporary:
                root = Path(temporary)
                value, computed, manifest, source, cloud = self.fixture(root)
                provenance = manifest["workflow_provenance"]
                if field == "documents":
                    provenance[field] = {key: val for key, val in provenance[field].items() if key != "execution_base_proof"}
                elif field == "inputs":
                    provenance[field][value["workflow_provenance"]["execution_base_proof"]]["sha256"] = "1" * 64
                elif field == "execution_parents":
                    provenance[field] = list(reversed(provenance[field]))
                else:
                    provenance[field] = "changed"
                with self.assertRaisesRegex(ValueError, "original run/PR/Git binding differs"):
                    self.invoke(root, value, manifest, source, cloud)
                self.assertEqual(source.workflow_binding.call_count, 1)
                cloud.load_module.assert_not_called()
                cloud.aws.AWSCLI.assert_not_called()
                cloud.aws.verify_caller.assert_not_called()

    def test_missing_proof_member_or_wrong_source_module_never_reaches_identity(self):
        for fault in ("missing-proof", "wrong-module"):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory(prefix="rove-ci-proof-source-") as temporary:
                root = Path(temporary)
                value, computed, manifest, source, cloud = self.fixture(root)
                if fault == "missing-proof":
                    (root / "seed" / value["workflow_provenance"]["execution_base_proof"]).unlink()
                else:
                    source.__file__ = str(root / "different-source.py")
                with self.assertRaises((ValueError, FileNotFoundError)):
                    self.invoke(root, value, manifest, source, cloud)
                source.workflow_binding.assert_not_called()
                cloud.aws.verify_caller.assert_not_called()


class ContextTests(unittest.TestCase):
    def bind(self, values=None, now=NOW):
        run, jobs, env = context_inputs() if values is None else values
        with patch("urllib.request.urlopen", side_effect=AssertionError("context binding must use supplied API evidence")):
            return ci.bind_context(run, jobs, env, now)

    def test_live_run_job_and_successful_oidc_step_define_safe_bound(self):
        result = self.bind()
        self.assertEqual(result["run_started_at_epoch"], START)
        self.assertEqual(result["job_started_at_epoch"], START + 20)
        self.assertEqual(result["oidc_step_started_at_epoch"], START + 30)
        self.assertEqual(result["conservatively_safe_use_until"], START + 21600)
        self.assertEqual(result["campaign_deadline_limit"], START + 20700)
        self.assertIsNone(result["actual_STS_expiration"])
        self.assertIs(result["actual_STS_expiration_observed"], False)

    def test_api_run_cannot_relabel_repository_head_or_attempt(self):
        changes = (("id", 78), ("run_attempt", 3), ("head_sha", "d" * 40),
                   ("event", "push"), ("status", "completed"),
                   ("repository", {"id": 200, "full_name": "other/Rove4k"}))
        for key, value in changes:
            with self.subTest(key=key):
                run, jobs, env = context_inputs(); run[key] = value
                with self.assertRaises(ValueError):
                    self.bind((run, jobs, env))

    def test_actual_environment_must_identify_github_workflow_dispatch(self):
        for key, value in (("GITHUB_ACTIONS", "false"), ("GITHUB_REPOSITORY", "other/Rove4k"),
                           ("GITHUB_EVENT_NAME", "push"), ("GITHUB_RUN_ID", "78"),
                           ("GITHUB_RUN_ATTEMPT", "3"), ("GITHUB_SHA", "d" * 40),
                           ("GITHUB_WORKFLOW_REF", "daejunnom/Rove4k/.github/workflows/other.yml@refs/heads/main")):
            with self.subTest(key=key):
                run, jobs, env = context_inputs(); env[key] = value
                with self.assertRaises(ValueError):
                    self.bind((run, jobs, env))

    def test_job_and_auth_step_must_be_unique(self):
        run, jobs, env = context_inputs(); jobs["jobs"].append(copy.deepcopy(jobs["jobs"][0]))
        jobs["total_count"] = 2
        with self.assertRaises(ValueError):
            self.bind((run, jobs, env))
        run, jobs, env = context_inputs()
        jobs["jobs"][0]["steps"].append(copy.deepcopy(jobs["jobs"][0]["steps"][0]))
        with self.assertRaises(ValueError):
            self.bind((run, jobs, env))

    def test_job_metadata_cannot_name_another_attempt_or_a_finished_job(self):
        for key, value in (("run_id", 78), ("run_attempt", 3), ("status", "completed"),
                           ("name", "another job"), ("steps", None)):
            with self.subTest(key=key):
                run, jobs, env = context_inputs(); jobs["jobs"][0][key] = value
                with self.assertRaises(ValueError):
                    self.bind((run, jobs, env))

    def test_nonfinite_or_non_numeric_local_time_cannot_create_an_auth_bound(self):
        for now in (float("nan"), float("inf"), -1, True, "now"):
            with self.subTest(now=now):
                with self.assertRaises(ValueError):
                    self.bind(now=now)

    def test_failed_or_unfinished_oidc_is_not_an_issuance_bound(self):
        for key, value in (("status", "in_progress"), ("conclusion", "failure"),
                           ("conclusion", "cancelled"), ("conclusion", "skipped")):
            with self.subTest(key=key, value=value):
                run, jobs, env = context_inputs(); jobs["jobs"][0]["steps"][0][key] = value
                with self.assertRaises(ValueError):
                    self.bind((run, jobs, env))

    def test_bad_future_or_reversed_started_times_fail_closed(self):
        changes = [("run", "not-a-time"), ("run", iso(-1)), ("run", iso(NOW + 1)),
                   ("job", iso(START - 1)), ("oidc", iso(START + 19)),
                   ("completed", iso(START + 29)), ("completed", iso(NOW + 1))]
        for kind, value in changes:
            with self.subTest(kind=kind, value=value):
                run, jobs, env = context_inputs()
                if kind == "run":
                    run["run_started_at"] = value
                elif kind == "job":
                    jobs["jobs"][0]["started_at"] = value
                else:
                    jobs["jobs"][0]["steps"][0]["completed_at" if kind == "completed" else "started_at"] = value
                with self.assertRaises(ValueError):
                    self.bind((run, jobs, env))


class DeadlineTests(unittest.TestCase):
    def context(self):
        return ci.bind_context(*context_inputs(), NOW)

    def test_exact_15_minute_reserve_is_allowed_without_rewriting_plan(self):
        value = request(); before = copy.deepcopy(value)
        ci.validate_window(value, self.context(), NOW)
        self.assertEqual(value, before)

    def test_one_second_over_bound_is_rejected_without_shortening_deadline(self):
        value = request(); value["aws_plan"]["deadline_epoch"] += 1
        before = copy.deepcopy(value)
        with self.assertRaises(ValueError):
            ci.validate_window(value, self.context(), NOW)
        self.assertEqual(value, before)

    def test_expired_deadline_or_exhausted_job_window_does_not_reset(self):
        for now in (START + 20700, START + 21601):
            with self.subTest(now=now):
                value = request(); before = copy.deepcopy(value)
                with self.assertRaises(ValueError):
                    ci.validate_window(value, self.context(), now)
                self.assertEqual(value, before)


class TransportTests(unittest.TestCase):
    def descriptor(self, body):
        return {"bucket": BUCKET, "key": "campaign-a/seed/request.json",
                "version_id": "version-unit-1", **ci.pin(body)}

    def test_exact_version_head_get_and_body_are_required(self):
        body = b'{"fixture":"offline service transport"}\n'
        descriptor = self.descriptor(body)
        calls = []
        with tempfile.TemporaryDirectory(prefix="rove-ci-version-") as directory:
            target = Path(directory) / "request.json"
            def service(name, operation, value, *, outfile=None):
                calls.append((name, operation, copy.deepcopy(value)))
                self.assertEqual(value, {"Bucket": BUCKET, "Key": descriptor["key"], "VersionId": "version-unit-1"})
                if operation == "get-object":
                    self.assertEqual(Path(outfile), target)
                    target.write_bytes(body)
                return {"VersionId": "version-unit-1", "ContentLength": len(body)}
            with patch.object(ci, "aws_call", side_effect=service):
                self.assertEqual(ci.fetch_version(descriptor, target, 4096), body)
            self.assertEqual([row[1] for row in calls], ["head-object", "get-object"])
            self.assertEqual(target.read_bytes(), body)

    def test_wrong_head_prevents_get_and_output(self):
        body = b"bounded response"
        for response in ({"VersionId": "another-version", "ContentLength": len(body)},
                         {"VersionId": "version-unit-1", "ContentLength": len(body) + 1}):
            with self.subTest(response=response), tempfile.TemporaryDirectory(prefix="rove-ci-head-") as directory:
                target = Path(directory) / "object"
                with patch.object(ci, "aws_call", return_value=response) as service:
                    with self.assertRaises(ValueError):
                        ci.fetch_version(self.descriptor(body), target, 4096)
                self.assertEqual(service.call_count, 1)
                self.assertEqual(service.call_args.args[1], "head-object")
                self.assertFalse(target.exists())

    def test_wrong_get_version_or_body_pin_preserves_failed_bytes(self):
        original = b"reviewed original"
        cases = [(b"unreviewed bytes", "version-unit-1"), (original, "different-version")]
        for body, version in cases:
            with self.subTest(body=body, version=version), tempfile.TemporaryDirectory(prefix="rove-ci-get-") as directory:
                target = Path(directory) / "object"
                def service(name, operation, value, *, outfile=None):
                    if operation == "head-object":
                        return {"VersionId": "version-unit-1", "ContentLength": len(original)}
                    target.write_bytes(body)
                    return {"VersionId": version, "ContentLength": len(original)}
                with patch.object(ci, "aws_call", side_effect=service) as port:
                    with self.assertRaises(ValueError):
                        ci.fetch_version(self.descriptor(original), target, 4096)
                self.assertEqual(port.call_count, 2)
                self.assertEqual(target.read_bytes(), body)

    def test_download_timeout_does_not_retry_or_delete_partial_evidence(self):
        body = b"reviewed original"
        with tempfile.TemporaryDirectory(prefix="rove-ci-timeout-") as directory:
            target = Path(directory) / "object"
            def service(name, operation, value, *, outfile=None):
                if operation == "head-object":
                    return {"VersionId": "version-unit-1", "ContentLength": len(body)}
                target.write_bytes(b"interrupted transfer")
                raise subprocess.TimeoutExpired("fake AWS transport", 60)
            with patch.object(ci, "aws_call", side_effect=service) as port:
                with self.assertRaises(subprocess.TimeoutExpired):
                    ci.fetch_version(self.descriptor(body), target, 4096)
            self.assertEqual(port.call_count, 2)
            self.assertEqual(target.read_bytes(), b"interrupted transfer")

    def test_pinned_local_read_rejects_mutation_and_oversize(self):
        body = b'{"request":"original"}\n'
        with tempfile.TemporaryDirectory(prefix="rove-ci-read-") as directory:
            target = Path(directory) / "request.json"
            target.write_bytes(body)
            self.assertEqual(ci.read_pinned(target, ci.pin(body), 4096), {"request": "original"})
            target.write_bytes(b'{"request":"replaced"}\n')
            with self.assertRaises(ValueError):
                ci.read_pinned(target, ci.pin(body), 4096)
            with patch.object(Path, "read_bytes", side_effect=AssertionError("oversize input must not be read")):
                with self.assertRaises(ValueError):
                    ci.ordinary(target, 1)

    def test_link_or_protected_name_is_rejected_before_read(self):
        with tempfile.TemporaryDirectory(prefix="rove-ci-path-") as directory:
            root = Path(directory)
            target = root / "ordinary.json"; target.write_bytes(b"safe ordinary fixture")
            linked = root / "hard-linked.json"
            os.link(target, linked)
            with self.assertRaises(ValueError):
                ci.ordinary(linked)
            with patch.object(Path, "read_bytes", side_effect=AssertionError("protected input must never be read")):
                with self.assertRaises(ValueError):
                    ci.ordinary(root / ".env")

    def test_duplicate_json_fields_do_not_last_writer_win(self):
        with self.assertRaises(ValueError):
            ci.document(b'{"seed":"original","seed":"replacement"}')

    def test_transport_keeps_environment_auth_and_blocks_profile_fallback(self):
        completed = SimpleNamespace(returncode=0, stdout=b'{"VersionId":"version-unit-1"}', stderr=b"")
        with patch.dict(os.environ, {"AWS_PROFILE": "fake-profile", "AWS_DEFAULT_PROFILE": "fake-default",
                                     "AWS_WEB_IDENTITY_TOKEN_FILE": "unused-unit-path",
                                     "AWS_ACCESS_KEY_ID": "unit-temporary-id", "AWS_SESSION_TOKEN": "unit-temporary-session"}), \
             patch.object(ci.subprocess, "run", return_value=completed) as process:
            self.assertEqual(ci.aws_call("s3api", "head-object", {"Bucket": BUCKET}), {"VersionId": "version-unit-1"})
        self.assertEqual(process.call_count, 1)
        passed = process.call_args.kwargs
        self.assertEqual(passed["timeout"], 60)
        environment = passed["env"]
        self.assertEqual(environment["AWS_CONFIG_FILE"], os.devnull)
        self.assertEqual(environment["AWS_SHARED_CREDENTIALS_FILE"], os.devnull)
        self.assertEqual(environment["AWS_MAX_ATTEMPTS"], "1")
        self.assertEqual(environment["AWS_ACCESS_KEY_ID"], "unit-temporary-id")
        self.assertEqual(environment["AWS_SESSION_TOKEN"], "unit-temporary-session")
        for key in ("AWS_PROFILE", "AWS_DEFAULT_PROFILE", "AWS_WEB_IDENTITY_TOKEN_FILE"):
            self.assertNotIn(key, environment)

    def test_transport_error_does_not_forward_untrusted_auth_diagnostics(self):
        completed = SimpleNamespace(returncode=1, stdout=b"", stderr=b"untrusted-auth-diagnostic-must-not-be-forwarded")
        with patch.object(ci.subprocess, "run", return_value=completed) as process:
            with self.assertRaises(ValueError) as caught:
                ci.aws_call("s3api", "head-object", {"Bucket": BUCKET})
        self.assertEqual(process.call_count, 1)
        self.assertNotIn("untrusted-auth-diagnostic", str(caught.exception))


class CampaignHistoryTests(unittest.TestCase):
    def ports(self, response, keys=(), snapshots=None):
        client = SimpleNamespace(call=Mock(return_value=response))
        snapshots = {} if snapshots is None else snapshots
        def read_verified(key, *, expected_sha, max_bytes):
            raw = snapshots[key]
            self.assertEqual(ci.pin(raw)["sha256"], expected_sha)
            self.assertLessEqual(len(raw), max_bytes)
            return raw
        publisher = SimpleNamespace(list_keys=Mock(return_value=list(keys)), read_verified=Mock(side_effect=read_verified))
        return SimpleNamespace(budget=budget, ledger=ledger), client, publisher

    def journal_descriptor(self, journal):
        return {"object_key": "campaign-a/controller-journals/" + ci.pin(journal.path.read_bytes())["sha256"] + ".jsonl",
                **ci.pin(journal.path.read_bytes()), "rows": len(journal.rows), "last_sha256": journal.last}

    def snapshot(self, raw):
        return "campaign-a/controller-journals/" + ci.pin(raw)["sha256"] + ".jsonl"

    def append_instance(self, journal, token, at, *, terminated):
        identity = "i-" + token
        journal.append("budget.launch_requested", {"launch_token": token, "max_hourly_usd": "8"}, time_utc=iso(at))
        journal.append("budget.instance_bound", {"launch_token": token, "instance_id": identity}, time_utc=iso(at + 1))
        if terminated:
            journal.append("budget.instance_observed", {"launch_token": token, "instance_id": identity,
                "state": "terminated", "evidence": "offline physical-termination fixture"}, time_utc=iso(at + 2))

    def test_fresh_empty_campaign_uses_actual_empty_ledger(self):
        value = request(); plan = base_plan()
        cloud, client, publisher = self.ports({"Items": []})
        with tempfile.TemporaryDirectory(prefix="rove-ci-history-") as directory, \
             ledger.Journal(Path(directory) / "campaign.jsonl", plan.campaign_id) as journal:
            ci.verify_campaign_history(cloud, client, plan, publisher, value, journal)
            self.assertEqual(journal.rows, [])
        self.assertEqual(client.call.call_args.args[:2], ("dynamodb", "query"))
        self.assertIs(client.call.call_args.args[2]["ConsistentRead"], True)
        publisher.list_keys.assert_called_once_with(plan.campaign_id + "/controller-journals/")

    def test_any_prior_remote_row_or_controller_journal_blocks_fresh_history(self):
        for response, keys in (({"Items": [{"record_id": {"S": "controller-marker"}}]}, ()),
                               ({"Items": []}, ("campaign-a/controller-journals/old.jsonl",))):
            with self.subTest(response=response, keys=keys), tempfile.TemporaryDirectory(prefix="rove-ci-reset-") as directory, \
                 ledger.Journal(Path(directory) / "campaign.jsonl", "campaign-a") as journal:
                cloud, client, publisher = self.ports(response, keys)
                with self.assertRaisesRegex(ValueError, "fresh/reset"):
                    ci.verify_campaign_history(cloud, client, base_plan(), publisher, request(), journal)
                self.assertEqual(journal.rows, [])

    def test_partial_ddb_page_never_proves_empty_campaign(self):
        cloud, client, publisher = self.ports({"Items": [], "LastEvaluatedKey": {"record_id": {"S": "more"}}})
        with tempfile.TemporaryDirectory(prefix="rove-ci-page-") as directory, \
             ledger.Journal(Path(directory) / "campaign.jsonl", "campaign-a") as journal:
            with self.assertRaisesRegex(ValueError, "complete bounded"):
                ci.verify_campaign_history(cloud, client, base_plan(), publisher, request(), journal)
        self.assertEqual(client.call.call_count, 1)
        publisher.list_keys.assert_not_called()

    def test_full_replay_retains_closed_old_instances_and_current_token(self):
        old, current = "launch-old-0001", "launch-current-0002"
        response = {"Items": [{"record_id": {"S": "launch#" + token}} for token in (old, current)]}
        with tempfile.TemporaryDirectory(prefix="rove-ci-full-history-") as directory, \
             ledger.Journal(Path(directory) / "campaign.jsonl", "campaign-a") as journal:
            self.append_instance(journal, old, 1000, terminated=True)
            self.append_instance(journal, current, 1010, terminated=False)
            value = request(); value["journal"] = {"object_key": "campaign-a/controller-journals/original.jsonl",
                **ci.pin(journal.path.read_bytes()), "rows": len(journal.rows), "last_sha256": journal.last}
            cloud, client, publisher = self.ports(response)
            ci.verify_campaign_history(cloud, client, base_plan(), publisher, value, journal)
            replayed = budget.CampaignBudget.replay("campaign-a", journal.rows)
            self.assertEqual({item.launch_token for item in replayed.instances}, {old, current})
            self.assertEqual(len(replayed.active_instances), 1)
            before = journal.path.read_bytes()
            for tokens in ((current,), (old,), (old, current, "launch-unrecorded-0003")):
                with self.subTest(tokens=tokens):
                    client.call.return_value = {"Items": [{"record_id": {"S": "launch#" + token}} for token in tokens]}
                    with self.assertRaisesRegex(ValueError, "omits remote launch history"):
                        ci.verify_campaign_history(cloud, client, base_plan(), publisher, value, journal)
                    self.assertEqual(journal.path.read_bytes(), before)

    def test_newer_remote_handoff_rejects_stale_journal_with_identical_tokens(self):
        token = "launch-token-0001"
        response = {"Items": [{"record_id": {"S": "launch#" + token}}]}
        with tempfile.TemporaryDirectory(prefix="rove-ci-stale-handoff-") as directory:
            root = Path(directory)
            with ledger.Journal(root / "original.jsonl", "campaign-a") as original:
                self.append_instance(original, token, 1000, terminated=False)
                stale = original.path.read_bytes()
                original.append("campaign.ssm_requested", {"instance_id": "i-" + token, "host_job_id": "offline-host"}, time_utc=iso(1003))
                remote = original.path.read_bytes()
            (root / "stale.jsonl").write_bytes(stale)
            with ledger.Journal(root / "stale.jsonl", "campaign-a") as journal:
                value = request(); value["journal"] = self.journal_descriptor(journal)
                key = self.snapshot(remote)
                cloud, client, publisher = self.ports(response, [key], {key: remote})
                self.assertEqual({item.launch_token for item in budget.CampaignBudget.replay("campaign-a", journal.rows).instances}, {token})
                with self.assertRaisesRegex(ValueError, "newer or conflicting"):
                    ci.verify_campaign_history(cloud, client, base_plan(), publisher, value, journal)
                publisher.read_verified.assert_called_once_with(key, expected_sha=ci.pin(remote)["sha256"], max_bytes=32 << 20)
                self.assertEqual(journal.path.read_bytes(), stale)
                self.assertEqual((root / "remote-controller-history" / (ci.pin(remote)["sha256"] + ".jsonl")).read_bytes(), remote)

    def test_every_remote_snapshot_must_be_a_prefix_not_a_conflicting_fork(self):
        token = "launch-token-0001"
        response = {"Items": [{"record_id": {"S": "launch#" + token}}]}
        with tempfile.TemporaryDirectory(prefix="rove-ci-history-fork-") as directory:
            root = Path(directory)
            with ledger.Journal(root / "full.jsonl", "campaign-a") as journal:
                self.append_instance(journal, token, 1000, terminated=False)
                prefix = journal.path.read_bytes()
                (root / "fork.jsonl").write_bytes(prefix)
                journal.append("campaign.ssm_requested", {"host_job_id": "original-host"}, time_utc=iso(1003))
                with ledger.Journal(root / "fork.jsonl", "campaign-a") as fork:
                    fork.append("campaign.ssm_requested", {"host_job_id": "different-host"}, time_utc=iso(1003))
                    conflict = fork.path.read_bytes()
                value = request(); value["journal"] = self.journal_descriptor(journal)
                old_key, conflict_key = self.snapshot(prefix), self.snapshot(conflict)
                cloud, client, publisher = self.ports(response, [old_key], {old_key: prefix})
                ci.verify_campaign_history(cloud, client, base_plan(), publisher, value, journal)
                self.assertEqual(publisher.read_verified.call_count, 1)
                cloud, client, publisher = self.ports(response, [old_key, conflict_key], {old_key: prefix, conflict_key: conflict})
                before = journal.path.read_bytes()
                with self.assertRaisesRegex(ValueError, "newer or conflicting"):
                    ci.verify_campaign_history(cloud, client, base_plan(), publisher, value, journal)
                self.assertEqual([row.args[0] for row in publisher.read_verified.call_args_list], [old_key, conflict_key])
                self.assertEqual(journal.path.read_bytes(), before)

    def test_unrecognized_remote_history_name_is_not_downloaded(self):
        token = "launch-token-0001"
        with tempfile.TemporaryDirectory(prefix="rove-ci-history-name-") as directory, \
             ledger.Journal(Path(directory) / "full.jsonl", "campaign-a") as journal:
            self.append_instance(journal, token, 1000, terminated=False)
            value = request(); value["journal"] = self.journal_descriptor(journal)
            cloud, client, publisher = self.ports({"Items": [{"record_id": {"S": "launch#" + token}}]},
                                                ["campaign-a/controller-journals/latest.jsonl"])
            with self.assertRaisesRegex(ValueError, "unrecognized remote"):
                ci.verify_campaign_history(cloud, client, base_plan(), publisher, value, journal)
            publisher.read_verified.assert_not_called()

    def test_inactive_local_budget_requires_real_remote_closed_record(self):
        token = "launch-token-0001"
        plan = replace(base_plan(), launch_token=token)
        intent = plan.intent(1000)
        with tempfile.TemporaryDirectory(prefix="rove-ci-inactive-proof-") as directory, \
             ledger.Journal(Path(directory) / "inactive.jsonl", plan.campaign_id) as journal:
            self.append_instance(journal, token, 1000, terminated=True)
            self.assertEqual(budget.CampaignBudget.replay(plan.campaign_id, journal.rows).active_instances, ())
            def service(name, operation, query):
                self.assertEqual((name, operation), ("dynamodb", "get-item"))
                if query["Key"]["record_id"]["S"] == "launch#" + token:
                    return {"Item": {"payload": {"S": ci.canonical(intent).decode()}}}
                return {}
            client = SimpleNamespace(call=Mock(side_effect=service))
            cloud = SimpleNamespace(budget=budget, ledger=ledger, aws=aws)
            with self.assertRaisesRegex(ValueError, "durable remote ownership closure"):
                ci.verify_inactive_ownership(cloud, client, plan, journal)
            self.assertEqual(client.call.call_count, 2)

    def test_remote_closed_record_must_bind_all_original_intent_fields(self):
        token = "launch-token-0001"
        plan = replace(base_plan(), launch_token=token)
        intent = plan.intent(1000)
        closed = {**intent, "terminal_state": "terminated", "instance_id": "i-" + token}
        with tempfile.TemporaryDirectory(prefix="rove-ci-closed-proof-") as directory, \
             ledger.Journal(Path(directory) / "inactive.jsonl", plan.campaign_id) as journal:
            self.append_instance(journal, token, 1000, terminated=True)
            cloud = SimpleNamespace(budget=budget, ledger=ledger, aws=aws)
            def service(name, operation, query):
                record = intent if query["Key"]["record_id"]["S"] == "launch#" + token else returned_closed
                return {"Item": {"payload": {"S": ci.canonical(record).decode()}}}
            client = SimpleNamespace(call=Mock(side_effect=service))
            returned_closed = closed
            ci.verify_inactive_ownership(cloud, client, plan, journal)
            for changes in ({"terminal_state": "running"}, {"instance_id": "i-another"}, {"request_sha256": "f" * 64}):
                with self.subTest(changes=changes):
                    returned_closed = {**closed, **changes}
                    with self.assertRaisesRegex(ValueError, "durable remote ownership closure"):
                        ci.verify_inactive_ownership(cloud, client, plan, journal)


class ProcessOwnershipTests(unittest.TestCase):
    OWNER = {"pid": 101, "pgid": 101, "session": 101, "start_ticks": 123, "state": "S"}

    def test_reused_or_absent_leader_is_never_signalled_or_enumerated(self):
        for observed in (None, {**self.OWNER, "start_ticks": 999}, {**self.OWNER, "session": 999}, {**self.OWNER, "pgid": 999}):
            with self.subTest(observed=observed), patch.object(ci, "process_identity", return_value=observed), \
                 patch.object(Path, "iterdir", side_effect=AssertionError("ownership must be checked before scanning")), \
                 patch.object(ci.os, "killpg") as kill:
                with self.assertRaisesRegex(ValueError, "original controller"):
                    ci.signal_controller(dict(self.OWNER), signal.SIGINT)
                kill.assert_not_called()

    def test_escaped_child_group_blocks_signal_to_original_group(self):
        processes = {101: dict(self.OWNER), 102: {"pid": 102, "pgid": 999, "session": 101, "start_ticks": 200, "state": "S"}}
        with patch.object(ci, "process_identity", side_effect=lambda pid: processes[pid]), \
             patch.object(Path, "iterdir", return_value=[Path("/proc/101"), Path("/proc/102")]), \
             patch.object(ci.os, "killpg") as kill:
            with self.assertRaisesRegex(ValueError, "escaped"):
                ci.signal_controller(dict(self.OWNER), signal.SIGTERM)
            kill.assert_not_called()

    def test_only_live_children_in_exact_original_session_are_counted(self):
        processes = {101: dict(self.OWNER),
            102: {"pid": 102, "pgid": 101, "session": 101, "start_ticks": 200, "state": "S"},
            103: {"pid": 103, "pgid": 101, "session": 101, "start_ticks": 201, "state": "Z"},
            104: {"pid": 104, "pgid": 101, "session": 999, "start_ticks": 202, "state": "S"}}
        with patch.object(ci, "process_identity", side_effect=lambda pid: processes[pid]), \
             patch.object(Path, "iterdir", return_value=[Path("/proc/" + str(pid)) for pid in processes]), \
             patch.object(ci.os, "killpg") as kill:
            self.assertEqual(ci.process_members(dict(self.OWNER)), [processes[102]])
            ci.signal_controller(dict(self.OWNER), signal.SIGINT)
            kill.assert_called_once_with(101, signal.SIGINT)


class OriginalGitRunnerTests(unittest.TestCase):
    def test_git_uses_only_reviewed_environment_config_and_literal_pathspecs(self):
        poison = {"GIT_INDEX_FILE": "/not-the-index", "GIT_DIR": "/not-the-repository",
            "GIT_WORK_TREE": "/not-the-worktree", "GIT_CONFIG_COUNT": "invalid",
            "GIT_CONFIG_KEY_0": "core.worktree", "GIT_CONFIG_VALUE_0": "/not-the-worktree",
            "Git_Alternate_Object_Directories": "/not-the-objects", "GIT_NO_REPLACE_OBJECTS": "0"}
        result = SimpleNamespace(returncode=0, stdout=b"original", stderr=b"")
        with patch.dict(os.environ, {**poison, "ROVE_UNIT_KEEP": "kept"}), \
             patch.object(ci.subprocess, "run", return_value=result) as run:
            self.assertEqual(ci.git(Path("/ordinary/origin"), "cat-file", "blob", "a" * 40,
                                   limit=32 << 20, input_bytes=b"unit input"), b"original")
        args, kwargs = run.call_args
        self.assertEqual(args[0], ["git", "-c", "core.fsmonitor=false", "-c", "core.untrackedCache=false",
            "-c", "core.hooksPath=" + os.devnull, "-c", "protocol.allow=never", "--literal-pathspecs",
            "-C", str(Path("/ordinary/origin")), "cat-file", "blob", "a" * 40])
        expected = {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0", "GIT_NO_REPLACE_OBJECTS": "1", "GIT_NO_LAZY_FETCH": "1", "GIT_ALLOW_PROTOCOL": ""}
        self.assertEqual({key: value for key, value in kwargs["env"].items() if key.upper().startswith("GIT_")}, expected)
        self.assertEqual(kwargs["env"]["ROVE_UNIT_KEEP"], "kept")
        self.assertEqual(kwargs["input"], b"unit input")
        self.assertEqual(kwargs["timeout"], 30)
        self.assertTrue(kwargs["capture_output"])
        self.assertEqual(kwargs["creationflags"], subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)

    def test_git_read_bound_is_explicit_and_failure_does_not_return_bytes(self):
        with patch.object(ci.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout=b"abcd", stderr=b"")):
            self.assertEqual(ci.git(Path("/ordinary/origin"), "show", limit=4), b"abcd")
            with self.assertRaisesRegex(ValueError, "exceeded its bound"):
                ci.git(Path("/ordinary/origin"), "show", limit=3)
        with patch.object(ci.subprocess, "run", return_value=SimpleNamespace(returncode=7, stdout=b"", stderr=b"untrusted")):
            with self.assertRaisesRegex(ValueError, "observation failed"):
                ci.git(Path("/ordinary/origin"), "show")
        for limit in (False, 0, -1, 1.5, (32 << 20) + 1):
            with self.subTest(limit=limit), patch.object(ci.subprocess, "run") as run:
                with self.assertRaisesRegex(ValueError, "invalid original source Git read bound"):
                    ci.git(Path("/ordinary/origin"), "show", limit=limit)
                run.assert_not_called()


class FrozenSourceTests(unittest.TestCase):
    def git(self, root, *arguments, input_bytes=None):
        # Fixture setup is isolated from ambient Git redirects. Deliberately do
        # not disable replacement refs: the attack test must show raw Git's
        # replacement before the production source binder rejects it.
        environment = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
        environment.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        result = subprocess.run(["git", "-C", str(root), "-c", "user.name=Offline source fixture",
            "-c", "user.email=fixture@example.invalid", "-c", "core.hooksPath=" + os.devnull,
            *arguments], capture_output=True, input=input_bytes, timeout=30, env=environment)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        return result.stdout

    def make_seed(self, root):
        repository = Path(__file__).resolve().parents[3]
        cloud_path = repository / "engines/experiments/strength/cloud_runtime.py"
        cloud_ast = ast.parse(cloud_path.read_bytes())
        assignment = next(node for node in cloud_ast.body if isinstance(node, ast.Assign)
                          and any(isinstance(target, ast.Name) and target.id == "HOST_SOURCE_FILES" for target in node.targets))
        names = eval(compile(ast.Expression(assignment.value), "<tracked HOST_SOURCE_FILES fixture>", "eval"), {"__builtins__": {"tuple": tuple}})
        files = {}
        for name in (*names, "engines/scripts/production.py"):
            files["source/" + name] = (repository / name).read_bytes().replace(b"\r\n", b"\n")
        origin = root.parent / "original-git"
        origin.mkdir()
        self.git(origin, "init", "--quiet")
        for name, body in files.items():
            path = origin / name[len("source/"):]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
        self.git(origin, "add", "--", *[name[len("source/"):] for name in files])
        self.git(origin, "commit", "--quiet", "--no-gpg-sign", "-m", "Offline exact-source binding fixture")
        source_origin = {**request()["source_origin"], "head_sha": self.git(origin, "rev-parse", "HEAD").decode().strip()}
        files.update({"peer/ice4/source.txt": b"schema-only peer fixture; not a qualified engine\n",
                      "bank/bank.json": b"{}\n", "bank/broad.pgn": b"schema-only\n", "bank/high.pgn": b"schema-only\n",
                      "runner/fastchess.bundle": b"schema-only transport fixture; never built or executed\n"})
        manifest = {"format": "rove4k-cloud-seed-v1", "source_origin": source_origin, "source_tree": "source",
            "rove": [], "peers": [{"family": "ice4", "profile": "test-p4", "source": "peer/ice4"}],
            "bank": "bank/bank.json", "bank_pgns": {"broad": "bank/broad.pgn", "high": "bank/high.pgn"},
            "runner": {"revision": "ebfd64cb7fac80d4822c50b07dca4fe934779d21", "checkout": "external/fastchess",
                       "transport": "external-git-bundle", "bundle": "runner/fastchess.bundle"},
            "members": {name: {**ci.pin(body), "mode": 0o600} for name, body in sorted(files.items())}}
        raw = ci.canonical(manifest) + b"\n"
        for name, body in {**files, "seed.json": raw}.items():
            target = root / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(body); target.chmod(0o600)
        return ci.pin(raw)["sha256"], origin, source_origin

    def child(self, root, manifest_sha, origin, source_origin, expected_error=None, git_environment=None):
        script = """import importlib.util,json,pathlib,sys,urllib.request
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('ci_transport_only',sys.argv[1]); ci=importlib.util.module_from_spec(spec); spec.loader.exec_module(ci)
root=pathlib.Path(sys.argv[2]); expected=(root/'source').resolve()
original_run=ci.subprocess.run
def local_git_only(argv,*args,**kwargs):
 assert argv[0]=='git',argv[0]
 return original_run(argv,*args,**kwargs)
with patch.object(urllib.request,'urlopen',side_effect=AssertionError('no network during frozen import')), patch.object(ci.subprocess,'run',side_effect=local_git_only):
 if sys.argv[6]:
  try: ci.load_frozen(root,sys.argv[3],origin=pathlib.Path(sys.argv[4]),expected_source_origin=json.loads(sys.argv[5]))
  except ValueError as error:
   assert sys.argv[6] in str(error),str(error)
   assert 'rove4k_cloud_runtime' not in sys.modules
  else: raise AssertionError('mutated source was imported')
 else:
  cloud,manifest=ci.load_frozen(root,sys.argv[3],origin=pathlib.Path(sys.argv[4]),expected_source_origin=json.loads(sys.argv[5]))
  assert cloud.ROOT.resolve()==expected
  modules=(cloud,cloud.aws,cloud.budget,cloud.registry,cloud.run,cloud.registry.production)
  assert all(pathlib.Path(module.__file__).resolve().is_relative_to(expected) for module in modules)
  assert cloud.canonical_provider() is cloud
  assert 'qualified' not in manifest
print('frozen-import-rejected' if sys.argv[6] else 'frozen-import-bound')
"""
        return subprocess.run([sys.executable, "-I", "-B", "-c", script, str(Path(ci.__file__).resolve()),
            str(root), manifest_sha, str(origin), ci.canonical(source_origin).decode(), expected_error or ""],
            capture_output=True, timeout=30, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1",
                "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", **(git_environment or {})})

    def rewrite_manifest(self, root, edit):
        path = root / "seed.json"
        manifest = ci.document(path.read_bytes())
        edit(manifest)
        raw = ci.canonical(manifest) + b"\n"
        path.write_bytes(raw)
        return ci.pin(raw)["sha256"]

    def make_materializer_origin(self, root, declaration_edit=None, omit=()):
        repository = Path(__file__).resolve().parents[3]
        seed_name = "engines/experiments/strength/seed.py"
        seed = (repository / seed_name).read_bytes().replace(b"\r\n", b"\n")
        assignments = {node.targets[0].id: node.value for node in ast.parse(seed).body
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)}
        modules = ast.literal_eval(assignments["HOST_MODULES"])
        core = ast.literal_eval(assignments["CORE_R"])
        league_modules = ast.literal_eval(assignments["LEAGUE_HOST_MODULES"])
        league_core = ast.literal_eval(assignments["LEAGUE_CORE_R"])
        self.assertIsInstance(modules, tuple)
        self.assertIsInstance(core, tuple)
        names = ({"engines/experiments/strength/" + name + ".py" for name in (*modules, *league_modules)}
                 | set(core) | set(league_core))
        names.difference_update(omit)
        root.mkdir()
        self.git(root, "init", "--quiet")
        for name in sorted(names):
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            body = (repository / name).read_bytes().replace(b"\r\n", b"\n")
            if name == seed_name and declaration_edit is not None:
                body = declaration_edit(body)
            path.write_bytes(body)
            path.chmod(0o644)
        self.git(root, "add", "--", *sorted(names))
        self.git(root, "commit", "--quiet", "--no-gpg-sign", "-m", "Offline materializer source closure fixture")
        return self.git(root, "rev-parse", "HEAD").decode().strip()

    def rejected_materializer_request(self, root, origin, head, message):
        value = request()
        value["source_origin"]["head_sha"] = head
        context = ci.bind_context(*context_inputs(), NOW)
        original_run = subprocess.run
        materializer_calls = []
        def local_git_only(argv, *arguments, **kwargs):
            if argv[0] != "git":
                materializer_calls.append(argv)
                raise AssertionError("unbound materializer subprocess must not start")
            return original_run(argv, *arguments, **kwargs)
        args = SimpleNamespace(stage=root / "stage.json", origin=origin, mode="execute")
        with patch.object(ci, "load_stage", return_value=({"root": str(root)}, value, context)), \
             patch.object(ci.time, "time", return_value=NOW), \
             patch.object(ci, "fetch_version", side_effect=AssertionError("unbound source must not download seed")) as fetch, \
             patch.object(ci, "run_owned", side_effect=AssertionError("unbound source must not start controller")) as owned, \
             patch.object(ci.subprocess, "run", side_effect=local_git_only):
            with self.assertRaisesRegex(ValueError, message):
                ci.run_request(args)
        fetch.assert_not_called()
        owned.assert_not_called()
        self.assertEqual(materializer_calls, [])

    def test_hidden_modified_materializer_or_imported_sibling_is_rejected_before_download(self):
        for relative in ("engines/experiments/strength/cloud_runtime.py", "engines/experiments/strength/aws.py",
                         "engines/experiments/strength/memory_observation.py",
                         "engines/experiments/strength/functional_uci_probe.py",
                         "engines/experiments/strength/functional_probe_session.py",
                         "engines/scripts/league_resource_profiles.py",
                         "engines/experiments/tcec-scope/verify.py",
                         "engines/compact/tiny-entry-d/verify.py", "engines/tests/chess_oracle.py"):
            for hidden in ("--assume-unchanged", "--skip-worktree"):
                with self.subTest(relative=relative, hidden=hidden), tempfile.TemporaryDirectory(prefix="rove-ci-materializer-hidden-") as directory:
                    root = Path(directory)
                    origin = root / "original-git"
                    head = self.make_materializer_origin(origin)
                    # Prove that the complete unmodified fixture passes the
                    # actual metadata/blob binder before injecting the fault.
                    ci.bind_materializer_source(origin, head)
                    path = origin / relative
                    path.write_bytes(path.read_bytes() + b"\n# hidden offline materializer mutation\n")
                    self.git(origin, "update-index", hidden, "--", relative)
                    self.assertEqual(self.git(origin, "status", "--porcelain=v1", "--untracked-files=normal"), b"")
                    self.rejected_materializer_request(root, origin, head, "materializer.*committed Git blob")

    def test_materializer_closure_metadata_must_remain_static_and_complete(self):
        edits = {
            "missing": lambda body: body.replace(b"HOST_MODULES =", b"OMITTED_HOST_MODULES =", 1),
            "dynamic": lambda body: body.replace(b"HOST_MODULES = (", b"HOST_MODULES = tuple((", 1).replace(
                b'"fastchess", "seed")', b'"fastchess", "seed"))', 1),
            "unsafe": lambda body: body.replace(b'"cloud_runtime", "campaign"', b'"../cloud_runtime", "campaign"', 1),
            "incomplete": lambda body: body.replace(b'"cloud_runtime", "campaign", "aws",', b'"cloud_runtime", "campaign",', 1),
            "league-one-missing": lambda body: body.replace(b"LEAGUE_HOST_MODULES =", b"OMITTED_LEAGUE_HOST_MODULES =", 1),
            "league-both-missing": lambda body: body.replace(b"LEAGUE_HOST_MODULES =", b"OMITTED_LEAGUE_HOST_MODULES =", 1).replace(
                b"LEAGUE_CORE_R =", b"OMITTED_LEAGUE_CORE_R =", 1),
            "league-mismatched": lambda body: body.replace(b'LEAGUE_HOST_MODULES = ("memory_observation",',
                b'LEAGUE_HOST_MODULES = ("wrong_module",', 1),
        }
        for case, edit in edits.items():
            with self.subTest(case=case), tempfile.TemporaryDirectory(prefix="rove-ci-materializer-metadata-") as directory:
                root = Path(directory)
                origin = root / "original-git"
                head = self.make_materializer_origin(origin, declaration_edit=edit)
                self.rejected_materializer_request(root, origin, head, "malformed node" if case == "dynamic" else "materializer")

    def test_legacy_materializer_without_league_code_keeps_original_closure(self):
        with tempfile.TemporaryDirectory(prefix="rove-ci-legacy-materializer-") as directory:
            root = Path(directory)
            origin = root / "original-git"
            self.make_materializer_origin(origin)
            seed_path = origin / "engines/experiments/strength/seed.py"
            body = seed_path.read_bytes().replace(b"LEAGUE_HOST_MODULES =", b"OLD_LEAGUE_HOST_MODULES =", 1).replace(
                b"LEAGUE_CORE_R =", b"OLD_LEAGUE_CORE_R =", 1)
            seed_path.write_bytes(body)
            # This isolated Git fixture models the old pre-league revision;
            # none of these synthetic files is imported or executed.
            (origin / "engines/experiments/strength/run.py").write_bytes(b"# legacy controller fixture\n")
            (origin / "engines/experiments/tcec-next/profile_verify.py").write_bytes(b"# legacy verifier fixture\n")
            self.git(origin, "add", "--", "engines/experiments/strength/seed.py",
                     "engines/experiments/strength/run.py", "engines/experiments/tcec-next/profile_verify.py")
            self.git(origin, "commit", "--quiet", "--no-gpg-sign", "-m", "Legacy closure fixture")
            head = self.git(origin, "rev-parse", "HEAD").decode().strip()
            result = ci.bind_materializer_source(origin, head)
            self.assertEqual(result["source_commit"], head)

    def test_prior_league_module_declarations_remain_bindable(self):
        old_declarations = (("memory_observation",),
            ("memory_observation", "overhead", "league_probe", "diagnostic_candidates", "peak_capacity",
             "peak_probe_session", "peak_ready_probe", "peak_receipt", "peak_supervisor"),
            ("memory_observation", "overhead", "league_probe", "diagnostic_candidates", "peak_capacity",
             "peak_probe_session", "peak_ready_probe", "peak_receipt", "peak_supervisor",
             "rove_runtime_observation", "rove_worker_observer", "rove_vma_observer"))
        for old_modules in old_declarations:
            with self.subTest(old_modules=old_modules), tempfile.TemporaryDirectory(prefix="rove-ci-prior-league-materializer-") as directory:
                origin = Path(directory) / "original-git"
                self.make_materializer_origin(origin)
                path = origin / "engines/experiments/strength/seed.py"
                raw = path.read_text(encoding="utf-8")
                node = next(node for node in ast.parse(raw).body if isinstance(node, ast.Assign)
                            and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                            and node.targets[0].id == "LEAGUE_HOST_MODULES")
                lines = raw.splitlines(keepends=True)
                lines[node.lineno - 1:node.end_lineno] = ["LEAGUE_HOST_MODULES = " + repr(old_modules) + "\n"]
                raw = "".join(lines)
                node = next(node for node in ast.parse(raw).body if isinstance(node, ast.Assign)
                            and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                            and node.targets[0].id == "LEAGUE_CORE_R")
                lines = raw.splitlines(keepends=True)
                lines[node.lineno - 1:node.end_lineno] = ['LEAGUE_CORE_R = ("engines/scripts/league_resource_profiles.py",)\n']
                path.write_text("".join(lines), encoding="utf-8")
                # Model the historical cloud declaration too: an actual new
                # cloud source that declares the functional CLI must not be
                # bound to an old seed inventory.
                cloud_path = origin / "engines/experiments/strength/cloud_runtime.py"
                cloud = cloud_path.read_text(encoding="utf-8")
                cloud_node = next(node for node in ast.parse(cloud).body if isinstance(node, ast.Assign)
                                  and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                                  and node.targets[0].id == "LEAGUE_HOST_SOURCE_FILES")
                old_cloud = tuple("engines/experiments/strength/" + name + ".py" for name in old_modules)
                old_cloud += ("engines/scripts/league_resource_profiles.py",)
                cloud_lines = cloud.splitlines(keepends=True)
                cloud_lines[cloud_node.lineno - 1:cloud_node.end_lineno] = ["LEAGUE_HOST_SOURCE_FILES = " + repr(old_cloud) + "\n"]
                cloud_path.write_text("".join(cloud_lines), encoding="utf-8")
                self.git(origin, "add", "--", "engines/experiments/strength/seed.py",
                         "engines/experiments/strength/cloud_runtime.py")
                self.git(origin, "commit", "--quiet", "--no-gpg-sign", "-m", "prior league closure")
                head = self.git(origin, "rev-parse", "HEAD").decode().strip()
                result = ci.bind_materializer_source(origin, head, out=Path(directory) / "materializer")
                self.assertEqual(result["source_commit"], head)
                self.assertNotIn("engines/experiments/strength/functional_uci_probe.py", result["members"])
                self.assertNotIn("engines/experiments/strength/functional_probe_session.py", result["members"])
                self.assertEqual("engines/experiments/strength/rove_vma_observer.py" in result["members"],
                                 "rove_vma_observer" in old_modules)

    def test_missing_league_blob_is_rejected_before_materializer_import(self):
        for name in ("engines/experiments/strength/memory_observation.py",
                     "engines/experiments/strength/overhead.py",
                     "engines/experiments/strength/league_probe.py",
                     "engines/experiments/strength/diagnostic_candidates.py",
                     "engines/experiments/strength/peak_capacity.py",
                     "engines/experiments/strength/peak_probe_session.py",
                     "engines/experiments/strength/peak_ready_probe.py",
                     "engines/experiments/strength/peak_receipt.py",
                     "engines/experiments/strength/peak_supervisor.py",
                     "engines/experiments/strength/rove_runtime_observation.py",
                     "engines/experiments/strength/rove_worker_observer.py",
                     "engines/experiments/strength/rove_vma_observer.py",
                     "engines/experiments/strength/functional_uci_probe.py",
                     "engines/experiments/strength/functional_probe_session.py",
                     "engines/scripts/league_resource_profiles.py",
                     "engines/experiments/tcec-scope/verify.py",
                     "engines/compact/tiny-entry-d/verify.py",
                     "engines/tests/chess_oracle.py"):
            with self.subTest(name=name), tempfile.TemporaryDirectory(prefix="rove-ci-league-missing-") as directory:
                root = Path(directory)
                origin = root / "original-git"
                head = self.make_materializer_origin(origin, omit=(name,))
                self.rejected_materializer_request(root, origin, head, "materializer source closure is missing")

    def test_current_functional_cloud_rejects_downgraded_seed_inventory(self):
        with tempfile.TemporaryDirectory(prefix="rove-ci-functional-downgrade-") as directory:
            root = Path(directory)
            origin = root / "original-git"
            self.make_materializer_origin(origin)
            path = origin / "engines/experiments/strength/seed.py"
            raw = path.read_text(encoding="utf-8")
            tree = ast.parse(raw)
            declarations = {node.targets[0].id: node for node in tree.body
                            if isinstance(node, ast.Assign) and len(node.targets) == 1
                            and isinstance(node.targets[0], ast.Name)}
            modules = ast.literal_eval(declarations["LEAGUE_HOST_MODULES"].value)
            core = ast.literal_eval(declarations["LEAGUE_CORE_R"].value)
            self.assertEqual(modules[-2:], ("functional_uci_probe", "functional_probe_session"))
            self.assertEqual(len(core), 4)
            lines = raw.splitlines(keepends=True)
            for name, value in sorted((("LEAGUE_HOST_MODULES", modules[:-2]),
                                       ("LEAGUE_CORE_R", core[:1])),
                                      key=lambda item: declarations[item[0]].lineno, reverse=True):
                node = declarations[name]
                lines[node.lineno - 1:node.end_lineno] = [name + " = " + repr(value) + "\n"]
            path.write_text("".join(lines), encoding="utf-8")
            self.git(origin, "add", "--", "engines/experiments/strength/seed.py")
            self.git(origin, "commit", "--quiet", "--no-gpg-sign", "-m", "downgraded seed inventory")
            head = self.git(origin, "rev-parse", "HEAD").decode().strip()
            with self.assertRaisesRegex(ValueError, "functional diagnostic source closure is incomplete"):
                ci.bind_materializer_source(origin, head)

    def test_functional_cli_runs_isolated_from_bound_materializer(self):
        with tempfile.TemporaryDirectory(prefix="rove-ci-functional-cli-") as directory:
            root = Path(directory)
            origin = root / "original-git"
            head = self.make_materializer_origin(origin)
            out = root / "materializer"
            proof = ci.bind_materializer_source(origin, head, out=out)
            entry = "engines/experiments/strength/functional_uci_probe.py"
            self.assertIn(entry, proof["members"])
            for name in ("engines/experiments/tcec-scope/verify.py",
                         "engines/compact/tiny-entry-d/verify.py", "engines/tests/chess_oracle.py"):
                self.assertIn(name, proof["members"])
            result = subprocess.run([sys.executable, "-I", "-B", str(out / entry), "--help"],
                                    capture_output=True, timeout=30,
                                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
            self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
            self.assertIn(b"--candidates-sha256", result.stdout)
            self.assertIn(b"--placement-sha256", result.stdout)
            session = "engines/experiments/strength/functional_probe_session.py"
            self.assertIn(session, proof["members"])
            result = subprocess.run([sys.executable, "-I", "-B", str(out / session), "--help"],
                                    capture_output=True, timeout=30,
                                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
            self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
            self.assertIn(b"--candidates-sha256", result.stdout)
            self.assertIn(b"--root", result.stdout)

    def test_dotted_league_import_requires_static_closure_even_without_verifier_marker(self):
        def omit_league(body):
            return body.replace(b"LEAGUE_HOST_MODULES =", b"OMITTED_LEAGUE_HOST_MODULES =", 1).replace(
                b"LEAGUE_CORE_R =", b"OMITTED_LEAGUE_CORE_R =", 1)
        for import_line in (b"from .memory_observation import observe_capacity\n",
                            b"import rove4k_cloud_strength.memory_observation\n"):
            with self.subTest(import_line=import_line), tempfile.TemporaryDirectory(prefix="rove-ci-league-import-") as directory:
                root = Path(directory)
                origin = root / "original-git"
                self.make_materializer_origin(origin, declaration_edit=omit_league)
                (origin / "engines/experiments/strength/run.py").write_bytes(import_line)
                (origin / "engines/experiments/tcec-next/profile_verify.py").write_bytes(b"# no league marker\n")
                self.git(origin, "add", "--", "engines/experiments/strength/run.py",
                         "engines/experiments/tcec-next/profile_verify.py")
                self.git(origin, "commit", "--quiet", "--no-gpg-sign", "-m", "Alternate import fixture")
                head = self.git(origin, "rev-parse", "HEAD").decode().strip()
                self.rejected_materializer_request(root, origin, head, "league materializer source closure is incomplete")

    def test_ignored_package_and_valid_bytecode_shadows_do_not_enter_fresh_materializer(self):
        for shadow in ("package", "bytecode"):
            with self.subTest(shadow=shadow), tempfile.TemporaryDirectory(prefix="rove-ci-materializer-shadow-") as directory:
                root = Path(directory)
                origin = root / "original-git"
                head = self.make_materializer_origin(origin)
                sibling = origin / "engines/experiments/strength"
                sentinel = "offline ignored " + shadow + " shadow"
                poison = ("raise RuntimeError(" + repr(sentinel) + ")\n").encode()
                (origin / ".git/info/exclude").write_text("__pycache__/\naws/\n")
                if shadow == "package":
                    package = sibling / "aws"
                    package.mkdir()
                    (package / "__init__.py").write_bytes(poison)
                else:
                    source = sibling / "aws.py"
                    metadata = source.stat()
                    self.assertLess(len(poison), metadata.st_size)
                    temporary_source = root / "offline_poison.py"
                    temporary_source.write_bytes(poison + b" " * (metadata.st_size - len(poison)))
                    os.utime(temporary_source, ns=(metadata.st_atime_ns, metadata.st_mtime_ns))
                    cache = Path(importlib.util.cache_from_source(str(source)))
                    cache.parent.mkdir()
                    py_compile.compile(str(temporary_source), cfile=str(cache), dfile=str(source), doraise=True,
                                       invalidation_mode=py_compile.PycInvalidationMode.TIMESTAMP)
                self.assertEqual(self.git(origin, "status", "--porcelain=v1", "--untracked-files=normal"), b"")
                cloud_relative = Path("engines/experiments/strength/cloud_runtime.py")
                poisoned = subprocess.run([sys.executable, "-I", "-B", str(origin / cloud_relative), "--help"],
                    capture_output=True, timeout=30, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
                self.assertNotEqual(poisoned.returncode, 0)
                self.assertIn(sentinel.encode(), poisoned.stderr)
                out = root / "materializer"
                proof = ci.bind_materializer_source(origin, head, out=out)
                self.assertEqual(Path(proof["root"]), out)
                expected = {name.decode() for name in self.git(origin, "ls-files", "-z").split(b"\0") if name}
                actual = {path.relative_to(out).as_posix() for path in out.rglob("*") if path.is_file()}
                self.assertEqual(actual, expected)
                for name in expected:
                    self.assertEqual((out / name).read_bytes(), (origin / name).read_bytes())
                    self.assertEqual(proof["members"][name], {**ci.pin((out / name).read_bytes()), "mode": 0o600})
                    self.assertEqual((out / name).stat().st_mode & 0o777, 0o600)
                self.assertEqual(proof["source_commit"], head)
                self.assertEqual(proof["materializer_path"], str(out / cloud_relative))
                clean = subprocess.run([sys.executable, "-I", "-B", str(out / cloud_relative), "--help"],
                    capture_output=True, timeout=30, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
                self.assertEqual(clean.returncode, 0, clean.stderr.decode())
                self.assertIn(b"materialize", clean.stdout)
                self.assertNotIn(sentinel.encode(), clean.stdout + clean.stderr)
                self.assertFalse(any(path.name == "__pycache__" or path.name == "aws" for path in out.rglob("*")))

    def test_run_request_executes_only_the_fresh_verified_materializer_path(self):
        with tempfile.TemporaryDirectory(prefix="rove-ci-materializer-command-") as directory:
            root = Path(directory)
            origin = root / "original-git"
            head = self.make_materializer_origin(origin)
            stage_root = root / "stage"
            (stage_root / "reports").mkdir(parents=True)
            value = request()
            value["source_origin"]["head_sha"] = head
            context = ci.bind_context(*context_inputs(), NOW)
            args = SimpleNamespace(stage=stage_root / "stage.json", origin=origin, mode="execute")
            original_run = subprocess.run
            materializer_calls = []
            def inspect_report_before_download(*arguments):
                report = ci.document((stage_root / "reports/materializer-source.json").read_bytes())
                self.assertEqual(report["source_commit"], head)
                self.assertEqual(report["source_origin"], value["source_origin"])
                self.assertEqual(Path(report["root"]), stage_root / "materializer")
                self.assertEqual(Path(report["materializer_path"]), stage_root / "materializer/engines/experiments/strength/cloud_runtime.py")
                self.assertEqual(report["source_files"], len(report["members"]))
                for name, expected in report["members"].items():
                    self.assertEqual(expected, {**ci.pin((Path(report["root"]) / name).read_bytes()), "mode": 0o600})
            def local_materializer_transport(argv, *arguments, **kwargs):
                if argv[0] == "git":
                    return original_run(argv, *arguments, **kwargs)
                materializer_calls.append((argv, kwargs))
                return SimpleNamespace(returncode=0)
            with patch.object(ci, "load_stage", return_value=({"root": str(stage_root)}, value, context)), \
                 patch.object(ci.time, "time", return_value=NOW), patch.object(ci, "fetch_version", side_effect=inspect_report_before_download) as fetch, \
                 patch.object(ci, "run_owned") as owned, \
                 patch.object(ci.subprocess, "run", side_effect=local_materializer_transport):
                ci.run_request(args)
            cloud = stage_root / "materializer/engines/experiments/strength/cloud_runtime.py"
            self.assertTrue(cloud.is_file())
            self.assertEqual(materializer_calls, [([sys.executable, "-I", "-B", str(cloud), "materialize", "--archive",
                str(stage_root / "reports/seed-transfer.zip"), "--manifest-sha256", value["seed_manifest_sha256"],
                "--out", str(stage_root / "seed")], {"check": True, "timeout": 300})])
            fetch.assert_called_once_with(value["seed"], stage_root / "reports/seed-transfer.zip", ci.MAX_SEED)
            owned.assert_called_once_with([sys.executable, "-I", "-B", str(Path(ci.__file__).resolve()), "_execute",
                "--stage", str(args.stage), "--origin", str(origin), "--mode", "execute"], stage_root, context, "controller")

    @unittest.skipUnless(os.name == "posix" and hasattr(os, "waitid") and Path("/proc/self/stat").is_file(), "settled local toy owner identity")
    def test_run_then_cleanup_preserves_materializer_without_recreating_its_namespace(self):
        """Entry-point seam only; no AWS execution or termination proof."""
        with tempfile.TemporaryDirectory(prefix="rove-ci-materializer-cleanup-sequence-") as directory:
            root = Path(directory)
            origin = root / "original-git"
            head = self.make_materializer_origin(origin)
            stage_root = root / "stage"
            reports = stage_root / "reports"
            reports.mkdir(parents=True)
            value = request()
            value["source_origin"]["head_sha"] = head
            context = ci.bind_context(*context_inputs(), NOW)
            request_pin = ci.write_new(reports / "request.original.json", ci.canonical(value) + b"\n")
            context_pin = ci.write_new(reports / "context.json", ci.canonical(context) + b"\n")
            stage = {"format": "rove4k-campaign-ci-stage-v1", "root": str(stage_root), "request": request_pin,
                "request_object": {**value["seed"], "key": "campaign-a/seed/request.json"},
                "context": context_pin, "role_arn": ROLE, "bucket": BUCKET}
            stage_path = stage_root / "stage.json"
            ci.write_new(stage_path, ci.canonical(stage) + b"\n")
            args = SimpleNamespace(stage=stage_path, origin=origin, mode="execute")
            original_run = subprocess.run
            materializer_calls = []
            def local_materializer_transport(argv, *arguments, **kwargs):
                if argv[0] == "git":
                    return original_run(argv, *arguments, **kwargs)
                materializer_calls.append((argv, kwargs))
                return SimpleNamespace(returncode=0)
            def download_transport(descriptor, path, maximum):
                path.write_bytes(b"offline sequence transport fixture; no qualified archive\n")
            def controller_transport(command, owned_root, owned_context, prefix, **kwargs):
                self.assertEqual(owned_root, stage_root)
                self.assertEqual(owned_context, context)
                if prefix == "controller":
                    ci.write_new(stage_root / "execution-started.json", ci.canonical({"campaign_id": value["aws_plan"]["campaign_id"],
                        "request_sha256": request_pin["sha256"]}) + b"\n")
                    # This real, short toy session supplies settled owner
                    # metadata; it runs no frozen code or cloud operation.
                    child = subprocess.Popen([sys.executable, "-I", "-B", "-c", "import time;time.sleep(.1)"],
                        start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    try:
                        owner = ci.process_identity(child.pid)
                        self.assertIsNotNone(owner)
                        self.assertEqual(owner["pid"], owner["pgid"])
                        self.assertEqual(owner["pid"], owner["session"])
                        until = time.monotonic() + 5
                        while os.waitid(os.P_PID, child.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is None:
                            self.assertLess(time.monotonic(), until)
                            time.sleep(.01)
                        self.assertEqual(ci.process_members(owner), [])
                        child.wait(timeout=5)
                    finally:
                        if child.poll() is None:
                            child.kill()
                            child.wait(timeout=5)
                    ci.write_new(reports / "controller-process.json", ci.canonical(owner) + b"\n")
                    ci.write_new(reports / "controller-settled.json", ci.canonical({"owner": owner, "returncode": child.returncode,
                        "group_absent_before_leader_reap": True, "forced": False}) + b"\n")
                else:
                    self.assertEqual(prefix, "cleanup")
                    self.assertEqual(command[-2:], ["--mode", "terminate"])
                    self.assertEqual(kwargs, {"maximum_seconds": 300})
            def namespace_pins():
                materializer = stage_root / "materializer"
                paths = [path for path in materializer.rglob("*") if path.is_file()]
                paths.append(reports / "materializer-source.json")
                return {path.relative_to(stage_root).as_posix(): {**ci.pin(path.read_bytes()),
                    "device": path.stat().st_dev, "inode": path.stat().st_ino, "mode": path.stat().st_mode} for path in paths}
            with patch.object(ci, "fetch_version", side_effect=download_transport) as fetch, \
                 patch.object(ci, "run_owned", side_effect=controller_transport) as owned, \
                 patch.object(ci, "bind_materializer_source", wraps=ci.bind_materializer_source) as bind, \
                 patch.object(ci.subprocess, "run", side_effect=local_materializer_transport):
                ci.run_request(args)
                before = namespace_pins()
                ci.cleanup_request(SimpleNamespace(stage=stage_path, origin=origin))
                self.assertEqual(namespace_pins(), before)
            bind.assert_called_once_with(origin, head, out=stage_root / "materializer")
            fetch.assert_called_once_with(value["seed"], reports / "seed-transfer.zip", ci.MAX_SEED)
            self.assertEqual(len(materializer_calls), 1)
            self.assertEqual(materializer_calls[0][0][3], str(stage_root / "materializer/engines/experiments/strength/cloud_runtime.py"))
            self.assertEqual([call.args[3] for call in owned.call_args_list], ["controller", "cleanup"])

    def test_real_frozen_modules_bind_only_the_materialized_source_tree(self):
        with tempfile.TemporaryDirectory(prefix="rove-ci-frozen-source-") as directory:
            root = Path(directory) / "seed"
            manifest_sha, origin, source_origin = self.make_seed(root)
            result = self.child(root, manifest_sha, origin, source_origin)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertEqual(result.stdout.strip(), b"frozen-import-bound")

    def test_source_pin_mutation_is_rejected_before_cloud_import(self):
        with tempfile.TemporaryDirectory(prefix="rove-ci-frozen-mutated-") as directory:
            root = Path(directory) / "seed"
            manifest_sha, origin, source_origin = self.make_seed(root)
            path = root / "source/engines/experiments/strength/aws.py"
            path.write_bytes(path.read_bytes() + b"\n# unit mutation\n")
            result = self.child(root, manifest_sha, origin, source_origin, "original committed Git blob")
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertEqual(result.stdout.strip(), b"frozen-import-rejected")

    def test_rewritten_source_and_self_consistent_manifest_cannot_replace_git_authority(self):
        with tempfile.TemporaryDirectory(prefix="rove-ci-frozen-repinned-") as directory:
            root = Path(directory) / "seed"
            _, origin, source_origin = self.make_seed(root)
            name = "source/engines/experiments/strength/campaign.py"
            path = root / name
            original = path.read_bytes()
            body = original.replace(b"Explicit", b"Unsealed", 1)
            self.assertEqual(len(body), len(original))
            self.assertNotEqual(body, original)
            path.write_bytes(body)
            manifest_sha = self.rewrite_manifest(root, lambda manifest: manifest["members"].update({name: {**ci.pin(body), "mode": 0o600}}))
            result = self.child(root, manifest_sha, origin, source_origin, "original committed Git blob")
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertEqual(result.stdout.strip(), b"frozen-import-rejected")

    def test_replace_ref_and_repinned_worktree_cannot_substitute_original_git_blob(self):
        with tempfile.TemporaryDirectory(prefix="rove-ci-frozen-replace-ref-") as directory:
            root = Path(directory) / "seed"
            _, origin, source_origin = self.make_seed(root)
            relative = "engines/experiments/strength/campaign.py"
            name = "source/" + relative
            original = (root / name).read_bytes()
            replacement = original.replace(b"Explicit", b"Unsealed", 1)
            self.assertNotEqual(replacement, original)
            self.assertEqual(len(replacement), len(original))
            old_blob = self.git(origin, "rev-parse", "HEAD:" + relative).decode().strip()
            new_blob = self.git(origin, "hash-object", "-w", "--stdin", input_bytes=replacement).decode().strip()
            self.git(origin, "replace", old_blob, new_blob)
            (origin / relative).write_bytes(replacement)
            self.git(origin, "update-index", "--assume-unchanged", "--", relative)
            self.assertEqual(self.git(origin, "status", "--porcelain=v1", "--untracked-files=normal"), b"")
            self.assertEqual(self.git(origin, "cat-file", "blob", old_blob), replacement)
            (root / name).write_bytes(replacement)
            manifest_sha = self.rewrite_manifest(root, lambda manifest: manifest["members"].update(
                {name: {**ci.pin(replacement), "mode": 0o600}}))
            result = self.child(root, manifest_sha, origin, source_origin, "original committed Git blob")
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertEqual(result.stdout.strip(), b"frozen-import-rejected")

    def test_poisoned_ambient_git_redirects_cannot_change_valid_or_invalid_source_binding(self):
        with tempfile.TemporaryDirectory(prefix="rove-ci-frozen-git-environment-") as directory:
            root = Path(directory) / "seed"
            manifest_sha, origin, source_origin = self.make_seed(root)
            poison_root = Path(directory) / "not-the-source"
            poisoned = {"GIT_DIR": str(poison_root / "git"), "GIT_WORK_TREE": str(poison_root / "worktree"),
                "GIT_INDEX_FILE": str(poison_root / "index"), "GIT_OBJECT_DIRECTORY": str(poison_root / "objects"),
                "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(poison_root / "alternates"),
                "GIT_COMMON_DIR": str(poison_root / "common"), "GIT_CONFIG_COUNT": "not-an-integer",
                "GIT_CONFIG_KEY_0": "core.worktree", "GIT_CONFIG_VALUE_0": str(poison_root / "other-worktree"),
                "GIT_CONFIG_PARAMETERS": "malformed injected config", "GIT_CONFIG_GLOBAL": str(poison_root / "config"),
                "GIT_CONFIG_SYSTEM": str(poison_root / "system-config"), "GIT_NO_REPLACE_OBJECTS": "0",
                "GIT_ALLOW_PROTOCOL": "all", "GIT_EXEC_PATH": str(poison_root / "exec"), "GIT_INDEX_VERSION": "invalid"}
            result = self.child(root, manifest_sha, origin, source_origin, git_environment=poisoned)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertEqual(result.stdout.strip(), b"frozen-import-bound")
            name = "source/engines/experiments/strength/campaign.py"
            original = (root / name).read_bytes()
            replacement = original.replace(b"Explicit", b"Unsealed", 1)
            self.assertNotEqual(replacement, original)
            self.assertEqual(len(replacement), len(original))
            (root / name).write_bytes(replacement)
            manifest_sha = self.rewrite_manifest(root, lambda manifest: manifest["members"].update(
                {name: {**ci.pin(replacement), "mode": 0o600}}))
            result = self.child(root, manifest_sha, origin, source_origin, "original committed Git blob", git_environment=poisoned)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertEqual(result.stdout.strip(), b"frozen-import-rejected")

    def test_source_mode_missing_and_extra_namespaces_reject_before_import(self):
        cases = ("mode", "actual-mode", "missing", "extra-file", "extra-directory", "declared-untracked")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory(prefix="rove-ci-frozen-namespace-") as directory:
                root = Path(directory) / "seed"
                manifest_sha, origin, source_origin = self.make_seed(root)
                name = "source/engines/experiments/strength/aws.py"
                if case == "mode":
                    manifest_sha = self.rewrite_manifest(root, lambda manifest: manifest["members"][name].update(mode=0o700))
                    error = "original committed Git blob"
                elif case == "actual-mode":
                    (root / name).chmod(0o700)
                    error = "original committed Git blob"
                elif case == "missing":
                    (root / name).unlink()
                    error = "source path set is incomplete"
                elif case == "extra-directory":
                    (root / "source/unlisted-directory").mkdir()
                    error = "unlisted/protected source directory"
                else:
                    name = "source/engines/experiments/strength/unlisted_fixture.py"
                    body = b"raise AssertionError('unlisted module must not run')\n"
                    (root / name).write_bytes(body)
                    error = "unlisted source member"
                    if case == "declared-untracked":
                        manifest_sha = self.rewrite_manifest(root, lambda manifest: manifest["members"].update({name: {**ci.pin(body), "mode": 0o600}}))
                        error = "exact tracked selection"
                result = self.child(root, manifest_sha, origin, source_origin, error)
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                self.assertEqual(result.stdout.strip(), b"frozen-import-rejected")


class WorkflowFailureTests(unittest.TestCase):
    def test_stage_failure_keeps_report_output_before_any_cloud_download(self):
        with tempfile.TemporaryDirectory(prefix="rove-ci-stage-failure-") as directory:
            root = Path(directory)
            output = root / "github-output.txt"
            output.write_text("")
            args = SimpleNamespace(out=root / "stage", campaign_id="campaign-a", bucket=BUCKET,
                key="campaign-a/seed/request.json", version_id="unit-version", sha256="a" * 64, bytes=100)
            with patch.dict(os.environ, {"GITHUB_OUTPUT": str(output), "GITHUB_RUN_ID": "77", "GITHUB_RUN_ATTEMPT": "2", "EXPECTED_BUCKET": BUCKET}), \
                 patch.object(ci, "github_get", side_effect=ValueError("offline API failure")) as github, \
                 patch.object(ci, "aws_call", side_effect=AssertionError("no AWS after failed context read")) as cloud:
                with self.assertRaisesRegex(ValueError, "offline API failure"):
                    ci.stage_request(args)
            self.assertEqual(output.read_text(), "report_path=" + str(args.out / "reports") + "\n")
            self.assertTrue((args.out / "reports").is_dir())
            self.assertFalse((args.out / "stage.json").exists())
            self.assertEqual(github.call_count, 1)
            cloud.assert_not_called()

    def test_execute_and_preflight_without_owner_gate_never_load_frozen_inputs(self):
        for mode in ("execute", "preflight"):
            with self.subTest(mode=mode), patch.object(ci, "frozen_inputs", side_effect=AssertionError("no unowned frozen import")) as frozen:
                with self.assertRaisesRegex(ValueError, "release gate"):
                    ci.execute_frozen(SimpleNamespace(mode=mode, gate_fd=None))
                frozen.assert_not_called()

    def test_cleanup_without_execution_marker_performs_no_owned_or_cloud_action(self):
        with tempfile.TemporaryDirectory(prefix="rove-ci-no-cleanup-") as directory:
            root = Path(directory)
            with patch.object(ci, "load_stage", return_value=({"root": str(root)}, request(), {})), \
                 patch.object(ci, "run_owned", side_effect=AssertionError("no execution owner")) as owned, \
                 patch.object(ci, "aws_call", side_effect=AssertionError("no AWS owner")) as cloud:
                ci.cleanup_request(SimpleNamespace(stage=root / "stage.json", origin=root / "origin"))
            owned.assert_not_called()
            cloud.assert_not_called()

    def test_cleanup_delegates_exact_terminate_path_with_300_second_bound(self):
        with tempfile.TemporaryDirectory(prefix="rove-ci-cleanup-delegate-") as directory:
            root = Path(directory); (root / "execution-started.json").write_text("{}\n")
            context = {"conservatively_safe_use_until": NOW + 1000}
            args = SimpleNamespace(stage=root / "stage.json", origin=root / "original-source")
            with patch.object(ci, "load_stage", return_value=({"root": str(root)}, request(), context)), \
                 patch.object(ci.time, "time", return_value=NOW), patch.object(ci, "run_owned") as owned:
                ci.cleanup_request(args)
            owned.assert_called_once_with([sys.executable, "-I", "-B", str(Path(ci.__file__).resolve()),
                "_execute", "--stage", str(args.stage), "--origin", str(args.origin), "--mode", "terminate"],
                root, context, "cleanup", maximum_seconds=300)


@unittest.skipUnless(os.name == "posix" and hasattr(os, "waitid") and Path("/proc/self/stat").is_file(),
                     "short owned POSIX transport process checks")
class OwnedProcessTransportTests(unittest.TestCase):
    def root_and_command(self, root, *, exit_code=0, descendant=False):
        (root / "reports").mkdir()
        script = root / "toy_transport.py"
        source = """import argparse,json,os,pathlib,subprocess,sys,time
p=argparse.ArgumentParser();p.add_argument('--gate-fd',type=int,required=True);a=p.parse_args()
assert os.read(a.gate_fd,1)==b'G';os.close(a.gate_fd)
print('owned-toy-gate-open',flush=True)
"""
        if descendant:
            identity = root / "toy-child.json"
            child = ("import json,os,pathlib,time; p=pathlib.Path('/proc/self/stat'); "
                     "f=p.read_text().rsplit(')',1)[1].split(); "
                     "pathlib.Path(" + repr(str(identity)) + ").write_text(json.dumps({'pid':os.getpid(),'start_ticks':int(f[19])})); "
                     "time.sleep(60)")
            source += "subprocess.Popen([sys.executable,'-I','-B','-c'," + repr(child) + "],close_fds=True)\n"
            source += "until=time.monotonic()+3\nwhile not pathlib.Path(" + repr(str(identity)) + ").exists():\n time.sleep(.01)\n assert time.monotonic()<until\n"
        source += "raise SystemExit(" + str(exit_code) + ")\n"
        script.write_text(source)
        return [sys.executable, "-I", "-B", str(script)]

    def test_short_toy_process_uses_gate_and_physically_settles(self):
        with tempfile.TemporaryDirectory(prefix="rove-ci-owned-toy-") as directory:
            root = Path(directory)
            command = self.root_and_command(root)
            ci.run_owned(command, root, {"conservatively_safe_use_until": time.time() + 1200}, "controller", maximum_seconds=5)
            report = ci.document((root / "reports/controller-settled.json").read_bytes())
            self.assertEqual(report["returncode"], 0)
            self.assertIs(report["forced"], False)
            self.assertIs(report["group_absent_before_leader_reap"], True)
            self.assertIsNone(ci.process_identity(report["owner"]["pid"]))
            self.assertEqual((root / "reports/controller.stdout").read_bytes().strip(), b"owned-toy-gate-open")

    def test_nonzero_toy_exit_keeps_settlement_report_before_failure(self):
        with tempfile.TemporaryDirectory(prefix="rove-ci-owned-failure-") as directory:
            root = Path(directory)
            command = self.root_and_command(root, exit_code=7)
            with self.assertRaisesRegex(ValueError, "failure"):
                ci.run_owned(command, root, {"conservatively_safe_use_until": time.time() + 1200}, "controller", maximum_seconds=5)
            report = ci.document((root / "reports/controller-settled.json").read_bytes())
            self.assertEqual(report["returncode"], 7)
            self.assertIs(report["group_absent_before_leader_reap"], True)
            self.assertIsNone(ci.process_identity(report["owner"]["pid"]))

    def test_exited_leader_with_sleeping_descendant_is_cleaned_and_rejected(self):
        with tempfile.TemporaryDirectory(prefix="rove-ci-owned-descendant-") as directory:
            root = Path(directory)
            command = self.root_and_command(root, descendant=True)
            try:
                with self.assertRaisesRegex(ValueError, "descendant"):
                    ci.run_owned(command, root, {"conservatively_safe_use_until": time.time() + 1200}, "controller", maximum_seconds=5)
                report = ci.document((root / "reports/controller-settled.json").read_bytes())
                self.assertEqual(report["returncode"], 0)
                self.assertIs(report["forced"], True)
                self.assertIs(report["group_absent_before_leader_reap"], True)
                child = ci.document((root / "toy-child.json").read_bytes())
                observed = ci.process_identity(child["pid"])
                self.assertTrue(observed is None or observed["start_ticks"] != child["start_ticks"] or observed["state"] == "Z")
            finally:
                # Preserve unrelated PID reuse; only this fixture's live child
                # may be stopped if the tested cleanup path failed.
                path = root / "toy-child.json"
                if path.exists():
                    child = ci.document(path.read_bytes())
                    observed = ci.process_identity(child["pid"])
                    if observed is not None and observed["start_ticks"] == child["start_ticks"] and observed["state"] != "Z":
                        os.kill(child["pid"], signal.SIGKILL)


class FrozenResultOrderTests(unittest.TestCase):
    def test_failed_preflight_or_execution_result_is_saved_before_error(self):
        for mode in ("preflight", "execute"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory(prefix="rove-ci-result-order-") as directory:
                root = Path(directory); (root / "reports").mkdir()
                value = request(); plan = aws.AWSPlan.from_dict(value["aws_plan"])
                client = SimpleNamespace(call=Mock(return_value={"Items": []}))
                publisher = SimpleNamespace(list_keys=Mock(return_value=[]))
                failed = {"allowed": False, "blockers": ["offline preflight denied"]} if mode == "preflight" else {
                    "complete": False, "cleanup": {"ownership_closed": False}}
                instance = SimpleNamespace(state=SimpleNamespace(active_instances=()), execute=Mock(return_value=failed))
                campaign = SimpleNamespace(CampaignController=Mock(return_value=instance),
                    SSMCommands=Mock(return_value="unit-ssm-port"), CloudRuntimeBridge=Mock(return_value="unit-live-bridge"),
                    bootstrap_recipe=Mock(return_value={"id": value["bootstrap"]["recipe_id"], "sha256": value["bootstrap"]["recipe_sha256"]}))
                cloud_aws = SimpleNamespace(S3Evidence=Mock(return_value=publisher), digest=aws.digest,
                    fetch_advisor=Mock(return_value={"source": "offline-fake-service"}), preflight=Mock(return_value=failed))
                cloud = SimpleNamespace(bootstrap_module=lambda: campaign, ledger=ledger, budget=budget, aws=cloud_aws)
                stage = {"root": str(root), "request": {"sha256": "9" * 64}}
                context = ci.bind_context(*context_inputs(), NOW)
                read_gate, write_gate = os.pipe(); os.write(write_gate, b"G"); os.close(write_gate)
                args = SimpleNamespace(mode=mode, gate_fd=read_gate, stage=root / "stage.json", origin=root / "origin")
                with patch.object(ci, "frozen_inputs", return_value=(stage, value, context, cloud, {}, plan, client)), \
                     patch.object(ci.time, "time", return_value=NOW):
                    with self.assertRaises(ValueError):
                        ci.execute_frozen(args)
                saved = ci.document((root / "reports" / (mode + "-result.json")).read_bytes())
                self.assertEqual(saved, failed)
                campaign.CampaignController.assert_called_once()
                called = campaign.CampaignController.call_args
                self.assertIs(called.args[0], plan)
                self.assertIsInstance(called.args[1], ledger.Journal)
                self.assertIs(called.args[2], client)
                self.assertIs(called.args[3], publisher)
                self.assertEqual(called.args[4], "unit-ssm-port")
                self.assertEqual(called.kwargs["seed"], value["seed"])
                campaign.SSMCommands.assert_called_once_with(client)
                if mode == "execute":
                    campaign.CloudRuntimeBridge.assert_called_once_with()
                    self.assertEqual(called.args[5], "unit-live-bridge")
                    instance.execute.assert_called_once()
                    self.assertTrue((root / "reports/permit.json").is_file())
                else:
                    campaign.CloudRuntimeBridge.assert_not_called()
                    self.assertIsNone(called.args[5])
                    cloud_aws.preflight.assert_called_once()


class WorkflowFenceTests(unittest.TestCase):
    def test_different_campaign_ids_share_one_project_execution_fence(self):
        workflow = Path(ci.__file__).resolve().parents[3] / ".github/workflows/aws-evaluation.yml"
        text = workflow.read_text(encoding="utf-8")
        self.assertEqual(re.findall(r"(?m)^  group: (.+)$", text),
                         ["aws-evaluation-rove4k-292341339363-ap-southeast-2"])
        self.assertEqual(re.findall(r"(?m)^  cancel-in-progress: (.+)$", text), ["false"])

    def test_reviewed_workflow_pin_binds_the_actual_fixed_fence_definition(self):
        workflow = Path(ci.__file__).resolve().parents[3] / ".github/workflows/aws-evaluation.yml"
        raw = workflow.read_bytes().replace(b"\r\n", b"\n")
        self.assertEqual(hashlib.sha256(raw).hexdigest(), ci.WORKFLOW_SHA256)


if __name__ == "__main__":
    unittest.main()
