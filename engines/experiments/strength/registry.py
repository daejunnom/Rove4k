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
    physical = 4 if artifact.profile == "test-p4" else 28
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
