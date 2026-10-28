"""Own one bounded P16/P192 functional diagnostic and its cgroup lifetime.

This is a single-engine diagnostic, not the eleven-game cohort or a scored
league admission.  It creates one fresh cgroup under a separately delegated
root, retains the original owner through the actual UCI probe, and only asks
the existing cgroup manager to remove its original empty groups afterwards.
It does not reserve physical RAM, exclude other writers, or prove TT pages.
Original cgroup identities are held in memory; an abrupt supervisor death
does not provide a durable recovery record or authenticate a later owner.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import threading

sys.dont_write_bytecode = True
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from . import diagnostic_candidates, functional_uci_probe, peak_capacity, peak_probe_session, placement, topology
except ImportError:
    import diagnostic_candidates
    import functional_uci_probe
    import peak_capacity
    import peak_probe_session
    import placement
    import topology


class FunctionalSetupFailure(RuntimeError):
    """Retain original cgroup identities and the owner after partial setup."""

    def __init__(self, message, *, records, cleanup_errors, owner=None):
        super().__init__(message + "; original cgroups=" + repr(records) +
                         "; cleanup errors=" + repr(cleanup_errors))
        self.records = records
        self.cleanup_errors = cleanup_errors
        self.owner = owner


class FunctionalCleanupFailure(RuntimeError):
    """A diagnostic ended, but its original cgroup owner needs attention."""

    def __init__(self, message, *, errors, owner, original=None):
        super().__init__(message + "; original cgroups=" + repr(_records(owner.manager)) +
                         "; cleanup errors=" + repr(errors))
        self.errors = errors
        self.owner = owner
        self.original = original


def _records(manager):
    return [{"path": str(path), "device": device, "inode": inode}
            for path, device, inode in manager.created]


def _declared_overhead(workers):
    # Match run_candidate's limit exactly.  This is declared headroom, not a
    # measured upper bound or a reservation of physical memory.
    return max(768 << 20, workers * (16 << 20)) + (256 << 20)


class OwnedFunctionalProbe:
    """Keep the delegated cgroup owner alive while the pinned engine runs."""

    def __init__(self, *, manager, candidate_path, candidate_sha256, profile,
                 artifact_id, out, wall_seconds, slot, cgroup, saved_ancestor_cpus, saved_ancestor_nodes):
        self.manager = manager
        self.candidate_path, self.candidate_sha256 = candidate_path, candidate_sha256
        self.profile, self.artifact_id, self.out = profile, artifact_id, out
        self.wall_seconds, self.slot, self.cgroup = wall_seconds, slot, cgroup
        self.saved_ancestor_cpus = saved_ancestor_cpus
        self.saved_ancestor_nodes = saved_ancestor_nodes
        self._attempted = False
        self._running = False
        self._closed = False
        self.last_report = None

    @classmethod
    def create(cls, *, root, campaign, candidate_path, candidate_sha256,
               profile, artifact_id, out, wall_seconds=120):
        if sys.platform != "linux":
            raise RuntimeError("functional diagnostic requires Linux")
        if (profile not in ("test-p16", "test-p192") or type(wall_seconds) is not int or
                not 90 <= wall_seconds <= 300):
            raise ValueError("a bounded P16/P192 diagnostic is required")
        root = Path(root)
        if (not root.is_absolute() or ".." in root.parts or
                any(path.is_symlink() for path in (root, *root.parents)) or
                root.resolve(strict=True) != root):
            raise ValueError("original delegated root must be a real absolute non-symlink path")
        # Fail before any cgroup mutation for missing/changed candidates or an
        # existing/protected output. run_candidate repeats identity validation.
        output = diagnostic_candidates._safe_output_path(out)
        if any(output == parent or output.is_relative_to(parent)
               for parent in (Path("/sys"), Path("/proc"), Path("/dev"))):
            raise ValueError("diagnostic output cannot be inside kernel virtual filesystems")
        if not output.parent.is_dir():
            raise ValueError("diagnostic output parent must already exist")
        candidates, actual_digest = diagnostic_candidates.read_candidates(candidate_path, candidate_sha256, profile,
                                                                            allow_single=True)
        selected = [row for row in candidates if row["artifact"].id == artifact_id]
        if len(selected) != 1 or actual_digest != candidate_sha256:
            raise ValueError("one exact pinned candidate is required")
        artifact = selected[0]["artifact"]
        workers = 16 if profile == "test-p16" else 192
        cap = (16 if profile == "test-p16" else 192) << 30
        if (artifact.profile != profile or artifact.workers != workers or
                type(artifact.tt_bytes) is not int or not 0 < artifact.tt_bytes <= cap):
            raise ValueError("candidate TT and workers differ from the selected profile")
        original = peak_probe_session._require_delegated_root(root)
        snapshot = topology.Topology.snapshot_target(root, device=original.st_dev, inode=original.st_ino)
        if profile == "test-p16":
            slot = topology.plan_slots(snapshot, 8, 16, reserve_physical=0, max_slots=1, policy="default")[0]
            by_id = {cpu.id: cpu for cpu in snapshot.cpus}
            for core in slot.physical_cores:
                members = {cpu for cpu in slot.cpus if by_id[cpu].physical == core}
                if len(members) != 2 or any(set(by_id[cpu].siblings) != members for cpu in members):
                    raise ValueError("P16 requires mutually observed SMT siblings")
        else:
            slot = topology.plan_p192_slot(snapshot, policy="default")
        saved_cpus = list(snapshot.allowed_cpus)
        saved_nodes = list(snapshot.allowed_nodes)
        memory_max = placement._align_memory_extent(artifact.tt_bytes + _declared_overhead(workers),
                                                     os.sysconf("SC_PAGE_SIZE"))
        checked = peak_probe_session._require_delegated_root(root)
        if (checked.st_dev, checked.st_ino) != (original.st_dev, original.st_ino):
            raise ValueError("delegated root identity changed during preflight")
        try:
            manager = placement.CgroupSlots(root, campaign, root_identity=(original.st_dev, original.st_ino))
        except placement.CgroupSetupFailure as error:
            records = list(error.records)
            if error.unrecorded_path is not None:
                records.append({"path": error.unrecorded_path, "identity_unavailable": True})
            raise FunctionalSetupFailure(str(error), records=records,
                                         cleanup_errors=error.cleanup_errors, owner=error.owner) from error
        try:
            current_root = manager.root.stat()
            if (manager.root != root or root.is_symlink() or
                    (current_root.st_dev, current_root.st_ino) != (original.st_dev, original.st_ino)):
                raise ValueError("delegated root identity changed during creation")
            parent = manager.parent_record()
            live = topology.Topology.snapshot_target(manager.parent, device=parent["device"], inode=parent["inode"])
            if json.loads(json.dumps(live.to_record())) != json.loads(json.dumps(snapshot.to_record())):
                raise ValueError("created diagnostic topology differs from the delegated root")
            group = manager.create(slot, memory_bytes=memory_max)
            peak_capacity._require_empty(Path(group["path"]))
            return cls(manager=manager, candidate_path=candidate_path, candidate_sha256=candidate_sha256,
                       profile=profile, artifact_id=artifact_id, out=output, wall_seconds=wall_seconds,
                       slot=slot, cgroup=group, saved_ancestor_cpus=saved_cpus, saved_ancestor_nodes=saved_nodes)
        except BaseException as error:
            records = _records(manager)
            if isinstance(error, placement.CgroupSetupFailure) and error.unrecorded_path is not None:
                records.append({"path": error.unrecorded_path, "identity_unavailable": True})
            try:
                cleanup_errors = manager.close()
            except Exception as cleanup:
                cleanup_errors = [{"error": str(cleanup)}]
            raise FunctionalSetupFailure(str(error), records=records, cleanup_errors=cleanup_errors,
                                         owner=manager) from error

    def run(self):
        """Run the same owned process path used by functional_uci_probe CLI."""
        if self._closed or self._attempted or self._running:
            raise ValueError("a closed or already attempted diagnostic cannot be reused")
        if threading.current_thread() is not threading.main_thread():
            raise RuntimeError("owned signal handling requires the main thread")
        self._attempted = self._running = True
        try:
            self.last_report = functional_uci_probe.run_candidate(
                candidate_path=self.candidate_path, candidate_sha256=self.candidate_sha256,
                profile=self.profile, artifact_id=self.artifact_id, slot=self.slot.to_record(),
                cgroup=self.cgroup, saved_ancestor_cpus=self.saved_ancestor_cpus,
                saved_ancestor_nodes=self.saved_ancestor_nodes, out=self.out, wall_seconds=self.wall_seconds)
            return self.last_report
        except functional_uci_probe.FunctionalProbeFailure as error:
            self.last_report = error.report
            raise
        finally:
            self._running = False

    def close(self):
        """Remove only the manager's original empty cgroups; never signal a child."""
        if self._running:
            raise RuntimeError("diagnostic is still running")
        if self._closed:
            return []
        errors = self.manager.close()
        if not errors:
            self._closed = True
        return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--candidates-sha256", required=True)
    parser.add_argument("--profile", choices=("test-p16", "test-p192"), required=True)
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--wall-seconds", type=int, default=120)
    args = parser.parse_args(argv)
    owner = OwnedFunctionalProbe.create(root=args.root, campaign=args.campaign,
        candidate_path=args.candidates, candidate_sha256=args.candidates_sha256,
        profile=args.profile, artifact_id=args.artifact, out=args.out, wall_seconds=args.wall_seconds)
    try:
        report = owner.run()
    except BaseException as error:
        try:
            cleanup = owner.close()
        except BaseException as cleanup_error:
            raise FunctionalCleanupFailure("diagnostic failed and owned group cleanup failed",
                errors=[{"error": str(cleanup_error)}], owner=owner, original=error) from error
        if cleanup:
            raise FunctionalCleanupFailure("diagnostic failed and owned groups need attention",
                                           errors=cleanup, owner=owner, original=error) from error
        raise
    try:
        cleanup = owner.close()
    except BaseException as cleanup_error:
        raise FunctionalCleanupFailure("diagnostic completed but owned group cleanup failed",
            errors=[{"error": str(cleanup_error)}], owner=owner) from cleanup_error
    if cleanup:
        raise FunctionalCleanupFailure("diagnostic completed but owned groups need attention",
                                       errors=cleanup, owner=owner)
    print(json.dumps({"report": str(args.out / "functional-runtime.json"),
                      "complete": report["complete"], "scored_game_admitted": False}, sort_keys=True))


if __name__ == "__main__":
    main()
