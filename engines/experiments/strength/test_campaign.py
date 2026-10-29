"""Short local lifecycle fault checks; fake AWS is never deployment evidence."""
from dataclasses import replace
import ast
import base64
import copy
import hashlib
import json
import os
import shutil
import pathlib
from pathlib import Path
import re
import stat
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

try:
    from . import aws, budget, campaign, ledger
    from .test_aws import FakeAWS, plan as base_plan
except ImportError:
    import aws
    import budget
    import campaign
    import ledger
    from test_aws import FakeAWS, plan as base_plan


def plan():
    p = base_plan()
    return replace(p, region="ap-southeast-2", project_region="ap-southeast-2",
        watchdog_arn=p.watchdog_arn.replace("us-east-2", "ap-southeast-2"))


class Clock:
    def __init__(self):
        self.now = 1000.125

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class Cloud(FakeAWS):
    def __init__(self, p, journal, *, terminated=True):
        super().__init__(p)
        self.journal = journal
        self.terminated = terminated
        self.command_id = "12345678-1234-1234-1234-123456789012"
        self.ssm_status = "Success"
        self.ssm_response = 0
        self.lose_send = False
        self.send_count = 0
        self.ssm_ready_calls = 0
        self.ssm_online_after = 0
        self.ssm_wrong_id = False

    def call(self, service, operation, request):
        if (service, operation) == ("ec2", "run-instances") and not request.get("DryRun"):
            original = ledger.read_journal(self.journal.path, self.plan.campaign_id)
            assert any(row["event"] == "budget.launch_requested" for row in original)
        if (service, operation) == ("ec2", "describe-instances") and self.instance:
            if self.instance["State"]["Name"] == "pending":
                self.instance["State"]["Name"] = "running"
            elif self.instance["State"]["Name"] == "shutting-down" and self.terminated:
                self.instance["State"]["Name"] = "terminated"
        if service == "ssm":
            self.calls.append((service, operation, copy.deepcopy(request)))
            if operation == "describe-instance-information":
                self.ssm_ready_calls += 1
                if self.ssm_ready_calls <= self.ssm_online_after:
                    return {"InstanceInformationList": []}
                return {"InstanceInformationList": [{"InstanceId": "i-wrong" if self.ssm_wrong_id else self.instance["InstanceId"],
                    "PingStatus": "Online", "PlatformType": "Linux", "AgentVersion": "3.3.1.0"}]}
            if operation == "send-command":
                self.send_count += 1
                if self.lose_send:
                    raise aws.AwsError("ObservationTimeout", "ssm.send-command")
                return {"Command": {"CommandId": self.command_id, "InstanceIds": request["InstanceIds"]}}
            if operation == "get-command-invocation":
                return {"CommandId": self.command_id, "InstanceId": self.instance["InstanceId"],
                        "Status": self.ssm_status, "ResponseCode": self.ssm_response}
            if operation == "cancel-command":
                return {}
            raise AssertionError(operation)
        return super().call(service, operation, request)


class Publisher:
    def __init__(self, root):
        self.root = root
        self.root.mkdir()

    def publish(self, path, key):
        raw = path.read_bytes()
        return {"verified": True, "sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": len(raw), "object_key": key, "backend": "s3"}


class Bridge:
    def __init__(self, journal):
        self.journal = journal
        self.valid = True
        self.collect_calls = 0
        self.corrupt = False
        self.complete = True

    def validate(self, **kw):
        return {"verified": self.valid, "plan_sha256": aws.digest(kw["plan"].as_dict()),
                "seed_sha256": kw["seed"]["sha256"], "seed_manifest_sha256": kw["manifest_sha256"],
                "deployment_receipt_sha256": kw["permit"]["deployment_receipt_sha256"],
                "ami_id": kw["plan"].ami_id}

    def collect(self, **kw):
        self.collect_calls += 1
        h = kw["handoff"]
        assert h["journal"]["last_sha256"] == self.journal.last
        assert h["journal"]["rows"] == len(self.journal.rows)
        rows = copy.deepcopy(self.journal.rows)
        row = {"format": "rove4k-campaign-v1", "seq": len(rows), "event": "host.short_local_check",
            "time_utc": rows[-1]["time_utc"], "campaign": self.journal.campaign,
            "pair": None, "game": None, "attempt": None, "data": {}, "previous_sha256": self.journal.last}
        row["sha256"] = ledger.digest(row)
        rows.append(row)
        if self.corrupt:
            rows[-1]["data"] = {"tampered": True}
        return {"terminal": {"complete": self.complete}, "rows": rows}


class CampaignTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="rove-campaign-test-")
        self.root = Path(self.tmp.name)
        self.journal = ledger.Journal(self.root / "campaign.jsonl", "campaign-a")
        self.clock = Clock()
        self.plan = plan()
        self.cloud = Cloud(self.plan, self.journal)
        self.publisher = Publisher(self.root / "evidence")
        self.bridge = Bridge(self.journal)
        self.seed = {"bucket": self.plan.artifact_bucket, "key": "campaign-a/seed.zip", "version_id": "v1",
                     "sha256": "a" * 64, "bytes": 100}
        self.permit = {"format": "rove4k-campaign-permit-v1", "campaign_id": self.plan.campaign_id,
            "plan_sha256": aws.digest(self.plan.as_dict()), "seed_sha256": self.seed["sha256"],
            "seed_manifest_sha256": "b" * 64, "deadline_epoch": self.plan.deadline_epoch,
            "issued_at": 999, "expires_at": 1800, "deployment_receipt_sha256": "c" * 64,
            "bootstrap": {"recipe_id": campaign.BOOTSTRAP_RECIPE_ID, "recipe_sha256": campaign.BOOTSTRAP_RECIPE_SHA256},
            "runtime_bridge": "rove4k_cloud_runtime", "host": {
                "root": "/opt/rove4k/campaign-a-" + self.plan.owner_nonce[:12],
                "cgroup_root": "/sys/fs/cgroup/system.slice/rove4k-host-one.service", "host_job_id": "host-one"}}
        self.advisor = {"source_url": aws.ADVISOR_URL, "fetched_at": self.clock(),
            "region": self.plan.region, "instance_type": "m6a.48xlarge", "os": "Linux",
            "maximum_percent": 5, "band": "<5%", "sha256": "d" * 64,
            "source_modified_at": self.clock()}

    def tearDown(self):
        self.journal.close()
        self.tmp.cleanup()

    def controller(self):
        return campaign.CampaignController(self.plan, self.journal, self.cloud, self.publisher,
            campaign.SSMCommands(self.cloud), self.bridge, seed=self.seed, manifest={"source_tree": "source"},
            manifest_sha256="b" * 64, clock=self.clock, monotonic=self.clock, sleep=self.clock.sleep,
            poll_seconds=1, cleanup_seconds=4)

    def launches(self):
        return [r for s, o, r in self.cloud.calls if (s, o) == ("ec2", "run-instances") and not r.get("DryRun")]

    def test_inspect_is_offline(self):
        result = self.controller().inspect()
        self.assertFalse(result["aws_calls_performed"])
        self.assertEqual(self.cloud.calls, [])
        self.assertEqual(self.journal.rows, [])

    def test_normal_handoff_merges_chain_before_physical_close(self):
        controller = self.controller()
        result = controller.execute(self.permit, self.advisor)
        self.assertTrue(result["complete"], result)
        self.assertEqual(len(self.launches()), 1)
        self.assertEqual(self.cloud.send_count, 1)
        self.assertEqual(self.bridge.collect_calls, 1)
        events = [row["event"] for row in self.journal.rows]
        self.assertLess(events.index("host.short_local_check"), events.index("budget.instance_observed"))
        self.assertIn("campaign.ownership_closed", events)
        self.assertEqual(controller.state.active_instances, ())
        replay = budget.CampaignBudget.replay(self.plan.campaign_id, ledger.read_journal(self.journal.path, self.plan.campaign_id))
        self.assertEqual(replay.instances[0].requested_at, 1000.125)
        intent = aws.get_record(self.cloud, self.plan, "launch#" + self.plan.launch_token)
        self.assertEqual(replay.instances[0].requested_at, intent["requested_at"])
        request = next(r for s, o, r in self.cloud.calls if (s, o) == ("ssm", "send-command"))
        self.assertEqual(request["InstanceIds"], [self.cloud.instance["InstanceId"]])
        self.assertEqual(request["Parameters"]["executionTimeout"], [str(int(self.plan.deadline_epoch - 1000.125 - 30))])

    def test_termination_ack_does_not_free_slot(self):
        self.cloud.terminated = False
        controller = self.controller()
        result = controller.execute(self.permit, self.advisor)
        self.assertFalse(result["complete"])
        self.assertFalse(result["cleanup"]["termination_observed"])
        self.assertEqual(len(controller.state.active_instances), 1)
        self.assertNotIn("campaign.ownership_closed", [r["event"] for r in self.journal.rows])

    def test_lost_launch_response_recovers_original_then_terminates(self):
        self.cloud.lose_launch_response = True
        result = self.controller().execute(self.permit, self.advisor)
        self.assertFalse(result["complete"])
        self.assertTrue(result["cleanup"]["termination_observed"])
        self.assertEqual(len(self.launches()), 1)
        self.assertEqual(self.launches()[0]["ClientToken"], self.plan.launch_token)
        self.assertEqual(self.cloud.send_count, 0)

    def test_resume_only_reconciles_original_token(self):
        controller = self.controller()
        controller.append("budget.launch_requested", {"launch_token": self.plan.launch_token, "max_hourly_usd": "8"})
        aws.put_immutable(self.cloud, self.plan, "launch#" + self.plan.launch_token, self.plan.intent(self.clock()))
        result = controller.execute(self.permit, self.advisor)
        self.assertFalse(result["complete"])
        self.assertTrue(result["cleanup"]["unresolved_launch"])
        self.assertEqual(self.launches(), [])
        self.assertEqual(len(controller.state.active_instances), 1)

    def test_cleanup_after_permit_expiry_never_launches_or_calls_bridge(self):
        controller = self.controller()
        controller.append("budget.launch_requested", {"launch_token": self.plan.launch_token, "max_hourly_usd": "8"})
        receipt = aws.preflight(self.cloud, self.plan, self.advisor, self.clock())
        controller._bind(aws.launch(self.cloud, self.plan, controller.state, receipt, self.clock()))
        controller.append("campaign.ssm_requested", {"instance_id": self.cloud.instance["InstanceId"], "host_job_id": "host-one"})
        self.clock.now = 50000
        with patch.object(self.bridge, "validate", side_effect=AssertionError("cleanup must not start runtime")):
            result = self.controller().terminate_owned()
        self.assertTrue(result["complete"], result)
        self.assertFalse(result["paid_launch_request_sent"])
        self.assertEqual(len(self.launches()), 1)
        self.assertEqual(self.cloud.send_count, 0)
        self.assertIn("campaign.host_history_unresolved", [row["event"] for row in self.journal.rows])

    def test_lost_ssm_response_never_resends(self):
        self.cloud.lose_send = True
        result = self.controller().execute(self.permit, self.advisor)
        self.assertFalse(result["complete"])
        self.assertTrue(result["cleanup"]["termination_observed"])
        self.assertEqual(self.cloud.send_count, 1)
        self.assertIn("campaign.host_history_unresolved", [r["event"] for r in self.journal.rows])
        with self.assertRaisesRegex(ValueError, "unresolved original host history"):
            self.controller().execute(self.permit, self.advisor)
        self.assertEqual(len(self.launches()), 1)

    def test_failed_or_incomplete_host_is_not_campaign_success(self):
        self.bridge.complete = False
        result = self.controller().execute(self.permit, self.advisor)
        self.assertFalse(result["complete"])
        self.assertTrue(result["cleanup"]["termination_observed"])

    def test_corrupt_host_chain_is_not_partially_imported(self):
        self.bridge.corrupt = True
        result = self.controller().execute(self.permit, self.advisor)
        self.assertFalse(result["complete"])
        self.assertNotIn("host.short_local_check", [r["event"] for r in self.journal.rows])
        self.assertTrue(result["cleanup"]["termination_observed"])

    def test_prelaunch_guards_have_no_paid_call(self):
        self.bridge.valid = False
        with self.assertRaisesRegex(ValueError, "authority"):
            self.controller().execute(self.permit, self.advisor)
        self.assertEqual(self.cloud.calls, [])
        self.assertEqual(self.journal.rows, [])

    def test_stale_advisor_cannot_launch(self):
        self.advisor["source_modified_at"] = 0
        self.clock.now = 700000
        self.permit.update(issued_at=699999, expires_at=700100, deadline_epoch=800000)
        self.plan = replace(self.plan, deadline_epoch=800000)
        self.cloud.plan = self.plan
        self.permit["plan_sha256"] = aws.digest(self.plan.as_dict())
        result = self.controller().execute(self.permit, self.advisor)
        self.assertFalse(result["complete"])
        self.assertEqual(self.launches(), [])
        self.assertFalse(any(r["event"] == "budget.launch_requested" for r in self.journal.rows))

    def test_actual_quota_port_below_192_cannot_launch(self):
        self.cloud.quota = 191
        result = self.controller().execute(self.permit, self.advisor)
        self.assertFalse(result["complete"])
        self.assertEqual(self.launches(), [])
        receipt = next(row["data"] for row in self.journal.rows if row["event"] == "campaign.preflight") if any(
            row["event"] == "campaign.preflight" for row in self.journal.rows) else None
        self.assertIsNone(receipt)
        self.assertTrue(any((s, o) == ("service-quotas", "get-service-quota") for s, o, _ in self.cloud.calls))
        self.assertFalse(any(row["event"] == "budget.launch_requested" for row in self.journal.rows))

    def test_free_plan_cannot_launch_or_upgrade(self):
        self.cloud.account_plan_response["accountPlanType"] = "FREE"
        result = self.controller().execute(self.permit, self.advisor)
        self.assertFalse(result["complete"])
        self.assertEqual(self.launches(), [])
        self.assertFalse(any("upgrade" in operation for _, operation, _ in self.cloud.calls))

    def test_permit_rejects_arbitrary_provider_and_expiry(self):
        p = copy.deepcopy(self.permit)
        p["runtime_bridge"] = {"module": "anything"}
        with self.assertRaisesRegex(ValueError, "canonical"):
            campaign.validate_permit(p, self.plan, self.seed, "b" * 64, self.clock())
        p = copy.deepcopy(self.permit)
        p["expires_at"] = 1000
        with self.assertRaisesRegex(ValueError, "stale"):
            campaign.validate_permit(p, self.plan, self.seed, "b" * 64, self.clock())

    def test_ssm_eventual_consistency_is_not_success(self):
        with patch.object(self.cloud, "call", side_effect=aws.AwsError("InvocationDoesNotExist", "ssm.get-command-invocation")):
            row = campaign.SSMCommands(self.cloud).observe(self.cloud.command_id, "i-1234567890abcdef0")
        self.assertEqual(row["status"], "NotObserved")

    def test_eventual_ssm_registration_waits_before_single_send(self):
        self.cloud.ssm_online_after = 2
        result = self.controller().execute(self.permit, self.advisor)
        self.assertTrue(result["complete"], result)
        self.assertEqual(self.cloud.ssm_ready_calls, 3)
        self.assertEqual(self.cloud.send_count, 1)
        requests = [request for service, operation, request in self.cloud.calls
                    if (service, operation) == ("ssm", "describe-instance-information")]
        self.assertEqual(requests, [{"Filters": [{"Key": "InstanceIds", "Values": [self.cloud.instance["InstanceId"]]}]}] * 3)
        self.assertGreaterEqual(self.clock(), 1002.125)
        ready = next(row for row in self.journal.rows if row["event"] == "campaign.ssm_ready")
        self.assertEqual(ready["data"]["agent_version"], "3.3.1.0")

    def test_wrong_ssm_identity_fails_before_send_and_terminates(self):
        self.cloud.ssm_wrong_id = True
        result = self.controller().execute(self.permit, self.advisor)
        self.assertFalse(result["complete"])
        self.assertTrue(result["cleanup"]["termination_observed"])
        self.assertEqual(self.cloud.send_count, 0)

    def test_keyboard_cancel_still_observes_termination_then_reraises(self):
        controller = self.controller()
        with patch.object(controller.ssm, "observe", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                controller.execute(self.permit, self.advisor)
        self.assertEqual(controller.state.active_instances, ())
        self.assertTrue(any(row["event"] == "campaign.ownership_closed" for row in self.journal.rows))

    def test_canonical_runtime_is_reused_without_second_import(self):
        runtime = SimpleNamespace(validate_controller_inputs=lambda **kw: {}, collect_host_result=lambda **kw: {})
        runtime.canonical_provider = lambda: runtime
        with patch.dict(campaign.sys.modules, {"rove4k_cloud_runtime": runtime}):
            with patch.object(campaign.importlib, "import_module", side_effect=AssertionError("second import")):
                bridge = campaign.CloudRuntimeBridge()
        self.assertEqual(bridge.validate(), {})

    def test_entire_returned_chain_is_checked_before_any_append(self):
        controller = self.controller()
        controller.append("campaign.test_prefix", {})
        handoff = {"journal": {"rows": len(self.journal.rows), "last_sha256": self.journal.last}}
        rows = self.bridge.collect(handoff=handoff)["rows"]
        next_row = copy.deepcopy(rows[-1])
        next_row.update(seq=len(rows), previous_sha256=rows[-1]["sha256"], extra="unappendable")
        next_row.pop("sha256")
        next_row["sha256"] = ledger.digest(next_row)
        rows.append(next_row)
        original = copy.deepcopy(self.journal.rows)
        with self.assertRaisesRegex(ValueError, "not appendable"):
            campaign.merge_host_rows(self.journal, handoff, rows)
        self.assertEqual(self.journal.rows, original)

    def test_delegation_path_must_match_exact_systemd_unit(self):
        p = copy.deepcopy(self.permit)
        p["host"]["cgroup_root"] = "/sys/fs/cgroup/other-controller"
        with self.assertRaisesRegex(ValueError, "delegated"):
            campaign.validate_permit(p, self.plan, self.seed, "b" * 64, self.clock())


@unittest.skipUnless(os.name == "posix", "actual short POSIX bootstrap check")
class BootstrapTests(unittest.TestCase):
    def test_actual_short_process_has_owned_session_and_reaped_group(self):
        with tempfile.TemporaryDirectory(prefix="rove-bootstrap-owner-") as directory:
            runner = campaign.BootstrapRunner(Path(directory), __import__('time').time() + 10)
            row = runner.run(["/usr/bin/python3", "-I", "-c", "print('bounded')"], 3)
            self.assertEqual(row["pid"], row["pgid"])
            self.assertEqual(row["pid"], row["sid"])
            self.assertGreater(row["start_ticks"], 0)
            self.assertTrue(row["reaped"] and row["group_absent"] and row["terminal"])
            self.assertFalse(row["forced_cleanup"])
            self.assertEqual(Path(row["stdout"]["path"]).read_bytes(), b"bounded\n")

    def test_bootstrap_timeout_preserves_failed_receipt_and_reaps_group(self):
        with tempfile.TemporaryDirectory(prefix="rove-bootstrap-timeout-") as directory:
            runner = campaign.BootstrapRunner(Path(directory), __import__('time').time() + 10)
            with self.assertRaisesRegex(RuntimeError, "failed"):
                runner.run(["/usr/bin/python3", "-I", "-c", "import time;time.sleep(5)"], 0.05)
            row = runner.commands[0]
            self.assertTrue(row["forced_cleanup"])
            self.assertTrue(row["reaped"] and row["group_absent"])

    def test_signed_recipe_is_fixed_and_has_no_prepared_ami_requirement(self):
        recipe = campaign.bootstrap_recipe()
        claimed = recipe.pop("sha256")
        self.assertEqual(claimed, ledger.digest(recipe))
        self.assertEqual(claimed, campaign.BOOTSTRAP_RECIPE_SHA256)
        self.assertIn("g++-12", recipe["apt_packages"])
        self.assertIn("gcc-11", recipe["apt_packages"])
        self.assertNotIn("numactl", recipe["apt_packages"])
        self.assertIn("signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg", recipe["apt_sources"])

    @unittest.skipUnless(shutil.which("gpg"), "public-key fingerprint validation needs local gpg")
    def test_official_public_signing_key_fingerprint(self):
        with tempfile.TemporaryDirectory(prefix="rove-public-key-") as directory:
            root = Path(directory)
            home = root / "public-only"
            home.mkdir(mode=0o700)
            key = root / "public.asc"
            key.write_text(campaign.AWS_CLI_PUBLIC_KEY)
            row = subprocess.run(["gpg", "--no-options", "--homedir", str(home), "--batch", "--with-colons",
                                  "--import-options", "show-only", "--import", str(key)],
                                 capture_output=True, timeout=5)
            self.assertEqual(row.returncode, 0, row.stderr.decode())
            fingerprints = [line.split(":")[9] for line in row.stdout.decode().splitlines() if line.startswith("fpr:")]
            self.assertIn(campaign.AWS_CLI_SIGNER, fingerprints)

    def test_install_failure_keeps_recipe_and_command_log_without_installing(self):
        class FakeRunner:
            def __init__(self, root, deadline, **kw):
                self.commands = []

            def run(self, argv, seconds, **kw):
                self.commands.append({"argv": argv, "returncode": 100, "reaped": True, "group_absent": True})
                raise RuntimeError("fake APT refusal")

        with tempfile.TemporaryDirectory(prefix="rove-bootstrap-refusal-") as directory:
            root = Path(directory)
            now = __import__('time').time()
            with self.assertRaisesRegex(RuntimeError, "fake APT"):
                campaign.install_bootstrap(root, campaign.bootstrap_recipe(), {"expires_at": now + 900},
                    {"deadline_epoch": now + 2000}, runner_factory=FakeRunner)
            receipt = json.loads((root / "bootstrap" / "receipt.json").read_bytes())
            self.assertFalse(receipt["complete"])
            self.assertEqual(receipt["recipe_sha256"], campaign.BOOTSTRAP_RECIPE_SHA256)
            self.assertEqual(receipt["commands"][0]["argv"][0], "/usr/bin/apt-get")
            self.assertNotIn("--allow-unauthenticated", receipt["commands"][0]["argv"])

    def test_actual_loader_checks_archive_and_executes_only_sealed_entry(self):
        with tempfile.TemporaryDirectory(prefix="rove-bootstrap-test-") as directory:
            root = Path(directory)
            target = root / "host"
            entry = "source/engines/experiments/strength/cloud_runtime.py"
            source = b"import pathlib,sys\nassert sys.flags.isolated == 1\npathlib.Path(__file__).parents[4].joinpath('local-check.txt').write_text('sealed')\n"
            manifest = {"format": "rove4k-cloud-seed-v1", "source_tree": "source", "rove": [],
                "peers": [{"family": "ice4", "profile": "test-p4"}], "members": {
                entry: {"bytes": len(source), "sha256": hashlib.sha256(source).hexdigest(), "mode": 0o600}}}
            manifest_raw = ledger.canonical(manifest) + b"\n"
            archive = root / "source.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("seed.json", manifest_raw)
                output.writestr(entry, source)
            tool = root / "aws"
            tool.write_text("#!/usr/bin/env python3\nimport os,shutil,sys\nshutil.copyfile(os.environ['ROVE_TEST_ARCHIVE'],sys.argv[-1])\n")
            tool.chmod(0o700)
            unit = root / "systemd-run"
            unit.write_text("#!/usr/bin/env python3\nimport subprocess,sys\nassert '--property=Delegate=yes' in sys.argv and '--wait' in sys.argv\nraise SystemExit(subprocess.run(sys.argv[sys.argv.index('--collect')+1:]).returncode)\n")
            unit.chmod(0o700)
            p = replace(plan(), deadline_epoch=int(__import__('time').time()) + 900)
            handoff = {"root": str(target), "host_job_id": "local-check", "aws_plan": p.as_dict(), "seed_manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
                "seed": {"bucket": p.artifact_bucket, "key": "campaign-a/seed.zip", "version_id": "v1",
                         "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(), "bytes": archive.stat().st_size}}
            environment = os.environ.copy()
            environment.update(PATH=str(root) + os.pathsep + environment["PATH"], ROVE_TEST_ARCHIVE=str(archive))
            permit = {"expires_at": int(__import__('time').time()) + 800}
            command = campaign.bootstrap_command(handoff, permit, manifest, systemd_run=str(unit))
            # Install transport is mocked; the actual sealed ZIP loader and
            # process handoff below still execute as ordinary local processes.
            command = command.replace("env=install_bootstrap(root,d['recipe'],p,h['aws_plan'])", "env=os.environ.copy()")
            result = subprocess.run(["/bin/sh", "-c", command], capture_output=True, timeout=10, env=environment)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertEqual((target / "seed" / "local-check.txt").read_text(), "sealed")
            bad = copy.deepcopy(handoff)
            bad["root"] = str(root / "bad-host")
            bad["seed"]["sha256"] = "0" * 64
            command = campaign.bootstrap_command(bad, permit, manifest, systemd_run=str(unit)).replace(
                "env=install_bootstrap(root,d['recipe'],p,h['aws_plan'])", "env=os.environ.copy()")
            result = subprocess.run(["/bin/sh", "-c", command],
                                    capture_output=True, timeout=10, env=environment)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((root / "bad-host" / "seed" / "local-check.txt").exists())


class BootstrapCapacityTests(unittest.TestCase):
    """Run the generated loader's real ZIP block with small owned fixtures.

    Large-boundary cases change only reported ZipInfo sizes, never allocate
    large payloads. The admission predicate and pre-read ordering stay real.
    """
    JOINT = [{"family": family, "profile": profile} for family in "ABCDEF"
             for profile in ("test-p4", "test-p28")]

    @staticmethod
    def inline_parts():
        command = campaign.bootstrap_command({"host_job_id": "capacity-check"}, {}, {"source_tree": "source"})
        source = command.split("<<'ROVE_CLOUD_BOOTSTRAP'\n", 1)[1].rsplit("ROVE_CLOUD_BOOTSTRAP\n", 1)[0]
        tree = ast.parse(source)
        predicate = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                         and node.name == "seed_expansion_limit")
        namespace = {}
        exec(compile(ast.Module(body=[predicate], type_ignores=[]), "<actual-inline-predicate>", "exec"), namespace)
        loader = next(node for node in tree.body if isinstance(node, ast.With))
        return namespace["seed_expansion_limit"], compile(ast.Module(body=[loader], type_ignores=[]),
                                                        "<actual-inline-ZIP-loader>", "exec")

    def fixture(self, root, *, rove=None, peers=None, suffix=b"\n", payload_count=9, mutate=None):
        names = ["source/engines/experiments/strength/cloud_runtime.py"]
        names += ["payload-" + str(index) for index in range(payload_count - 1)]
        contents = {name: b"small bounded fixture\n" for name in names}
        manifest = {"format": "rove4k-cloud-seed-v1", "source_tree": "source",
                    "rove": copy.deepcopy(self.JOINT if rove is None else rove),
                    "peers": copy.deepcopy([] if peers is None else peers),
                    "members": {name: {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                                       "mode": 0o600} for name, data in contents.items()}}
        if mutate is not None:
            mutate(manifest)
        raw = ledger.canonical(manifest) + suffix
        archive = root / "source.zip"
        with zipfile.ZipFile(archive, "w") as output:
            output.writestr("seed.json", raw)
            for name, data in contents.items():
                output.writestr(name, data)
        return manifest, raw, archive, contents

    def load(self, root, raw, archive, *, total=None, member_size=None, manifest_size=None,
             extra_infos=0, manifest_sha=None):
        predicate, loader = self.inline_parts()
        opened, sizes = [], []
        original_zip = zipfile.ZipFile

        class ObservedZip(original_zip):
            def infolist(self):
                rows = [copy.copy(info) for info in super().infolist()]
                if total is not None:
                    remaining = total - rows[0].file_size
                    for row in rows[1:]:
                        row.file_size = min(32 << 20, remaining)
                        remaining -= row.file_size
                    if remaining:
                        raise AssertionError("fixture needs enough small metadata rows")
                if member_size is not None:
                    rows[1].file_size = member_size
                if extra_infos:
                    for index in range(extra_infos):
                        rows.append(zipfile.ZipInfo("extra-" + str(index)))
                sizes.extend(row.file_size for row in rows)
                return rows

            def getinfo(self, name):
                info = copy.copy(super().getinfo(name))
                if name == "seed.json" and manifest_size is not None:
                    info.file_size = manifest_size
                return info

            def open(self, name, *args, **kwargs):
                opened.append(name.filename if isinstance(name, zipfile.ZipInfo) else name)
                return super().open(name, *args, **kwargs)

        output = root / "materialized"
        context = {"zipfile": zipfile, "hashlib": hashlib, "json": json, "pathlib": pathlib,
                   "re": re, "stat": stat, "archive": archive, "out": output, "enc": ledger.canonical,
                   "h": {"seed_manifest_sha256": manifest_sha or hashlib.sha256(raw).hexdigest()},
                   "p": {"expires_at": __import__("time").time() + 100},
                   "seed_expansion_limit": predicate}
        context["h"]["aws_plan"] = {"deadline_epoch": __import__("time").time() + 100}
        try:
            with patch.object(zipfile, "ZipFile", ObservedZip):
                exec(loader, context)
        except Exception as error:
            return error, opened, output, sizes
        return None, opened, output, sizes

    def test_inline_and_cloud_predicates_have_exact_same_cohort_policy(self):
        try:
            from . import cloud_runtime
        except ImportError:
            import cloud_runtime
        inline, _ = self.inline_parts()
        valid = [
            ({"rove": self.JOINT, "peers": []}, 256 << 20),
            ({"rove": self.JOINT, "peers": [{"family": "ice4", "profile": "test-p28"}]}, 256 << 20),
            ({"rove": self.JOINT[:6], "peers": []}, 128 << 20),
            ({"rove": [row for row in self.JOINT if row["profile"] == "test-p4"],
              "peers": [{"family": "c4ke", "profile": "test-p28"}]}, 128 << 20),
            ({"rove": [row for row in self.JOINT if row["profile"] == "test-p28"], "peers": []}, 128 << 20),
            ({"rove": [], "peers": [{"family": "ice4", "profile": "test-p28"}]}, 128 << 20),
        ]
        invalid = [None, {}, {"rove": [], "peers": []}, {"rove": None, "peers": []},
                   {"rove": self.JOINT, "peers": None}, {"rove": self.JOINT + [self.JOINT[0]], "peers": []},
                   {"rove": self.JOINT, "peers": [{"family": "ice4", "profile": "submission"}]},
                   {"rove": self.JOINT, "peers": [{"family": "ice4", "profile": "test-p4"}] * 2},
                   {"rove": [{"family": [], "profile": "test-p4"}], "peers": []},
                   {"rove": [{"family": "A", "profile": []}], "peers": []},
                   {"rove": [{"family": "AB", "profile": "test-p4"}], "peers": []}]
        for value, limit in valid:
            with self.subTest(value=value):
                self.assertEqual(inline(value), limit)
                self.assertEqual(cloud_runtime.seed_expansion_limit(value), limit)
        for value in invalid:
            with self.subTest(value=value):
                for predicate in (inline, cloud_runtime.seed_expansion_limit):
                    with self.assertRaises(ValueError):
                        predicate(value)

    def test_real_small_joint_loader_materializes_only_after_all_checks(self):
        with tempfile.TemporaryDirectory(prefix="rove-inline-small-") as directory:
            root = Path(directory)
            _, raw, archive, contents = self.fixture(root)
            error, opened, out, _ = self.load(root, raw, archive)
            self.assertIsNone(error)
            self.assertEqual(opened[0], "seed.json")
            self.assertEqual((out / "seed.json").read_bytes(), raw)
            self.assertEqual({name: (out / name).read_bytes() for name in contents}, contents)

    def test_actual_128_and_256_boundaries_precede_all_payload_reads(self):
        for rove, limit in ((self.JOINT[:6], 128 << 20), (self.JOINT, 256 << 20)):
            for delta in (0, 1):
                with self.subTest(limit=limit, delta=delta), tempfile.TemporaryDirectory(prefix="rove-inline-size-") as directory:
                    root = Path(directory)
                    _, raw, archive, _ = self.fixture(root, rove=rove)
                    error, opened, out, sizes = self.load(root, raw, archive, total=limit + delta)
                    self.assertEqual(sum(sizes), limit + delta)
                    self.assertIsInstance(error, AssertionError)
                    self.assertIn("ZIP metadata differs" if delta == 0 else "ZIP expansion", str(error))
                    self.assertEqual(opened, ["seed.json"])
                    self.assertFalse(out.exists())

    def test_member_32mib_and_manifest_4mib_limits_remain_independent(self):
        for options, message, expected_reads in (({"member_size": (32 << 20) + 1}, "ZIP expansion", ["seed.json"]),
                                                  ({"manifest_size": (4 << 20) + 1}, "bounded read", [])):
            with self.subTest(options=options), tempfile.TemporaryDirectory(prefix="rove-inline-limits-") as directory:
                root = Path(directory)
                _, raw, archive, _ = self.fixture(root)
                error, opened, out, _ = self.load(root, raw, archive, **options)
                self.assertIsInstance(error, AssertionError)
                self.assertIn(message, str(error))
                self.assertEqual(opened, expected_reads)
                self.assertFalse(out.exists())

    def test_manifest_requires_controller_sha_and_exactly_one_lf(self):
        for suffix, expected_sha, message in ((b"", None, "canonical"), (b"\n\n", None, "canonical"),
                                               (b"\n", "0" * 64, "identity differs")):
            with self.subTest(suffix=suffix, sha=expected_sha), tempfile.TemporaryDirectory(prefix="rove-inline-manifest-") as directory:
                root = Path(directory)
                _, raw, archive, _ = self.fixture(root, suffix=suffix)
                error, opened, out, _ = self.load(root, raw, archive, manifest_sha=expected_sha)
                self.assertIsInstance(error, AssertionError)
                self.assertIn(message, str(error))
                self.assertEqual(opened, ["seed.json"])
                self.assertFalse(out.exists())

    def test_total_20000_count_rejects_before_manifest_read(self):
        with tempfile.TemporaryDirectory(prefix="rove-inline-count-") as directory:
            root = Path(directory)
            _, raw, archive, _ = self.fixture(root, payload_count=1)
            error, opened, out, _ = self.load(root, raw, archive, extra_infos=19999)
            self.assertIsInstance(error, AssertionError)
            self.assertIn("excessive ZIP namespace", str(error))
            self.assertEqual(opened, [])
            self.assertFalse(out.exists())

    def test_actual_count_guard_accepts_19999_payload_plus_manifest(self):
        command = campaign.bootstrap_command({"host_job_id": "capacity-check"}, {}, {"source_tree": "source"})
        tree = ast.parse(command.split("<<'ROVE_CLOUD_BOOTSTRAP'\n", 1)[1].rsplit("ROVE_CLOUD_BOOTSTRAP\n", 1)[0])
        guard = next(node for node in ast.walk(tree) if isinstance(node, ast.Assert)
                     and isinstance(node.msg, ast.Constant) and node.msg.value == "duplicate/excessive ZIP namespace")
        code = compile(ast.Module(body=[guard], type_ignores=[]), "<actual-inline-count-guard>", "exec")
        names = ["seed.json"] + ["payload-" + str(index) for index in range(19999)]
        exec(code, {"names": names})
        with self.assertRaisesRegex(AssertionError, "excessive ZIP namespace"):
            exec(code, {"names": names + ["payload-19999"]})
        with self.assertRaisesRegex(AssertionError, "duplicate"):
            exec(code, {"names": names + ["seed.json"]})

    def test_malformed_joint_cohort_stops_before_payload_read(self):
        cases = [(self.JOINT + [self.JOINT[0]], []),
                 (self.JOINT, [{"family": "ice4", "profile": "test-p4"}] * 2),
                 (self.JOINT, [{"family": "ice4", "profile": "test-p400"}])]
        for rove, peers in cases:
            with self.subTest(peers=peers), tempfile.TemporaryDirectory(prefix="rove-inline-cohort-") as directory:
                root = Path(directory)
                _, raw, archive, _ = self.fixture(root, rove=rove, peers=peers)
                error, opened, out, _ = self.load(root, raw, archive)
                self.assertIsInstance(error, ValueError)
                self.assertEqual(opened, ["seed.json"])
                self.assertFalse(out.exists())

    def test_wire_seed_descriptor_keeps_128mib_limit(self):
        selected = plan()
        descriptor = {"bucket": selected.artifact_bucket, "key": selected.campaign_id + "/seed.zip",
                      "version_id": "v1", "sha256": "a" * 64, "bytes": 128 << 20}
        self.assertEqual(campaign.seed_descriptor(descriptor, selected)["bytes"], 128 << 20)
        with self.assertRaisesRegex(ValueError, "bounded"):
            campaign.seed_descriptor({**descriptor, "bytes": (128 << 20) + 1}, selected)

    def assert_manifest_refused_before_payload(self, mutate, message):
        with tempfile.TemporaryDirectory(prefix="rove-inline-member-fault-") as directory:
            root = Path(directory)
            _, raw, archive, _ = self.fixture(root, mutate=mutate)
            error, opened, out, _ = self.load(root, raw, archive)
            self.assertIsInstance(error, AssertionError, repr(error))
            self.assertIn(message, str(error))
            self.assertEqual(opened, ["seed.json"])
            self.assertFalse(out.exists())

    def test_later_oversized_descriptor_precedes_all_payload_reads(self):
        def mutate(manifest):
            manifest["members"]["payload-7"]["bytes"] = (32 << 20) + 1
        self.assert_manifest_refused_before_payload(mutate, "bounded manifest member descriptor")

    def test_declared_aggregate_precedes_all_payload_reads(self):
        def mutate(manifest):
            for descriptor in manifest["members"].values():
                descriptor["bytes"] = 32 << 20
        self.assert_manifest_refused_before_payload(mutate, "declared seed expansion")

    def test_later_zip_length_mismatch_precedes_all_payload_reads(self):
        def mutate(manifest):
            manifest["members"]["payload-7"]["bytes"] += 1
        self.assert_manifest_refused_before_payload(mutate, "ZIP metadata differs")

    def test_manifest_cannot_describe_or_descend_from_reserved_seed_file(self):
        for name, message in (("seed.json", "unsafe manifest member path"),
                              ("seed.json/child", "namespace collision")):
            def mutate(manifest, name=name):
                manifest["members"][name] = {"bytes": 0, "sha256": hashlib.sha256(b"").hexdigest(), "mode": 0o600}
            with self.subTest(name=name):
                self.assert_manifest_refused_before_payload(mutate, message)

    def test_member_container_shape_and_count_precede_all_payload_reads(self):
        for value in (None, [], "members", {}):
            with self.subTest(value=value):
                self.assert_manifest_refused_before_payload(lambda manifest: manifest.update(members=value),
                                                            "explicit bounded member map")
        def excessive(manifest):
            descriptor = {"bytes": 0, "sha256": hashlib.sha256(b"").hexdigest(), "mode": 0o600}
            manifest["members"] = {"member-" + str(index): descriptor for index in range(20000)}
        self.assert_manifest_refused_before_payload(excessive, "explicit bounded member map")

    def test_descriptor_exact_keys_types_and_modes_precede_all_payload_reads(self):
        invalid = [None, [], {"bytes": 0},
                   {"bytes": 0, "sha256": "a" * 64, "mode": 0o600, "extra": False},
                   {"bytes": True, "sha256": "a" * 64, "mode": 0o600},
                   {"bytes": -1, "sha256": "a" * 64, "mode": 0o600},
                   {"bytes": 0, "sha256": "A" * 64, "mode": 0o600},
                   {"bytes": 0, "sha256": int("1" * 64), "mode": 0o600},
                   {"bytes": 0, "sha256": "a" * 64, "mode": 384.0},
                   {"bytes": 0, "sha256": "a" * 64, "mode": 0o777}]
        for descriptor in invalid:
            with self.subTest(descriptor=descriptor):
                self.assert_manifest_refused_before_payload(
                    lambda manifest: manifest["members"].update({"payload-7": descriptor}),
                    "bounded manifest member descriptor")

    def test_member_paths_and_file_directory_collisions_precede_all_payload_reads(self):
        for name, message in (("../escaped", "unsafe manifest member path"),
                              ("a//b", "unsafe manifest member path"),
                              ("a\\b", "unsafe manifest member path"),
                              ("a\0b", "unsafe manifest member path"),
                              ("protected/.env", "protected manifest member path"),
                              ("source", "namespace collision")):
            def mutate(manifest, name=name):
                manifest["members"][name] = {"bytes": 0, "sha256": hashlib.sha256(b"").hexdigest(), "mode": 0o600}
            with self.subTest(name=name):
                self.assert_manifest_refused_before_payload(mutate, message)


if __name__ == "__main__":
    unittest.main()
