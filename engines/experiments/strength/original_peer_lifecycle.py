"""Run pinned, unchanged upstream peers in an owned, non-scoring TEST session.

Source, native, placement records and the report remain outside Git.  The two
profiles use the upstream UCI options, not rewritten source or a 4 KiB gate.
The report is an observation, not authority to score a game or release.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace

sys.dont_write_bytecode = True
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from . import original_peer_build as original, original_peer_uci as uci
    from . import rove_owned_lifecycle as lifecycle
except ImportError:
    import original_peer_build as original
    import original_peer_uci as uci
    import rove_owned_lifecycle as lifecycle

functional = lifecycle.functional
peer = lifecycle.peer
placement = lifecycle.placement
memory = lifecycle.memory
diagnostic = lifecycle.diagnostic
LABELS = lifecycle.LABELS


def _recheck_environment(group_path, cgroup, identity_group, snapshot, boot):
    """Recheck a previously admitted empty cgroup without resetting its peak."""
    current = placement.verify_cgroup_live(cgroup)
    if lifecycle._group_identity(current) != identity_group:
        raise ValueError("owned cgroup identity or fixed limits changed")
    if memory._file(group_path / "cgroup.events").splitlines().count("populated 0") != 1:
        raise ValueError("owned cgroup is not empty")
    observed = lifecycle.topology.Topology.snapshot_target(group_path, device=current["device"], inode=current["inode"]).to_record()
    if observed != snapshot or lifecycle._boot() != boot:
        raise ValueError("host boot or topology changed")


def _launcher(path, *, native, digest, slot, cgroup, saved_cpus, saved_nodes,
              record, owner_file, release_file, temporary, address_limit, cpu_limit):
    """Reuse the sealed-image placement gate and add finite inherited limits."""
    template = path.with_name(path.name + ".template")
    functional._launcher(template, whole=native, whole_sha256=digest, slot=slot,
        cgroup=cgroup, saved_cpus=saved_cpus, saved_nodes=saved_nodes, record=record,
        owner_file=owner_file, release_file=release_file, temporary=temporary)
    code = template.read_text(encoding="utf-8")
    needle = "record=placement.apply_slot("
    if code.count(needle) != 1:
        raise ValueError("placement launcher template changed")
    limits = ("import resource\n"
        "def cap(kind,soft,hard):\n"
        " before=resource.getrlimit(kind)\n"
        " if any(v!=resource.RLIM_INFINITY and v<hard for v in before): raise RuntimeError('inherited soft or hard limit below requested budget')\n"
        " resource.setrlimit(kind,(soft,hard))\n"
        f"cap(resource.RLIMIT_AS,{address_limit},{address_limit})\n"
        f"cap(resource.RLIMIT_CPU,{cpu_limit},{cpu_limit+max(5, 2*len(slot['cpus']))})\n")
    code = code.replace(needle, limits + needle, 1)
    marker = "with Path(" + repr(str(record)) + ").open('x',encoding='utf-8') as stream:"
    if code.count(marker) != 1:
        raise ValueError("placement launcher record marker changed")
    code = code.replace(marker, "record['runtime_limits']={'address_space':list(resource.getrlimit(resource.RLIMIT_AS)),'cpu':list(resource.getrlimit(resource.RLIMIT_CPU))}\n" + marker, 1)
    functional._write_exclusive(path, code.encode("utf-8"))
    path.chmod(0o700)


def _pins(peer_name, profile, build_dir, build_record):
    files = original._read_sources(peer_name, build_dir)
    snapshot = original.source_record(peer_name, profile, files)
    if (snapshot["source"] != build_record["source"] or
            snapshot["source_closure_sha256"] != build_record["source_closure_sha256"]):
        raise ValueError("original source snapshot changed")
    fd = original.peer_exact_runner._open_directory(build_dir)
    try:
        data = original._read_regular(fd, "peer-native-1", original.MAX_NATIVE_BYTES)
    finally:
        os.close(fd)
    attempt = build_record["attempts"][0]
    if len(data) != attempt["bytes"] or hashlib.sha256(data).hexdigest() != attempt["sha256"]:
        raise ValueError("original native changed")
    return data


def _mapping_observation(pid, expected_bytes, native, peer_name):
    """Observe candidate pointer and VMAs without assuming ABI or residency."""
    maps = peer.mappings(pid)
    candidates = [row for row in maps if row["permissions"].startswith("rw-p") and
                  not row["path"] and row["end"] - row["start"] >= expected_bytes]
    if len(candidates) > 64:
        raise ValueError("too many large mapping candidates")
    node_rows = {}
    for line in Path(f"/proc/{pid}/numa_maps").read_text().splitlines():
        fields = line.split()
        if fields:
            try:
                start = int(fields[0], 16)
            except ValueError:
                continue
            if any(row["start"] == start for row in candidates):
                node_rows[start] = {int(k[1:]): int(v) for field in fields[1:]
                    if "=" in field for k, v in [field.split("=", 1)]
                    if k.startswith("N") and k[1:].isdigit() and v.isdigit()}
    result = {"candidate_mappings": [{"start": row["start"], "end": row["end"],
             "node_pages": node_rows.get(row["start"])} for row in candidates],
            "tt_attribution_proven": False, "tt_abi_verified": False,
            "scope": "large anonymous RW mappings only; page counts can include non-TT memory"}
    symbol = {"ice4": "TT", "c4ke": "TTABLE"}[peer_name]
    try:
        # Candidate pointer from this exact running image. The source/compiler
        # provenance and assumed eight-byte entry ABI are not authenticated.
        result["symbol_candidate"] = peer.runtime_tt(pid, peer.Elf64(native), symbol, expected_bytes)
        result["symbol_candidate"]["symbol"] = symbol
        result["symbol_candidate"]["entry_bytes_assumed"] = result["symbol_candidate"].pop("entry_bytes")
        result["symbol_candidate"]["scope"] = "symbol pointer candidate and contiguous private RW virtual extent; ABI and allocation attribution unverified"
        result["symbol_candidate"]["abi_assumption_unverified"] = True
    except (ValueError, OSError, RuntimeError) as error:
        result["symbol_candidate_unavailable"] = {"type": type(error).__name__, "message": str(error)}
    return result


def _infinite_stop(owned, scope, oracle, cpus, *, verify_owner=None):
    """Observe activity and a legal stop response for infinite GO only."""
    pid = owned.process.pid
    before = scope.task_snapshot(pid)
    previous = len(peer._best_lines(owned))
    owned.send(b"position startpos\ngo infinite\n")
    deadline = time.monotonic() + owned.budget.left(20)
    observed = None
    while time.monotonic() < deadline:
        if owned.exited() or len(peer._best_lines(owned)) != previous:
            raise ValueError("infinite search ended before stop")
        for tid, item in scope.task_snapshot(pid).items():
            if tid == pid or item["cpu_ticks"] <= before.get(tid, {}).get("cpu_ticks", 0):
                continue
            try:
                sample = peer._worker_evidence(pid, tid)
            except (FileNotFoundError, ProcessLookupError):
                continue
            if sample["cpus"] != sorted(cpus):
                raise ValueError("infinite search worker left its CPU slot")
            observed = sample
            break
        if observed is not None:
            break
        time.sleep(.01)
    if observed is None:
        raise TimeoutError("infinite search worker activity not observed")
    if verify_owner is not None:
        verify_owner()
    if owned.exited() or len(peer._best_lines(owned)) != previous:
        raise ValueError("infinite search ended before stop")
    owned.send(b"stop\n")
    owned.stdout.until(lambda raw: sum(line.startswith(b"bestmove ") for line in raw.splitlines()) > previous,
                       owned.budget, seconds=30)
    lines = peer._best_lines(owned)
    if len(lines) != previous + 1:
        raise ValueError("infinite stop produced duplicate bestmove")
    best = peer.checked_best(lines[-1], oracle.Board.from_fen())
    ready = owned.stdout.bytes().splitlines().count(b"readyok") + 1
    owned.send(b"isready\n")
    owned.wait_line(b"readyok", ready)
    if len(peer._best_lines(owned)) != previous + 1:
        raise ValueError("late duplicate bestmove after infinite stop")
    return {"worker_activity": observed, "bestmove": best, "ready_observed": True,
            "scope": "infinite GO stop only; timed GO stop responsiveness is unproved"}


def _run_session(*, label, peer_name, profile, build_dir, build_record, output,
                 slot, cgroup, saved_cpus, saved_nodes, group_path, identity_group,
                 snapshot, boot, wall_seconds, address_limit, cpu_limit, seen, sessions):
    scope, owner, oracle = diagnostic._profile_verifier().support_modules()
    directory = output / label
    directory.mkdir(mode=0o700)
    own_dir, tmp = directory / "owned", directory / "tmp"
    own_dir.mkdir(mode=0o700)
    tmp.mkdir(mode=0o700)
    launcher, preexec = directory / "launcher", directory / "placement.json"
    owner_file, release = directory / "owner.json", directory / "release"
    native_sha = build_record["attempts"][0]["sha256"]
    native = _pins(peer_name, profile, build_dir, build_record)
    expected = original._PROFILES[profile]
    _launcher(launcher, native=build_dir / "peer-native-1", digest=native_sha,
        slot=slot, cgroup=cgroup, saved_cpus=saved_cpus, saved_nodes=saved_nodes,
        record=preexec, owner_file=owner_file, release_file=release, temporary=tmp,
        address_limit=address_limit, cpu_limit=cpu_limit)
    row = {"label": label, "complete": False, "events_before": functional._events(group_path)}
    sessions.append(row)
    owned = None
    try:
        owned = peer.construct_owned(owner, launcher, own_dir, owner.Budget(wall_seconds))
        identity = placement._process_identity(owned.process.pid)
        if not identity["alive"] or identity["pid"] != identity["pgid"] or identity["pid"] != identity["session"]:
            raise ValueError("owned leader is not the original session leader")
        key = (identity["pid"], identity["start_ticks"])
        if key in seen:
            raise ValueError("lifecycle process identity reused")
        seen.add(key)
        row["owner_identity"] = identity
        raw = (json.dumps(identity, sort_keys=True, separators=(",", ":")) + "\n").encode()
        functional._write_exclusive(owner_file, raw)
        functional._write_exclusive(release, hashlib.sha256(raw).hexdigest().encode())
        deadline = time.monotonic() + owned.budget.left(30)
        while not preexec.exists():
            if owned.exited() or time.monotonic() >= deadline:
                raise TimeoutError("owned placement did not complete")
            time.sleep(.01)
        reader = diagnostic._profile_verifier().input_reader()
        row["pre_exec"] = json.loads(reader.read_regular(preexec, limit=65536))
        view = SimpleNamespace(cpus=tuple(slot["cpus"]), memory_nodes=tuple(slot["memory_nodes"]), policy=slot["policy"])
        row["pre_exec_verified"] = diagnostic.run.verify_preexec_placement(row["pre_exec"], pid=identity["pid"], slot=view, cgroup=cgroup)
        limits = {"address_space": [address_limit, address_limit],
                  "cpu": [cpu_limit, cpu_limit + max(5, 2 * len(slot["cpus"]))]}
        if row["pre_exec"].get("runtime_limits") != limits:
            raise ValueError("pre-exec hard limits differ")

        def verify_policy(_owned, resources):
            lifecycle._current_owner(identity, group_path)
            if os.sched_getaffinity(identity["pid"]) != set(slot["cpus"]):
                raise ValueError("live engine CPU mask differs")
            current = placement.verify_cgroup_live(cgroup)
            if lifecycle._group_identity(current) != identity_group:
                raise ValueError("cgroup changed before allocation")
            if (resources["workers"] != expected["workers"] or
                    resources["hash_mib"] != expected["hash_mib"]):
                raise ValueError("requested upstream options changed")
            row["startup_image"] = scope.image_snapshot(identity["pid"], native_sha)
            return True

        row["uci"] = uci.configure_owned(owned, peer=peer_name, profile=profile,
            verify_owned_policy=verify_policy, timeout_seconds=min(600, wall_seconds - 5))
        lifecycle._current_owner(identity, group_path)
        # Clearing can touch the full TT. Observe completion separately; readyok
        # does not establish the allocation, object identity, or residency.
        ready = owned.stdout.bytes().splitlines().count(b"readyok") + 1
        start = time.monotonic()
        owned.send(b"ucinewgame\nisready\n")
        owned.stdout.until(lambda raw: raw.splitlines().count(b"readyok") >= ready,
                           owned.budget, seconds=wall_seconds)
        if owned.stdout.bytes().splitlines().count(b"readyok") != ready:
            raise ValueError("ucinewgame acknowledgement differs")
        row["ucinewgame"] = {"ready_observed": True, "elapsed_seconds": time.monotonic() - start}
        lifecycle._current_owner(identity, group_path)
        row["memory_after_clear"] = _mapping_observation(identity["pid"], expected["expected_tt_bytes_if_entry8"], native, peer_name)
        if label in ("cold", "warm"):
            if label == "warm":
                row["warmup_search"] = peer._search(owned, scope, oracle, [], "warmup")
            row["search"] = peer._search(owned, scope, oracle, [], label,
                workers=expected["workers"], cpus=slot["cpus"], capture_smt=True)
            lifecycle._current_owner(identity, group_path)
            row["memory_after_search"] = _mapping_observation(identity["pid"], expected["expected_tt_bytes_if_entry8"], native, peer_name)
            if label == "warm":
                row["infinite_stop"] = _infinite_stop(owned, scope, oracle, slot["cpus"],
                    verify_owner=lambda: lifecycle._current_owner(identity, group_path))
                lifecycle._current_owner(identity, group_path)
            row["pre_terminal_image"] = scope.image_snapshot(identity["pid"], native_sha)
            owned.send(b"quit\n")
            owned.close_input()
        else:
            row["active_termination"] = lifecycle._active_termination(owned, scope, slot["cpus"], label,
                expected_identity=identity, group_path=group_path, native_sha256=native_sha,
                before_terminal=lambda: _mapping_observation(identity["pid"], expected["expected_tt_bytes_if_entry8"], native, peer_name),
                expected_workers=expected["workers"])
            row["memory_during_search"] = row["active_termination"].pop("b_symbol_candidate")
        row["finish"] = peer._finish_peer(owned, seconds=20)
        if label.startswith("active-"):
            lines = peer._best_lines(owned)
            if len(lines) > 1:
                raise ValueError("active termination emitted duplicate bestmove")
            row["closing_bestmove"] = peer.checked_best(lines[0], oracle.Board.from_fen()) if lines else None
        cleaned = owned.cleanup()
        owned = None
        row["cleanup"] = cleaned
        if (row["cleanup"].get("owned_group_absent") is not True or
                row["cleanup"].get("readers_joined") is not True or
                row["cleanup"].get("forced_cleanup") or row["cleanup"].get("errors")):
            raise ValueError("owned peer did not settle normally")
    except BaseException as error:
        row["failure"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        if owned is not None:
            row["cleanup"] = owned.cleanup()
        for remaining in tuple(owner.OWNED):
            row.setdefault("recovered_constructor_handles", []).append(remaining.cleanup())
        row["events_after"] = functional._events(group_path)
        if any(row["events_after"][key] < value for key, value in row["events_before"].items()):
            raise ValueError("cgroup memory counters regressed")
        if any(row["events_after"][key] > row["events_before"][key] for key in ("oom", "oom_kill")):
            raise ValueError("owned cgroup observed an OOM")
        if memory._file(group_path / "cgroup.events").splitlines().count("populated 0") != 1:
            raise ValueError("owned cgroup did not become empty")
        row["cgroup_populated_zero"] = True
        _pins(peer_name, profile, build_dir, build_record)
        _recheck_environment(group_path, cgroup, identity_group, snapshot, boot)
    row["complete"] = True
    return row


@peer.owned_signals
def collect(*, peer_name, profile, source_root, output, slot, cgroup,
            saved_ancestor_cpus, saved_ancestor_nodes=None, wall_seconds=600):
    if sys.platform != "linux" or peer_name not in ("ice4", "c4ke") or profile not in original._PROFILES:
        raise ValueError("Linux and a supported original peer TEST profile are required")
    if type(wall_seconds) is not int or not 90 <= wall_seconds <= 3600:
        raise ValueError("bounded per-session wall time required")
    output = original._outside_checkout(Path(output))
    source_root = original._outside_checkout(Path(source_root))
    if output == source_root or output.is_relative_to(source_root) or source_root.is_relative_to(output):
        raise ValueError("source and output must not overlap")
    group_path, group, snapshot = lifecycle._verify_environment(profile, slot, cgroup,
        saved_ancestor_cpus, saved_ancestor_nodes)
    expected = original._PROFILES[profile]
    overhead = max(768 << 20, expected["workers"] * (16 << 20)) + (1 << 30)
    required = expected["expected_tt_bytes_if_entry8"] + overhead
    if group["memory_max"] < required:
        raise ValueError("declared cgroup hard limit below requested TT and overhead")
    parent_fd = original.peer_exact_runner._open_directory(output.parent)
    try:
        os.mkdir(output.name, 0o700, dir_fd=parent_fd)
        out_fd = os.open(output.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
        try:
            original._guard_output_path(output, parent_fd, out_fd)
        finally:
            os.close(out_fd)
    finally:
        os.close(parent_fd)
    boot, identity_group = lifecycle._boot(), lifecycle._group_identity(group)
    report = {"format": "rove4k-original-peer-owned-test-v1", "peer": peer_name,
        "profile": profile, "requested_uci": dict(expected), "slot": slot,
        "cgroup": group, "topology": snapshot, "boot_id": boot,
        "current_availability_enforced": False, "tcec_size_limit_applied": False,
        "performance_eligible": False, "gc_intervention_observation": "unknown",
        "league_qualified": False, "scored_game_admitted": False,
        "source_to_native_proven": False, "tt_abi_verified": False,
        "tt_allocation_observed": False, "complete": False, "sessions": [],
        "limitations": ["source and native pins do not authenticate compiler or exclude transient same-UID mutation",
            "unattributed anonymous mappings do not prove TT layout or physical residency",
            "owned group cleanup cannot exclude escaped descendants or supervisor death",
            "upstream timed GO joins search workers; prompt stop during timed GO is not established",
            "GC intervention coverage is unknown; no performance data or score authority"]}
    failure = None
    try:
        built = original.build(peer_name, profile, source_root, output / "snapshot", cpu=min(os.sched_getaffinity(0)))
        build_record = built["record"]
        if (build_record["complete"] is not True or build_record["same_host_native_reproduced"] is not True or
                len(build_record["attempts"]) != 2 or
                any((x["bytes"], x["sha256"]) != (build_record["attempts"][0]["bytes"], build_record["attempts"][0]["sha256"]) for x in build_record["attempts"])):
            raise ValueError("original native reproduction differs")
        report["build"] = {"receipt_sha256": built["sha256"], "revision": build_record["revision"],
            "source_closure_sha256": build_record["source_closure_sha256"],
            "native_bytes": build_record["attempts"][0]["bytes"],
            "native_sha256": build_record["attempts"][0]["sha256"],
            "same_host_native_reproduced": True}
        _pins(peer_name, profile, output / "snapshot", build_record)
        seen = set()
        for label in LABELS:
            _recheck_environment(group_path, cgroup, identity_group, snapshot, boot)
            _run_session(label=label, peer_name=peer_name, profile=profile,
                build_dir=output / "snapshot", build_record=build_record, output=output,
                slot=slot, cgroup=cgroup, saved_cpus=saved_ancestor_cpus, saved_nodes=saved_ancestor_nodes,
                group_path=group_path, identity_group=identity_group, snapshot=snapshot, boot=boot,
                wall_seconds=wall_seconds, address_limit=required,
                cpu_limit=wall_seconds * expected["workers"] + 30, seen=seen, sessions=report["sessions"])
        report["complete"] = len(report["sessions"]) == len(LABELS) and all(row["complete"] for row in report["sessions"])
        if not report["complete"]:
            raise ValueError("original peer lifecycle observations are incomplete")
    except BaseException as error:
        failure = error
        report["failure"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        functional._write_exclusive(output / "lifecycle.json", (json.dumps(report, sort_keys=True, indent=2) + "\n").encode())
    if failure is not None:
        raise functional.FunctionalProbeFailure("original peer owned diagnostic failed; see retained report", report) from failure
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--peer", choices=("ice4", "c4ke"), required=True)
    parser.add_argument("--profile", choices=tuple(original._PROFILES), required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--placement", type=Path, required=True)
    parser.add_argument("--placement-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--wall-seconds", type=int, default=600)
    args = parser.parse_args(argv)
    record, _ = diagnostic.run.json_input(diagnostic._safe_input_path(args.placement), args.placement_sha256)
    if type(record) is not dict or set(record) not in ({"slot", "cgroup", "saved_ancestor_cpus"},
            {"slot", "cgroup", "saved_ancestor_cpus", "saved_ancestor_nodes"}):
        raise ValueError("pinned single-slot placement record required")
    result = collect(peer_name=args.peer, profile=args.profile, source_root=args.source, output=args.out,
        slot=record["slot"], cgroup=record["cgroup"], saved_ancestor_cpus=record["saved_ancestor_cpus"],
        saved_ancestor_nodes=record.get("saved_ancestor_nodes"), wall_seconds=args.wall_seconds)
    print(json.dumps({"report": str(args.out / "lifecycle.json"), "complete": result["complete"],
                      "scored_game_admitted": False}, sort_keys=True))


if __name__ == "__main__":
    main()
