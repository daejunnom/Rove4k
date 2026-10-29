"""Bounded read-only SSM diagnostic receipt observation.

The caller supplies an already bound invocation and a separately established
reader for host files. Neither SSM success, file hashes, nor this module prove
host identity, exclusive ownership, process settlement, or scored-game GO.
No command is sent or retried here; any ambiguous observation is unresolved.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import PurePosixPath
import re
import uuid

_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}\Z')
_SHA = re.compile(r'[0-9a-f]{64}\Z')
_ATTEMPT = re.compile(r'[0-9a-f]{32}\Z')
_COMMAND = re.compile(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\Z')
_INSTANCE = re.compile(r'i-(?:[0-9a-f]{8}|[0-9a-f]{17})\Z')
_MAX_STDOUT = 24000  # SSM truncates at this boundary; reject boundary itself.
_MAX_REPORT = 16 << 20
_MAX_REQUEST = 1 << 16


def _absolute(value):
    if not isinstance(value, str) or not value or '\x00' in value or '\\' in value:
        raise ValueError('absolute POSIX path required')
    path = PurePosixPath(value)
    if not path.is_absolute() or '..' in path.parts or str(path) != value or value == '/':
        raise ValueError('normalized non-root POSIX path required')
    return value


def _unique_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('duplicate JSON key')
        value[key] = item
    return value


def _object(data):
    value = json.loads(data, object_pairs_hook=_unique_pairs,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
    if type(value) is not dict:
        raise ValueError('JSON object required')
    return value


def _validate_expected(expected):
    fields = {'state_dir', 'root', 'campaign', 'candidates', 'candidates_sha256',
              'profile', 'artifact', 'out', 'wall_seconds', 'boot_id'}
    if type(expected) is not dict or set(expected) != fields:
        raise ValueError('exact expected diagnostic identity required')
    fixed = dict(expected)
    for key in ('state_dir', 'root', 'candidates', 'out'):
        _absolute(fixed[key])
    for key in ('campaign', 'artifact'):
        if not isinstance(fixed[key], str) or not _ID.fullmatch(fixed[key]):
            raise ValueError('invalid diagnostic identifier')
    if (not isinstance(fixed['boot_id'], str) or
            str(uuid.UUID(fixed['boot_id'])) != fixed['boot_id'] or uuid.UUID(fixed['boot_id']).int == 0):
        raise ValueError('canonical expected boot UUID required')
    if (not isinstance(fixed['candidates_sha256'], str) or
            not _SHA.fullmatch(fixed['candidates_sha256']) or
            fixed['profile'] not in ('test-p16', 'test-p192') or
            type(fixed['wall_seconds']) is not int or not 90 <= fixed['wall_seconds'] <= 300):
        raise ValueError('invalid diagnostic pin, profile or wall time')
    return fixed


def observe(client, command_id, instance_id, *, dispatch_sha256, expected, read_file):
    """Read one SSM invocation and verify separately fetched request/report bytes.

    ``read_file(path, max_bytes)`` must return bytes from the caller's chosen
    host-file transport. This API does not authenticate that transport. The
    paths and expected input identity are fixed before observing stdout. A
    successful return is a diagnostic receipt, not a host or scoring authority.
    The reported boot ID is bound to the caller's expectation but remains a
    value reported by the unauthenticated remote process.
    """
    if (not isinstance(command_id, str) or not _COMMAND.fullmatch(command_id) or
            not isinstance(instance_id, str) or not _INSTANCE.fullmatch(instance_id) or
            not isinstance(dispatch_sha256, str) or not _SHA.fullmatch(dispatch_sha256) or
            not callable(read_file)):
        raise ValueError('bound command, instance and host-file reader required')
    fixed = _validate_expected(expected)
    result = {'state': 'unresolved', 'command_id': command_id, 'instance_id': instance_id,
              'authorizes_go': False, 'host_authenticated': False,
              'process_settlement_proven': False}
    try:
        invocation = client.call('ssm', 'get-command-invocation',
                                 {'CommandId': command_id, 'InstanceId': instance_id})
        if (type(invocation) is not dict or invocation.get('CommandId') != command_id or
                invocation.get('InstanceId') != instance_id or invocation.get('Status') != 'Success' or
                (invocation.get('StatusDetails') is not None and invocation['StatusDetails'] != 'Success') or
                type(invocation.get('ResponseCode')) is not int or invocation['ResponseCode'] != 0):
            return dict(result, reason='invocation_not_confirmed')
        stdout = invocation.get('StandardOutputContent')
        if not isinstance(stdout, str) or not 0 < len(stdout) < _MAX_STDOUT:
            return dict(result, reason='stdout_missing_or_possibly_truncated')
        envelope = _object(stdout)
        if (set(envelope) != {'format', 'request_sha256', 'observed_boot_id', 'result'} or
                envelope.get('format') != 'rove4k-ssm-functional-v2' or
                envelope.get('request_sha256') != dispatch_sha256 or
                envelope.get('observed_boot_id') != fixed['boot_id'] or type(envelope.get('result')) is not dict):
            return dict(result, reason='dispatch_identity_mismatch')
        receipt = envelope['result']
        if (set(receipt) != {'format', 'attempt', 'request_sha256', 'status', 'report', 'error',
                             'cleanup_errors', 'scored_game_admitted', 'limitations'} or
                receipt.get('format') != 'rove4k-functional-host-result-v1' or
                receipt.get('status') != 'complete' or receipt.get('scored_game_admitted') is not False or
                receipt.get('error') is not None or receipt.get('cleanup_errors') != [] or
                not isinstance(receipt.get('attempt'), str) or not _ATTEMPT.fullmatch(receipt['attempt']) or
                not isinstance(receipt.get('request_sha256'), str) or not _SHA.fullmatch(receipt['request_sha256'])):
            return dict(result, reason='host_receipt_not_complete')
        report = receipt.get('report')
        report_path = str(PurePosixPath(fixed['out']) / 'functional-runtime.json')
        if (type(report) is not dict or set(report) != {'path', 'sha256', 'bytes'} or
                report.get('path') != report_path or not isinstance(report.get('sha256'), str) or
                not _SHA.fullmatch(report['sha256']) or type(report.get('bytes')) is not int or
                not 0 < report['bytes'] <= _MAX_REPORT):
            return dict(result, reason='report_descriptor_invalid')
        request_path = str(PurePosixPath(fixed['state_dir']) / receipt['attempt'] / 'request.json')
        request_bytes = read_file(request_path, _MAX_REQUEST)
        if (type(request_bytes) is not bytes or not 0 < len(request_bytes) <= _MAX_REQUEST or
                hashlib.sha256(request_bytes).hexdigest() != receipt['request_sha256']):
            return dict(result, reason='request_bytes_unverified')
        request = _object(request_bytes)
        expected_request = {key: value for key, value in fixed.items() if key not in ('state_dir', 'boot_id')}
        if (set(request) != set(expected_request) | {'format', 'attempt', 'pid', 'scored_game_admitted'} or
                any(request.get(key) != value for key, value in expected_request.items()) or
                request.get('format') != 'rove4k-functional-host-request-v1' or
                request.get('attempt') != receipt['attempt'] or request.get('scored_game_admitted') is not False or
                type(request.get('pid')) is not int or request['pid'] <= 0):
            return dict(result, reason='request_identity_mismatch')
        report_bytes = read_file(report_path, _MAX_REPORT)
        if (type(report_bytes) is not bytes or len(report_bytes) != report['bytes'] or
                hashlib.sha256(report_bytes).hexdigest() != report['sha256']):
            return dict(result, reason='report_bytes_unverified')
        body = _object(report_bytes)
        if (body.get('format') != 'rove4k-functional-candidate-v1' or
                body.get('profile') != fixed['profile'] or body.get('artifact_id') != fixed['artifact'] or
                body.get('candidate_set_sha256') != fixed['candidates_sha256'] or
                body.get('boot_id') != fixed['boot_id'] or body.get('complete') is not True or
                body.get('scored_game_admitted') is not False):
            return dict(result, reason='report_identity_mismatch')
        return dict(result, state='verified_diagnostic_receipt', reason=None,
                    attempt=receipt['attempt'], request_sha256=receipt['request_sha256'],
                    report_sha256=report['sha256'], report_bytes=report['bytes'],
                    observed_boot_id=fixed['boot_id'])
    except Exception:
        # Includes missing/eventually-consistent invocations and uncertain
        # remote file reads. Never retry or infer an outcome here.
        return dict(result, reason='observation_or_parse_uncertain')


def observe_peer(client, command_id, instance_id, *, dispatch_sha256, expected, read_file):
    """Observe a host-produced peer candidate and its functional receipt.

    The candidate does not exist until the remote peer build and native
    reference finish. Fixed caller-supplied directories, profile and seed pin
    constrain the dynamic descriptors; file bytes are fetched independently
    from the supplied reader. This is consistency checking only: the reader,
    remote host, seed producer, upstream provenance and process settlement are
    not authenticated, and the result grants neither GO nor score admission.
    """
    fields = {'state_dir', 'root', 'campaign', 'preparation_dir', 'profile', 'family',
              'out', 'wall_seconds', 'boot_id', 'seed_manifest_sha256', 'upstream_repository', 'upstream_revision'}
    if type(expected) is not dict or set(expected) != fields:
        raise ValueError('exact expected peer diagnostic identity required')
    fixed = dict(expected)
    preparation = PurePosixPath(_absolute(fixed['preparation_dir']))
    if (fixed['family'] not in ('ice4', 'c4ke') or
            not isinstance(fixed['upstream_repository'], str) or
            not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', fixed['upstream_repository']) or
            not isinstance(fixed['upstream_revision'], str) or not re.fullmatch(r'[0-9a-f]{40}', fixed['upstream_revision']) or
            not isinstance(fixed['seed_manifest_sha256'], str) or not _SHA.fullmatch(fixed['seed_manifest_sha256'])):
        raise ValueError('explicit peer family and seed manifest hash required')
    # Reuse existing input validation without treating these placeholders as
    # candidate evidence: the actual dynamic fields are validated below.
    _validate_expected({**{k: fixed[k] for k in ('state_dir', 'root', 'campaign', 'profile', 'out', 'wall_seconds', 'boot_id')},
                        'candidates': str(preparation / 'candidate.json'), 'candidates_sha256': '0' * 64,
                        'artifact': 'pending'})
    if (not isinstance(command_id, str) or not _COMMAND.fullmatch(command_id) or
            not isinstance(instance_id, str) or not _INSTANCE.fullmatch(instance_id) or
            not isinstance(dispatch_sha256, str) or not _SHA.fullmatch(dispatch_sha256) or
            not callable(read_file)):
        raise ValueError('bound command, instance and host-file reader required')
    unresolved = {'state': 'unresolved', 'command_id': command_id, 'instance_id': instance_id,
                  'authorizes_go': False, 'host_authenticated': False, 'process_settlement_proven': False}
    try:
        invocation = client.call('ssm', 'get-command-invocation',
                                 {'CommandId': command_id, 'InstanceId': instance_id})
        if (type(invocation) is not dict or invocation.get('CommandId') != command_id or
                invocation.get('InstanceId') != instance_id or invocation.get('Status') != 'Success' or
                (invocation.get('StatusDetails') is not None and invocation['StatusDetails'] != 'Success') or
                type(invocation.get('ResponseCode')) is not int or invocation['ResponseCode'] != 0):
            return dict(unresolved, reason='invocation_not_confirmed')
        stdout = invocation.get('StandardOutputContent')
        if not isinstance(stdout, str) or not 0 < len(stdout) < _MAX_STDOUT:
            return dict(unresolved, reason='stdout_missing_or_possibly_truncated')
        envelope = _object(stdout)
        if (set(envelope) != {'format', 'request_sha256', 'observed_boot_id', 'preparation', 'result'} or
                envelope.get('format') != 'rove4k-ssm-peer-functional-v1' or
                envelope.get('request_sha256') != dispatch_sha256 or envelope.get('observed_boot_id') != fixed['boot_id']):
            return dict(unresolved, reason='dispatch_identity_mismatch')
        prep = envelope.get('preparation')
        if (type(prep) is not dict or set(prep) != {'format', 'seed_sha256', 'family', 'profile', 'artifact_id', 'candidate', 'build', 'reference', 'scope'} or
                prep.get('format') != 'rove4k-peer-diagnostic-preparation-v1' or
                prep.get('seed_sha256') != fixed['seed_manifest_sha256'] or prep.get('family') != fixed['family'] or
                prep.get('profile') != fixed['profile'] or prep.get('scope') != 'host source/whole/native preparation only; no engine execution or admission' or
                not isinstance(prep.get('artifact_id'), str) or not _ID.fullmatch(prep['artifact_id'])):
            return dict(unresolved, reason='preparation_identity_mismatch')
        descriptors = {'candidate': preparation / 'candidate.json', 'build': preparation / 'peer-build' / 'peer.json',
                       'reference': preparation / 'peer-reference' / 'reference.json'}
        values = {}
        for role, path in descriptors.items():
            pin = prep.get(role)
            if (type(pin) is not dict or set(pin) != {'path', 'bytes', 'sha256'} or pin.get('path') != str(path) or
                    type(pin.get('bytes')) is not int or not 0 < pin['bytes'] <= _MAX_REPORT or
                    not isinstance(pin.get('sha256'), str) or not _SHA.fullmatch(pin['sha256'])):
                return dict(unresolved, reason='preparation_descriptor_invalid')
            raw = read_file(str(path), _MAX_REPORT)
            if type(raw) is not bytes or len(raw) != pin['bytes'] or hashlib.sha256(raw).hexdigest() != pin['sha256']:
                return dict(unresolved, reason='preparation_bytes_unverified')
            values[role] = _object(raw)
        candidate_set, build, reference = (values[k] for k in ('candidate', 'build', 'reference'))
        if (set(candidate_set) != {'format', 'profile', 'candidates'} or
                candidate_set.get('format') != 'rove4k-diagnostic-candidate-set-v1' or
                candidate_set.get('profile') != fixed['profile'] or type(candidate_set.get('candidates')) is not list or
                len(candidate_set['candidates']) != 1 or type(candidate_set['candidates'][0]) is not dict):
            return dict(unresolved, reason='candidate_identity_mismatch')
        row = candidate_set['candidates'][0]
        artifact = row.get('artifact')
        if (set(row) != {'artifact', 'source', 'native', 'evidence'} or type(artifact) is not dict or
                artifact.get('family') != fixed['family'] or artifact.get('profile') != fixed['profile'] or
                artifact.get('id') != prep['artifact_id'] or artifact.get('purpose') != 'test' or
                artifact.get('representation') != 'source-jit' or artifact.get('full') is not True or
                artifact.get('workers') != {'test-p16': 16, 'test-p192': 192}[fixed['profile']] or
                artifact.get('tt_bytes') != {'test-p16': 16 << 30, 'test-p192': 128 << 30}[fixed['profile']] or
                artifact.get('entry_bytes') != 8 or type(artifact.get('whole_bytes')) is not int or
                not 0 < artifact['whole_bytes'] <= 4096 or
                not isinstance(artifact.get('sha256'), str) or not _SHA.fullmatch(artifact['sha256']) or
                not isinstance(artifact.get('native_sha256'), str) or not _SHA.fullmatch(artifact['native_sha256'])):
            return dict(unresolved, reason='candidate_identity_mismatch')
        name = {'ice4': 'ice4-tcec', 'c4ke': 'c4ke-tcec'}[fixed['family']]
        whole_path = str(preparation / 'peer-build' / 'attempt-1' / name)
        source_path = str(preparation / 'peer-reference' / 'main.cpp')
        native_path = str(preparation / 'peer-reference' / 'reference-1')
        if (artifact.get('path') != whole_path or
                prep['artifact_id'] != f'{fixed["family"]}-{fixed["profile"]}-{artifact["sha256"][:8]}-{artifact["native_sha256"][:8]}' or
                row.get('evidence') != {'kind': 'peer-reference-v1', 'build': prep['build'], 'reference': prep['reference']}):
            return dict(unresolved, reason='candidate_identity_mismatch')
        for role, path in (('source', source_path), ('native', native_path)):
            pin = row.get(role)
            if (type(pin) is not dict or set(pin) != {'path', 'bytes', 'sha256'} or pin.get('path') != path or
                    type(pin.get('bytes')) is not int or not 0 < pin['bytes'] <= 256 << 20 or
                    not isinstance(pin.get('sha256'), str) or not _SHA.fullmatch(pin['sha256'])):
                return dict(unresolved, reason='candidate_identity_mismatch')
        native = reference.get('native')
        build_whole = build.get('whole')
        attempts = build.get('attempts')
        bits = {'test-p16': 31, 'test-p192': 34}[fixed['profile']]
        layout = {'id': fixed['profile'], 'purpose': 'test', 'workers': artifact['workers'],
                  'entry_bytes': 8, 'tt_bits': bits, 'tt_entries': 1 << bits,
                  'tt_bytes': artifact['tt_bytes'], 'tt_shift': 64 - bits}
        if (build.get('peer') != fixed['family'] or build.get('artifact_kind') != 'resource-tiny' or
                build.get('revision') != fixed['upstream_revision'] or
                build.get('source_url') != 'https://github.com/' + fixed['upstream_repository'] + '/tree/' + fixed['upstream_revision'] or
                build.get('complete') is not True or build.get('reproducible') is not True or
                build.get('resources') != layout or
                type(build_whole) is not dict or {k: build_whole.get(k) for k in ('path', 'bytes', 'sha256')} !=
                    {'path': whole_path, 'bytes': artifact['whole_bytes'], 'sha256': artifact['sha256']} or
                type(attempts) is not list or len(attempts) != 2 or
                reference.get('format') != 'rove4k-peer-reference-v1' or reference.get('complete') is not True or
                reference.get('engines_executed') != 0 or reference.get('entry_size_compile_assertion') is not True or
                reference.get('peer') != fixed['family'] or
                reference.get('resources') != build['resources'] or
                reference.get('build') != {'path': str(descriptors['build']), 'sha256': prep['build']['sha256']} or
                reference.get('source') != {k: row['source'][k] for k in ('bytes', 'sha256')} or
                type(native) is not dict or {k: native.get(k) for k in ('path', 'bytes', 'sha256')} != row['native'] or
                native.get('sha256') != artifact['native_sha256']):
            return dict(unresolved, reason='build_reference_identity_mismatch')
        for index, attempt in enumerate(attempts, 1):
            if (type(attempt) is not dict or attempt.get('source') != {k: row['source'][k] for k in ('bytes', 'sha256')} or
                    attempt.get('whole') != {'path': str(preparation / 'peer-build' / ('attempt-' + str(index)) / name),
                                             'bytes': artifact['whole_bytes'], 'sha256': artifact['sha256']}):
                return dict(unresolved, reason='build_reference_identity_mismatch')
        natives = reference.get('native_attempts')
        if type(natives) is not list or len(natives) != 3:
            return dict(unresolved, reason='build_reference_identity_mismatch')
        for index, attempt in enumerate(natives, 1):
            if (type(attempt) is not dict or attempt.get('path') != str(preparation / 'peer-reference' / ('reference-' + str(index))) or
                    attempt.get('bytes') != row['native']['bytes'] or attempt.get('sha256') != artifact['native_sha256'] or
                    attempt.get('layout_assertion') is not (index == 3)):
                return dict(unresolved, reason='build_reference_identity_mismatch')
        # Delegate existing host request/report verification to observe using
        # the already-read immutable invocation; this does not query SSM again.
        class _Invocation:
            def call(self, service, operation, request):
                copy = dict(invocation)
                copy['StandardOutputContent'] = json.dumps({'format': 'rove4k-ssm-functional-v2',
                    'request_sha256': dispatch_sha256, 'observed_boot_id': fixed['boot_id'],
                    'result': envelope['result']}, separators=(',', ':'))
                return copy
        identity = {**{k: fixed[k] for k in ('state_dir', 'root', 'campaign', 'profile', 'out', 'wall_seconds', 'boot_id')},
                    'candidates': str(descriptors['candidate']), 'candidates_sha256': prep['candidate']['sha256'],
                    'artifact': prep['artifact_id']}
        captured = {}
        report_path = str(PurePosixPath(fixed['out']) / 'functional-runtime.json')
        def capture_report(path, maximum):
            data = read_file(path, maximum)
            if path == report_path:
                captured['report'] = data
            return data
        result = observe(_Invocation(), command_id, instance_id, dispatch_sha256=dispatch_sha256,
                         expected=identity, read_file=capture_report)
        if result['state'] == 'verified_diagnostic_receipt':
            report = _object(captured['report'])
            evidence = {'kind': 'peer-reference-v1', 'build_sha256': prep['build']['sha256'],
                        'reference_sha256': prep['reference']['sha256'], 'source_contract_verified': True,
                        'native_reference_files_replay_verified': True}
            if (report.get('family') != fixed['family'] or report.get('whole_sha256') != artifact['sha256'] or
                    report.get('native_sha256') != artifact['native_sha256'] or report.get('source_evidence') != evidence or
                    report.get('workers') != artifact['workers'] or report.get('tt_bytes') != artifact['tt_bytes'] or
                    report.get('source_sha256') != row['source']['sha256']):
                return dict(unresolved, reason='report_identity_mismatch')
            result.update(peer_family=fixed['family'], seed_manifest_sha256=fixed['seed_manifest_sha256'],
                          candidate_sha256=prep['candidate']['sha256'], build_sha256=prep['build']['sha256'],
                          reference_sha256=prep['reference']['sha256'])
        return result
    except Exception:
        return dict(unresolved, reason='observation_or_parse_uncertain')
