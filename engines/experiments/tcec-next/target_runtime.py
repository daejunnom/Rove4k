"""Bind a source-JIT submission to a GitHub Actions Ubuntu 22 image.

The Ubuntu 24 source producer remains the canonical factory authority.  This
consumer replays the existing production admission and binds the same payload
to actual system-GCC-11 compiler evidence; it never edits the producer's native
expectation.  A reference permits a later runtime observation, not qualification.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from hashlib import sha256
import importlib.util
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import subprocess
import sys
import zipfile

sys.dont_write_bytecode = True
_EXECUTING_CODE = sys._getframe().f_code
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FORMAT = "rove4k.target-runtime-reference.v1"
SEAL_FORMAT = "rove4k.source-bundle-seal.v1"
COMPILER_FORMAT = "rove4k.profile-compiler.v1"
SELF = "engines/experiments/tcec-next/target_runtime.py"
SHA = re.compile(r"[0-9a-f]{64}\Z")
MAX_BUNDLE = 128 << 20
MAX_MEMBER = 16 << 20
MAX_TOOL = 128 << 20
_VALIDATED = object()
COMPILER_ENV = ("GCC_EXEC_PREFIX", "COMPILER_PATH", "LIBRARY_PATH", "CPATH",
                "C_INCLUDE_PATH", "CPLUS_INCLUDE_PATH", "OBJC_INCLUDE_PATH",
                "LD_PRELOAD", "LD_LIBRARY_PATH")


def require(value, detail):
    if not value:
        raise ValueError(detail)


def pin(data):
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


def _member(name):
    require(isinstance(name, str) and name and "\\" not in name and ":" not in name and "\0" not in name,
            "normalized source-bundle member required")
    pure = PurePosixPath(name)
    require(not pure.is_absolute() and all(part not in ("", ".", "..") for part in name.split("/")),
            "source-bundle member escaped its relative namespace")
    lower = [p.casefold() for p in pure.parts]
    forbidden = {".git", ".ssh", ".aws", "node_modules", "dist", "dist-server", "coverage",
                 "models", "checkpoints", ".cache"}
    require(not any(p in forbidden or p == ".env" or p.startswith(".env.") for p in lower),
            "protected/heavy input is not a source-bundle member")
    require(lower[-1] not in ("inventory.json", "package-lock.json", "id_rsa", "id_ed25519", "authorized_keys")
            and not any(word in lower[-1] for word in
                ("credential", "serviceaccount", "service-account", "service_account", "ssh_key", "api_key")),
            "protected input is not a source-bundle member")
    return name


INPUT_PATH = "engines/scripts/production_input.py"


def input_reader():
    name = "rove4k_production_input"
    module = sys.modules.get(name)
    if module is None:
        spec = importlib.util.spec_from_file_location(name, ROOT / INPUT_PATH)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    module = module.cached_module()
    require(Path(module.__file__).absolute() == (ROOT / INPUT_PATH).absolute(),
            "production input reader is outside the named source closure")
    return module


def _read_file(path, *, limit, allow_hardlinks):
    return input_reader().read_regular(path, limit=limit, allow_hardlinks=allow_hardlinks)


def _regular(path, *, limit=MAX_MEMBER):
    return _read_file(path, limit=limit, allow_hardlinks=False)


def _normalized_source(path):
    data = _regular(path).replace(b"\r\n", b"\n")
    require(b"\r" not in data, "lone CR in target authority source")
    return data


def _named(path, name, *, limit=MAX_MEMBER):
    path = Path(path)
    require(path.name == name, "explicit named evidence required: " + name)
    return _regular(path, limit=limit)


def _identity(value):
    require(isinstance(value, dict) and set(value) == {"bytes", "sha256"}
            and type(value["bytes"]) is int and 0 <= value["bytes"] <= MAX_BUNDLE
            and isinstance(value["sha256"], str) and SHA.fullmatch(value["sha256"]),
            "bounded SHA-256 file identity required")
    return value


@dataclass(frozen=True)
class CIContext:
    repository: str
    head_sha: str
    run_id: str
    run_attempt: str

    def __post_init__(self):
        require(isinstance(self.repository, str) and re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", self.repository),
                "explicit workflow repository required")
        require(isinstance(self.head_sha, str) and re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", self.head_sha),
                "explicit workflow head SHA required")
        require(all(isinstance(v, str) and re.fullmatch(r"[1-9][0-9]*", v)
                    for v in (self.run_id, self.run_attempt)), "explicit workflow run and attempt required")

    @classmethod
    def from_environment(cls, environment=None):
        """Read only named, non-secret workflow identity fields from live CI."""
        environment = os.environ if environment is None else environment
        require(environment.get("GITHUB_ACTIONS") == "true", "live GitHub Actions context required")
        result = cls(*(environment.get(key) for key in
                       ("GITHUB_REPOSITORY", "GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT")))
        _ci(result, environment=environment)
        return result

    def to_record(self):
        return dict(repository=self.repository, head_sha=self.head_sha,
                    run_id=self.run_id, run_attempt=self.run_attempt)


def _checkout_head():
    result = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10, check=False)
    require(result.returncode == 0 and len(result.stdout) <= 128 and len(result.stderr) <= 4096,
            "current source checkout HEAD is unavailable")
    return result.stdout.decode("ascii").strip()


def _ci(expected, *, environment=None):
    # The caller obtains this from its live trusted workflow.  A receipt is
    # never allowed to choose its own expected head/run/bundle authority.
    require(type(expected) is CIContext, "live expected CIContext must be supplied separately")
    environment = os.environ if environment is None else environment
    require(environment.get("GITHUB_ACTIONS") == "true", "target reference is GitHub Actions CI-only")
    current = dict(zip(("repository", "head_sha", "run_id", "run_attempt"),
                      (environment.get(key) for key in
                       ("GITHUB_REPOSITORY", "GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT"))))
    require(current == expected.to_record(), "expected CIContext differs from live workflow identity")
    require(_checkout_head() == expected.head_sha, "checked-out git HEAD differs from live workflow GITHUB_SHA")
    return expected.to_record()


def _archive(data):
    require(len(data) <= MAX_BUNDLE, "source bundle exceeds bounded input")
    members = {}
    total = 0
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        require(len(archive.infolist()) <= 10000, "too many source-bundle entries")
        for item in archive.infolist():
            name = item.filename[:-1] if item.is_dir() else item.filename
            _member(name)
            mode = stat.S_IFMT(item.external_attr >> 16)
            require(mode in (0, stat.S_IFREG, stat.S_IFDIR) and not item.flag_bits & 1,
                    "source bundle cannot contain links, devices or encrypted members")
            if item.is_dir():
                continue
            require(name not in members and item.file_size <= MAX_MEMBER,
                    "duplicate or oversized source-bundle member")
            total += item.file_size
            require(total <= MAX_BUNDLE, "expanded source bundle exceeds bound")
            value = archive.read(item)
            require(len(value) == item.file_size, "source-bundle member extent differs")
            members[name] = value
    require(members, "source bundle is empty")
    return members


def _compiler_module():
    path = HERE / "profile_compiler.py"
    spec = importlib.util.spec_from_file_location("target_runtime_compiler_contract", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _frozen_value(value):
    """Type-preserving JSON nodes, with no references to caller-owned dicts."""
    if value is None:
        return ["none"]
    if type(value) in (str, bool, int):
        return [type(value).__name__, value]
    if type(value) is float:
        require(math.isfinite(value), "admission snapshot requires finite values")
        return ["float", value]
    if isinstance(value, Path):
        return ["path", type(value).__name__, str(value)]
    if type(value) in (list, tuple):
        return [type(value).__name__, [_frozen_value(item) for item in value]]
    if type(value) is dict:
        pairs = [[_frozen_value(key), _frozen_value(item)] for key, item in value.items()]
        pairs.sort(key=lambda pair: json.dumps(pair[0], sort_keys=True))
        return ["dict", pairs]
    if is_dataclass(value) and not isinstance(value, type):
        return ["dataclass", type(value).__qualname__,
                [[field.name, _frozen_value(getattr(value, field.name))] for field in fields(value)]]
    raise ValueError("admission contains an unsupported execution-field value")


def _admission_snapshot(admitted):
    require(is_dataclass(admitted) and not isinstance(admitted, type),
            "complete admission dataclass instance required")
    # Walking fields, rather than a hand-maintained subset, includes every
    # current/future execution choice.  In particular program/source/native,
    # wrapper ownership, complete source proof and full policy are all bound.
    record = [[field.name, _frozen_value(getattr(admitted, field.name))] for field in fields(admitted)]
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _source_facts(admitted, build, verify, compiler):
    build = Path(build)
    require(build.is_absolute() and build.resolve() == build and not build.is_symlink(),
            "original owned absolute source-build layout required")
    raw = _named(build / "build.json", "build.json", limit=8 << 20)
    record = json.loads(raw)
    require(admitted.representation == "source-jit" and admitted.full is True,
            "target reference accepts only a full source-JIT submission")
    actual = (verify.admit_d_build(record, build, "D-source-jit") if admitted.family == "D"
              else verify.admit_c_build(record, build))
    admission = _admission_snapshot(actual)
    require(type(actual) is type(admitted) and admission == _admission_snapshot(admitted),
            "supplied admission differs from fresh strict source admission")
    selected = compiler.admit(build, verify)
    whole = verify.checked_artifact(build, actual.program,
        {key: actual.expected["whole_" + key] for key in ("bytes", "sha256")})
    boundary = actual.expected["header_bytes"]
    require(type(boundary) is int and 0 < boundary < len(whole), "submission header extent differs")
    if actual.family == "D":
        files = {name: "shipping-inputs/" + name for name in selected.files}
    else:
        files = {"main.c": "main.c"}
    return {"family": actual.family, "profile": actual.profile_id, "full": True,
            "representation": "source-jit", "build_root": str(build), "input_manifest": pin(raw),
            "program": str(Path(actual.program).relative_to(build)) if Path(actual.program).is_absolute() else actual.program,
            "submission": pin(whole), "header": pin(whole[:boundary]), "payload": pin(whole[boundary:]),
            "source_files": {name: pin(value) for name, value in selected.files.items()},
            "source_paths": files, "flags": list(selected.flags), "units": list(selected.units),
            "assertions": list(selected.assertions), "old_expected_contract": dict(actual.expected),
            "execution_admission": pin(admission.encode())}, raw, selected


def _source_host():
    fields = {}
    for line in _regular(Path("/etc/os-release").resolve(), limit=16384).decode().splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            if key in ("ID", "VERSION_ID"):
                fields[key] = value.strip('"')
    require(fields == {"ID": "ubuntu", "VERSION_ID": "24.04"},
            "source seal must be made by the actual Ubuntu24 producer")
    return fields


def _absolute_layout_path(value):
    require(isinstance(value, str) and value.startswith("/") and value != "/"
            and "\\" not in value and ":" not in value and "\0" not in value
            and all(part not in ("", ".", "..") for part in value.split("/")[1:]),
            "exact normalized absolute Linux restore path required")
    return PurePosixPath(value)


def validate_restore_layout(seal, *, runner_temp_root):
    """Validate transport metadata; filesystem creation/link checks stay with its owner."""
    layout = seal.get("restore_layout")
    require(isinstance(layout, dict) and set(layout) == {"runner_temp_root", "output_root", "builds"},
            "explicit restore_layout metadata is required for transport")
    require(runner_temp_root is not None, "live RUNNER_TEMP root must be supplied separately")
    live = _absolute_layout_path(str(runner_temp_root))
    original = _absolute_layout_path(layout["runner_temp_root"])
    output = _absolute_layout_path(layout["output_root"])
    require(live == original and original in output.parents,
            "restore output must remain under the exact original live RUNNER_TEMP root")
    profiles = seal.get("profiles")
    require(isinstance(profiles, list) and profiles, "restore layout requires explicit source profiles")
    builds = {}
    paths = []
    for entry in profiles:
        require(isinstance(entry, dict), "restore profile must be a mapping")
        prefix = _member(entry.get("archive_prefix"))
        path = _absolute_layout_path(entry.get("build_root"))
        require(prefix not in builds and path not in paths and output in path.parents,
                "restore profile roots must be unique children of their source output")
        require(not any(path in old.parents or old in path.parents for old in paths)
                and not any(prefix.startswith(old + "/") or old.startswith(prefix + "/") for old in builds),
                "restore build roots/archive prefixes must not overlap")
        builds[prefix] = str(path)
        paths.append(path)
    require(isinstance(layout["builds"], dict) and layout["builds"] == builds,
            "restore build mapping differs from sealed original profile roots")
    return {"runner_temp_root": str(original), "output_root": str(output),
            "builds": dict(sorted(builds.items()))}


def build_source_seal(bundle, entries, *, verify, ci_context, restore_layout=None):
    """Seal a caller-created ZIP; entries are (admitted, build, archive_prefix).

    Every archived file must correspond to a file under one of these explicit
    owned build roots.  No directory scan, extraction, compiler or engine runs.
    The CI producer writes the returned record as source-seal.json.
    """
    context = _ci(ci_context)
    source_host = _source_host()
    bundle = Path(bundle)
    require(bundle.name == "source-bundle.zip", "explicit source-bundle.zip required")
    data = _regular(bundle, limit=MAX_BUNDLE)
    members = _archive(data)
    compiler = _compiler_module()
    profiles, roots = [], {}
    for admitted, build, prefix in entries:
        _member(prefix)
        require(prefix not in roots, "duplicate source-build archive prefix")
        facts, _, _ = _source_facts(admitted, build, verify, compiler)
        facts["archive_prefix"] = prefix
        profiles.append(facts)
        roots[prefix] = Path(build)
    require(profiles and len({(p["family"], p["profile"]) for p in profiles}) == len(profiles),
            "one source bundle entry per family/profile required")
    for name, value in members.items():
        matches = [(prefix, root) for prefix, root in roots.items() if name.startswith(prefix + "/")]
        require(len(matches) == 1, "bundle contains an unowned source-build member")
        prefix, root = matches[0]
        require(_regular(root / name[len(prefix) + 1:]) == value, "archive differs from the actual source build")
    seal = {"format": SEAL_FORMAT, "ci_context": context, "producer": source_host,
            "bundle_format": "zip", "bundle": pin(data),
            "members": {name: pin(value) for name, value in sorted(members.items())}, "profiles": profiles}
    if restore_layout is not None:
        seal["restore_layout"] = json.loads(json.dumps(restore_layout))
        validate_restore_layout(seal, runner_temp_root=os.environ.get("RUNNER_TEMP"))
    _sealed_source(seal, data, context)
    for entry in profiles:
        prefix = entry["archive_prefix"]
        for name in ("build.json", entry["program"], *entry["source_paths"].values()):
            require(prefix + "/" + name in members, "source bundle omitted a required submission/source member")
    return seal


def _sealed_source(seal, bundle, expected_ci):
    require(seal.get("format") == SEAL_FORMAT and seal.get("ci_context") == expected_ci
            and seal.get("producer") == {"ID": "ubuntu", "VERSION_ID": "24.04"}
            and seal.get("bundle_format") == "zip", "source seal context/producer differs")
    require(_identity(seal.get("bundle")) == pin(bundle), "raw source-bundle identity differs")
    members = _archive(bundle)
    require(seal.get("members") == {name: pin(value) for name, value in sorted(members.items())},
            "source-bundle members differ from its seal")
    if "restore_layout" in seal:
        validate_restore_layout(seal, runner_temp_root=os.environ.get("RUNNER_TEMP"))
    return members


def current_system_context(compiler):
    require(sys.platform == "linux" and platform.machine() == "x86_64", "actual Linux x86-64 target runtime host required")
    require(not any(os.environ.get(name) for name in COMPILER_ENV),
            "compiler redirection environment is not admitted")
    path = shutil.which("cc")
    require(path is not None, "source-JIT cc is absent from PATH")
    return compiler.system_descriptor(Path(path).resolve())


def _source_binding(admitted, build, *, verify, source_bundle, source_seal, expected_ci):
    context = _ci(expected_ci)
    reader_source = input_reader().source_identity()
    own_source = _regular(Path(__file__).resolve()).replace(b"\r\n", b"\n")
    require(compile(own_source, __file__, "exec", dont_inherit=True) == _EXECUTING_CODE,
            "target reference validator changed after its executing module was compiled")
    seal_raw = _named(source_seal, "source-seal.json")
    bundle_raw = _named(source_bundle, "source-bundle.zip", limit=MAX_BUNDLE)
    seal = json.loads(seal_raw)
    members = _sealed_source(seal, bundle_raw, context)
    compiler = _compiler_module()
    facts, manifest_raw, selected = _source_facts(admitted, Path(build), verify, compiler)
    matches = [entry for entry in seal.get("profiles", []) if
               (entry.get("family"), entry.get("profile")) == (facts["family"], facts["profile"])]
    require(len(matches) == 1, "source seal has no unique selected family/profile")
    entry = matches[0]
    prefix = _member(entry.get("archive_prefix"))
    require({key: value for key, value in entry.items() if key != "archive_prefix"} == facts,
            "source seal does not bind this exact admitted submission/header/source/flags/layout")
    required = {"build.json", facts["program"], *facts["source_paths"].values()}
    selected_members = {name[len(prefix) + 1:]: value for name, value in members.items()
                        if name.startswith(prefix + "/")}
    require(required <= set(selected_members), "sealed source build omitted a required input")
    for name, value in selected_members.items():
        require(_regular(verify.artifact_file(Path(build), _member(name))) == value,
                "sealed build member differs from actual input")
    return ({"source_context": context, "source_bundle": pin(bundle_raw), "source_seal": pin(seal_raw),
             "source_provenance_tools": {SELF: pin(own_source), INPUT_PATH: pin(reader_source)}, "source_profile": facts},
            selected, manifest_raw, compiler)


def source_bundle_binding(admitted, build, *, verify, source_bundle, source_seal, expected_ci):
    """Compiler-side source/context preflight; no target/native map is produced."""
    binding, _, _, _ = _source_binding(admitted, build, verify=verify,
        source_bundle=source_bundle, source_seal=source_seal, expected_ci=expected_ci)
    return binding


def _system_input(path):
    path = Path(path)
    require(path.is_absolute(), "absolute target compiler input required")
    _member(str(path).lstrip("/"))
    resolved = path.resolve(strict=True)
    require(resolved == path and any(root == path or root in path.parents for root in
                (Path("/usr"), Path("/lib"), Path("/lib64"), Path("/bin"))),
            "target compiler input escaped installed system roots")
    # Installed tool/library hard links are ordinary inputs, unlike mutable
    # evidence aliases.  Their exact resolved content is pinned before runtime.
    return _read_file(path, limit=MAX_TOOL, allow_hardlinks=True)


def _command_records(report, root):
    require(report.get("host_cleanup") == {"unsettled_commands": 0, "errors": []},
            "target compiler owner has not settled")
    rows = report.get("commands")
    require(isinstance(rows, list) and rows, "actual owned compiler commands required")
    by_kind = {}
    for index, row in enumerate(rows, 1):
        require(row.get("started") is True and row.get("terminal") is True and row.get("reaped") is True
                and row.get("returncode") == 0 and row.get("forced_cleanup") is False
                and row.get("owned_group_absent") is True
                and row.get("other_group_members_before_reap") == []
                and row.get("original_identity_retained_until_other_members_absent") is True,
                "compiler command did not retain and naturally settle its original group")
        kind = row.get("kind")
        require(isinstance(kind, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]*", kind) and kind not in by_kind,
                "unique named compiler commands required")
        for pipe in ("stdout", "stderr"):
            expected = row.get(pipe, {})
            path = (root / ("tool-" + str(index) + "-" + kind)).with_suffix("." + pipe)
            require(expected.get("path") == str(path) and
                    {key: expected.get(key) for key in ("bytes", "sha256")} == pin(_regular(path)),
                    "compiler raw pipe identity differs")
        by_kind[kind] = (index, row)
    return by_kind


@dataclass(frozen=True, init=False)
class TargetRuntimeReference:
    family: str
    profile: str
    native_path: Path
    _native_bytes: int
    _native_sha256: str
    _record: str
    _inputs: tuple
    _admission: str
    _build_root: str
    _admission_type: type

    def __init__(self, token, *, family, profile, native_path, native_pin, record, inputs=(),
                 admission_snapshot=None, build_root=None, admission_type=None):
        require(token is _VALIDATED, "target reference must pass compiler/source validation")
        require(isinstance(admission_snapshot, str) and isinstance(build_root, str)
                and isinstance(admission_type, type) and is_dataclass(admission_type),
                "validated immutable admission and build root required")
        for key, value in (("family", family), ("profile", profile), ("native_path", native_path),
                           ("_native_bytes", native_pin["bytes"]), ("_native_sha256", native_pin["sha256"]),
                           ("_record", json.dumps(record, sort_keys=True)), ("_inputs", tuple(inputs)),
                           ("_admission", admission_snapshot), ("_build_root", build_root),
                           ("_admission_type", admission_type)):
            object.__setattr__(self, key, value)

    @property
    def native_pin(self):
        return {"bytes": self._native_bytes, "sha256": self._native_sha256}

    def to_record(self):
        return json.loads(self._record)

    @property
    def compiler_context(self):
        return self.to_record()["compiler_context"]

    def assert_admission(self, admitted, build):
        """Bind the execution object, including nested mutable values, to this reference."""
        build = Path(build)
        require(build.is_absolute() and str(build) == self._build_root and build.resolve() == build,
                "execution build root differs from the validated target reference")
        require(type(admitted) is self._admission_type and _admission_snapshot(admitted) == self._admission,
                "execution admission differs from the validated immutable target reference")

    def revalidate(self, *, verify, expected_ci):
        """Repeat the whole authority check after the wrapper, without rebasing."""
        admitted, build, receipt, bundle, seal, command = self._inputs
        self.assert_admission(admitted, build)
        current = validate_target_runtime(admitted, build, receipt, verify=verify,
            source_bundle=bundle, source_seal=seal, expected_ci=expected_ci, compiler_argv=command)
        require(current.to_record() == self.to_record(),
                "target runtime reference changed between its before/post validations")
        return current


def validate_target_runtime(admitted, build, compiler_receipt, *, verify, source_bundle,
                            source_seal, expected_ci, compiler_argv=("cc",)):
    """Validate a reference before execution, without compiling/running an engine.

    A system22 compiler receipt additionally carries ``source_context`` (the
    exact CIContext), ``source_bundle`` and ``source_seal`` file pins, captured
    before compilation and checked unchanged by that future producer mode.
    SDK or historical receipts missing those fields deliberately fail closed.
    """
    require(tuple(compiler_argv) == ("cc",), "runtime reference follows the source-JIT's exact cc command")
    admission_snapshot = _admission_snapshot(admitted)
    binding, selected, manifest_raw, compiler = _source_binding(admitted, build, verify=verify,
        source_bundle=source_bundle, source_seal=source_seal, expected_ci=expected_ci)
    facts, context = binding["source_profile"], binding["source_context"]
    raw = _named(compiler_receipt, "compiler.json", limit=64 << 20)
    report = json.loads(raw)
    require(report.get("format") == COMPILER_FORMAT and report.get("complete") is True
            and report.get("engine_executed") is False and report.get("large_TT_allocated") is False
            and report.get("submission_qualified") is False and "error" not in report,
            "actual completed compile-only target receipt required")
    target = report.get("compiler_context", {})
    require(target.get("kind") == "ubuntu22-system", "SDK/compiler-only context is not runtime eligible")
    require(all(report.get(key) == binding[key] for key in
                ("source_context", "source_bundle", "source_seal", "source_provenance_tools", "source_profile")),
            "compiler receipt has no matching CI/source-bundle seal")
    require(json.loads(json.dumps(current_system_context(compiler))) == target
            and report.get("host", {}).get("libc") == ["glibc", "2.35"],
            "current source-JIT cc/host differs from the actual Ubuntu22 compiler context")
    root = Path(compiler_receipt).parent
    commands = _command_records(report, root)
    driver = target.get("driver", {})
    require(target.get("wrapper") == driver and driver.get("path") and
            {key: driver.get(key) for key in ("bytes", "sha256")} == pin(_system_input(driver["path"])),
            "current system compiler driver differs")
    version = commands.get("compiler-version")
    require(version is not None and version[1].get("command") == [driver["path"], "-dumpfullversion"]
            and _regular(root / ("tool-" + str(version[0]) + "-compiler-version.stdout")).decode().strip() == "11.4.0",
            "actual target compiler is not the separately observed GCC11.4.0")
    banner = commands.get("compiler-banner")
    require(banner is not None and banner[1].get("command") == [driver["path"], "--version"]
            and _regular(root / ("tool-" + str(banner[0]) + "-compiler-banner.stdout")).decode()
                == report.get("compiler_version") and "11.4.0" in report["compiler_version"],
            "actual target compiler banner differs from its owned output")
    tools = report.get("tools", {})
    expected_tools = (compiler.SELF, compiler.VERIFY_PATH, compiler.HOST_PATH, INPUT_PATH)
    require(set(tools) == set(expected_tools), "target compiler checker tool closure differs")
    for name in expected_tools:
        _member(name)
        data = _regular(root / "tools" / name)
        require(pin(data) == tools[name] and _normalized_source(ROOT / name) == data,
                "compiler checker frozen/current source differs")
    require(tools[compiler.HOST_PATH]["sha256"] == compiler.HOST_SHA, "literal compiler command owner differs")
    for name, expected in binding["source_provenance_tools"].items():
        require(pin(_regular(root / "tools" / name)) == expected
                and pin(_normalized_source(ROOT / name)) == expected,
                "optional compiler provenance helper changed before/post source capture")
    inputs = report.get("compiler_consumed_inputs")
    require(isinstance(inputs, dict) and driver["path"] in inputs, "actual compiler consumed-input closure absent")
    expected_inputs = {driver["path"]}
    before_indices = [version[0], banner[0]]
    after_indices = []
    roles = report.get("compiler_programs", {})
    require(isinstance(roles, dict) and set(roles) == {"cc1", "as", "ld", "collect2", "lto1"},
            "exact compiler subprogram roles required")
    require(report.get("compiler_programs_rechecked") is True, "compiler subprogram roles were not rechecked after compile")
    for query in ("cc1", "as", "ld", "collect2", "lto1"):
        kind = "compiler-program-" + query
        require(kind in commands and commands[kind][1].get("command") == [driver["path"], "-print-prog-name=" + query],
                "actual compiler subprogram query is absent")
        index = commands[kind][0]
        before_indices.append(index)
        answer = _regular(root / ("tool-" + str(index) + "-" + kind + ".stdout")).decode().strip()
        program = compiler.compiler_program(answer, system=True)
        role = roles[query]
        require(isinstance(role, dict) and set(role) == {"path", "bytes", "sha256"}
                and role["path"] == str(program) and str(program) in inputs
                and inputs[str(program)] == {key: role[key] for key in ("bytes", "sha256")},
                "compiler subprogram role changed or was not separately pinned")
        expected_inputs.add(str(program))
        after_kind = "compiler-program-recheck-" + query
        require(after_kind in commands and commands[after_kind][1].get("command") ==
                [driver["path"], "-print-prog-name=" + query], "post-compile compiler role query absent")
        after_index = commands[after_kind][0]
        after_indices.append(after_index)
        after_answer = _regular(root / ("tool-" + str(after_index) + "-" + after_kind + ".stdout")).decode().strip()
        require(compiler.compiler_program(after_answer, system=True) == program,
                "compiler subprogram role changed after compile")
    require(isinstance(report.get("profiles"), list) and len(report["profiles"]) == 1,
            "runtime reference requires one selected family/profile per compiler receipt")
    rows = [row for row in report["profiles"] if
            (row.get("family"), row.get("profile")) == (facts["family"], facts["profile"])]
    require(len(rows) == 1, "unique target compiler row required")
    row = rows[0]
    directory = root / (facts["family"] + "-" + facts["profile"])
    require(row.get("build") == str(Path(build)) and row.get("input_manifest") == pin(manifest_raw)
            and _named(directory / "input-build.json", "input-build.json", limit=8 << 20) == manifest_raw
            and row.get("sources") == facts["source_files"] and row.get("flags") == facts["flags"]
            and row.get("original_compiler_native") == facts["old_expected_contract"],
            "target compile does not bind the original source/profile/flags/whole manifest")
    for name, value in selected.files.items():
        require(_regular(directory / "source" / name) == value, "compiler frozen source differs from actual payload")
    require(row.get("engine_executed") is False and row.get("native_reproduced") is True
            and row.get("type_assertions_native_identical") is True
            and row.get("dependency_discovery_precedes_two_fresh_compiles") is True
            and row.get("cross_compiler_native_identity_required") is False,
            "target source/native/type reproduction is incomplete")
    if facts["family"] == "D":
        require(row.get("per_unit_dependency_discovery") == facts["units"],
                "D requires dependency discovery for every frozen compilation unit")
        for unit in facts["units"]:
            kind = "D-dependencies-" + unit
            dep = directory / ("unit-" + unit + ".d")
            require(kind in commands and commands[kind][1].get("cwd") == str(directory)
                    and commands[kind][1].get("command") == [driver["path"], *facts["flags"],
                        "-M", "-MF", str(dep), str(directory / "source" / unit)],
                    "D per-unit dependency command differs")
            before_indices.append(commands[kind][0])
            dependencies = compiler.dependency_paths(_regular(dep), owned_root=directory,
                input_roots=tuple(Path(p).resolve() for p in target["input_roots"]))
            expected_inputs.update(str(path) for path in dependencies if
                compiler.within(path, [Path(p).resolve() for p in target["input_roots"]]))
    attempts = row.get("attempts", [])
    require([a.get("directory") for a in attempts] == ["dependency-discovery", "first", "repeat", "target-types"],
            "actual independent target attempts/type gate are missing")
    image = None
    compile_indices = []
    for attempt in attempts:
        label = attempt["directory"]
        output = directory / label
        native = _regular(output / "x")
        require(attempt.get("native") == row.get("native") == pin(native), "actual target native repetitions differ")
        kind = facts["family"] + "-" + label
        require(kind in commands, "target compile command absent")
        index, command = commands[kind]
        compile_indices.append(index)
        expected = [driver["path"], *facts["flags"]]
        data = selected.files["main.c"]
        if label == "target-types":
            data += ("\n" + "\n".join(facts["assertions"]) + "\n").encode()
        if facts["family"] == "D":
            require(_regular(output / "main.c") == data, "D target type-gate source differs")
            expected += [str(output / "main.c"), str(directory / "source/start.S"),
                         "-Wl,-T," + str(directory / "source/image.ld"), "-o", "x"]
        else:
            require(_regular(root / ("tool-" + str(index) + "-" + kind + ".stdin")) == data,
                    "target compiler stdin/type assertions differ")
        expected += ["-MD", "-MF", str(output / "dependencies.d"), "-Wl,-t"]
        require(command.get("cwd") == str(output) and command.get("command") == expected,
                "actual target compiler command/flags differ")
        dependencies = compiler.dependency_paths(_regular(output / "dependencies.d"),
            owned_root=directory, input_roots=tuple(Path(p).resolve() for p in target["input_roots"]))
        trace = _regular(root / ("tool-" + str(index) + "-" + kind + ".stdout"))
        roots = [*(Path(p).resolve() for p in target["input_roots"]), root]
        for line in trace.decode().splitlines():
            candidate = Path(line.strip())
            if candidate.is_absolute():
                candidate = candidate.resolve()
                require(compiler.within(candidate, roots), "target link trace escaped compiler/owned input roots")
                if candidate.is_file():
                    dependencies.add(candidate)
        require(sorted(map(str, dependencies)) == sorted(attempt.get("dependencies", [])),
                "target dependency closure differs from the actual compiler output")
        expected_inputs.update(str(path) for path in dependencies if
            compiler.within(path, [Path(p).resolve() for p in target["input_roots"]]))
        image = native
    require(compile_indices == sorted(compile_indices) and len(set(compile_indices)) == 4
            and max(before_indices) < compile_indices[0]
            and min(after_indices) > compile_indices[-1],
            "target compiler before/discovery/compile/type/post command chronology differs")
    require(set(inputs) == expected_inputs,
            "compiler consumed-input set has missing dependencies or unrelated extra paths")
    for name in sorted(expected_inputs):
        require(_identity(inputs[name]) == pin(_system_input(name)),
                "target compiler/header/link input changed after compile")
    require(compiler.elf_abi(image, verify) == row.get("elf"), "actual target ELF/type/version evidence differs")
    native_path = directory / "first/x"
    require(facts["execution_admission"] == pin(admission_snapshot.encode())
            and _admission_snapshot(admitted) == admission_snapshot,
            "execution admission changed during target reference validation")
    record = {"format": FORMAT, "family": facts["family"], "profile": facts["profile"],
              "consumer_scope": "github-actions-ubuntu22-system",
              "representation": "source-jit", "full": True, "runtime_eligible": True,
              "runtime_executed": False, "runtime_qualified": False, "event_target_confirmed": False,
              "factory_replayed_on_target": False,
              "authority": "strict Ubuntu24 canonical producer and current named-base/resource/post/model/payload admission",
              "ci_context": context, "source_bundle": binding["source_bundle"], "source_seal": binding["source_seal"],
              "source_build": {"path": str(Path(build)), **pin(manifest_raw)},
              "submission": facts["submission"], "header": facts["header"], "payload": facts["payload"],
              "source_files": facts["source_files"], "flags": facts["flags"], "units": facts["units"],
              "original_build_expected_contract": facts["old_expected_contract"],
              "execution_admission": facts["execution_admission"],
              "compiler_receipt": {"path": str(Path(compiler_receipt)), **pin(raw)},
              "compiler_context": target, "compiler_tools": tools,
              "source_provenance_tools": binding["source_provenance_tools"],
              "reference_validator": {"path": SELF, **binding["source_provenance_tools"][SELF]},
              "target_native": {"path": str(native_path), **row["native"]}, "target_elf": row["elf"],
              "not_proven": ["engine execution", "startup/cleanup/protocol/resources", "physical placement",
                             "playing strength", "TCEC-specific hardware and compiler acceptance"]}
    return TargetRuntimeReference(_VALIDATED, family=facts["family"], profile=facts["profile"],
        native_path=native_path, native_pin=row["native"], record=record,
        inputs=(admitted, Path(build), Path(compiler_receipt), Path(source_bundle), Path(source_seal), tuple(compiler_argv)),
        admission_snapshot=admission_snapshot, build_root=str(Path(build)), admission_type=type(admitted))


def load_reference(path, admitted, build, compiler_receipt, **kwargs):
    """Revalidate the complete authority chain; a saved native map is not admission."""
    raw = _named(path, "target-runtime.json")
    reference = validate_target_runtime(admitted, build, compiler_receipt, **kwargs)
    require(json.loads(raw) == reference.to_record(), "saved target reference differs from current validated evidence")
    return reference
