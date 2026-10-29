"""Nonblocking diagnostic bridge from READY gates to the shared journal.

Only the background thread talks to S3 or fsyncs a Journal. This component
records diagnostic observation events and *always* denies GO. A locally pinned
instance/boot/attempt/fence identity is diagnostic metadata, not proof of a
remote owner, a unique distributed fence, an authenticated clock or a GO
receipt. No scored release, admission, or physical settlement is performed.
An uncertain write stays quarantined in SharedBudgetJournal; never retry it.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import queue
import re
import threading
import time
import uuid

try:
    from .shared_coordinator import SharedBudgetJournal
    from .wave import AsyncGateDecision, WaveJob
except ImportError:
    from shared_coordinator import SharedBudgetJournal
    from wave import AsyncGateDecision, WaveJob

_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}")
_ATTEMPT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{15,127}")
_INSTANCE = re.compile(r"i-[a-z0-9]{3,32}")


@dataclass(frozen=True)
class DiagnosticHost:
    instance_id: str
    boot_id: str
    launch_token: str

    def __post_init__(self):
        if not isinstance(self.instance_id, str) or not _INSTANCE.fullmatch(self.instance_id):
            raise ValueError("invalid diagnostic instance identity")
        if not isinstance(self.launch_token, str) or not 8 <= len(self.launch_token) <= 64:
            raise ValueError("invalid diagnostic launch identity")
        try:
            canonical = str(uuid.UUID(self.boot_id))
        except (ValueError, AttributeError, TypeError) as error:
            raise ValueError("invalid diagnostic boot identity") from error
        if canonical != self.boot_id:
            raise ValueError("diagnostic boot identity must be canonical")


def current_boot_id():
    """Read the current Linux boot identity; this does not attest the host."""
    return Path('/proc/sys/kernel/random/boot_id').read_text(encoding='ascii').strip()


def binding(job, host):
    """Validate and pin one proposal. A proposal is not a release fence."""
    if not isinstance(job, WaveJob) or not isinstance(host, DiagnosticHost):
        raise TypeError("exact job and diagnostic host required")
    return _binding(job.identity, job.start_job, host)


def _binding(identity, meta, host):
    if not _ID.fullmatch(identity):
        raise ValueError("invalid shared ledger game identity")
    attempt, fence_id = meta.get('attempt_id'), meta.get('probe_fence_id')
    if not isinstance(attempt, str) or not _ATTEMPT.fullmatch(attempt):
        raise ValueError("explicit attempt identity required")
    if not isinstance(fence_id, str) or not _ID.fullmatch(fence_id):
        raise ValueError("explicit diagnostic fence identity required")
    if (meta.get('boot_id'), meta.get('instance_id'), meta.get('launch_token')) != (
            host.boot_id, host.instance_id, host.launch_token):
        raise ValueError("job does not match the pinned diagnostic host")
    raw = json.dumps({'identity': identity, 'start_job': meta}, sort_keys=True,
                     allow_nan=False, separators=(',', ':')).encode('utf-8')
    return {'game_id': identity, 'attempt_id': attempt, 'probe_fence_id': fence_id,
            'job_sha256': hashlib.sha256(raw).hexdigest(), 'instance_id': host.instance_id,
            'boot_id': host.boot_id, 'launch_token': host.launch_token}


class DiagnosticLedgerMailbox:
    """Actual Wave mailbox backed by a serialized journal observation worker.

    request/poll/on_drain perform bounded local operations and never call the
    remote store. The worker journals a bound diagnostic observation and emits
    a denial; no API or caller option can convert this into a GO approval.
    On ambiguous I/O the underlying owner remains blocked and the bridge does
    not retry. Call close and confirm its return before closing the Journal: a
    network call already in flight cannot be safely stopped by the selector.
    """
    provides_go_authority = False

    def __init__(self, owner, host, *, read_boot=current_boot_id, now_utc=time.time, max_pending=16):
        if not isinstance(owner, SharedBudgetJournal) or not isinstance(host, DiagnosticHost):
            raise TypeError("actual journal owner and pinned host required")
        if owner.provides_go_authority is not False:
            raise ValueError("diagnostic mailbox must not impersonate GO authority")
        if type(max_pending) is not int or not 1 <= max_pending <= 64:
            raise ValueError("bounded diagnostic mailbox size required")
        if not callable(read_boot) or not callable(now_utc) or read_boot() != host.boot_id:
            raise ValueError("current boot does not match diagnostic host")
        self._owner, self.host, self._max_pending = owner, host, max_pending
        self._now_utc, self._read_boot = now_utc, read_boot
        self._requests = queue.Queue(max_pending)
        self._decisions = queue.Queue(max_pending)
        self._mutex = threading.Lock()
        self._stop = threading.Event()
        self._draining = threading.Event()
        self._ids, self._attempts, self._fences = set(), set(), set()
        self._records = []
        self._fault = None
        self._worker = threading.Thread(target=self._run, name='rove4k-diagnostic-ledger', daemon=True)
        self._worker.start()

    def request(self, job, observation):
        if not isinstance(job, WaveJob):
            raise TypeError('exact Wave job required')
        if not isinstance(observation, dict) or observation.get('ready_monotonic') is None:
            raise ValueError("a READY observation is required")
        ready = observation.get('ready')
        if not isinstance(ready, dict) or ready.get('event') != 'READY' or not isinstance(ready.get('job'), dict):
            raise ValueError('exact runner READY job is required')
        expected = json.dumps(job.start_job, sort_keys=True, allow_nan=False, separators=(',', ':'))
        received = json.dumps(ready['job'], sort_keys=True, allow_nan=False, separators=(',', ':'))
        if expected != received:
            raise ValueError('READY job differs from diagnostic proposal')
        value = _binding(job.identity, json.loads(expected), self.host)
        with self._mutex:
            if self._stop.is_set() or self._draining.is_set():
                raise ValueError("diagnostic mailbox is closed or draining")
            if len(self._ids) >= self._max_pending:
                raise ValueError('diagnostic wave request limit reached')
            if (value['game_id'] in self._ids or value['attempt_id'] in self._attempts
                    or value['probe_fence_id'] in self._fences):
                raise ValueError("duplicate game, attempt or diagnostic fence")
            # put_nowait is bounded and has no network or filesystem operation.
            self._requests.put_nowait(value)
            self._ids.add(value['game_id'])
            self._attempts.add(value['attempt_id'])
            self._fences.add(value['probe_fence_id'])

    def poll(self):
        if self._fault is not None:
            raise RuntimeError(self._fault)
        if self._stop.is_set() or not self._worker.is_alive():
            raise RuntimeError('diagnostic worker is closed or unavailable')
        rows = []
        while True:
            try:
                rows.append(self._decisions.get_nowait())
            except queue.Empty:
                return rows

    def on_drain(self, reason, job, observation):
        """Local stop signal, not proof that any other host has been fenced."""
        self._draining.set()

    def transport(self, job, observation):
        """This denial-only bridge must never observe a GO transport."""
        raise ValueError("diagnostic mailbox cannot observe GO delivery")

    def records(self):
        with self._mutex:
            return tuple(json.loads(json.dumps(row)) for row in self._records)

    def _run(self):
        while not self._stop.is_set():
            try:
                value = self._requests.get(timeout=.05)
            except queue.Empty:
                continue
            if self._draining.is_set() or self._stop.is_set():
                continue
            canonical = json.dumps(value, sort_keys=True, separators=(',', ':')).encode('utf-8')
            request_id = 'diagnostic-' + hashlib.sha256(canonical).hexdigest()
            result = {'binding': value, 'status': 'observed', 'request_id': request_id}
            try:
                if self._read_boot() != self.host.boot_id:
                    raise ValueError('diagnostic host boot changed')
                at = self._now_utc()
                if type(at) not in (float, int) or not math.isfinite(at):
                    raise ValueError('invalid observation timestamp')
                self._owner.record(request_id=request_id, event='budget.v2.observe',
                    data={'scope': 'diagnostic-wave-request', **value}, at=at)
            except Exception as error:
                result.update(status='unresolved', error=type(error).__name__)
            with self._mutex:
                self._records.append(result)
            if not self._draining.is_set() and not self._stop.is_set():
                # Regardless of whether recording succeeded there is no GO authority.
                try:
                    self._decisions.put_nowait(AsyncGateDecision(value['game_id'], False))
                except queue.Full:
                    self._fault = 'diagnostic decision queue is full'
                    self._draining.set()
            if result['status'] != 'observed':
                self._draining.set()

    def close(self, timeout=1.0):
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout < 0:
            raise ValueError('invalid worker close timeout')
        self._stop.set()
        self._worker.join(timeout)
        return not self._worker.is_alive()
