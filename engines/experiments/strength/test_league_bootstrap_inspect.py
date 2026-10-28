"""Fake S3 to independently pinned bootstrap and same-snapshot inspection."""
from dataclasses import replace
import hashlib
import json
import unittest

try:
    from .league_bootstrap_inspect import inspect_envelope
    from .league_pinned_bootstrap import BootstrapRequest, LoaderPin, fetch_for_verified_loader
    from .test_cloud_runtime import WorkflowBytesFixture, archive_bytes
    from .test_league_pinned_bootstrap import ACCOUNT, BOOT, INSTANCE, PROGRAM, Client
except ImportError:
    from league_bootstrap_inspect import inspect_envelope
    from league_pinned_bootstrap import BootstrapRequest, LoaderPin, fetch_for_verified_loader
    from test_cloud_runtime import WorkflowBytesFixture, archive_bytes
    from test_league_pinned_bootstrap import ACCOUNT, BOOT, INSTANCE, PROGRAM, Client


def fixture():
    f = WorkflowBytesFixture()
    data, manifest_sha = archive_bytes(f.seed, f.files)
    loader = f.seed['source_tree'] + '/engines/experiments/strength/cloud_runtime.py'
    source = f.files[loader]
    origin = f.seed['source_origin']
    request = BootstrapRequest(campaign='league-test', plan_sha256='b' * 64,
        bucket='league-campaign-bucket', bucket_region='ap-southeast-2', bucket_owner=ACCOUNT,
        key='league-test/seed/archive.zip', version_id='immutable-version',
        archive_sha256=hashlib.sha256(data).hexdigest(), archive_bytes=len(data),
        manifest_sha256=manifest_sha, repository=origin['repository'], source_head=origin['head_sha'],
        producer_run_id=origin['run_id'], producer_run_attempt=origin['run_attempt'], host_account=ACCOUNT,
        host_region='ap-southeast-1', host_instance_id=INSTANCE, host_boot_id=BOOT,
        host_launch_token='second-host-token', profile='test-p16',
        host_role_arn=f'arn:aws:iam::{ACCOUNT}:role/team/league-host',
        caller_arn=f'arn:aws:sts::{ACCOUNT}:assumed-role/league-host/{INSTANCE}',
        transfer_quote_id='quote-for-regions', quote_observed_at=1700000000,
        bootstrap_sha256=hashlib.sha256(PROGRAM).hexdigest(),
        loader_pins=(LoaderPin(loader, hashlib.sha256(source).hexdigest(), len(source)),))
    return request, data


class BootstrapInspectTests(unittest.TestCase):
    def test_checked_loader_and_complete_archive_share_exact_snapshot(self):
        request, data = fixture()
        client = Client(data)
        envelope = fetch_for_verified_loader(request, client, bootstrap_source=PROGRAM)
        snapshot, result = inspect_envelope(request, envelope, bootstrap_source=PROGRAM)
        self.assertIs(snapshot, envelope.archive)
        self.assertEqual(snapshot, data)
        self.assertTrue(result['scope']['all_seed_members_checked'])
        self.assertTrue(result['scope']['workflow_proof_checked'])
        for key in ('actual_s3_access_authenticated', 'complete_loader_closure_verified',
                    'running_bootstrap_authenticated', 'host_authenticated',
                    'producer_authenticated', 'aws_cost_confirmed', 'materialized',
                    'runtime_qualified', 'go_authorized'):
            self.assertFalse(result['scope'][key])

    def test_archive_loader_receipt_and_independent_request_changes_rejected(self):
        request, data = fixture()
        envelope = fetch_for_verified_loader(request, Client(data), bootstrap_source=PROGRAM)
        receipt = envelope.receipt
        receipt['version_id'] = 'forged'
        forged_receipt = json.dumps(receipt).encode()
        cases = (
            (request, replace(envelope, archive=b'forged'), PROGRAM),
            (request, replace(envelope, loader_sources=((request.loader_pins[0].name, b'forged'),)), PROGRAM),
            (request, replace(envelope, receipt_json=forged_receipt), PROGRAM),
            (replace(request, version_id='different'), envelope, PROGRAM),
            (replace(request, host_boot_id='12345678-1234-1234-1234-123456789abd'), envelope, PROGRAM),
            (request, envelope, b'wrong bootstrap'),
        )
        for independent, candidate, program in cases:
            with self.subTest(candidate=type(candidate).__name__), self.assertRaises(ValueError):
                inspect_envelope(independent, candidate, bootstrap_source=program)

    def test_bad_seed_proof_is_never_accepted_by_bootstrap_inspector(self):
        request, data = fixture()
        envelope = fetch_for_verified_loader(request, Client(data), bootstrap_source=PROGRAM)
        # An independently wrong source/manifest declaration is refused even if
        # the dataclass and receipt were both rewritten to agree with each other.
        impostor = replace(request, manifest_sha256='a' * 64)
        receipt = envelope.receipt
        receipt['manifest_sha256'] = impostor.manifest_sha256
        forged = replace(envelope, receipt_json=json.dumps(receipt).encode())
        with self.assertRaises(ValueError):
            inspect_envelope(impostor, forged, bootstrap_source=PROGRAM)


if __name__ == '__main__':
    unittest.main()
