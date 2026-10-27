#!/usr/bin/env python3
"""Finite B/F profile header costs; no engine, rules probe or TT is executed.

Ubuntu 24 creates a fresh strict original GCC13 parent. Ubuntu 22 re-admits
that exact owned artifact and never rebuilds its factory or runs its tools.
Only the two named compiler-option deletions are candidates. Target-native
identity and reused-payload wrapper costs are observations, not selection or
runtime qualification, and do not change any production compiler whitelist.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import signal
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREFIX = "engines/experiments/tcec-next/"
SELF = PREFIX + "header_cost.py"
COST = PREFIX + "terminal_cost.py"
BUILDER = PREFIX + "profile_build.py"
VERIFIER = PREFIX + "profile_verify.py"
DEPENDENCIES = PREFIX + "profile_dependencies.py"
WRAPPER = PREFIX + "wrapper.py"
UNLINK = PREFIX + "self_unlink.py"
OWNER = "engines/experiments/tcec-scope/build.py"
UTILITY = "engines/experiments/tiny-d-submission/structural_size.py"
PACKAGE = "engines/scripts/source_package.py"
PRODUCTION = "engines/scripts/production.py"
READERS = ("engines/scripts/production_input.py", "engines/scripts/source_composition.py")
SUPPORT = (SELF, COST, BUILDER, VERIFIER, DEPENDENCIES, WRAPPER, UNLINK,
           OWNER, UTILITY, PACKAGE, PRODUCTION, *READERS)
CLASS = "rove4k-BF-header-cost-v1"
PROFILE = "test-p4"
PROFILES = (PROFILE, "test-p28", "tcec-provisional")
MAX_FILE = 16 << 20
COMPILERS = {
    "B": ("cc", "-std=c11", "-Os", "-pthread", "-x", "c", "-", "-o", "x"),
    "F": ("cc", "-Os", "-pthread", "-x", "c", "-", "-o", "x", "-s"),
}
CONTROL = {
    "B": {
        "source": (7934, "09546a75f5e417125ec033994fec52b1e23da4d504e5146a54cead53966136ce"),
        "native": (25744, "89b695055e8fbcdfd64f9cfd07e127180eb9827e4245631afd0525d2e0609e29"),
        "header": (109, "579c456c8ca9af8acde4bc4a41307807bc85d76d11b56ec5fcdcaa7e304ed911"),
        "payload": (3962, "2ff39681818973f97a03591af52d7ac77c6363aedd2e9df879e1e937d08f790e"),
        "whole": (4071, "c64753dc77b2c287d13612f985ed4c77d53caafc532530169ec328ee577dbeae"),
    },
    "F": {
        "source": (7030, "0aa062ec8440911d094a1b4eea48eceb96facfaa4ce94d654f46bfa19c83c7f0"),
        "native": (18568, "5b4e662a29f7a989c8b7a81f8a41e46a96df5c3e805f4b7b29929b6a2725ae50"),
        "header": (103, "de8e199aa72661012417d5a9004e3c4c5079d704d6558286bd282319c078a8a0"),
        "payload": (3484, "f31169149c99192d914e906dd13b601975e490528657cbec04371b3a14c34760"),
        "whole": (3587, "c4e5be74f6aed58b7407444119e4de834f9ee3e4c9e99998922685a4f80fd343"),
    },
}
# P28 is the named 40494326732 B/F archive data; W256 is the fresh 40476243172
# B/F data. Every literal was checked against all five actual original parts.
PROFILE_CONTROL = {
    ("B", PROFILE): CONTROL["B"],
    ("F", PROFILE): CONTROL["F"],
    ("B", "test-p28"): {
        "source": (7962, "326e18b0b480a42c16ab0c4ec06ff90770842aec2bd8c9e1ea91f70be9427eb6"),
        "native": (25744, "755dffaf68cb2eff582260550f6c7a174bb09de9e5bf7a773f311c7c1dce9a24"),
        "header": (109, "579c456c8ca9af8acde4bc4a41307807bc85d76d11b56ec5fcdcaa7e304ed911"),
        "payload": (3972, "987817e100c9371abe9bcbbdc7507f507e5ba1259d8a57fe788d470a55599b27"),
        "whole": (4081, "93634a5bb12dcef46e7e80242982511de3ef62db1e60c70ee082b24186f30123"),
    },
    ("F", "test-p28"): {
        "source": (7063, "5a016f252e8efb4faf356de92397964d19e6c5e95863e063a5179864988dcdc5"),
        "native": (18568, "843bbc1ea78ef68c4cde578df93218f6d36b5f3c48cfa794ba6022b75e949262"),
        "header": (103, "de8e199aa72661012417d5a9004e3c4c5079d704d6558286bd282319c078a8a0"),
        "payload": (3499, "81905d60d0ba5f9ed48d307ad3281c503ec2c2099405f0c2c7dc40f9a1ab82ca"),
        "whole": (3602, "7c5b930a2a113a2cc294e97d56457896418f90b3df90eebfccba489b61342baa"),
    },
    ("B", "tcec-provisional"): {
        "source": (7936, "5f64922b49923ef9637dc41328761a4c3f4eb0063e39bd9f04c46e3d19c9b62d"),
        "native": (25744, "db780f8318783991535a56e3d26f3d9e18e3a139fdbd9f0ced56784f7f236613"),
        "header": (109, "579c456c8ca9af8acde4bc4a41307807bc85d76d11b56ec5fcdcaa7e304ed911"),
        "payload": (3963, "e680022b57423066591d73d18918b3edb71e9e72669240ca6613ff7b69b9b180"),
        "whole": (4072, "2f1cd9e6559594fa6142188df851c8ff6a8e57edd4de49c14fcdbbb67214f6b6"),
    },
    ("F", "tcec-provisional"): {
        "source": (7032, "7701b38ad0957066d427bb085575f26b511691a6ea60e67f44835ce9359db9df"),
        "native": (18568, "e536de10e8792573548864d6267e8ce3cde76102b6134552f9dbca0d2672437b"),
        "header": (103, "de8e199aa72661012417d5a9004e3c4c5079d704d6558286bd282319c078a8a0"),
        "payload": (3486, "90405436b74f2dc5e72a45340aff53b22a6c5845d8db40e4b62f890b268575b6"),
        "whole": (3589, "28f3f9024443b7dd63955b543ed2e6849905e1d0767a52c1d35ff51017889f30"),
    },
}
COMPILER_ENV = ("GCC_EXEC_PREFIX", "COMPILER_PATH", "LIBRARY_PATH", "CPATH", "C_INCLUDE_PATH",
                "CPLUS_INCLUDE_PATH", "OBJC_INCLUDE_PATH", "LD_PRELOAD", "LD_LIBRARY_PATH")
CONTEXT_MACROS = ("__GNUC__", "__GNUC_MINOR__", "__GLIBC__", "__GLIBC_MINOR__", "__STDC_VERSION__",
                  "__STRICT_ANSI__", "_REENTRANT", "_POSIX_C_SOURCE", "_GNU_SOURCE", "_DEFAULT_SOURCE",
                  "__x86_64__", "__SIZEOF_POINTER__", "__SIZEOF_SIZE_T__", "__SIZEOF_INT__",
                  "__SIZEOF_LONG__", "__STDC_HOSTED__")
_EXECUTING_CODE = sys._getframe().f_code


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(data):
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


def expected(pair):
    return {"bytes": pair[0], "sha256": pair[1]}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def plan(family, mode, *, profile=PROFILE):
    require(type(family) is str and family in COMPILERS and type(mode) is str
            and mode in ("producer", "replay"), "finite B/F producer/replay header trial required")
    require(type(profile) is str and profile in PROFILES, "finite named header profile required")
    compiler = list(COMPILERS[family])
    minimal = [arg for arg in compiler if arg not in (("-std=c11", "-pthread") if family == "B" else ("-pthread",))]
    return dict(family=family, profile=profile, mode=mode, cases=["control", "minimal"], compiler=compiler,
        minimal_compiler=minimal, control={name: expected(value) for name, value in PROFILE_CONTROL[family, profile].items()},
        header_delta=-18 if family == "B" else -9, expected_commands=13 if mode == "producer" else 12,
        GCC_major=13 if mode == "producer" else 11, os_version="24.04" if mode == "producer" else "22.04",
        libc="2.39" if mode == "producer" else "2.35", source_changed=False, payload_recompressed=False)


def factory_argv(family, output, *, profile=PROFILE):
    plan(family, "producer", profile=profile)
    return [sys.executable, "-I", "-B", str(ROOT / BUILDER), "--entry", family,
        "--profile", profile, "--representation", "source-jit", "--b-variant",
        "tcec-final-lf" if family == "B" else "control", "--phase-variant",
        "control" if family == "B" else "phase-init", "--spelling-variant",
        "best" if family == "B" else "compound-v2", "--source-dependencies", "unused-includes",
        "--ep-variant", "control", "--out", str(output)]


def parse_macros(data):
    require(type(data) is bytes and b"\r" not in data, "LF compiler macro bytes required")
    result = {}
    for line in data.decode("ascii").splitlines():
        require(line.startswith("#define "), "compiler macro dump contains another output mode")
        name, _, value = line[8:].partition(" ")
        require(name and name not in result, "duplicate/empty compiler macro")
        result[name] = value
    require(result, "empty actual compiler macro dump")
    return result


def macro_observation(family, mode, old_bytes, new_bytes, *, profile=PROFILE):
    policy = plan(family, mode, profile=profile)
    old, new = parse_macros(old_bytes), parse_macros(new_bytes)
    common = {"__GNUC__": str(policy["GCC_major"]), "__GLIBC__": "2",
        "__GLIBC_MINOR__": policy["libc"].split(".")[1], "_POSIX_C_SOURCE": "200809L",
        "__x86_64__": "1", "__SIZEOF_POINTER__": "8", "__SIZEOF_SIZE_T__": "8",
        "__SIZEOF_INT__": "4", "__SIZEOF_LONG__": "8", "__STDC_HOSTED__": "1"}
    for record in (old, new):
        require(all(record.get(name) == value for name, value in common.items())
                and re.fullmatch(r"\d+", record.get("__GNUC_MINOR__", "")) is not None,
                "actual system GCC/glibc/POSIX/LP64 macro context differs")
        require(all(name not in record for name in ("_GNU_SOURCE", "_DEFAULT_SOURCE", "__cplusplus")),
                "header trial does not admit GNU/default-source or C++ feature injection")
    require(old.get("_REENTRANT") == "1" and "_REENTRANT" not in new,
            "actual pthread predefinition differs")
    require(old.get("__STDC_VERSION__") == ("201112L" if family == "B" else "201710L")
            and new.get("__STDC_VERSION__") == "201710L"
            and old.get("__STRICT_ANSI__") == ("1" if family == "B" else None)
            and "__STRICT_ANSI__" not in new, "actual C11/GNU17 context differs")
    return dict(selected={label: {name: record.get(name) for name in CONTEXT_MACROS}
                          for label, record in (("control", old), ("minimal", new))},
        differences={name: {"control": old.get(name), "minimal": new.get(name)}
                     for name in sorted(set(old) | set(new)) if old.get(name) != new.get(name)},
        scope="context diagnostics only; complete actual CPP and native equality are separate gates")


def source_context(source, *, family, profile=PROFILE):
    policy = plan(family, "producer", profile=profile)
    require(type(source) is bytes and pin(source) == policy["control"]["source"], "exact full original named profile source required")
    directive = b"#define _POSIX_C_SOURCE 200809L\n"
    require(source.count(directive) == 1 and source.index(directive) < source.index(b"#include")
            and not re.search(rb"(?m)^\s*#\s*(if|ifdef|ifndef|elif)\b", source),
            "closed POSIX2008 source premises differ")
    require(not re.search(rb"\b(_GNU_SOURCE|_REENTRANT|__STRICT_ANSI__|__STDC_VERSION__|dlopen|dlsym|readlink)\b", source)
            and b"/proc" not in source, "source consumes an excluded feature/self-loading distinction")
    return dict(source=pin(source), POSIX_C_SOURCE=200809, direct_conditional_consumers=False,
                source_changed=False, model_or_resource_change=False)


def candidate_header(control_header, generated_header, *, family, profile=PROFILE):
    policy = plan(family, "producer", profile=profile)
    require(type(control_header) is bytes and type(generated_header) is bytes
            and pin(control_header) == policy["control"]["header"], "exact original wrapper header required")
    result = control_header
    for token in ((b" -std=c11", b" -pthread") if family == "B" else (b" -pthread",)):
        require(result.count(token) == 1, "unique finite compiler-option deletion required")
        result = result.replace(token, b"", 1)
    require(result == generated_header and len(result) - len(control_header) == policy["header_delta"]
            and len(result.splitlines()) == len(control_header.splitlines()) == 5
            and result.splitlines()[:3] == control_header.splitlines()[:3]
            and result.splitlines()[4:] == control_header.splitlines()[4:]
            and result.count(b'tail -n+6 "$0"|xz -d|') == 1,
            "candidate header changed more than the exact compiler flags")
    minimal = b"|cc -Os "
    original = b"|cc -std=c11 -Os -pthread " if family == "B" else b"|cc -Os -pthread "
    require(result.count(minimal) == 1 and result.replace(minimal, original, 1) == control_header,
            "complete header inverse differs")
    return result


def ci_context(env):
    require(env.get("GITHUB_ACTIONS") == "true" and env.get("GITHUB_REPOSITORY") == "daejunnom/Rove4k"
            and env.get("GITHUB_REPOSITORY_OWNER") == "daejunnom",
            "explicit Rove4k GitHub Actions artifact context required")
    sha = env.get("GITHUB_SHA", "")
    workflow_ref = env.get("GITHUB_WORKFLOW_REF", "")
    prefix = "daejunnom/Rove4k/.github/workflows/header-cost.yml@refs/"
    require(re.fullmatch(r"[0-9a-f]{40}", sha) is not None
            and all(re.fullmatch(r"[1-9][0-9]*", env.get(name, "")) is not None
                    for name in ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT"))
            and env.get("GITHUB_WORKFLOW") == "Experimental compiler header cost"
            and workflow_ref.startswith(prefix) and len(workflow_ref) > len(prefix)
            and not any(char in workflow_ref for char in "\0\r\n"), "complete live source artifact context required")
    return dict(repository=env["GITHUB_REPOSITORY"], sha=sha, run_id=env["GITHUB_RUN_ID"],
                run_attempt=env["GITHUB_RUN_ATTEMPT"], workflow=env["GITHUB_WORKFLOW"],
                owner=env["GITHUB_REPOSITORY_OWNER"], workflow_ref=workflow_ref)


def read_source(path):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= MAX_FILE,
            "bounded named source file required")
    data = path.read_bytes().replace(b"\r\n", b"\n")
    require(b"\r" not in data, "lone CR in named source")
    return data


def load_bytes(name, logical, data):
    spec = importlib.util.spec_from_file_location(name, ROOT / logical)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    exec(compile(data, str(ROOT / logical), "exec", dont_inherit=True), module.__dict__)
    return module


def capture():
    files = {name: read_source(ROOT / name) for name in SUPPORT}
    require(compile(files[SELF], _EXECUTING_CODE.co_filename, "exec", dont_inherit=True) == _EXECUTING_CODE,
            "executing header controller differs from captured source")
    common = load_bytes("header_cost_common", COST, files[COST])
    require(compile(files[COST], common._EXECUTING_CODE.co_filename, "exec", dont_inherit=True) == common._EXECUTING_CODE,
            "executing shared cost owner differs from captured source")
    return files, common


def measure(family, out, *, mode, producer=None, execute=False, profile=PROFILE):
    require(execute is True, "explicit --execute required before source capture or output creation")
    policy = plan(family, mode, profile=profile)
    require((producer is None) == (mode == "producer"), "only replay requires its explicit producer artifact root")
    require(sys.platform == "linux" and platform.machine() == "x86_64", "Linux x86-64 required")
    import resource
    started = time.monotonic()
    inherited = {"CPU": resource.getrlimit(resource.RLIMIT_CPU), "AS": resource.getrlimit(resource.RLIMIT_AS),
                 "FSIZE": resource.getrlimit(resource.RLIMIT_FSIZE)}
    files, common = capture()
    applied = common.limit_plan(inherited["CPU"], inherited["AS"], inherited["FSIZE"])
    utility = load_bytes("header_cost_utility", UTILITY, files[UTILITY])
    out = utility.new_output(out)
    out.mkdir(parents=True)
    for name, data in files.items():
        common.write(out / "support", name, data)
    report = dict(format=1, **{"class": CLASS}, family=family, mode=mode, policy=policy, complete=False,
        reproducible=False, support={name: pin(data) for name, data in files.items()}, commands=[], attempts=[],
        outer_command_limit=14, engine_executed=False, TT_allocated=False, runtime_qualified=False,
        qualification=False, selected=False, payload_recompressed=False,
        scope="same-source compiler/header trial; replay package bytes reuse the original GCC13 producer payload",
        limits={**applied, "inherited": inherited, "work_seconds": 600, "cleanup_budget_seconds": 30,
                "combined_stdio_bytes": MAX_FILE})

    def save():
        (out / "result.json").write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")

    save()
    host = owner = None
    old_limits = body_error = None
    previous_chld = signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    try:
        resource.setrlimit(resource.RLIMIT_FSIZE, applied["FSIZE"])
        owner = load_bytes("header_cost_process_owner", OWNER, files[OWNER])
        require(owner.EXECUTING_BUILD == files[OWNER], "process owner reread changed")
        old_limits = dict(owner.LIMITS)
        remaining = math.floor(600 - (time.monotonic() - started))
        require(remaining > 0, "header work budget expired before Host construction")
        owner.LIMITS.update(aggregate_wall=remaining, per_command_wall=600,
            parent_AS=applied["parent_AS"], parent_CPU=applied["parent_CPU"][0],
            parent_CPU_hard=applied["parent_CPU"][1], tool_output_bytes=MAX_FILE)

        class Host(owner.Host):
            def settle(self, child, row, force=False):
                if row.get("kind") == "fresh-profile":
                    row["cooperative_termination_seconds"] = 15
                return super().settle(child, row, force)

        host = Host(out, report, save)
        report["limits"].update(aggregate_work_alarm_seconds=remaining,
            actual_parent_CPU=resource.getrlimit(resource.RLIMIT_CPU),
            actual_parent_AS=resource.getrlimit(resource.RLIMIT_AS),
            actual_FSIZE=resource.getrlimit(resource.RLIMIT_FSIZE))
        R = load_bytes("header_cost_strict_R", VERIFIER, files[VERIFIER])
        dependencies = load_bytes("header_cost_dependencies", DEPENDENCIES, files[DEPENDENCIES])
        wrapper = load_bytes("header_cost_wrapper", WRAPPER, files[WRAPPER])
        unlink = load_bytes("header_cost_unlink", UNLINK, files[UNLINK])
        package = load_bytes("header_cost_package", PACKAGE, files[PACKAGE])
        reader = R.input_reader()
        ci = ci_context(os.environ)
        require(not any(os.environ.get(name) for name in COMPILER_ENV), "compiler redirection environment is not admitted")
        release_path = Path("/etc/os-release").resolve(strict=True)
        release = reader.read_regular(release_path, limit=16384, allow_hardlinks=True)
        fields = {}
        for line in release.decode("ascii").splitlines():
            if "=" in line:
                name, value = line.split("=", 1)
                if name in ("ID", "VERSION_ID"):
                    tokens = shlex.split(value)
                    require(len(tokens) == 1, "ordinary OS identity required")
                    fields[name] = tokens[0]
        libc = os.confstr("CS_GNU_LIBC_VERSION")
        require(fields == {"ID": "ubuntu", "VERSION_ID": policy["os_version"]}
                and libc == "glibc " + policy["libc"], "actual Ubuntu/glibc context differs")
        compiler_path = Path(shutil.which("cc") or "").resolve(strict=True)
        require(compiler_path.is_relative_to(Path("/usr/bin")) and compiler_path.is_file(), "installed system compiler required")
        compiler_data = reader.read_regular(compiler_path, limit=MAX_FILE, allow_hardlinks=True)
        banner_raw = common.run_command(host, owner, ["cc", "--version"], cwd=out, kind="compiler-version")
        version_raw = common.run_command(host, owner, ["cc", "-dumpfullversion"], cwd=out, kind="compiler-full-version")
        require(all(row["stderr"]["bytes"] == 0 for row in report["commands"][-2:]), "compiler context query emitted diagnostics")
        banner, version = banner_raw.decode("ascii").splitlines()[0], version_raw.decode("ascii").strip()
        require(re.fullmatch(str(policy["GCC_major"]) + r"\.\d+(?:\.\d+)?", version) is not None
                and "Ubuntu " + str(policy["GCC_major"]) + "." in banner,
                "actual system GCC version differs")
        if mode == "producer":
            require(banner == common.BANNER, "strict producer compiler banner differs")
        report.update(ci=ci, host_context=dict(os_release={**fields, **pin(release)}, libc=libc,
            compiler={"path": str(compiler_path), **pin(compiler_data)}, banner=banner, full_version=version,
            python=sys.version, uname=list(os.uname()), cpu_affinity=sorted(os.sched_getaffinity(0))))
        producer_raw = producer_record = None
        if mode == "producer":
            baseline = out / "fresh-profile"
            common.run_command(host, owner, factory_argv(family, baseline, profile=profile), cwd=out, kind="fresh-profile", factory=True)
        else:
            producer = Path(producer)
            require(producer.is_absolute() and ".." not in producer.parts
                    and producer.is_dir() and producer.stat().st_uid == os.getuid()
                    and not out.is_relative_to(producer) and not producer.is_relative_to(out)
                    and not any(p.is_symlink() or (p / ".git").exists() for p in (producer, *producer.parents)),
                    "explicit external owned producer artifact root required")
            producer_raw = reader.read_regular(R.artifact_file(producer, "result.json"), limit=MAX_FILE)
            producer_record = json.loads(producer_raw)
            utility.require_settled_cost(producer_record)
            require(producer_record.get("format") == 1 and producer_record.get("class") == CLASS
                    and producer_record.get("family") == family and producer_record.get("mode") == "producer"
                    and producer_record.get("policy") == plan(family, "producer", profile=profile)
                    and producer_record.get("ci") == ci and producer_record.get("reproducible") is True
                    and producer_record.get("engine_executed") is False and producer_record.get("TT_allocated") is False
                    and common.settled(producer_record.get("commands"))
                    and len(producer_record["commands"]) == plan(family, "producer", profile=profile)["expected_commands"],
                    "matching completed original producer artifact required")
            require(producer_record["support"] == {name: pin(data) for name, data in files.items()}
                    and all(reader.read_regular(R.artifact_file(producer, "support/" + name), limit=MAX_FILE) == data
                            for name, data in files.items()), "producer support is not this frozen/current source cohort")
            baseline = producer / "fresh-profile"
            report["producer_artifact"] = dict(result=pin(producer_raw), source_root="fresh-profile",
                original_host_context=producer_record["host_context"], original_ci=producer_record["ci"],
                tools_executed_from_artifact=False, factory_rebuilt=False)
        raw = reader.read_regular(R.artifact_file(baseline, "build.json"), limit=MAX_FILE)
        manifest = json.loads(raw)
        admitted = R.admit_c_build(manifest, baseline)
        control_raw = R.checked_artifact(baseline, "control/build.json", manifest["control"]["report"])
        control_manifest = json.loads(control_raw)
        for record, kind in ((manifest, "rove4k-production-profile-v1"), (control_manifest, "tcec-full-C-v1")):
            require(type(record.get("format")) is int and record["format"] == 1 and record.get("class") == kind
                    and record.get("family") == family and record.get("entry") == family
                    and record.get("complete") is True and record.get("reproducible") is True
                    and common.settled(record.get("commands"))
                    and record.get("host_cleanup") == {"unsettled_commands": 0, "errors": []},
                    "original strict factory receipt is incomplete")
        require(admitted.family == family and admitted.profile_id == profile and admitted.full is True
                and admitted.representation == "source-jit" and manifest["plan"]["entry_cleanup"] == "private-path"
                and manifest["compiler"] == policy["compiler"] and manifest["compile_executor"] == policy["compiler"]
                and manifest["compile_executor_version"] == common.BANNER,
                "original GCC13 parent context differs")
        parts = {name: R.checked_artifact(baseline, path, policy["control"][name]) for name, path in
                 (("source", "main.c"), ("native", "native/x"), ("header", "header.sh"),
                  ("payload", "payload.lzma"), ("whole", "x"))}
        require(parts["whole"] == parts["header"] + parts["payload"], "original whole parts differ")
        common.restored_payload(parts["whole"], parts["header"], parts["source"])
        premises = source_context(parts["source"], family=family, profile=profile)
        inputs = {name: R.checked_artifact(baseline, "inputs/" + name, value)
                  for name, value in admitted.input_pins.items()}
        require(all(data == R.source_bytes(name, admitted.input_pins[name]) for name, data in inputs.items()),
                "original complete source closure is not current")
        require(all(name in inputs for name in (BUILDER, VERIFIER, DEPENDENCIES, WRAPPER, UNLINK, PACKAGE, PRODUCTION, OWNER)),
                "original factory owner is missing")
        require(all(name not in inputs or inputs[name] == data for name, data in files.items()),
                "original and derived source owners conflict")
        closure = {**inputs, **files}
        if producer_record is not None:
            require(producer_record.get("factory_manifest") == pin(raw)
                    and producer_record.get("control_manifest") == pin(control_raw)
                    and producer_record.get("factory_inputs") == {name: pin(data) for name, data in inputs.items()},
                    "replayed original manifest or complete closure differs from producer")
        report.update(factory_manifest=pin(raw), control_manifest=pin(control_raw), original_control=policy["control"],
            factory_inputs={name: pin(data) for name, data in inputs.items()}, source_closure={name: pin(data) for name, data in closure.items()},
            original_resources=admitted.resources, original_compiler=manifest["compiler"],
            original_compiler_version=manifest["compile_executor_version"], source_premises=premises,
            original_factory_commands=manifest["commands"], original_control_commands=control_manifest["commands"],
            nested_command_counts={"profile": len(manifest["commands"]), "selected_control": len(control_manifest["commands"]),
                                   "exhaustive_physical_process_count": False})
        macro_outputs = {}
        for case, command in (("control", policy["compiler"]), ("minimal", policy["minimal_compiler"])):
            flags = [flag for flag in dependencies.preprocess_command(command) if flag != "-P"] + ["-dM"]
            data = common.run_command(host, owner, flags, cwd=out, kind=case + "-predefinitions", data=parts["source"])
            require(report["commands"][-1]["stderr"]["bytes"] == 0, "macro dump emitted diagnostics")
            common.write(out / "context", case + ".macros", data)
            macro_outputs[case] = data
        macros = macro_observation(family, mode, macro_outputs["control"], macro_outputs["minimal"], profile=profile)
        require(all(macros["selected"][case]["__GNUC_MINOR__"] == version.split(".")[1]
                    for case in ("control", "minimal")),
                "actual version command and compiler macros disagree")
        report["macros"] = dict(**macros, outputs={name: pin(data) for name, data in macro_outputs.items()})
        binaries, expansions, tables = [], [], []
        for case, command in (("control", policy["compiler"]), ("minimal", policy["minimal_compiler"])):
            for attempt in ("first", "repeat"):
                target = out / case / attempt
                target.mkdir(parents=True)
                common.write(target, "main.c", parts["source"])
                cpp = common.run_command(host, owner, dependencies.preprocess_command(command), cwd=target,
                                         kind=case + "-" + attempt + "-CPP", data=parts["source"])
                common.run_command(host, owner, command, cwd=target, kind=case + "-" + attempt + "-native", data=parts["source"])
                require(all(row["stderr"]["bytes"] == 0 for row in report["commands"][-2:]), "actual compiler emitted diagnostics")
                native = reader.read_regular(target / "x", limit=MAX_FILE)
                table = R.native_dependencies(native)
                common.write(target, "expanded.i", cpp)
                binaries.append(native)
                expansions.append(cpp)
                tables.append(table)
                report["attempts"].append(dict(case=case, attempt=attempt, source=pin(parts["source"]),
                    CPP=pin(cpp), native=pin(native), dependencies=table, compiler=command))
                save()
        require(all(data == expansions[0] for data in expansions), "complete repeated control/candidate CPP differs")
        require(all(data == binaries[0] for data in binaries) and all(table == tables[0] for table in tables),
                "complete repeated control/candidate native or dependency table differs")
        if mode == "producer":
            require(binaries[0] == parts["native"], "actual GCC13 original native differs from strict parent")
        old_header = wrapper.header(package, unlink, policy["compiler"])
        require(old_header == parts["header"], "actual original wrapper differs")
        new_header = candidate_header(old_header, wrapper.header(package, unlink, policy["minimal_compiler"]),
                                      family=family, profile=profile)
        new_whole = new_header + parts["payload"]
        common.restored_payload(new_whole, new_header, parts["source"])
        require(new_whole[len(new_header):] == parts["payload"]
                and len(new_whole) - len(parts["whole"]) == policy["header_delta"], "exact reused-payload whole delta differs")
        for case, header, whole in (("control", old_header, parts["whole"]), ("minimal", new_header, new_whole)):
            for name, data in (("main.c", parts["source"]), ("header.sh", header),
                               ("payload.lzma", parts["payload"]), ("x", whole)):
                common.write(out / "packages" / case, name, data)
                require(reader.read_regular(out / "packages" / case / name, limit=MAX_FILE) == data,
                        "actual written source/header/payload/whole differs")
        require(len(report["commands"]) == policy["expected_commands"] and common.settled(report["commands"]),
                "finite header command schedule did not settle cleanly")
        require(reader.read_regular(R.artifact_file(baseline, "build.json"), limit=MAX_FILE) == raw,
                "original factory receipt changed")
        R.admit_c_build(manifest, baseline)
        require(all((name not in inputs or R.checked_artifact(baseline, "inputs/" + name, admitted.input_pins[name]) == data
                     == R.source_bytes(name, admitted.input_pins[name])) and
                    (name not in files or read_source(ROOT / name) == data
                     and reader.read_regular(out / "support" / name, limit=MAX_FILE) == data)
                    for name, data in closure.items()), "complete current/frozen source closure changed")
        if producer_record is not None:
            require(reader.read_regular(R.artifact_file(producer, "result.json"), limit=MAX_FILE) == producer_raw
                    and all(reader.read_regular(R.artifact_file(producer, "support/" + name), limit=MAX_FILE) == data
                            for name, data in files.items()), "original producer artifact changed during replay")
        require(ci_context(os.environ) == ci and os.confstr("CS_GNU_LIBC_VERSION") == libc
                and reader.read_regular(release_path, limit=16384, allow_hardlinks=True) == release
                and Path(shutil.which("cc") or "").resolve(strict=True) == compiler_path
                and reader.read_regular(compiler_path, limit=MAX_FILE, allow_hardlinks=True) == compiler_data
                and not any(os.environ.get(name) for name in COMPILER_ENV), "actual compiler/host context changed")
        report.update(reproducible=True, CPP_equal=True, native_equal=True, dependency_tables_equal=True,
            producer_native_equal=True if mode == "producer" else None, actual_native=pin(binaries[0]),
            packages={"control": {"header": pin(old_header), "payload": pin(parts["payload"]), "whole": pin(parts["whole"])},
                      "minimal": {"header": pin(new_header), "payload": pin(parts["payload"]), "whole": pin(new_whole)}},
            wrapper_contract=wrapper.contract(package, unlink, policy["minimal_compiler"]),
            whole_delta=policy["header_delta"], original_payload_reused=True, header_full_inverse=True,
            cross_host_native_identity_claimed=False,
            package_scope="original producer payload plus finite header deletion; replay does not claim a newly produced Ubuntu22 payload")
    except BaseException as error:
        body_error = error
        report["failure"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        try:
            utility.finish_report(host, report, save, body_error)
        finally:
            if owner is not None and old_limits is not None:
                owner.LIMITS.clear()
                owner.LIMITS.update(old_limits)
            signal.signal(signal.SIGCHLD, previous_chld)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entry", choices=("B", "F"), required=True)
    parser.add_argument("--mode", choices=("producer", "replay"), required=True)
    parser.add_argument("--profile", choices=PROFILES, default=PROFILE)
    parser.add_argument("--producer", type=Path, help="explicit complete original producer output, replay only")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        parser.error("--execute is required before source capture or output creation")
    result = measure(args.entry, args.out, mode=args.mode, producer=args.producer, execute=True, profile=args.profile)
    print(json.dumps({"class": CLASS, "family": args.entry, "mode": args.mode,
                      "complete": result["complete"], "whole_delta": result["whole_delta"]}, sort_keys=True))


if __name__ == "__main__":
    main()
