"""Exercise per-game league budget decisions against real Wave and ledger APIs.

This is a local trial path, not a scored league or an AWS launcher.  The
shared ledger and the caller's clocks are not authenticated, exclusive
multi-host ownership is not established, and a socket write is not remote
execution or physical settlement.  Nothing in this module grants production
GO, launch, settlement, or termination authority.  In particular, the
conservative $120 upper estimate is not the AWS invoice or credit balance.
"""
from __future__ import annotations

import base64
from contextlib import contextmanager
import hashlib
import json
import math
from pathlib import Path
import queue
import re
import sys
import threading
import time
import uuid

try:
    from .diagnostic_ledger_bridge import DiagnosticHost
    from .league_controller import _snapshot_state
    from .budget import valid_game_pair_id
    from . import global_budget as _global_budget
    from .shared_coordinator import SharedBudgetJournal
    from .wave import AsyncGateDecision, ReleaseFence, WaveExecutor, WaveJob
except ImportError:
    from diagnostic_ledger_bridge import DiagnosticHost
    from league_controller import _snapshot_state
    from budget import valid_game_pair_id
    import global_budget as _global_budget
    from shared_coordinator import SharedBudgetJournal
    from wave import AsyncGateDecision, ReleaseFence, WaveExecutor, WaveJob


# The public local-trial entrypoint is deliberately restricted to this fixed
# toy, run with Python's isolated mode, and to the in-memory S3 implementation
# below. It must not be used to send an unauthenticated GO to an actual engine.
_TRIAL_SOURCE = r'''import json, os, socket, sys, time
sock=socket.socket(fileno=int(os.environ['ROVE_START_FD']))
job=json.loads(os.environ['ROVE_START_JOB'])
assert os.environ.get('ROVE_START_PROTOCOL') == '2'
sock.sendall((json.dumps({'event':'READY','job':job,'white_clock_ms':1803000,'black_clock_ms':1803000})+'\n').encode())
data=b''
while b'\n' not in data:
    more=sock.recv(1024)
    if not more: sys.exit(3)
    data+=more
if data==b'ABORT\n': sys.exit(2)
kind,attempt,fence,sha,nonce=data.decode().strip().split(' ')
assert kind=='GO2' and attempt==job['attempt_id']
ack={'event':'GO2_ACCEPTED','attempt_id':attempt,'fence_id':fence,'job_sha256':sha,'nonce':nonce}
sock.sendall((json.dumps(ack)+'\n').encode())
time.sleep(.2)
'''
TRIAL_RUNNER = "import base64;exec(base64.b64decode(%r))" % base64.b64encode(_TRIAL_SOURCE.encode('ascii')).decode('ascii')


class OfflineS3Error(Exception):
    def __init__(self, code):
        self.code = code


class OfflineS3:
    """In-memory S3-shaped transport for local trials; performs no network I/O.

    It models an existing versioned object and ETag conditional writes.  It is
    not an AWS emulator, independently authenticated authority, or ABA fix.
    """
    region = 'ap-southeast-2'

    def __init__(self):
        self.doc = {'format': 'rove4k-shared-budget-v1', 'campaign': 'test-campaign',
                    'account': '123456789012', 'home_region': self.region,
                    'opening': {'prior_compute_usd': '0', 'prior_ancillary_usd': '0',
                        'prior_limit_confirmed': False, 'as_of': 900, 'source_sha256': 'a' * 64,
                        'excludes_opening_events': True, 'complete_identities': True,
                        'prior_game_ids': [], 'prior_pair_ids': [], 'prior_request_ids': [],
                        'prior_launch_tokens': [], 'prior_instance_ids': [], 'prior_receipts': [], 'events': []},
                    'events': []}
        self.versions = {}
        self.seq = 0
        self.conflict = False
        self.timeout_after_write = False
        self.error_after_write = None
        self.malformed_after_write = False
        self.fail_confirmation = False
        self.malformed_confirmation = False
        self._publish(_global_budget.canonical(self.doc))

    def _publish(self, body):
        self.seq += 1
        self.raw = body
        self.sha = hashlib.sha256(body).hexdigest()
        self.checksum = base64.b64encode(bytes.fromhex(self.sha)).decode('ascii')
        self.etag = '"' + self.sha + '"'
        self.version = 'version-' + str(self.seq)
        self.versions[self.version] = self._head()

    def _head(self):
        return {'Metadata': {'sha256': self.sha}, 'ChecksumSHA256': self.checksum,
                'ContentLength': len(self.raw), 'ETag': self.etag, 'VersionId': self.version}

    def call(self, service, operation, request):
        if (service, operation) != ('s3api', 'head-object') or request['ExpectedBucketOwner'] != '123456789012':
            raise ValueError('unexpected offline API request')
        version = request.get('VersionId')
        if version is not None:
            if self.fail_confirmation:
                raise OfflineS3Error('ObservationTimeout')
            if self.malformed_confirmation:
                return dict(self.versions[version], Metadata=None)
            return dict(self.versions[version])
        return self._head()

    def get_file(self, bucket, key, path, etag, *, expected_owner):
        if expected_owner != '123456789012' or etag != self.etag:
            raise OfflineS3Error('PreconditionFailed')
        Path(path).write_bytes(self.raw)
        return {'ChecksumSHA256': self.checksum, 'VersionId': self.version}

    def put_file_if_match(self, bucket, key, path, sha, etag, *, expected_owner):
        if expected_owner != '123456789012' or self.conflict or etag != self.etag:
            raise OfflineS3Error('PreconditionFailed')
        data = Path(path).read_bytes()
        if hashlib.sha256(data).hexdigest() != sha:
            raise ValueError('offline write checksum differs')
        self._publish(data)
        if self.timeout_after_write:
            raise OfflineS3Error('ObservationTimeout')
        if self.error_after_write:
            raise OfflineS3Error(self.error_after_write)
        if self.malformed_after_write:
            return None
        return {'ChecksumSHA256': self.checksum, 'VersionId': self.version, 'ETag': self.etag}


def _job_digest(job):
    raw = json.dumps({'identity': job.identity, 'start_job': job.start_job},
                     sort_keys=True, allow_nan=False, separators=(',', ':')).encode()
    return hashlib.sha256(raw).hexdigest()


class _TrialMailbox:
    """Serialize ledger calls in a worker; Wave callbacks never perform I/O.

    Allow decisions here are local simulation decisions, not authorization.
    One process may share a journal owner among host stages, but the S3 CAS
    and local lock do not constitute a cross-host fence.  Unknown writes are
    never retried, and authorized-but-unsettled games remain in the ledger.
    """
    provides_go_authority = False

    def __init__(self, owner, host, *, read_boot, now_utc, now_mono,
                 observe_interval, window_seconds):
        self.owner, self.host = owner, host
        self.read_boot, self.now_utc, self.now_mono = read_boot, now_utc, now_mono
        self.interval, self.window = observe_interval, window_seconds
        self._requests = queue.Queue(64)
        self._responses = queue.Queue(64)
        self._mutex = threading.Lock()
        self._gate_lock = threading.RLock()
        self._stop, self._drain = threading.Event(), threading.Event()
        self._drain_requested = threading.Event()
        self._pending = {}
        self._issued = {}
        self._transport_wait = {}
        self._seen = set()
        self._fault = None
        self._observations = []
        self._worker = threading.Thread(target=self._run, name='rove4k-trial-budget', daemon=True)

    def start(self):
        self._worker.start()

    def _record(self, event, data, at):
        return self.owner.record(request_id='trial-' + uuid.uuid4().hex,
                                 event=event, data=data, at=at)

    def _state(self, snapshot):
        return _snapshot_state(self.owner._store.campaign, snapshot)

    @contextmanager
    def _budget_gate(self):
        with self._gate_lock:
            try:
                yield
            finally:
                if self._drain_requested.is_set():
                    self._drain.set()

    def _record_observation(self):
        if self.read_boot() != self.host.boot_id:
            raise ValueError('host boot changed during local trial')
        # A nonblocking Wave release guard sees this lock as busy and denies
        # rather than letting the selector wait on an observation's I/O.
        with self._budget_gate():
            at = self.now_utc()
            snap = self._record('budget.v2.observe', {'scope': 'league-local-trial'}, at)
            state = self._state(snap)
            compute, upper = state.totals(at)
            matching = [r for r in state.active_instances
                        if r.charge.launch_token == self.host.launch_token and
                        r.charge.instance_id == self.host.instance_id and not r.closing]
            if len(matching) != 1:
                raise ValueError('trial host is not the bound active instance')
            if state.draining:
                self._drain_requested.set()
                self._drain.set()
            with self._mutex:
                self._observations.append({'compute_upper_usd': str(compute),
                                           'total_upper_usd': str(upper),
                                           'draining': state.draining})
        return state

    def request(self, job, observation):
        if not isinstance(job, WaveJob) or not isinstance(observation, dict):
            raise TypeError('Wave job and READY observation required')
        ready = observation.get('ready')
        if (observation.get('ready_monotonic') is None or not isinstance(ready, dict)
                or ready.get('event') != 'READY' or ready.get('job') != job.start_job):
            raise ValueError('runner READY does not match trial job')
        frozen = json.loads(json.dumps(job.start_job, sort_keys=True, allow_nan=False))
        digest = _job_digest(job)
        with self._mutex:
            if self._stop.is_set() or job.identity in self._seen:
                raise ValueError('trial mailbox closed or duplicate game')
            self._seen.add(job.identity)
            self._pending[job.identity] = digest
        if self._drain_requested.is_set():
            self._responses.put_nowait(AsyncGateDecision(job.identity, False))
        else:
            self._requests.put_nowait((job.identity, frozen, digest))

    def poll(self):
        if not self._worker.is_alive() and not self._stop.is_set():
            raise RuntimeError('trial worker unavailable')
        decisions = []
        while True:
            try:
                decision = self._responses.get_nowait()
            except queue.Empty:
                break
            with self._mutex:
                if decision.identity not in self._pending:
                    continue
                del self._pending[decision.identity]
            if self._drain_requested.is_set() and decision.allowed:
                decision = AsyncGateDecision(decision.identity, False)
            decisions.append(decision)
        if self._drain_requested.is_set():
            with self._mutex:
                remaining = tuple(self._pending)
                self._pending.clear()
            decisions.extend(AsyncGateDecision(identity, False) for identity in remaining)
        return decisions

    def on_drain(self, reason, job, observation):
        # Never wait for network I/O or a worker-held gate on the selector.
        # A send already inside the gate linearizes before the drain. The
        # request flag nevertheless prevents any later gate from starting.
        self._drain_requested.set()
        if self._gate_lock.acquire(blocking=False):
            try:
                self._drain.set()
            finally:
                self._gate_lock.release()

    @contextmanager
    def release_guard(self, job, observation, fence):
        """Order a locally observed drain and one nonblocking socket write.

        The Wave selector must never wait for the budget worker: a busy lock
        returns false. This guard does not serialize a remote host or make
        an external invoice and a socket write atomic.
        """
        acquired = self._gate_lock.acquire(blocking=False)
        try:
            if not acquired:
                yield False if (self._stop.is_set() or self._drain_requested.is_set()
                                or self._fault is not None) else None
            else:
                yield self.can_release(job, observation, fence)
        finally:
            if acquired:
                if self._drain_requested.is_set():
                    self._drain.set()
                self._gate_lock.release()

    def can_release(self, job, observation, fence):
        """Nonblocking local check immediately before a trial GO write.

        This is not an atomic cross-host fence; another owner may change the
        budget immediately after this check. Production GO remains disabled.
        """
        if self._stop.is_set() or self._drain_requested.is_set() or self._fault is not None:
            return False
        with self._mutex:
            expected = self._issued.get(job.identity)
            return (expected == (fence.fence_id, _job_digest(job))
                    and not self._stop.is_set() and not self._drain_requested.is_set()
                    and self._fault is None)

    def transport(self, job, observation):
        # A local socket write does not establish remote receipt or settlement.
        # The ledger deliberately retains the authorized game as unsettled.
        with self._mutex:
            signal = self._transport_wait.get(job.identity)
        if signal is not None:
            signal.set()

    def _deny(self, identity):
        self._responses.put_nowait(AsyncGateDecision(identity, False))

    def _run(self):
        next_observation = 0.0
        while not self._stop.is_set():
            try:
                current = self.now_mono()
                if not self._drain_requested.is_set() and current >= next_observation:
                    self._record_observation()
                    if self._stop.is_set():
                        break
                    next_observation = current + self.interval
                try:
                    identity, metadata, digest = self._requests.get(timeout=min(self.interval, .05))
                except queue.Empty:
                    continue
                if self._stop.is_set():
                    break
                if self._drain_requested.is_set():
                    self._deny(identity)
                    continue
                with self._budget_gate():
                    if self._stop.is_set() or self._drain_requested.is_set():
                        self._deny(identity)
                        continue
                    at = self.now_utc()
                    self._record('budget.v2.game_admitted', {
                        'game_id': metadata['game'], 'pair_id': metadata['pair'],
                        'launch_token': self.host.launch_token}, at)
                    if self._stop.is_set() or self._drain_requested.is_set():
                        self._deny(identity)
                        continue
                    at = self.now_utc()
                    expiry = at + self.window
                    self._record('budget.v2.game_release_authorized', {
                        'game_id': metadata['game'], 'valid_until_utc': expiry}, at)
                    # Reject a window consumed by a slow write; do not undo or
                    # retry the persisted admission/authorization.
                    remaining = expiry - self.now_utc()
                    if self._stop.is_set() or self._drain_requested.is_set() or remaining <= 0:
                        self._deny(identity)
                        self.on_drain('window_or_stop', None, {})
                        continue
                    now = self.now_mono()
                    fence = ReleaseFence(identity, 'trial-' + uuid.uuid4().hex, digest,
                                         now, now + min(self.window, remaining))
                    signal = threading.Event()
                    with self._mutex:
                        self._issued[identity] = (fence.fence_id, digest)
                        self._transport_wait[identity] = signal
                    self._responses.put_nowait(AsyncGateDecision(identity, True, fence))
                # Keep observing while awaiting transport. A concurrent slow
                # observation denies release without blocking the selector.
                while not (signal.is_set() or self._stop.is_set() or self._drain_requested.is_set()
                           or self.now_mono() >= fence.expires_monotonic):
                    current = self.now_mono()
                    if current >= next_observation:
                        self._record_observation()
                        next_observation = self.now_mono() + self.interval
                    else:
                        signal.wait(min(.05, max(0.0, next_observation - current)))
            except Exception as error:
                with self._mutex:
                    self._fault = type(error).__name__
                self.on_drain('ledger_error', None, {})

    def close(self, timeout=2.0):
        self._stop.set()
        self._worker.join(timeout)
        return not self._worker.is_alive()

    def report(self):
        with self._mutex:
            return {'draining': self._drain.is_set(), 'drain_requested': self._drain_requested.is_set(), 'fault': self._fault,
                    'observations': list(self._observations)}


class LeagueStage:
    """Run an explicitly local, non-scoring league scheduling trial.

    P16 reserves up to eleven slot IDs and P192 one.  Slot IDs are planning
    labels only: this class does not attach or verify cgroups, affinities,
    memory policy, CPU/NUMA placement, TT allocations, or engine strength.
    The caller must perform those operations and retain their own evidence.
    A production scoring entrypoint does not exist here.
    """
    provides_go_authority = False
    provides_termination_authority = False

    def __init__(self, owner, host, profile, *, read_boot, now_utc=time.time,
                 now_mono=time.monotonic, observe_interval=1.0, window_seconds=2.0):
        if not isinstance(owner, SharedBudgetJournal) or not isinstance(host, DiagnosticHost):
            raise TypeError('actual shared journal owner and host identity required')
        if type(owner._store.client) is not OfflineS3:
            raise ValueError('local trial requires the in-memory offline ledger transport')
        if profile not in ('test-p16', 'test-p192'):
            raise ValueError('only P16 and P192 local trials are supported')
        if any(not callable(value) for value in (read_boot, now_utc, now_mono)):
            raise TypeError('explicit callable clocks and boot observer required')
        if (type(observe_interval) not in (int, float) or not math.isfinite(observe_interval)
                or not .01 <= observe_interval <= 60 or type(window_seconds) not in (int, float)
                or not math.isfinite(window_seconds) or not .1 <= window_seconds <= 60):
            raise ValueError('bounded local observation interval and GO window required')
        self.owner, self.host, self.profile = owner, host, profile
        self.read_boot, self.now_utc, self.now_mono = read_boot, now_utc, now_mono
        self.interval, self.window = observe_interval, window_seconds
        self._mailbox = None
        self._stage_lock = threading.Lock()
        self._busy = False

    def close_pending_worker(self, timeout=2.0):
        """Keep the original worker handle until any pending I/O finishes.

        The shared journal is caller-owned and must stay open while this
        returns false.  Closing a socket or retrying the remote write cannot
        resolve an unknown outcome.
        """
        with self._stage_lock:
            if self._busy:
                raise ValueError('cannot close the worker while its wave is active')
        return self._close_worker(timeout)

    def _close_worker(self, timeout=2.0):
        if self._mailbox is None:
            return True
        if self._mailbox.close(timeout):
            self._mailbox = None
            return True
        return False

    def run_wave(self, jobs, wall_seconds, *, intent_owner, on_event=None, local_trial=False):
        with self._stage_lock:
            if self._busy or self._mailbox is not None:
                raise ValueError('previous trial worker must be reconciled before reuse')
            self._busy = True
        try:
            return self._run_wave(jobs, wall_seconds, intent_owner=intent_owner,
                                  on_event=on_event, local_trial=local_trial)
        finally:
            with self._stage_lock:
                self._busy = False

    def _run_wave(self, jobs, wall_seconds, *, intent_owner, on_event=None, local_trial=False):
        if local_trial is not True:
            raise ValueError('this entrypoint is restricted to explicit local trials')
        if not isinstance(jobs, (list, tuple)) or not jobs or len(jobs) > (11 if self.profile == 'test-p16' else 1):
            raise ValueError('P16 permits at most eleven jobs; P192 permits one')
        campaign = self.owner._store.campaign
        slots, games, attempts = set(), set(), set()
        for job in jobs:
            if not isinstance(job, WaveJob):
                raise TypeError('WaveJob required')
            if (len(job.argv) != 5 or Path(job.argv[0]).resolve() != Path(sys.executable).resolve()
                    or tuple(job.argv[1:]) != ('-I', '-c', TRIAL_RUNNER, 'ok') or job.env):
                raise ValueError('local trial permits only the fixed isolated Python toy runner')
            m = job.start_job
            slot = m.get('slot_id')
            if (type(slot) is not int or not 0 <= slot < (11 if self.profile == 'test-p16' else 1)
                    or slot in slots or m.get('campaign') != campaign or not valid_game_pair_id(m.get('game'))
                    or m['game'] in games or not valid_game_pair_id(m.get('pair'))
                    or m.get('instance_id') != self.host.instance_id or m.get('boot_id') != self.host.boot_id
                    or m.get('launch_token') != self.host.launch_token
                    or type(m.get('attempt')) is not int or m['attempt'] < 0
                    or not isinstance(m.get('attempt_id'), str)
                    or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{15,127}', m['attempt_id'])
                    or m['attempt_id'] in attempts):
                raise ValueError('job slot, host, game, pair or attempt binding differs')
            slots.add(slot)
            games.add(m['game'])
            attempts.add(m['attempt_id'])
        if self.read_boot() != self.host.boot_id:
            raise ValueError('trial host boot differs')
        mailbox = _TrialMailbox(self.owner, self.host, read_boot=self.read_boot,
                                now_utc=self.now_utc, now_mono=self.now_mono,
                                observe_interval=self.interval, window_seconds=self.window)
        # Establish an actual budget/host observation before starting children.
        mailbox._record_observation()
        if mailbox._drain.is_set():
            return {'mode': 'local-trial', 'profile': self.profile, 'results': [],
                    'budget': mailbox.report(), 'worker_closed': True,
                    'scored_go_allowed': False, 'remote_authority_verified': False,
                    'placement_verified': False, 'billing_verified': False,
                    'physical_settlement_verified': False}
        self._mailbox = mailbox
        mailbox.start()
        try:
            results = WaveExecutor().run_wave(list(jobs), wall_seconds, async_authorizer=mailbox,
                intent_owner=intent_owner, observe_transport=mailbox.transport,
                on_drain=mailbox.on_drain, on_event=on_event)
        finally:
            worker_closed = self._close_worker()
        return {'mode': 'local-trial', 'profile': self.profile, 'results': results,
                'budget': mailbox.report(), 'worker_closed': worker_closed,
                'scored_go_allowed': False, 'remote_authority_verified': False,
                'placement_verified': False, 'billing_verified': False,
                'physical_settlement_verified': False}
