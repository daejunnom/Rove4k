"""Prepare a pinned Rove diagnostic request from live GitHub source evidence.

This is a read-only controller preparation CLI.  It does not fetch or attest
the named S3 version, authenticate a host or its boot, reserve budget, or send
an SSM command.  The public SSM dispatcher remains closed.  Its receipt is an
observation bound to a request, never a reusable authority or scored GO.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
from pathlib import Path
import zipfile

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from . import league_github_producer as producer, league_ssm_dispatch as ssm, ledger, seed
except ImportError:
    import league_github_producer as producer
    import league_ssm_dispatch as ssm
    import ledger
    import seed


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _request_from_bytes(raw):
    data = producer._json(raw)
    _require(type(data) is dict and data.get('format') == 'rove4k-ssm-functional-request-v2',
             'exact Rove diagnostic request v2 required')
    values = {key: value for key, value in data.items() if key != 'format'}
    try:
        request = ssm.Request(**values)
    except (TypeError, ValueError) as error:
        raise ValueError('invalid exact diagnostic request') from error
    _require(request.record() == data, 'request fields or values differ from the canonical contract')
    return request


def _safe_path(value):
    path = producer._safe_absolute_file(value)
    _require(not any(re.fullmatch(r'id_(rsa|ed25519|dsa|ecdsa)(?:\..*)?', part, re.I)
                     for part in path.parts), 'protected SSH key path')
    return path


def _preflight_archive(archive):
    # Check names without reading contents before the seed archive inspector.
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        entries = bundle.infolist()
        _require(len(entries) <= producer._MAX_FILES, 'too many seed archive members')
        for entry in entries:
            name = producer._safe_name(entry.filename, directory=entry.is_dir())
            _require(not any(re.fullmatch(r'id_(rsa|ed25519|dsa|ecdsa)(?:\..*)?', part, re.I)
                             for part in name.split('/')), 'protected SSH key member')


def prepare(request, *, expected_request_sha256, expected_boot_id, expected_pr,
            archive_path, seed_root, candidate_path, family, variant):
    """Re-observe source provenance and bind it to one immutable request.

    Expected values are caller-supplied pins, not authentication.  The seed
    archive is checked locally; S3 version identity is only a request claim.
    The observer verifies producer ZIP and manifest pins, not candidate files
    on the diagnostic host or the native build's semantics.
    """
    _require(type(request) is ssm.Request, 'validated immutable Rove Request required')
    request_data = request.record()
    request_sha256 = ledger.digest(request_data)
    _require(type(expected_request_sha256) is str and expected_request_sha256 == request_sha256,
             'request digest differs from expected pin')
    _require(type(expected_boot_id) is str and request.boot_id == expected_boot_id,
             'requested boot differs from expected pin')
    _require(type(expected_pr) is int and expected_pr > 0, 'explicit PR number required')

    archive = producer.cloud.ordinary(_safe_path(archive_path), limit=seed.MAX_SEED)
    _require(len(archive) == request.seed_archive_bytes
             and hashlib.sha256(archive).hexdigest() == request.seed_archive_sha256,
             'local seed archive differs from the request pin')
    _preflight_archive(archive)
    archive_observation = seed.inspect_archive(archive)
    _require(archive_observation['manifest_sha256'] == request.seed_manifest_sha256,
             'archive manifest differs from request')
    del archive

    manifest_path = _safe_path(Path(seed_root) / 'seed.json')
    manifest_bytes = producer.cloud.ordinary(manifest_path, limit=producer._MAX_JSON)
    _require(hashlib.sha256(manifest_bytes).hexdigest() == request.seed_manifest_sha256,
             'materialized seed manifest differs from request')
    manifest = producer._json(manifest_bytes)
    proof = manifest.get('workflow_provenance')
    _require(type(proof) is dict and proof.get('kind') == 'pull-request-merge'
             and producer._decimal(proof.get('pull_request')) == expected_pr,
             'seed PR identity differs from expected pin')

    candidate_path = _safe_path(candidate_path)
    observation = producer.observe_github_via_gh(request, seed_root=seed_root,
                  candidate_path=candidate_path, family=family, variant=variant)
    _require(type(observation) is dict
             and observation.get('format') == 'rove4k.github-source-observation-v1'
             and observation.get('repository') == request.repository
             and observation.get('run_id') == int(request.producer_run_id)
             and observation.get('run_attempt') == int(request.producer_run_attempt)
             and observation.get('artifact_id') == int(request.producer_artifact_id)
             and observation.get('source_head') == request.source_head
             and observation.get('profile') == request.profile
             and observation.get('family') == family and observation.get('variant') == variant
             and observation.get('candidate_pins_match') is True
             and all(observation.get(flag) is False for flag in
                     ('candidate_files_observed', 'workflow_commit_reviewed',
                      'host_authenticated', 'runtime_qualified', 'authorizes_go')),
             'GitHub observation differs from exact request or scope')
    # A pushed workflow cannot stand in for the PR snapshot. Re-read the live
    # run and PR/merge at the end so a changed branch cannot be silently used.
    run_path = ('/repos/' + request.repository + '/actions/runs/' + request.producer_run_id
                + '/attempts/' + request.producer_run_attempt)
    latest_run = producer._gh_api_json(run_path)
    _require(type(latest_run) is dict and latest_run.get('event') == 'pull_request'
             and latest_run.get('id') == int(request.producer_run_id)
             and latest_run.get('run_attempt') == int(request.producer_run_attempt)
             and latest_run.get('status') == 'completed' and latest_run.get('conclusion') == 'success'
             and type(latest_run.get('repository')) is dict
             and latest_run['repository'].get('full_name') == request.repository,
             'live PR producer run changed or is not successful')
    producer._live_pr_merge(manifest, latest_run, producer._gh_api_json)
    # Check the request and manifest again after the potentially long API call.
    _require(request.record() == request_data and ledger.digest(request.record()) == request_sha256,
             'request changed during source observation')
    _require(producer.cloud.ordinary(manifest_path, limit=producer._MAX_JSON) == manifest_bytes,
             'materialized seed manifest changed during source observation')
    candidate_bytes = producer.cloud.ordinary(candidate_path, limit=producer._MAX_JSON)
    _require(hashlib.sha256(candidate_bytes).hexdigest() == request.candidates_sha256,
             'candidate manifest changed during source observation')
    command = ssm.command(request)
    return {'format': 'rove4k-ssm-source-preparation-v1', 'request': request_data,
            'request_sha256': request_sha256, 'github_observation': observation,
            'github_observation_sha256': ledger.digest(observation),
            'local_archive_inspected': True, 'expected_pr': expected_pr,
            'command_sha256': hashlib.sha256(command.encode()).hexdigest(),
            'expected_receipt_inputs': ssm.expected_receipt_inputs(request),
            'candidate_files_observed': False, 's3_version_authenticated': False,
            'host_authenticated': False, 'boot_authenticated': False,
            'budget_authenticated': False, 'runtime_qualified': False,
            'authorizes_dispatch': False, 'authorizes_go': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True, help='absolute request v2 JSON path')
    parser.add_argument('--expected-request-sha256', required=True)
    parser.add_argument('--expected-boot-id', required=True)
    parser.add_argument('--expected-pr', required=True, type=int)
    parser.add_argument('--archive', required=True)
    parser.add_argument('--seed-root', required=True)
    parser.add_argument('--candidates', required=True)
    parser.add_argument('--family', required=True, choices=list('ABCEF'))
    parser.add_argument('--variant', required=True)
    args = parser.parse_args(argv)
    request = _request_from_bytes(producer.cloud.ordinary(_safe_path(args.request), limit=producer._MAX_JSON))
    result = prepare(request, expected_request_sha256=args.expected_request_sha256,
        expected_boot_id=args.expected_boot_id, expected_pr=args.expected_pr,
        archive_path=args.archive, seed_root=args.seed_root, candidate_path=args.candidates,
        family=args.family, variant=args.variant)
    sys.stdout.write(json.dumps(result, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
