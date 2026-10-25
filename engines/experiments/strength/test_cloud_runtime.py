"""Local transport and authority rejection tests; no engines or AWS sessions."""
from dataclasses import dataclass, replace
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
