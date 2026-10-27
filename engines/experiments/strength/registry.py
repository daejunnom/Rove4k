"""Measured artifact intake; size metadata alone never admits a league player."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location("rove_production", ROOT / "engines/scripts/production.py")
production = sys.modules.get(_spec.name)
if production is None:
    production = importlib.util.module_from_spec(_spec)
    sys.modules[_spec.name] = production
    _spec.loader.exec_module(production)

SHA = re.compile(r"^[0-9a-f]{64}$")
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,95}$")
CHECKS = ("reproduction", "size", "startup", "dependencies", "cleanup", "protocol", "legal_moves", "resources", "lifecycle", "placement")


def file_sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def identifier(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ValueError("invalid external job/artifact identifier")
    return value


def smt_runtime_evidence(report, artifact):
    """Recheck recorded host-bound SMT evidence without granting score admission.

    The receipt is an observation from the frozen driver, not a signature
    against a malicious external writer. A NUMA-map row can cover other data
    alongside TT pages, so this checker never asserts TT-only page placement.
    """
    result = {"profile": artifact.profile, "host_runtime_evidence_complete": False,
              "tt_overlapping_vma_pages_observed": False, "tt_only_pages_proven": False,
              "scored_game_placement_confirmed": False,
              "scope": "single peer and actual recorded CPU/policy observations; no scored game or TT-only NUMA claim"}

    def require(condition, message):
        if not condition:
            raise ValueError(message)

    def mapping_starts(rows, pointer, tt_bytes):
        require(type(pointer) is int and pointer > 0 and type(tt_bytes) is int and tt_bytes > 0
                and pointer + tt_bytes < 1 << 63 and isinstance(rows, list) and rows,
                "actual TT mapping identity is invalid")
        coverage, end, starts = pointer, pointer + tt_bytes, []
        for row in rows:
            start, stop, permissions = row["start"], row["end"], row["permissions"]
            require(type(start) is int and type(stop) is int and start <= coverage < stop
                    and isinstance(permissions, str) and len(permissions) >= 4
                    and permissions[:2] == "rw" and permissions[3] == "p",
                    "actual TT mapping does not provide contiguous private RW coverage")
            starts.append(start)
            coverage = min(end, stop)
            require(coverage < end or row is rows[-1], "extra mappings after TT coverage")
        require(coverage == end and len(starts) == len(set(starts)), "actual TT extent was not covered")
        return starts

    try:
        expected_cores, expected_workers = {"test-p16": (8, 16), "test-p192": (96, 192)}[artifact.profile]
        require(artifact.workers == expected_workers, "profile worker identity differs")
        topology, placement = report["topology"], report["placement"]
        rows = topology["cpus"]
        require(isinstance(rows, (list, tuple)) and rows, "actual topology rows missing")
        by_id = {row["id"]: row for row in rows}
        require(len(by_id) == len(rows) and all(type(cpu) is int and cpu >= 0 for cpu in by_id),
                "topology CPU identities invalid")
        cpus, nodes = placement["cpu_ids"], placement["memory_nodes"]
        require(isinstance(cpus, list) and len(cpus) == expected_workers and len(set(cpus)) == len(cpus)
                and all(type(cpu) is int and cpu in by_id for cpu in cpus), "CPU envelope identity differs")
        require(set(cpus) <= set(topology["allowed_cpus"]) and set(nodes) <= set(topology["allowed_nodes"]),
                "CPU or memory node outside actual allowed topology")
        require(artifact.profile != "test-p192" or set(cpus) == set(topology["allowed_cpus"]),
                "P192 did not use the entire allowed CPU envelope")
        chosen = [by_id[cpu] for cpu in cpus]
        groups = {}
        for row in chosen:
            key = row["socket"], row["core"]
            groups.setdefault(key, []).append(row)
        require(len(groups) == expected_cores and set(nodes) == {row["node"] for row in chosen},
                "observed core or node identities differ")
        require(artifact.profile != "test-p16" or len(nodes) == 1, "P16 slot spans NUMA nodes")
        for group in groups.values():
            members = {row["id"] for row in group}
            require(len(group) == 2 and all(set(row["siblings"]) == members for row in group),
                    "actual SMT sibling identity differs")

        sessions = report["sessions"]
        require([row["label"] for row in sessions] == ["cold", "warm", "active-quit", "active-eof"],
                "four owned runtime sessions are required")
        for session in sessions:
            owner, preexec, budget = session["owner"], session["preexec_placement"], session["runtime_budget"]
            require(owner["whole_sha256"] == artifact.sha256 and owner["runtime_native_sha256"] == artifact.native_sha256,
                    "session image identity differs")
            require(owner["pid"] == owner["pgid"] == owner["session"] == preexec["pid"]
                    and type(owner["start_ticks"]) is int and owner["start_ticks"] > 0,
                    "owned process identity differs")
            require(preexec["requested_cpus"] == preexec["effective_cpus"] == sorted(cpus)
                    and set(preexec["requested_nodes"]) == set(nodes)
                    and set(nodes) <= set(preexec["effective_allowed_nodes"]),
                    "actual pre-exec CPU or memory envelope differs")
            require(preexec["fallback"] is None and preexec["observed_policy"].get("available") is True,
                    "actual memory policy is unavailable or fell back")
            policy = preexec["observed_policy"]
            requested = preexec["requested_policy"]
            require(requested in ("inherit", "default", "interleave") and policy.get("mode") in (0, 2, 3, 4),
                    "unsupported actual memory policy")
            if requested in ("default", "interleave"):
                require(policy["mode"] == {"default": 0, "interleave": 3}[requested]
                        and (requested == "default" or set(policy.get("nodes", [])) == set(nodes)),
                        "actual memory policy differs from the explicit request")
            if artifact.profile == "test-p16":
                require(set(preexec["effective_allowed_nodes"]) == set(nodes)
                        or (policy.get("mode") in (2, 3) and set(policy.get("nodes", [])) == set(nodes)),
                        "P16 single-node memory policy was not observed")
            require(budget["profile"] == artifact.profile and budget["workers"] == artifact.workers
                    and budget["tt_bytes"] == artifact.tt_bytes
                    and budget["availability"]["effective_available_bytes"] >= budget["required_available_bytes"],
                    "actual resource preflight differs")
            expected_tt = {"test-p16": 16 << 30, "test-p192": 128 << 30}[artifact.profile]
            other = max(768 << 20, expected_workers * (16 << 20))
            require(artifact.tt_bytes == expected_tt and budget["other_peak_bytes"] == other
                    and budget["required_available_bytes"] == expected_tt + other + (256 << 20)
                    and budget["address_space_bytes"] == max(4 << 30, expected_tt + other)
                    and budget["effective_cpus"] == expected_workers
                    and type(budget["wall_seconds"]) is int and 60 <= budget["wall_seconds"] <= 600,
                    "profile-specific resource budget differs")
            cpu_soft = max(180, min(140, budget["wall_seconds"] - 10) * expected_workers)
            require(budget["cpu_seconds"] == [cpu_soft, cpu_soft + max(5, 2 * expected_workers)],
                    "profile-specific CPU budget differs")
            availability = budget["availability"]
            require(type(availability["host_available_bytes"]) is int and availability["host_available_bytes"] > 0
                    and isinstance(availability["cgroup_remaining_bytes"], list)
                    and all(type(value) is int and value >= 0 for value in availability["cgroup_remaining_bytes"])
                    and availability["effective_available_bytes"] == min(
                        [availability["host_available_bytes"], *availability["cgroup_remaining_bytes"]]),
                    "effective host/cgroup memory evidence differs")
            expected_limits = {"address_space": [budget["address_space_bytes"]] * 2,
                               "cpu": budget["cpu_seconds"]}
            require(preexec["runtime_limits"] == expected_limits, "actual child limits differ")
            for name, hard in (("address_space", budget["address_space_bytes"]), ("cpu", budget["cpu_seconds"][1])):
                for limits in (budget["parent_limits"][name], preexec["child_inherited_limits"][name]):
                    require(isinstance(limits, (list, tuple)) and len(limits) == 2 and all(
                        type(value) is int and (value == -1 or value >= hard) for value in limits),
                        "child increased inherited resource limits")
            require(session["image"]["native_sha256"] == artifact.native_sha256
                    and session["image"]["tt"]["mapping_extent_verified"] is True
                    and session["image"]["tt"]["tt_bytes"] == artifact.tt_bytes,
                    "actual runtime image or TT mapping differs")
            mapping_starts(session["image"]["tt"]["mappings"], session["image"]["tt"]["pointer"], artifact.tt_bytes)
            finish = session["finish"]
            require(type(finish["returncode"]) is int and finish["returncode"] == 0
                    and finish["readers_joined"] is True and finish["reaped"] is True
                    and finish["forced_cleanup"] is False
                    and finish["original_identity_retained_until_other_members_absent"] is True,
                    "normal session finish was not observed")
            require(session["cleanup"]["owned_group_absent"] is True and
                    session["cleanup"]["readers_joined"] is True and session["cleanup"]["forced_cleanup"] is False
                    and session["cleanup"]["settled_before_cleanup"] is True
                    and session["cleanup"]["reaped"] is True and not session["cleanup"]["errors"],
                    "owned session cleanup is incomplete")

        require(any(session["finish"]["leader_exited_with_other_members"] is True and
                    session["finish"]["other_members_observed"] for session in sessions[2:]),
                "delayed cleanup ownership was not actually observed")

        cold = sessions[0]
        search = cold["searches"][0]
        workers = search["worker_affinity_evidence"]
        require(search["worker_affinity_evidence_complete"] is True and len(workers) == expected_workers,
                "complete worker identity and CPU evidence missing")
        tids = {row["tid"] for row in workers}
        require(len(tids) == expected_workers and tids == set(search["worker_ids"]) == set(search["positive_cpu_worker_ids"]),
                "worker identities differ from actual search")
        for row in workers:
            require(type(row["start_ticks"]) is int and row["start_ticks"] > 0
                    and row["cpus"] == sorted(cpus)
                    and type(row["cpu_ticks_first"]) is int and type(row["cpu_ticks_last"]) is int
                    and row["cpu_ticks_last"] > row["cpu_ticks_first"] >= 0,
                    "worker affinity or CPU ticks lack stable evidence")

        observation = cold["post_go_tt_numa"]
        owner = {key: cold["owner"][key] for key in ("pid", "pgid", "session", "start_ticks")}
        require(observation["owner"] == owner and observation["tt_bytes"] == artifact.tt_bytes
                and observation["tt_pointer"] == cold["image"]["tt"]["pointer"],
                "post-GO TT mapping is not bound to the live owner")
        vmas = observation["tt_overlapping_vmas"]
        starts = mapping_starts(observation["tt_mappings"], observation["tt_pointer"], artifact.tt_bytes)
        require(isinstance(vmas, list) and len(vmas) == len(starts) and
                sorted(row["mapping_start"] for row in vmas) == sorted(starts) == observation["matching_vma_starts"],
                "NUMA observations do not match the TT-overlapping mappings")
        for row in vmas:
            raw = row["raw"].split()
            require(raw and re.fullmatch(r"[0-9a-fA-F]+", raw[0]) is not None
                    and int(raw[0], 16) == row["mapping_start"], "NUMA row mapping identity differs")
            parsed = {int(node): int(pages) for node, pages in re.findall(r"\bN(\d+)=(\d+)", row["raw"])}
            require({int(node): pages for node, pages in row["node_pages"].items()} == parsed,
                    "NUMA page counts differ from the observed row")
        actual_nodes = {int(node) for row in vmas for node, pages in row["node_pages"].items() if pages > 0}
        require(observation["all_mapping_starts_observed"] is True and actual_nodes
                and sorted(actual_nodes) == observation["observed_page_nodes"] and actual_nodes <= set(nodes),
                "post-GO TT-overlapping VMA page observations are incomplete or outside the slot")
        result["host_runtime_evidence_complete"] = True
        result["tt_overlapping_vma_pages_observed"] = True
    except (KeyError, TypeError, ValueError, IndexError) as error:
        result["reason"] = str(error)
    return result


@dataclass(frozen=True)
class Artifact:
    id: str
    family: str
    path: Path
    purpose: str
    profile: str
    workers: int
    tt_bytes: int
    entry_bytes: int
    representation: str
    full: bool
    sha256: str
    whole_bytes: int
    native_sha256: str

    @classmethod
    def from_record(cls, value):
        return cls(**{**value, "path": Path(value["path"])})

    def __post_init__(self):
        identifier(self.id)
        if self.family not in (*"ABCDEF", "ice4", "c4ke"):
            raise ValueError("unknown active engine family")
        profile = production.resource_profile(self.profile)
        if self.purpose != profile.purpose or self.workers != profile.workers:
            raise ValueError("artifact purpose/worker count differs from resource profile")
        if type(self.entry_bytes) is not int or self.entry_bytes <= 0:
            raise ValueError("actual TT entry size is required")
        if self.tt_bytes != profile.layout(self.entry_bytes).bytes:
            raise ValueError("artifact TT extent differs from actual profile layout")
        if self.representation not in ("source-jit", "packed-native", "self-contained-elf", "configurable-native"):
            raise ValueError("unknown artifact representation")
        if type(self.full) is not bool or type(self.whole_bytes) is not int or self.whole_bytes <= 0:
            raise ValueError("full policy and actual positive whole size required")
        if not SHA.fullmatch(self.sha256) or not SHA.fullmatch(self.native_sha256):
            raise ValueError("whole and native SHA-256 identities required")
        if not self.path.is_absolute():
            raise ValueError("artifact path must be absolute")

    def verify_bytes(self):
        if self.path.is_symlink() or not self.path.is_file():
            raise ValueError("whole artifact must be an existing ordinary file")
        if self.path.stat().st_size != self.whole_bytes or file_sha(self.path) != self.sha256:
            raise ValueError("artifact bytes differ from the registered identity")

    def identity(self):
        return {"id": self.id, "family": self.family, "purpose": self.purpose, "profile": self.profile,
                "workers": self.workers, "tt_bytes": self.tt_bytes, "entry_bytes": self.entry_bytes,
                "representation": self.representation, "full": self.full,
                "sha256": self.sha256, "whole_bytes": self.whole_bytes, "native_sha256": self.native_sha256}


def admit_to_test_league(artifact, receipt, receipt_sha256):
    """Read a bound qualification receipt, not an unverified build-summary flag.

    A qualification driver must produce these observations from its real
    source/runtime checks. This intake validates their identity and scope; it
    does not manufacture observations or upgrade a narrow receipt.
    """
    artifact.verify_bytes()
    if artifact.purpose != "test" or not artifact.full:
        raise ValueError("only full TEST artifacts enter this score cohort")
    if artifact.representation == "configurable-native" or artifact.whole_bytes > 4096:
        raise ValueError("test league admits only qualified complete 4KiB files")
    raw = receipt.read_bytes()
    if not SHA.fullmatch(receipt_sha256) or hashlib.sha256(raw).hexdigest() != receipt_sha256:
        raise ValueError("qualification receipt identity changed")
    report = json.loads(raw)
    if report.get("format") != "rove4k-qualification-v1" or report.get("complete") is not True or report.get("failures") != []:
        raise ValueError("completed qualification contract is missing")
    if report.get("division") != "general4k" or report.get("artifact") != artifact.identity():
        raise ValueError("receipt does not bind the exact TEST artifact/resource/policy")
    checks = report.get("checks", {})
    if any(checks.get(name) is not True for name in CHECKS):
        raise ValueError("a required qualification check is missing or failed")
    observed = report.get("observations", {})
    startup = observed.get("startup_ms")
    if type(startup) not in (int, float) or not math.isfinite(startup) or not 0 <= startup <= 60000:
        raise ValueError("actual complete startup must be within 60 seconds")
    for name, expected in (("workers", artifact.workers), ("positive_cpu_workers", artifact.workers),
                           ("tt_bytes", artifact.tt_bytes), ("runtime_native_sha256", artifact.native_sha256)):
        if observed.get(name) != expected:
            raise ValueError("runtime qualification observation differs: " + name)
    if artifact.profile in ("test-p16", "test-p192"):
        raise ValueError("SMT TEST runtime and placement evidence is not yet admitted")
    physical = {"test-p4": 4, "test-p28": 28}.get(artifact.profile)
    if physical is None:
        raise ValueError("unknown TEST placement profile")
    if observed.get("physical_cores") != physical or observed.get("logical_cpus") != physical:
        raise ValueError("a named physical TEST slot has not actually been observed")
    if observed.get("temporary_cleanup_while_live") is not True:
        raise ValueError("cleanup during live usable startup has not been observed")
    if observed.get("nbrq_replay") is not True:
        raise ValueError("external promotion replay has not been qualified")
    if artifact.family in "ABCDEF" and observed.get("nbrq_generation") is not True:
        raise ValueError("Rove full baseline requires actual N/B/R/Q generation")
    if artifact.family not in "ABCDEF" and observed.get("promotion_generation_policy") not in ("queen-only", "NBRQ"):
        raise ValueError("peer promotion policy must be declared, not silently equated to Rove")
    return {"artifact": artifact.identity(), "receipt": str(receipt), "receipt_sha256": receipt_sha256,
            "qualified": True, "scope": "TEST general4k; not TCEC W256 playing-strength evidence"}
