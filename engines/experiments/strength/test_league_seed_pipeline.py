"""End-to-end mock transfer into a pinned in-memory archive snapshot."""
from dataclasses import replace
import hashlib
import io
import os
from pathlib import Path
import tempfile
import unittest

try:
    from .league_seed_pipeline import SeedPreparationError, stage_and_inspect
    from .test_cloud_runtime import WorkflowBytesFixture, archive_bytes, seed_fixture
    from .test_league_seed_transfer import Client, spec
except ImportError:
    from league_seed_pipeline import SeedPreparationError, stage_and_inspect
    from test_cloud_runtime import WorkflowBytesFixture, archive_bytes, seed_fixture
    from test_league_seed_transfer import Client, spec


def transfer_spec_for(raw, manifest_sha, origin):
    base = spec()
    request = replace(base.request, seed_archive_bytes=len(raw),
                      seed_archive_sha256=hashlib.sha256(raw).hexdigest(),
                      seed_manifest_sha256=manifest_sha, source_head=origin['head_sha'],
                      producer_run_id=origin['run_id'], producer_run_attempt=origin['run_attempt'])
    return replace(base, request=request)


@unittest.skipUnless(os.name == 'posix' and hasattr(os, 'pread') and hasattr(os, 'pwrite')
                     and hasattr(os, 'O_NOFOLLOW'), 'POSIX staging required')
class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'private-stage'
        self.root.mkdir(mode=0o700)
        os.chmod(self.root, 0o700)

    def tearDown(self):
        self.temp.cleanup()

    def test_fake_cross_region_transfer_and_same_snapshot_workflow_verification(self):
        fixture = WorkflowBytesFixture()
        raw, manifest_sha = archive_bytes(fixture.seed, fixture.files)
        request = transfer_spec_for(raw, manifest_sha, fixture.seed['source_origin'])
        client = Client(data=raw)
        result = stage_and_inspect(request, client, self.root)
        try:
            self.assertEqual(result.snapshot, raw)
            self.assertEqual(result.inspection['archive_sha256'], hashlib.sha256(raw).hexdigest())
            self.assertTrue(result.inspection['scope']['workflow_proof_checked'])
            self.assertFalse(result.inspection['scope']['host_authenticated'])
            self.assertFalse(result.inspection['scope']['materialized'])
            self.assertFalse(result.inspection['scope']['go_authorized'])
            self.assertFalse(result.transfer['scope']['aws_cost_confirmed'])
            self.assertEqual(result.transfer['request']['region'], 'ap-southeast-1')
            self.assertEqual(result.transfer['bucket_region'], 'ap-southeast-2')
            self.assertEqual(client.calls[0]['ExpectedBucketOwner'], request.plan.account)
            self.assertEqual(client.calls[0]['VersionId'], request.request.seed_version_id)
            with self.assertRaises((AttributeError, TypeError)):
                result.snapshot = b'different'
            with self.assertRaises(ValueError):
                replace(result, _snapshot=b'forged')
            independently_checked, inspection = result.verify_for(request)
            self.assertEqual(independently_checked, raw)
            self.assertTrue(inspection['scope']['workflow_proof_checked'])
            forged = b'forged'
            impostor = replace(result, _snapshot=forged, _bytes=len(forged),
                               _sha256=hashlib.sha256(forged).hexdigest(),
                               _inspection_json=b'{"scope":{"go_authorized":true}}')
            with self.assertRaises(ValueError):
                impostor.verify_for(request)
            for updated in (replace(request.request, seed_version_id='other-version'),
                            replace(request.request, boot_id='12345678-1234-1234-1234-123456789abd')):
                with self.assertRaises(ValueError):
                    result.verify_for(replace(request, request=updated))
            with self.assertRaises(ValueError):
                result.verify_for(replace(request, quote=replace(request.quote, quote_id='other-quote')))
            detached = result.inspection
            detached['scope']['go_authorized'] = True
            self.assertFalse(result.inspection['scope']['go_authorized'])
            detached_transfer = result.transfer
            detached_transfer['scope']['host_authenticated'] = True
            self.assertFalse(result.transfer['scope']['host_authenticated'])
        finally:
            result.close()
        self.assertTrue(result.quarantine_path.is_file())

    def test_legacy_seed_without_workflow_proof_is_preserved_but_not_accepted(self):
        seed, files = seed_fixture()
        raw, manifest_sha = archive_bytes(seed, files)
        request = transfer_spec_for(raw, manifest_sha, seed['source_origin'])
        with self.assertRaises(SeedPreparationError) as captured:
            stage_and_inspect(request, Client(data=raw), self.root)
        error = captured.exception
        self.assertFalse(error.path_verified)
        self.assertFalse(error.actual_cost_known)
        self.assertEqual(error.candidate.read_bytes(), raw)

    def test_bad_s3_version_never_accepts_archive_and_preserves_stage(self):
        fixture = WorkflowBytesFixture()
        raw, manifest_sha = archive_bytes(fixture.seed, fixture.files)
        request = transfer_spec_for(raw, manifest_sha, fixture.seed['source_origin'])
        client = Client(data=raw, version='other')
        with self.assertRaises(SeedPreparationError) as captured:
            stage_and_inspect(request, client, self.root)
        self.assertTrue(client.body.closed)
        self.assertEqual(captured.exception.candidate.read_bytes(), b'')

    def test_source_origin_mismatch_preserves_stage_without_acceptance(self):
        fixture = WorkflowBytesFixture()
        raw, manifest_sha = archive_bytes(fixture.seed, fixture.files)
        request = transfer_spec_for(raw, manifest_sha, fixture.seed['source_origin'])
        request = replace(request, request=replace(request.request, source_head='f' * 40))
        with self.assertRaises(SeedPreparationError) as captured:
            stage_and_inspect(request, Client(data=raw), self.root)
        self.assertEqual(captured.exception.candidate.read_bytes(), raw)

    def test_cancel_preserves_original_exception_and_marks_uncertain_cost(self):
        fixture = WorkflowBytesFixture()
        raw, manifest_sha = archive_bytes(fixture.seed, fixture.files)
        request = transfer_spec_for(raw, manifest_sha, fixture.seed['source_origin'])

        class InterruptedBody(io.BytesIO):
            def read(self, count=-1):
                raise KeyboardInterrupt()

        client = Client(data=raw)
        client.body = InterruptedBody(raw)
        with self.assertRaises(KeyboardInterrupt) as captured:
            stage_and_inspect(request, client, self.root)
        self.assertTrue(client.body.closed)
        self.assertEqual(len(list(self.root.iterdir())), 1)
        self.assertTrue(any('actual cost is unknown' in note for note in captured.exception.__notes__))


if __name__ == '__main__':
    unittest.main()
