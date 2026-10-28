"""One-engine UCI smoke for a separately owned, bounded diagnostic session.

The caller owns the process and its resource placement. This module does not
open a scored game, prove TT provenance, or turn a smoke into qualification.
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

# Isolated Python omits the executed script's directory. Admit only this
# source-bound sibling directory, as the existing strength CLI does.
sys.dont_write_bytecode = True
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from . import diagnostic_candidates, memory_observation, peak_capacity, peak_probe_session, peer_runtime, placement, topology
except ImportError:
    import diagnostic_candidates
    import memory_observation
    import peak_capacity
    import peak_probe_session
    import peer_runtime
    import placement
    import topology


class FunctionalProbeFailure(RuntimeError):
    """A failed owned diagnostic; its report retains cleanup and OOM evidence."""

    def __init__(self, message, report):
        super().__init__(message)
        self.report = report


def _write_exclusive(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def _events(path):
    raw = memory_observation._file(path / "memory.events")
    result = {}
    for line in raw.splitlines():
        fields = line.split()
        if len(fields) != 2 or fields[0] in result or not fields[1].isdecimal():
            raise ValueError("malformed cgroup memory events")
        result[fields[0]] = int(fields[1])
    if not {"oom", "oom_kill"}.issubset(result):
        raise ValueError("cgroup OOM event counters unavailable")
    return result


def _launcher(path, *, whole, whole_sha256, slot, cgroup, saved_cpus, saved_nodes=None, record, owner_file, release_file, temporary):
    """Place a registered session leader in its original cgroup before exec."""
    placement_source = diagnostic_candidates._safe_input_path(Path(placement.__file__).absolute())
    reader = diagnostic_candidates._profile_verifier().input_reader()
    placement_sha = hashlib.sha256(reader.read_regular(placement_source, limit=1 << 20)).hexdigest()
    topology_source = diagnostic_candidates._safe_input_path(Path(topology.__file__).absolute())
    topology_sha = hashlib.sha256(reader.read_regular(topology_source, limit=1 << 20)).hexdigest()
    # The script receives only values that the parent has just validated. It
    # waits until the original process-group owner has been durably recorded.
    code = "#!/usr/bin/python3 -I\n" + "\n".join((
        "import fcntl,hashlib,json,os,stat,sys,time,types", "from pathlib import Path", "sys.dont_write_bytecode=True",
        "def read_safe(path,limit):",
        " p=Path(path)",
        " if not p.is_absolute() or '..' in p.parts: raise RuntimeError('unsafe input path')",
        " d=os.open(p.anchor,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)",
        " try:",
        "  for part in p.parts[1:-1]:",
        "   n=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=d);os.close(d);d=n",
        "  f=os.open(p.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=d)",
        "  try:",
        "   s=os.fstat(f)",
        "   if not stat.S_ISREG(s.st_mode) or s.st_nlink!=1 or s.st_size<0 or s.st_size>limit: raise RuntimeError('input extent differs')",
        "   pieces=[];left=s.st_size",
        "   while left:",
        "    chunk=os.read(f,min(left,65536))",
        "    if not chunk: raise RuntimeError('short input')",
        "    pieces.append(chunk);left-=len(chunk)",
        "   t=os.fstat(f);current=os.stat(p.name,dir_fd=d,follow_symlinks=False)",
        "   if (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)!=(t.st_dev,t.st_ino,t.st_size,t.st_mtime_ns,t.st_ctime_ns) or (s.st_dev,s.st_ino)!=(current.st_dev,current.st_ino): raise RuntimeError('input changed')",
        "   return b''.join(pieces)",
        "  finally: os.close(f)", " finally: os.close(d)",
        "for name,path,digest in " + repr((('topology', str(topology_source), topology_sha),
                                               ('placement', str(placement_source), placement_sha))) + ":",
        " raw=read_safe(path,1<<20)",
        " if hashlib.sha256(raw).hexdigest()!=digest: raise RuntimeError('placement source changed')",
        " mod=types.ModuleType(name);mod.__file__=path;sys.modules[name]=mod;exec(compile(raw,path,'exec'),mod.__dict__)",
        "placement=sys.modules['placement']",
        "release=Path(" + repr(str(release_file)) + ")", "deadline=time.monotonic()+30",
        "while not release.exists():",
        " if os.getppid()!=" + str(os.getpid()) + " or time.monotonic()>deadline: raise RuntimeError('diagnostic owner gate not released')",
        " time.sleep(.01)",
        "raw=read_safe(" + repr(str(owner_file)) + ",65536)", "owner=json.loads(raw)",
        "if hashlib.sha256(raw).hexdigest()!=read_safe(release,128).decode('ascii').strip() or owner['pid']!=os.getpid(): raise RuntimeError('owner identity differs')",
        "fields=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()",
        "if [owner['pgid'],owner['session'],owner['start_ticks']]!=[int(fields[2]),int(fields[3]),int(fields[19])]: raise RuntimeError('original process identity changed')",
        "target=Path(" + repr(str(whole)) + ")",
        "whole=read_safe(target,256<<20)",
        "if hashlib.sha256(whole).hexdigest()!=" + repr(whole_sha256) + ": raise RuntimeError('whole candidate changed')",
        # Seal the verified bytes before placement so a later pathname swap or
        # in-place write cannot change the script that the kernel interprets.
        # The inheritable fd is essential: submitted shell wrappers reopen $0.
        "image=os.memfd_create('rove4k-functional-whole',os.MFD_ALLOW_SEALING)",
        "os.fchmod(image,0o700)",
        "view=memoryview(whole)",
        "while view:",
        " written=os.write(image,view)",
        " if written<=0: raise RuntimeError('short candidate snapshot write')",
        " view=view[written:]",
        "seals=fcntl.F_SEAL_WRITE|fcntl.F_SEAL_GROW|fcntl.F_SEAL_SHRINK|fcntl.F_SEAL_SEAL",
        "fcntl.fcntl(image,fcntl.F_ADD_SEALS,seals)",
        "if fcntl.fcntl(image,fcntl.F_GET_SEALS)&seals!=seals: raise RuntimeError('candidate snapshot not sealed')",
        "os.set_inheritable(image,True)",
        "record=placement.apply_slot(" + repr(slot) + ",cgroup=" + repr(cgroup) + ",saved_ancestor_cpus=" + repr(saved_cpus) + ",saved_ancestor_nodes=" + repr(saved_nodes) + ")",
        "policy=record.get('observed_policy')",
        "if record['fallback'] is not None or not isinstance(policy,dict) or policy.get('available') is not True or policy.get('request_applied') is not True or policy.get('mode')!=0: raise RuntimeError('requested NUMA policy not observed')",
        "with Path(" + repr(str(record)) + ").open('x',encoding='utf-8') as stream:",
        " stream.write(json.dumps(record,sort_keys=True)+'\\n');stream.flush();os.fsync(stream.fileno())",
        "os.environ['TMPDIR']=" + repr(str(temporary)),
        "os.execve(image,[str(target)],os.environ)", "",
    ))
    _write_exclusive(path, code.encode("utf-8"))
    path.chmod(0o700)


@peer_runtime.owned_signals
def run_candidate(*, candidate_path, candidate_sha256, artifact_id, profile,
                  slot, cgroup, saved_ancestor_cpus, out, wall_seconds=120, saved_ancestor_nodes=None):
    """Run one pinned candidate in a fresh owned cgroup, without score authority.

    This uses point-in-time capacity and kernel cgroup limits, not a physical
    reservation. The caller remains responsible for the cgroup's ownership,
    creating/removing it and recording any external runtime prerequisites.
    """
    if sys.platform != "linux":
        raise RuntimeError("functional diagnostic requires Linux")
    if (profile not in ("test-p16", "test-p192") or type(wall_seconds) is not int or
            not 90 <= wall_seconds <= 300):
        raise ValueError("a bounded P16/P192 diagnostic is required")
    rows, candidate_digest = diagnostic_candidates.read_candidates(candidate_path, candidate_sha256, profile,
                                                                    allow_single=True)
    matches = [row for row in rows if row["artifact"].id == artifact_id]
    if len(matches) != 1:
        raise ValueError("one exact pinned candidate is required")
    candidate = matches[0]
    artifact = candidate["artifact"]
    workers = {"test-p16": 16, "test-p192": 192}[profile]
    slot = json.loads(json.dumps(slot.to_record() if hasattr(slot, "to_record") else slot))
    if (not isinstance(slot, dict) or slot.get("workers") != workers or
            not isinstance(slot.get("cpus"), list) or len(slot["cpus"]) != workers or
            len(set(slot["cpus"])) != workers or slot["cpus"] != sorted(slot["cpus"]) or
            any(type(x) is not int or x < 0 for x in slot["cpus"]) or
            not isinstance(slot.get("memory_nodes"), list) or not slot["memory_nodes"] or
            any(type(x) is not int or x < 0 for x in slot["memory_nodes"]) or
            len(set(slot["memory_nodes"])) != len(slot["memory_nodes"]) or
            slot["memory_nodes"] != sorted(slot["memory_nodes"]) or
            profile == "test-p16" and len(slot["memory_nodes"]) != 1 or
            slot.get("policy") != "default"):
        raise ValueError("slot does not match the diagnostic profile")
    if (not isinstance(saved_ancestor_cpus, list) or any(type(x) is not int or x < 0 for x in saved_ancestor_cpus) or
            not set(slot["cpus"]).issubset(saved_ancestor_cpus) or
            len(set(saved_ancestor_cpus)) != len(saved_ancestor_cpus)):
        raise ValueError("original CPU envelope does not contain the slot")
    if saved_ancestor_nodes is not None and (not isinstance(saved_ancestor_nodes, list) or
            not saved_ancestor_nodes or any(type(x) is not int or x < 0 for x in saved_ancestor_nodes) or
            len(set(saved_ancestor_nodes)) != len(saved_ancestor_nodes) or
            not set(slot["memory_nodes"]).issubset(saved_ancestor_nodes)):
        raise ValueError("original NUMA node envelope does not contain the slot")
    if not isinstance(cgroup, dict) or not isinstance(cgroup.get("path"), str):
        raise ValueError("original cgroup identity is required")
    group_path = Path(cgroup["path"])
    mount = Path("/sys/fs/cgroup")
    if (not group_path.is_absolute() or ".." in group_path.parts or not group_path.is_relative_to(mount) or
            group_path == mount or any(path.is_symlink() for path in (group_path, *group_path.parents))):
        raise ValueError("diagnostic cgroup must be an original visible cgroup2 descendant")
    peak_probe_session._require_delegated_root(group_path)
    group = placement.verify_cgroup_live(cgroup)
    if (group["cpus"] != sorted(slot["cpus"]) or group["memory_nodes"] != sorted(slot["memory_nodes"])):
        raise ValueError("original cgroup masks differ from the selected slot")
    # Ensure this is a real visible cgroup2 leaf; a fixture directory must not
    # be capable of authorizing an actual large process.
    peak_capacity._require_empty(group_path)
    observed_topology = topology.Topology.snapshot_target(group_path, device=group["device"], inode=group["inode"])
    if profile == "test-p16":
        planned_slots = topology.plan_slots(observed_topology, 8, 16, reserve_physical=0, max_slots=1, policy="default")
        if len(planned_slots) != 1:
            raise ValueError("P16 requires one complete SMT slot")
        planned = planned_slots[0]
        by_id = {cpu.id: cpu for cpu in observed_topology.cpus}
        for core in planned.physical_cores:
            members = {cpu for cpu in planned.cpus if by_id[cpu].physical == core}
            if len(members) != 2 or any(set(by_id[cpu].siblings) != members for cpu in members):
                raise ValueError("P16 requires mutually observed SMT siblings")
    else:
        planned = topology.plan_p192_slot(observed_topology, policy="default")
    expected_slot = json.loads(json.dumps(planned.to_record()))
    if any(slot.get(key) != expected_slot[key] for key in ("cpus", "physical_cores", "memory_nodes", "workers", "smt", "policy")):
        raise ValueError("live physical cores, SMT siblings or NUMA nodes differ from the frozen slot")
    overhead = max(768 << 20, workers * (16 << 20)) + (256 << 20)
    required = artifact.tt_bytes + overhead
    if group["memory_max"] < required:
        raise ValueError("cgroup memory.max is below TT and declared headroom")
    capacity = memory_observation.observe_capacity([slot], group_path, mask_scope="delegated-only")
    remaining = peak_capacity._finite_remaining(capacity["delegated_cgroup"])
    available = min([capacity["host_memavailable_bytes"], *remaining])
    node_available = sum(capacity["node_available_bytes"].values())
    if available < required or node_available < required:
        raise ValueError("current host or visible cgroup/node capacity is insufficient")
    output = diagnostic_candidates._safe_output_path(out)
    output.mkdir(mode=0o700)
    own_directory = output / "owned"
    own_directory.mkdir(mode=0o700)
    temporary = output / "tmp"
    temporary.mkdir(mode=0o700)
    scope, owner, oracle = diagnostic_candidates._profile_verifier().support_modules()
    events_before = _events(group_path)
    boot_id = Path("/proc/sys/kernel/random/boot_id").read_text(encoding="ascii").strip()
    if not re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", boot_id):
        raise ValueError("kernel boot identity unavailable or malformed")
    report = {"format": "rove4k-functional-candidate-v1", "profile": profile, "artifact_id": artifact.id,
              "family": artifact.family, "candidate_set_sha256": candidate_digest,
              "whole_sha256": artifact.sha256, "native_sha256": artifact.native_sha256,
              "tt_bytes": artifact.tt_bytes, "workers": artifact.workers, "source_evidence": candidate["evidence"],
              "source_sha256": candidate["source"]["sha256"],
              "placement": group, "topology": observed_topology.to_record(), "capacity": capacity, "declared_overhead_bytes": overhead,
              "required_bytes": required, "memory_events_before": events_before, "boot_id": boot_id,
              "complete": False, "scored_game_admitted": False,
              "limitations": ["point-in-time availability is not memory reservation",
                  "external cgroup writers and hidden ancestors are not excluded",
                  "declared overhead is not a proven workload upper bound",
                  "existing candidate/receipt parser performs path checks and reads separately",
                  "sealed snapshot execution depends on Linux memfd and /dev/fd support, and differs from TCEC path execution",
                  "whole/native identity does not prove executable continuity or source provenance",
                  "worker completeness and TT-specific NUMA placement remain unproved"]}
    launcher = output / "launcher"
    placement_record = output / "placement.json"
    owner_file, release_file = output / "owner.json", output / "release"
    _launcher(launcher, whole=candidate["whole"], whole_sha256=artifact.sha256, slot=slot,
              cgroup=cgroup, saved_cpus=saved_ancestor_cpus, saved_nodes=saved_ancestor_nodes, record=placement_record,
              owner_file=owner_file, release_file=release_file, temporary=temporary)
    owned, failure = None, None
    try:
        launch_started = time.monotonic()
        owned = peer_runtime.construct_owned(owner, launcher, own_directory, owner.Budget(wall_seconds))
        identity = placement._process_identity(owned.process.pid)
        if not identity["alive"] or identity["pid"] != identity["pgid"] or identity["pid"] != identity["session"]:
            raise ValueError("diagnostic leader does not own its original session")
        raw = (json.dumps(identity, sort_keys=True, separators=(",", ":")) + "\n").encode()
        report["owner_identity"] = identity
        _write_exclusive(owner_file, raw)
        _write_exclusive(release_file, hashlib.sha256(raw).hexdigest().encode("ascii"))
        placement_deadline = time.monotonic() + owned.budget.left(30)
        while not placement_record.exists():
            if owned.exited():
                raise ValueError("diagnostic launcher exited before placement")
            if time.monotonic() >= placement_deadline:
                raise TimeoutError("diagnostic placement deadline expired")
            time.sleep(.01)
        if placement_record.is_symlink() or placement_record.stat().st_size > 65536:
            raise ValueError("invalid placement receipt")
        report["pre_exec"] = json.loads(placement_record.read_text(encoding="utf-8"))
        slot_view = SimpleNamespace(cpus=tuple(slot["cpus"]), memory_nodes=tuple(slot["memory_nodes"]),
                                    policy=slot["policy"])
        report["pre_exec_verified"] = diagnostic_candidates.run.verify_preexec_placement(
            report["pre_exec"], pid=identity["pid"], slot=slot_view, cgroup=cgroup)
        if str(identity["pid"]) not in memory_observation._file(group_path / "cgroup.procs").splitlines():
            raise ValueError("original diagnostic leader is absent from its cgroup")
        result = exercise_protocol(owned, oracle=oracle, scope=scope, native_sha256=artifact.native_sha256,
                                   cpus=slot["cpus"], launched_at=launch_started)
        if placement._process_identity(owned.process.pid) != identity:
            raise ValueError("original process identity changed during diagnostic")
        if str(identity["pid"]) not in memory_observation._file(group_path / "cgroup.procs").splitlines():
            raise ValueError("original diagnostic leader left its cgroup")
        report["uci"] = result
        after_topology = topology.Topology.snapshot_target(group_path, device=group["device"], inode=group["inode"])
        if after_topology.to_record() != observed_topology.to_record():
            raise ValueError("diagnostic topology changed during UCI search")
        owned.send(b"quit\n")
        owned.close_input()
        report["settled"] = peer_runtime._finish_peer(owned, seconds=20)
        diagnostic_candidates._pinned_file(candidate["source"])
        diagnostic_candidates._pinned_file(candidate["native"], expected=artifact.native_sha256)
        diagnostic_candidates._pinned_file({"path": str(candidate["whole"]), "bytes": artifact.whole_bytes,
                                             "sha256": artifact.sha256}, expected=artifact.sha256)
    except Exception as error:
        failure = error
        report["failure"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        if owned is not None:
            try:
                report["cleanup"] = owned.cleanup()
            except BaseException as error:
                report["cleanup_failure"] = {"type": type(error).__name__, "message": str(error)}
                failure = failure or error
        # If construction raised after registering the process, the handle may
        # exist only in this freshly loaded owner's registry.
        for remaining in tuple(owner.OWNED):
            try:
                recovered = remaining.cleanup()
                report.setdefault("recovered_constructor_handles", []).append(recovered)
            except BaseException as error:
                report["recovered_cleanup_failure"] = {"type": type(error).__name__, "message": str(error)}
                failure = failure or error
        try:
            report["memory_events_after"] = _events(group_path)
            report["cgroup_after"] = placement.verify_cgroup_live(cgroup)
            if any(report["memory_events_after"][key] < value for key, value in events_before.items()):
                raise ValueError("cgroup memory event counters went backwards")
            report["oom_observed"] = any(report["memory_events_after"][key] > events_before[key]
                                         for key in ("oom", "oom_kill"))
            if report["oom_observed"]:
                raise ValueError("cgroup observed an OOM event")
            cgroup_events = memory_observation._file(group_path / "cgroup.events")
            report["cgroup_populated_zero"] = cgroup_events.splitlines().count("populated 0") == 1
            if not report["cgroup_populated_zero"]:
                raise ValueError("diagnostic cgroup still contains a live process")
        except BaseException as error:
            report["observation_failure"] = {"type": type(error).__name__, "message": str(error)}
            failure = failure or error
        if (failure is None and "uci" in report and "settled" in report and
                report.get("cleanup", {}).get("owned_group_absent") is True and
                report["cleanup"].get("readers_joined") is True and
                not report["cleanup"].get("errors") and not report["cleanup"].get("forced_cleanup")):
            report["complete"] = True
        _write_exclusive(output / "functional-runtime.json", (json.dumps(report, sort_keys=True, indent=2) + "\n").encode())
    if failure is not None or not report["complete"]:
        raise FunctionalProbeFailure("functional diagnostic failed; see retained report", report) from failure
    return report


def _best_lines(data):
    return [line for line in data.splitlines() if line.startswith(b"bestmove ")]


def _ready_count(data):
    return data.splitlines().count(b"readyok")


def _numa_summary(pid):
    """Read whole-process mappings; this cannot establish TT-only placement."""
    path = Path("/proc") / str(pid) / "numa_maps"
    before = placement._process_identity(pid)
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(fd, "rb") as source:
            raw = source.read((16 << 20) + 1)
        if len(raw) > 16 << 20:
            raise ValueError("NUMA map exceeds diagnostic byte bound")
        nodes = {}
        for node, count in re.findall(rb"(?:^|\s)N(\d+)=(\d+)(?=\s|$)", raw):
            key = int(node)
            nodes[key] = nodes.get(key, 0) + int(count)
        result = {"available": True, "all_mapping_pages": nodes,
                  "raw_sha256": hashlib.sha256(raw).hexdigest()}
    except OSError as error:
        result = {"available": False, "reason": str(error)}
    if placement._process_identity(pid) != before:
        raise ValueError("process identity changed during NUMA observation")
    result["scope"] = "all mappings; not TT-only pages or NUMA remote-access efficiency"
    return result


def exercise_protocol(owned, *, oracle, scope, native_sha256, cpus,
                      startup_seconds=60, search_seconds=20, launched_at=None):
    """Exercise the original process, returning a diagnostic-only observation.

    ``owned`` must retain the original process group and bounded output readers.
    The search uses ordinary UCI clock fields rather than development options.
    TCEC 4K permits optional commands to be ignored: an idle stop is observed,
    but does not need to produce a response or start a search. The caller must
    still quit/reap the owned group and inspect cgroup events afterwards.
    """
    if (not isinstance(native_sha256, str) or len(native_sha256) != 64 or
            any(c not in "0123456789abcdef" for c in native_sha256)):
        raise ValueError("a frozen native SHA-256 is required")
    if (not isinstance(cpus, (tuple, list)) or not cpus or
            any(type(cpu) is not int or cpu < 0 for cpu in cpus) or len(set(cpus)) != len(cpus)):
        raise ValueError("distinct observed slot CPUs required")
    if (type(startup_seconds) not in (int, float) or not 0 < startup_seconds <= 60 or
            type(search_seconds) not in (int, float) or not 0 < search_seconds <= 30):
        raise ValueError("bounded startup and search deadlines required")
    pid = owned.process.pid
    started = time.monotonic() if launched_at is None else launched_at
    if type(started) not in (int, float) or started > time.monotonic():
        raise ValueError("invalid process launch monotonic time")
    remaining = startup_seconds - (time.monotonic() - started)
    if remaining <= 0:
        raise TimeoutError("combined startup exceeded deadline")
    owned.send(b"uci\n")
    owned.stdout.until(lambda raw: b"uciok" in raw.splitlines(), owned.budget, seconds=remaining)
    if _best_lines(owned.stdout.bytes()):
        raise ValueError("unsolicited bestmove during UCI startup")
    owned.send(b"isready\n")
    remaining = startup_seconds - (time.monotonic() - started)
    if remaining <= 0:
        raise TimeoutError("combined startup exceeded deadline")
    owned.stdout.until(lambda raw: _ready_count(raw) >= 1, owned.budget, seconds=remaining)
    if owned.stdout.bytes().splitlines().count(b"uciok") != 1 or _ready_count(owned.stdout.bytes()) != 1:
        raise ValueError("startup UCI acknowledgements were duplicated")
    if _best_lines(owned.stdout.bytes()):
        raise ValueError("unsolicited bestmove before search")
    image_before = scope.image_snapshot(pid, native_sha256)
    startup = time.monotonic() - started
    before = scope.task_snapshot(pid)
    board = oracle.Board.from_fen()
    if not list(board.legal_moves()):
        raise ValueError("start position has no legal move")
    owned.send(b"position startpos\ngo wtime 1000 btime 1000 winc 0 binc 0\n")
    started_search = time.monotonic()
    deadline = started_search + owned.budget.left(search_seconds)
    samples, positive, identities, initial_ticks = [], set(), {}, {}
    for tid in before:
        try:
            evidence = peer_runtime._worker_evidence(pid, tid)
        except (FileNotFoundError, ProcessLookupError):
            continue
        if not evidence["cpus"] or not set(evidence["cpus"]).issubset(cpus):
            raise ValueError("observed thread escaped its CPU slot")
        identities[tid] = {"tid": tid, "start_ticks": evidence["start_ticks"],
                           "cpus": evidence["cpus"], "cpu_ticks": evidence["cpu_ticks_last"]}
        initial_ticks[tid] = evidence["cpu_ticks_first"]
    while not _best_lines(owned.stdout.bytes()):
        if owned.exited():
            raise ValueError("engine exited before a natural bestmove")
        if time.monotonic() >= deadline:
            raise TimeoutError("clocked diagnostic search exceeded its deadline")
        current = scope.task_snapshot(pid)
        row = {}
        for tid, item in current.items():
            try:
                evidence = peer_runtime._worker_evidence(pid, tid)
            except (FileNotFoundError, ProcessLookupError):
                continue
            mask = evidence["cpus"]
            if not mask or not set(mask).issubset(cpus):
                raise ValueError("observed thread escaped its CPU slot")
            ticks = evidence["cpu_ticks_last"]
            previous = identities.get(tid)
            if previous and (previous["start_ticks"] != evidence["start_ticks"] or ticks < previous["cpu_ticks"]):
                raise ValueError("observed thread identity or CPU ticks changed unexpectedly")
            initial = initial_ticks.setdefault(tid, evidence["cpu_ticks_first"])
            if ticks > initial:
                positive.add(tid)
            identities[tid] = {"tid": tid, "start_ticks": evidence["start_ticks"], "cpus": mask, "cpu_ticks": ticks}
            row[str(tid)] = {"state": item["state"], "cpu_ticks": ticks, "cpus": mask}
        if len(samples) < 256:
            samples.append({"elapsed_seconds": time.monotonic() - started_search, "tasks": row})
        time.sleep(.01)
    lines = _best_lines(owned.stdout.bytes())
    if len(lines) != 1:
        raise ValueError("clocked search did not emit exactly one bestmove")
    move = peer_runtime.checked_best(lines[0], board)
    ready = _ready_count(owned.stdout.bytes())
    owned.send(b"stop\nisready\n")
    owned.stdout.until(lambda raw: _ready_count(raw) >= ready + 1, owned.budget, seconds=5)
    if _ready_count(owned.stdout.bytes()) != ready + 1:
        raise ValueError("idle ready acknowledgement was duplicated")
    if len(_best_lines(owned.stdout.bytes())) != 1:
        raise ValueError("idle stop or ready produced an extra bestmove")
    image_after = scope.image_snapshot(pid, native_sha256)
    numa = _numa_summary(pid)
    return {"format": "rove4k-functional-uci-smoke-v1", "startup_seconds": startup,
            "clocked_search_seconds": time.monotonic() - started_search,
            "bestmove": move, "position": "startpos", "legal_bestmove": True,
            "startup_image": image_before, "post_search_image": image_after, "numa_mappings": numa,
            "observed_threads": [identities[key] for key in sorted(identities)],
            "positive_cpu_tids": sorted(positive), "search_samples": samples,
            "any_observed_cpu_progress": bool(positive),
            "non_leader_cpu_progress": any(tid != pid for tid in positive),
            "idle_stop_sent": True, "stop_support_required": False,
            "claims": {"complete_runtime_qualification": False,
                       "complete_worker_set": False, "search_causality": False,
                       "tt_address_provenance": False, "tt_only_residency": False,
                       "numa_remote_access": False, "scored_game_admitted": False}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--candidates-sha256", required=True)
    parser.add_argument("--profile", choices=("test-p16", "test-p192"), required=True)
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--placement", type=Path, required=True)
    parser.add_argument("--placement-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--wall-seconds", type=int, default=120)
    args = parser.parse_args(argv)
    placement_path = diagnostic_candidates._safe_input_path(args.placement)
    plan, _ = diagnostic_candidates.run.json_input(placement_path, args.placement_sha256)
    if (type(plan) is not dict or set(plan) not in ({"slot", "cgroup", "saved_ancestor_cpus"},
                                                    {"slot", "cgroup", "saved_ancestor_cpus", "saved_ancestor_nodes"})):
        raise ValueError("an exact pinned single-slot placement record is required")
    result = run_candidate(candidate_path=args.candidates, candidate_sha256=args.candidates_sha256,
                           profile=args.profile, artifact_id=args.artifact, slot=plan["slot"],
                           cgroup=plan["cgroup"], saved_ancestor_cpus=plan["saved_ancestor_cpus"],
                           saved_ancestor_nodes=plan.get("saved_ancestor_nodes"),
                           out=args.out, wall_seconds=args.wall_seconds)
    print(json.dumps({"report": str(args.out / "functional-runtime.json"),
                      "complete": result["complete"], "scored_game_admitted": False}, sort_keys=True))


if __name__ == "__main__":
    main()
