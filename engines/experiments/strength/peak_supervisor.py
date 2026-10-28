"""Optional functional-only supervisor for a cooperative controller.

This is not a scored league launcher or a resource-admission authority.  The
caller must create the fresh, delegated cgroups before calling ``observe``;
the controller must implement the small protocol below and own its games.
No timeout or protocol failure signals, kills, or reaps a running child.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import select
import socket
import subprocess
import sys
import threading
import time

try:
    from . import overhead, placement, peak_capacity
except ImportError:
    import overhead
    import placement
    import peak_capacity


_LIMIT = 1 << 20
_FD_ENV = "ROVE4K_PEAK_SUPERVISOR_FD"


class SupervisorFailure(RuntimeError):
    """Failure retains the child handle: its owner must reconcile it."""

    def __init__(self, message, process=None, evidence=None):
        super().__init__(message)
        self.process = process
        self.evidence = evidence


class _Channel:
    def __init__(self, sock):
        self.sock, self.buffer = sock, bytearray()

    def send(self, value, *, timeout=60):
        payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n"
        if len(payload) > _LIMIT:
            raise ValueError("protocol message exceeds its bound")
        deadline = time.monotonic() + timeout
        view = memoryview(payload)
        while view:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([], [self.sock], [], remaining)[1]:
                raise TimeoutError("diagnostic send timed out; child not terminated")
            try:
                count = self.sock.send(view, socket.MSG_DONTWAIT)
            except BlockingIOError:
                continue
            if count <= 0:
                raise EOFError("controller closed diagnostic channel")
            view = view[count:]

    def receive(self, deadline):
        while True:
            where = self.buffer.find(b"\n")
            if where >= 0:
                raw = bytes(self.buffer[:where])
                del self.buffer[:where + 1]
                value = json.loads(raw.decode("utf-8"))
                if not isinstance(value, dict):
                    raise ValueError("controller message must be an object")
                return value
            remaining = None if deadline is None else deadline - time.monotonic()
            if (remaining is not None and remaining <= 0) or not select.select([self.sock], [], [], remaining)[0]:
                raise TimeoutError("diagnostic protocol deadline expired; child not terminated")
            data = self.sock.recv(min(65536, _LIMIT + 1 - len(self.buffer)))
            if not data:
                raise EOFError("controller closed diagnostic channel")
            self.buffer.extend(data)
            if len(self.buffer) > _LIMIT:
                raise ValueError("protocol message exceeds its bound")


class ControllerChannel:
    """Controller-side calls; neither request nor response authorizes GO.

    Call ``handoff`` to receive original group identities, then ``active``
    with actual current PIDs only after launching the complete
    cohort. After all games have physically ended, call ``settled`` while the
    controller is still alive. I/O or observer failures return False; a caller
    must continue owning any already-started games and must not abort them just
    because diagnostic observation failed.
    """

    def __init__(self):
        raw = os.environ.pop(_FD_ENV, None)
        if raw is None or not raw.isdecimal():
            raise ValueError("missing diagnostic supervisor channel")
        self.channel = _Channel(socket.socket(fileno=int(raw)))
        # Fastchess/engines must not keep the controller's protocol socket open.
        os.set_inheritable(self.channel.sock.fileno(), False)
        self.state = "new"

    def handoff(self, *, timeout=60):
        if self.state != "new" or not 0 < timeout <= 86400:
            raise ValueError("one bounded group handoff is required")
        try:
            data = self.channel.receive(time.monotonic() + timeout)
            if set(data) != {"kind", "games", "controller", "runtime_admission"} or data["kind"] != "groups" or data["runtime_admission"] is not False:
                raise ValueError("invalid supervisor group handoff")
        except (OSError, EOFError, TimeoutError, ValueError):
            self.state = "unavailable"
            return None
        self.state = "groups"
        return data

    def _exchange(self, request, expected, timeout):
        if not 0 < timeout <= 86400:
            raise ValueError("invalid diagnostic response timeout")
        self.channel.send(request, timeout=timeout)
        response = self.channel.receive(time.monotonic() + timeout)
        if response != {"kind": expected, "runtime_admission": False}:
            raise SupervisorFailure("diagnostic supervisor did not acknowledge " + expected)

    def active(self, members, *, timeout=60):
        if self.state != "groups":
            raise ValueError("group handoff must precede the active cohort")
        try:
            self._exchange({"kind": "active", "members": members}, "sampled", timeout)
        except (OSError, EOFError, TimeoutError, ValueError, SupervisorFailure):
            self.state = "unavailable"
            return False
        self.state = "active"
        return True

    def settled(self, *, timeout=60):
        if self.state != "active":
            raise ValueError("active cohort must precede settlement")
        try:
            self._exchange({"kind": "settled"}, "finished", timeout)
        except (OSError, EOFError, TimeoutError, ValueError, SupervisorFailure):
            self.state = "unavailable"
            return False
        self.state = "finished"
        return True


def _group_records(observer):
    result = {}
    for name, group in observer.groups.items():
        value = (group.path / "memory.max").read_text(encoding="ascii").strip()
        if not value.isdecimal():
            raise ValueError("a bounded kernel memory.max is required")
        record = {"path": str(group.path), "device": group.device, "inode": group.inode,
                  "cpus": list(group.cpus), "memory_nodes": list(group.nodes), "memory_max": int(value)}
        placement.verify_cgroup_live(record)
        result[name] = record
    controller = result.pop("controller")
    return {"kind": "groups", "games": result, "controller": controller, "runtime_admission": False}


class CapacityPending(ValueError):
    """Compatibility error for an unavailable diagnostic capacity observation."""
    def __init__(self, assessment):
        super().__init__("diagnostic capacity observation is unavailable")
        self.assessment = assessment


def _require_live_capacity_owner(**arguments):
    """Read real capacity for a pre-GO probe, not a scored launch authority.

    The original cgroup2 mount and leaf identities are checked on the actual
    Linux host.  The resulting snapshot is neither a physical reservation nor
    proof that another host process cannot consume memory concurrently.
    """
    if any(arguments.get(name) is None for name in ("frozen_topology", "groups", "controller")):
        raise ValueError("diagnostic launch requires original live capacity and group identities")
    try:
        from . import peak_probe_session
    except ImportError:
        import peak_probe_session
    peak_probe_session._require_delegated_root(Path(arguments["root"]))
    assessment = peak_capacity.inspect_capacity(**arguments)
    if (type(assessment) is not dict or assessment.get("format") != "rove4k-diagnostic-capacity-assessment-v1"
            or assessment.get("profile") != arguments.get("profile")
            or assessment.get("runtime_admission") is not False
            or assessment.get("launch_permitted") is not False):
        raise ValueError("live capacity assessment differs from the diagnostic contract")
    return assessment


def _validate_probe_command(argv, *, profile, games, runner_sha256, frozen_topology):
    """Permit only the repository's pre-GO probe with its exact pinned plan.

    ``observe`` is public and cannot assume callers went through
    OwnedProbeCohort. An arbitrary controller could send GO, or supply a
    smaller TT extent to the capacity check than its actual manifest uses.
    """
    try:
        from . import peak_ready_probe
    except ImportError:
        import peak_ready_probe
    if (not isinstance(argv, (tuple, list)) or len(argv) != 6 or
            any(not isinstance(arg, str) or not arg or "\0" in arg for arg in argv) or
            argv[2] != "--manifest" or argv[4] != "--manifest-sha256" or
            not Path(argv[0]).is_absolute() or not Path(argv[1]).is_absolute() or
            not Path(argv[3]).is_absolute() or
            argv[0] != str(Path(sys.executable).resolve(strict=True)) or
            argv[1] != str(Path(peak_ready_probe.__file__).resolve(strict=True))):
        raise ValueError("only the pinned pre-GO diagnostic controller is supported")
    manifest = peak_ready_probe.load_controller_manifest(Path(argv[3]), argv[5])
    if (manifest.get("profile") != profile or manifest.get("topology") != frozen_topology
            or manifest.get("runner_sha256") != runner_sha256 or not isinstance(games, list)):
        raise ValueError("diagnostic manifest and capacity context differ")
    entries = manifest.get("entries")
    if not isinstance(entries, list) or len(entries) != len(games):
        raise ValueError("diagnostic manifest and capacity cohort differ")
    by_slot = {row.get("slot"): row for row in games if isinstance(row, dict)}
    if len(by_slot) != len(games):
        raise ValueError("diagnostic capacity slots are not distinct")
    for entry in entries:
        slot, commands = entry.get("slot"), entry.get("engines")
        if (slot is None or not isinstance(commands, list) or len(commands) != 2 or
                slot.id not in by_slot or any(not isinstance(row, dict) or
                set(row) != {"id", "path", "whole_sha256", "native_sha256", "tt_bytes"} for row in commands)):
            raise ValueError("diagnostic manifest has an invalid engine cohort")
        game = by_slot[slot.id]
        expected = [{key: row[key] for key in ("id", "whole_sha256", "native_sha256", "tt_bytes")}
                    for row in commands]
        if (game.get("cpus") != sorted(slot.cpus) or game.get("nodes") != sorted(slot.memory_nodes)
                or game.get("artifacts") != expected):
            raise ValueError("diagnostic manifest and capacity engine extents differ")
    if {entry["slot"].id for entry in entries} != set(by_slot):
        raise ValueError("diagnostic manifest and capacity slot identities differ")


def _bind_capacity_report(report, assessment):
    """Retain the live preflight in the integrity-protected diagnostic report."""
    if type(report) is not dict or "capacity_preflight" in report:
        raise ValueError("invalid diagnostic report")
    supplied = report.get("observation_sha256")
    core = dict(report)
    core.pop("observation_sha256", None)
    encoded = json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    if not isinstance(supplied, str) or hashlib.sha256(encoded).hexdigest() != supplied:
        raise ValueError("diagnostic report integrity differs before preflight binding")
    core["capacity_preflight"] = assessment
    encoded = json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")
    core["observation_sha256"] = hashlib.sha256(encoded).hexdigest()
    return core


def _verify_handoff(handoff, group_records, controller_record):
    """Recheck the original bounded leaves just before controller creation."""
    fields = ("path", "device", "inode", "cpus", "memory_nodes", "memory_max")
    def identity(record):
        if type(record) is not dict or any(key not in record for key in fields):
            raise ValueError("original diagnostic cgroup identity is incomplete")
        return {key: record[key] for key in fields}
    if (type(handoff) is not dict or type(group_records) is not dict or
            type(handoff.get("games")) is not dict or
            set(handoff["games"]) != set(group_records) or
            identity(handoff.get("controller")) != identity(controller_record)):
        raise ValueError("diagnostic controller cgroup changed after preflight")
    for name, record in group_records.items():
        if identity(handoff["games"][name]) != identity(record):
            raise ValueError("diagnostic game cgroup changed after preflight")


def _failure_snapshot(observer, assessment, cause):
    """Best-effort cgroup OOM evidence without disturbing any live child.

    This is a point-in-time observation. If a group cannot be read or remains
    populated, a later OOM or change may not be reflected here.
    """
    groups, oom_observed, all_read = [], False, True
    for name, original in observer.groups.items():
        try:
            current, used, peak, state, members = observer._read_group(name, original.path)
            if (current.device, current.inode) != (original.device, original.inode):
                raise ValueError("cgroup identity changed during failure observation")
            before = {key: original.events.get(key, 0) for key in overhead._EVENTS}
            after = {key: current.events.get(key, 0) for key in overhead._EVENTS}
            if any(after[key] < before[key] for key in overhead._EVENTS):
                raise ValueError("cgroup OOM counter regressed")
            oom_observed = oom_observed or any(after[key] > before[key] for key in overhead._EVENTS)
            groups.append({"group": name, "path": str(current.path), "device": current.device,
                           "inode": current.inode, "current_bytes": used, "peak_bytes": peak,
                           "initial_events": before, "observed_events": after,
                           "populated": state.get("populated"), "member_pids": sorted(members)})
        except BaseException as error:
            all_read = False
            groups.append({"group": name, "read_error": repr(error)})
    initial_oom = cause.evidence if isinstance(cause, overhead.ObservationFailure) else None
    if isinstance(initial_oom, dict):
        before, after = initial_oom.get("initial_events", {}), initial_oom.get("final_events", {})
        if isinstance(before, dict) and isinstance(after, dict):
            oom_observed = oom_observed or any(type(before.get(key)) is int and type(after.get(key)) is int
                                               and after[key] > before[key] for key in overhead._EVENTS)
    return {"format": "rove4k-pre-go-probe-failure-v1", "cause": str(cause),
            "capacity_preflight": assessment, "groups": groups, "oom_observed": oom_observed,
            "initial_observation_failure": initial_oom,
            "scope": "point-in-time only; later OOM or group changes are not excluded",
            "all_groups_read": all_read, "physical_settlement_proven": False,
            "runtime_admission": False, "scored_qualification": False}


def observe(*, profile, root, games, controller, runner_sha256, controller_sha256,
            argv, per_game_headroom_bytes, controller_headroom_bytes, timeout_seconds,
            frozen_topology=None, group_records=None, controller_record=None):
    """Start and observe one cooperative functional-only controller.

    The controller cgroup and all game cgroups must already exist empty and
    stay owned by the caller. The controller must inherit the passed socket,
    launch games in the specified game cgroups, and use ControllerChannel.
    Parent receives a child handle even after successful report generation;
    joining and cleanup remain the caller's responsibility. The returned
    report is diagnostic, not authenticated admission or a future peak bound.
    The timeout bounds both initial active sampling and the wait for settlement,
    separately. A settlement timeout returns the still-owned child in
    SupervisorFailure for reconciliation; it does not signal, kill, or reap it.
    A caller must preserve any game that may have received GO.
    """
    if os.name != "posix" or not hasattr(os, "sched_setaffinity"):
        raise RuntimeError("Linux cgroup and affinity support required")
    if threading.active_count() != 1:
        raise RuntimeError("launch requires a single-threaded supervisor for safe pre-exec setup")
    if not isinstance(timeout_seconds, (int, float)) or not 0 < timeout_seconds <= 86400:
        raise ValueError("bounded diagnostic timeout required")
    _validate_probe_command(argv, profile=profile, games=games, runner_sha256=runner_sha256,
                            frozen_topology=frozen_topology)
    assessment = _require_live_capacity_owner(profile=profile, root=root, games=games,
                                 groups=group_records, controller=controller_record,
                                 controller_path=controller,
                                 frozen_topology=frozen_topology,
                                 per_game_headroom_bytes=per_game_headroom_bytes,
                                 controller_headroom_bytes=controller_headroom_bytes)
    if overhead._sha_file(Path(argv[0])) != controller_sha256:
        raise ValueError("controller executable digest differs before launch")
    observer = overhead.CohortPeakObserver(profile=profile, root=root, games=games,
                                           controller=controller, runner_sha256=runner_sha256)
    observer.begin()  # Must precede any charge to the controller or game groups.
    handoff = _group_records(observer)
    _verify_handoff(handoff, group_records, controller_record)
    group = observer.groups["controller"]
    group_fd = os.open(group.path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    stat = os.fstat(group_fd)
    if (stat.st_dev, stat.st_ino) != (group.device, group.inode):
        os.close(group_fd)
        raise ValueError("controller cgroup identity changed before launch")
    try:
        parent, child = socket.socketpair()
    except BaseException:
        os.close(group_fd)
        raise
    process = None
    try:
        # Functional diagnostic controllers do not need host credentials or
        # a copy of the caller's arbitrary environment.
        env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "TZ": "UTC", _FD_ENV: str(child.fileno())}

        def enter_controller_group():
            stat = os.fstat(group_fd)
            if (stat.st_dev, stat.st_ino) != (group.device, group.inode):
                raise ValueError("controller cgroup identity changed before launch")
            target = os.open("cgroup.procs", os.O_WRONLY | os.O_NOFOLLOW, dir_fd=group_fd)
            try:
                value = str(os.getpid()).encode("ascii")
                if os.write(target, value) != len(value):
                    raise OSError("short cgroup membership write")
            finally:
                os.close(target)
                os.close(group_fd)
            os.sched_setaffinity(0, set(group.cpus))
            if set(os.sched_getaffinity(0)) != set(group.cpus):
                raise ValueError("controller affinity differs from its cgroup")

        process = subprocess.Popen(argv, env=env, pass_fds=(child.fileno(), group_fd),
                                   preexec_fn=enter_controller_group, start_new_session=True)
        child.close()
        channel = _Channel(parent)
        deadline = time.monotonic() + timeout_seconds
        channel.send(handoff, timeout=timeout_seconds)
        request = channel.receive(deadline)
        if set(request) != {"kind", "members"} or request["kind"] != "active":
            raise ValueError("expected active full-cohort request")
        observer.sample_active(members=request["members"], controller_pid=process.pid,
                               controller_sha256=controller_sha256)
        channel.send({"kind": "sampled", "runtime_admission": False})
        # A diagnostic controller can stall or lose its channel after the
        # active snapshot. Bound observation without terminating its owner:
        # uncertain children remain the caller's responsibility on failure.
        request = channel.receive(time.monotonic() + timeout_seconds)
        if request != {"kind": "settled"}:
            raise ValueError("expected physically settled cohort request")
        report = observer.finish(per_game_headroom_bytes=per_game_headroom_bytes,
                                 controller_headroom_bytes=controller_headroom_bytes)
        channel.send({"kind": "finished", "runtime_admission": False})
        return _bind_capacity_report(report, assessment), process
    except BaseException as error:
        # Never turn observation failure into termination of a real game.
        try:
            evidence = _failure_snapshot(observer, assessment, error)
        except BaseException as snapshot_error:
            evidence = {"format": "rove4k-pre-go-probe-failure-v1", "cause": str(error),
                        "snapshot_error": repr(snapshot_error), "all_groups_read": False,
                        "oom_observed": False, "physical_settlement_proven": False,
                        "runtime_admission": False, "scored_qualification": False}
        raise SupervisorFailure(str(error), process=process, evidence=evidence) from error
    finally:
        child.close()
        parent.close()
        os.close(group_fd)
