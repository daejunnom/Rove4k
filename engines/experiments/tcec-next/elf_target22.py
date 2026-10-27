#!/usr/bin/env python3
"""Seal an original full TEST ELF and observe that same image on Ubuntu 22.

The source-JIT seal/admission is not used. The exact original build path is
restored so its producer receipts retain their real path meaning. The target
never reruns the source factory, recompiles the production image or repacks it.
System GCC11 compiles only the existing source-bound rules probes. All target
observations are non-scoring; size, placement and event acceptance stay separate.
"""
from __future__ import annotations

import argparse
from fnmatch import fnmatchcase
from hashlib import sha256
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import sys
import time
import zipfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREFIX = "engines/experiments/tcec-next/"
SELF = PREFIX + "elf_target22.py"
PROFILE = PREFIX + "elf_profile.py"
TARGET = PREFIX + "target_runtime.py"
COMPILER = PREFIX + "profile_compiler.py"
TRANSPORT = "engines/scripts/production_source_bundle.py"
WORKFLOW = ".github/workflows/elf-profiles.yml"
FORMAT = "rove4k-original-elf-target22-v1"
SEAL_FORMAT = "rove4k-original-elf-seal-v1"
BUNDLE = "elf-bundle.zip"
SEAL = "elf-seal.json"
MAX_MEMBER = 16 << 20
MAX_SEAL = 8 << 20
MAX_BUNDLE = 128 << 20
MAX_FILES = 10000
WORK_SECONDS = 600
CLEANUP_SECONDS = 30
LOADER_ENV = ("LD_AUDIT", "LD_PROFILE", "LD_DEBUG", "LD_DEBUG_OUTPUT", "LD_ORIGIN_PATH",
              "LD_TRACE_LOADED_OBJECTS", "LD_CONFIG_FILE")
_EXECUTING_CODE = sys._getframe().f_code


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(data):
    require(type(data) is bytes, "immutable bytes required")
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def encoded(value):
    return (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()


def read(path, limit=MAX_MEMBER):
    path = Path(path)
    require(path.is_absolute() and ".." not in path.parts and type(limit) is int and limit > 0
            and os.name == "posix", "absolute bounded POSIX non-link input required")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    parent = os.open(path.anchor, flags)
    descriptor = None
    try:
        for part in path.parts[1:-1]:
            child = os.open(part, flags, dir_fd=parent)
            os.close(parent)
            parent = child
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        before = os.fstat(descriptor)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and 0 <= before.st_size <= limit,
                "bounded regular single-link input required")
        chunks, total = [], 0
        while total <= before.st_size:
            data = os.read(descriptor, min(65536, before.st_size + 1 - total))
            if not data:
                break
            chunks.append(data)
            total += len(data)
        fields = lambda value: (value.st_dev, value.st_ino, value.st_mode, value.st_nlink,
                               value.st_size, value.st_mtime_ns, value.st_ctime_ns)
        require(fields(before) == fields(os.fstat(descriptor)) ==
                fields(os.stat(path.name, dir_fd=parent, follow_symlinks=False)) and total == before.st_size,
                "input changed during descriptor-bound read")
        return b"".join(chunks)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent)


def selection(record):
    """Called before importing any codec/admission/rules owner or reading a ZIP."""
    require(type(record) is dict and type(record.get("family")) is str
            and record["family"] in ("A", "B", "C", "E", "F")
            and type(record.get("profile")) is str and record["profile"] in ("test-p4", "test-p28")
            and type(record.get("native_variant")) is str and record["native_variant"] in ("baseline", "lean"),
            "only full ABCEF TEST-P4/P28 original ELF transport is supported")
    return {key: record[key] for key in ("family", "profile", "native_variant")}


def context(environment=None):
    environment = os.environ if environment is None else environment
    require(environment.get("GITHUB_ACTIONS") == "true", "live GitHub Actions context required")
    names = ("GITHUB_REPOSITORY", "GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT",
             "GITHUB_REF", "GITHUB_WORKFLOW_REF")
    values = {name: environment.get(name) for name in names}
    require(all(type(value) is str for value in values.values()), "named live CI identity fields required")
    require(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", values["GITHUB_REPOSITORY"])
            and re.fullmatch(r"[0-9a-f]{40}", values["GITHUB_SHA"])
            and all(re.fullmatch(r"[1-9][0-9]*", values[name]) for name in ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT"))
            and values["GITHUB_REF"].startswith("refs/")
            and values["GITHUB_WORKFLOW_REF"] == values["GITHUB_REPOSITORY"] + "/" + WORKFLOW + "@" + values["GITHUB_REF"],
            "actual ELF workflow repository/SHA/run/attempt/ref binding required")
    return values


def capture():
    names = (SELF, PROFILE, TARGET, COMPILER, TRANSPORT)
    files = {name: read(ROOT / name).replace(b"\r\n", b"\n") for name in names}
    require(all(b"\r" not in value for value in files.values())
            and compile(files[SELF], _EXECUTING_CODE.co_filename, "exec", dont_inherit=True) == _EXECUTING_CODE,
            "current target consumer source differs from its executing source")
    E = load("elf22_profile_owner", PROFILE, files[PROFILE])
    for name, data in E.capture().items():
        require(name not in files or files[name] == data, "ELF/target owner source conflict")
        files[name] = data
    return E, files


def load(name, logical, data):
    spec = importlib.util.spec_from_file_location(name, ROOT / logical)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    exec(compile(data, str(ROOT / logical), "exec", dont_inherit=True), module.__dict__)
    return module


def modules(files):
    return {name: load("elf22_" + name, logical, files[logical]) for name, logical in
            (("transport", TRANSPORT), ("target", TARGET), ("compiler", COMPILER))}


def owners(files):
    return {name: pin(data) for name, data in sorted(files.items())}


def recheck(files):
    require(all(read(ROOT / name).replace(b"\r\n", b"\n") == value for name, value in files.items()),
            "current frozen ELF target owners changed")


def runner_path():
    value = os.environ.get("RUNNER_TEMP")
    require(type(value) is str, "live RUNNER_TEMP required")
    path = Path(value)
    require(path.is_absolute() and path.resolve() == path and path.is_dir()
            and not any(part.is_symlink() for part in (path, *path.parents)), "ordinary live RUNNER_TEMP required")
    return path


def owned(path, runner, *, new=False):
    path = Path(path)
    require(path.is_absolute() and path.resolve() == path and path != runner and runner in path.parents
            and not any(part.is_symlink() or (part / ".git").exists() for part in (path, *path.parents)),
            "owned normalized output below live RUNNER_TEMP and outside checkout required")
    require(not new or not os.path.lexists(path), "owned output already exists")
    return path


def layout(build, runner, *, new=False):
    build = owned(build, runner, new=new)
    require(build.name == "build", "original ELF producer build leaf must be named build")
    parent = owned(build.parent, runner, new=new)
    return {"runner_temp": str(runner), "output_root": str(parent), "build_root": str(build)}


def snapshot(build, m):
    values, stamps, directories = m["transport"]._snapshot(build, m["target"])
    convert = lambda rows: {"build/" + name[len("artifact/"):]: value for name, value in rows.items()}
    require(values and all(name.startswith("artifact/") for name in values), "one closed artifact tree required")
    return convert(values), convert(stamps), directories


def members_record(values, stamps):
    return {name: {**pin(value), "mode": stamps[name][2] & 0o777} for name, value in sorted(values.items())}


def decode_bundle(data, manifest, m):
    require(type(data) is bytes and 0 < len(data) <= MAX_BUNDLE and type(manifest) is dict
            and 0 < len(manifest) <= MAX_FILES, "bounded nonempty closed ELF transport required")
    modes = m["transport"]._zip_modes(data, None, m["target"])
    require(set(modes) == set(manifest) and all(name.startswith("build/") for name in modes),
            "ELF archive member set/root differs")
    values = {}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for item in archive.infolist():
            require(item.filename not in values and item.date_time == (1980, 1, 1, 0, 0, 0)
                    and item.create_system == 3, "deterministic unique original ELF member required")
            expected = manifest[item.filename]
            require(type(expected) is dict and set(expected) == {"bytes", "sha256", "mode"}
                    and type(expected["bytes"]) is int and expected["bytes"] == item.file_size
                    and type(expected["mode"]) is int and expected["mode"] == modes[item.filename],
                    "sealed member extent or mode differs")
            value = archive.read(item)
            require(pin(value) == {key: expected[key] for key in ("bytes", "sha256")}, "sealed raw member differs")
            values[item.filename] = value
    require(set(values) == set(manifest), "closed ELF archive omitted a member")
    stamps = {name: (0, 0, stat.S_IFREG | modes[name]) for name in values}
    require(m["transport"]._zip_bytes(values, stamps) == data,
            "ELF transport differs from deterministic closed ZIP serialization")
    return values, modes


def write(path, data, m):
    m["transport"]._write_new(Path(path), data, m["target"])


def transport_file_limits(extents, *, maximum):
    """Transport files precede tool limits; never raise an inherited file cap."""
    import resource
    require(type(extents) is tuple and extents and maximum in (MAX_MEMBER, MAX_BUNDLE)
            and all(type(size) is int and 0 <= size <= maximum for size in extents),
            "finite owned transport file extents required")
    inherited = resource.getrlimit(resource.RLIMIT_FSIZE)
    require(type(inherited) is tuple and len(inherited) == 2
            and all(type(limit) is int and limit >= -1 for limit in inherited)
            and (inherited[1] == -1 or 0 <= inherited[0] <= inherited[1]),
            "valid inherited transport file limits required")
    require(all(limit == -1 or max(extents) <= limit for limit in inherited),
            "inherited file limit is insufficient for owned transport artifacts")
    return dict(inherited_FSIZE=inherited, declared_maximum_bytes=maximum,
                largest_file_bytes=max(extents), inherited_limit_raised=False)


def host_for(E, files, out, report, save, started):
    import resource
    owner = load("elf22_process_owner", E.OWNER, files[E.OWNER])
    require(owner.EXECUTING_BUILD == files[E.OWNER], "existing process owner source differs")
    inherited = {name: resource.getrlimit(kind) for name, kind in
                 (("CPU", resource.RLIMIT_CPU), ("AS", resource.RLIMIT_AS), ("FSIZE", resource.RLIMIT_FSIZE))}
    applied = E.limit_plan(inherited["CPU"], inherited["AS"], inherited["FSIZE"])
    resource.setrlimit(resource.RLIMIT_FSIZE, applied["FSIZE"])
    previous = dict(owner.LIMITS)
    remaining = math.floor(WORK_SECONDS - (time.monotonic() - started))
    require(remaining > 0, "target work budget expired before existing Host construction")
    owner.LIMITS.update(aggregate_wall=remaining, per_command_wall=remaining, parent_AS=applied["parent_AS"],
        parent_CPU=applied["parent_CPU"][0], parent_CPU_hard=applied["parent_CPU"][1], tool_output_bytes=E.MAX_FILE)

    class Host(owner.Host):
        def settle(self, child, row, force=False):
            if row.get("kind") in ("rules", "runtime"):
                row["cooperative_termination_seconds"] = 15
            return super().settle(child, row, force)

    handlers = {kind: signal.getsignal(kind) for kind in (signal.SIGTERM, signal.SIGINT, signal.SIGALRM, signal.SIGXCPU)}
    try:
        host = Host(out, report, save)
    except BaseException:
        owner.LIMITS.clear()
        owner.LIMITS.update(previous)
        signal.alarm(0)
        for kind, handler in handlers.items():
            signal.signal(kind, handler)
        raise
    report["limits"] = {"inherited": inherited, "applied": applied,
                         "work_seconds_including_setup": WORK_SECONDS, "cleanup_seconds": CLEANUP_SECONDS}
    return owner, previous, host


def git_binding(E, host, owner, ci):
    value = E.run_command(host, owner, ["git", "-C", str(ROOT), "rev-parse", "HEAD"], cwd=host.out,
                          kind="checkout-head")
    require(value.decode("ascii").strip() == ci["GITHUB_SHA"], "actual checkout differs from live workflow SHA")


def _operation(out, E, files, report, started, body, *, prepare=None):
    """Owned artifact I/O precedes tool caps; one Host owns every command."""
    m = modules(files)
    out.mkdir(parents=True)
    for name, data in files.items():
        path = out / "support" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        write(path, data, m)
    save = lambda: (out / "result.json").write_bytes(encoded(report))
    save()
    owner = previous = host = None
    error = None
    prior = signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    utility = load("elf22_finish_owner", E.UTILITY, files[E.UTILITY])
    try:
        report["host_constructed"] = False
        if prepare is not None:
            report["operation_stage"] = "transport-artifacts-before-tool-limits"
            save()
            prepare(m, save)
        report["operation_stage"] = "owned-command-evidence"
        owner, previous, host = host_for(E, files, out, report, save, started)
        report["host_constructed"] = True
        git_binding(E, host, owner, report["ci_context"])
        body(m, host, owner, save)
        recheck(files)
        require(context() == report["ci_context"], "live workflow context changed")
    except BaseException as failure:
        error = failure
        report["failure"] = {"type": type(failure).__name__, "message": str(failure)}
        raise
    finally:
        try:
            if host is None:
                report["host_cleanup"] = {"unsettled_commands": 0, "errors": []}
            utility.finish_report(host, report, save, error)
        finally:
            if owner is not None and previous is not None:
                owner.LIMITS.clear()
                owner.LIMITS.update(previous)
            signal.signal(signal.SIGCHLD, prior)
    return report


def export_bundle(build, out, *, execute=False):
    require(execute is True, "export is inactive without --execute")
    started = time.monotonic()
    build = Path(build)
    metadata = json.loads(read(build / "build.json"))
    chosen = selection(metadata)
    ci = context()
    require(os.environ.get("GITHUB_JOB") == "full-profiles", "ELF producer job authority required")
    E, files = capture()
    m = modules(files)
    require(m["target"]._source_host() == {"ID": "ubuntu", "VERSION_ID": "24.04"}, "real Ubuntu24 exporter required")
    runner = runner_path()
    original = layout(build, runner)
    out = owned(out, runner, new=True)
    require(not out.is_relative_to(build) and not build.is_relative_to(out),
            "transport output must not overlap the closed artifact tree")
    manifest, admitted, R, unused = E.read_build(build, test_only=True)
    require(selection(manifest) == chosen and admitted.representation == "self-contained-elf", "same original full TEST ELF required")
    report = dict(format=FORMAT, action="export", complete=False, commands=[], outer_command_limit=1,
                  ci_context=ci, selection=chosen, engine_executed=False, factory_replayed=False)
    pending = {}

    def prepare(m, save):
        before = snapshot(build, m)
        bundle = m["transport"]._zip_bytes(before[0], before[1])
        require(len(bundle) <= MAX_BUNDLE, "ELF transport exceeds raw ZIP bound")
        seal = dict(format=SEAL_FORMAT, ci_context=ci, producer_job="full-profiles", producer_os="ubuntu-24.04",
            selection=chosen, policy=manifest["policy"], representation="self-contained-elf", full=True,
            original_layout=original, expected_contract=admitted.expected,
            producer_build=pin(read(build / "build.json")), owners=owners(files), bundle=pin(bundle),
            members=members_record(before[0], before[1]), source_factory_replayed=False,
            producer_runtime_qualification_carried=False, export_closed=True)
        decode_bundle(bundle, seal["members"], m)
        report["transport_artifact_limits"] = transport_file_limits((len(bundle),), maximum=MAX_BUNDLE)
        save()
        write(out / BUNDLE, bundle, m)
        require(snapshot(build, m) == before and read(out / BUNDLE, MAX_BUNDLE) == bundle,
                "original ELF build or transport changed during sealing")
        pending.update(bundle=bundle, before=before, seal=encoded(seal), modules=m)
        require(len(pending["seal"]) <= MAX_SEAL, "bounded ELF seal required")
        report.update(bundle=pin(bundle), seal=pin(pending["seal"]), members=len(before[0]),
                      transport_prepared_before_tool_limits=True,
                      generation_only_seal=True, submission_qualified=False, elf_qualified=False)
        save()

    def body(m, host, owner, save):
        require(snapshot(build, m) == pending["before"] and read(out / BUNDLE, MAX_BUNDLE) == pending["bundle"],
                "prepared transport or original build changed before command evidence")
        checked, actual, unused_R, unused_files = E.read_build(build, test_only=True)
        require(checked == manifest and actual.expected == admitted.expected, "strict producer admission changed")
        require([row["kind"] for row in report["commands"]] == ["checkout-head"] and E.settled(report["commands"]),
                "actual exporter checkout command did not settle cleanly")
        require(snapshot(build, m) == pending["before"] and read(out / BUNDLE, MAX_BUNDLE) == pending["bundle"],
                "prepared transport or original build changed after command evidence")

    result = _operation(out, E, files, report, started, body, prepare=prepare)
    try:
        # The seal is a publication marker: do not expose it from an exporter
        # which later fails its existing Host's physical settlement.
        require(result["complete"] is True and result["host_cleanup"] == {"unsettled_commands": 0, "errors": []},
                "ELF exporter must settle before publishing its trusted seal")
        write(out / SEAL, pending["seal"], pending["modules"])
        require(read(out / SEAL, MAX_SEAL) == pending["seal"], "published ELF seal changed")
        result["seal_published_after_settlement"] = True
        (out / "result.json").write_bytes(encoded(result))
    except BaseException as error:
        result.update(complete=False, publication_failure={"type": type(error).__name__, "message": str(error)})
        (out / "result.json").write_bytes(encoded(result))
        raise
    return result


def allowed_path(path, patterns):
    require(type(path) is str and path.startswith("/") and Path(path).as_posix() == path
            and ".." not in Path(path).parts, "normalized absolute installed dependency path required")
    return any(str(Path(path).parent) == directory and any(fnmatchcase(Path(path).name, pattern) for pattern in names)
               for directory, names in patterns.items())


def parse_resolution(raw):
    """Read the installed GNU loader's bounded --list output, not ldd."""
    require(type(raw) is bytes and 0 < len(raw) <= 1 << 20, "bounded actual loader output required")
    result = {}
    for line in raw.decode("ascii", "strict").splitlines():
        line = line.strip()
        if re.fullmatch(r"linux-vdso\.so\.1 \(0x[0-9a-f]+\)", line):
            continue
        match = re.fullmatch(r"(\S+) => (/\S+) \(0x[0-9a-f]+\)", line)
        if match:
            name, path = match.groups()
        else:
            match = re.fullmatch(r"(/\S+) \(0x[0-9a-f]+\)", line)
            require(match is not None, "unresolved or unrecognized installed loader output")
            path = match[1]
            name = Path(path).name
        require(name not in result, "duplicate installed loader library entry")
        result[name] = path
    require(result, "installed loader reported no dependencies")
    return result


def resolved_inputs(raw, metadata, dependency, compiler):
    rows = parse_resolution(raw)
    require(all((Path(name).name if "/" in name else name) in rows for name in metadata["needed"]),
            "installed loader omitted a direct DT_NEEDED library")
    records = {}
    for name, path in rows.items():
        require(allowed_path(path, dependency.LIBRARY_PATHS), "resolved library escaped documented TCEC directories")
        actual = Path(path).resolve()
        require(actual.parent in {Path(directory).resolve() for directory in dependency.LIBRARY_PATHS},
                "resolved library escaped installed directory aliases")
        data = compiler.regular(actual, limit=MAX_MEMBER, allow_hardlinks=True)
        detail = dependency.inspect_dependencies(data)
        require(dependency.check_tcec_policy(detail)["allowed"] is True
                and detail["soname"] == Path(name).name, "resolved library SONAME or dependency policy differs")
        records[name] = dict(path=path, real_path=str(actual), **pin(data), dependency_metadata=detail)
    return records


def consume(bundle, seal_path, out, *, execute=False):
    require(execute is True, "target consumption is inactive without --execute")
    started = time.monotonic()
    bundle, seal_path = Path(bundle), Path(seal_path)
    require(bundle.name == BUNDLE and seal_path.name == SEAL, "named original ELF bundle and seal required")
    seal_raw = read(seal_path, MAX_SEAL)
    seal = json.loads(seal_raw)
    chosen = selection(seal.get("selection"))
    ci = context()
    require(seal.get("format") == SEAL_FORMAT and seal.get("ci_context") == ci
            and seal.get("producer_job") == "full-profiles" and seal.get("producer_os") == "ubuntu-24.04"
            and os.environ.get("GITHUB_JOB") not in (None, "", "full-profiles")
            and seal.get("representation") == "self-contained-elf" and seal.get("full") is True
            and seal.get("source_factory_replayed") is False and seal.get("producer_runtime_qualification_carried") is False
            and seal.get("export_closed") is True,
            "same live ELF workflow producer seal required")
    E, files = capture()
    require(seal.get("owners") == owners(files), "sealed/current target consumer owners differ")
    m = modules(files)
    compiler = m["compiler"]
    compiler.require_compiler_environment()
    require(not any(os.environ.get(name) for name in LOADER_ENV), "loader redirection environment is unsupported")
    system = compiler.system_descriptor(Path("/usr/bin/cc"))
    require(shutil.which("cc") is not None and Path(shutil.which("cc")).resolve() == Path("/usr/bin/cc").resolve(),
            "rules compiler PATH does not select the admitted system compiler")
    runner = runner_path()
    original = seal.get("original_layout")
    require(type(original) is dict and original == layout(Path(original.get("build_root", "")), runner, new=True),
            "original normalized build layout is unavailable on target")
    build, original_out = Path(original["build_root"]), Path(original["output_root"])
    out = owned(out, runner, new=True)
    require(not out.is_relative_to(original_out) and not original_out.is_relative_to(out),
            "target output overlaps the original producer root")
    raw = read(bundle, MAX_BUNDLE)
    require(pin(raw) == seal.get("bundle"), "original ELF ZIP identity differs")
    values, modes = decode_bundle(raw, seal.get("members"), m)
    report = dict(format=FORMAT, action="consume", complete=False, commands=[], outer_command_limit=6,
        ci_context=ci, selection=chosen, system=system, original_layout=original,
        bundle=pin(raw), seal=pin(seal_raw), factory_replayed=False, production_native_recompiled=False,
        original_whole_executed=False, engine_executed=False, TT_allocated=False,
        elf_qualified=False, submission_qualified=False, placement_qualified=False,
        event_target_confirmed=False, release_qualified=False, selected=False, scoring=False)

    prepared = {}

    def prepare(m, save):
        report["transport_artifact_limits"] = transport_file_limits(tuple(len(value) for value in values.values()), maximum=MAX_MEMBER)
        save()
        descriptor = m["transport"]._create_root(runner, original_out)
        try:
            m["transport"]._restore_files(descriptor, values, modes)
        finally:
            os.close(descriptor)
        restored = snapshot(build, m)
        require(restored[0] == values and members_record(restored[0], restored[1]) == seal["members"],
                "restored original ELF members or modes differ")
        prepared["restored"] = restored
        report["transport_prepared_before_tool_limits"] = True
        save()

    def body(m, host, owner, save):
        version = E.run_command(host, owner, ["/usr/bin/cc", "-dumpfullversion"], cwd=out, kind="system-compiler-version")
        require(version.decode("ascii").strip() == "11.4.0", "actual system GCC11.4 required")
        restored = prepared["restored"]
        require(snapshot(build, m) == restored and read(bundle, MAX_BUNDLE) == raw and read(seal_path, MAX_SEAL) == seal_raw,
                "restored transport changed before strict source admission")
        manifest, admitted, R, unused = E.read_build(build, test_only=True)
        require(selection(manifest) == chosen and manifest["policy"] == seal["policy"]
                and pin(read(build / "build.json")) == seal["producer_build"]
                and admitted.expected == seal["expected_contract"]
                and type(admitted.wrapper_contract) is R.AnonymousMemfdContract,
                "restored original ELF strict admission differs from producer seal")
        native = R.checked_artifact(build, admitted.native, R._field_pin(admitted.expected, "native"))
        whole = R.checked_artifact(build, admitted.program, R._field_pin(admitted.expected, "whole"))
        abi = compiler.elf_abi(native, R)
        dependency = load("elf22_dependency_owner", E.ELF_DEPENDENCIES, files[E.ELF_DEPENDENCIES])
        metadata = dependency.inspect_dependencies(native)
        require(dependency.check_tcec_policy(metadata)["allowed"] is True and type(metadata["interpreter"]) is str,
                "original native interpreter/dependency policy unsupported on target")
        interpreter = metadata["interpreter"]
        require(allowed_path(interpreter, dependency.INTERPRETER_PATHS), "native installed interpreter path differs")
        loader = Path(interpreter).resolve()
        loader_pin = pin(compiler.regular(loader, limit=MAX_MEMBER, allow_hardlinks=True))
        command = [interpreter, "--list", str(build / admitted.native)]
        before = resolved_inputs(E.run_command(host, owner, command, cwd=out, kind="installed-libraries-before"),
                                 metadata, dependency, compiler)
        report.update(native_abi=abi, native_dependencies=metadata, installed_loader=dict(path=interpreter,
            real_path=str(loader), **loader_pin), installed_dependencies=before, original_whole=pin(whole))
        save()
        for action in ("rules", "runtime"):
            recheck(files)
            require(snapshot(build, m) == restored, "sealed original artifact changed before target consumer")
            if action == "runtime":
                report.update(engine_execution_attempted=True, TT_allocation_attempted=True,
                              engine_executed=None, TT_allocated=None, original_whole_executed=None)
                save()
            E.run_command(host, owner, [sys.executable, "-I", "-B", str(ROOT / PROFILE), action,
                "--build", str(build), "--out", str(out / action), "--execute"], cwd=out, kind=action, factory=True)
            recheck(files)
            require(snapshot(build, m) == restored, "sealed original artifact changed after target consumer")
        after = resolved_inputs(E.run_command(host, owner, command, cwd=out, kind="installed-libraries-after"),
                                metadata, dependency, compiler)
        require(before == after and pin(compiler.regular(loader, limit=MAX_MEMBER, allow_hardlinks=True)) == loader_pin
                and compiler.system_descriptor(Path("/usr/bin/cc")) == system,
                "installed compiler/loader/library identities changed")
        rules = E.rules_receipt(build, out / "rules/rules.json")
        observed = json.loads(read(out / "runtime/runtime.json"))
        runtime = R.qualification_record(admitted, build, out / "runtime/runtime.json", rules_path=None)
        checks = runtime["checks"]
        require(all(value is True for name, value in checks.items() if name not in ("size", "placement", "legal_moves"))
                and rules["nbrq_generation"] is True and observed.get("complete") is True,
                "non-scoring original ELF functional evidence is incomplete")
        require(read(bundle, MAX_BUNDLE) == raw and read(seal_path, MAX_SEAL) == seal_raw
                and snapshot(build, m) == restored, "original transport/build changed after target observation")
        require([row["kind"] for row in report["commands"]] == ["checkout-head", "system-compiler-version",
                "installed-libraries-before", "rules", "runtime", "installed-libraries-after"]
                and E.settled(report["commands"]), "actual finite target commands did not settle cleanly")
        report.update(functional_complete=True, original_whole_executed=True, engine_executed=True, TT_allocated=True,
            counts=observed["counts"], runtime_checks=checks, actual_source_rules=rules,
            runtime_receipt=pin(read(out / "runtime/runtime.json")),
            status="deferred_size" if admitted.expected["whole_bytes"] > 4096 else "functional_unqualified",
            size_eligible=admitted.expected["whole_bytes"] <= 4096,
            producer_expected_contract=admitted.expected, original_artifact_unchanged=True,
            scope="same original producer ELF on actual Ubuntu22; GCC11 rules only; no scoring, placement, event or ELF qualification")
        save()

    return _operation(out, E, files, report, started, body, prepare=prepare)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    export = sub.add_parser("export")
    export.add_argument("--build", type=Path, required=True)
    target = sub.add_parser("consume")
    target.add_argument("--bundle", type=Path, required=True)
    target.add_argument("--seal", type=Path, required=True)
    for item in (export, target):
        item.add_argument("--out", type=Path, required=True)
        item.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    result = (export_bundle(args.build, args.out, execute=args.execute) if args.action == "export" else
              consume(args.bundle, args.seal, args.out, execute=args.execute))
    print(json.dumps({key: result[key] for key in ("action", "complete", "functional_complete", "status") if key in result}, sort_keys=True))


if __name__ == "__main__":
    main()
