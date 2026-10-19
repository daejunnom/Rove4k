#!/usr/bin/env python3
"""Build all independent C/Rust A-F engines and measure complete deployment files.

Run on Linux. --out must be an absolute directory outside this checkout. Large
target profiles are compile-only here; a profile is not runtime validation.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

from minify import compact_source
from pack import write_launchers
from specialize import specialize_c


ROOT = Path(__file__).resolve().parents[2]
PROFILES = ROOT / "engines/profiles/fixed.json"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def run(command, *, cwd=None, env=None, timeout=180, input=None):
    started = time.monotonic()
    process = subprocess.run(command, cwd=cwd, env=env, input=input,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             timeout=timeout)
    record = {"command": list(map(str, command)), "returncode": process.returncode,
              "wall_seconds": time.monotonic() - started,
              "stdout": process.stdout.decode(errors="replace"),
              "stderr": process.stderr.decode(errors="replace")}
    if process.returncode:
        raise RuntimeError(json.dumps(record, indent=2))
    return record


def tool_version(command):
    return run([command, "--version"])["stdout"].strip()


def source_files(language):
    directory = ROOT / "engines" / language
    extensions = (".c", ".h") if language == "c" else (".rs",)
    files = {str(path.relative_to(directory.parent)).replace(os.sep, "/"): path.read_bytes()
             for path in sorted(directory.rglob("*")) if path.is_file() and path.suffix in extensions}
    shared = directory.parent / "model"
    if shared.exists():
        files.update({str(path.relative_to(directory.parent)).replace(os.sep, "/"): path.read_bytes()
                      for path in sorted(shared.rglob("*")) if path.is_file() and path.suffix in extensions})
    required = any(name.endswith(".c") for name in files) if language == "c" else "rust/main.rs" in files
    if not required:
        raise ValueError(f"no complete {language} engine source in {directory}")
    return files


def write_files(files, directory):
    directory.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def compiler_recipe(language, variant, profile, optimize, *, compiler, files, parallel=0, model=False):
    development = int(profile["development"])
    workers, bits = profile["search_workers"], profile["tt_bits"]
    environment = {"ROVE_VARIANT": variant, "ROVE_WORKERS": str(workers),
                   "ROVE_TT_BITS": str(bits), "ROVE_DEV": str(development),
                   "ROVE_PARALLEL": str(parallel), "ROVE_MODEL": str(int(model)),
                   "SOURCE_DATE_EPOCH": "0", "LC_ALL": "C", "TZ": "UTC"}
    if language == "c":
        flags = ["-std=c11", "-Os" if optimize == "size" else "-O2", "-pthread",
                 f"-DROVE_VARIANT={ord(variant) - ord('A') + 1}",
                 f"-DROVE_WORKERS={workers}", f"-DROVE_TT_BITS={bits}", f"-DROVE_DEV={development}",
                 f"-DROVE_PARALLEL={parallel}", f"-DROVE_MODEL={int(model)}",
                 "-ffunction-sections", "-fdata-sections", "-fno-ident",
                 "-fno-asynchronous-unwind-tables", "-fno-unwind-tables",
                 "-Wl,--gc-sections,--build-id=none", "-s"]
        if variant == "C":
            flags.append("-mavx2")
        names = sorted(name for name in files if name.endswith(".c"))
        return [compiler] + flags + names + ["-o", "x"], environment
    flags = ["--edition=2024", "-C", "opt-level=" + ("z" if optimize == "size" else "2"),
             "-C", "panic=abort", "-C", "lto=fat", "-C", "codegen-units=1",
             "-C", "strip=symbols", "-C", "debuginfo=0", "-C", "link-arg=-Wl,--build-id=none"]
    if variant == "C":
        flags += ["-C", "target-feature=+avx2"]
    return [compiler] + flags + ["rust/main.rs", "-o", "x"], environment


def compile_files(files, directory, command, fixed_env):
    write_files(files, directory)
    environment = os.environ.copy()
    environment.update(fixed_env)
    # Compilers may encode source paths. Map each build root to the same logical
    # path; never erase a path mismatch after hashing the executable.
    options = list(command)
    if "--edition=2024" in options:
        options[1:1] = ["--remap-path-prefix", str(directory) + "=."]
    else:
        options[1:1] = ["-ffile-prefix-map=" + str(directory) + "=.",
                        "-fmacro-prefix-map=" + str(directory) + "=."]
    record = run(options, cwd=directory, env=environment)
    native = directory / "x"
    if native.read_bytes()[:4] != b"\x7fELF":
        raise ValueError("Linux compiler did not produce an ELF executable")
    record.update({"path": str(native), "bytes": native.stat().st_size,
                   "sha256": digest(native.read_bytes())})
    return record


def smoke(path):
    try:
        result = run([str(path)], input=b"uci\nisready\nquit\n", timeout=60)
        words = result["stdout"].splitlines()
        result["passed"] = "uciok" in words and "readyok" in words
        result["startup_under_60s_observed"] = result["passed"] and result["wall_seconds"] < 60
        if not result["passed"]:
            result["reason"] = "UCI handshake did not include both expected responses"
        return result
    except (RuntimeError, subprocess.TimeoutExpired, OSError) as error:
        return {"passed": False, "error": str(error), "startup_under_60s_observed": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--profile", default="local-dev")
    parser.add_argument("--variants", "--variant", default="ABCDEF")
    parser.add_argument("--languages", "--language", default="c,rust")
    parser.add_argument("--optimize", choices=("size", "speed"), default="size")
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--rustc", default="rustc")
    parser.add_argument("--parallel", choices=("loose", "root", "groups", "pals", "hybrid"), default="loose")
    parser.add_argument("--model", action="store_true", help="explicit SIMD plus frozen-model cross candidate")
    parser.add_argument("--reproduce", action="store_true", help="compile independent second copies and compare actual bytes")
    parser.add_argument("--self-elf", action="store_true", help="also build the syscall-only self-restoring ELF candidates")
    parser.add_argument("--no-pack", action="store_true", help="only build original and compact source engines")
    parser.add_argument("--no-smoke", action="store_true", help="skip all execution, recorded as unverified")
    args = parser.parse_args()
    if sys.platform != "linux" or platform.machine() not in ("x86_64", "amd64"):
        parser.error("build this Linux x86-64 portfolio in Linux, including WSL Ubuntu")
    out = args.out
    if not out.is_absolute():
        parser.error("--out must be absolute")
    out = out.resolve()
    if out == ROOT or ROOT in out.parents:
        parser.error("--out must be outside the source checkout")
    if out.exists() and any(out.iterdir()):
        parser.error("--out must be new or empty; preserve earlier evidence")
    profiles = json.loads(PROFILES.read_text())
    if args.profile not in profiles:
        parser.error("unknown fixed profile: " + args.profile)
    profile = profiles[args.profile]
    languages = args.languages.split(",")
    if not languages or any(item not in ("c", "rust") for item in languages):
        parser.error("--languages must be c,rust, or either one")
    variants = list(args.variants.replace(",", ""))
    if not variants or any(item not in "ABCDEF" for item in variants) or len(set(variants)) != len(variants):
        parser.error("--variants must contain distinct letters from A-F")
    out.mkdir(parents=True, exist_ok=True)
    # A local script must never accidentally start a 255/508/511-worker profile.
    execute = not args.no_smoke and profile["expected_total_threads"] <= min(8, os.cpu_count() or 1)
    summary = {"schema": 1, "source_root": str(ROOT), "profile_name": args.profile,
               "profile": profile, "optimize": args.optimize,
               "parallel": args.parallel, "model_cross_candidate": args.model,
               "platform": platform.platform(), "machine": platform.machine(),
               "python": sys.version, "rules": "https://wiki.chessdom.org/index.php?title=TCEC_4k_Rules&oldid=7853",
               "tools": {}, "engines": [], "complete": False,
               "execution_policy": "local profiles only; target profiles remain compile-only",
               "eligibility": "no tournament approval or playing-strength claim"}
    try:
        try:
            summary["git_head"] = run(["git", "rev-parse", "HEAD"], cwd=ROOT)["stdout"].strip()
            summary["git_engine_status"] = run(["git", "status", "--porcelain", "--", "engines"], cwd=ROOT)["stdout"]
        except RuntimeError as error:
            # A Windows-managed worktree's absolute .git target is not a Linux
            # path in WSL. Actual source-byte hashes remain authoritative; do
            # not invent a revision or reject otherwise supported Linux builds.
            summary["git_head"] = None
            summary["git_diagnostic"] = str(error)
        for language in languages:
            compiler = args.cc if language == "c" else args.rustc
            summary["tools"][language] = {"compiler": compiler, "version": tool_version(compiler)}
            files = source_files(language)
            compact = {name: compact_source(data, language) for name, data in files.items()}
            for variant in variants:
                identifier = variant + "-" + language + ("-model" if args.model else "")
                base = out / identifier
                command, fixed_env = compiler_recipe(language, variant, profile, args.optimize, compiler=compiler,
                                                       files=files, parallel=("loose", "root", "groups", "pals", "hybrid").index(args.parallel), model=args.model)
                record = {"id": identifier, "profile": "dev" if profile["development"] else "shipping",
                          "workers": profile["search_workers"], "configuration": fixed_env,
                          "sources": [{"path": "engines/" + name,
                                       "bytes": len(data), "sha256": digest(data),
                                       "compact_bytes": len(compact[name]), "compact_sha256": digest(compact[name])}
                                      for name, data in files.items()], "artifacts": []}
                summary["engines"].append(record)
                forms = [("original", files), ("compact", compact)]
                if language == "c" and not args.no_pack:
                    environment = os.environ.copy()
                    environment.update(fixed_env)
                    specialized, observations = specialize_c(files, base / "preprocessor", command, environment)
                    specialized = {name: compact_source(data, "c") for name, data in specialized.items()}
                    record["specialization"] = observations
                    forms.append(("specialized", specialized))
                original_hash = None
                for form, inputs in forms:
                    native = compile_files(inputs, base / form, command, fixed_env)
                    native["format"] = "native-elf"
                    native["category"] = "4k-elf"
                    native["under_4096_bytes"] = native["bytes"] <= 4096
                    native["rules_eligibility"] = "unproven_requires_runtime_and_full_rules_review"
                    native["source_form"] = form
                    if original_hash is None:
                        original_hash = native["sha256"]
                    native["byte_identical_to_original_native"] = native["sha256"] == original_hash
                    native["runtime"] = smoke(Path(native["path"])) if execute else {"passed": None, "reason": "not executed"}
                    if args.reproduce:
                        other = compile_files(inputs, base / (form + "-repeat"), command, fixed_env)
                        native["reproduction"] = {"sha256": other["sha256"], "path": other["path"],
                                                  "identical": other["sha256"] == native["sha256"]}
                        if not native["reproduction"]["identical"]:
                            raise RuntimeError(identifier + " " + form + " rebuild was not byte-identical")
                    record["artifacts"].append(native)
                    if form == "original":
                        record["command"] = [native["path"]]
                        record["cwd"] = str(base / form)
                    if not args.no_pack:
                        # Runtime compiler resolves from the tournament PATH,
                        # independent from this workstation's installation path.
                        runtime_command = list(command)
                        runtime_command[0] = "cc" if language == "c" else "rustc"
                        packages = write_launchers(inputs, base / (form + "-source"), command=runtime_command,
                                                   environment=fixed_env)
                        packages += write_launchers({"x": Path(native["path"]).read_bytes()},
                                                    base / (form + "-native"))
                        if args.self_elf:
                            from elf_loader import pack_elf
                            elf_output = base / (form + "-self-elf") / "x"
                            elf_output.parent.mkdir(parents=True, exist_ok=True)
                            packed = pack_elf(Path(native["path"]), elf_output, cc=args.cc)
                            packed.setdefault("path", str(elf_output))
                            packed.setdefault("format", "self-restoring-elf")
                            packed.setdefault("bytes", elf_output.stat().st_size)
                            packed.setdefault("sha256", digest(elf_output.read_bytes()))
                            packed["category"] = "4k-elf"
                            packed["under_4096_bytes"] = packed["bytes"] <= 4096
                            packed["rules_eligibility"] = "unproven_requires_runtime_and_full_rules_review"
                            packages.append(packed)
                        for package in packages:
                            package["source_form"] = form
                            package["runtime"] = smoke(Path(package["path"])) if execute else {"passed": None, "reason": "not executed"}
                            record["artifacts"].append(package)
                record["smallest_observed_complete_file"] = min(record["artifacts"], key=lambda item: item["bytes"])["path"]
                record["size_eligible_count"] = sum(item["under_4096_bytes"] for item in record["artifacts"])
                print(identifier + ": " + ", ".join(str(item["bytes"]) + "B " + item["format"]
                      for item in record["artifacts"]), flush=True)
        summary["complete"] = True
    except Exception as error:
        summary["failure"] = str(error)
        raise
    finally:
        (out / "build.json").write_text(json.dumps(summary, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
