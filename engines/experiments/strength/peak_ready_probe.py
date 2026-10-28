"""A diagnostic, pre-GO-only cohort probe using supervisor-owned groups.

This probe cannot release a game, issue a score, or authorize AWS spending. It
uses the normal placement and Fastchess READY path so that an independent
peak supervisor can inspect a live, simultaneous initialization cohort. It
does not prove search workload, resident TT, or future memory requirements.
The supervisor retains ownership of groups; this module never removes them.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

try:
    from . import fastchess, placement, topology, wave, run, peak_supervisor, peak_receipt
except ImportError:
    import fastchess, placement, topology, wave, run, peak_supervisor, peak_receipt


class ProbeFailure(RuntimeError):
    """Keep returned owner observations for reconciliation when unproven."""
    def __init__(self, message, observations):
        super().__init__(message)
        self.observations = observations


def _require_unreleased(observations, expected_ids):
    if (len(observations) != len(expected_ids) or
            {row.get("identity") for row in observations} != set(expected_ids) or
            any(row.get("gate_released") is not False or row.get("gate_cancelled") is not True or
                row.get("gate_authorized") is not False or row.get("gate_authorization_unknown") is not False or
                row.get("gate_transport") != "not_attempted" for row in observations)):
        raise ProbeFailure("probe GO state is uncertain; preserve all owners for reconciliation", observations)


def _file_sha(path):
    path = run.protected_input(path)
    if not path.is_file() or path.is_symlink():
        raise ValueError("an explicit regular non-symlink executable is required")
    run.protected_input(path.resolve(strict=True))
    value = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            value.update(block)
    return value.hexdigest()


def _read_receipt(path):
    if not hasattr(os, "O_NOFOLLOW"):
        raise RuntimeError("Linux no-follow receipt opening is required")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as source:
        before = os.fstat(source.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > 131072:
            raise ValueError("placement receipt is not a bounded regular file")
        raw = source.read(131073)
        after = os.fstat(source.fileno())
    current = path.lstat()
    if (len(raw) > 131072 or
            (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) !=
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns) or
            (current.st_dev, current.st_ino) != (before.st_dev, before.st_ino)):
        raise ValueError("placement receipt changed during read")
    return json.loads(raw)


def accept_supervisor_groups(*, slots, channel, include_controller_nodes=False):
    """Consume the original group handoff without taking cleanup ownership.

    Inode and kernel masks are verified at this instant; the supervisor's
    private channel does not prove an external writer is fenced. This helper
    can be used by a future StageController functional-only mode, but does not
    override its scored-entry guard, create groups, or grant GO authority.
    """
    handoff = channel.handoff()
    if not isinstance(handoff, dict) or handoff.get("runtime_admission") is not False:
        raise ValueError("supervisor group handoff is unavailable")
    groups = handoff.get("games")
    if (type(groups) is not dict or len(groups) != len(slots) or
            set(groups) != {slot.id for slot in slots}):
        raise ValueError("supervisor groups differ from frozen slots")
    controller = handoff.get("controller")
    controller_live = placement.verify_cgroup_live(controller)
    if str(os.getpid()) not in (Path(controller["path"]) / "cgroup.procs").read_text().split():
        raise ValueError("controller is not in its supervisor-owned group")
    if set(os.sched_getaffinity(0)) != set(controller["cpus"]):
        raise ValueError("controller affinity differs from supervisor handoff")
    for slot in slots:
        live = placement.verify_cgroup_live(groups[slot.id])
        if live["cpus"] != sorted(slot.cpus) or live["memory_nodes"] != sorted(slot.memory_nodes):
            raise ValueError("live supervisor group masks differ from the frozen slot")
        if Path(groups[slot.id]["path"]).parent != Path(controller["path"]).parent:
            raise ValueError("controller and game groups do not share their supervisor parent")
        # This existing diagnostic keeps the controller on every game node.
        # A narrower controller needs a separately verified ancestor-envelope
        # handoff; do not spawn a runner and rely on its later failure.
        if not set(slot.memory_nodes) <= set(controller_live["memory_nodes"]):
            raise ValueError("controller memory nodes must include every game node before placement")
    if include_controller_nodes:
        return groups, list(controller_live["memory_nodes"])
    return groups


def ready_probe(*, profile, entries, runner, runner_sha256, opening, opening_sha256, saved_ancestor_cpus,
                channel, wall_seconds=180):
    """Observe actual initialized engines, then refuse every GO.

    Each entry supplies ``slot`` (a frozen Slot), ``engines`` (two distinct
    dictionaries: id, path, whole_sha256, native_sha256 and tt_bytes), ``opening_start``, and a new
    absolute ``out`` directory outside Git. Group identity is accepted only
    through the supervisor's private channel and checked against the frozen
    slot and the live kernel before launch. The observer independently checks
    actual process identities and cgroup membership. The handoff is not an
    authenticated budget authority or a memory admission.
    """
    count = {"test-p16": 11, "test-p192": 1}.get(profile)
    if count is None or not isinstance(entries, list) or len(entries) != count:
        raise ValueError("the full named P16 or P192 cohort is required")
    if _file_sha(Path(runner)) != runner_sha256:
        raise ValueError("Fastchess image differs from the frozen digest")
    opening = run.protected_input(Path(opening))
    if _file_sha(opening) != opening_sha256:
        raise ValueError("opening PGN differs from its frozen digest")
    slots = [entry.get("slot") for entry in entries]
    if any(not isinstance(slot, topology.Slot) for slot in slots) or len({slot.id for slot in slots}) != count:
        raise ValueError("distinct frozen slots are required")
    groups, saved_ancestor_nodes = accept_supervisor_groups(slots=slots, channel=channel,
                                                            include_controller_nodes=True)
    jobs, specs, ready = [], {}, {}
    for entry in entries:
        slot = entry["slot"]
        if (slot.workers != (16 if profile == "test-p16" else 192) or slot.policy != "default"
                or len(slot.cpus) != slot.workers or not re.fullmatch(r"[A-Za-z0-9_.-]+", slot.id)):
            raise ValueError("frozen slot differs from the profile")
        group = groups[slot.id]
        live = placement.verify_cgroup_live(group)
        if live["cpus"] != sorted(slot.cpus) or live["memory_nodes"] != sorted(slot.memory_nodes):
            raise ValueError("live supervisor group masks differ from the frozen slot")
        engines = entry.get("engines")
        if not isinstance(engines, list) or len(engines) != 2 or engines[0]["id"] == engines[1]["id"]:
            raise ValueError("two distinct frozen engine images are required")
        for engine in engines:
            if (set(engine) != {"id", "path", "whole_sha256", "native_sha256", "tt_bytes"} or
                    _file_sha(Path(engine["path"])) != engine["whole_sha256"]):
                raise ValueError("engine image differs from the frozen digest")
        out = run.protected_input(Path(entry["out"]))
        resolved = run.protected_input(out.resolve())
        if (not out.is_absolute() or out.exists() or out.is_symlink() or
                any((p / ".git").exists() for p in (resolved, *resolved.parents))):
            raise ValueError("a new external output directory is required")
        out.mkdir(parents=True)
        slot_file, receipt_file = out / "slot.json", out / "placement.json"
        slot_file.write_text(json.dumps({"slot": slot.to_record(), "cgroup": group,
                                         "saved_ancestor_cpus": list(saved_ancestor_cpus),
                                         "saved_ancestor_nodes": saved_ancestor_nodes}, sort_keys=True), encoding="utf-8")
        commands = [fastchess.EngineCommand(engine["id"], (str(Path(engine["path"])),)) for engine in engines]
        argv = fastchess.single_game_argv(Path(runner), *commands, opening_pgn=opening,
                                         opening_start=entry["opening_start"], out=out)
        placement_path = Path(placement.__file__).resolve()
        executable = str(Path(sys.executable).resolve())
        job = wave.WaveJob(slot.id, (executable, str(placement_path), "--slot", str(slot_file),
                                    "--record", str(receipt_file), "--", *argv),
                           {"TZ": "UTC", "LANG": "C.UTF-8"}, {"slot": slot.id}, out)
        jobs.append(job)
        specs[slot.id] = (slot, group, engines, receipt_file)

    def event(kind, job, observation):
        if kind != "ready":
            return
        slot, group, engines, receipt_file = specs[job.identity]
        receipt = _read_receipt(receipt_file)
        run.verify_preexec_placement(receipt, pid=observation["pid"], slot=slot, cgroup=group)
        placement.verify_cgroup_live(group)
        evidence = placement.observe_game_engines(observation["pid"],
                    [engine["native_sha256"] for engine in engines], slot.cpus,
                    expected_start_ticks=observation["start_ticks"])
        remaining = list(evidence["engines"])
        ordered = []
        for engine in engines:
            matching = next((row for row in remaining if row["native_sha256"] == engine["native_sha256"]), None)
            if matching is None:
                raise ValueError("observed engine identity does not match frozen colour order")
            ordered.append(matching["pid"])
            remaining.remove(matching)
        ready[job.identity] = {"runner": observation["pid"], "engines": ordered}

    sampled = False
    def before_release():
        nonlocal sampled
        if set(ready) != set(specs):
            raise ValueError("the full cohort is not READY")
        for _, group, _, _ in specs.values():
            placement.verify_cgroup_live(group)
        sampled = channel.active(ready) is True
        return sampled

    executor = wave.WaveExecutor()
    observations = executor.run_wave(jobs, wall_seconds=wall_seconds, release_callback=before_release,
                                     on_event=event, authorize_go=lambda _job, _snapshot: False,
                                     observe_transport=lambda _job, _snapshot: None)
    _require_unreleased(observations, specs)
    if not sampled or any(not run.physically_settled(row) for row in observations):
        raise ProbeFailure("probe did not observe and physically settle the complete cohort", observations)
    settled = channel.settled() is True
    return {"format": "rove4k-pre-go-peak-probe-v1", "sampled": sampled, "settled": settled,
            "games_started": 0, "go_authority": False, "runtime_admission": False,
            "scored_qualification": False, "representative_search_workload_verified": False,
            "all_tt_resident_verified": False, "observations": observations}


def _persist_report(report_path, report):
    """Persist an external diagnostic report before journalling its digest."""
    raw = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                     allow_nan=False).encode("ascii")
    with report_path.open("xb") as output:
        output.write(raw)
        output.flush()
        os.fsync(output.fileno())
    if os.name == "posix":
        directory_fd = os.open(report_path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    return hashlib.sha256(raw).hexdigest()


def observe_and_record(*, observe_args, expected_context, report_path, append):
    """Persist and journal a supervisor's report as diagnostic evidence only.

    The no-argument expected_context callable supplies an independently frozen
    context and current monotonic time after observation; it must never read the
    report. On failure after process launch the handle
    remains attached to SupervisorFailure for physical reconciliation.
    """
    report_path = run.protected_input(Path(report_path))
    resolved = run.protected_input(report_path.resolve())
    if report_path.exists() or report_path.is_symlink() or any((p / ".git").exists() for p in resolved.parents):
        raise ValueError("a new external report path is required")
    if not callable(expected_context):
        raise TypeError("an independent expected-context provider is required")
    try:
        report, process = peak_supervisor.observe(**observe_args)
    except peak_supervisor.SupervisorFailure as failure:
        # A runner may OOM before it sends READY.  Preserve best-effort
        # memory.events and process ownership even when no successful peak
        # receipt exists.  A failed persistence never hides the original
        # exception or its child handle.
        if isinstance(failure.evidence, dict):
            try:
                evidence_sha = _persist_report(report_path, failure.evidence)
                failure.evidence_path = str(report_path)
                failure.evidence_sha256 = evidence_sha
                append("campaign.memory_peak_diagnostic_failed", {
                    "report_path": str(report_path), "report_bytes_sha256": evidence_sha,
                    "oom_observed": failure.evidence.get("oom_observed") is True,
                    "all_groups_read": failure.evidence.get("all_groups_read") is True,
                    "runtime_admission": False, "scored_qualification": False})
            except BaseException as recording_error:
                failure.evidence_persistence_error = repr(recording_error)
        raise
    try:
        expected = expected_context()
        peak_receipt.inspect_diagnostic(report, expected=expected)
        raw_sha256 = _persist_report(report_path, report)
        def append_with_evidence(event, data):
            append(event, {**data, "report_path": str(report_path), "report_bytes_sha256": raw_sha256})
        receipt = peak_receipt.record_diagnostic(append_with_evidence, report, expected=expected)
        return receipt, process
    except BaseException as error:
        failure = peak_supervisor.SupervisorFailure("diagnostic receipt persistence failed: " + str(error), process)
        failure.report = report
        raise failure from error


def load_controller_manifest(path, expected_sha256):
    """Load an independently pinned, bounded controller input, not an admission."""
    path = run.protected_input(Path(path))
    run.protected_input(path.resolve(strict=True))
    if not isinstance(expected_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise ValueError("a lowercase controller manifest SHA-256 is required")
    if not hasattr(os, "O_NOFOLLOW"):
        raise RuntimeError("Linux no-follow manifest opening is required")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as source:
        before = os.fstat(source.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > 131072:
            raise ValueError("controller manifest is not a bounded regular file")
        raw = source.read(131073)
        after = os.fstat(source.fileno())
    current = path.lstat()
    if (len(raw) > 131072 or
            (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) !=
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns) or
            (current.st_dev, current.st_ino) != (before.st_dev, before.st_ino) or
            hashlib.sha256(raw).hexdigest() != expected_sha256):
        raise ValueError("controller manifest changed or differs from its pinned digest")
    manifest = json.loads(raw)
    if type(manifest) is not dict or set(manifest) != {
            "format", "profile", "entries", "runner", "runner_sha256", "opening", "opening_sha256", "topology",
            "saved_ancestor_cpus", "wall_seconds"} or manifest["format"] != "rove4k-pre-go-controller-v2":
        raise ValueError("invalid controller manifest")
    entries = manifest["entries"]
    if type(entries) is not list or type(manifest["topology"]) is not dict:
        raise ValueError("controller entries must be a list")
    decoded = []
    for entry in entries:
        if type(entry) is not dict or set(entry) != {"slot", "engines", "opening_start", "out"}:
            raise ValueError("invalid controller entry")
        slot = entry["slot"]
        if type(slot) is not dict or set(slot) != {"id", "cpus", "physical_cores", "memory_nodes", "workers", "smt", "policy"}:
            raise ValueError("invalid controller slot")
        if (type(slot["cpus"]) is not list or type(slot["memory_nodes"]) is not list or
                type(slot["physical_cores"]) is not list or
                any(type(row) is not list or len(row) != 2 or any(type(x) is not int or x < 0 for x in row)
                    for row in slot["physical_cores"]) or
                any(type(x) is not int or x < 0 for x in slot["cpus"] + slot["memory_nodes"]) or
                type(slot["workers"]) is not int or type(slot["smt"]) is not bool):
            raise ValueError("invalid controller slot types")
        decoded.append({**entry, "slot": topology.Slot(slot["id"], tuple(slot["cpus"]),
                         tuple(tuple(row) for row in slot["physical_cores"]), tuple(slot["memory_nodes"]),
                         slot["workers"], slot["smt"], slot["policy"])})
    cpus, seconds = manifest["saved_ancestor_cpus"], manifest["wall_seconds"]
    if (type(cpus) is not list or not cpus or any(type(x) is not int or x < 0 for x in cpus) or
            len(set(cpus)) != len(cpus) or type(seconds) not in (int, float) or not 0 < seconds <= 180):
        raise ValueError("invalid ancestor CPU envelope or probe deadline")
    return {**manifest, "entries": decoded}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run a supervisor-owned pre-GO diagnostic cohort; never start games")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--manifest-sha256", required=True)
    args = parser.parse_args(argv)
    manifest = load_controller_manifest(args.manifest, args.manifest_sha256)
    channel = peak_supervisor.ControllerChannel()
    result = ready_probe(profile=manifest["profile"], entries=manifest["entries"], runner=manifest["runner"],
                         runner_sha256=manifest["runner_sha256"], opening=manifest["opening"],
                         opening_sha256=manifest["opening_sha256"],
                         saved_ancestor_cpus=manifest["saved_ancestor_cpus"], channel=channel,
                         wall_seconds=manifest["wall_seconds"])
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
