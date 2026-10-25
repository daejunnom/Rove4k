"""Short local lifecycle fault checks; fake AWS is never deployment evidence."""
from dataclasses import replace
import base64
import copy
import hashlib
import json
import os
import shutil
from pathlib import Path
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
            manifest = {"format": "rove4k-cloud-seed-v1", "source_tree": "source", "members": {
                entry: {"bytes": len(source), "sha256": hashlib.sha256(source).hexdigest(), "mode": 0o600}}}
            manifest_raw = ledger.canonical(manifest)
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


if __name__ == "__main__":
    unittest.main()
