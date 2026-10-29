#!/usr/bin/env python3
"""Explicit campaign AWS ports; planning never creates paid resources.

The CLI exposes plan/template/read-only preflight. The controller calls launch
only after its durable budget event and an independently deployed watchdog.
No static credentials or credential-file discovery are implemented here.
"""
from dataclasses import asdict, dataclass, fields
import base64
from datetime import datetime, timezone
from decimal import Decimal
from email.utils import parsedate_to_datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import urllib.request
import uuid

if __name__ == '__main__' and not __package__:
    # Isolated (-I) operator entry: import only this known sibling tree.
    import sys
    import types
    sys.dont_write_bytecode = True
    _package_name = 'rove4k_aws_operator_source'
    _package_path = str(Path(__file__).resolve().parent)
    _package = sys.modules.setdefault(_package_name, types.ModuleType(_package_name))
    if hasattr(_package, '__path__') and list(_package.__path__) != [_package_path]:
        raise ValueError('operator sibling package belongs to another source tree')
    _package.__path__ = [_package_path]
    __package__ = _package_name

try:
    from .budget import CampaignBudget, decimal, timestamp
except ImportError:
    from budget import CampaignBudget, decimal, timestamp


INSTANCE_TYPE = 'm6a.48xlarge'
STANDARD_SPOT_QUOTA = 'L-34B43A08'
ADVISOR_URL = 'https://spot-bid-advisor.s3.amazonaws.com/spot-advisor-data.json'
ADVISOR_MAX_SOURCE_AGE_SECONDS = 7 * 86400
ACCOUNT_PLAN_REGION = 'us-east-1'
ACCOUNT_PLAN_ENDPOINT = 'https://freetier.us-east-1.api.aws'
GLOBAL_METADATA_REGION = 'us-east-1'
ACCOUNT_INFORMATION_ENDPOINT = 'https://account.us-east-1.amazonaws.com'
ORGANIZATION_INFORMATION_ENDPOINT = 'https://organizations.us-east-1.amazonaws.com'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def iso(epoch):
    return datetime.fromtimestamp(timestamp(epoch), timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


class AwsError(RuntimeError):
    def __init__(self, code, operation):
        super().__init__(operation + ': ' + code)
        self.code, self.operation = code, operation


class AWSCLI:
    """AWS CLI transport for exported OIDC credentials or an EC2 profile.

    Local credential/config files and token-file discovery are disabled. The
    configured GitHub action or EC2 metadata provider owns authentication.
    """
    def __init__(self, region, executable='aws', timeout=30):
        if not re.fullmatch(r'[a-z]{2}(?:-[a-z]+)+-\d', region):
            raise ValueError('explicit commercial AWS region required')
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError('positive finite AWS transport timeout required')
        self.region, self.executable, self.timeout = region, executable, timeout

    def call(self, service, operation, request):
        # File input avoids Windows command length and .cmd JSON quoting. These
        # files contain only this module's explicit non-secret API request.
        with tempfile.TemporaryDirectory(prefix='rove4k-aws-input-') as temporary:
            path = Path(temporary) / 'request.json'
            path.write_text(canonical(request), encoding='utf-8')
            return self._execute(service, operation, ['--cli-input-json', 'file://' + str(path)])

    def account_plan_state(self):
        """Explicit read of global billing state; never a workload fallback.

        AWS lists Free Tier's account-global endpoint only in us-east-1.
        This separate port cannot create resources or upgrade an account.
        """
        reader = AWSCLI(ACCOUNT_PLAN_REGION, executable=self.executable, timeout=self.timeout)
        return reader._execute('freetier', 'get-account-plan-state',
                               ['--endpoint-url', ACCOUNT_PLAN_ENDPOINT])

    def own_account_information(self):
        """Account Management is global; omit AccountId for the caller's account."""
        reader = AWSCLI(GLOBAL_METADATA_REGION, executable=self.executable, timeout=self.timeout)
        return reader._execute('account', 'get-account-information',
                               ['--endpoint-url', ACCOUNT_INFORMATION_ENDPOINT])

    def organization_information(self):
        """Fixed commercial Organizations read/signing endpoint, never fallback."""
        reader = AWSCLI(GLOBAL_METADATA_REGION, executable=self.executable, timeout=self.timeout)
        return reader._execute('organizations', 'describe-organization',
                               ['--endpoint-url', ORGANIZATION_INFORMATION_ENDPOINT])

    def command_prefix(self):
        executable = shutil.which(self.executable) or self.executable
        if os.name == 'nt' and Path(executable).suffix.lower() in ('.cmd', '.bat'):
            scripts = Path(executable).resolve().parent
            for python in (scripts / 'python.exe', scripts.parent / 'python.exe'):
                if python.is_file():
                    return [str(python), '-m', 'awscli']
            raise AwsError('NativeCLIEntryPointUnavailable', 'CLI bootstrap')
        return [executable]

    def put_file(self, bucket, key, path, sha256):
        checksum = base64.b64encode(bytes.fromhex(sha256)).decode('ascii')
        return self._execute('s3api', 'put-object', ['--bucket', bucket, '--key', key,
            '--body', str(path), '--metadata', 'sha256=' + sha256,
            '--checksum-sha256', checksum, '--if-none-match', '*'])

    def put_file_if_match(self, bucket, key, path, sha256, etag, *, expected_owner):
        """Attempt one conditional replacement against an observed strong ETag.

        The return is the unmodified service response. In particular, transport
        timeout is uncertain, and conflicts are not retried or acknowledged as
        successful. Callers own durable reconciliation and VersionId checks.
        """
        if not isinstance(sha256, str) or not re.fullmatch(r'[a-f0-9]{64}', sha256):
            raise ValueError('a lowercase SHA-256 digest is required')
        # S3 ETags are opaque: preserve the observed entity tag verbatim rather
        # than assuming MD5, while rejecting wildcards, weak tags and newlines.
        if not isinstance(etag, str) or not re.fullmatch(r'"[\x21\x23-\x7e]{1,256}"', etag):
            raise ValueError('one observed quoted strong ETag is required')
        if not isinstance(expected_owner, str) or not re.fullmatch(r'[0-9]{12}', expected_owner):
            raise ValueError('expected bucket owner must be an AWS account ID')
        checksum = base64.b64encode(bytes.fromhex(sha256)).decode('ascii')
        return self._execute('s3api', 'put-object', ['--bucket', bucket, '--key', key,
            '--body', str(path), '--metadata', 'sha256=' + sha256,
            '--checksum-sha256', checksum, '--expected-bucket-owner', expected_owner, '--if-match', etag])

    def get_file(self, bucket, key, path, etag, *, expected_owner=None):
        if expected_owner is not None and (not isinstance(expected_owner, str)
                                            or not re.fullmatch(r'[0-9]{12}', expected_owner)):
            raise ValueError('expected bucket owner must be an AWS account ID')
        arguments = ['--bucket', bucket, '--key', key, '--checksum-mode', 'ENABLED', '--if-match', etag]
        if expected_owner is not None:
            arguments.extend(['--expected-bucket-owner', expected_owner])
        return self._execute('s3api', 'get-object', [*arguments, str(path)])

    def _execute(self, service, operation, arguments):
        if not all(re.fullmatch(r'[a-z][a-z0-9-]*', value) for value in (service, operation)):
            raise ValueError('invalid AWS operation')
        command = [*self.command_prefix(), '--region', self.region, '--no-paginate',
                   service, operation, *arguments, '--output', 'json']
        environment = os.environ.copy()
        environment['AWS_PAGER'] = ''
        environment['AWS_CLI_AUTO_PROMPT'] = 'off'
        # In particular SendCommand has no idempotency token. A transport
        # timeout is unresolved; only the lifecycle owner may reconcile it.
        environment['AWS_MAX_ATTEMPTS'] = '1'
        environment['AWS_SHARED_CREDENTIALS_FILE'] = os.devnull
        environment['AWS_CONFIG_FILE'] = os.devnull
        for name in ('AWS_PROFILE', 'AWS_DEFAULT_PROFILE', 'AWS_WEB_IDENTITY_TOKEN_FILE'):
            environment.pop(name, None)
        try:
            result = subprocess.run(command, capture_output=True, timeout=self.timeout, env=environment,
                                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        except FileNotFoundError as error:
            raise AwsError('CLIUnavailable', service + '.' + operation) from error
        except subprocess.TimeoutExpired as error:
            raise AwsError('ObservationTimeout', service + '.' + operation) from error
        if len(result.stdout) > 4 * 1024 * 1024 or len(result.stderr) > 256 * 1024:
            raise AwsError('OutputLimit', service + '.' + operation)
        if result.returncode:
            # Never forward raw auth/HTTP diagnostics, arguments, or environment.
            match = re.search(rb'An error occurred \(([^)]+)\)', result.stderr)
            code = match.group(1).decode('ascii', 'replace') if match else (
                'CredentialsUnavailable' if b'Unable to locate credentials' in result.stderr else 'CLIError')
            raise AwsError(code, service + '.' + operation)
        return json.loads(result.stdout) if result.stdout.strip() else {}


_ADVANCED_TRANSITION = (
    'configured-advanced-member-project', 'daejunnom', 'Rove4k',
    '292341339363', 'o-5bqojfsbnd', '814650855198',
    'user-confirmed-advanced-2026-10-26',
    'd2e6769eee3734f543b252c2fa9bba1e03563bbab022ae7b4689c3c0480913e4')
ADVANCED_PROJECT_REGION = 'ap-southeast-2'


class OperatorReadinessCLI:
    """Explicit local-profile read-only adapter, separate from runtime AWSCLI.

    It delegates authentication to the requested official CLI profile and never
    opens/discovers a credential or config file. There is no arbitrary service
    operation, resource-write method, account switch, or retry path.
    """
    def __init__(self, region, executable, profile, readiness_kind, timeout=30):
        if (region != ADVANCED_PROJECT_REGION or type(profile) is not str or not profile or
                not re.fullmatch(r'[A-Za-z0-9_.-]{1,64}', profile) or
                type(executable) is not str or not Path(executable).is_absolute() or
                readiness_kind not in ('freetier-paid', _ADVANCED_TRANSITION[0]) or
                type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 45):
            raise ValueError('explicit operator region, absolute CLI, profile and readiness selector required')
        self.region, self.executable, self.profile = region, executable, profile
        self.readiness_kind, self.timeout = readiness_kind, timeout

    def call(self, service, operation, request):
        if (type(service) is not str or type(operation) is not str or
                type(request) is not dict or request or
                (service, operation) != ('sts', 'get-caller-identity')):
            raise ValueError('operator adapter permits only explicit readiness reads')
        return self._read(service, operation)

    def account_plan_state(self):
        return self._read('freetier', 'get-account-plan-state')

    def own_account_information(self):
        return self._read('account', 'get-account-information')

    def organization_information(self):
        return self._read('organizations', 'describe-organization')

    def _read(self, service, operation):
        if (service, operation) == ('sts', 'get-caller-identity'):
            region, endpoint = self.region, 'https://sts.' + self.region + '.amazonaws.com'
        elif self.readiness_kind == 'freetier-paid' and (service, operation) == ('freetier', 'get-account-plan-state'):
            region, endpoint = ACCOUNT_PLAN_REGION, ACCOUNT_PLAN_ENDPOINT
        elif self.readiness_kind == _ADVANCED_TRANSITION[0] and (service, operation) == ('account', 'get-account-information'):
            region, endpoint = GLOBAL_METADATA_REGION, ACCOUNT_INFORMATION_ENDPOINT
        elif self.readiness_kind == _ADVANCED_TRANSITION[0] and (service, operation) == ('organizations', 'describe-organization'):
            region, endpoint = GLOBAL_METADATA_REGION, ORGANIZATION_INFORMATION_ENDPOINT
        else:
            raise ValueError('read is outside the explicitly selected operator readiness class')
        command = [self.executable, '--profile', self.profile, '--region', region,
            '--endpoint-url', endpoint, '--no-cli-pager', '--no-cli-auto-prompt', '--no-paginate',
            '--cli-connect-timeout', '5', '--cli-read-timeout', '10', service, operation, '--output', 'json']
        environment = os.environ.copy()
        for name in ('AWS_PROFILE', 'AWS_DEFAULT_PROFILE', 'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY',
                'AWS_SESSION_TOKEN', 'AWS_SECURITY_TOKEN', 'AWS_WEB_IDENTITY_TOKEN_FILE', 'AWS_ROLE_ARN',
                'AWS_CONFIG_FILE', 'AWS_SHARED_CREDENTIALS_FILE',
                'AWS_CONTAINER_CREDENTIALS_RELATIVE_URI', 'AWS_CONTAINER_CREDENTIALS_FULL_URI'):
            environment.pop(name, None)
        environment.update(AWS_PAGER='', AWS_CLI_AUTO_PROMPT='off', AWS_MAX_ATTEMPTS='1',
                           AWS_EC2_METADATA_DISABLED='true')
        try:
            result = subprocess.run(command, capture_output=True, timeout=self.timeout, env=environment,
                                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        except FileNotFoundError as error:
            raise AwsError('CLIUnavailable', service + '.' + operation) from error
        except subprocess.TimeoutExpired as error:
            raise AwsError('ObservationTimeout', service + '.' + operation) from error
        if len(result.stdout) > 4 * 1024 * 1024 or len(result.stderr) > 256 * 1024:
            raise AwsError('OutputLimit', service + '.' + operation)
        if result.returncode:
            match = re.search(rb'An error occurred \(([^)]+)\)', result.stderr)
            raise AwsError(match.group(1).decode('ascii', 'replace') if match else 'CLIError',
                           service + '.' + operation)
        return json.loads(result.stdout) if result.stdout.strip() else {}


@dataclass(frozen=True)
class AdvancedTransitionConfirmation:
    """Identity of the source-reviewed direct-user activation record.

    The external record remains outside Git. Accepting any supplied JSON/hash
    would not establish its authority; only this reviewed reference/pin is
    supported. This is configuration authority, never a billing API response.
    """
    reference: str = _ADVANCED_TRANSITION[6]
    sha256: str = _ADVANCED_TRANSITION[7]

    def __post_init__(self):
        if (type(self.reference) is not str or type(self.sha256) is not str or
                (self.reference, self.sha256) != _ADVANCED_TRANSITION[6:]):
            raise ValueError('Advanced transition confirmation is not source-reviewed')

    @classmethod
    def from_dict(cls, value):
        if type(value) is not dict or set(value) != {'reference', 'sha256'}:
            raise ValueError('exact reviewed Advanced transition confirmation required')
        return cls(**value)


@dataclass(frozen=True)
class AdvancedMemberProjectReadiness:
    """Explicit opt-in for the one reviewed Advanced member-project transition."""
    kind: str = _ADVANCED_TRANSITION[0]
    team: str = _ADVANCED_TRANSITION[1]
    project: str = _ADVANCED_TRANSITION[2]
    project_account_id: str = _ADVANCED_TRANSITION[3]
    organization_id: str = _ADVANCED_TRANSITION[4]
    management_account_id: str = _ADVANCED_TRANSITION[5]
    transition_confirmation: AdvancedTransitionConfirmation = AdvancedTransitionConfirmation()

    def __post_init__(self):
        context = (self.kind, self.team, self.project, self.project_account_id,
                   self.organization_id, self.management_account_id)
        if (any(type(value) is not str for value in context) or
                context != _ADVANCED_TRANSITION[:6] or
                type(self.transition_confirmation) is not AdvancedTransitionConfirmation):
            raise ValueError('Advanced member-project context is not source-reviewed')

    def as_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, value):
        names = {item.name for item in fields(cls)}
        if type(value) is not dict or set(value) != names:
            raise ValueError('exact configured Advanced member-project fields required')
        converted = dict(value)
        converted['transition_confirmation'] = AdvancedTransitionConfirmation.from_dict(
            converted['transition_confirmation'])
        return cls(**converted)


@dataclass(frozen=True)
class AWSPlan:
    campaign_id: str
    account_id: str
    region: str
    owner_nonce: str
    launch_token: str
    ami_id: str
    subnet_id: str
    security_group_id: str
    instance_profile_arn: str
    controller_role_arn: str
    watchdog_stack: str
    ownership_table: str
    schedule_name: str
    watchdog_arn: str
    artifact_bucket: str
    deadline_epoch: int
    root_device_name: str = '/dev/sda1'
    root_volume_gib: int = 32
    max_hourly_usd: str = '8'
    project_region: str | None = None
    account_readiness: AdvancedMemberProjectReadiness | None = None

    def __post_init__(self):
        checks = ((self.campaign_id, r'[a-z][a-z0-9-]{2,39}'),
                  (self.account_id, r'\d{12}'), (self.region, r'[a-z]{2}(?:-[a-z]+)+-\d'),
                  (self.owner_nonce, r'[a-f0-9]{32,64}'),
                  (self.launch_token, r'[A-Za-z0-9_-]{16,64}'),
                  (self.ami_id, r'ami-[a-f0-9]{8,17}'), (self.subnet_id, r'subnet-[a-f0-9]{8,17}'),
                  (self.security_group_id, r'sg-[a-f0-9]{8,17}'))
        if any(not isinstance(value, str) or not re.fullmatch(pattern, value) for value, pattern in checks):
            raise ValueError('invalid explicit campaign/AWS resource identity')
        if (self.project_region is not None and
                (not isinstance(self.project_region, str)
                 or not re.fullmatch(r'[a-z]{2}(?:-[a-z]+)+-\d', self.project_region)
                 or self.region != self.project_region)):
            raise ValueError('workload region must equal the explicitly bound project region; no fallback')
        prefix = 'arn:aws:iam::' + self.account_id + ':'
        if not self.instance_profile_arn.startswith(prefix + 'instance-profile/') or not self.controller_role_arn.startswith(prefix + 'role/'):
            raise ValueError('IAM identities must belong to the campaign account')
        if not self.watchdog_arn.startswith(f'arn:aws:lambda:{self.region}:{self.account_id}:function:'):
            raise ValueError('watchdog must belong to the campaign account/region')
        if not isinstance(self.deadline_epoch, int) or isinstance(self.deadline_epoch, bool) or self.deadline_epoch <= 0:
            raise ValueError('integer UTC termination-trigger epoch required')
        if not 8 <= self.root_volume_gib <= 64 or not self.root_device_name.startswith('/dev/'):
            raise ValueError('bounded explicit root EBS configuration required')
        if not 0 < decimal(self.max_hourly_usd) <= 8:
            raise ValueError('Spot price ceiling exceeds accepted policy')
        if not all(isinstance(value, str) and value for value in (
                self.watchdog_stack, self.ownership_table, self.schedule_name, self.artifact_bucket)):
            raise ValueError('deployed watchdog/storage outputs are required')
        if self.account_readiness is not None:
            if type(self.account_readiness) is not AdvancedMemberProjectReadiness:
                raise ValueError('typed source-reviewed account readiness configuration required')
            if (self.account_id != self.account_readiness.project_account_id or
                    self.region != ADVANCED_PROJECT_REGION or self.project_region != self.region):
                raise ValueError('Advanced readiness must bind the reviewed project account and Sydney region')

    def request(self):
        tags = [{'Key': 'RoveCampaign', 'Value': self.campaign_id},
                {'Key': 'RoveOwner', 'Value': self.owner_nonce}]
        # Backstop for a delayed allocation that becomes visible only after the
        # external deadline worker's retry window. The declared target AMI is
        # Ubuntu/cloud-init with Python3/systemd; target preflight verifies it.
        boot_guard = ("#!/bin/sh\npython3 - <<'ROVE_DEADLINE'\nimport os,time\n"
            f"minutes=max(0,int(({self.deadline_epoch}-time.time())//60))\n"
            "os.execv('/sbin/shutdown',['shutdown','-h','+'+str(minutes)])\nROVE_DEADLINE\n")
        return {'ImageId': self.ami_id, 'InstanceType': INSTANCE_TYPE, 'MinCount': 1, 'MaxCount': 1,
                'ClientToken': self.launch_token,
                'UserData': base64.b64encode(boot_guard.encode()).decode('ascii'),
                'InstanceInitiatedShutdownBehavior': 'terminate',
                'IamInstanceProfile': {'Arn': self.instance_profile_arn},
                'NetworkInterfaces': [{'DeviceIndex': 0, 'SubnetId': self.subnet_id,
                                       'Groups': [self.security_group_id], 'AssociatePublicIpAddress': True,
                                       'DeleteOnTermination': True}],
                'MetadataOptions': {'HttpTokens': 'required', 'HttpEndpoint': 'enabled'},
                'BlockDeviceMappings': [{'DeviceName': self.root_device_name, 'Ebs': {
                    'VolumeSize': self.root_volume_gib, 'VolumeType': 'gp3', 'Encrypted': True,
                    'DeleteOnTermination': True}}],
                'InstanceMarketOptions': {'MarketType': 'spot', 'SpotOptions': {
                    'MaxPrice': self.max_hourly_usd, 'SpotInstanceType': 'one-time',
                    'InstanceInterruptionBehavior': 'terminate'}},
                'TagSpecifications': [{'ResourceType': kind, 'Tags': tags} for kind in ('instance', 'volume')]}

    def intent(self, requested_at):
        requested_at = timestamp(requested_at)
        if not requested_at < self.deadline_epoch <= requested_at + 43200:
            raise ValueError('termination trigger must fall within the cumulative run horizon')
        return {'campaign_id': self.campaign_id, 'account_id': self.account_id,
                'region': self.region, 'owner_nonce': self.owner_nonce,
                'launch_token': self.launch_token, 'requested_at': requested_at,
                'deadline_epoch': self.deadline_epoch, 'instance_type': INSTANCE_TYPE,
                'ami_id': self.ami_id, 'subnet_id': self.subnet_id,
                'instance_profile_arn': self.instance_profile_arn,
                'request_sha256': digest(self.request()),
                **({'project_region': self.project_region} if self.project_region is not None else {})}

    def as_dict(self):
        configured = asdict(self)
        if self.account_readiness is None:
            # Preserve historical configuration bytes and their plan digest.
            del configured['account_readiness']
        return {**configured, 'instance_type': INSTANCE_TYPE, 'request': self.request(),
                'request_sha256': digest(self.request()), 'paid_launch_performed': False,
                'oidc_scope': 'AWS controller role; independent from npm trusted publishing'}

    @classmethod
    def from_dict(cls, value):
        """Load configuration or a plan report, checking derived fields."""
        if not isinstance(value, dict):
            raise ValueError('AWS plan must be a JSON object')
        names = {item.name for item in fields(cls)}
        derived = {'instance_type', 'request', 'request_sha256', 'paid_launch_performed', 'oidc_scope'}
        if set(value) - names - derived:
            raise ValueError('unknown AWS plan fields')
        configured = {key: item for key, item in value.items() if key in names}
        if configured.get('account_readiness') is not None:
            configured['account_readiness'] = AdvancedMemberProjectReadiness.from_dict(
                configured['account_readiness'])
        plan = cls(**configured)
        expected = plan.as_dict()
        if any(value[key] != expected[key] for key in derived & set(value)):
            raise ValueError('derived AWS plan fields differ from their canonical input')
        return plan


def fetch_advisor(region, now=None, opener=urllib.request.urlopen):
    """Fetch the public AWS snapshot; it is a historical band, not capacity."""
    now = time.time() if now is None else timestamp(now)
    with opener(ADVISOR_URL, timeout=20) as response:
        raw = response.read(20 * 1024 * 1024 + 1)
        if len(raw) > 20 * 1024 * 1024:
            raise ValueError('Spot Advisor response too large')
        document = json.loads(raw)
        row = document['spot_advisor'][region]['Linux'][INSTANCE_TYPE]
        bands = [item for item in document['ranges'] if item['index'] == row['r']]
        if len(bands) != 1:
            raise ValueError('ambiguous Spot Advisor range identity')
        band = bands[0]
        maximum = band.get('max')
        if maximum is None:
            # AWS's top open-ended range has no finite maximum.
            maximum = 101
        modified = response.headers.get('Last-Modified')
        try:
            modified_at = parsedate_to_datetime(modified).timestamp() if modified else None
        except (TypeError, ValueError, OverflowError):
            modified_at = None
        return {'source_url': ADVISOR_URL, 'fetched_at': now,
                'sha256': hashlib.sha256(raw).hexdigest(), 'region': region,
                'instance_type': INSTANCE_TYPE, 'os': 'Linux', 'band': band['label'],
                'maximum_percent': maximum, 'last_modified': modified, 'source_modified_at': modified_at,
                'meaning': 'backward-looking interruption frequency; capacity and next-run probability unknown'}


def pages(client, service, operation, request, result_key):
    request, seen = dict(request), set()
    for _ in range(1000):
        row = client.call(service, operation, request)
        yield from row.get(result_key, [])
        token = row.get('NextToken')
        if not token:
            return
        if token in seen:
            raise ValueError('AWS pagination token repeated')
        seen.add(token)
        request['NextToken'] = token
    raise ValueError('AWS pagination limit exceeded')


def verify_caller(client, plan):
    verify_region(client, plan)
    caller = client.call('sts', 'get-caller-identity', {})
    role = plan.controller_role_arn.rsplit('/', 1)[-1]
    expected = f'arn:aws:sts::{plan.account_id}:assumed-role/{role}/'
    if caller.get('Account') != plan.account_id or not caller.get('Arn', '').startswith(expected):
        raise ValueError('active AWS identity does not match the explicit controller role/account')
    return {'account_id': plan.account_id, 'caller_arn': caller['Arn']}


def verify_region(client, plan):
    if getattr(client, 'region', plan.region) != plan.region:
        raise ValueError('AWS workload transport and campaign/project region differ; no fallback')


def account_plan_preflight(client, account_id, now):
    """Read-only PAID gate usable before creating even the watchdog stack.

    Free Tier credit/plan status is recorded, not interpreted as EC2 capacity
    or account activation. An expired credit period does not authorize an
    upgrade; only an explicitly observed PAID type passes this money gate.
    """
    if not isinstance(account_id, str) or not re.fullmatch(r'\d{12}', account_id):
        raise ValueError('explicit expected AWS account id required')
    report = {'format': 'rove4k-aws-account-plan-v1', 'account_id': account_id,
              'checked_at': timestamp(now), 'allowed': False, 'blockers': [],
              'account_plan_type': None, 'account_plan_status': None,
              'source': {'service': 'freetier', 'operation': 'GetAccountPlanState',
                         'region': ACCOUNT_PLAN_REGION, 'endpoint': ACCOUNT_PLAN_ENDPOINT,
                         'scope': 'account-global read only; no regional workload resource'},
              'automatic_upgrade_performed': False}
    try:
        port = getattr(client, 'account_plan_state', None)
        if not callable(port):
            raise ValueError('explicit read-only global account-plan port required')
        observed = port()
        if not isinstance(observed, dict):
            raise ValueError('account-plan response must be an object')
        report['response_sha256'] = digest(observed)
        report['account_plan_type'] = observed.get('accountPlanType')
        report['account_plan_status'] = observed.get('accountPlanStatus')
        if observed.get('accountId') != account_id:
            raise ValueError('account-plan response belongs to another or unknown AWS account')
        if observed.get('accountPlanStatus') not in ('NOT_STARTED', 'ACTIVE', 'EXPIRED'):
            raise ValueError('account-plan status is unknown; paid resources are blocked')
        if observed.get('accountPlanType') != 'PAID':
            raise ValueError('paid m6a campaign requires an observed PAID account plan; FREE/unknown is blocked; automatic upgrade is forbidden')
        report['allowed'] = True
    except (AwsError, ValueError, TypeError) as error:
        report['blockers'].append(str(error))
    return report


def require_paid_account_plan(client, account_id, now):
    report = account_plan_preflight(client, account_id, now)
    if not report['allowed']:
        raise ValueError('; '.join(report['blockers']))
    return report


def own_account_identity(client, account_id):
    """Observe the own-account identity without assuming a not-yet-created role."""
    caller = client.call('sts', 'get-caller-identity', {})
    if (type(caller) is not dict or caller.get('Account') != account_id or
            type(caller.get('Arn')) is not str or not re.fullmatch(
                r'arn:aws:(?:iam::' + re.escape(account_id) + r':(?:root|user/.+|role/.+)|sts::' +
                re.escape(account_id) + r':(?:assumed-role/[^/]+/.+|federated-user/.+))', caller['Arn'])):
        raise ValueError('fresh AWS identity does not belong to the configured own account')
    return {'account_id': account_id, 'caller_arn': caller['Arn']}


def observe_advanced_member_project(client, configured, now):
    """One plan-free observer shared by pre-stack and deployed readiness.

    Configuration is a source-reviewed direct-user transition, not observed
    PAID status. Fresh own-account and organization reads bind it to the caller;
    neither organization membership nor a missing Free Tier response opts in.
    Action owners separately enforce their deployed ControllerRole authority.
    """
    report = {'format': 'rove4k-aws-account-readiness-v1',
              'account_id': configured.project_account_id if type(configured) is AdvancedMemberProjectReadiness else None,
              'checked_at': timestamp(now),
              'readiness_basis': 'configured-advanced-member-project',
              'allowed': False, 'blockers': [], 'account_plan_type': None,
              'account_plan_status': None, 'paid_plan_observed': False,
              'automatic_upgrade_performed': False}
    try:
        if type(configured) is not AdvancedMemberProjectReadiness:
            raise ValueError('typed source-reviewed account readiness configuration required')
        configured = AdvancedMemberProjectReadiness.from_dict(configured.as_dict())
        if not callable(getattr(client, 'call', None)) or getattr(client, 'region', None) != ADVANCED_PROJECT_REGION:
            raise ValueError('fresh same-project AWS read port required')
        account_port = getattr(client, 'own_account_information', None)
        organization_port = getattr(client, 'organization_information', None)
        if not callable(account_port) or not callable(organization_port):
            raise ValueError('explicit read-only global account and organization ports required')
        report['configured_transition'] = configured.as_dict()
        report['sources'] = {
            'account': {'operation': 'GetAccountInformation', 'region': GLOBAL_METADATA_REGION,
                        'endpoint': ACCOUNT_INFORMATION_ENDPOINT, 'scope': 'own account; AccountId omitted'},
            'organization': {'operation': 'DescribeOrganization', 'region': GLOBAL_METADATA_REGION,
                             'endpoint': ORGANIZATION_INFORMATION_ENDPOINT}}
        report['identity'] = own_account_identity(client, configured.project_account_id)
        account = account_port()
        if (type(account) is not dict or account.get('AccountId') != configured.project_account_id or
                account.get('AccountState') != 'ACTIVE'):
            raise ValueError('fresh own-account information is missing, mismatched, or not ACTIVE')
        report['account_response_sha256'] = digest(account)
        report['account_observation'] = {key: account[key] for key in ('AccountId', 'AccountState')}
        organization_response = organization_port()
        organization = organization_response.get('Organization') if type(organization_response) is dict else None
        expected_arn = ('arn:aws:organizations::' + configured.management_account_id +
                        ':organization/' + configured.organization_id)
        if (type(organization) is not dict or
                organization.get('Id') != configured.organization_id or
                organization.get('MasterAccountId') != configured.management_account_id or
                organization.get('Arn') != expected_arn or organization.get('FeatureSet') != 'ALL'):
            raise ValueError('fresh organization/member-project context is missing or differs')
        report['organization_response_sha256'] = digest(organization_response)
        report['organization_observation'] = {key: organization[key]
            for key in ('Id', 'MasterAccountId', 'Arn', 'FeatureSet')}
        report['allowed'] = True
    except (AwsError, ValueError, TypeError, KeyError, AttributeError) as error:
        report['blockers'].append(str(error))
    return report


def account_readiness_preflight(client, plan, now):
    """Select a configured authority; a failed legacy read never changes class."""
    if plan.account_readiness is None:
        return account_plan_preflight(client, plan.account_id, now)
    if (type(plan.account_readiness) is not AdvancedMemberProjectReadiness or
            plan.account_readiness.project_account_id != plan.account_id or
            plan.region != ADVANCED_PROJECT_REGION or plan.project_region != plan.region):
        raise ValueError('Advanced readiness project/region binding changed')
    return observe_advanced_member_project(client, plan.account_readiness, now)


def require_account_readiness(client, plan, now):
    if plan.account_readiness is None:
        return require_paid_account_plan(client, plan.account_id, now)
    report = account_readiness_preflight(client, plan, now)
    if not report['allowed']:
        raise ValueError('; '.join(report['blockers']))
    return report


def verify_watchdog(client, plan, now):
    verify_region(client, plan)
    if not timestamp(now) < plan.deadline_epoch:
        raise ValueError('watchdog trigger is already due')
    stacks = client.call('cloudformation', 'describe-stacks', {'StackName': plan.watchdog_stack})['Stacks']
    if len(stacks) != 1 or stacks[0]['StackStatus'] not in ('CREATE_COMPLETE', 'UPDATE_COMPLETE'):
        raise ValueError('independent watchdog stack is not ready')
    parameters = {row['ParameterKey']: row.get('ParameterValue') for row in stacks[0].get('Parameters', [])}
    outputs = {row['OutputKey']: row['OutputValue'] for row in stacks[0].get('Outputs', [])}
    expected = {'CampaignId': plan.campaign_id, 'OwnerNonce': plan.owner_nonce,
                'HardDeadlineUtc': iso(plan.deadline_epoch)[:-1]}
    if plan.project_region is not None:
        expected['ProjectRegion'] = plan.project_region
    if any(parameters.get(key) != value for key, value in expected.items()):
        raise ValueError('watchdog stack identity/deadline differs from the immutable plan')
    for key, value in {'OwnershipTable': plan.ownership_table, 'ScheduleName': plan.schedule_name,
                       'WatchdogArn': plan.watchdog_arn, 'InstanceProfileArn': plan.instance_profile_arn,
                       'SecurityGroupId': plan.security_group_id, 'ArtifactBucket': plan.artifact_bucket,
                       'ControllerRoleArn': plan.controller_role_arn}.items():
        if outputs.get(key) != value:
            raise ValueError('watchdog output mismatch: ' + key)
    schedule = client.call('scheduler', 'get-schedule', {'Name': plan.schedule_name, 'GroupName': 'default'})
    if (schedule.get('State') != 'ENABLED' or schedule.get('ScheduleExpression') != 'at(' + expected['HardDeadlineUtc'] + ')'
            or schedule.get('ScheduleExpressionTimezone', 'UTC') != 'UTC'
            or schedule.get('FlexibleTimeWindow', {}).get('Mode') != 'OFF'
            or schedule.get('Target', {}).get('Arn') != plan.watchdog_arn):
        raise ValueError('independent one-time termination schedule is not armed for this plan')
    return {'stack_id': stacks[0]['StackId'], 'schedule_arn': schedule['Arn'],
            'deadline_epoch': plan.deadline_epoch, 'checked_at': timestamp(now)}


def verify_owned_lease(client, plan, budget, now, *, caller_kind='controller'):
    """Live admission for a bound cloud host, not a serialized passed flag.

    Instance callers must be the EC2 profile role with this instance's session
    name. The external controller uses its separately trusted GitHub role.
    """
    now = timestamp(now)
    verify_region(client, plan)
    active = budget.active_instances
    if (budget.campaign != plan.campaign_id or len(active) != 1
            or active[0].launch_token != plan.launch_token or active[0].instance_id is None):
        raise ValueError('exactly one bound campaign instance is required')
    if not budget.admit(now, 0).allowed or not now < plan.deadline_epoch <= budget.deadline(now):
        raise ValueError('live campaign lease is draining or its watchdog exceeds the remaining budget')
    instance_id = active[0].instance_id
    if caller_kind == 'controller':
        caller = verify_caller(client, plan)
    elif caller_kind == 'instance':
        profile_name = plan.instance_profile_arn.rsplit('/', 1)[-1]
        profile = client.call('iam', 'get-instance-profile', {'InstanceProfileName': profile_name})['InstanceProfile']
        roles = profile.get('Roles', [])
        if profile.get('Arn') != plan.instance_profile_arn or len(roles) != 1:
            raise ValueError('instance profile identity is incomplete')
        role = roles[0]
        if not role.get('Arn', '').startswith(f'arn:aws:iam::{plan.account_id}:role/'):
            raise ValueError('instance role belongs to another account')
        identity = client.call('sts', 'get-caller-identity', {})
        expected_arn = f"arn:aws:sts::{plan.account_id}:assumed-role/{role['RoleName']}/{instance_id}"
        if (identity.get('Account') != plan.account_id or identity.get('Arn') != expected_arn
                or identity.get('UserId', '').split(':', 1)[0] != role['RoleId']):
            raise ValueError('caller is not the bound EC2 instance profile session')
        caller = {'account_id': plan.account_id, 'caller_arn': identity['Arn']}
    else:
        raise ValueError('caller_kind must explicitly select controller or instance')
    intent = get_record(client, plan, 'launch#' + plan.launch_token)
    bound = get_record(client, plan, 'owned#' + plan.launch_token)
    if intent != plan.intent(active[0].requested_at) or bound != {**intent, 'instance_id': instance_id}:
        raise ValueError('live host differs from its immutable budget and ownership binding')
    instance = reconcile(client, plan, intent, instance_id)
    if instance is None or instance['State']['Name'] != 'running':
        raise ValueError('bound instance is not physically observed running')
    watchdog = verify_watchdog(client, plan, now)
    return {'verified': True, 'instance_id': instance_id, 'account_id': plan.account_id,
            'region': plan.region, 'caller_kind': caller_kind, 'caller': caller,
            'checked_at': now, 'plan_sha256': digest(plan.as_dict()),
            'ownership_sha256': digest(bound), 'terminate_trigger_epoch': plan.deadline_epoch,
            'watchdog': watchdog}


def standard_spot_used(client):
    """Count running/pending Standard usage and unfulfilled open requests."""
    types = []
    for reservation in pages(client, 'ec2', 'describe-instances', {'Filters': [
            {'Name': 'instance-lifecycle', 'Values': ['spot']},
            {'Name': 'instance-state-name', 'Values': ['pending', 'running', 'stopping', 'stopped']}]}, 'Reservations'):
        types.extend(item['InstanceType'] for item in reservation['Instances'])
    for request in pages(client, 'ec2', 'describe-spot-instance-requests', {'Filters': [
            {'Name': 'state', 'Values': ['open']}]}, 'SpotInstanceRequests'):
        if not request.get('InstanceId'):
            types.append(request['LaunchSpecification']['InstanceType'])
    types = [kind for kind in types if kind[0].lower() in 'acdhimrtz' and not kind.startswith(('dl', 'inf', 'trn'))]
    counts = {}
    unique = sorted(set(types))
    for start in range(0, len(unique), 100):
        response = client.call('ec2', 'describe-instance-types', {'InstanceTypes': unique[start:start + 100]})
        counts.update({row['InstanceType']: row['VCpuInfo']['DefaultVCpus'] for row in response['InstanceTypes']})
    if set(counts) != set(unique):
        raise ValueError('incomplete vCPU metadata for current Standard Spot usage')
    return sum(counts[kind] for kind in types)


def preflight(client, plan, advisor, now):
    """Read APIs plus RunInstances DryRun; this does not prove live capacity."""
    now = timestamp(now)
    result = {'plan_sha256': digest(plan.as_dict()), 'checked_at': now,
              'allowed': False, 'blockers': [], 'capacity_available': None,
              'paid_launch_performed': False}
    try:
        result['identity'] = verify_caller(client, plan)
        result['account_plan'] = account_readiness_preflight(client, plan, now)
        if not result['account_plan']['allowed']:
            raise ValueError('; '.join(result['account_plan']['blockers']))
        result['watchdog'] = verify_watchdog(client, plan, now)
        if (advisor.get('source_url') != ADVISOR_URL or advisor.get('region') != plan.region
                or advisor.get('instance_type') != INSTANCE_TYPE or advisor.get('os') != 'Linux'
                or not 0 <= now - timestamp(advisor['fetched_at']) <= 86400
                or not 0 <= advisor.get('maximum_percent', 101) <= 5
                or not re.fullmatch(r'[a-f0-9]{64}', advisor.get('sha256', ''))
                or advisor.get('band', '').replace(' ', '') != '<5%'):
            raise ValueError('current AWS Linux Spot Advisor <5% evidence required')
        source_at = advisor.get('source_modified_at')
        if source_at is None or not 0 <= now - timestamp(source_at) <= ADVISOR_MAX_SOURCE_AGE_SECONDS:
            raise ValueError('Spot Advisor source freshness is unproven or older than seven days')
        result['advisor'] = advisor
        spot_role = client.call('iam', 'get-role', {'RoleName': 'AWSServiceRoleForEC2Spot'})['Role']
        expected_spot_role = f'arn:aws:iam::{plan.account_id}:role/aws-service-role/spot.amazonaws.com/AWSServiceRoleForEC2Spot'
        if spot_role.get('Arn') != expected_spot_role:
            raise ValueError('the account Spot service-linked role must be provisioned by the bootstrap principal')
        types = client.call('ec2', 'describe-instance-types', {'InstanceTypes': [INSTANCE_TYPE]})['InstanceTypes']
        if (len(types) != 1 or types[0]['InstanceType'] != INSTANCE_TYPE or types[0]['VCpuInfo']['DefaultVCpus'] != 192
                or types[0]['MemoryInfo']['SizeInMiB'] != 786432 or 'spot' not in types[0]['SupportedUsageClasses']
                or 'x86_64' not in types[0]['ProcessorInfo']['SupportedArchitectures']):
            raise ValueError('actual m6a.48xlarge metadata differs from the campaign contract')
        images = client.call('ec2', 'describe-images', {'ImageIds': [plan.ami_id]})['Images']
        if (len(images) != 1 or images[0]['ImageId'] != plan.ami_id or images[0]['State'] != 'available' or images[0]['Architecture'] != 'x86_64'
                or images[0].get('PlatformDetails') != 'Linux/UNIX'
                or images[0].get('RootDeviceName') != plan.root_device_name):
            raise ValueError('AMI does not match the declared Linux x86-64 root image')
        subnets = client.call('ec2', 'describe-subnets', {'SubnetIds': [plan.subnet_id]})['Subnets']
        if len(subnets) != 1 or subnets[0]['SubnetId'] != plan.subnet_id or subnets[0]['State'] != 'available' or subnets[0]['AvailableIpAddressCount'] < 1:
            raise ValueError('declared subnet is unavailable')
        zone = subnets[0]['AvailabilityZone']
        offerings = list(pages(client, 'ec2', 'describe-instance-type-offerings', {
            'LocationType': 'availability-zone', 'Filters': [
                {'Name': 'location', 'Values': [zone]},
                {'Name': 'instance-type', 'Values': [INSTANCE_TYPE]}]}, 'InstanceTypeOfferings'))
        if not any(row.get('InstanceType') == INSTANCE_TYPE and row.get('Location') == zone for row in offerings):
            raise ValueError('m6a.48xlarge is not offered in the declared AZ')
        groups = client.call('ec2', 'describe-security-groups', {'GroupIds': [plan.security_group_id]})['SecurityGroups']
        if len(groups) != 1 or groups[0]['GroupId'] != plan.security_group_id or groups[0]['VpcId'] != subnets[0]['VpcId']:
            raise ValueError('security group and subnet must share the declared VPC')
        quota = client.call('service-quotas', 'get-service-quota', {
            'ServiceCode': 'ec2', 'QuotaCode': STANDARD_SPOT_QUOTA})['Quota']['Value']
        used = standard_spot_used(client)
        result['quota'] = {'limit_vcpus': quota, 'used_vcpus': used, 'available_vcpus': quota - used}
        if quota - used < 192:
            raise ValueError('fewer than 192 Standard Spot vCPUs are available')
        prices = list(pages(client, 'ec2', 'describe-spot-price-history', {
            'InstanceTypes': [INSTANCE_TYPE], 'ProductDescriptions': ['Linux/UNIX'],
            'AvailabilityZone': zone, 'StartTime': iso(max(0, now - 3600)), 'EndTime': iso(now)}, 'SpotPriceHistory'))
        prices = [row for row in prices if row['AvailabilityZone'] == zone and row['InstanceType'] == INSTANCE_TYPE]
        if not prices:
            raise ValueError('no actual Linux Spot price returned for the declared AZ')
        current = max(prices, key=lambda row: row['Timestamp'])
        if decimal(current['SpotPrice']) > decimal(plan.max_hourly_usd):
            raise ValueError('current Spot price exceeds the fixed ceiling')
        result['price'] = current
        try:
            client.call('ec2', 'run-instances', {**plan.request(), 'DryRun': True})
        except AwsError as error:
            if error.code != 'DryRunOperation':
                raise
        else:
            raise ValueError('EC2 did not return the required DryRunOperation authorization result')
        result['allowed'] = True
    except (AwsError, ValueError, KeyError, TypeError) as error:
        result['blockers'].append(str(error))
    return result


def record_key(plan, record_id):
    return {'campaign_id': {'S': plan.campaign_id}, 'record_id': {'S': record_id}}


def get_record(client, plan, record_id):
    row = client.call('dynamodb', 'get-item', {'TableName': plan.ownership_table,
                    'Key': record_key(plan, record_id), 'ConsistentRead': True}).get('Item')
    return json.loads(row['payload']['S']) if row else None


def put_immutable(client, plan, record_id, payload):
    item = {**record_key(plan, record_id), 'payload': {'S': canonical(payload)},
            'expires_at': {'N': str(int(payload['requested_at']) + 30 * 86400)}}
    try:
        client.call('dynamodb', 'put-item', {'TableName': plan.ownership_table, 'Item': item,
                    'ConditionExpression': 'attribute_not_exists(campaign_id) AND attribute_not_exists(record_id)'})
    except AwsError as error:
        if error.code != 'ConditionalCheckFailedException' or get_record(client, plan, record_id) != payload:
            raise


def verify_instance(plan, intent, reservation, instance, *, expected_id=None):
    tags = {row['Key']: row['Value'] for row in instance.get('Tags', [])}
    launch = instance['LaunchTime']
    if isinstance(launch, str):
        launch = datetime.fromisoformat(launch.replace('Z', '+00:00')).timestamp()
    elif isinstance(launch, datetime):
        launch = launch.timestamp()
    if (reservation.get('OwnerId') != plan.account_id
            or instance.get('ClientToken') != intent['launch_token']
            or instance.get('InstanceType') != intent['instance_type']
            or instance.get('ImageId') != intent['ami_id'] or instance.get('SubnetId') != intent['subnet_id']
            or instance.get('IamInstanceProfile', {}).get('Arn') != intent['instance_profile_arn']
            or tags.get('RoveCampaign') != plan.campaign_id or tags.get('RoveOwner') != plan.owner_nonce
            or not intent['requested_at'] - 2 <= timestamp(launch) <= time.time() + 2
            or (expected_id is not None and instance.get('InstanceId') != expected_id)):
        raise ValueError('EC2 resource does not match the immutable launch ownership manifest')
    return instance['InstanceId']


def reconcile(client, plan, intent, expected_id=None):
    rows = []
    for reservation in pages(client, 'ec2', 'describe-instances', {'Filters': [
            {'Name': 'client-token', 'Values': [intent['launch_token']]}]}, 'Reservations'):
        for instance in reservation['Instances']:
            verify_instance(plan, intent, reservation, instance, expected_id=expected_id)
            rows.append(instance)
    if len(rows) > 1:
        raise ValueError('one-instance launch returned multiple resources; do not launch another')
    return rows[0] if rows else None


def launch(client, plan, budget, receipt, now):
    """Paid port. Caller must persist launch_requested before invoking this."""
    now = timestamp(now)
    if budget.campaign != plan.campaign_id or receipt.get('plan_sha256') != digest(plan.as_dict()):
        raise ValueError('campaign/preflight does not match the immutable launch plan')
    if not receipt.get('allowed') or not 0 <= now - receipt['checked_at'] <= 900:
        raise ValueError('fresh successful preflight required')
    active = budget.active_instances
    if len(active) != 1 or active[0].launch_token != plan.launch_token or not budget.admit(now, 0).allowed:
        raise ValueError('the durable budget does not exclusively own this launch slot')
    if plan.deadline_epoch > budget.deadline(now):
        raise ValueError('watchdog trigger exceeds the remaining cumulative campaign budget')
    if plan.deadline_epoch - now < budget.policy.termination_slack_seconds:
        raise ValueError('insufficient reconciliation lead time before the watchdog trigger')
    verify_caller(client, plan)
    require_account_readiness(client, plan, now)
    verify_watchdog(client, plan, now)
    for reservation in pages(client, 'ec2', 'describe-instances', {'Filters': [
            {'Name': 'tag:RoveCampaign', 'Values': [plan.campaign_id]},
            {'Name': 'instance-state-name', 'Values': ['pending', 'running', 'stopping', 'stopped', 'shutting-down']}]}, 'Reservations'):
        if any(item.get('ClientToken') != plan.launch_token for item in reservation['Instances']):
            raise ValueError('another unresolved campaign instance exists; reconcile its original budget history')
    intent = plan.intent(active[0].requested_at)
    put_immutable(client, plan, 'launch#' + plan.launch_token, intent)
    bound = get_record(client, plan, 'owned#' + plan.launch_token)
    if bound is not None and bound != {**intent, 'instance_id': bound.get('instance_id')}:
        raise ValueError('immutable instance binding does not match this launch intent')
    existing = reconcile(client, plan, intent, bound['instance_id'] if bound else active[0].instance_id)
    if existing is not None:
        if existing['State']['Name'] == 'terminated':
            raise ValueError('launch token already belongs to a terminated instance; preserve its history')
        instance_id = existing['InstanceId']
    else:
        # Same token and exact request on every retry: an observation timeout is
        # unresolved, never permission to issue a new launch token.
        response = client.call('ec2', 'run-instances', plan.request())
        instances = response.get('Instances', [])
        if len(instances) != 1:
            raise ValueError('RunInstances outcome is unresolved; reconcile the original token')
        instance_id = verify_instance(plan, intent, response, instances[0])
    binding = {**intent, 'instance_id': instance_id}
    put_immutable(client, plan, 'owned#' + plan.launch_token, binding)
    return {'instance_id': instance_id, 'launch_token': plan.launch_token,
            'ownership': binding, 'termination_observed': False}


def recover_launch(client, plan):
    """Reconcile an original uncertain request, even after admission closes.

    Never issues RunInstances. A missing response remains unresolved, not a
    refund/absence proof. A recovered binding can be terminated immediately.
    """
    verify_caller(client, plan)
    intent = get_record(client, plan, 'launch#' + plan.launch_token)
    if intent is None or intent != plan.intent(intent['requested_at']):
        raise ValueError('the original immutable intent is required for recovery')
    bound = get_record(client, plan, 'owned#' + plan.launch_token)
    if bound is not None and bound != {**intent, 'instance_id': bound.get('instance_id')}:
        raise ValueError('binding differs from the original launch intent')
    existing = reconcile(client, plan, intent, bound['instance_id'] if bound else None)
    if existing is None:
        return {'launch_token': plan.launch_token, 'state': 'unresolved', 'instance_id': None,
                'paid_launch_request_sent': False}
    binding = {**intent, 'instance_id': existing['InstanceId']}
    put_immutable(client, plan, 'owned#' + plan.launch_token, binding)
    return {'launch_token': plan.launch_token, 'state': existing['State']['Name'],
            'instance_id': existing['InstanceId'], 'ownership': binding,
            'paid_launch_request_sent': False}


def terminate(client, plan, instance_id):
    """Only terminate a manifest-owned resource; response is still a request."""
    verify_caller(client, plan)
    intent = get_record(client, plan, 'launch#' + plan.launch_token)
    binding = get_record(client, plan, 'owned#' + plan.launch_token)
    if intent is None or binding is None or binding.get('instance_id') != instance_id:
        raise ValueError('exact immutable intent and instance binding are required')
    if intent != plan.intent(intent['requested_at']) or binding != {**intent, 'instance_id': instance_id}:
        raise ValueError('ownership records differ from the declared request')
    observed = reconcile(client, plan, intent, instance_id)
    if observed is None:
        raise ValueError('absence is not a termination observation')
    if observed['State']['Name'] == 'terminated':
        return {'instance_id': instance_id, 'state': 'terminated', 'observed': True}
    client.call('ec2', 'terminate-instances', {'InstanceIds': [instance_id]})
    return {'instance_id': instance_id, 'state': 'termination_requested', 'observed': False}


def observe_termination(client, plan, instance_id):
    verify_caller(client, plan)
    intent = get_record(client, plan, 'launch#' + plan.launch_token)
    binding = get_record(client, plan, 'owned#' + plan.launch_token)
    if intent is None or intent != plan.intent(intent['requested_at']) or binding != {**intent, 'instance_id': instance_id}:
        raise ValueError('ownership binding required for physical observation')
    row = reconcile(client, plan, intent, instance_id)
    return {'instance_id': instance_id, 'state': row['State']['Name'] if row else 'not_observed',
            'observed': bool(row and row['State']['Name'] == 'terminated')}


def close_ownership(client, plan, instance_id, now, evidence):
    """Persist actual termination before EC2 eventually forgets its history."""
    if not isinstance(evidence, str) or not 0 < len(evidence) <= 4096:
        raise ValueError('original EC2 observation reference is required')
    observation = observe_termination(client, plan, instance_id)
    if not observation['observed']:
        raise ValueError('physical termination has not been observed')
    intent = get_record(client, plan, 'launch#' + plan.launch_token)
    closed = {**intent, 'instance_id': instance_id, 'terminal_state': 'terminated',
              'observed_at': timestamp(now), 'evidence': evidence}
    previous = get_record(client, plan, 'closed#' + plan.launch_token)
    if previous is not None:
        if any(previous.get(key) != value for key, value in {
                **intent, 'instance_id': instance_id, 'terminal_state': 'terminated'}.items()):
            raise ValueError('prior termination record contradicts this immutable ownership')
        return previous
    put_immutable(client, plan, 'closed#' + plan.launch_token, closed)
    return closed


class S3Evidence:
    """Immutable, checksum-acknowledged objects from an explicit owned directory.

    The game journal owns file creation/fsync and calls this on immutable
    chunks. A timeout is unacknowledged; retrying the same key verifies the
    committed object's checksum instead of replacing it.
    """
    def __init__(self, client, plan, owned_root):
        verify_region(client, plan)
        self.client, self.plan = client, plan
        root = Path(owned_root)
        self.root = root.resolve()
        if not root.is_absolute() or any((p / '.git').exists() for p in (self.root, *self.root.parents)):
            raise ValueError('explicit external owned evidence directory required')

    @property
    def max_publish_seconds(self):
        """Declared two-call budget; stalled OS/file I/O can violate it.

        The controller must retain the publisher owner if this deadline is
        exceeded, rather than reporting a terminated worker from elapsed time.
        """
        seconds = getattr(self.client, 'timeout', None)
        if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds <= 0:
            raise ValueError('publisher requires a positive finite transport timeout')
        bound = 2 * seconds + 5
        if not math.isfinite(bound):
            raise ValueError('publisher timeout budget is not finite')
        return bound

    def publish(self, path, key):
        path = Path(path).resolve()
        if not path.is_relative_to(self.root) or not path.is_file():
            raise ValueError('evidence source must be a file inside the owned directory')
        if (not isinstance(key, str) or not key.startswith(self.plan.campaign_id + '/')
                or any(part in ('', '.', '..') for part in key.split('/'))):
            raise ValueError('remote key must stay inside the campaign prefix')
        sha = hashlib.sha256()
        size = 0
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                sha.update(block)
                size += len(block)
        fingerprint = sha.hexdigest()
        checksum = base64.b64encode(sha.digest()).decode('ascii')
        reused = False
        try:
            response = self.client.put_file(self.plan.artifact_bucket, key, path, fingerprint)
            if response.get('ChecksumSHA256') != checksum:
                raise ValueError('S3 did not acknowledge the submitted object checksum')
        except AwsError as error:
            if error.code != 'PreconditionFailed':
                raise
            reused = True
        observed = self.client.call('s3api', 'head-object', {'Bucket': self.plan.artifact_bucket,
                'Key': key, 'ChecksumMode': 'ENABLED'})
        if (observed.get('Metadata', {}).get('sha256') != fingerprint
                or observed.get('ContentLength') != size or observed.get('ChecksumSHA256') != checksum):
            raise ValueError('existing remote evidence differs from the immutable local chunk')
        return {'bucket': self.plan.artifact_bucket, 'key': key, 'object_key': key, 'bytes': size,
                'sha256': fingerprint, 'checksum_sha256': checksum,
                'version_id': observed.get('VersionId'), 'acknowledged': True,
                'verified': True, 'backend': 's3',
                'reused_existing': reused}

    def list_keys(self, prefix):
        prefix = prefix.rstrip('/')
        self._key(prefix + '/placeholder')
        request = {'Bucket': self.plan.artifact_bucket, 'Prefix': prefix + '/', 'MaxKeys': 1000}
        results, seen = [], set()
        for _ in range(1000):
            response = self.client.call('s3api', 'list-objects-v2', request)
            for item in response.get('Contents', []):
                self._key(item['Key'])
                if not item['Key'].startswith(prefix + '/'):
                    raise ValueError('S3 listing escaped the requested campaign prefix')
                results.append(item['Key'])
            token = response.get('NextContinuationToken')
            if not token:
                return sorted(set(results))
            if token in seen:
                raise ValueError('S3 continuation token repeated')
            seen.add(token)
            request['ContinuationToken'] = token
        raise ValueError('S3 recovery listing exceeded its finite page bound')

    def _key(self, key):
        if (not isinstance(key, str) or not key.startswith(self.plan.campaign_id + '/')
                or any(part in ('', '.', '..') for part in key.split('/'))):
            raise ValueError('remote key must stay inside the campaign prefix')

    def read_verified(self, key, *, expected_sha=None, max_bytes=4 * 1024 * 1024):
        self._key(key)
        if type(max_bytes) is not int or not 0 < max_bytes <= 128 * 1024 * 1024:
            raise ValueError('bounded recovery object size required')
        head = self.client.call('s3api', 'head-object', {'Bucket': self.plan.artifact_bucket,
                            'Key': key, 'ChecksumMode': 'ENABLED'})
        sha = head.get('Metadata', {}).get('sha256', '')
        checksum = head.get('ChecksumSHA256')
        if (not re.fullmatch(r'[a-f0-9]{64}', sha) or not isinstance(head.get('ContentLength'), int)
                or not 0 <= head['ContentLength'] <= max_bytes or not head.get('ETag')
                or checksum != base64.b64encode(bytes.fromhex(sha)).decode('ascii')
                or expected_sha is not None and sha != expected_sha):
            raise ValueError('remote recovery metadata does not match the expected checksum/size')
        recovered = self.root / 'recovered'
        recovered.mkdir(parents=True, exist_ok=True)
        path = recovered / (uuid.uuid4().hex + '.unverified')
        with path.open('xb'):
            pass
        response = self.client.get_file(self.plan.artifact_bucket, key, path, head['ETag'])
        data = path.read_bytes()
        if (len(data) != head['ContentLength'] or hashlib.sha256(data).hexdigest() != sha
                or response.get('ChecksumSHA256') != checksum):
            raise ValueError('downloaded recovery bytes failed verification; preserved at ' + str(path))
        verified = path.with_suffix('.verified')
        path.rename(verified)
        return data


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('plan', 'preflight', 'template', 'account-readiness'))
    parser.add_argument('--config', type=Path)
    parser.add_argument('--project-region', help='explicit template deployment binding; never inferred or changed')
    parser.add_argument('--account-readiness', choices=('freetier-paid', _ADVANCED_TRANSITION[0]),
                        help='explicit pre-stack observer class; never inferred from an API failure')
    parser.add_argument('--account-id', help='expected own account for the read-only operator entry')
    parser.add_argument('--profile', help='explicit local operator CLI profile; no profile file inspection')
    parser.add_argument('--aws-cli', help='absolute official CLI entry for operator reads only')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.project_region is not None and args.action not in ('template', 'account-readiness'):
        parser.error('--project-region applies to template; campaign plans bind project_region inside --config')
    operator_options = (args.account_readiness, args.account_id, args.profile, args.aws_cli)
    if args.action != 'account-readiness' and any(value is not None for value in operator_options):
        parser.error('operator authentication/observer options apply only to account-readiness')
    output = args.out.resolve()
    if not args.out.is_absolute() or output.exists() or any((p / '.git').exists() for p in (output.parent, *output.parents)):
        parser.error('new absolute output outside any Git checkout required')
    if args.action == 'account-readiness':
        if (args.config is not None or any(value is None for value in operator_options) or
                args.project_region != ADVANCED_PROJECT_REGION or
                not re.fullmatch(r'\d{12}', args.account_id)):
            parser.error('account-readiness requires explicit class/account/profile/absolute CLI/Sydney region and no deployed plan')
        configured = AdvancedMemberProjectReadiness() if args.account_readiness == _ADVANCED_TRANSITION[0] else None
        if configured is not None and args.account_id != configured.project_account_id:
            parser.error('Advanced readiness account differs from the source-reviewed project')
        client = OperatorReadinessCLI(args.project_region, args.aws_cli, args.profile, args.account_readiness)
        if configured is not None:
            result = observe_advanced_member_project(client, configured, time.time())
        else:
            # Preserve the legacy PAID observer while still checking the selected
            # local profile's own account before its account-global billing read.
            own_account_identity(client, args.account_id)
            result = account_plan_preflight(client, args.account_id, time.time())
    elif args.action == 'template':
        try:
            from .aws_infrastructure import template
        except ImportError:
            from aws_infrastructure import template
        result = template(project_region=args.project_region)
    else:
        if args.config is None:
            parser.error('--config must name the explicit non-secret campaign plan JSON')
        plan = AWSPlan.from_dict(json.loads(args.config.read_text(encoding='utf-8')))
        result = plan.as_dict() if args.action == 'plan' else preflight(
            AWSCLI(plan.region), plan, fetch_advisor(plan.region), time.time())
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    return 2 if args.action in ('preflight', 'account-readiness') and not result.get('allowed') else 0


if __name__ == '__main__':
    raise SystemExit(main())
