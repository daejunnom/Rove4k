"""Own one initialization-isolated wave of patched Fastchess processes.

This module does not qualify artifacts or score games. The campaign controller
must do both. Before GO any failure aborts the whole unstarted wave. In the
per-game authorization path, a denied or uncertain GO blocks later local GO
writes while already sent or uncertain games retain their original owners.
Other runtime failures can still abort the wave and require reconciliation.

Callbacks execute on the controller thread and must not wait on network I/O.
Each runner gets an independent session/process group and a private gate FD.
The optional drain callback is only a best-effort local notification, not a
durable or global fence. It must enqueue without blocking; an ordinary callback
exception is recorded, while process-level interrupts retain abort semantics.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from contextlib import nullcontext
import hashlib
import json
import math
import os
from pathlib import Path
import re
import secrets
import selectors
import signal
import socket
import subprocess
import sys
import time
from typing import Callable, Mapping

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[3]
CLOCK_MS = 1_803_000
ATTEMPT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{15,127}")


class WaveAbort(RuntimeError):
    """A controller policy may raise this from a callback to cancel the wave."""


@dataclass(frozen=True)
class WaveJob:
    identity: str
    argv: tuple[str, ...]
    env: Mapping[str, str]
    start_job: dict
    out: Path

    def __post_init__(self):
        if not self.identity or any(c in self.identity for c in "\x00\r\n"):
            raise ValueError("a stable global job identity is required")
        if not self.argv or not Path(self.argv[0]).is_absolute():
            raise ValueError("absolute runner/placement executable required")
        if any(not isinstance(arg, str) or any(c in arg for c in "\x00\r\n") for arg in self.argv):
            raise ValueError("invalid runner argument")
        if not isinstance(self.start_job, dict) or not self.start_job:
            raise ValueError("nonempty job metadata object required")
        encoded = json.dumps(self.start_job, allow_nan=False, separators=(",", ":"))
        if len(encoded.encode("utf-8")) > 4096:
            raise ValueError("job metadata exceeds the runner gate limit")
        if not isinstance(self.out, Path) or not self.out.is_absolute():
            raise ValueError("absolute external attempt directory required")
        for key, value in self.env.items():
            if not isinstance(key, str) or not isinstance(value, str) or "=" in key or not key or "\x00" in key + value:
                raise ValueError("invalid process environment override")
        object.__setattr__(self, "env", dict(self.env))
        object.__setattr__(self, "start_job", json.loads(encoded))

    @property
    def id(self):
        return self.identity


@dataclass(frozen=True)
class ReleaseFence:
    """A caller-supplied local-clock GO window, not an authorization proof.

    ``fence_id`` is a non-secret audit identity, never a bearer credential.
    Monotonic times are meaningful only in the current host/boot clock domain.
    A caller must independently authenticate, fence and translate any remote
    coordinator decision; this type validates only its local representation.
    The coordinator also owns globally unique attempt/fence IDs and replay
    prevention. Matching this object's fields cannot establish either one.
    """
    game_id: str
    fence_id: str
    job_sha256: str
    not_before_monotonic: float
    expires_monotonic: float

    def __post_init__(self):
        if (not isinstance(self.game_id, str) or not self.game_id or
                any(c in self.game_id for c in "\x00\r\n") or
                not isinstance(self.fence_id, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,96}", self.fence_id) or
                not isinstance(self.job_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", self.job_sha256)):
            raise ValueError("explicit game and non-secret fence identities required")
        if any(type(value) not in (int, float) or not math.isfinite(value) for value in
               (self.not_before_monotonic, self.expires_monotonic)):
            raise ValueError("finite local monotonic fence bounds required")
        if (self.not_before_monotonic < 0 or self.expires_monotonic <= self.not_before_monotonic
                or self.expires_monotonic - self.not_before_monotonic > 60):
            raise ValueError("fence window must be positive and at most 60 seconds")


@dataclass(frozen=True)
class AsyncGateDecision:
    """One nonblocking owner response; it is not proof of global authority."""
    identity: str
    allowed: bool
    fence: ReleaseFence | None = None

    def __post_init__(self):
        if (not isinstance(self.identity, str) or not self.identity or type(self.allowed) is not bool
                or (self.allowed and type(self.fence) is not ReleaseFence)
                or (not self.allowed and self.fence is not None)):
            raise ValueError("an allowed decision requires its exact fence; denial must not have one")


@dataclass(frozen=True)
class AsyncIntentDecision:
    """Local owner reports an intent append; it is not global authority.

    ``journal_sha256`` identifies the owner-reported durable record. The
    campaign recovery path must read and validate that journal independently.
    """
    identity: str
    intent: dict
    journal_seq: int
    journal_sha256: str

    def __post_init__(self):
        if (not isinstance(self.identity, str) or not self.identity or not isinstance(self.intent, dict)
                or type(self.journal_seq) is not int or self.journal_seq < 0
                or not isinstance(self.journal_sha256, str)
                or not re.fullmatch(r"[0-9a-f]{64}", self.journal_sha256)):
            raise ValueError("bounded local durable intent receipt required")


def _boot_id():
    return Path("/proc/sys/kernel/random/boot_id").read_text().strip()


def intent_payload(job, observation, *, boot_id):
    """Return the exact non-secret pre-send binding for an intent owner."""
    if (not isinstance(boot_id, str) or not boot_id
            or type(observation.get("pid")) is not int or observation["pid"] <= 0
            or type(observation.get("start_ticks")) is not int or observation["start_ticks"] < 0
            or not isinstance(observation.get("ready"), dict)
            or not _same_json(observation["ready"].get("job"), job.start_job)
            or not isinstance(observation.get("gate_fence"), dict)
            or not isinstance(observation.get("gate_receipt_expected"), dict)):
        raise ValueError("complete pre-send runner, job and fence binding required")
    payload = {"identity": job.identity, "job": job.start_job, "ready": observation["ready"],
               "fence": observation["gate_fence"], "receipt": observation["gate_receipt_expected"],
               "pid": observation["pid"], "start_ticks": observation["start_ticks"], "boot_id": boot_id}
    return json.loads(json.dumps(payload, allow_nan=False, separators=(",", ":")))


@dataclass
class _Channel:
    name: str
    pipe: object
    path: Path
    target: object
    stored: int = 0
    total: int = 0
    eof: bool = False
    error: str | None = None


@dataclass
class _Child:
    job: WaveJob
    expected: dict
    observation: dict
    process: subprocess.Popen | None = None
    control: socket.socket | None = None
    channels: list[_Channel] = field(default_factory=list)
    gate_bytes: bytes = b""
    last_tick: float = 0.0
    completion_notified: bool = False


def _terminal_gate_class(observation):
    """Classify the gate only; no chess result or score is inferred."""
    if observation.get("gate_cancelled") is True:
        uncertain_auth = (observation.get("gate_authorized") is True or
                          observation.get("gate_authorization_unknown") is True or
                          observation.get("gate_intent_requested") is True)
        return "cancelled", "cancelled_unreconciled" if uncertain_auth else "cancelled_before_go"
    if (observation.get("gate_receipt_required") and observation.get("gate_receipt") != "matched" or
            observation.get("gate_transport") == "uncertain" or
            observation.get("gate_transport_observation_error") or
            observation.get("gate_release_event_error")):
        return "delivery_uncertain", "delivery_unresolved"
    return "completed", "completed"


def _release_individually(children, snapshot, authorize_go, observe_transport, emit, *, deadline=None,
                          notify_drain=None, release_fence=None, wire_go=None, pre_send=None, release_guard=None):
    """Try budget-owner authorization immediately before each private gate write.

    The callbacks must be supplied by a durable, serialized owner. This helper
    cannot prove cross-host atomicity or that a successful socket write was read
    by the runner: an actual runner/engine GO requires separate evidence.
    A denial or callback/transport fault prevents later GO writes. Already sent
    or possibly sent games are not signalled here and must be physically settled.
    A release_fence window is checked locally immediately before attempting the
    socket write. It cannot make that check atomic with delivery, establish a
    trusted clock, or revoke other hosts' authorizations.
    """
    def cancel(child):
        child.observation.setdefault("gate_cancel_started_monotonic", time.monotonic())
        if child.control is None:
            return
        try:
            child.control.sendall(b"ABORT\n")
        except OSError as error:
            child.observation["gate_cancel_error"] = repr(error)
            try:
                child.control.shutdown(socket.SHUT_WR)
            except OSError:
                pass

    draining = False

    def begin_drain(child, reason):
        nonlocal draining
        if draining:
            return
        draining = True
        child.observation["drain_reason"] = reason
        if notify_drain is not None:
            notify_drain(child, reason)

    for child in children:
        obs = child.observation
        obs.update(gate_authorized=False, gate_authorization_unknown=False,
                   gate_transport="not_attempted", gate_cancelled=False)
        if not draining and deadline is not None and time.monotonic() >= deadline:
            obs["gate_denied_reason"] = "wave deadline expired before authorization"
            begin_drain(child, "admission_deadline")
        if not draining:
            try:
                decision = authorize_go(child.job, snapshot(child))
                allowed = decision is True
                if decision is not True and decision is not False:
                    # A malformed reply cannot prove whether the durable owner
                    # recorded an authorization before returning it.
                    obs["gate_authorization_unknown"] = True
                    obs["gate_authorization_error"] = "non-boolean authorization response"
            except Exception as error:
                # The owner might have committed before its response failed.
                obs["gate_authorization_unknown"] = True
                obs["gate_authorization_error"] = repr(error)
                allowed = False
            if allowed:
                obs["gate_authorized"] = True
                if deadline is not None and time.monotonic() >= deadline:
                    obs["gate_transport_error"] = "wave deadline expired after authorization"
                    obs["gate_cancelled"] = True
                    begin_drain(child, "deadline_after_authorization")
                    cancel(child)
                elif child.control is None:
                    obs["gate_transport"] = "not_attempted"
                    obs["gate_transport_error"] = "runner gate closed before GO"
                    cancel(child)
                    begin_drain(child, "gate_unavailable")
                else:
                    fence = None
                    if release_fence is not None:
                        try:
                            attempt_id = child.expected.get("attempt_id")
                            if not isinstance(attempt_id, str) or not ATTEMPT_ID.fullmatch(attempt_id):
                                raise ValueError("explicit non-secret unique attempt identity required")
                            binding = json.dumps({"identity": child.job.identity, "start_job": child.expected},
                                                 sort_keys=True, allow_nan=False, separators=(",", ":")).encode("utf-8")
                            obs["gate_fence_binding_sha256"] = hashlib.sha256(binding).hexdigest()
                            fence = release_fence(child.job, snapshot(child))
                            if (type(fence) is not ReleaseFence or fence.game_id != child.job.identity or
                                    fence.job_sha256 != obs["gate_fence_binding_sha256"]):
                                raise ValueError("exact per-game release fence required")
                            obs["gate_fence"] = {"game_id": fence.game_id, "fence_id": fence.fence_id, "job_sha256": fence.job_sha256,
                                "not_before_monotonic": fence.not_before_monotonic,
                                "expires_monotonic": fence.expires_monotonic}
                        except Exception as error:
                            obs["gate_fence_error"] = repr(error)
                            obs["gate_cancelled"] = True
                            begin_drain(child, "release_fence_unavailable")
                            cancel(child)
                            continue
                    # Re-read after the fence callback: a valid authorization
                    # may expire while that callback is running.
                    send_started = time.monotonic()
                    if deadline is not None and send_started >= deadline:
                        obs["gate_transport_error"] = "wave deadline expired before GO attempt"
                        obs["gate_cancelled"] = True
                        begin_drain(child, "deadline_before_go")
                        cancel(child)
                        continue
                    if fence is not None and not (fence.not_before_monotonic <= send_started < fence.expires_monotonic):
                        obs["gate_fence_error"] = "fence is not valid at the local GO attempt"
                        obs["gate_cancelled"] = True
                        begin_drain(child, "release_fence_not_valid")
                        cancel(child)
                        continue
                    # A failed sendall can have written a prefix or all bytes.
                    # Closing only the write side makes an incomplete gate see
                    # EOF; a runner that received complete GO may still run.
                    command = b"GO\n"
                    if wire_go is not None:
                        try:
                            command = wire_go(child, fence)
                            if not isinstance(command, bytes) or not command.endswith(b"\n") or len(command) > 512:
                                raise ValueError("invalid bounded GO command")
                        except Exception as error:
                            obs["gate_wire_error"] = repr(error)
                            obs["gate_cancelled"] = True
                            begin_drain(child, "invalid_gate_command")
                            cancel(child)
                            continue
                    failure = None
                    try:
                        guard = (release_guard(child.job, snapshot(child), fence)
                                 if release_guard is not None else nullcontext(True))
                        with guard as held:
                            if held is None and release_guard is not None:
                                failure = "release_guard_busy"
                            elif held is not True:
                                obs["gate_pre_send_error"] = "release guard unavailable"
                                failure = "release_recheck_failed"
                            elif pre_send is not None and pre_send(child.job, snapshot(child), fence) is not True:
                                obs["gate_pre_send_error"] = "release recheck denied or indeterminate"
                                failure = "release_recheck_failed"
                            else:
                                send_started = time.monotonic()
                                if deadline is not None and send_started >= deadline:
                                    obs["gate_transport_error"] = "wave deadline expired while preparing GO"
                                    failure = "deadline_before_go"
                                elif fence is not None and not (fence.not_before_monotonic <= send_started < fence.expires_monotonic):
                                    obs["gate_fence_error"] = "fence expired while preparing GO"
                                    failure = "release_fence_not_valid"
                                elif (obs.get("gate_intent_required") is True and
                                      (type(obs.get("gate_receipt_deadline")) not in (int, float)
                                       or send_started >= obs["gate_receipt_deadline"])):
                                    obs["gate_intent_error"] = "receipt window expired immediately before GO"
                                    failure = "durable_intent_window_expired"
                                else:
                                    obs["gate_transport"] = "uncertain"
                                    obs["gate_send_started_monotonic"] = send_started
                                    child.control.sendall(command)
                                    finished = time.monotonic()
                                    obs.update(gate_transport="sent", gate_released=True,
                                               released_monotonic=finished, status="running")
                                    if fence is not None and (not math.isfinite(finished) or finished < send_started or finished >= fence.expires_monotonic
                                            or (deadline is not None and finished >= deadline)):
                                        obs["gate_transport"] = "uncertain"
                                        obs["gate_fence_send_time_uncertain"] = True
                                        failure = "release_fence_send_time_uncertain"
                    except Exception as error:
                        if obs["gate_transport"] in ("sent", "uncertain"):
                            obs["gate_transport"] = "uncertain"
                            obs["gate_transport_error"] = repr(error)
                            failure = "go_transport_uncertain"
                        else:
                            obs["gate_pre_send_error"] = repr(error)
                            failure = "release_recheck_failed"
                    if failure is not None:
                        if failure == "release_guard_busy":
                            return "guard_busy"
                        begin_drain(child, failure)
                        if obs["gate_transport"] == "not_attempted":
                            obs["gate_cancelled"] = True
                            cancel(child)
                            continue
                        try:
                            child.control.shutdown(socket.SHUT_WR)
                        except OSError:
                            pass
                    try:
                        # Only transport state is reported, never actual GO receipt.
                        observe_transport(child.job, snapshot(child))
                    except Exception as error:
                        obs["gate_transport_observation_error"] = repr(error)
                        begin_drain(child, "transport_observation_failed")
                    if obs["gate_transport"] == "sent":
                        try:
                            emit("released", child)
                        except WaveAbort as error:
                            obs["gate_release_event_error"] = str(error)
                            begin_drain(child, "release_event_failed")
                # Authorized games remain unsettled even if no GO was sent.
                if obs["gate_transport"] == "not_attempted":
                    obs["gate_cancelled"] = True
                continue
            obs.setdefault("gate_denied_reason", "release authorization denied")
            begin_drain(child, "authorization_uncertain" if obs["gate_authorization_unknown"] else "authorization_denied")
        obs["gate_cancelled"] = True
        obs.setdefault("gate_denied_reason", "earlier release denied or uncertain")
        cancel(child)
    return draining


def _proc_identity(pid: int) -> dict | None:
    try:
        raw = Path(f"/proc/{pid}/stat").read_text()
    except (FileNotFoundError, ProcessLookupError):
        return None
    values = raw[raw.rfind(")") + 2:].split()
    return {"pid": pid, "state": values[0], "pgid": int(values[2]),
            "session": int(values[3]), "start_ticks": int(values[19])}


def _same_json(left, right) -> bool:
    # Python equality aliases booleans/integers/floats. READY must echo the
    # complete JSON metadata, including each value's JSON type.
    return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(right, sort_keys=True, allow_nan=False)


def _owned_members(child: _Child) -> list[dict]:
    if child.process is None:
        return []
    observed = child.observation
    if observed["start_ticks"] is None:
        # Initial identity admission failed. A live numeric PID/group is not
        # proof of ownership, and must never become an empty/pass observation.
        try:
            os.killpg(observed["pgid"], 0)
        except ProcessLookupError:
            return []
        except PermissionError:
            observed["ownership_unreadable"] = True
        return [{"pid": child.process.pid, "state": "ownership_unverified",
                 "pgid": observed["pgid"], "session": observed["session"]}]
    try:
        leader = _proc_identity(child.process.pid)
    except PermissionError:
        observed["ownership_unreadable"] = True
        return [{"pid": child.process.pid, "state": "unreadable", "pgid": observed["pgid"], "session": observed["session"]}]
    if leader is not None and leader["start_ticks"] != observed["start_ticks"]:
        # The original group/session cannot survive reuse of the leader's PID.
        # Never signal a new process that inherited its numeric identifier.
        observed["pid_reused"] = True
        return []
    result = []
    unreadable = False
    for path in Path("/proc").iterdir():
        if not path.name.isdigit():
            continue
        try:
            item = _proc_identity(int(path.name))
        except ProcessLookupError:
            continue
        except PermissionError:
            unreadable = True
            continue
        if item and item["pgid"] == observed["pgid"] and item["session"] == observed["session"]:
            result.append(item)
    if not result:
        try:
            os.killpg(observed["pgid"], 0)
        except ProcessLookupError:
            pass
        else:
            result.append({"pid": None, "state": "group_exists_unobserved", "pgid": observed["pgid"], "session": observed["session"]})
    # A restricted /proc can hide a live member behind an otherwise visible
    # zombie.  An extant group is not settled if any candidate is unreadable.
    if unreadable and result:
        observed["ownership_unreadable"] = True
        result.append({"pid": None, "state": "group_members_unobservable",
                       "pgid": observed["pgid"], "session": observed["session"]})
    return result


def _live_owned_members(child: _Child) -> list[dict]:
    """Keep unknown ownership conservative; a zombie cannot execute or be killed."""
    return [member for member in _owned_members(child) if member.get("state") != "Z"]


def _signal(child: _Child, sig: int) -> bool:
    if not _owned_members(child) or child.observation.get("ownership_unreadable") or child.observation.get("ownership_unverified"):
        return False
    try:
        os.killpg(child.observation["pgid"], sig)
    except ProcessLookupError:
        return False
    return True


class WaveExecutor:
    def __init__(self, *, ready_seconds: float = 180, poll_seconds: float = .05,
                 output_limit_bytes: int = 2 << 20, raw_log_limit_bytes: int = 128 << 20):
        if not 0 < ready_seconds <= 180 or not 0 < poll_seconds <= .1:
            raise ValueError("invalid bounded wave readiness/poll interval")
        if output_limit_bytes <= 0 or raw_log_limit_bytes <= 0:
            raise ValueError("positive output bounds required")
        self.ready_seconds = ready_seconds
        self.poll_seconds = poll_seconds
        self.output_limit_bytes = output_limit_bytes
        self.raw_log_limit_bytes = raw_log_limit_bytes

    def run_wave(self, jobs: list[WaveJob], wall_seconds: float,
                 release_callback: Callable[[], bool] | None = None,
                 on_event: Callable[[str, WaveJob, dict], None] | None = None,
                 *, authorize_go: Callable[[WaveJob, dict], bool] | None = None,
                 observe_transport: Callable[[WaveJob, dict], None] | None = None,
                 on_drain: Callable[[str, WaveJob, dict], None] | None = None,
                 release_fence: Callable[[WaveJob, dict], ReleaseFence] | None = None,
                 async_authorizer=None, intent_owner=None) -> list[dict]:
        """Run a wave; ``on_drain`` is an unverified, nonblocking owner signal.

        Supplying it neither seals other hosts' gates nor proves that its
        notification was durably received. Callers remain responsible for
        fencing admission and reconciling the physical owners and instances.
        Async authorizers must provide a nonblocking, in-memory
        ``release_guard(job, observation, fence)`` context and a
        ``can_release(job, observation, fence)`` recheck. The guard must
        serialize local drain observation and GO send without waiting; it
        yields None only when temporarily busy, False for denial, and True
        when held. Only literal True from both permits a GO. Neither establishes
        a global ownership fence or atomicity across hosts.

        In individual-authorized and async modes, an owner with sent or
        uncertain GO is preserved after any exception, not only budget drain.
        This deliberately has no settlement timeout: a still-running owner or
        an unreadable /proc observation can block indefinitely and continue to
        consume resources. An unreadable PID cannot be associated with a group,
        so even an unrelated PID can leave an extant zombie-only group unknown.
        This wait alone establishes no performance or scoring eligibility.
        A process group does not prove cgroup-wide settlement, and process
        interruption, external termination and durable recovery are separate.
        """
        if sys.platform != "linux":
            raise RuntimeError("the wave executor requires Linux /proc and Unix sockets")
        asynchronous = async_authorizer is not None
        # In the per-game paths this is an admission deadline, never a
        # campaign lifetime or a timeout for a sent/possibly sent game.  The
        # legacy all-at-once path retains its existing bounded wall timeout.
        if not jobs or type(wall_seconds) not in (int, float):
            raise ValueError("nonempty jobs and a finite positive wave time required")
        try:
            wall_seconds = float(wall_seconds)
        except OverflowError as error:
            raise ValueError("finite positive wave time required") from error
        if (not math.isfinite(wall_seconds) or wall_seconds <= 0
                or (authorize_go is None and not asynchronous and wall_seconds > 12 * 3600)):
            raise ValueError("finite positive wave time required; legacy wall time is bounded")
        if asynchronous and (authorize_go is not None or release_callback is not None or release_fence is not None
                or not callable(getattr(async_authorizer, "request", None))
                or not callable(getattr(async_authorizer, "poll", None)) or not callable(observe_transport)
                or not callable(getattr(intent_owner, "request", None))
                or not callable(getattr(intent_owner, "poll", None))):
            raise ValueError("async authorization requires nonblocking durable intent owner callbacks")
        if not asynchronous and intent_owner is not None:
            raise ValueError("durable intent owner is reserved for async authorization")
        if asynchronous:
            # A caller-supplied object that merely returns a hash is not a
            # durable journal. Only the registered local journal owner may
            # supply these receipts. Global/remote authority remains separate.
            try:
                from .run import IntentJournalOwner
            except ImportError:
                from run import IntentJournalOwner
            if type(intent_owner) is not IntentJournalOwner or not intent_owner.registered():
                raise ValueError("async GO requires its registered durable intent journal owner")
        if not asynchronous and ((authorize_go is None) != (observe_transport is None) or (authorize_go is not None and
                (not callable(authorize_go) or not callable(observe_transport)))):
            raise ValueError("per-game authorization and transport observer must be supplied together")
        if on_drain is not None and ((authorize_go is None and not asynchronous) or not callable(on_drain)):
            raise ValueError("drain notification requires per-game authorization")
        if release_fence is not None and (authorize_go is None or not callable(release_fence)):
            raise ValueError("release fence requires per-game authorization")
        if release_fence is not None or asynchronous:
            attempts = [job.start_job.get("attempt_id") for job in jobs]
            if (any(not isinstance(value, str) or not ATTEMPT_ID.fullmatch(value) for value in attempts)
                    or len(set(attempts)) != len(attempts)):
                raise ValueError("fenced jobs require distinct explicit attempt identities")
        if len({job.identity for job in jobs}) != len(jobs) or len({job.out.resolve() for job in jobs}) != len(jobs):
            raise ValueError("job identities and attempt directories must be distinct")
        for job in jobs:
            output = job.out.resolve()
            if output == REPO or REPO in output.parents or any((p / ".git").exists() for p in (output, *output.parents)):
                raise ValueError("attempt outputs must be outside every Git checkout")
            if output.exists() and not output.is_dir():
                raise ValueError("attempt output is not a directory")
            if any((output / name).exists() or (output / name).is_symlink() for name in ("runner.stdout.log", "runner.stderr.log", "wave-observation.json",
                                                         "raw.log", "game.pgn", "config.json")):
                raise ValueError("attempt evidence already exists; use a new attempt")
        if asynchronous:
            intent_owner.track_wave(jobs)
        started = time.monotonic()
        wall_deadline = started + wall_seconds
        ready_deadline = min(wall_deadline, started + self.ready_seconds)
        selector = selectors.DefaultSelector()
        children = [_Child(job, json.loads(json.dumps(job.start_job, allow_nan=False)), {
            "identity": job.identity, "id": job.identity, "argv": list(job.argv),
            "pid": None, "pgid": None, "session": None, "start_ticks": None,
            "spawn_monotonic": None, "ready_monotonic": None, "released_monotonic": None,
            "completed_monotonic": None, "gate_released": False, "gate_error": None,
            "wave_aborted": False, "returncode": None, "cleanup_forced": False,
            "remaining_processes": [], "readers_done": False, "status": "not_started",
            "stdout_path": str(job.out / "runner.stdout.log"),
            "stderr_path": str(job.out / "runner.stderr.log"),
            "stdout_bytes": 0, "stderr_bytes": 0,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }) for job in jobs]
        wave_error = None
        event_error = None
        released = False
        cleaning = False
        drain_notified = False
        async_draining = False
        async_seen_fences = set()
        async_commands = {}
        async_pending_intents = {}
        boot_id = _boot_id() if asynchronous else None

        def snapshot(child):
            observed = dict(child.observation)
            for channel in child.channels:
                observed[channel.name + "_bytes"] = channel.stored
                observed[channel.name + "_total_bytes"] = channel.total
            return observed

        def notify_drain(child, reason):
            """Signal the owner once; delivery is not a durable global fence."""
            nonlocal drain_notified
            if drain_notified:
                return
            drain_notified = True
            child.observation["drain_reason"] = reason
            if on_drain is None:
                child.observation["drain_notification"] = "unconfigured"
                return
            try:
                on_drain(reason, child.job, snapshot(child))
            except Exception as error:
                child.observation["drain_notification"] = "failed"
                child.observation["drain_notification_error"] = repr(error)
            else:
                child.observation["drain_notification"] = "returned_unverified"

        def begin_async_drain(child, reason):
            """Stop only unsent gates; preserve every possible GO owner."""
            nonlocal async_draining
            if async_draining:
                return
            async_draining = True
            notify_drain(child, reason)
            for pending in children:
                obs = pending.observation
                if obs.get("gate_transport") in ("sent", "uncertain") or obs.get("gate_cancelled"):
                    continue
                if obs.get("gate_authorization_requested") and not obs.get("gate_authorization_resolved"):
                    obs["gate_authorization_unknown"] = True
                if obs.get("gate_intent_requested"):
                    # A worker may have committed even when its reply is lost.
                    obs["gate_authorization_unknown"] = True
                obs.update(gate_cancelled=True, gate_transport="not_attempted",
                           gate_cancel_started_monotonic=time.monotonic())
                if pending.control is not None:
                    try:
                        pending.control.sendall(b"ABORT\n")
                    except OSError as error:
                        obs["gate_cancel_error"] = repr(error)
                        try:
                            pending.control.shutdown(socket.SHUT_WR)
                        except OSError:
                            pass

        def go2_wire(child, fence):
            if fence is None:
                raise ValueError("GO2 requires an explicit fence")
            attempt = child.expected["attempt_id"]
            nonce = secrets.token_hex(32)
            expected = {"event": "GO2_ACCEPTED", "attempt_id": attempt, "fence_id": fence.fence_id,
                        "job_sha256": fence.job_sha256, "nonce": nonce}
            child.observation.update(gate_receipt_required=True, gate_receipt="pending",
                                     gate_receipt_expected=expected,
                                     gate_receipt_deadline=min(fence.expires_monotonic, time.monotonic() + 5))
            return f"GO2 {attempt} {fence.fence_id} {fence.job_sha256} {nonce}\n".encode("ascii")

        def prepare_intent(child, fence):
            """Prepare the exact GO2 bytes before the owner durably records intent."""
            binding = json.dumps({"identity": child.job.identity, "start_job": child.expected},
                                 sort_keys=True, allow_nan=False, separators=(",", ":")).encode("utf-8")
            digest = hashlib.sha256(binding).hexdigest()
            now = time.monotonic()
            if (type(fence) is not ReleaseFence or fence.game_id != child.job.identity
                    or fence.job_sha256 != digest or not fence.not_before_monotonic <= now < fence.expires_monotonic):
                raise ValueError("exact, currently valid per-game fence required before intent")
            child.observation["gate_fence_binding_sha256"] = digest
            child.observation["gate_fence"] = {"game_id": fence.game_id, "fence_id": fence.fence_id,
                "job_sha256": fence.job_sha256, "not_before_monotonic": fence.not_before_monotonic,
                "expires_monotonic": fence.expires_monotonic}
            command = go2_wire(child, fence)
            payload = intent_payload(child.job, snapshot(child), boot_id=boot_id)
            child.observation.update(gate_intent_required=True, gate_intent_requested=True,
                                     gate_intent_resolved=False, gate_intent_payload=payload)
            async_commands[child.job.identity] = (fence, command)
            # This method is a local enqueue only. The owner does fsync or
            # network operations in its own execution context, never here.
            intent_owner.request(child.job, snapshot(child))

        def async_tick():
            """Poll only a local nonblocking mailbox; never perform remote I/O here."""
            for item in children:
                obs = item.observation
                if obs.get("gate_receipt") == "pending" and time.monotonic() >= obs["gate_receipt_deadline"]:
                    obs["gate_receipt"] = "unresolved"
                    begin_async_drain(item, "gate_receipt_timeout")
                if item.process is not None and item.process.poll() is not None and item.control is not None:
                    obs.setdefault("gate_eof_deadline", time.monotonic() + 5)
                    if time.monotonic() >= obs["gate_eof_deadline"]:
                        obs["gate_receipt"] = "unresolved"
                        begin_async_drain(item, "gate_control_eof_timeout")
                        unregister(item.control)
                        item.control.close()
                        item.control = None
            if async_draining:
                return
            for item in children:
                obs = item.observation
                if (item.process is not None and item.process.poll() is not None
                        and obs.get("gate_transport") == "not_attempted" and not obs.get("gate_cancelled")):
                    begin_async_drain(item, "pending_runner_exit")
                    return
            if time.monotonic() >= wall_deadline:
                pending = next((item for item in children if not item.observation.get("gate_cancelled")
                                and (not item.observation.get("gate_authorization_resolved")
                                     or (item.observation.get("gate_intent_requested")
                                         and not item.observation.get("gate_intent_resolved")))), None)
                if pending is not None:
                    begin_async_drain(pending, "async_authorization_deadline")
                    return
            try:
                decisions = async_authorizer.poll()
                if not isinstance(decisions, (list, tuple)) or len(decisions) > len(children):
                    raise ValueError("bounded decision batch required")
            except Exception as error:
                children[0].observation["gate_authorizer_poll_error"] = repr(error)
                begin_async_drain(children[0], "async_authorizer_failed")
                return
            for decision in decisions:
                matches = [item for item in children if item.job.identity == getattr(decision, "identity", None)]
                if (type(decision) is not AsyncGateDecision or len(matches) != 1
                        or not matches[0].observation.get("gate_authorization_requested")
                        or matches[0].observation.get("gate_authorization_resolved")):
                    begin_async_drain(children[0], "invalid_or_duplicate_decision")
                    return
                item = matches[0]
                item.observation.update(gate_authorization_resolved=True, gate_authorization_unknown=False)
                if not decision.allowed:
                    item.observation["gate_denied_reason"] = "release authorization denied"
                    begin_async_drain(item, "authorization_denied")
                    return
                if decision.fence.fence_id in async_seen_fences:
                    item.observation["gate_authorized"] = True
                    item.observation["gate_fence_error"] = "duplicate fence identity within wave"
                    begin_async_drain(item, "duplicate_release_fence")
                    return
                async_seen_fences.add(decision.fence.fence_id)
                try:
                    prepare_intent(item, decision.fence)
                except Exception as error:
                    item.observation["gate_intent_request_error"] = repr(error)
                    item.observation["gate_authorization_unknown"] = True
                    begin_async_drain(item, "durable_intent_request_failed")
                    return
            try:
                intents = intent_owner.poll()
                if not isinstance(intents, (list, tuple)) or len(intents) > len(children):
                    raise ValueError("bounded durable intent response batch required")
            except Exception as error:
                children[0].observation["gate_intent_poll_error"] = repr(error)
                begin_async_drain(children[0], "durable_intent_owner_failed")
                return
            for decision in intents:
                matches = [item for item in children if item.job.identity == getattr(decision, "identity", None)]
                if (type(decision) is not AsyncIntentDecision or len(matches) != 1
                        or not matches[0].observation.get("gate_intent_requested")
                        or matches[0].observation.get("gate_intent_resolved")
                        or matches[0].job.identity in async_pending_intents):
                    begin_async_drain(children[0], "invalid_or_duplicate_intent")
                    return
                item = matches[0]
                async_pending_intents[item.job.identity] = decision
            for item in children:
                decision = async_pending_intents.get(item.job.identity)
                if decision is None:
                    continue
                obs = item.observation
                try:
                    confirmed = (_same_json(decision.intent, obs["gate_intent_payload"])
                                 and _same_json(decision.intent, intent_payload(item.job, snapshot(item), boot_id=boot_id))
                                 and intent_owner.confirm(decision, item.job, snapshot(item)))
                except Exception as error:
                    obs["gate_intent_error"] = repr(error)
                    begin_async_drain(item, "durable_intent_validation_failed")
                    return
                if not confirmed:
                    obs["gate_intent_error"] = "durable intent binding differs"
                    begin_async_drain(item, "durable_intent_binding_changed")
                    return
                obs.update(gate_intent_resolved=True, gate_intent_seq=decision.journal_seq,
                           gate_intent_sha256=decision.journal_sha256)
                fence, command = async_commands[item.job.identity]
                if time.monotonic() >= obs["gate_receipt_deadline"]:
                    obs["gate_intent_error"] = "receipt window expired before GO"
                    begin_async_drain(item, "durable_intent_window_expired")
                    return
                def recheck(job, current, current_fence):
                    guard = getattr(async_authorizer, "can_release", None)
                    return guard(job, current, current_fence) if callable(guard) else False
                def hold_release(job, current, current_fence):
                    guard = getattr(async_authorizer, "release_guard", None)
                    return guard(job, current, current_fence) if callable(guard) else nullcontext(False)
                drained = _release_individually([item], snapshot, lambda job, obs: True, observe_transport, event,
                    deadline=wall_deadline, notify_drain=notify_drain,
                    release_fence=lambda job, obs: fence, wire_go=lambda child, current: command,
                    pre_send=recheck, release_guard=hold_release)
                if drained == "guard_busy":
                    continue
                del async_pending_intents[item.job.identity]
                if drained:
                    begin_async_drain(item, item.observation.get("drain_reason", "gate_release_failed"))
                    return

        def event(name, child):
            nonlocal event_error
            if on_event is None or event_error is not None:
                return
            try:
                on_event(name, child.job, snapshot(child))
            except Exception as error:
                event_error = f"{type(error).__name__}: {error}"
                raise WaveAbort("event callback failed: " + event_error) from error

        def capture_logs(child):
            for channel in child.channels:
                child.observation[channel.name + "_bytes"] = channel.stored
                child.observation[channel.name + "_total_bytes"] = channel.total
                child.observation[channel.name + "_eof"] = channel.eof
                if channel.target.closed:
                    child.observation[channel.name + "_sha256"] = hashlib.sha256(channel.path.read_bytes()).hexdigest()
            child.observation["readers_done"] = all(channel.eof or channel.pipe is None for channel in child.channels)

        def notify_completed():
            # A completed colour must be durable while unrelated games are
            # still running. Waiting for the whole wave would lose that game
            # on a later Spot interruption and bias half-pair recovery.
            if not released or wave_error is not None or event_error is not None:
                return
            for child in children:
                if child.completion_notified or child.process is None:
                    continue
                if asynchronous and (child.observation.get("gate_receipt") == "pending" or child.control is not None):
                    continue
                code = child.process.poll()
                if code is None or not all(channel.eof for channel in child.channels) or _owned_members(child):
                    continue
                if any(channel.error for channel in child.channels):
                    continue
                capture_logs(child)
                name, gate_status = _terminal_gate_class(child.observation)
                child.observation.update(returncode=code, remaining_processes=[],
                                         status=gate_status,
                                         completed_monotonic=time.monotonic())
                try:
                    event(name, child)
                except WaveAbort as error:
                    if authorize_go is None and not asynchronous:
                        raise
                    # An audit/ledger failure is not evidence that another
                    # already-started game has failed. Quarantine receipts and
                    # retain natural ownership until all running games settle.
                    child.observation["completion_event_error"] = str(error)
                    notify_drain(child, "completion_event_failed")
                    if asynchronous:
                        begin_async_drain(child, "completion_event_failed")
                    return
                child.completion_notified = True

        def ticks():
            now = time.monotonic()
            for child in children:
                if child.process is not None and now - child.last_tick >= .75:
                    child.last_tick = now
                    try:
                        event("tick", child)
                    except WaveAbort as error:
                        if (authorize_go is None and not asynchronous) or not released:
                            raise
                        child.observation["tick_event_error"] = str(error)
                        notify_drain(child, "tick_event_failed")
                        if asynchronous:
                            begin_async_drain(child, "tick_event_failed")

        def cleanup_cancelled():
            """Only gates proven not to have attempted GO may be timed out."""
            now = time.monotonic()
            unresolved = []
            for child in children:
                obs = child.observation
                if not obs.get("gate_cancelled") or obs.get("gate_transport") != "not_attempted":
                    continue
                since = obs.get("gate_cancel_started_monotonic")
                if since is None or child.process is None or not _owned_members(child):
                    continue
                elapsed = now - since
                for delay, sig, key in ((2, signal.SIGTERM, "cancel_term_attempted"),
                                        (3, signal.SIGKILL, "cancel_kill_attempted")):
                    if elapsed >= delay and not obs.get(key):
                        obs[key] = True
                        try:
                            if _signal(child, sig):
                                obs["cleanup_forced"] = True
                        except (OSError, ValueError) as error:
                            obs["cancel_signal_error"] = repr(error)
                if elapsed >= 5 and _owned_members(child):
                    obs["cancel_owner_unresolved"] = True
                    unresolved.append(child)
            if unresolved:
                # Never use the global abort path while any sent/uncertain game
                # still has a live owner. Unknown cancelled owners are returned
                # only after unrelated started games have physically settled.
                running_games = [child for child in children
                                 if child.observation.get("gate_transport") in ("sent", "uncertain")
                                 and _owned_members(child)]
                if not running_games:
                    raise WaveAbort("cancelled pre-GO owner remains unresolved")

        def unregister(fileobj):
            try:
                selector.unregister(fileobj)
            except (KeyError, ValueError):
                pass

        def finish_channel(channel):
            if channel.pipe is not None:
                unregister(channel.pipe)
                channel.pipe.close()
            if not channel.target.closed:
                try:
                    channel.target.flush()
                    os.fsync(channel.target.fileno())
                except OSError as error:
                    channel.error = f"log fsync failed: {error}"
                finally:
                    channel.target.close()

        def read_log(channel):
            try:
                chunk = os.read(channel.pipe.fileno(), 65536)
            except BlockingIOError:
                return
            except OSError as error:
                channel.error = f"log read failed: {error}"
                finish_channel(channel)
                return
            if not chunk:
                channel.eof = True
                finish_channel(channel)
                return
            channel.total += len(chunk)
            keep = chunk[:max(0, self.output_limit_bytes - channel.stored)]
            try:
                if keep and not channel.target.closed:
                    count = channel.target.write(keep)
                    channel.stored += count
                    if count != len(keep):
                        raise OSError("short log write")
            except OSError as error:
                channel.error = f"log write failed: {error}"
            if channel.total > self.output_limit_bytes:
                channel.error = "stdio output limit exceeded"

        def completed_before_abort():
            if not released:
                return
            for child in children:
                if child.completion_notified or child.process is None or child.process.poll() is None or _owned_members(child):
                    continue
                # A terminal sibling may have EOF queued in the same poll batch
                # as another child's fault. Drain only that terminal sibling;
                # do not wait for active games or read an unbounded stream.
                for channel in child.channels:
                    for _ in range(self.output_limit_bytes // 65536 + 3):
                        if channel.eof or channel.pipe is None or channel.pipe.closed or channel.error:
                            break
                        previous = channel.total
                        read_log(channel)
                        if channel.total == previous and not channel.eof:
                            break
            notify_completed()

        def pump(timeout):
            for key, _ in selector.select(max(0, timeout)):
                kind, child, channel = key.data
                if kind == "log":
                    read_log(channel)
                else:
                    try:
                        data = child.control.recv(4096)
                    except BlockingIOError:
                        continue
                    except OSError as error:
                        child.observation["control_error"] = repr(error)
                        data = b""
                    if not data:
                        unregister(child.control)
                        child.control.close()
                        child.control = None
                        child.observation["control_closed_monotonic"] = time.monotonic()
                        if asynchronous and child.observation.get("gate_receipt_required") and child.observation.get("gate_receipt") != "matched":
                            child.observation["gate_receipt"] = "unresolved"
                            begin_async_drain(child, "gate_receipt_missing")
                        elif asynchronous and released and child.observation.get("gate_transport") not in ("sent", "uncertain") and not child.observation.get("gate_cancelled"):
                            begin_async_drain(child, "pending_gate_closed")
                        if not released and not cleaning:
                            raise WaveAbort("runner control EOF before READY: " + child.job.identity)
                        continue
                    if cleaning:
                        continue
                    if child.observation["ready_monotonic"] is not None:
                        if not asynchronous or not child.observation.get("gate_receipt_required") or child.observation.get("gate_receipt") != "pending":
                            if asynchronous:
                                child.observation["gate_receipt"] = "unresolved"
                                begin_async_drain(child, "unexpected_gate_message")
                                continue
                            raise WaveAbort("unexpected repeated control message: " + child.job.identity)
                        child.gate_bytes += data
                        if len(child.gate_bytes) > 4096:
                            child.observation["gate_receipt"] = "unresolved"
                            begin_async_drain(child, "excessive_gate_receipt")
                            continue
                        if b"\n" not in child.gate_bytes:
                            continue
                        line, extra = child.gate_bytes.split(b"\n", 1)
                        child.gate_bytes = b""
                        try:
                            receipt = json.loads(line, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
                        except (ValueError, UnicodeDecodeError):
                            receipt = None
                        if (extra or not _same_json(receipt, child.observation["gate_receipt_expected"])
                                or time.monotonic() >= child.observation["gate_receipt_deadline"]):
                            child.observation["gate_receipt"] = "unresolved"
                            begin_async_drain(child, "gate_receipt_mismatch_or_expired")
                        else:
                            child.observation["gate_receipt"] = "matched"
                            child.observation["gate_receipt_monotonic"] = time.monotonic()
                            try:
                                event("gate_received", child)
                            except WaveAbort as error:
                                child.observation["gate_receipt_event_error"] = str(error)
                                child.observation["gate_receipt"] = "unresolved"
                                begin_async_drain(child, "gate_receipt_event_failed")
                        continue
                    child.gate_bytes += data
                    if len(child.gate_bytes) > 16384:
                        raise WaveAbort("excessive READY message: " + child.job.identity)
                    if b"\n" not in child.gate_bytes:
                        continue
                    line, extra = child.gate_bytes.split(b"\n", 1)
                    if extra:
                        raise WaveAbort("extra READY protocol bytes: " + child.job.identity)
                    try:
                        ready = json.loads(line, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
                    except (ValueError, UnicodeDecodeError) as error:
                        raise WaveAbort("invalid READY JSON: " + child.job.identity) from error
                    expected = {"event": "READY", "job": child.expected,
                                "white_clock_ms": CLOCK_MS, "black_clock_ms": CLOCK_MS}
                    if not _same_json(ready, expected) or type(ready.get("white_clock_ms")) is not int or type(ready.get("black_clock_ms")) is not int:
                        raise WaveAbort("READY identity or clock mismatch: " + child.job.identity)
                    child.observation["ready"] = ready
                    child.observation["ready_monotonic"] = time.monotonic()
                    child.gate_bytes = b""
                    child.observation["status"] = "ready"
                    event("ready", child)

        def inspect_failures():
            for child in children:
                for channel in child.channels:
                    if channel.error:
                        raise WaveAbort(child.job.identity + ": " + channel.error)
                raw = child.job.out / "raw.log"
                if raw.is_symlink():
                    raise WaveAbort("raw log is not an owned regular file: " + child.job.identity)
                if raw.exists() and raw.stat().st_size > self.raw_log_limit_bytes:
                    raise WaveAbort("raw log limit exceeded: " + child.job.identity)
                if child.process is not None:
                    code = child.process.poll()
                    if code is not None:
                        child.observation["returncode"] = code
                        child.observation.setdefault("exit_observed_monotonic", time.monotonic())
                        if not released:
                            raise WaveAbort("runner exited before wave release: " + child.job.identity)

        def abort_controls():
            for child in children:
                # A sent or partially sent GO may already have been consumed.
                # Do not send an additional command to that owner.
                if (authorize_go is not None or asynchronous) and child.observation.get("gate_transport") in ("sent", "uncertain"):
                    continue
                if authorize_go is not None or asynchronous:
                    child.observation.setdefault("gate_cancel_started_monotonic", time.monotonic())
                    child.observation["gate_cancelled"] = True
                if child.control is not None:
                    try:
                        child.control.sendall(b"ABORT\n")
                    except OSError:
                        pass

        def possible_go_still_live(child):
            if not (authorize_go is not None or asynchronous) or child.observation.get("gate_transport") not in ("sent", "uncertain"):
                return False
            try:
                return bool(_live_owned_members(child))
            except Exception as error:
                # Losing /proc evidence is not proof of physical settlement.
                child.observation.setdefault("settlement_ownership_error", repr(error))
                return True

        def drain_until(deadline, *, signal_at_start=None):
            if signal_at_start is not None:
                for child in children:
                    if (authorize_go is not None or asynchronous) and child.observation.get("gate_transport") in ("sent", "uncertain"):
                        continue
                    if _signal(child, signal_at_start):
                        child.observation["cleanup_forced"] = True
            while time.monotonic() < deadline:
                for child in children:
                    if child.process is not None:
                        child.observation["returncode"] = child.process.poll()
                if not any(_owned_members(child) for child in children):
                    break
                pump(min(self.poll_seconds, deadline - time.monotonic()))
                try:
                    ticks()
                except WaveAbort:
                    pass

        try:
            for child in children:
                if time.monotonic() >= ready_deadline:
                    raise WaveAbort("wave startup deadline expired during spawn")
                child.job.out.mkdir(parents=True, exist_ok=True)
                # Reserve logs before creating a process, so file-admission
                # failure cannot leave a child with unowned stdout/stderr.
                for name in ("stdout", "stderr"):
                    target = child.job.out / ("runner." + name + ".log")
                    child.channels.append(_Channel(name, None, target, target.open("xb", buffering=0)))
                parent, passed = socket.socketpair()
                child.control = parent
                parent.setblocking(False)
                environment = dict(os.environ)
                environment.update(child.job.env)
                # The executor owns the protocol selection. A parent shell or
                # caller environment must never silently change legacy GO.
                environment.pop("ROVE_START_PROTOCOL", None)
                # Only the post-placement sealed-opening launcher may set this
                # private FD; neither a parent shell nor a job may supply it.
                environment.pop("ROVE_OPENING_FD", None)
                environment.update(ROVE_START_FD=str(passed.fileno()),
                    ROVE_START_JOB=json.dumps(child.expected, allow_nan=False, separators=(",", ":")))
                if asynchronous:
                    environment["ROVE_START_PROTOCOL"] = "2"
                try:
                    child.process = subprocess.Popen(list(child.job.argv), cwd=child.job.out,
                        env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, bufsize=0, pass_fds=(passed.fileno(),), start_new_session=True)
                finally:
                    passed.close()
                child.observation.update(pid=child.process.pid, pgid=child.process.pid,
                                         session=child.process.pid, ownership_unverified=True)
                child.observation["spawn_monotonic"] = time.monotonic()
                child.observation["status"] = "initializing"
                for channel, pipe in zip(child.channels, (child.process.stdout, child.process.stderr)):
                    channel.pipe = pipe
                for channel in child.channels:
                    pipe = channel.pipe
                    os.set_blocking(pipe.fileno(), False)
                    selector.register(pipe, selectors.EVENT_READ, ("log", child, channel))
                selector.register(parent, selectors.EVENT_READ, ("control", child, None))
                identity = _proc_identity(child.process.pid)
                if not identity or identity["pgid"] != child.process.pid or identity["session"] != child.process.pid:
                    child.observation["initial_identity_failed"] = True
                    raise WaveAbort("owned runner session could not be verified")
                child.observation.update(identity, ownership_unverified=False)
                event("spawned", child)
                ticks()
            while not all(child.observation["ready_monotonic"] is not None for child in children):
                if time.monotonic() >= ready_deadline:
                    raise WaveAbort("wave READY deadline expired")
                pump(min(self.poll_seconds, ready_deadline - time.monotonic()))
                inspect_failures()
                ticks()
            inspect_failures()
            if release_callback is not None and release_callback() is not True:
                raise WaveAbort("controller denied wave release")
            if time.monotonic() >= wall_deadline:
                raise WaveAbort("wave wall deadline expired before release")
            if asynchronous:
                # request and poll must touch only a local nonblocking mailbox;
                # the serialized owner performs network/durable work elsewhere.
                released = True
                for child in children:
                    child.observation.update(gate_authorized=False, gate_authorization_unknown=False,
                                             gate_authorization_requested=False, gate_authorization_resolved=False,
                                             gate_transport="not_attempted", gate_cancelled=False,
                                             gate_intent_requested=False, gate_intent_resolved=False)
                for child in children:
                    if async_draining:
                        break
                    child.observation["gate_authorization_requested"] = True
                    try:
                        async_authorizer.request(child.job, snapshot(child))
                    except Exception as error:
                        child.observation["gate_authorization_request_error"] = repr(error)
                        begin_async_drain(child, "async_authorization_request_failed")
                run_deadline = None
            elif authorize_go is not None:
                _release_individually(children, snapshot, authorize_go, observe_transport, event,
                                      deadline=wall_deadline, notify_drain=notify_drain,
                                      release_fence=release_fence)
                # A denied or transport-uncertain gate is not a global abort:
                # let every already sent/possibly sent original owner settle.
                released = True
                # The old pre-GO admission deadline is never a deadline for a
                # game that may already have received GO. Actual output, owner,
                # controller and child failures are still checked below.
                sent_at = [child.observation["gate_send_started_monotonic"] for child in children
                           if "gate_send_started_monotonic" in child.observation]
                run_deadline = None if sent_at else max(wall_deadline, time.monotonic() + 2)
            else:
                for child in children:
                    if child.control is None:
                        raise WaveAbort("runner gate closed before GO")
                    child.control.sendall(b"GO\n")
                    child.observation["gate_released"] = True
                    child.observation["released_monotonic"] = time.monotonic()
                    child.observation["status"] = "running"
                released = True
                run_deadline = wall_deadline
                for child in children:
                    event("released", child)
            while True:
                if run_deadline is not None and time.monotonic() >= run_deadline:
                    raise WaveAbort("wave wall deadline expired")
                pump(self.poll_seconds if run_deadline is None else min(self.poll_seconds, run_deadline - time.monotonic()))
                if asynchronous:
                    async_tick()
                notify_completed()
                inspect_failures()
                ticks()
                if authorize_go is not None or asynchronous:
                    cleanup_cancelled()
                if (all(child.process.poll() is not None for child in children) and
                        all(not possible_go_still_live(child) for child in children) and
                        (not asynchronous or all(child.observation.get("gate_receipt") != "pending" and child.control is None
                                                 for child in children))):
                    break
        except BaseException as error:
            if authorize_go is not None or asynchronous:
                # No host may infer that other owners stopped just because
                # this wave failed. Notify the external coordinator to fence
                # further starts; physical settlement remains separate.
                notify_drain(children[0], "wave_failed")
            try:
                completed_before_abort()
            except BaseException as completion_error:
                for child in children:
                    child.observation["completion_event_error"] = repr(completion_error)
            wave_error = f"{type(error).__name__}: {error}"
            for child in children:
                if not child.completion_notified:
                    child.observation.update(wave_aborted=True, gate_error=wave_error, status="aborting")
            abort_controls()
        finally:
            cleaning = True
            # This is still the original unreaped Popen child: no poll/wait has
            # run after failed initial admission. One fresh /proc observation
            # may establish its identity for safe cleanup; otherwise retain an
            # explicit unknown group and refuse group signals.
            for child in children:
                if child.process is not None and child.observation["start_ticks"] is None and child.process.returncode is None:
                    try:
                        identity = _proc_identity(child.process.pid)
                    except (OSError, ValueError) as error:
                        child.observation["identity_cleanup_error"] = repr(error)
                        identity = None
                    if identity and identity["pgid"] == child.process.pid and identity["session"] == child.process.pid:
                        child.observation.update(identity, ownership_unverified=False, identity_verified_during_cleanup=True)
            # Read any final output while all original leaders and groups settle.
            # The three phases are collective, never a per-job timeout sum.
            try:
                # Even an exception is not evidence that a complete or partial
                # GO failed to reach its runner. Keep its original process and
                # output channels under observation until the live group ends;
                # never retry or signal a potentially started game here.
                while any(possible_go_still_live(child) for child in children):
                    try:
                        pump(self.poll_seconds)
                    except Exception as error:
                        # Keep the original pipes and owners alive even when
                        # selector polling fails.  Drain nonblocking log FDs
                        # directly so a running engine cannot stall on output.
                        for child in children:
                            child.observation.setdefault("settlement_pump_error", repr(error))
                            for channel in child.channels:
                                if channel.pipe is not None and not channel.pipe.closed:
                                    try:
                                        read_log(channel)
                                    except Exception as read_error:
                                        child.observation.setdefault("settlement_read_error", repr(read_error))
                        time.sleep(self.poll_seconds)
                    try:
                        cleanup_cancelled()
                    except Exception as error:
                        for child in children:
                            child.observation.setdefault("settlement_cancel_error", repr(error))
                drain_until(time.monotonic() + 2)
                if any(_owned_members(child) for child in children):
                    drain_until(time.monotonic() + 1, signal_at_start=signal.SIGTERM)
                if any(_owned_members(child) for child in children):
                    drain_until(time.monotonic() + 2, signal_at_start=signal.SIGKILL)
                reader_deadline = time.monotonic() + 2
                while any(channel.pipe is not None and not channel.eof and not channel.pipe.closed
                          for child in children for channel in child.channels):
                    if time.monotonic() >= reader_deadline:
                        break
                    pump(min(self.poll_seconds, reader_deadline - time.monotonic()))
                notify_completed()
            except BaseException as error:
                for child in children:
                    child.observation["cleanup_error"] = repr(error)
                if wave_error is None:
                    wave_error = "cleanup failed: " + repr(error)
            for child in children:
                observation = child.observation
                if child.process is not None:
                    observation["returncode"] = child.process.poll()
                    observation["remaining_processes"] = _owned_members(child)
                for channel in child.channels:
                    if channel.pipe is None or not channel.pipe.closed:
                        finish_channel(channel)
                    observation[channel.name + "_bytes"] = channel.stored
                    observation[channel.name + "_total_bytes"] = channel.total
                    observation[channel.name + "_sha256"] = hashlib.sha256(channel.path.read_bytes()).hexdigest()
                    observation[channel.name + "_eof"] = channel.eof
                    if channel.error:
                        observation[channel.name + "_error"] = channel.error
                        if wave_error is None:
                            wave_error = child.job.identity + ": " + channel.error
                observation["readers_done"] = all(channel.eof or channel.pipe is None for channel in child.channels)
                if child.control is not None:
                    unregister(child.control)
                    child.control.close()
                    child.control = None
                if not child.completion_notified:
                    if observation["cleanup_forced"] or observation["remaining_processes"] or (child.process and not observation["readers_done"]):
                        observation["local_error"] = "runner group or output required forced/incomplete cleanup"
                    observation["completed_monotonic"] = time.monotonic()
                if wave_error is not None:
                    observation["wave_error_context"] = wave_error
                if child.completion_notified:
                    _, observation["status"] = _terminal_gate_class(observation)
                elif wave_error is not None or observation.get("local_error"):
                    observation.update(wave_aborted=True, gate_error=wave_error or observation["local_error"], status="aborted")
                else:
                    observation["status"] = "completed"
            selector.close()
            for child in children:
                if event_error is not None:
                    child.observation["event_error"] = event_error
                try:
                    if not child.completion_notified:
                        event("aborted" if child.observation["wave_aborted"] else "completed", child)
                except WaveAbort as error:
                    child.observation["event_error"] = str(error)
                    wave_error = str(error)
            if event_error is not None:
                for child in children:
                    child.observation.update(event_error=event_error, wave_error_context=wave_error or event_error)
                    if not child.completion_notified:
                        child.observation.update(wave_aborted=True, gate_error=wave_error or event_error, status="aborted")
            for child in children:
                child.observation["elapsed_seconds"] = time.monotonic() - started
                if child.job.out.is_dir():
                    path = child.job.out / "wave-observation.json"
                    try:
                        with path.open("x", encoding="utf-8") as handle:
                            handle.write(json.dumps(child.observation, allow_nan=False, indent=2) + "\n")
                            handle.flush()
                            os.fsync(handle.fileno())
                    except OSError as error:
                        child.observation["sidecar_error"] = str(error)
        return [dict(child.observation) for child in children]
