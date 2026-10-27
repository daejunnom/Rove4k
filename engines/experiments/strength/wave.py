"""Own one initialization-isolated wave of patched Fastchess processes.

This module does not qualify artifacts or score games. The campaign controller
must do both. Before GO any failure aborts the whole unstarted wave. After GO,
individual runner exits remain observations for the controller to adjudicate;
budget, journal, output and global wall failures abort the whole wave.

Callbacks execute on the controller thread and must not wait on network I/O.
Each runner gets an independent session/process group and a private gate FD.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
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
                          observation.get("gate_authorization_unknown") is True)
        return "cancelled", "cancelled_unreconciled" if uncertain_auth else "cancelled_before_go"
    if (observation.get("gate_transport") == "uncertain" or
            observation.get("gate_transport_observation_error") or
            observation.get("gate_release_event_error")):
        return "delivery_uncertain", "delivery_unresolved"
    return "completed", "completed"


def _release_individually(children, snapshot, authorize_go, observe_transport, emit, *, deadline=None):
    """Try budget-owner authorization immediately before each private gate write.

    The callbacks must be supplied by a durable, serialized owner. This helper
    cannot prove cross-host atomicity or that a successful socket write was read
    by the runner: an actual runner/engine GO requires separate evidence.
    A denial or callback/transport fault prevents later GO writes. Already sent
    or possibly sent games are not signalled here and must be physically settled.
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
    for child in children:
        obs = child.observation
        obs.update(gate_authorized=False, gate_authorization_unknown=False,
                   gate_transport="not_attempted", gate_cancelled=False)
        if not draining and deadline is not None and time.monotonic() >= deadline:
            obs["gate_denied_reason"] = "wave deadline expired before authorization"
            draining = True
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
                    draining = True
                    cancel(child)
                elif child.control is None:
                    obs["gate_transport"] = "not_attempted"
                    obs["gate_transport_error"] = "runner gate closed before GO"
                    cancel(child)
                    draining = True
                else:
                    # A failed sendall can have written a prefix or all bytes.
                    # Closing only the write side makes an incomplete gate see
                    # EOF; a runner that received complete GO may still run.
                    obs["gate_transport"] = "uncertain"
                    obs["gate_send_started_monotonic"] = time.monotonic()
                    try:
                        child.control.sendall(b"GO\n")
                    except OSError as error:
                        obs["gate_transport_error"] = repr(error)
                        draining = True
                        try:
                            child.control.shutdown(socket.SHUT_WR)
                        except OSError:
                            pass
                    else:
                        obs.update(gate_transport="sent", gate_released=True,
                                   released_monotonic=time.monotonic(), status="running")
                    try:
                        # Only transport state is reported, never actual GO receipt.
                        observe_transport(child.job, snapshot(child))
                    except Exception as error:
                        obs["gate_transport_observation_error"] = repr(error)
                        draining = True
                    if obs["gate_transport"] == "sent":
                        try:
                            emit("released", child)
                        except WaveAbort as error:
                            obs["gate_release_event_error"] = str(error)
                            draining = True
                # Authorized games remain unsettled even if no GO was sent.
                if obs["gate_transport"] == "not_attempted":
                    obs["gate_cancelled"] = True
                continue
            obs.setdefault("gate_denied_reason", "release authorization denied")
            draining = True
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
    for path in Path("/proc").iterdir():
        if not path.name.isdigit():
            continue
        try:
            item = _proc_identity(int(path.name))
        except (ProcessLookupError, PermissionError):
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
    return result


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
                 observe_transport: Callable[[WaveJob, dict], None] | None = None) -> list[dict]:
        if sys.platform != "linux":
            raise RuntimeError("the wave executor requires Linux /proc and Unix sockets")
        if not jobs or not 0 < wall_seconds <= 12 * 3600:
            raise ValueError("nonempty jobs and a bounded positive wave wall time required")
        if (authorize_go is None) != (observe_transport is None) or (authorize_go is not None and
                (not callable(authorize_go) or not callable(observe_transport))):
            raise ValueError("per-game authorization and transport observer must be supplied together")
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

        def snapshot(child):
            observed = dict(child.observation)
            for channel in child.channels:
                observed[channel.name + "_bytes"] = channel.stored
                observed[channel.name + "_total_bytes"] = channel.total
            return observed

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
                    if authorize_go is None:
                        raise
                    # An audit/ledger failure is not evidence that another
                    # already-started game has failed. Quarantine receipts and
                    # retain natural ownership until all running games settle.
                    child.observation["completion_event_error"] = str(error)
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
                        if authorize_go is None or not released:
                            raise
                        child.observation["tick_event_error"] = str(error)

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
                        if not released and not cleaning:
                            raise WaveAbort("runner control EOF before READY: " + child.job.identity)
                        continue
                    if cleaning:
                        continue
                    if child.observation["ready_monotonic"] is not None:
                        raise WaveAbort("unexpected repeated control message: " + child.job.identity)
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
                if child.control is not None:
                    try:
                        child.control.sendall(b"ABORT\n")
                    except OSError:
                        pass

        def drain_until(deadline, *, signal_at_start=None):
            if signal_at_start is not None:
                for child in children:
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
                environment.update(ROVE_START_FD=str(passed.fileno()),
                    ROVE_START_JOB=json.dumps(child.expected, allow_nan=False, separators=(",", ":")))
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
            if authorize_go is not None:
                _release_individually(children, snapshot, authorize_go, observe_transport, event,
                                      deadline=wall_deadline)
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
                notify_completed()
                inspect_failures()
                ticks()
                if authorize_go is not None:
                    cleanup_cancelled()
                if all(child.process.poll() is not None for child in children):
                    break
        except BaseException as error:
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
