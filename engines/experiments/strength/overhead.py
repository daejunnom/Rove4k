"""Bounded, read-only Linux cgroup peak observations for a league cohort.

This observer neither starts nor stops processes, creates groups, modifies a
memory policy, reserves memory, or grants permission to start a game.  The
caller owns the cgroups and child processes and must independently authenticate
artifact, lifecycle, timing and workload evidence.  All output is diagnostic.

The kernel cgroup-v2 memory.peak includes all charged memory for the cgroup and
its descendants.  In particular it can include compiler, Fastchess, engines,
TT pages, page cache and kernel memory.  A virtual TT extent is not a bound on
its resident charge at the instant of peak; this module never subtracts it.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from copy import deepcopy
from pathlib import Path
import re
import time


_SHA = re.compile(r"[0-9a-f]{64}")
_SLOT = re.compile(r"slot-[0-9]{3}")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}")
_MAX = (1 << 63) - 1
_MAX_EXE = 64 << 20
_MAX_SAMPLES = 64
_EVENTS = ("oom", "oom_kill", "oom_group_kill")


class ObservationFailure(ValueError):
    """An observation failed; evidence is diagnostic and never an admission."""

    def __init__(self, message, evidence):
        super().__init__(message)
        self.evidence = evidence


def _positive(value, name):
    if type(value) is not int or not 0 < value <= _MAX:
        raise ValueError(name + " must be a positive bounded integer")
    return value


def _digest(value):
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        raise ValueError("a lowercase SHA-256 identity is required")
    return value


def _number(text, name):
    if not re.fullmatch(r"[0-9]+", text.strip()):
        raise ValueError(name + " is not an unsigned integer")
    result = int(text)
    if result > _MAX:
        raise ValueError(name + " exceeds the bounded integer range")
    return result


def _pairs(path):
    result = {}
    for row in path.read_text(encoding="ascii").splitlines():
        parts = row.split()
        if len(parts) != 2 or parts[0] in result:
            raise ValueError("duplicate or malformed cgroup status")
        result[parts[0]] = _number(parts[1], parts[0])
    return result


def _list(text):
    result = set()
    for part in text.strip().split(","):
        if not re.fullmatch(r"[0-9]+(?:-[0-9]+)?", part):
            raise ValueError("malformed effective cgroup list")
        bounds = [int(x) for x in part.split("-")]
        first, last = bounds[0], bounds[-1]
        if first > last or last - first > 1_000_000:
            raise ValueError("malformed cgroup extent")
        result.update(range(first, last + 1))
    if not result:
        raise ValueError("empty effective cgroup list")
    return tuple(sorted(result))


def _sha_file(path):
    digest, total = hashlib.sha256(), 0
    with path.open("rb") as stream:
        while True:
            data = stream.read(1 << 20)
            if not data:
                break
            total += len(data)
            if total > _MAX_EXE:
                raise ValueError("observed executable exceeds bounded read")
            digest.update(data)
    return digest.hexdigest()


def _stat(proc_root, pid):
    if type(pid) is not int or pid <= 0:
        raise ValueError("positive Linux PID required")
    text = (proc_root / str(pid) / "stat").read_text(encoding="ascii")
    close = text.rfind(")")
    if not text.startswith(str(pid) + " (") or close < 0:
        raise ValueError("malformed process identity")
    fields = text[close + 2:].split()
    if len(fields) < 20:
        raise ValueError("incomplete process identity")
    return {"pid": pid, "ppid": _number(fields[1], "ppid"),
            "pgrp": _number(fields[2], "pgrp"), "session": _number(fields[3], "session"),
            "start_ticks": _number(fields[19], "start_ticks")}


@dataclass(frozen=True)
class Group:
    name: str
    path: Path
    device: int
    inode: int
    nodes: tuple[int, ...]
    cpus: tuple[int, ...]
    events: dict


class CohortPeakObserver:
    """Observe empty fresh game/controller groups across a single full run.

    ``games`` contains exact slot id, cgroup directory, effective cpu/node
    masks and two already-admitted artifact identities.  Artifact fields are
    ``id``, ``whole_sha256``, ``native_sha256`` and ``tt_bytes``.  The caller
    must establish their provenance separately; this observer compares only the
    actual live native image with the supplied native digest.

    ``proc_root`` and ``affinity`` injection are for test fixtures.  Reports
    record their presence and never become runtime or scored-run admission.
    The observer never resets memory.peak; each game/controller cgroup must be
    empty with current and peak zero at begin, before any child is placed.
    """

    def __init__(self, *, profile, root, games, controller, runner_sha256,
                 proc_root=Path("/proc"), affinity=None):
        if profile not in ("test-p16", "test-p192"):
            raise ValueError("named P16/P192 profile required")
        self.profile = profile
        self.workers = 16 if profile == "test-p16" else 192
        self.proc_root = Path(proc_root)
        self.test_inputs = (self.proc_root != Path("/proc") or affinity is not None or
                            not Path(root).is_relative_to(Path("/sys/fs/cgroup")))
        self.affinity = affinity if affinity is not None else os.sched_getaffinity
        self.root = Path(root)
        if not self.root.is_absolute() or self.root.resolve(strict=True) != self.root:
            raise ValueError("cgroup root must be an existing real absolute directory")
        if not isinstance(games, (list, tuple)) or len(games) != (11 if self.workers == 16 else 1):
            raise ValueError("exactly eleven P16 games or one P192 game required")
        self.runner_sha256 = _digest(runner_sha256)
        self.games = []
        ids, paths, used_cpus = set(), [], set()
        for game in games:
            if not isinstance(game, dict) or set(game) != {"slot", "path", "cpus", "nodes", "artifacts"}:
                raise ValueError("exact game observation plan required")
            slot = game["slot"]
            if not isinstance(slot, str) or not _SLOT.fullmatch(slot) or slot in ids:
                raise ValueError("distinct slot ids required")
            cpus, nodes = tuple(game["cpus"]), tuple(game["nodes"])
            if (len(cpus) != self.workers or len(set(cpus)) != len(cpus) or any(type(x) is not int or x < 0 for x in cpus)
                    or not nodes or len(set(nodes)) != len(nodes) or any(type(x) is not int or x < 0 for x in nodes)
                    or (self.workers == 16 and len(nodes) != 1) or used_cpus.intersection(cpus)):
                raise ValueError("game CPU/NUMA envelope differs from the named profile")
            artifacts = game["artifacts"]
            if not isinstance(artifacts, (list, tuple)) or len(artifacts) != 2:
                raise ValueError("two engine artifacts required")
            frozen = []
            for artifact in artifacts:
                if (not isinstance(artifact, dict) or set(artifact) != {"id", "whole_sha256", "native_sha256", "tt_bytes"}
                        or not isinstance(artifact["id"], str) or not _ID.fullmatch(artifact["id"])):
                    raise ValueError("exact named engine artifact identity required")
                frozen.append({"id": artifact["id"], "whole_sha256": _digest(artifact["whole_sha256"]),
                               "native_sha256": _digest(artifact["native_sha256"]),
                               "tt_bytes": _positive(artifact["tt_bytes"], "TT extent")})
                if frozen[-1]["tt_bytes"] > (16 << 30 if self.workers == 16 else 192 << 30):
                    raise ValueError("engine TT extent exceeds the profile cap")
            path = self._path(game["path"])
            ids.add(slot)
            paths.append(path)
            used_cpus.update(cpus)
            self.games.append({"slot": slot, "path": path, "cpus": tuple(sorted(cpus)),
                               "nodes": tuple(sorted(nodes)), "artifacts": frozen})
        self.controller_path = self._path(controller)
        paths.append(self.controller_path)
        if len(set(paths)) != len(paths) or any(a in b.parents for a in paths for b in paths if a != b):
            raise ValueError("game and controller cgroups must be distinct and non-nested")
        self.groups = {}
        self.samples = []
        self.started_ns = None
        self.boot_id = None
        self.previous_peak = {}
        self.active_ids = None
        self.finished = False
        self.controller_sha256 = None
        self.observer_source_sha256 = None

    def _path(self, value):
        path = Path(value)
        if not path.is_absolute() or path.resolve(strict=True) != path or not path.is_relative_to(self.root) or path == self.root:
            raise ValueError("owned cgroup path must be a real descendant of the selected root")
        return path

    def _read_group(self, name, path):
        info = path.stat()
        if name in self.groups and (info.st_dev, info.st_ino) != (self.groups[name].device, self.groups[name].inode):
            raise ValueError("owned cgroup identity changed")
        current = _number((path / "memory.current").read_text(encoding="ascii"), "memory.current")
        peak = _number((path / "memory.peak").read_text(encoding="ascii"), "memory.peak")
        events = _pairs(path / "memory.events")
        state = _pairs(path / "cgroup.events")
        if "populated" not in state or "oom" not in events or "oom_kill" not in events:
            raise ValueError("required cgroup lifecycle/OOM evidence unavailable")
        members = {_number(row, "cgroup PID") for row in (path / "cgroup.procs").read_text(encoding="ascii").splitlines()}
        nodes = _list((path / "cpuset.mems.effective").read_text(encoding="ascii"))
        cpus = _list((path / "cpuset.cpus.effective").read_text(encoding="ascii"))
        if peak < current or peak < self.previous_peak.get(name, 0):
            raise ValueError("cgroup memory peak is inconsistent or regressed")
        self.previous_peak[name] = peak
        return Group(name, path, info.st_dev, info.st_ino, nodes, cpus, events), current, peak, state, members

    def begin(self):
        if self.started_ns is not None:
            raise ValueError("cohort observer has already begun")
        boot = (self.proc_root / "sys/kernel/random/boot_id").read_text(encoding="ascii").strip()
        if not re.fullmatch(r"[0-9a-fA-F-]{36}", boot):
            raise ValueError("kernel boot identity unavailable")
        self.boot_id, self.started_ns = boot.lower(), time.monotonic_ns()
        self.observer_source_sha256 = _sha_file(Path(__file__))
        self.started_utc = datetime.now(timezone.utc).isoformat()
        plans = [(g["slot"], g["path"], g["cpus"], g["nodes"]) for g in self.games]
        plans.append(("controller", self.controller_path, None, None))
        for name, path, cpus, nodes in plans:
            group, current, peak, state, members = self._read_group(name, path)
            if current or peak or state["populated"] or members or any(group.events.get(key, 0) for key in _EVENTS):
                raise ValueError("fresh empty cgroup with zero prior peak required")
            if cpus is not None and (group.cpus != cpus or group.nodes != nodes):
                raise ValueError("effective game masks differ from planned masks")
            self.groups[name] = group
        game_cpus = {cpu for game in self.games for cpu in game["cpus"]}
        controller_cpus = set(self.groups["controller"].cpus)
        if self.workers == 16 and (controller_cpus.intersection(game_cpus) or len(controller_cpus) != 16):
            raise ValueError("P16 controller requires sixteen distinct reserved CPUs")
        if self.workers == 192 and controller_cpus != game_cpus:
            raise ValueError("P192 controller must share the full game CPU envelope")
        return {"boot_id": self.boot_id, "started_ns": self.started_ns,
                "fresh_empty_groups": len(self.groups), "runtime_admission": False}

    def _process(self, pid, expected_sha, group, *, observe_threads=False):
        before = _stat(self.proc_root, pid)
        executable = self.proc_root / str(pid) / "exe"
        file_before = executable.stat()
        actual = _sha_file(executable)
        file_after = executable.stat()
        mask = set(self.affinity(pid))
        after = _stat(self.proc_root, pid)
        image_before = (file_before.st_dev, file_before.st_ino, file_before.st_size,
                        file_before.st_mtime_ns, file_before.st_ctime_ns)
        image_after = (file_after.st_dev, file_after.st_ino, file_after.st_size,
                       file_after.st_mtime_ns, file_after.st_ctime_ns)
        if before != after or image_before != image_after or actual != expected_sha or not mask or not mask <= set(group.cpus):
            raise ValueError("live process identity, executable or affinity differs")
        threads, thread_affinities = [], []
        if observe_threads:
            for task in (self.proc_root / str(pid) / "task").iterdir():
                if not task.name.isdecimal():
                    continue
                tid = int(task.name)
                if tid <= 0:
                    raise ValueError("invalid engine thread identity")
                affinity = set(self.affinity(tid))
                if not affinity or not affinity <= set(group.cpus):
                    raise ValueError("thread affinity escapes game slot")
                threads.append(tid)
                thread_affinities.append({"tid": tid, "cpu_mask": sorted(affinity)})
            if not threads or pid not in threads:
                raise ValueError("engine leader thread was not observed")
            if _stat(self.proc_root, pid) != before:
                raise ValueError("engine identity changed during thread observation")
        return {**before, "native_sha256": actual,
                "executable_identity": {"device": image_before[0], "inode": image_before[1],
                                        "bytes": image_before[2], "mtime_ns": image_before[3],
                                        "ctime_ns": image_before[4]},
                "cpu_mask": sorted(mask), "thread_ids": sorted(threads),
                "thread_affinities": sorted(thread_affinities, key=lambda row: row["tid"]),
                "observed_thread_count": len(threads) if observe_threads else None,
                "requested_worker_count": self.workers if observe_threads else None,
                "worker_set_complete_verified": False, "worker_cpu_activity_verified": False}

    def sample_active(self, *, members, controller_pid, controller_sha256):
        """Sample all simultaneous game members and controller while alive.

        ``members`` maps each slot to ``runner`` PID and ordered ``engines``
        PIDs. The observer sees live cgroup membership and image/affinity; it
        cannot infer whether each engine actually searched or touched all TT.
        """
        if self.started_ns is None or self.finished or not isinstance(members, dict) or set(members) != {g["slot"] for g in self.games}:
            raise ValueError("begin and the full planned cohort are required")
        if len(self.samples) >= _MAX_SAMPLES:
            raise ValueError("bounded cohort sample count exceeded")
        controller_sha256 = _digest(controller_sha256)
        if self.controller_sha256 is not None and self.controller_sha256 != controller_sha256:
            raise ValueError("controller executable identity changed")
        started = time.monotonic_ns()
        if (self.proc_root / "sys/kernel/random/boot_id").read_text(encoding="ascii").strip().lower() != self.boot_id:
            raise ValueError("kernel boot identity changed")
        if _sha_file(Path(__file__)) != self.observer_source_sha256:
            raise ValueError("observer source file changed during observation")
        observed, all_pids = [], set()
        identities = {}
        for game in self.games:
            row = members[game["slot"]]
            if not isinstance(row, dict) or set(row) != {"runner", "engines"} or not isinstance(row["engines"], (list, tuple)) or len(row["engines"]) != 2:
                raise ValueError("one runner and two ordered engine PIDs per slot required")
            group, current, peak, state, procs = self._read_group(game["slot"], game["path"])
            if (group.cpus != game["cpus"] or group.nodes != game["nodes"] or not state["populated"]
                    or not current or not peak):
                raise ValueError("active game cgroup masks or lifecycle differ")
            pids = [row["runner"], *row["engines"]]
            if any(type(pid) is not int or pid <= 0 for pid in pids) or len(set(pids)) != 3 or not set(pids) <= procs:
                raise ValueError("expected live members are not in the game cgroup")
            if all_pids.intersection(pids):
                raise ValueError("a live process cannot belong to multiple game slots")
            all_pids.update(pids)
            runner = self._process(row["runner"], self.runner_sha256, group)
            engines = [self._process(pid, artifact["native_sha256"], group, observe_threads=True)
                       for pid, artifact in zip(row["engines"], game["artifacts"])]
            identities[game["slot"]] = [(p["pid"], p["start_ticks"]) for p in [runner, *engines]]
            observed.append({"slot": game["slot"], "cgroup": {"device": group.device, "inode": group.inode},
                             "cpus": list(group.cpus), "nodes": list(group.nodes), "current_bytes": current,
                             "lifetime_peak_bytes": peak, "events": group.events, "runner": runner, "engines": engines})
        control, current, peak, state, procs = self._read_group("controller", self.controller_path)
        if (not state["populated"] or not current or not peak or controller_pid not in procs or controller_pid in all_pids
                or control.cpus != self.groups["controller"].cpus or control.nodes != self.groups["controller"].nodes):
            raise ValueError("expected controller is not in its dedicated cgroup")
        controller = self._process(controller_pid, controller_sha256, control)
        identities["controller"] = [(controller["pid"], controller["start_ticks"])]
        # Recheck after collecting the last slot. Sequential observations do
        # not establish simultaneity without independent cgroup-writer fencing.
        for game in self.games:
            group, _, _, state, procs = self._read_group(game["slot"], game["path"])
            if group.cpus != game["cpus"] or group.nodes != game["nodes"]:
                raise ValueError("game masks changed during the active sample")
            for pid, ticks in identities[game["slot"]]:
                if not state["populated"] or pid not in procs or _stat(self.proc_root, pid)["start_ticks"] != ticks:
                    raise ValueError("cohort member exited or moved during the active sample")
        _, _, _, control_state, control_members = self._read_group("controller", self.controller_path)
        for pid, ticks in identities["controller"]:
            if not control_state["populated"] or pid not in control_members or _stat(self.proc_root, pid)["start_ticks"] != ticks:
                raise ValueError("controller identity changed during the active sample")
        if self.active_ids is not None and identities != self.active_ids:
            raise ValueError("active cohort member identity changed between samples")
        self.active_ids = identities
        self.controller_sha256 = controller_sha256
        sample = {"started_ns": started, "completed_ns": time.monotonic_ns(), "games": observed,
                  "controller": {"cgroup": {"device": control.device, "inode": control.inode},
                                 "cpus": list(control.cpus), "nodes": list(control.nodes),
                                 "current_bytes": current, "lifetime_peak_bytes": peak,
                                 "events": control.events, "process": controller}}
        self.samples.append(deepcopy(sample))
        return deepcopy(sample)

    def finish(self, *, per_game_headroom_bytes, controller_headroom_bytes):
        """Read terminal game-group peaks after all game members physically leave.

        Controller may remain alive while reporting; its peak is observed but
        its eventual cleanup is not claimed. Additional headroom is explicitly
        configured, not inferred from a sampled run or certified sufficient.
        """
        if self.started_ns is None or not self.samples or self.finished:
            raise ValueError("at least one full active-cohort sample is required")
        game_margin = _positive(per_game_headroom_bytes, "per-game headroom")
        controller_margin = _positive(controller_headroom_bytes, "controller headroom")
        if (self.proc_root / "sys/kernel/random/boot_id").read_text(encoding="ascii").strip().lower() != self.boot_id:
            raise ValueError("kernel boot identity changed")
        if _sha_file(Path(__file__)) != self.observer_source_sha256:
            raise ValueError("observer source file changed during observation")
        final = []
        for game in self.games:
            name = game["slot"]
            group, current, peak, state, members = self._read_group(name, game["path"])
            if state["populated"] or members:
                raise ValueError("game cgroup still contains live processes")
            if group.cpus != game["cpus"] or group.nodes != game["nodes"]:
                raise ValueError("game effective masks changed before finalization")
            for pid, ticks in self.active_ids[name]:
                try:
                    live = _stat(self.proc_root, pid)
                except FileNotFoundError:
                    continue
                if live["start_ticks"] == ticks:
                    raise ValueError("an observed game process remains alive outside its original cgroup")
            initial = self.groups[name]
            for key in _EVENTS:
                if group.events.get(key, 0) != initial.events.get(key, 0):
                    raise ObservationFailure("game cgroup OOM event occurred", {
                        "group": name, "path": str(group.path), "device": group.device, "inode": group.inode,
                        "boot_id": self.boot_id, "observed_ns": time.monotonic_ns(),
                        "initial_events": {event: initial.events.get(event, 0) for event in _EVENTS},
                        "final_events": {event: group.events.get(event, 0) for event in _EVENTS},
                        "current_bytes": current, "lifetime_peak_bytes": peak,
                        "runtime_admission": False})
            final.append({"slot": name, "cgroup": {"device": group.device, "inode": group.inode},
                          "final_current_bytes": current, "lifetime_peak_bytes": peak,
                          "oom_events": {key: group.events.get(key, 0) for key in _EVENTS}})
        control, current, peak, state, members = self._read_group("controller", self.controller_path)
        controller_pid, controller_ticks = self.active_ids["controller"][0]
        if (not state["populated"] or controller_pid not in members or
                _stat(self.proc_root, controller_pid)["start_ticks"] != controller_ticks or
                _sha_file(self.proc_root / str(controller_pid) / "exe") != self.controller_sha256 or
                control.cpus != self.groups["controller"].cpus or control.nodes != self.groups["controller"].nodes):
            raise ValueError("controller cgroup must remain observable at finalization")
        if not set(self.affinity(controller_pid)) or not set(self.affinity(controller_pid)) <= set(control.cpus):
            raise ValueError("controller affinity changed before finalization")
        for key in _EVENTS:
            if control.events.get(key, 0) != self.groups["controller"].events.get(key, 0):
                raise ObservationFailure("controller cgroup OOM event occurred", {
                    "group": "controller", "path": str(control.path), "device": control.device,
                    "inode": control.inode, "boot_id": self.boot_id, "observed_ns": time.monotonic_ns(),
                    "initial_events": {event: self.groups["controller"].events.get(event, 0) for event in _EVENTS},
                    "final_events": {event: control.events.get(event, 0) for event in _EVENTS},
                    "current_bytes": current, "lifetime_peak_bytes": peak,
                    "runtime_admission": False})
        max_peak = max(row["lifetime_peak_bytes"] for row in final)
        all_in_per_game = max_peak + game_margin
        all_in_controller = peak + controller_margin
        all_in_cohort = all_in_per_game * len(final) + all_in_controller
        if all_in_per_game > _MAX or all_in_controller > _MAX or all_in_cohort > _MAX:
            raise ValueError("peak and headroom exceed bounded integer range")
        plans = [{"slot": g["slot"], "cgroup_path": str(g["path"]), "cpus": list(g["cpus"]), "nodes": list(g["nodes"]),
                  "artifacts": g["artifacts"]} for g in self.games]
        report = {"format": "rove4k-cohort-peak-observation-v2", "profile": self.profile,
                  "boot_id": self.boot_id, "started_utc": self.started_utc,
                  "started_ns": self.started_ns, "finished_ns": time.monotonic_ns(),
                  "observer_source_sha256": self.observer_source_sha256, "runner_sha256": self.runner_sha256,
                  "test_inputs": self.test_inputs, "cgroup_root": str(self.root),
                  "controller_cgroup_path": str(self.controller_path), "controller_sha256": self.controller_sha256,
                  "plan": plans, "samples": self.samples,
                  "finished_game_groups": final,
                  "controller": {"cgroup": {"device": control.device, "inode": control.inode},
                                 "current_bytes": current, "lifetime_peak_bytes": peak,
                                 "oom_events": {key: control.events.get(key, 0) for key in _EVENTS}},
                  "arithmetic": {"observed_max_game_peak_bytes": max_peak,
                                 "configured_per_game_headroom_bytes": game_margin,
                                 "observed_controller_peak_bytes": peak,
                                 "configured_controller_headroom_bytes": controller_margin,
                                 "legacy_per_game_overhead_bytes": all_in_per_game,
                                 "legacy_controller_reserve_bytes": all_in_controller,
                                 "all_in_per_game_envelope_bytes": all_in_per_game,
                                 "all_in_controller_envelope_bytes": all_in_controller,
                                 "all_in_cohort_envelope_bytes": all_in_cohort,
                                 "legacy_double_counts_tt": True},
                  "game_groups_empty_observed": True, "controller_cleanup_observed": False,
                  "artifact_source_provenance_verified": False, "all_tt_resident_verified": False,
                  "representative_search_workload_verified": False, "future_peak_bound_verified": False,
                  "worker_completeness_verified": False, "worker_cpu_activity_verified": False,
                  "external_cgroup_writer_excluded": False, "process_charges_complete": False,
                  "executable_continuity_verified": False,
                  "observer_loaded_source_verified": False,
                  "observer_and_external_system_charges_included": False, "physical_topology_verified": False,
                  "simultaneous_cohort_presence_verified": False,
                  "runtime_admission": False,
                  "scored_qualification": False,
                  "scope": "whole-lifetime cgroup charged peak; TT not subtracted; configured headroom is not a proven bound"}
        raw = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
        report["observation_sha256"] = hashlib.sha256(raw).hexdigest()
        self.finished = True
        return report


def inspect_report(report, *, profile, plan, boot_id, cgroup_root, controller_cgroup_path,
                   runner_sha256, controller_sha256, observer_source_sha256,
                   now_monotonic_ns, max_age_ns):
    """Check a diagnostic report's integrity and caller-supplied context.

    This deliberately does not authenticate the producer or prove the values
    were measured: an attacker can construct matching JSON and a matching SHA.
    The caller must obtain report bytes and expected context from a trusted,
    fenced observer and separately verify host identity, owner and workload.
    Passing this check never grants runtime or league admission.
    """
    if not isinstance(report, dict):
        raise ValueError("observation report must be a JSON object")
    supplied = report.get("observation_sha256")
    _digest(supplied)
    core = dict(report)
    del core["observation_sha256"]
    raw = json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    if hashlib.sha256(raw).hexdigest() != supplied:
        raise ValueError("observation report digest differs")
    if (profile not in ("test-p16", "test-p192") or report.get("profile") != profile
            or report.get("format") != "rove4k-cohort-peak-observation-v2"
            or not isinstance(plan, list) or report.get("plan") != plan
            or not isinstance(boot_id, str) or report.get("boot_id") != boot_id
            or not isinstance(cgroup_root, str) or report.get("cgroup_root") != cgroup_root
            or not isinstance(controller_cgroup_path, str) or report.get("controller_cgroup_path") != controller_cgroup_path
            or report.get("runner_sha256") != _digest(runner_sha256)
            or report.get("controller_sha256") != _digest(controller_sha256)
            or report.get("observer_source_sha256") != _digest(observer_source_sha256)):
        raise ValueError("observation context differs from the caller's expected values")
    started, finished = report.get("started_ns"), report.get("finished_ns")
    if (type(now_monotonic_ns) is not int or type(max_age_ns) is not int or max_age_ns <= 0
            or type(started) is not int or type(finished) is not int or started < 0 or finished < started
            or now_monotonic_ns < finished
            or now_monotonic_ns - finished > max_age_ns):
        raise ValueError("observation freshness cannot be established")
    if report.get("runtime_admission") is not False or report.get("scored_qualification") is not False:
        raise ValueError("diagnostic report cannot assert runtime or scored qualification")
    return {"digest_matches": True, "context_matches": True, "within_supplied_age_window": True,
            "authenticated": False, "actual_owner_verified": False,
            "runtime_admission": False, "scored_qualification": False}
