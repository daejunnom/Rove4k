"""Owned P16/P192 Rove lifecycle observation, without qualification authority.

Each session is a real fresh owned process in the caller's delegated cgroup.
The report is diagnostic only: four lifecycles do not establish the TT address
or the identity of all declared workers, nor authorize a score or release.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from types import SimpleNamespace

sys.dont_write_bytecode = True
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from . import functional_uci_probe as functional
except ImportError:
    import functional_uci_probe as functional

peer = functional.peer_runtime
placement = functional.placement
memory = functional.memory_observation
topology = functional.topology
diagnostic = functional.diagnostic_candidates
LABELS = ("cold", "warm", "active-quit", "active-eof")


def _group_identity(group):
    # observed_at_utc is intentionally not an identity field: each live
    # verification takes a fresh timestamp.
    return {key: group[key] for key in ("path", "device", "inode", "cpus", "memory_nodes", "memory_max")}


def _pins(candidate, artifact):
    diagnostic._pinned_file(candidate["source"])
    diagnostic._pinned_file(candidate["native"], expected=artifact.native_sha256)
    diagnostic._pinned_file({"path": str(candidate["whole"]), "bytes": artifact.whole_bytes,
                             "sha256": artifact.sha256}, expected=artifact.sha256)


def _candidate_still_matches(path, digest, profile, candidate):
    rows, observed = diagnostic.read_candidates(path, digest, profile, allow_single=True)
    artifact = candidate["artifact"]
    matches = [row for row in rows if row["artifact"].id == artifact.id]
    if (observed != digest or len(matches) != 1 or matches[0]["artifact"].identity() != artifact.identity() or
            any(matches[0][key] != candidate[key] for key in ("source", "native", "whole", "evidence"))):
        raise ValueError("pinned candidate set or source evidence changed during lifecycle observation")


def _boot():
    value = Path("/proc/sys/kernel/random/boot_id").read_text(encoding="ascii").strip()
    if not re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", value):
        raise ValueError("kernel boot identity unavailable or malformed")
    return value


def _current_owner(identity, group_path):
    if placement._process_identity(identity["pid"]) != identity:
        raise ValueError("original process identity changed before terminal request")
    if str(identity["pid"]) not in memory._file(group_path / "cgroup.procs").splitlines():
        raise ValueError("diagnostic leader left its original cgroup")


def _verify_environment(profile, slot, cgroup, saved_cpus, saved_nodes):
    workers = {"test-p16": 16, "test-p192": 192}[profile]
    if (type(slot) is not dict or slot.get("workers") != workers or
            type(slot.get("cpus")) is not list or len(slot["cpus"]) != workers or
            any(type(x) is not int or x < 0 for x in slot["cpus"]) or
            slot["cpus"] != sorted(set(slot["cpus"])) or
            type(slot.get("memory_nodes")) is not list or not slot["memory_nodes"] or
            any(type(x) is not int or x < 0 for x in slot["memory_nodes"]) or
            slot["memory_nodes"] != sorted(set(slot["memory_nodes"])) or
            (profile == "test-p16" and len(slot["memory_nodes"]) != 1) or
            slot.get("policy") != "default"):
        raise ValueError("slot does not match the Rove diagnostic profile")
    if (type(saved_cpus) is not list or any(type(x) is not int or x < 0 for x in saved_cpus) or
            len(saved_cpus) != len(set(saved_cpus)) or not set(slot["cpus"]) <= set(saved_cpus)):
        raise ValueError("original CPU envelope does not contain the slot")
    if saved_nodes is not None and (type(saved_nodes) is not list or not saved_nodes or
            any(type(x) is not int or x < 0 for x in saved_nodes) or
            len(saved_nodes) != len(set(saved_nodes)) or
            not set(slot["memory_nodes"]) <= set(saved_nodes)):
        raise ValueError("original NUMA envelope does not contain the slot")
    if type(cgroup) is not dict or type(cgroup.get("path")) is not str:
        raise ValueError("original cgroup identity is required")
    path, root = Path(cgroup["path"]), Path("/sys/fs/cgroup")
    if (not path.is_absolute() or ".." in path.parts or not path.is_relative_to(root) or path == root or
            any(item.is_symlink() for item in (path, *path.parents))):
        raise ValueError("diagnostic cgroup must be a visible cgroup2 descendant")
    functional.peak_probe_session._require_delegated_root(path)
    actual = placement.verify_cgroup_live(cgroup)
    if actual["cpus"] != slot["cpus"] or actual["memory_nodes"] != slot["memory_nodes"]:
        raise ValueError("cgroup masks differ from selected slot")
    functional.peak_capacity._require_empty(path)
    snapshot = topology.Topology.snapshot_target(path, device=actual["device"], inode=actual["inode"])
    if profile == "test-p16":
        slots = topology.plan_slots(snapshot, 8, 16, reserve_physical=0, max_slots=1, policy="default")
        if len(slots) != 1:
            raise ValueError("P16 requires a full SMT slot")
        planned = slots[0]
        by_id = {cpu.id: cpu for cpu in snapshot.cpus}
        for core in planned.physical_cores:
            members = {cpu for cpu in planned.cpus if by_id[cpu].physical == core}
            if len(members) != 2 or any(set(by_id[cpu].siblings) != members for cpu in members):
                raise ValueError("P16 requires mutually observed SMT siblings")
    else:
        planned = topology.plan_p192_slot(snapshot, policy="default")
    planned = json.loads(json.dumps(planned.to_record()))
    if any(slot.get(key) != planned[key] for key in ("cpus", "physical_cores", "memory_nodes", "workers", "smt", "policy")):
        raise ValueError("live physical cores, SMT siblings or NUMA nodes differ from frozen slot")
    return path, actual, snapshot.to_record()


def _startup(owned, started):
    remaining = 60 - (time.monotonic() - started)
    if remaining <= 0:
        raise TimeoutError("aggregate startup exceeded 60 seconds")
    owned.send(b"uci\nisready\n")
    owned.stdout.until(lambda data: b"uciok" in data.splitlines() and b"readyok" in data.splitlines(),
                       owned.budget, seconds=remaining)
    lines = owned.stdout.bytes().splitlines()
    if lines.count(b"uciok") != 1 or lines.count(b"readyok") != 1 or any(
            line.startswith(b"bestmove ") for line in lines):
        raise ValueError("startup protocol acknowledgements or bestmove differ")
    elapsed = time.monotonic() - started
    if elapsed > 60:
        raise TimeoutError("aggregate startup exceeded 60 seconds")
    return elapsed


def _b_has_no_static_symtab(owned, identity, cgroup, native_sha256, boot, group):
    """Prove only SHT_SYMTAB absence in this pinned, still-owned image."""
    observer = functional.rove_b_tt_observe
    pid = identity["pid"]
    _current_owner(identity, Path(cgroup["path"]))
    group_keys = ("device", "inode", "cpus", "memory_nodes", "memory_max")
    before_group = observer._group(pid, cgroup)
    if observer._boot() != boot or before_group != {key: group[key] for key in group_keys}:
        raise ValueError("B stripped-image boot or cgroup changed")
    image, image_identity = observer._image(pid, native_sha256)
    elf = peer.Elf64(image)
    for section in elf.sections:
        if section[1] not in (0, 8):  # SHT_NULL and SHT_NOBITS have no file payload.
            elf.segment(section[4], section[5])
    if any(section[1] == 2 for section in elf.sections):  # SHT_SYMTAB
        return False
    image_after, identity_after = observer._image(pid, native_sha256)
    _current_owner(identity, Path(cgroup["path"]))
    if (owned.exited() or image != image_after or image_identity != identity_after or
            observer._group(pid, cgroup) != before_group or observer._boot() != boot):
        raise ValueError("B stripped-image owner, image, boot or cgroup changed")
    return True


def _observe_b(owned, owner, candidate, artifact, identity, cgroup, profile, slot, boot, group):
    """Observe a B pointer candidate while this exact owned process is alive."""
    if owned not in owner.OWNED:
        raise ValueError("B observation requires the original registered owner")
    try:
        observed = functional.rove_b_tt_observe.observe_owned_b(
            owned, native_sha256=artifact.native_sha256, expected_identity=identity,
            cgroup=cgroup, profile=profile, allowed_nodes=slot["memory_nodes"])
    except functional.rove_b_tt_observe.ObservationUnavailable as error:
        return {"state": "unavailable", "error_type": type(error).__name__, "detail": str(error)}
    except ValueError as error:
        if (str(error) != "actual TT pointer has no unique ELF object symbol" or
                not _b_has_no_static_symtab(owned, identity, cgroup, artifact.native_sha256, boot, group)):
            raise
        return {"state": "unavailable", "error_type": "StaticSymbolTableAbsent",
                "detail": "pinned live ELF has no SHT_SYMTAB; B symbol candidate cannot be observed"}
    group_keys = ("device", "inode", "cpus", "memory_nodes", "memory_max")
    if (observed["owner"] != identity or observed["boot_id"] != boot or
            observed["cgroup"] != {key: group[key] for key in group_keys} or
            observed["native_sha256"] != artifact.native_sha256):
        raise ValueError("B observation differs from this session's owner, boot, cgroup or native pin")
    if not observed.get("claims") or any(value is not False for value in observed["claims"].values()):
        raise ValueError("B candidate observation must not assert unproven claims")
    static = candidate["evidence"].get("b_static_correlation")
    if static is not None:
        functional._bind_b_static_live(observed, static, candidate["source"]["sha256"])
    return {"state": "observed", "observation": observed}


def _active_termination(owned, scope, cpus, label, *, expected_identity, group_path,
                        native_sha256, maximum=15, before_terminal=None, expected_workers=None):
    """Sample task identity and CPU activity in the original active search."""
    if label not in ("active-quit", "active-eof"):
        raise ValueError("active termination label required")
    pid = owned.process.pid
    before = scope.task_snapshot(pid)
    baseline = {}
    for tid in before:
        if tid == pid:
            continue
        try:
            baseline[tid] = peer._worker_evidence(pid, tid)
        except (FileNotFoundError, ProcessLookupError):
            continue
    prior_best = len(peer._best_lines(owned))
    owned.send(b"position startpos\ngo wtime 60000 btime 60000 winc 0 binc 0\n")
    deadline = time.monotonic() + owned.budget.left(maximum)
    evidence, samples, current_ids = None, {}, set()
    while True:
        if owned.exited() or len(peer._best_lines(owned)) != prior_best:
            raise ValueError("search completed before active termination")
        current_ids = set(scope.task_snapshot(pid)) - {pid}
        if expected_workers is not None and (len(current_ids) > expected_workers or
                len(set(samples) | current_ids) > expected_workers):
            raise ValueError("more observed search threads than declared workers")
        for tid in sorted(current_ids):
            if tid == pid:
                continue
            try:
                sample = peer._worker_evidence(pid, tid)
            except (FileNotFoundError, ProcessLookupError):
                continue
            if sample["cpus"] != sorted(cpus):
                raise ValueError("observed search thread escaped CPU slot")
            initial = before.get(tid, {}).get("cpu_ticks", 0)
            previous = samples.get(tid)
            base = baseline.get(tid)
            if base is not None and base["start_ticks"] != sample["start_ticks"]:
                raise ValueError("thread TID was reused after pre-search observation")
            if previous is not None:
                if (previous["start_ticks"] != sample["start_ticks"] or
                        sample["cpu_ticks_first"] < previous["cpu_ticks_last"]):
                    raise ValueError("thread identity changed or CPU ticks regressed")
                previous["cpu_ticks_last"] = sample["cpu_ticks_last"]
                previous["samples"] += 1
            else:
                samples[tid] = {**sample, "samples": 1,
                                "pre_go": base, "cpu_ticks_before_go": initial}
            if evidence is None and sample["cpu_ticks_last"] > initial:
                evidence = {**sample, "cpu_ticks_before_go": initial}
        all_active = (expected_workers is not None and len(current_ids) == expected_workers and
                      set(samples) == current_ids and all(
                          item["samples"] >= 2 and item["cpu_ticks_last"] > item["cpu_ticks_first"]
                          for item in samples.values()))
        if evidence is not None and (expected_workers is None or all_active or time.monotonic() >= deadline):
            break
        if time.monotonic() >= deadline:
            if evidence is None:
                raise TimeoutError("no nonleader CPU progress before active termination")
            break
        time.sleep(.01)
    if owned.exited() or len(peer._best_lines(owned)) != prior_best:
        raise ValueError("search completed before active termination")
    _current_owner(expected_identity, group_path)
    image = scope.image_snapshot(pid, native_sha256)
    _current_owner(expected_identity, group_path)
    if owned.exited() or len(peer._best_lines(owned)) != prior_best:
        raise ValueError("search completed before active termination")
    observation = before_terminal() if before_terminal is not None else None
    _current_owner(expected_identity, group_path)
    if owned.exited() or len(peer._best_lines(owned)) != prior_best:
        raise ValueError("search completed before active termination")
    if all_active:
        final_ids = set(scope.task_snapshot(pid)) - {pid}
        if final_ids != current_ids:
            all_active = False
        else:
            for tid in sorted(final_ids):
                try:
                    final = peer._worker_evidence(pid, tid)
                except (FileNotFoundError, ProcessLookupError):
                    all_active = False
                    break
                previous = samples[tid]
                if (final["start_ticks"] != previous["start_ticks"] or
                        final["cpu_ticks_first"] < previous["cpu_ticks_last"] or
                        final["cpus"] != sorted(cpus)):
                    raise ValueError("thread identity, affinity or CPU ticks changed before termination")
                previous["cpu_ticks_last"] = final["cpu_ticks_last"]
                previous["samples"] += 1
    image = scope.image_snapshot(pid, native_sha256)
    _current_owner(expected_identity, group_path)
    if owned.exited() or len(peer._best_lines(owned)) != prior_best:
        raise ValueError("search completed before active termination")
    if label == "active-eof":
        owned.close_input()
    else:
        owned.send(b"quit\n")
    return {"requested": "eof" if label == "active-eof" else "quit",
            "observed_progress_before_request": evidence,
            "active_thread_samples": [samples[tid] for tid in sorted(samples)],
            "all_declared_thread_activity_observed": bool(all_active),
            "thread_activity_status": ("not-requested" if expected_workers is None else
                "observed" if all_active else "incomplete"),
            "thread_activity_incomplete_reason": (None if all_active or expected_workers is None else
                "declared count, repeated positive activity, or final live membership not observed"),
            "pre_terminal_image": image,
            "b_symbol_candidate": observation,
            "complete_worker_set_proven": False}


@peer.owned_signals
def collect(*, candidate_path, candidate_sha256, artifact_id, profile, slot, cgroup,
            saved_ancestor_cpus, out, saved_ancestor_nodes=None, wall_seconds=180):
    if sys.platform != "linux":
        raise RuntimeError("owned Rove lifecycle observation requires Linux")
    if profile not in ("test-p16", "test-p192") or type(wall_seconds) is not int or not 90 <= wall_seconds <= 300:
        raise ValueError("bounded P16/P192 lifecycle observation required")
    rows, candidate_digest = diagnostic.read_candidates(candidate_path, candidate_sha256, profile, allow_single=True)
    matches = [row for row in rows if row["artifact"].id == artifact_id]
    if len(matches) != 1 or matches[0]["artifact"].family not in ("A", "B", "C", "E", "F"):
        raise ValueError("one exact pinned Rove candidate is required")
    candidate, artifact = matches[0], matches[0]["artifact"]
    slot = json.loads(json.dumps(slot.to_record() if hasattr(slot, "to_record") else slot))
    group_path, original_group, original_topology = _verify_environment(
        profile, slot, cgroup, saved_ancestor_cpus, saved_ancestor_nodes)
    overhead = max(768 << 20, artifact.workers * (16 << 20)) + (256 << 20)
    required = artifact.tt_bytes + overhead
    if original_group["memory_max"] < required:
        raise ValueError("declared cgroup memory.max is below TT and diagnostic overhead")
    boot = _boot()
    output = diagnostic._safe_output_path(out)
    output.mkdir(mode=0o700)
    scope, owner, oracle = diagnostic._profile_verifier().support_modules()
    started_monotonic = time.monotonic()
    report = {"format": "rove4k-owned-lifecycle-v1", "profile": profile,
              "artifact": artifact.identity(), "candidate_set_sha256": candidate_digest,
              "source_sha256": candidate["source"]["sha256"], "boot_id": boot,
              "slot": slot, "cgroup": original_group, "topology": original_topology,
              "sessions": [], "complete": False, "current_availability_enforced": False,
              "per_session_wall_seconds": wall_seconds, "started_monotonic": started_monotonic,
              "performance_eligible": False,
              "declared_overhead_bytes": overhead, "declared_required_bytes": required,
              "claims": {"source_provenance_authenticated": False, "complete_worker_set": False,
                         "tt_address_provenance": False, "tt_only_residency": False,
                         "loaded_driver_identity_proven": False, "executable_continuity_proven": False,
                         "smt_qualification": False, "score_authorized": False,
                         "release_authorized": False},
              "limitations": ["cache temperature is not established by cold/warm labels",
                  "TT address meaning and complete worker identity remain unproved",
                  "driver source closure and continuous executable identity are not proven",
                  "cooperative GC coverage is unobserved; timing is not performance or strength evidence",
                  "cgroup ownership does not exclude external writers or hidden ancestors"]}
    failure = None
    seen_processes = set()
    try:
        for label in LABELS:
            _candidate_still_matches(candidate_path, candidate_digest, profile, candidate)
            _pins(candidate, artifact)
            path, group, observed = _verify_environment(profile, slot, cgroup, saved_ancestor_cpus, saved_ancestor_nodes)
            if (path != group_path or _group_identity(group) != _group_identity(original_group) or
                    observed != original_topology or _boot() != boot):
                raise ValueError("boot, topology or cgroup changed between sessions")
            before = functional._events(group_path)
            directory = output / label
            directory.mkdir(mode=0o700)
            own_dir, tmp = directory / "owned", directory / "tmp"
            own_dir.mkdir(mode=0o700)
            tmp.mkdir(mode=0o700)
            launcher, preexec = directory / "launcher", directory / "placement.json"
            owner_file, release = directory / "owner.json", directory / "release"
            functional._launcher(launcher, whole=candidate["whole"], whole_sha256=artifact.sha256, slot=slot,
                cgroup=cgroup, saved_cpus=saved_ancestor_cpus, saved_nodes=saved_ancestor_nodes,
                record=preexec, owner_file=owner_file, release_file=release, temporary=tmp)
            row = {"label": label, "complete": False, "events_before": before}
            report["sessions"].append(row)
            owned = None
            try:
                started = time.monotonic()
                owned = peer.construct_owned(owner, launcher, own_dir, owner.Budget(wall_seconds))
                identity = placement._process_identity(owned.process.pid)
                if not identity["alive"] or identity["pid"] != identity["pgid"] or identity["pid"] != identity["session"]:
                    raise ValueError("diagnostic leader does not own its original process group")
                process_key = (identity["pid"], identity["start_ticks"])
                if process_key in seen_processes:
                    raise ValueError("lifecycle sessions reused an observed process identity")
                seen_processes.add(process_key)
                row["owner_identity"] = identity
                raw = (json.dumps(identity, sort_keys=True, separators=(",", ":")) + "\n").encode()
                functional._write_exclusive(owner_file, raw)
                functional._write_exclusive(release, hashlib.sha256(raw).hexdigest().encode("ascii"))
                deadline = time.monotonic() + owned.budget.left(30)
                while not preexec.exists():
                    if owned.exited() or time.monotonic() >= deadline:
                        raise TimeoutError("owned pre-exec placement did not complete")
                    time.sleep(.01)
                reader = diagnostic._profile_verifier().input_reader()
                row["pre_exec"] = json.loads(reader.read_regular(preexec, limit=65536))
                view = SimpleNamespace(cpus=tuple(slot["cpus"]), memory_nodes=tuple(slot["memory_nodes"]), policy=slot["policy"])
                row["pre_exec_verified"] = diagnostic.run.verify_preexec_placement(
                    row["pre_exec"], pid=identity["pid"], slot=view, cgroup=cgroup)
                _current_owner(identity, group_path)
                row["startup_seconds"] = _startup(owned, started)
                _current_owner(identity, group_path)
                row["startup_image"] = scope.image_snapshot(identity["pid"], artifact.native_sha256)
                _current_owner(identity, group_path)
                observe_b = (lambda: _observe_b(owned, owner, candidate, artifact, identity,
                    cgroup, profile, slot, boot, original_group)) if artifact.family == "B" else None
                if label in ("cold", "warm"):
                    row["search"] = peer._search(owned, scope, oracle, [], label,
                        workers=artifact.workers, cpus=slot["cpus"], capture_smt=True)
                    _current_owner(identity, group_path)
                    if observe_b is not None:
                        row["b_symbol_candidate"] = observe_b()
                        _current_owner(identity, group_path)
                    row["pre_terminal_image"] = scope.image_snapshot(identity["pid"], artifact.native_sha256)
                    _current_owner(identity, group_path)
                    owned.send(b"quit\n")
                    owned.close_input()
                else:
                    row["active_termination"] = _active_termination(
                        owned, scope, slot["cpus"], label, expected_identity=identity, group_path=group_path,
                        native_sha256=artifact.native_sha256, before_terminal=observe_b,
                        expected_workers=artifact.workers)
                    if observe_b is not None:
                        row["b_symbol_candidate"] = row["active_termination"].pop("b_symbol_candidate")
                row["finish"] = peer._finish_peer(owned, seconds=20)
                if label.startswith("active-"):
                    closing = peer._best_lines(owned)
                    if len(closing) > 1:
                        raise ValueError("active terminal request produced duplicate bestmoves")
                    row["closing_bestmove"] = (peer.checked_best(closing[0], oracle.Board.from_fen())
                                               if closing else None)
                row["cleanup"] = owned.cleanup()
                if (row["cleanup"].get("owned_group_absent") is not True or
                        row["cleanup"].get("readers_joined") is not True or
                        row["cleanup"].get("forced_cleanup") or row["cleanup"].get("errors")):
                    raise ValueError("owned session did not settle normally")
                owned = None
            finally:
                if owned is not None:
                    row["cleanup"] = owned.cleanup()
                for remaining in tuple(owner.OWNED):
                    report.setdefault("recovered_constructor_handles", []).append(remaining.cleanup())
                row["events_after"] = functional._events(group_path)
                if any(row["events_after"][key] < value for key, value in before.items()):
                    raise ValueError("cgroup memory event counters regressed")
                if any(row["events_after"][key] > before[key] for key in ("oom", "oom_kill")):
                    raise ValueError("cgroup observed an OOM event")
                events = memory._file(group_path / "cgroup.events")
                row["cgroup_populated_zero"] = events.splitlines().count("populated 0") == 1
                if not row["cgroup_populated_zero"]:
                    raise ValueError("owned cgroup is still populated")
                _pins(candidate, artifact)
                _candidate_still_matches(candidate_path, candidate_digest, profile, candidate)
                _path, after_group, after_topology = _verify_environment(
                    profile, slot, cgroup, saved_ancestor_cpus, saved_ancestor_nodes)
                if (_group_identity(after_group) != _group_identity(original_group) or
                        after_topology != original_topology or _boot() != boot):
                    raise ValueError("boot, topology or cgroup changed during session")
            row["complete"] = True
        report["complete"] = len(report["sessions"]) == 4 and all(row["complete"] for row in report["sessions"])
    except BaseException as error:
        failure = error
        report["failure"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        report["finished_monotonic"] = time.monotonic()
        report["elapsed_seconds"] = report["finished_monotonic"] - started_monotonic
        functional._write_exclusive(output / "lifecycle.json",
            (json.dumps(report, sort_keys=True, indent=2) + "\n").encode())
    if failure is not None or not report["complete"]:
        raise functional.FunctionalProbeFailure("owned lifecycle diagnostic failed; see retained report", report) from failure
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--candidates-sha256", required=True)
    parser.add_argument("--profile", choices=("test-p16", "test-p192"), required=True)
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--placement", type=Path, required=True)
    parser.add_argument("--placement-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--wall-seconds", type=int, default=180)
    args = parser.parse_args(argv)
    record, _ = diagnostic.run.json_input(diagnostic._safe_input_path(args.placement), args.placement_sha256)
    if type(record) is not dict or set(record) not in ({"slot", "cgroup", "saved_ancestor_cpus"},
            {"slot", "cgroup", "saved_ancestor_cpus", "saved_ancestor_nodes"}):
        raise ValueError("an exact pinned single-slot placement record is required")
    result = collect(candidate_path=args.candidates, candidate_sha256=args.candidates_sha256,
        artifact_id=args.artifact, profile=args.profile, slot=record["slot"], cgroup=record["cgroup"],
        saved_ancestor_cpus=record["saved_ancestor_cpus"], saved_ancestor_nodes=record.get("saved_ancestor_nodes"),
        out=args.out, wall_seconds=args.wall_seconds)
    print(json.dumps({"report": str(args.out / "lifecycle.json"), "complete": result["complete"],
                      "smt_qualification": False, "score_authorized": False}, sort_keys=True))


if __name__ == "__main__":
    main()
