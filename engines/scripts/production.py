"""C portfolio production inputs and resource arithmetic, without execution.

These contracts select a single family's source closure. They do not compile,
allocate a TT, change host placement, or turn a size observation into runtime
qualification. Existing exact producer pins remain the producer's authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from math import gcd
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Iterable, Mapping


MiB = 1 << 20
GiB = 1 << 30
SUBMISSION_LIMIT = 4096
_FAMILIES = "ABCDEF"
_REPRESENTATIONS = ("source-jit", "packed-native", "self-contained-elf")
_FORBIDDEN_PARTS = frozenset((".git", "node_modules", "dist", "dist-server",
                              "build", "coverage", "models", "checkpoints",
                              ".cache", "__pycache__"))
COMMON_RUNTIME_INPUTS = ("engines/scripts/elf-loader/loader.c",
                         "engines/scripts/elf-loader/loader.ld")
# Existing recipes explicitly reuse these transformations across family roots.
# This is not permission to import another family's algorithm-emitting core.
SHARED_COMPACT_TOOLS = frozenset((
    "engines/compact/tiny-a/pack_stream.py",
    "engines/compact/tiny-a/shipping_readonly.py",
    "engines/compact/tiny-a/stitch.py",
    "engines/compact/tiny-b/generate.py",
    *("engines/compact/tiny-entry-a/" + name for name in (
        "shipping_condition_bce.py", "shipping_constants_bce.py",
        "shipping_output_bce.py", "shipping_setter_phase_bce.py",
        "shipping_worker_epilogue_bce.py")),
))


def _integer(value: int, name: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _logical_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ValueError("input must be a repository-relative POSIX path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(p in ("", ".", "..") for p in value.split("/")):
        raise ValueError("input must be a normalized repository-relative path")
    if any(p.casefold() in _FORBIDDEN_PARTS or p.casefold() == ".env" or p.casefold().startswith(".env.")
           for p in path.parts):
        raise ValueError("input is outside the source-only production closure")
    lower = path.name.lower()
    if (lower in ("inventory.json", "package-lock.json") or
            any(word in lower for word in ("credential", "serviceaccount", "service-account",
                                          "service_account", "ssh_key", "api_key"))):
        raise ValueError("protected input is not a production source")
    return str(path)


@dataclass(frozen=True)
class TTLayout:
    entry_bytes: int
    bits: int
    entries: int
    bytes: int
    mask: int

    def __post_init__(self) -> None:
        _integer(self.entry_bytes, "entry_bytes", minimum=1)
        _integer(self.bits, "bits")
        _integer(self.entries, "entries", minimum=1)
        _integer(self.bytes, "bytes", minimum=1)
        _integer(self.mask, "mask")
        if self.bits >= 63:
            raise ValueError("TT index exceeds the admitted 64-bit object domain")
        if (self.entries != 1 << self.bits or self.bytes != self.entries * self.entry_bytes
                or self.mask != self.entries - 1):
            raise ValueError("inconsistent TT count, bytes, or mask")
        if self.bytes > (1 << 63) - 1:
            raise ValueError("TT byte extent exceeds signed pointer-difference range")

    def to_record(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class InitRange:
    worker: int
    begin: int
    end: int

    @property
    def entries(self) -> int:
        return self.end - self.begin


@dataclass(frozen=True)
class ResourceProfile:
    id: str
    purpose: str
    workers: int
    tt_cap_bytes: int
    control_threads: int = 1
    parallel_init: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id or self.purpose not in ("test", "submission"):
            raise ValueError("profile requires an id and test/submission purpose")
        _integer(self.workers, "workers", minimum=1)
        _integer(self.control_threads, "control_threads")
        _integer(self.tt_cap_bytes, "tt_cap_bytes", minimum=1)
        if self.workers > 512 or type(self.parallel_init) is not bool:
            raise ValueError("unsupported worker count or initialization policy")
        registered = globals().get("PROFILES", {}).get(self.id)
        if registered is not None and self != registered:
            raise ValueError("a registered resource profile cannot be redefined")

    @property
    def os_threads(self) -> int:
        """Requested search plus separately accounted control threads."""
        return self.workers + self.control_threads

    @property
    def minimum_counter_bits(self) -> int:
        """A completion count must represent workers, including W256 itself."""
        return self.workers.bit_length()

    def layout(self, entry_bytes: int, address_bits: int = 64) -> TTLayout:
        _integer(entry_bytes, "entry_bytes", minimum=1)
        if address_bits not in (32, 64):
            raise ValueError("only explicit 32/64-bit address arithmetic is admitted")
        object_limit = (1 << (address_bits - 1)) - 1
        if self.tt_cap_bytes > object_limit:
            raise ValueError("TT cap cannot fit the target address/object width")
        maximum = self.tt_cap_bytes // entry_bytes
        if not maximum:
            raise ValueError("TT cap cannot contain one entry")
        bits = maximum.bit_length() - 1
        entries = 1 << bits
        return TTLayout(entry_bytes, bits, entries, entries * entry_bytes, entries - 1)

    def init_ranges(self, layout: TTLayout, page_bytes: int = 4096,
                    base_address: int | None = None) -> tuple[InitRange, ...]:
        """Partition relative entry indexes for a page-aligned TT allocation.

        For 24-byte entries and 4KiB pages the unit is 512 entries (12KiB),
        rather than incorrectly dividing a page into a fractional entry.
        Zero ranges are explicit when a small fixture has fewer units than W.
        Omitted base_address establishes relative geometry only; the allocator
        must supply a page-aligned base before claiming physical first-touch
        separation. Passing its actual address checks that precondition.
        """
        _integer(page_bytes, "page_bytes", minimum=1)
        if base_address is not None:
            _integer(base_address, "base_address")
            if base_address % page_bytes:
                raise ValueError("TT base is not aligned to the initialization page size")
        if layout.bytes > self.tt_cap_bytes:
            raise ValueError("layout exceeds this profile's TT cap")
        unit = page_bytes // gcd(page_bytes, layout.entry_bytes)
        units = (layout.entries + unit - 1) // unit
        result = []
        for worker in range(self.workers):
            begin = min(layout.entries, (units * worker // self.workers) * unit)
            end = min(layout.entries, (units * (worker + 1) // self.workers) * unit)
            result.append(InitRange(worker, begin, end))
        return tuple(result)

    def to_record(self, entry_bytes: int) -> dict:
        layout = self.layout(entry_bytes)
        return {"id": self.id, "purpose": self.purpose, "workers": self.workers,
                "control_threads": self.control_threads, "os_threads": self.os_threads,
                "tt_cap_bytes": self.tt_cap_bytes, "tt_bits": layout.bits,
                "tt_entries": layout.entries, "tt_bytes": layout.bytes,
                "tt_entry_bytes": layout.entry_bytes, "tt_mask": layout.mask,
                "parallel_init": self.parallel_init,
                "init_partition_requires_page_aligned_base": True,
                "initialization_in_startup": True,
                "event_allocation_confirmed": False if self.purpose == "submission" else None}


PROFILES: Mapping[str, ResourceProfile] = MappingProxyType({
    "test-p4": ResourceProfile("test-p4", "test", 4, 128 * MiB),
    "test-p28": ResourceProfile("test-p28", "test", 28, 512 * MiB),
    "tcec-provisional": ResourceProfile("tcec-provisional", "submission", 256, 256 * GiB),
})


def resource_profile(profile_id: str) -> ResourceProfile:
    try:
        return PROFILES[profile_id]
    except (KeyError, TypeError):
        raise ValueError("unknown production resource profile: " + str(profile_id)) from None


@dataclass(frozen=True)
class EngineSpec:
    family: str
    source_root: str
    source_inputs: tuple[str, ...]
    entry_bytes: int

    def __post_init__(self) -> None:
        if self.family not in tuple(_FAMILIES):
            raise ValueError("active engine family must be C A-F")
        root = _logical_path(self.source_root)
        if root != f"engines/compact/tiny-entry-{self.family.lower()}":
            raise ValueError("engine source root does not match its family")
        if type(self.source_inputs) is not tuple or not self.source_inputs:
            raise ValueError("engine canonical source inputs must be an immutable tuple")
        for path in self.source_inputs:
            if not _logical_path(path).startswith(root + "/"):
                raise ValueError("cross-family canonical source input")
        _integer(self.entry_bytes, "entry_bytes", minimum=1)

    def layout(self, profile: ResourceProfile) -> TTLayout:
        return profile.layout(self.entry_bytes)

    @property
    def required_source_inputs(self) -> tuple[str, ...]:
        """HQ belongs only to D's explicit HQ feature, not every D payload."""
        return tuple(path for path in self.source_inputs
                     if not (self.family == "D" and PurePosixPath(path).name in ("hq.c", "hq.h")))


def _spec(family: str) -> EngineSpec:
    root = f"engines/compact/tiny-entry-{family.lower()}"
    if family == "D":
        sources = tuple(root + "/native/" + name for name in
                        ("tiny.h", "board.c", "search.c", "runtime.c", "start.S",
                         "image.ld", "hq.c", "hq.h"))
    else:
        sources = (root + "/engine.c",)
        if family == "E":
            sources += (root + "/model19.h",)
    return EngineSpec(family, root, sources, 16 if family == "D" else 24)


ENGINES: Mapping[str, EngineSpec] = MappingProxyType({family: _spec(family) for family in _FAMILIES})


def engine_spec(family: str) -> EngineSpec:
    try:
        return ENGINES[family]
    except (KeyError, TypeError):
        raise ValueError("unknown or retired production engine: " + str(family)) from None


@dataclass(frozen=True)
class SourceClosure:
    family: str
    engine_inputs: tuple[str, ...]
    tool_inputs: tuple[str, ...]
    test_inputs: tuple[str, ...] = ()

    @classmethod
    def validate(cls, spec: EngineSpec, *, engine_inputs: Iterable[str],
                 tool_inputs: Iterable[str] = (), test_inputs: Iterable[str] = (),
                 submission: bool = True) -> SourceClosure:
        groups = [tuple(_logical_path(p) for p in paths)
                  for paths in (engine_inputs, tool_inputs, test_inputs)]
        flat = tuple(p for group in groups for p in group)
        if len(set(flat)) != len(flat):
            raise ValueError("input cannot occupy more than one closure role")
        if any(p not in (*spec.source_inputs, *COMMON_RUNTIME_INPUTS) for p in groups[0]):
            raise ValueError("engine input is not this family's canonical source")
        if not set(spec.required_source_inputs).issubset(groups[0]):
            raise ValueError("canonical engine source or required model input is missing")
        for path in groups[1]:
            pure = PurePosixPath(path)
            prefixes = ("engines/scripts/", spec.source_root + "/",
                        "engines/experiments/tcec-next/", "engines/experiments/tcec-scope/",
                        f"engines/experiments/tiny-{spec.family.lower()}-submission/")
            is_model_input = (spec.family == "E" and
                              path in ("engines/model/e19.py", "engines/model/e19.json"))
            is_wrapper = path in (spec.source_root + "/bootstrap.py.in",
                                  spec.source_root + "/launcher.sh")
            diagnostic = (pure.name.startswith(("test", "check", "verify"))
                          or pure.stem in ("fresh", "algorithms"))
            is_tool = ((path.startswith(prefixes) or path in SHARED_COMPACT_TOOLS) and
                       (pure.suffix == ".py" or pure.name == "recipe.json"))
            if (not (is_tool or is_model_input or is_wrapper) or
                    diagnostic or any("rust" in part.lower() for part in pure.parts)):
                raise ValueError("tool closure accepts only C production helpers/configuration")
        for path in groups[2]:
            pure = PurePosixPath(path)
            if (not path.startswith(("engines/tests/", "engines/experiments/", spec.source_root + "/"))
                    or pure.suffix not in (".py", ".c", ".h", ".S", ".ld", ".json", ".pgn", ".txt")):
                raise ValueError("test input is outside the declared test roots")
        if submission and groups[2]:
            raise ValueError("submission source closure cannot include test inputs")
        return cls(spec.family, *groups)

    def to_record(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class InputPin:
    path: str
    role: str
    bytes: int
    sha256: str
    raw_bytes: int
    raw_sha256: str


@dataclass(frozen=True)
class ClosureSnapshot:
    family: str
    inputs: tuple[InputPin, ...]
    admission: str

    def to_record(self) -> dict:
        return {"family": self.family, "admission": self.admission,
                "normalization": "LF; lone CR rejected",
                "inputs": [asdict(pin) for pin in self.inputs]}


def snapshot_closure(root: Path, closure: SourceClosure, *,
                     expected: Mapping[str, str] | None = None) -> ClosureSnapshot:
    """Read admitted source paths only; observed hashes are not qualified pins.

    Passing expected requires a complete exact pin set. No path is added to or
    removed from that set to accommodate the current working tree.
    """
    root = Path(root).resolve(strict=True)
    # SourceClosure is public, so do not trust a direct dataclass constructor.
    closure = SourceClosure.validate(engine_spec(closure.family),
                                     engine_inputs=closure.engine_inputs,
                                     tool_inputs=closure.tool_inputs,
                                     test_inputs=closure.test_inputs,
                                     submission=False)
    groups = (("engine", closure.engine_inputs), ("tool", closure.tool_inputs),
              ("test", closure.test_inputs))
    paths = tuple(p for _, values in groups for p in values)
    if expected is not None and set(expected) != set(paths):
        raise ValueError("expected pins must exactly cover the admitted closure")
    pins = []
    for role, values in groups:
        for logical in values:
            logical = _logical_path(logical)
            path = root / logical
            for candidate in (path, *path.parents):
                if candidate == root:
                    break
                if candidate.is_symlink() or (hasattr(candidate, "is_junction") and candidate.is_junction()):
                    raise ValueError("source closure cannot follow links")
            resolved = path.resolve(strict=True)
            if not resolved.is_relative_to(root) or not resolved.is_file():
                raise ValueError("source closure escaped the checkout")
            _logical_path(resolved.relative_to(root).as_posix())
            if resolved.stat().st_nlink != 1:
                raise ValueError("source closure cannot read hard-linked inputs")
            raw = resolved.read_bytes()
            data = raw.replace(b"\r\n", b"\n")
            if b"\r" in data:
                raise ValueError("lone CR in source input: " + logical)
            digest = sha256(data).hexdigest()
            if expected is not None and expected[logical] != digest:
                raise ValueError("production input pin differs: " + logical)
            pins.append(InputPin(logical, role, len(data), digest, len(raw), sha256(raw).hexdigest()))
    return ClosureSnapshot(closure.family, tuple(pins),
                           "expected-pins-verified" if expected is not None else "observed-only")


@dataclass(frozen=True)
class HostAdmission:
    admitted: bool
    reason: str
    required_bytes: int
    available_bytes: int
    tt_bytes: int
    other_peak_bytes: int
    reserve_bytes: int

    def require(self) -> HostAdmission:
        if not self.admitted:
            raise ValueError(self.reason)
        return self

    def to_record(self) -> dict:
        return asdict(self)


def host_admission(profile: ResourceProfile, layout: TTLayout, available_bytes: int,
                   *, other_peak_bytes: int = 0, reserve_bytes: int = 256 * MiB) -> HostAdmission:
    """Pure execution gate: the caller supplies effective host/cgroup headroom."""
    _integer(available_bytes, "available_bytes")
    _integer(other_peak_bytes, "other_peak_bytes")
    _integer(reserve_bytes, "reserve_bytes")
    if layout.bytes > profile.tt_cap_bytes:
        raise ValueError("layout exceeds the profile TT cap")
    if layout != profile.layout(layout.entry_bytes):
        raise ValueError("execution layout does not match the requested resource profile")
    required = layout.bytes + other_peak_bytes + reserve_bytes
    if required > (1 << 63) - 1:
        raise ValueError("execution budget overflows the admitted address domain")
    admitted = required <= available_bytes
    reason = ("headroom admitted; execution has not been performed" if admitted else
              f"insufficient effective headroom before allocation: need {required}, have {available_bytes}")
    return HostAdmission(admitted, reason, required, available_bytes,
                         layout.bytes, other_peak_bytes, reserve_bytes)


def require_host_capacity(profile: ResourceProfile, layout: TTLayout,
                          available_bytes: int, **kwargs) -> HostAdmission:
    return host_admission(profile, layout, available_bytes, **kwargs).require()


@dataclass(frozen=True)
class ArtifactPlan:
    engine: EngineSpec
    profile: ResourceProfile
    representation: str
    cleanup: str
    full: bool = True

    def __post_init__(self) -> None:
        if self.representation not in _REPRESENTATIONS or self.cleanup not in ("private-path", "none"):
            raise ValueError("unsupported representation or entry cleanup policy")
        if type(self.full) is not bool:
            raise ValueError("full policy must be explicit")
        if self.representation == "self-contained-elf" and self.cleanup != "none":
            raise ValueError("self-contained ELF cannot unlink a pathname entry")

    @property
    def id(self) -> str:
        policy = "full" if self.full else "reduced"
        return f"{self.engine.family}-{self.profile.id}-{self.representation}-{policy}"

    def size_decision(self, whole_bytes: int, division: str) -> dict:
        """A size observation, never an assertion of full qualification."""
        _integer(whole_bytes, "whole_bytes")
        if division not in ("general4k", "elf4k"):
            raise ValueError("unknown tournament division")
        applicable = division == "general4k" or self.representation == "self-contained-elf"
        if not applicable:
            status = "not_applicable"
        elif whole_bytes <= SUBMISSION_LIMIT:
            status = "within_limit"
        else:
            status = "deferred_size" if division == "elf4k" else "blocked_size"
        return {"division": division, "status": status, "whole_bytes": whole_bytes,
                "limit_bytes": SUBMISSION_LIMIT, "full": self.full,
                "qualified": False, "runtime": "not-established-by-size-observation"}

    def to_record(self) -> dict:
        return {"id": self.id, "family": self.engine.family, "full": self.full,
                "resources": self.profile.to_record(self.engine.entry_bytes),
                "representation": self.representation, "entry_cleanup": self.cleanup}
