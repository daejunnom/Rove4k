"""A bounded, conditional S3 ledger for a future shared budget owner.

This module provides no game-start authority: S3 writes and a socket GO are
separate operations. A deployment must additionally prove coordinator fencing,
physical owner settlement, fresh-clock admission, bucket policy and recovery.
No caller may turn this module's receipt into a production GO by itself.

S3 If-Match compares the current ETag, not VersionId. Unique chained events
prevent ordinary state reuse; a separately persisted trusted anchor is still
required to detect rollback or object replacement after a process restart. An
anchor read cannot prevent a different writer restoring old bytes between the
read and conditional PUT (the ABA problem); deployment requires an independent
fenced single-writer owner, and this module does not implement that authority.
"""
from dataclasses import dataclass, replace
import base64
import hashlib
import json
from pathlib import Path
import re
import tempfile

try:
    from .budget import SharedCampaignBudget, decimal, timestamp
    from .ledger import canonical, digest, valid_id
except ImportError:
    from budget import SharedCampaignBudget, decimal, timestamp
    from ledger import canonical, digest, valid_id


MAX_LEDGER_BYTES = 4 * 1024 * 1024
ZERO = '0' * 64
HEX = re.compile(r'[0-9a-f]{64}')
REQUEST = re.compile(r'[a-zA-Z0-9][a-zA-Z0-9_.-]{15,95}')


class LedgerConflict(ValueError):
    """The conditional write did not take effect; reread and re-evaluate."""


class LedgerUncertain(ValueError):
    """An interrupted write may have committed; never blindly repeat it."""


@dataclass(frozen=True)
class Anchor:
    seq: int
    sha256: str
    authority: str
    opening_sha256: str

    def __post_init__(self):
        if (type(self.seq) is not int or self.seq < -1 or not isinstance(self.sha256, str) or not HEX.fullmatch(self.sha256)
                or not isinstance(self.authority, str) or not HEX.fullmatch(self.authority)):
            raise ValueError('invalid trusted anchor')
        if not isinstance(self.opening_sha256, str) or not HEX.fullmatch(self.opening_sha256):
            raise ValueError('trusted opening checkpoint required')
        if (self.seq == -1) != (self.sha256 == ZERO):
            raise ValueError('invalid genesis anchor')


@dataclass(frozen=True)
class Snapshot:
    rows: tuple[dict, ...]
    opening: dict
    etag: str
    version_id: str
    anchor: Anchor


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


class S3SharedBudget:
    """One existing versioned general-purpose S3 object in one home region.

    The caller supplies and durably advances a trusted anchor outside this
    mutable S3 object. Bootstrap, overwrite/delete policy deployment and AWS
    account/role validation are intentionally outside this class. Missing
    objects, unknown write outcomes and conflicts fail closed; this class never
    creates a replacement head or retries a write automatically.
    """
    provides_go_authority = False
    def __init__(self, client, *, bucket, key, account, region, campaign):
        if (not isinstance(bucket, str) or not re.fullmatch(r'[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]', bucket)
                or not isinstance(account, str) or not re.fullmatch(r'\d{12}', account)
                or not isinstance(region, str) or not re.fullmatch(r'[a-z]{2}(?:-gov)?-[a-z]+-\d+', region)
                or getattr(client, 'region', None) != region):
            raise ValueError('explicit account, home region and bucket are required')
        self.campaign = valid_id(campaign)
        if (not isinstance(key, str) or not key.startswith(campaign + '/')
                or any(part in ('', '.', '..') for part in key.split('/'))):
            raise ValueError('shared ledger key must stay within the campaign prefix')
        self.client, self.bucket, self.key, self.account, self.region = client, bucket, key, account, region
        self.authority = digest({'format': 'rove4k-shared-budget-v1', 'campaign': self.campaign,
                                 'account': account, 'home_region': region, 'bucket': bucket, 'key': key})

    def _parse(self, raw, trusted):
        if not isinstance(trusted, Anchor):
            raise ValueError('independently persisted trusted anchor required')
        if trusted.authority != self.authority:
            raise ValueError('trusted anchor belongs to another ledger authority')
        if not isinstance(raw, bytes) or len(raw) > MAX_LEDGER_BYTES:
            raise ValueError('ledger bytes exceed the bounded snapshot')
        try:
            doc = json.loads(raw, object_pairs_hook=_pairs,
                             parse_constant=lambda _: (_ for _ in ()).throw(ValueError('non-finite JSON')))
        except (UnicodeError, json.JSONDecodeError) as error:
            raise ValueError('ledger is not valid JSON') from error
        if (not isinstance(doc, dict) or set(doc) != {'format', 'campaign', 'account', 'home_region', 'opening', 'events'}
                or doc['format'] != 'rove4k-shared-budget-v1' or doc['campaign'] != self.campaign
                or doc['account'] != self.account or doc['home_region'] != self.region
                or not isinstance(doc['events'], list) or canonical(doc) != raw):
            raise ValueError('ledger identity or canonical encoding differs')
        opening = doc['opening']
        if (not isinstance(opening, dict) or set(opening) != {'prior_compute_usd', 'prior_ancillary_usd', 'prior_limit_confirmed',
                'as_of', 'source_sha256', 'excludes_opening_events', 'complete_identities',
                'prior_game_ids', 'prior_pair_ids', 'prior_request_ids', 'prior_launch_tokens',
                'prior_instance_ids', 'prior_receipts', 'events'}
                or not isinstance(opening['prior_compute_usd'], str) or not isinstance(opening['prior_ancillary_usd'], str)
                or type(opening['prior_limit_confirmed']) is not bool
                or not isinstance(opening['source_sha256'], str) or not HEX.fullmatch(opening['source_sha256'])
                or opening['source_sha256'] == ZERO or opening['excludes_opening_events'] is not True
                or opening['complete_identities'] is not True or not isinstance(opening['events'], list)
                or not isinstance(opening['prior_game_ids'], list) or not isinstance(opening['prior_pair_ids'], list)
                or not isinstance(opening['prior_request_ids'], list) or not isinstance(opening['prior_launch_tokens'], list)
                or not isinstance(opening['prior_instance_ids'], list) or not isinstance(opening['prior_receipts'], list)
                or digest(opening) != trusted.opening_sha256):
            raise ValueError('trusted opening checkpoint identity or evidence differs')
        for name in ('prior_game_ids', 'prior_pair_ids', 'prior_request_ids', 'prior_launch_tokens', 'prior_instance_ids'):
            values = opening[name]
            if (any(not isinstance(value, str) for value in values) or len(set(values)) != len(values)
                    or len(values) > 65536):
                raise ValueError('opening identity history is invalid or duplicated')
        if any(not REQUEST.fullmatch(value) for value in opening['prior_request_ids']):
            raise ValueError('opening request identities are invalid')
        if (len(opening['prior_receipts']) > 65536 or any(not isinstance(row, list) or len(row) != 2
                or not isinstance(row[0], str) or not row[0] or not isinstance(row[1], str)
                for row in opening['prior_receipts'])):
            raise ValueError('opening receipt identities are invalid')
        opened_at = timestamp(opening['as_of'])
        # Restore the opening's own chronological events first. Carry-in costs
        # are as-of balances; applying them to earlier events would falsely
        # reject owners or games that started before the cap was reached.
        state = SharedCampaignBudget(self.campaign)
        for opening_row in opening['events']:
            if (not isinstance(opening_row, dict) or set(opening_row) != {'campaign', 'event', 'data', 'time_utc'}
                    or opening_row['campaign'] != self.campaign or not isinstance(opening_row['event'], str)
                    or not opening_row['event'].startswith('budget.v2.') or not isinstance(opening_row['data'], dict)
                    or timestamp(opening_row['time_utc']) > opened_at):
                raise ValueError('opening event is outside the trusted checkpoint')
            state = state.apply(opening_row['event'], opening_row['data'], opening_row['time_utc'])
        if state.last_at > opened_at:
            raise ValueError('opening event occurs after checkpoint')
        if set(opening['prior_game_ids']).intersection(game.game_id for game in state.games):
            raise ValueError('opening game identity cannot be both prior and active')
        if len(set(opening['prior_pair_ids']) | {game.pair_id for game in state.games}) > 128:
            raise ValueError('opening cumulative pair cap exceeded')
        if (set(opening['prior_launch_tokens']).intersection(row.charge.launch_token for row in state.instances)
                or set(opening['prior_instance_ids']).intersection(row.charge.instance_id for row in state.instances if row.charge.instance_id)
                or {row[0] for row in opening['prior_receipts']}.intersection(name for name, _ in state.ancillary_receipts)):
            raise ValueError('opening prior ownership or receipt identity overlaps restored events')
        state = replace(state, last_at=opened_at, prior_compute_usd=decimal(opening['prior_compute_usd']),
                        prior_ancillary_usd=decimal(opening['prior_ancillary_usd']),
                        confirmed_limit=state.confirmed_limit or opening['prior_limit_confirmed'],
                        prior_game_ids=frozenset(opening['prior_game_ids']),
                        prior_pair_ids=frozenset(opening['prior_pair_ids']),
                        prior_launch_tokens=frozenset(opening['prior_launch_tokens']),
                        prior_instance_ids=frozenset(opening['prior_instance_ids']),
                        prior_receipts=tuple(tuple(row) for row in opening['prior_receipts']))
        previous, requests = ZERO, set(opening['prior_request_ids'])
        for seq, row in enumerate(doc['events']):
            if (not isinstance(row, dict) or set(row) != {'campaign', 'seq', 'previous_sha256', 'event', 'data',
                                                       'time_utc', 'request_id', 'sha256'}
                    or row['campaign'] != self.campaign or type(row['seq']) is not int or row['seq'] != seq
                    or row['previous_sha256'] != previous or not isinstance(row['event'], str)
                    or not row['event'].startswith('budget.v2.') or not isinstance(row['data'], dict)
                    or not isinstance(row['request_id'], str) or not REQUEST.fullmatch(row['request_id'])
                    or row['request_id'] in requests or not isinstance(row['sha256'], str)
                    or not HEX.fullmatch(row['sha256'])):
                raise ValueError('ledger event identity, order or request differs')
            body = {key: value for key, value in row.items() if key != 'sha256'}
            if digest(body) != row['sha256']:
                raise ValueError('ledger event hash differs')
            timestamp(row['time_utc'])
            requests.add(row['request_id'])
            previous = row['sha256']
        if trusted.seq >= len(doc['events']) or (trusted.seq >= 0 and doc['events'][trusted.seq]['sha256'] != trusted.sha256):
            raise ValueError('ledger rolled back or diverged from trusted anchor')
        for row in doc['events']:
            state = state.apply(row['event'], row['data'], row['time_utc'])
        return doc

    def load(self, trusted):
        head = self.client.call('s3api', 'head-object', {'Bucket': self.bucket, 'Key': self.key,
                                                        'ChecksumMode': 'ENABLED', 'ExpectedBucketOwner': self.account})
        if not isinstance(head, dict) or not isinstance(head.get('Metadata'), dict):
            raise ValueError('ledger head metadata is unavailable')
        sha, checksum, size = head.get('Metadata', {}).get('sha256'), head.get('ChecksumSHA256'), head.get('ContentLength')
        etag, version = head.get('ETag'), head.get('VersionId')
        if (not isinstance(sha, str) or not HEX.fullmatch(sha)
                or checksum != base64.b64encode(bytes.fromhex(sha)).decode('ascii')
                or type(size) is not int or not 0 <= size <= MAX_LEDGER_BYTES
                or not isinstance(etag, str) or not etag or etag == '*'
                or not isinstance(version, str) or version in ('', 'null')):
            raise ValueError('ledger head lacks exact checksum, ETag or version')
        with tempfile.TemporaryDirectory(prefix='rove4k-global-ledger-') as temporary:
            path = Path(temporary) / 'ledger.json'
            response = self.client.get_file(self.bucket, self.key, path, etag, expected_owner=self.account)
            if not path.is_file() or path.stat().st_size > MAX_LEDGER_BYTES:
                raise ValueError('downloaded ledger is missing or too large')
            raw = path.read_bytes()
        if (len(raw) != size or hashlib.sha256(raw).hexdigest() != sha
                or response.get('ChecksumSHA256') != checksum or response.get('VersionId') != version):
            raise ValueError('downloaded ledger does not match the exact observed version')
        doc = self._parse(raw, trusted)
        rows = tuple(doc['events'])
        anchor = Anchor(len(rows) - 1, rows[-1]['sha256'] if rows else ZERO, self.authority, trusted.opening_sha256)
        return Snapshot(rows, doc['opening'], etag, version, anchor)

    def append(self, *, trusted, request_id, event, data, at, expected_head=None):
        if not isinstance(request_id, str) or not REQUEST.fullmatch(request_id):
            raise ValueError('unique bounded request identity required')
        if not isinstance(event, str) or not event.startswith('budget.v2.') or not isinstance(data, dict):
            raise ValueError('only explicit shared-budget events can be appended')
        timestamp(at)
        try:
            encoded_data = canonical(data)
            if len(encoded_data) > MAX_LEDGER_BYTES:
                raise ValueError('event data exceeds the bounded ledger size')
            fixed_data = json.loads(encoded_data, object_pairs_hook=_pairs)
        except (TypeError, UnicodeError, json.JSONDecodeError) as error:
            raise ValueError('event data must be bounded canonical JSON') from error
        current = self.load(trusted)
        # `trusted` is a rollback anchor and may name a prefix of the current
        # log. A serialized caller can additionally demand an exact current
        # head before submitting its event. If-Match then protects the
        # observed ETag from ordinary changes between this read and PUT;
        # it is not a fence against ABA or an independent single-writer proof.
        if expected_head is not None:
            if not isinstance(expected_head, Anchor):
                raise ValueError('expected head must be an anchor')
            if current.anchor != expected_head:
                raise LedgerConflict('current ledger head differs from the expected head')
        if request_id in current.opening['prior_request_ids'] or any(row['request_id'] == request_id for row in current.rows):
            raise ValueError('request already exists; reconcile rather than replaying side effects')
        body = {'campaign': self.campaign, 'seq': len(current.rows), 'previous_sha256': current.anchor.sha256,
                'event': event, 'data': fixed_data, 'time_utc': at, 'request_id': request_id}
        row = dict(body, sha256=digest(body))
        rows = [*current.rows, row]
        doc = {'format': 'rove4k-shared-budget-v1', 'campaign': self.campaign, 'account': self.account,
               'home_region': self.region, 'opening': current.opening, 'events': rows}
        raw = canonical(doc)
        if len(raw) > MAX_LEDGER_BYTES:
            raise ValueError('ledger snapshot exceeds the bounded size')
        self._parse(raw, trusted)
        sha = hashlib.sha256(raw).hexdigest()
        submitted = False
        try:
            with tempfile.TemporaryDirectory(prefix='rove4k-global-ledger-') as temporary:
                path = Path(temporary) / 'ledger.json'
                path.write_bytes(raw)
                submitted = True
                response = self.client.put_file_if_match(self.bucket, self.key, path, sha, current.etag,
                                                         expected_owner=self.account)
        except Exception as error:
            if submitted:
                code = getattr(error, 'code', None)
                if code in ('PreconditionFailed', 'ConditionalRequestConflict', '409', '412'):
                    raise LedgerConflict('conditional ledger conflict; do not release GO') from error
                raise LedgerUncertain('ledger write outcome unknown; reconcile request ' + request_id) from error
            raise
        checksum = base64.b64encode(bytes.fromhex(sha)).decode('ascii')
        if (not isinstance(response, dict) or response.get('ChecksumSHA256') != checksum or not isinstance(response.get('ETag'), str)
                or not response['ETag'] or response['ETag'] == '*'
                or not isinstance(response.get('VersionId'), str) or response['VersionId'] in ('', 'null')):
            raise LedgerUncertain('ledger write acknowledgement incomplete; reconcile request ' + request_id)
        try:
            confirmed = self.client.call('s3api', 'head-object', {'Bucket': self.bucket, 'Key': self.key,
                'VersionId': response['VersionId'], 'ChecksumMode': 'ENABLED', 'ExpectedBucketOwner': self.account})
        except Exception as error:
            raise LedgerUncertain('ledger version confirmation failed; reconcile request ' + request_id) from error
        if (not isinstance(confirmed, dict) or not isinstance(confirmed.get('Metadata'), dict)
                or confirmed.get('VersionId') != response['VersionId'] or confirmed.get('ETag') != response['ETag']
                or confirmed.get('ContentLength') != len(raw) or confirmed.get('ChecksumSHA256') != checksum
                or confirmed.get('Metadata', {}).get('sha256') != sha):
            raise LedgerUncertain('ledger version confirmation differs; reconcile request ' + request_id)
        return Snapshot(tuple(rows), current.opening, response['ETag'], response['VersionId'],
                        Anchor(row['seq'], row['sha256'], self.authority, trusted.opening_sha256))
