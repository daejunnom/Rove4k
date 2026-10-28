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
              'profile', 'artifact', 'out', 'wall_seconds'}
    if type(expected) is not dict or set(expected) != fields:
        raise ValueError('exact expected diagnostic identity required')
    fixed = dict(expected)
    for key in ('state_dir', 'root', 'candidates', 'out'):
        _absolute(fixed[key])
    for key in ('campaign', 'artifact'):
        if not isinstance(fixed[key], str) or not _ID.fullmatch(fixed[key]):
            raise ValueError('invalid diagnostic identifier')
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
        if (set(envelope) != {'format', 'request_sha256', 'result'} or
                envelope.get('format') != 'rove4k-ssm-functional-v1' or
                envelope.get('request_sha256') != dispatch_sha256 or type(envelope.get('result')) is not dict):
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
        expected_request = {key: value for key, value in fixed.items() if key != 'state_dir'}
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
                body.get('complete') is not True or body.get('scored_game_admitted') is not False):
            return dict(result, reason='report_identity_mismatch')
        return dict(result, state='verified_diagnostic_receipt', reason=None,
                    attempt=receipt['attempt'], request_sha256=receipt['request_sha256'],
                    report_sha256=report['sha256'], report_bytes=report['bytes'])
    except Exception:
        # Includes missing/eventually-consistent invocations and uncertain
        # remote file reads. Never retry or infer an outcome here.
        return dict(result, reason='observation_or_parse_uncertain')
