#!/usr/bin/env python3
"""Compile admitted full profiles with a separately identified target compiler.

This is a compile/ELF compatibility observation, not engine execution, source
selection, TCEC approval or Ubuntu 22 runtime qualification. A source-JIT wrapper
still needs the same compiler context at runtime; its bare ``cc`` is not changed.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import signal
import struct
import sys

sys.dont_write_bytecode = True
_EXECUTING_CODE = sys._getframe().f_code
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SELF = "engines/experiments/tcec-next/profile_compiler.py"
VERIFY_PATH = "engines/experiments/tcec-next/profile_verify.py"
HOST_PATH = "engines/experiments/tcec-scope/build.py"
HOST_SHA = "fc916e798952cff1c915a6846e758874bc2d858b3c59dec73870b95c7e3d4828"
SCHEMA = "rove4k.profile-compiler.v1"
GLIBC_MAX = (2, 35)
C_FLAGS = {
    "A": ("cc", "-Os", "-x", "c", "-", "-o", "x", "-s"),
    "B": ("cc", "-std=c11", "-Os", "-pthread", "-x", "c", "-", "-o", "x"),
    "C": ("cc", "-Os", "-mavx2", "-x", "c", "-", "-o", "x", "-s"),
    "E": ("cc", "-Os", "-x", "c", "-", "-o", "x", "-s"),
    "F": ("cc", "-Os", "-pthread", "-x", "c", "-", "-o", "x", "-s"),
}


def require(condition, detail):
    if not condition:
        raise ValueError(detail)


def pin(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def normalized(path):
    data = Path(path).read_bytes().replace(b"\r\n", b"\n")
    require(b"\r" not in data, "lone CR in named tool source")
    return data


def executing_source(data):
    require(compile(data, __file__, "exec", dont_inherit=True) == _EXECUTING_CODE,
            "compiler checker changed after its executing module was compiled")
    return data


def regular(path, *, limit=64 << 20):
    path = Path(path)
    require(path.is_absolute() and not path.is_symlink(), "absolute non-link input required")
    require(path.is_file() and path.stat().st_size <= limit, "bounded regular input required")
    return path.read_bytes()


def sdk_descriptor(compiler, audit_raw, smoke_raw=None, *, audit_sha256):
    require(isinstance(audit_sha256, str) and re.fullmatch(r"[0-9a-f]{64}", audit_sha256) is not None,
            "explicit SDK audit SHA-256 required")
    require(pin(audit_raw)["sha256"] == audit_sha256, "SDK audit identity differs")
    audit = json.loads(audit_raw)
    root = compiler.parent.parent.resolve()
    combined = audit.get("schema") == "rove4k.jammy-gcc11-relocated-sdk-audit.v2"
    if combined:
        require(smoke_raw is None and audit.get("dumpfullversion") == "11.4.0" and
                audit.get("compile", {}).get("returncode") == 0,
                "relocated SDK audit must contain its actual GCC 11.4 smoke")
        require(audit.get("providers") and audit.get("ordinary_target_interpreter_preserved") is True,
                "relocated SDK provider/interpreter audit is incomplete")
        for row in audit["providers"].values():
            path = Path(row["path"]).resolve()
            require(root in path.parents and str(path) == row["resolved"] and
                    pin(regular(path))["sha256"] == row["sha256"],
                    "relocated SDK provider changed or escaped")
        smoke = {"complete": audit.get("complete"), "wrapper": audit["wrapper"]["path"],
                 "wrapper_sha256": audit["wrapper"]["sha256"],
                 "wrapper_version": audit["cc_version"], "cc": audit["providers"]["compiler"]["path"]}
        smoke_pin = pin(audit_raw)
    else:
        require(smoke_raw is not None, "legacy SDK requires its separately bound smoke receipt")
        smoke = json.loads(smoke_raw)
        require(audit.get("smoke_receipt_sha256") == pin(smoke_raw)["sha256"],
                "SDK audit does not bind this compiler smoke receipt")
        smoke_pin = pin(smoke_raw)
    require(audit.get("complete") is True and smoke.get("complete") is True,
            "SDK preparation/audit did not complete")
    require(audit["wrapper"]["path"] == str(compiler) == smoke["wrapper"],
            "target compiler is outside the audited SDK context")
    require(audit["wrapper"]["sha256"] == smoke["wrapper_sha256"] ==
            pin(regular(compiler))["sha256"], "SDK compiler wrapper identity differs")
    require("11.4.0" in smoke["wrapper_version"], "provisional GCC 11.4 SDK required")
    driver = Path(smoke["cc"]).resolve()
    require(root in driver.parents and driver.is_file(), "SDK compiler driver escaped its context")
    return {"kind": "audited-jammy-sdk", "audit": pin(audit_raw), "smoke": smoke_pin,
            "smoke_is_in_audit": combined,
            "root": str(root), "input_roots": [str(root)],
            "wrapper": {"path": str(compiler), **pin(regular(compiler))},
            "driver": {"path": str(driver), **pin(regular(driver))},
            "scope": "audited Jammy compiler/sysroot; actual host runtime recorded separately"}


def ubuntu22_host(fields, libc):
    require(fields.get("ID") == "ubuntu" and fields.get("VERSION_ID") == "22.04",
            "explicit system mode requires actual Ubuntu 22.04")
    require(tuple(libc) == ("glibc", "2.35"), "Ubuntu 22 system mode requires actual glibc 2.35")


def system_descriptor(compiler):
    release_path = Path("/etc/os-release").resolve()
    release = regular(release_path, limit=16384)
    fields = {}
    for line in release.decode().splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            if key in ("ID", "VERSION_ID"):
                tokens = shlex.split(value)
                require(len(tokens) == 1, "invalid OS identity field")
                fields[key] = tokens[0]
    libc = platform.libc_ver()
    ubuntu22_host(fields, libc)
    compiler = compiler.resolve()
    require(Path("/usr/bin") in compiler.parents, "system compiler must be an installed /usr/bin tool")
    binary = {"path": str(compiler), **pin(regular(compiler))}
    return {"kind": "ubuntu22-system", "root": "/", "input_roots": ["/usr", "/lib", "/lib64", "/bin"],
            "wrapper": binary, "driver": binary, "os_release": {**fields, **pin(release)},
            "libc": libc, "scope": "actual Ubuntu 22.04 system compiler; engine runtime remains separate"}


def within(path, roots):
    return any(root == path or root in path.parents for root in roots)


def record_input(inputs, path):
    observed = pin(regular(path))
    require(str(path) not in inputs or inputs[str(path)] == observed,
            "compiler input changed during discovery or compilation")
    inputs[str(path)] = observed


def compiler_program(name, *, system):
    path = Path(name)
    if system and not path.is_absolute() and len(path.parts) == 1:
        found = shutil.which(name)
        require(found is not None, "system compiler program is absent from PATH")
        path = Path(found)
    require(path.is_absolute(), "compiler program did not resolve to an absolute executable")
    return path.resolve()


@dataclass(frozen=True)
class SourceInput:
    family: str
    profile: str
    build: Path
    manifest_raw: bytes
    manifest: dict
    files: dict[str, bytes]
    flags: tuple[str, ...]
    units: tuple[str, ...]
    assertions: tuple[str, ...]
    old_native: dict


def admit(build, verify):
    """Use the current production admission; do not weaken stale closure checks."""
    build = Path(build)
    require(build.is_absolute() and build.is_dir() and not build.is_symlink(),
            "absolute production build directory required")
    raw = regular(build / "build.json", limit=8 << 20)
    record = json.loads(raw)
    if record.get("family") == "D":
        accepted = verify.admit_d_build(record, build, "D-source-jit")
        builder = load("profile_compiler_D_builder", ROOT / "engines/experiments/tiny-d-submission/build.py")
        profile = verify.contracts().resource_profile(accepted.profile_id)
        expected = builder.native_flags(profile)
        require(record["flags"] == expected, "D target compiler flags differ from current production")
        require(record["units"] == ["main.c", "start.S"], "D explicit single-TU compiler input required")
        names = set(record["units"]) | {"image.ld"}
        require(set(record["shipping_inputs"]) == names, "D target source membership differs")
        files = {name: verify.checked_artifact(build, "shipping-inputs/" + name,
                                               record["shipping_inputs"][name]) for name in sorted(names)}
        flags, units = tuple(expected), tuple(record["units"])
        assertions = ("_Static_assert(sizeof(void*)==8 && sizeof(unsigned long)==8 && "
                      "sizeof(unsigned long long)==8 && __SIZEOF_INT128__==16,\"D LP64/int128 ABI\");",)
    else:
        accepted = verify.admit_c_build(record, build)
        require(accepted.family in C_FLAGS and tuple(record["compiler"]) == C_FLAGS[accepted.family],
                "C target compiler argv differs from the reviewed family contract")
        files = {"main.c": verify.checked_artifact(build, "main.c",
                  {"bytes": record["expected_contract"]["source_bytes"],
                   "sha256": record["expected_contract"]["source_sha256"]})}
        flags, units = tuple(record["compiler"])[1:], ()
        assertions = tuple(record["source_proofs"][0]["target_type_assertions"])
    require(accepted.profile_id in ("tcec-provisional", "test-p4", "test-p28"),
            "named immutable resource profile required")
    return SourceInput(accepted.family, accepted.profile_id, build, raw, record, files,
                       flags, units, assertions, dict(accepted.expected))


def elf_abi(native, verify):
    """Parse imported version requirements, not coincidental strings in .text."""
    result = verify.native_dependencies(native)
    values = struct.unpack_from("<16sHHIQQQIHHHHHH", native)
    headers = [struct.unpack_from("<IIQQQQQQ", native, values[5] + values[9] * i)
               for i in range(values[10])]

    def mapped(address, length):
        matches = [offset + address - base for kind, _, offset, base, _, size, _, _ in headers
                   if kind == 1 and base <= address and address + length <= base + size]
        require(len(matches) == 1, "ELF version table escaped uniquely file-backed loaded bytes")
        return matches[0]

    tags = {}
    for kind, _, offset, _, _, size, _, _ in headers:
        if kind == 2:
            terminated = False
            for at in range(offset, offset + size, 16):
                tag, value = struct.unpack_from("<qQ", native, at)
                if tag == 0:
                    terminated = True
                    break
                if tag in (5, 10, 0x6ffffffe, 0x6fffffff):
                    require(tag not in tags, "duplicate ELF ABI dynamic tag")
                    tags[tag] = value
            require(terminated, "unterminated ELF dynamic table")
    requirements = []
    has_need, has_count = 0x6ffffffe in tags, 0x6fffffff in tags
    require(has_need == has_count, "ELF version need pointer/count pair required")
    if has_need:
        require(5 in tags and 10 in tags and 0 < tags[0x6fffffff] <= 64,
                "bounded ELF version/string tables required")
        table_at = mapped(tags[5], tags[10])
        strings = native[table_at:table_at + tags[10]]

        def string(index):
            require(index < len(strings) and b"\0" in strings[index:], "invalid ELF ABI string")
            return strings[index:].split(b"\0", 1)[0].decode("ascii")

        address, seen = tags[0x6ffffffe], set()
        for index in range(tags[0x6fffffff]):
            require(address not in seen, "cyclic ELF version need chain")
            seen.add(address)
            at = mapped(address, 16)
            version, count, file_name, aux, following = struct.unpack_from("<HHIII", native, at)
            library = string(file_name)
            require(version == 1 and 0 < count <= 128 and aux >= 16 and
                    library in result["DT_NEEDED"], "invalid imported ELF version need record")
            aux_address, aux_seen = address + aux, set()
            for item in range(count):
                require(aux_address not in aux_seen, "cyclic ELF version auxiliary chain")
                aux_seen.add(aux_address)
                _, _, _, name, next_aux = struct.unpack_from("<IHHII", native, mapped(aux_address, 16))
                name = string(name)
                if name.startswith("GLIBC_"):
                    match = re.fullmatch(r"GLIBC_(\d+(?:\.\d+)+)", name)
                    require(match is not None, "unsupported private/non-numeric GLIBC ABI requirement")
                    number = tuple(map(int, match[1].split(".")))
                    require(number <= GLIBC_MAX, "native requires GLIBC newer than Ubuntu 22.04")
                requirements.append({"library": library, "version": name})
                require((next_aux == 0) if item + 1 == count else next_aux >= 16,
                        "ELF auxiliary count and termination differ")
                aux_address += next_aux
            require((following == 0) if index + 1 == tags[0x6fffffff] else following >= 16,
                    "ELF need count and termination differ")
            address += following
    return {**result, "imported_versions": requirements, "glibc_ceiling": "2.35",
            "scope": "actual ELF program/dynamic/version tables; no engine was executed"}


def dependency_paths(data, *, sdk_root=None, owned_root, input_roots=()):
    """Decode the compiler's make dependency file; bound every real input."""
    text = data.decode().replace("\\\n", "")
    require(":" in text, "compiler dependency target is absent")
    names = shlex.split(text.split(":", 1)[1], posix=True)
    result = set()
    for name in names:
        if name == "<stdin>":
            continue
        path = Path(name).resolve()
        roots = [Path(p).resolve() for p in input_roots] if input_roots else [sdk_root]
        require(within(path, [*roots, owned_root]),
                "compiler dependency escaped the SDK and frozen source context")
        require(path.is_file(), "compiler dependency is not a regular file")
        result.add(path)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="append", type=Path, required=True)
    parser.add_argument("--compiler", type=Path, required=True)
    context = parser.add_mutually_exclusive_group(required=True)
    context.add_argument("--sdk-audit", type=Path)
    context.add_argument("--ubuntu22-system", action="store_true",
                         help="explicit real Ubuntu22/glibc2.35 context for target CI")
    parser.add_argument("--sdk-audit-sha256")
    parser.add_argument("--sdk-smoke", type=Path, help="legacy separate smoke receipt; relocated audit includes its own")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    executing = executing_source(normalized(Path(__file__)))
    require(sys.platform == "linux" and platform.machine() == "x86_64", "Linux x86-64 compiler host required")
    out = args.out.resolve()
    require(args.out.is_absolute() and not out.exists() and
            not any((p / ".git").exists() for p in (out, *out.parents)),
            "new absolute external compiler output required")
    compiler = args.compiler.resolve() if args.ubuntu22_system else args.compiler.absolute()
    if args.ubuntu22_system:
        require(not args.sdk_audit_sha256 and not args.sdk_smoke, "system and SDK metadata cannot be mixed")
        audit_raw = smoke_raw = None
        def current_context():
            return system_descriptor(compiler)
    else:
        require(args.sdk_audit_sha256, "SDK audit identity required")
        audit_raw = regular(args.sdk_audit)
        smoke_raw = regular(args.sdk_smoke) if args.sdk_smoke else None
        def current_context():
            return sdk_descriptor(compiler, regular(args.sdk_audit),
                                  regular(args.sdk_smoke) if args.sdk_smoke else None,
                                  audit_sha256=args.sdk_audit_sha256)
    sdk = current_context()
    input_roots = tuple(Path(path).resolve() for path in sdk["input_roots"])
    verify = load("profile_compiler_verify", ROOT / VERIFY_PATH)
    sources = [admit(path, verify) for path in args.build]
    require(len({(s.family, s.profile) for s in sources}) == len(sources), "duplicate family/profile compiler input")
    tools = {SELF: executing, **{name: normalized(ROOT / name) for name in (VERIFY_PATH, HOST_PATH)}}
    verify.executing_source(tools[VERIFY_PATH])
    require(pin(tools[HOST_PATH])["sha256"] == HOST_SHA, "bounded command owner differs")
    out.mkdir()
    for name, data in tools.items():
        target = out / "tools" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    if audit_raw is not None:
        (out / "sdk-audit.json").write_bytes(audit_raw)
    if smoke_raw is not None:
        (out / "sdk-smoke.json").write_bytes(smoke_raw)
    report = {"format": SCHEMA, "complete": False, "engine_executed": False,
              "large_TT_allocated": False, "submission_qualified": False, "compiler_context": sdk,
              "tools": {name: pin(data) for name, data in tools.items()}, "commands": [], "profiles": [],
              "host": {"platform": platform.platform(), "libc": platform.libc_ver(),
                       "cpu_affinity": sorted(os.sched_getaffinity(0))},
              "not_proven": ["Ubuntu 22.04 actual runtime", "event-specific compiler acceptance",
                             "source-JIT runtime cc identity", "many-core startup or engine strength"]}
    def save():
        (out / "compiler.json").write_text(json.dumps(report, indent=2) + "\n")
    owner = load("profile_compiler_host", out / "tools" / HOST_PATH)
    owner.LIMITS.update(aggregate_wall=600, per_command_wall=90, parent_CPU=240,
                        parent_CPU_hard=270, child_CPU=60, child_AS=2 << 30)
    previous = signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    temporary = os.environ.get("TMPDIR")
    os.environ["TMPDIR"] = str(out / "tmp")
    (out / "tmp").mkdir()
    host = owner.Host(out, report, save)
    sdk_files = {row["path"]: {key: row[key] for key in ("bytes", "sha256")}
                 for row in (sdk["wrapper"], sdk["driver"])}
    try:
        version = host.run([compiler, "-dumpfullversion"], cwd=out, kind="compiler-version").decode().strip()
        require(version == "11.4.0", "actual target compiler is not GCC 11.4.0")
        report["compiler_version"] = host.run([compiler, "--version"], cwd=out, kind="compiler-banner").decode()
        for query in ("cc1", "as", "ld", "collect2", "lto1"):
            name = host.run([compiler, "-print-prog-name=" + query], cwd=out,
                            kind="compiler-program-" + query).decode().strip()
            path = compiler_program(name, system=args.ubuntu22_system)
            require(within(path, input_roots), "compiler program escaped its admitted context")
            record_input(sdk_files, path)
        for selected in sources:
            directory = out / (selected.family + "-" + selected.profile)
            directory.mkdir()
            frozen = directory / "source"
            frozen.mkdir()
            for name, data in selected.files.items():
                (frozen / name).write_bytes(data)
            (directory / "input-build.json").write_bytes(selected.manifest_raw)
            row = {"family": selected.family, "profile": selected.profile,
                   "build": str(selected.build), "input_manifest": pin(selected.manifest_raw),
                   "sources": {n: pin(d) for n, d in selected.files.items()},
                   "original_compiler_native": selected.old_native, "flags": list(selected.flags),
                   "attempts": [], "engine_executed": False}
            report["profiles"].append(row)
            if selected.family == "D":
                # GCC -MF shared by several source files is overwritten by the
                # last unit. Discover each frozen unit explicitly before the
                # two real compiles, rather than claiming a complete union.
                for name in selected.units:
                    dep = directory / ("unit-" + name + ".d")
                    host.run([compiler, *selected.flags, "-M", "-MF", dep, frozen / name], cwd=directory,
                             kind="D-dependencies-" + name)
                    for path in dependency_paths(dep.read_bytes(), owned_root=directory,
                                                 input_roots=input_roots):
                        if within(path, input_roots):
                            record_input(sdk_files, path)
                row["per_unit_dependency_discovery"] = list(selected.units)
            images = []
            for attempt in ("dependency-discovery", "first", "repeat", "target-types"):
                target = directory / attempt
                target.mkdir()
                data = selected.files["main.c"]
                if attempt == "target-types":
                    data += ("\n" + "\n".join(selected.assertions) + "\n").encode()
                flags = list(selected.flags)
                if selected.family == "D":
                    (target / "main.c").write_bytes(data)
                    command = [compiler, *flags, str(target / "main.c"), str(frozen / "start.S"),
                               "-Wl,-T," + str(frozen / "image.ld"), "-o", "x"]
                    stdin = None
                else:
                    command, stdin = [compiler, *flags], data
                command += ["-MD", "-MF", str(target / "dependencies.d"), "-Wl,-t"]
                trace = host.run(command, cwd=target, kind=selected.family + "-" + attempt, data=stdin)
                image = regular(target / "x")
                dependencies = dependency_paths((target / "dependencies.d").read_bytes(),
                    input_roots=input_roots, owned_root=directory)
                for line in trace.decode().splitlines():
                    candidate = Path(line.strip())
                    if candidate.is_absolute():
                        candidate = candidate.resolve()
                        require(within(candidate, [*input_roots, out]),
                                "link input escaped SDK and owned compiler output")
                        if candidate.is_file():
                            dependencies.add(candidate)
                for path in dependencies:
                    if within(path, input_roots):
                        record_input(sdk_files, path)
                row["attempts"].append({"directory": attempt, "native": pin(image),
                                         "dependencies": sorted(map(str, dependencies))})
                images.append(image)
                if attempt == "dependency-discovery":
                    row["dependency_discovery_precedes_two_fresh_compiles"] = True
            require(all(image == images[0] for image in images[1:]),
                    "target native/type-gate bytes did not reproduce")
            row.update(native=pin(images[1]), elf=elf_abi(images[1], verify),
                       native_reproduced=True, type_assertions_native_identical=True,
                       cross_compiler_native_identity_required=False)
            save()
        for selected in sources:
            require(regular(selected.build / "build.json", limit=8 << 20) == selected.manifest_raw,
                    "source build manifest changed during target compilation")
            for name, data in selected.files.items():
                source_path = selected.build / ("shipping-inputs" if selected.family == "D" else "") / name
                require(regular(source_path) == data, "actual production C input changed during compilation")
        require(all(normalized(ROOT / name) == data for name, data in tools.items()),
                "compiler verifier tools changed during execution")
        require(all(pin(regular(Path(path))) == expected for path, expected in sdk_files.items()),
                "SDK consumed input changed after compilation")
        require(current_context() == sdk,
                "audited SDK descriptor changed during compilation")
        report["compiler_consumed_inputs"] = sdk_files
        report["complete"] = True
        report["six_submission_profiles_compiled"] = {
            (s.family, s.profile) for s in sources} == {(f, "tcec-provisional") for f in "ABCDEF"}
    except BaseException as error:
        report["error"] = str(error)
        raise
    finally:
        try:
            host.close()
        except BaseException:
            report["complete"] = False
            raise
        finally:
            signal.signal(signal.SIGCHLD, previous)
            if temporary is None:
                os.environ.pop("TMPDIR", None)
            else:
                os.environ["TMPDIR"] = temporary
            save()
    print(json.dumps({"complete": report["complete"], "profiles": len(sources),
                      "six_submission_profiles_compiled": report["six_submission_profiles_compiled"],
                      "engine_executed": False, "receipt": str(out / "compiler.json")}))


if __name__ == "__main__":
    main()
