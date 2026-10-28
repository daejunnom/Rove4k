"""Measured artifact intake; size metadata alone never admits a league player."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import stat
import sys

ROOT = Path(__file__).resolve().parents[3]
# A frozen registry must resolve its production contract from that same source
# root rather than a same-named module loaded earlier from another checkout.
_production_name = "rove_production_" + hashlib.sha256(str(ROOT).encode()).hexdigest()[:16]
_spec = importlib.util.spec_from_file_location(_production_name, ROOT / "engines/scripts/production.py")
production = sys.modules.get(_spec.name)
if production is None:
    production = importlib.util.module_from_spec(_spec)
    sys.modules[_spec.name] = production
    _spec.loader.exec_module(production)

SHA = re.compile(r"^[0-9a-f]{64}$")
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,95}$")
CHECKS = ("reproduction", "size", "startup", "dependencies", "cleanup", "protocol", "legal_moves", "resources", "lifecycle", "placement")
LEAGUE_PROFILE_OWNER = "engines/scripts/league_resource_profiles.py"
PEER_EXACT_P192_LAYOUT = "peer-p192-exact-3x2p33-v1"


def resource_profile(profile_id):
    """Resolve league profiles lazily so historical source seeds stay closed."""
    if profile_id not in ("test-p16", "test-p192"):
        return production.resource_profile(profile_id)
    spec = importlib.util.spec_from_file_location("rove_league_profiles", ROOT / LEAGUE_PROFILE_OWNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.resource_profile(production, profile_id)


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


def _unique_json_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate league-test receipt field")
        result[key] = value
    return result


def _reject_nonfinite_json(_value):
    raise ValueError("non-finite league-test receipt value")


def _finite_json_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("non-finite league-test receipt value")
    return number


def inspect_exact_peer_proposal(producer_record, producer_sha256):
    """Inspect experimental 3×2^33 source evidence without admitting an Artifact.

    Legacy power-of-two Artifact serialization and league admission stay
    unchanged. The exact producer has no emitted TT semantic or native
    reference proof yet, so even an inspected proposal is not executable
    diagnostic evidence and cannot qualify for scored play.
    """
    try:
        from . import peer_exact_proposal
    except ImportError:
        import peer_exact_proposal
    return peer_exact_proposal.inspect(producer_record, producer_sha256)


def smt_runtime_evidence(report, artifact, *, require_delayed_group_observation=True):
    """Recheck recorded host-bound SMT evidence without granting score admission.

    The receipt is an observation from the frozen driver, not a signature
    against a malicious external writer. A NUMA-map row can cover other data
    alongside TT pages, so this checker never asserts TT-only page placement.
    """
    result = {"profile": artifact.profile, "host_runtime_evidence_complete": False,
              "tt_overlapping_vma_pages_observed": False, "tt_only_pages_proven": False,
              "scored_game_placement_confirmed": False,
              "scope": "single engine and recorded CPU/policy observations; no scored game or TT-only NUMA claim"}

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
        require(type(require_delayed_group_observation) is bool,
                "explicit delayed-group observation policy required")
        if not require_delayed_group_observation:
            require(getattr(artifact, "family", None) in ("A", "B", "C", "E", "F"),
                    "delayed-group exception is for Rove diagnostics only")
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
                and all(type(cpu) is int and cpu in by_id for cpu in cpus)
                and type(nodes) is list and all(type(node) is int and node >= 0 for node in nodes),
                "CPU envelope identity differs")
        require(set(cpus) <= set(topology["allowed_cpus"]) and set(nodes) <= set(topology["allowed_nodes"]),
                "CPU or memory node outside actual allowed topology")
        require(artifact.profile != "test-p192" or set(cpus) == set(topology["allowed_cpus"]),
                "P192 did not use the entire allowed CPU envelope")
        chosen = [by_id[cpu] for cpu in cpus]
        require(all(type(row[key]) is int and row[key] >= 0 for row in chosen for key in ("socket", "core", "node")),
                "topology identities must be nonnegative integers")
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
        availability_observations = []
        require([row["label"] for row in sessions] == ["cold", "warm", "active-quit", "active-eof"],
                "four owned runtime sessions are required")
        for session in sessions:
            owner, preexec, budget = session["owner"], session["preexec_placement"], session["runtime_budget"]
            require(owner["whole_sha256"] == artifact.sha256 and owner["runtime_native_sha256"] == artifact.native_sha256,
                    "session image identity differs")
            require(all(type(value) is int and value > 0 for value in
                        (owner["pid"], owner["pgid"], owner["session"], preexec["pid"]))
                    and owner["pid"] == owner["pgid"] == owner["session"] == preexec["pid"]
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
            require(requested in ("inherit", "default", "interleave") and type(policy.get("mode")) is int
                    and policy.get("mode") in (0, 2, 3, 4),
                    "unsupported actual memory policy")
            if requested in ("default", "interleave"):
                require(policy["mode"] == {"default": 0, "interleave": 3}[requested]
                        and (requested == "default" or set(policy.get("nodes", [])) == set(nodes)),
                        "actual memory policy differs from the explicit request")
            if artifact.profile == "test-p16":
                require(set(preexec["effective_allowed_nodes"]) == set(nodes)
                        or (policy.get("mode") in (2, 3) and set(policy.get("nodes", [])) == set(nodes)),
                        "P16 single-node memory policy was not observed")
            require(budget["profile"] == artifact.profile and type(budget["workers"]) is int
                    and budget["workers"] == artifact.workers and type(budget["tt_bytes"]) is int
                    and budget["tt_bytes"] == artifact.tt_bytes,
                    "actual resource preflight differs")
            # Available-memory/headroom measurements are snapshots, not a
            # reliable admission or runtime-success condition. Preserve what
            # was observed without making their presence or value a gate.
            availability = budget.get("availability")
            estimated_required = budget.get("required_available_bytes")
            require(estimated_required is None or type(estimated_required) is int,
                    "invalid available-memory estimate format")
            if availability is not None:
                require(type(availability) is dict, "invalid available-memory observation format")
                for field in ("host_available_bytes", "effective_available_bytes"):
                    value = availability.get(field)
                    require(value is None or type(value) is int, "invalid available-memory value format")
                remaining = availability.get("cgroup_remaining_bytes")
                require(remaining is None or (type(remaining) is list and
                        all(type(value) is int for value in remaining)),
                        "invalid cgroup-memory observation format")
            availability_observations.append({"label": session["label"],
                "availability": availability, "estimated_required_available_bytes": estimated_required})
            expected_tt = resource_profile(artifact.profile).layout(artifact.entry_bytes).bytes
            other = max(768 << 20, expected_workers * (16 << 20))
            require(artifact.tt_bytes == expected_tt and type(budget["other_peak_bytes"]) is int
                    and budget["other_peak_bytes"] == other and type(budget["address_space_bytes"]) is int
                    and budget["address_space_bytes"] == max(4 << 30, expected_tt + other)
                    and type(budget["effective_cpus"]) is int and budget["effective_cpus"] == expected_workers
                    and type(budget["wall_seconds"]) is int and 60 <= budget["wall_seconds"] <= 600,
                    "profile-specific resource budget differs")
            cpu_soft = max(180, min(140, budget["wall_seconds"] - 10) * expected_workers)
            require(type(budget["cpu_seconds"]) is list and all(type(value) is int for value in budget["cpu_seconds"])
                    and budget["cpu_seconds"] == [cpu_soft, cpu_soft + max(5, 2 * expected_workers)],
                    "profile-specific CPU budget differs")
            expected_limits = {"address_space": [budget["address_space_bytes"]] * 2,
                               "cpu": budget["cpu_seconds"]}
            actual_limits = preexec["runtime_limits"]
            require(type(actual_limits) is dict and set(actual_limits) == set(expected_limits) and
                    all(type(actual_limits[name]) is list and len(actual_limits[name]) == 2 and
                        all(type(value) is int for value in actual_limits[name]) for name in expected_limits) and
                    actual_limits == expected_limits, "actual child limits differ")
            for name, hard in (("address_space", budget["address_space_bytes"]), ("cpu", budget["cpu_seconds"][1])):
                for limits in (budget["parent_limits"][name], preexec["child_inherited_limits"][name]):
                    require(isinstance(limits, (list, tuple)) and len(limits) == 2 and all(
                        type(value) is int and (value == -1 or value >= hard) for value in limits),
                        "child increased inherited resource limits")
            require(session["image"]["native_sha256"] == artifact.native_sha256
                    and session["image"]["tt"]["mapping_extent_verified"] is True
                    and type(session["image"]["tt"]["tt_bytes"]) is int
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

        if require_delayed_group_observation:
            require(any(session["finish"]["leader_exited_with_other_members"] is True and
                        session["finish"]["other_members_observed"] for session in sessions[2:]),
                    "delayed cleanup ownership was not actually observed")

        cold = sessions[0]
        search = cold["searches"][0]
        workers = search["worker_affinity_evidence"]
        require(search["worker_affinity_evidence_complete"] is True and len(workers) == expected_workers,
                "complete worker identity and CPU evidence missing")
        require(all(type(row.get("tid")) is int and row["tid"] > 0 for row in workers)
                and all(type(tid) is int and tid > 0 for tid in search["worker_ids"])
                and all(type(tid) is int and tid > 0 for tid in search["positive_cpu_worker_ids"]),
                "worker IDs must be positive integers")
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
        require(observation["owner"] == owner and type(observation["tt_bytes"]) is int
                and observation["tt_bytes"] == artifact.tt_bytes
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
        result["availability_observations"] = availability_observations
    except (KeyError, TypeError, ValueError, IndexError, AttributeError) as error:
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
    # Absent from legacy identities. This identifies a layout, not a verified
    # implementation, reference build, runtime qualification or scored player.
    layout_id: str | None = None

    @classmethod
    def from_record(cls, value):
        if "layout_id" in value and value["layout_id"] is None:
            raise ValueError("legacy artifact identity must omit layout_id")
        return cls(**{**value, "path": Path(value["path"])})

    def __post_init__(self):
        identifier(self.id)
        if self.family not in (*"ABCDEF", "ice4", "c4ke"):
            raise ValueError("unknown active engine family")
        profile = resource_profile(self.profile)
        if (self.purpose != profile.purpose or type(self.workers) is not int or
                self.workers != profile.workers or type(self.tt_bytes) is not int):
            raise ValueError("artifact purpose/worker count differs from resource profile")
        if type(self.entry_bytes) is not int or self.entry_bytes <= 0:
            raise ValueError("actual TT entry size is required")
        if self.layout_id is None:
            if self.tt_bytes != profile.layout(self.entry_bytes).bytes:
                raise ValueError("artifact TT extent differs from actual profile layout")
        elif (type(self.layout_id) is not str or self.layout_id != PEER_EXACT_P192_LAYOUT or
              self.family not in ("ice4", "c4ke") or self.profile != "test-p192" or
              self.purpose != "test" or type(self.workers) is not int or self.workers != 192 or
              type(self.entry_bytes) is not int or self.entry_bytes != 8 or
              type(self.tt_bytes) is not int or self.tt_bytes != 192 << 30 or
              self.representation != "source-jit" or self.full is not True):
            raise ValueError("explicit peer P192 TT layout contract differs")
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
        result = {"id": self.id, "family": self.family, "purpose": self.purpose, "profile": self.profile,
                "workers": self.workers, "tt_bytes": self.tt_bytes, "entry_bytes": self.entry_bytes,
                "representation": self.representation, "full": self.full,
                "sha256": self.sha256, "whole_bytes": self.whole_bytes, "native_sha256": self.native_sha256}
        if self.layout_id is not None:
            result["layout_id"] = self.layout_id
        return result


def admit_to_test_league(artifact, receipt, receipt_sha256):
    """Read a bound qualification receipt, not an unverified build-summary flag.

    A qualification driver must produce these observations from its real
    source/runtime checks. This intake validates their identity and scope; it
    does not manufacture observations or upgrade a narrow receipt.
    """
    return _check_test_receipt(artifact, receipt, receipt_sha256, diagnostic_only=False)


def inspect_league_test_receipt(artifact, receipt, receipt_sha256, *, smt_evidence_path=None,
                                smt_evidence_sha256=None, expected_runtime_sha256=None,
                                expected_source_sha256=None):
    """Inspect a v2 receipt; separate SMT pins do not authenticate the host."""
    smt_inputs = (smt_evidence_path, smt_evidence_sha256, expected_runtime_sha256, expected_source_sha256)
    return _check_test_receipt(artifact, receipt, receipt_sha256, diagnostic_only=True, smt_inputs=smt_inputs)


def _inspection_path(value, name):
    try:
        path = Path(value)
    except (TypeError, ValueError) as error:
        raise ValueError("invalid inspection input path") from error
    blocked = {"node_modules", "dist", "dist-server", "build", "coverage", "models", "checkpoints", ".cache",
               ".aws", ".ssh", ".npmrc", "id_rsa", "id_ed25519"}
    parts = [part.casefold() for part in path.parts]
    if (not path.is_absolute() or path.name != name or ".." in path.parts or
            any(part in blocked or part.startswith(".env") or
                any(word in part for word in ("credential", "service-account", "service_account", "serviceaccount",
                                             "api_key", "api-key", "access_key", "access-key", "ssh_key",
                                             "secret", "password")) or part == "token" or part.startswith("token.") or
                part.endswith("_token") or part.endswith("-token") for part in parts)):
        raise ValueError("inspection input is not an allowed absolute path")
    return path


def _read_inspection_file(value, digest, name, limit, *, hash_only=False, expected_size=None):
    """Read one pinned ordinary file without following path links."""
    path = _inspection_path(value, name)
    if type(digest) is not str or not SHA.fullmatch(digest):
        raise ValueError("independent inspection SHA-256 pin required")
    try:
        chain = (path, *path.parents)
        before_chain = [part.lstat() for part in chain]
        reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        if (any(stat.S_ISLNK(item.st_mode) or getattr(item, "st_file_attributes", 0) & reparse
                for item in before_chain) or path.resolve(strict=True) != path):
            raise ValueError("inspection input must not traverse links or parent escapes")
        before = before_chain[0]
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        with os.fdopen(os.open(path, flags), "rb") as stream:
            opened = os.fstat(stream.fileno())
            if (not stat.S_ISREG(before.st_mode) or not stat.S_ISREG(opened.st_mode) or
                    before.st_nlink != 1 or opened.st_nlink != 1 or
                    (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino) or
                    not 0 < opened.st_size <= limit or
                    (expected_size is not None and opened.st_size != expected_size)):
                raise ValueError("SMT observation is not a bounded ordinary file")
            if hash_only:
                hasher, count = hashlib.sha256(), 0
                while True:
                    block = stream.read(1 << 20)
                    if not block:
                        break
                    count += len(block)
                    if count > limit:
                        raise ValueError("inspection input exceeds its pinned size")
                    hasher.update(block)
                raw, actual_hash = None, hasher.hexdigest()
            else:
                raw = stream.read(limit + 1)
                count, actual_hash = len(raw), hashlib.sha256(raw).hexdigest()
            after = os.fstat(stream.fileno())
            if (count != opened.st_size or count > limit or
                    (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns) !=
                    (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns)):
                raise ValueError("SMT observation changed during reading")
            after_chain = [part.lstat() for part in chain]
            if (any((left.st_dev, left.st_ino, left.st_mode, getattr(left, "st_file_attributes", 0)) !=
                    (right.st_dev, right.st_ino, right.st_mode, getattr(right, "st_file_attributes", 0))
                    for left, right in zip(before_chain, after_chain)) or path.resolve(strict=True) != path):
                raise ValueError("inspection path changed during reading")
    except OSError as error:
        raise ValueError("cannot read owned inspection input") from error
    if actual_hash != digest:
        raise ValueError("inspection input identity changed")
    parent = before_chain[1]
    return path, raw, (parent.st_dev, parent.st_ino)


def _read_smt_evidence(receipt, path, digest, expected_parent_identity):
    """Read only the bounded, independently pinned sibling observation file."""
    receipt = _inspection_path(receipt, "qualification.json")
    path = _inspection_path(path, "smt-observation.json")
    if path.parent != receipt.parent:
        raise ValueError("independently pinned sibling SMT observation required")
    _, raw, parent_identity = _read_inspection_file(path, digest, "smt-observation.json", 16 << 20)
    if parent_identity != expected_parent_identity:
        raise ValueError("qualification and SMT observation parent identity differs")
    record = json.loads(raw, object_pairs_hook=_unique_json_fields, parse_constant=_reject_nonfinite_json,
                        parse_float=_finite_json_float)
    if type(record) is not dict:
        raise ValueError("SMT observation must be an object")
    return record


def _validate_rove_smt_binding(artifact, receipt, receipt_sha256, report, smt_inputs, receipt_parent_identity):
    path, digest, runtime_sha, source_sha = smt_inputs
    if (path is None or any(type(value) is not str or not SHA.fullmatch(value)
                            for value in (digest, runtime_sha, source_sha))):
        raise ValueError("independent SMT, runtime and source SHA-256 pins are required")
    record = _read_smt_evidence(receipt, path, digest, receipt_parent_identity)
    binding = report.get("smt_binding")
    fields = {"runtime_sha256", "source_sha256", "boot_id", "cgroup_path", "tt_symbol", "tt_symbol_evidence_sha256"}
    if type(binding) is not dict or set(binding) != fields:
        raise ValueError("complete Rove SMT binding required")
    boot, cgroup, symbol, symbol_sha = (binding["boot_id"], binding["cgroup_path"],
                                        binding["tt_symbol"], binding["tt_symbol_evidence_sha256"])
    if (binding["runtime_sha256"] != runtime_sha or binding["source_sha256"] != source_sha or
            report.get("source_sha256") != source_sha or
            type(report.get("evidence")) is not dict or type(report["evidence"].get("runtime")) is not dict or
            report["evidence"]["runtime"].get("sha256") != runtime_sha or
            type(boot) is not str or not re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", boot) or
            type(cgroup) is not str or not cgroup.startswith("/") or "\0" in cgroup or
            len(cgroup) > 4096 or any(part in (".", "..") for part in cgroup.split("/")) or
            type(symbol) is not str or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", symbol) or
            type(symbol_sha) is not str or not SHA.fullmatch(symbol_sha)):
        raise ValueError("SMT runtime, source or host binding differs")
    if (record.get("format") != "rove4k-owned-smt-observation-v1" or
            record.get("qualification_sha256") != receipt_sha256 or
            json.dumps(record.get("artifact"), sort_keys=True, separators=(",", ":"), allow_nan=False) !=
            json.dumps(artifact.identity(), sort_keys=True, separators=(",", ":"), allow_nan=False) or
            record.get("binding") != binding):
        raise ValueError("SMT observation does not bind the qualification and artifact")
    sessions = record.get("sessions")
    if type(sessions) is not list or len(sessions) != 4:
        raise ValueError("four bound SMT sessions are required")
    owners = set()
    for session in sessions:
        if (type(session) is not dict or type(session.get("owner")) is not dict or
                session["owner"].get("boot_id") != boot or session["owner"].get("cgroup_path") != cgroup or
                type(session.get("image")) is not dict or type(session["image"].get("tt")) is not dict or
                session["image"]["tt"].get("symbol") != symbol or
                session["image"]["tt"].get("symbol_evidence_sha256") != symbol_sha):
            raise ValueError("SMT session owner or TT symbol binding differs")
        pid, start = session["owner"].get("pid"), session["owner"].get("start_ticks")
        if type(pid) is not int or pid <= 0 or type(start) is not int or start <= 0 or (pid, start) in owners:
            raise ValueError("SMT sessions require distinct positive owner identities")
        owners.add((pid, start))
    result = smt_runtime_evidence(record, artifact, require_delayed_group_observation=False)
    if (result.get("host_runtime_evidence_complete") is not True or
            result.get("tt_overlapping_vma_pages_observed") is not True or
            result.get("scored_game_placement_confirmed") is not False):
        raise ValueError("SMT runtime observation is incomplete: " + str(result.get("reason", "unknown")))
    return result


def _check_test_receipt(artifact, receipt, receipt_sha256, *, diagnostic_only, smt_inputs=(None, None, None, None)):
    if diagnostic_only:
        _read_inspection_file(artifact.path, artifact.sha256, artifact.path.name, artifact.whole_bytes,
                              hash_only=True, expected_size=artifact.whole_bytes)
    else:
        artifact.verify_bytes()
    if artifact.purpose != "test" or not artifact.full:
        raise ValueError("only full TEST artifacts enter this score cohort")
    # Configurable upstream builds need their own original-source/native
    # provenance and runtime contract. A generic receipt cannot establish it.
    if artifact.representation == "configurable-native":
        raise ValueError("configurable native requires a separate original-source qualification")
    if not diagnostic_only and artifact.whole_bytes > 4096:
        raise ValueError("legacy scored intake requires a complete 4KiB file")
    if diagnostic_only:
        _, raw, receipt_parent_identity = _read_inspection_file(receipt, receipt_sha256, "qualification.json", 64 << 20)
    else:
        raw = receipt.read_bytes()
        if type(receipt_sha256) is not str or not SHA.fullmatch(receipt_sha256) or hashlib.sha256(raw).hexdigest() != receipt_sha256:
            raise ValueError("qualification receipt identity changed")
    report = json.loads(raw)
    if type(report) is not dict:
        raise ValueError("qualification receipt must be an object")
    if report.get("format") == "rove4k-qualification-v2":
        report = json.loads(raw, object_pairs_hook=_unique_json_fields, parse_constant=_reject_nonfinite_json,
                            parse_float=_finite_json_float)
    if report.get("complete") is not True or report.get("failures") != []:
        raise ValueError("completed qualification contract is missing")
    actual_identity = report.get("artifact")
    if report.get("format") == "rove4k-qualification-v2":
        try:
            identity_matches = (json.dumps(actual_identity, sort_keys=True, separators=(",", ":"), allow_nan=False) ==
                                json.dumps(artifact.identity(), sort_keys=True, separators=(",", ":"), allow_nan=False))
        except (TypeError, ValueError):
            identity_matches = False
    else:
        identity_matches = actual_identity == artifact.identity()
    if not identity_matches:
        raise ValueError("receipt does not bind the exact TEST artifact/resource/policy")
    checks = report.get("checks", {})
    receipt_format = report.get("format")
    if receipt_format == "rove4k-qualification-v1":
        if diagnostic_only:
            raise ValueError("explicit league-test v2 receipt required")
        if report.get("division") != "general4k" or artifact.whole_bytes > 4096:
            raise ValueError("legacy general4k qualification requires a complete 4KiB file")
        required_checks = CHECKS
    elif receipt_format == "rove4k-qualification-v2":
        if not diagnostic_only:
            raise ValueError("league-test receipt does not authorize scored admission")
        if (report.get("division") != "league-test" or report.get("qualification_scope") != "league-test" or
                artifact.family not in ("A", "B", "C", "E", "F") or
                report.get("functional_runtime_complete") is not True or report.get("test_qualified") is not True or
                report.get("release_qualified") is not False or report.get("event_target_confirmed") is not False or
                report.get("score_authorized") is not False):
            raise ValueError("explicit Rove league-test-only qualification is required")
        within_4k = artifact.whole_bytes <= 4096
        if (type(checks) is not dict or type(checks.get("size")) is not bool or
                checks["size"] is not within_4k or
                type(report.get("submission_size_within_4096")) is not bool or
                report["submission_size_within_4096"] is not within_4k):
            raise ValueError("recorded submission size differs from the complete file")
        required_checks = tuple(name for name in CHECKS if name != "size")
    else:
        raise ValueError("unknown qualification receipt format")
    if type(checks) is not dict or any(checks.get(name) is not True for name in required_checks):
        raise ValueError("a required qualification check is missing or failed")
    observed = report.get("observations", {})
    if receipt_format == "rove4k-qualification-v2" and type(observed) is not dict:
        raise ValueError("league-test observations must be an object")
    startup = observed.get("startup_ms")
    if type(startup) not in (int, float) or not math.isfinite(startup) or not 0 <= startup <= 60000:
        raise ValueError("actual complete startup must be within 60 seconds")
    for name, expected in (("workers", artifact.workers), ("positive_cpu_workers", artifact.workers),
                           ("tt_bytes", artifact.tt_bytes), ("runtime_native_sha256", artifact.native_sha256)):
        if (observed.get(name) != expected or
                (diagnostic_only and name != "runtime_native_sha256" and type(observed.get(name)) is not int)):
            raise ValueError("runtime qualification observation differs: " + name)
    is_smt = artifact.profile in ("test-p16", "test-p192")
    if is_smt and not diagnostic_only:
        raise ValueError("SMT TEST runtime and placement evidence is not yet admitted to scored play")
    if not is_smt and any(value is not None for value in smt_inputs):
        raise ValueError("SMT observation is only valid for P16/P192")
    physical = {"test-p4": 4, "test-p28": 28, "test-p16": 8, "test-p192": 96}.get(artifact.profile)
    logical = artifact.workers if is_smt else physical
    if physical is None:
        raise ValueError("unknown TEST placement profile")
    if (observed.get("physical_cores") != physical or observed.get("logical_cpus") != logical or
            (diagnostic_only and (type(observed.get("physical_cores")) is not int or
                                  type(observed.get("logical_cpus")) is not int))):
        raise ValueError("a named physical TEST slot has not actually been observed")
    if observed.get("temporary_cleanup_while_live") is not True:
        raise ValueError("cleanup during live usable startup has not been observed")
    if observed.get("nbrq_replay") is not True:
        raise ValueError("external promotion replay has not been qualified")
    if artifact.family in "ABCDEF" and observed.get("nbrq_generation") is not True:
        raise ValueError("Rove full baseline requires actual N/B/R/Q generation")
    if artifact.family not in "ABCDEF" and observed.get("promotion_generation_policy") not in ("queen-only", "NBRQ"):
        raise ValueError("peer promotion policy must be declared, not silently equated to Rove")
    if diagnostic_only:
        result = {"artifact": artifact.identity(), "receipt": str(receipt), "receipt_sha256": receipt_sha256,
                  "diagnostic_eligible": True, "score_authorized": False,
                  "scope": "league-test receipt inspection; no scored admission or release authorization"}
        if is_smt:
            observed_smt = _validate_rove_smt_binding(artifact, receipt, receipt_sha256, report, smt_inputs,
                                                      receipt_parent_identity)
            result.update(smt_evidence_sha256=smt_inputs[1], smt_observations_consistent=True,
                          host_origin_authenticated=False, source_origin_authenticated=False,
                          tt_symbol_origin_authenticated=False,
                          availability_observations=observed_smt.get("availability_observations", []),
                          scope=("bound SMT observation consistency only; host and source origin are not authenticated, "
                                 "no scored admission or release authorization"))
        return result
    return {"artifact": artifact.identity(), "receipt": str(receipt), "receipt_sha256": receipt_sha256,
            "qualified": True, "scope": "TEST general4k; not TCEC W256 playing-strength evidence"}
