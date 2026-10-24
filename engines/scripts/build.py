#!/usr/bin/env python3
"""Build all independent C/Rust A-F engines and measure complete deployment files.

Run on Linux. --out must be an absolute directory outside this checkout. Large
target profiles are compile-only here; a profile is not runtime validation.
"""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import time

from minify import compact_source
from pack import write_launchers
from compiler_group import transform_bootstrap
from specialize import specialize_c


ROOT = Path(__file__).resolve().parents[2]
PROFILES = ROOT / "engines/profiles/fixed.json"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run(command, *, cwd=None, env=None, timeout=180, input=None):
    started = time.monotonic()
    process = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    try:
        stdout, stderr = process.communicate(input=input, timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            stdout, stderr = process.communicate(timeout=6)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
        raise RuntimeError(json.dumps({"command": list(map(str, command)), "timeout_seconds": timeout,
                                       "stdout": stdout.decode(errors="replace"), "stderr": stderr.decode(errors="replace")}))
    record = {"command": list(map(str, command)), "returncode": process.returncode,
              "wall_seconds": time.monotonic() - started,
              "stdout": stdout.decode(errors="replace"),
              "stderr": stderr.decode(errors="replace")}
    if process.returncode:
        raise RuntimeError(json.dumps(record, indent=2))
    return record


def tool_version(command):
    return run([command, "--version"])["stdout"].strip()


def source_files(language, source_root=None):
    directory = (source_root or ROOT / "engines") / language
    extensions = (".c", ".h") if language == "c" else (".rs",)
    files = {str(path.relative_to(directory.parent)).replace(os.sep, "/"): path.read_bytes()
             for path in sorted(directory.rglob("*")) if path.is_file() and path.suffix in extensions}
    shared = directory.parent / "model"
    if shared.exists():
        # Model production definitions are include/module inputs. Standalone C
        # translation units there are development fixtures, never engine mains.
        shared_extensions = (".h",) if language == "c" else (".rs",)
        files.update({str(path.relative_to(directory.parent)).replace(os.sep, "/"): path.read_bytes()
                      for path in sorted(shared.rglob("*")) if path.is_file() and path.suffix in shared_extensions})
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


def compiler_recipe(language, variant, profile, optimize, *, compiler, files, parallel=0, model=False, hq=None, c_lto=False,
                    f_tt="paired", f_guess="previous"):
    if hq is None:
        hq = variant == "D"
    development = int(profile["development"])
    workers, bits = profile["search_workers"], profile["tt_bits"]
    environment = {"ROVE_VARIANT": variant, "ROVE_WORKERS": str(workers),
                   "ROVE_TT_BITS": str(bits), "ROVE_DEV": str(development),
                   "ROVE_PARALLEL": str(parallel), "ROVE_MODEL": str(int(model)),
                   "ROVE_HQ": str(int(hq)),
                   "SOURCE_DATE_EPOCH": "0", "LC_ALL": "C", "TZ": "UTC"}
    if variant == "F":
        environment.update({"ROVE_F_SINGLE": str(int(f_tt == "single")), "ROVE_F_PARITY": str(int(f_guess == "parity"))})
    if language == "c":
        flags = ["-std=c11", "-Os" if optimize == "size" else "-O2", "-pthread",
                 f"-DROVE_VARIANT={ord(variant) - ord('A') + 1}",
                 f"-DROVE_WORKERS={workers}", f"-DROVE_TT_BITS={bits}", f"-DROVE_DEV={development}",
                 f"-DROVE_PARALLEL={parallel}", f"-DROVE_MODEL={int(model)}",
                 f"-DROVE_HQ={int(hq)}",
                 "-ffunction-sections", "-fdata-sections", "-fno-ident",
                 "-fno-asynchronous-unwind-tables", "-fno-unwind-tables",
                 "-Wl,--gc-sections,--build-id=none", "-s"]
        if variant == "C":
            flags.append("-mavx2")
        if c_lto:
            flags.append("-flto")
        if variant == "F":
            flags += ["-DROVE_F_SINGLE=" + environment["ROVE_F_SINGLE"], "-DROVE_F_PARITY=" + environment["ROVE_F_PARITY"]]
        names = sorted(name for name in files if name.endswith(".c"))
        return [compiler] + flags + names + ["-o", "x"], environment
    flags = ["--edition=2024", "-C", "opt-level=" + ("z" if optimize == "size" else "2"),
             "-C", "panic=abort", "-C", "lto=fat", "-C", "codegen-units=1",
             "-C", "strip=symbols", "-C", "debuginfo=0", "-C", "link-arg=-Wl,--build-id=none"]
    if variant == "C":
        flags += ["-C", "target-feature=+avx2"]
    if variant == "F" and f_tt == "single":
        flags += ["--cfg", "rove_f_single"]
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


def smoke(path, environment=None):
    try:
        result = run([str(path)], input=b"uci\nisready\nquit\n", timeout=60, env=environment)
        words = result["stdout"].splitlines()
        result["passed"] = "uciok" in words and "readyok" in words
        result["startup_under_60s_observed"] = result["passed"] and result["wall_seconds"] < 60
        if not result["passed"]:
            result["reason"] = "UCI handshake did not include both expected responses"
        return result
    except (RuntimeError, subprocess.TimeoutExpired, OSError) as error:
        return {"passed": False, "error": str(error), "startup_under_60s_observed": False}


def main():
    global compact_source, write_launchers, specialize_c
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
    parser.add_argument("--model-format", choices=("varint", "static16"), default="varint", help="explicit exact E-model representation candidate")
    parser.add_argument("--source-root", type=Path, help="reuse an explicit c/rust/model source snapshot; hashes remain authoritative")
    parser.add_argument("--structural-compact", action="store_true", help="also generate C structural source forms; fixed root requires A shipping workers2/TT18")
    parser.add_argument("--rust-structural-compact", action="store_true", help="also compare bound Rust A shipping structural forms for loose or fixed root workers2/TT18")
    parser.add_argument("--structural-search", action="store_true", help="also compare the separately generated C search layout; requires loose policy")
    parser.add_argument("--small-worker", action="store_true", help="also compare compact C worker storage; requires structural-search and shipping")
    parser.add_argument("--shipping-operations", action="store_true", help="also compare specialized C shipping operations; requires small-worker, shipping and loose policy")
    parser.add_argument("--identifier-compact", action="store_true", help="also compare C identifier spelling accepted only by full-native byte identity")
    parser.add_argument("--identifier-trials", type=int, default=64, help="finite compile-gated C identifier trials (1..256)")
    parser.add_argument("--hq", choices=("auto", "scalar", "hq"), default="auto", help="D sliding attacks: auto selects HQ only for D; scalar/HQ require --variant D")
    parser.add_argument("--c-lto", choices=("off", "on"), default="off", help="explicit C cross-translation-unit optimization comparison")
    parser.add_argument("--f-tt", choices=("paired", "single"), default="paired", help="explicit F TT bound-storage experiment")
    parser.add_argument("--f-guess", choices=("previous", "parity"), default="previous", help="explicit F initial-guess experiment")
    parser.add_argument("--reproduce", action="store_true", help="compile independent second copies and compare actual bytes")
    parser.add_argument("--self-elf", action="store_true", help="also build the syscall-only self-restoring ELF candidates")
    parser.add_argument("--no-pack", action="store_true", help="omit complete-file wrappers; still build every explicitly requested source form")
    parser.add_argument("--native-backend", choices=("archive", "file", "memfd"), default="archive",
                        help="native wrappers only: existing archive, single ELF file FD, or explicit executable memfd")
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
    profile_bytes = PROFILES.read_bytes()
    profiles = json.loads(profile_bytes)
    if args.profile not in profiles:
        parser.error("unknown fixed profile: " + args.profile)
    profile = profiles[args.profile]
    source_root = (args.source_root or ROOT / "engines").resolve()
    languages = args.languages.split(",")
    if not languages or any(item not in ("c", "rust") for item in languages):
        parser.error("--languages must be c,rust, or either one")
    variants = list(args.variants.replace(",", ""))
    if not variants or any(item not in "ABCDEF" for item in variants) or len(set(variants)) != len(variants):
        parser.error("--variants must contain distinct letters from A-F")
    if args.model and variants != ["C"]:
        parser.error("--model is the explicit C plus E cross candidate; select --variant C")
    if args.model_format != "varint" and not (variants == ["E"] or (args.model and variants == ["C"])):
        parser.error("--model-format static16 requires --variant E or --variant C --model")
    if "F" in variants and args.parallel != "loose":
        parser.error("F currently requires --parallel loose to preserve whole-root MTD(f); select another variant for other parallel policies")
    if args.hq != "auto" and variants != ["D"]:
        parser.error("explicit --hq scalar|hq is the D comparison; select --variant D")
    fixed_root_structural = args.parallel == "root" and (args.structural_compact or args.rust_structural_compact)
    if fixed_root_structural:
        if variants != ["A"] or profile["development"] or profile["search_workers"] != 2 or profile["tt_bits"] != 18 or profile["expected_total_threads"] != 3:
            parser.error("fixed root structural source requires --variant A, shipping, workers2, TT18 and three total engine threads")
        if args.structural_compact and "c" not in languages:
            parser.error("fixed root --structural-compact requires the C implementation")
    if args.rust_structural_compact and ("rust" not in languages or variants != ["A"] or profile["development"] or args.parallel not in ("loose", "root")):
        parser.error("--rust-structural-compact requires Rust, --variant A, shipping and loose or fixed root policy")
    if args.structural_search:
        args.structural_compact = True
        if args.parallel != "loose" or "c" not in languages:
            parser.error("--structural-search currently requires C and --parallel loose")
    if args.c_lto == "on" and "c" not in languages:
        parser.error("--c-lto on requires the C implementation")
    if args.small_worker and (not args.structural_search or profile["development"]):
        parser.error("--small-worker requires --structural-search and a shipping profile")
    if args.shipping_operations and (not args.small_worker or "c" not in languages or profile["development"] or args.parallel != "loose"):
        parser.error("--shipping-operations requires C, --structural-search --small-worker, a shipping profile and --parallel loose")
    if args.identifier_compact and ("c" not in languages or not 1 <= args.identifier_trials <= 256):
        parser.error("--identifier-compact requires C and --identifier-trials within 1..256")
    if args.f_tt != "paired" or args.f_guess != "previous":
        if variants != ["F"]:
            parser.error("nondefault --f-tt/--f-guess experiments require --variant F")
        if args.structural_compact or args.structural_search or args.small_worker:
            parser.error("nondefault F experiments are not yet qualified with structural overlays")
    root_source_contract = None
    if fixed_root_structural:
        root_source_contract = {
            "scope": "current canonical fixed mode1 root scheduling and NORMAL reuse, specialized as A shipping source",
            "variant": "A", "parallel": "root", "search_workers": 2, "tt_bits": 18,
            "expected_total_threads": 3,
            "normal_reuse": {"c": "completed NORMAL first/depth/generation with compatible bound/window",
                             "rust": "exact first proposal seeds initial best and is skipped by first_job=1/finished=1; cache=None; PALS cache/Repair producers excluded"},
            "root_TT": "partial first-move results do not publish a whole-root exact entry; canonical child TT contracts retained",
            "completed_depth": "canonical aggregate completion; incomplete work retains last completed result or legal root fallback",
            "deadline": "one original job deadline and cancellation policy; reassignment does not reset the budget",
            "ownership": "immutable job root until callback drain; private worker search state; coherent shared TT; physical joins before release",
            "language_semantics": "each canonical evaluator, correction, search and TT meaning retained; no language-only matched claim",
            "excluded": ["groups", "PALS", "Repair", "hybrid", "F non-loose", "new UCI options"],
            "evidence": "source-generation contract only; no build/runtime/strength/scaling acceptance implied"}
    out.mkdir(parents=True, exist_ok=True)
    # A local script must never accidentally start a 255/508/511-worker profile.
    execute = not args.no_smoke and profile["expected_total_threads"] <= min(8, os.cpu_count() or 1)
    runtime_environment = os.environ.copy()
    compiler_prefixes = [str(Path(tool).parent) for tool in (args.cc, args.rustc) if Path(tool).is_absolute()]
    if compiler_prefixes:
        runtime_environment["PATH"] = os.pathsep.join(compiler_prefixes + [runtime_environment.get("PATH", "")])
    summary = {"schema": 1, "source_root": str(ROOT), "profile_name": args.profile,
               "profile": profile, "optimize": args.optimize,
               "engine_source_root": str(source_root), "runtime_compiler_path_prefixes": compiler_prefixes,
               "parallel": args.parallel, "model_cross_candidate": args.model,
               "model_format": args.model_format,
               "structural_compact": args.structural_compact, "structural_search": args.structural_search,
               "rust_structural_compact": args.rust_structural_compact,
               "small_worker": args.small_worker, "identifier_compact": args.identifier_compact,
               "shipping_operations": args.shipping_operations,
               "d_sliding_attacks": args.hq,
               "c_lto": args.c_lto,
               "f_tt": args.f_tt, "f_guess": args.f_guess,
               "platform": platform.platform(), "machine": platform.machine(),
               "python": sys.version, "rules": "https://wiki.chessdom.org/index.php?title=TCEC_4k_Rules&oldid=7853",
               "tools": {}, "engines": [], "complete": False,
               "execution_policy": "local profiles only; target profiles remain compile-only",
               "eligibility": "no tournament approval or playing-strength claim"}
    summary["native_packaging"] = {"requested_backend": args.native_backend, "enabled": not args.no_pack,
                                   "source_packages_changed": False,
                                   "external_programs": ["python3"] if not args.no_pack else [],
                                   "rules_eligibility": "unproven_requires_runtime_and_full_rules_review"}
    if root_source_contract is not None:
        summary["fixed_root_structural_source_contract"] = root_source_contract
    tooling_paths = [path for path in (ROOT / "engines/scripts").rglob("*")
                     if path.is_file() and path.suffix in (".py", ".c", ".ld")]
    compact_directory = ROOT / "engines/compact"
    if compact_directory.exists():
        tooling_paths += [path for path in compact_directory.rglob("*")
                          if path.is_file() and path.suffix in (".py", ".h", ".in")]
    tooling_paths.append(PROFILES)
    model_directory = ROOT / "engines/model"
    if model_directory.exists():
        tooling_paths += [path for path in (model_directory / "representations").rglob("*")
                          if path.is_file() and path.suffix == ".py"]
        tooling_paths += [model_directory / "codec.py", model_directory / "frozen.json"]
    tooling = {str(path.relative_to(ROOT)): path.read_bytes() for path in sorted(tooling_paths)}
    tooling["engines/profiles/fixed.json"] = profile_bytes
    summary["tooling_inputs"] = [{"path": name, "sha256": digest(data)} for name, data in tooling.items()]
    recipe_root = out / "recipe"
    write_files(tooling, recipe_root)
    # Execute the preserved transformation/template bytes, so another worker's
    # later edit cannot silently change a long campaign halfway through.
    compact_source = load_module("rove_frozen_minify", recipe_root / "engines/scripts/minify.py").compact_source
    frozen_pack = load_module("rove_frozen_pack", recipe_root / "engines/scripts/pack.py")
    write_launchers = frozen_pack.write_launchers
    specialize_c = load_module("rove_frozen_specialize", recipe_root / "engines/scripts/specialize.py").specialize_c
    native_elf_admission = None
    if args.self_elf or (not args.no_pack and args.native_backend != "archive"):
        frozen_elf = load_module("rove_frozen_elf", recipe_root / "engines/scripts/elf_loader.py")
        if args.self_elf:
            pack_elf = frozen_elf.pack_elf
        if not args.no_pack and args.native_backend != "archive":
            native_elf_admission = frozen_elf._elf
    if "E" in variants or args.model:
        frozen_model_directory = recipe_root / "engines/model"
        codec = load_module("codec", frozen_model_directory / "codec.py")
        load_module("generate", frozen_model_directory / "representations/generate.py")
        model_transform = load_module("rove_frozen_model_prepare", frozen_model_directory / "representations/prepare.py").transform_sources
        frozen_model = codec.load_model(frozen_model_directory / "frozen.json")
    summary["profile_input_sha256"] = digest(profile_bytes)
    summary["glibc"] = os.confstr("CS_GNU_LIBC_VERSION")
    try:
        if not args.no_pack and args.native_backend == "memfd":
            summary["native_packaging"]["host_support"] = frozen_pack.memfd_support()
        try:
            summary["git_head"] = run(["git", "rev-parse", "HEAD"], cwd=ROOT)["stdout"].strip()
            summary["git_engine_status"] = run(["git", "status", "--porcelain", "--", "engines"], cwd=ROOT)["stdout"]
        except RuntimeError as error:
            # A Windows-managed worktree's absolute .git target is not a Linux
            # path in WSL. Actual source-byte hashes remain authoritative; do
            # not invent a revision or reject otherwise supported Linux builds.
            summary["git_head"] = None
            summary["git_diagnostic"] = str(error)
        frozen_sources = {language: source_files(language, source_root) for language in languages}
        for inputs in frozen_sources.values():
            write_files(inputs, out / "sources")
        for language in languages:
            compiler = args.cc if language == "c" else args.rustc
            summary["tools"][language] = {"compiler": compiler, "version": tool_version(compiler)}
            canonical_files = frozen_sources[language]
            for variant in variants:
                files, model_record = canonical_files, None
                if variant == "E" or args.model:
                    files, model_record = model_transform(canonical_files, representation=args.model_format,
                                                         language=language, model=frozen_model)
                    if args.reproduce:
                        again, _ = model_transform(canonical_files, representation=args.model_format,
                                                   language=language, model=frozen_model)
                        model_record["source_reproduction_identical"] = files == again
                        if not model_record["source_reproduction_identical"]:
                            raise RuntimeError("model source representation did not reproduce")
                compact = {name: compact_source(data, language) for name, data in files.items()}
                identifier = variant + "-" + language + ("-model" if args.model else "") + ("-static16" if model_record and args.model_format == "static16" else "")
                base = out / identifier
                use_hq = args.hq == "hq" or (args.hq == "auto" and variant == "D")
                command, fixed_env = compiler_recipe(language, variant, profile, args.optimize, compiler=compiler,
                                                       files=files, parallel=("loose", "root", "groups", "pals", "hybrid").index(args.parallel), model=args.model, hq=use_hq, c_lto=args.c_lto == "on", f_tt=args.f_tt, f_guess=args.f_guess)
                record = {"id": identifier, "profile": "dev" if profile["development"] else "shipping",
                          "workers": profile["search_workers"], "configuration": fixed_env,
                          "startup_threads": profile["expected_total_threads"],
                          "max_threads": profile["expected_total_threads"], "startup_timeout": 60,
                          "sources": [{"path": "engines/" + name,
                                       "bytes": len(data), "sha256": digest(data),
                                       "compact_bytes": len(compact[name]), "compact_sha256": digest(compact[name])}
                                      for name, data in files.items()], "artifacts": []}
                summary["engines"].append(record)
                if model_record is not None:
                    record["model_representation"] = model_record
                    record["canonical_sources"] = [{"path": "engines/" + name, "bytes": len(data), "sha256": digest(data)}
                                                    for name, data in canonical_files.items()]
                generation_config = {"language": language, "variant": variant, "profile": profile,
                                     "parallel": args.parallel, "model": args.model, "hq": "hq" if use_hq else "scalar", "requested_hq": args.hq,
                                     "model_format": args.model_format if model_record else None,
                                     "optimize": args.optimize, "command": command, "fixed_environment": fixed_env,
                                     "structural_compact": args.structural_compact, "structural_search": args.structural_search,
                                     "rust_structural_compact": args.rust_structural_compact,
                                     "small_worker": args.small_worker, "identifier_compact": args.identifier_compact,
                                     "shipping_operations": args.shipping_operations,
                                     "identifier_trials": args.identifier_trials if args.identifier_compact else None,
                                     "c_lto": args.c_lto,
                                     "f_tt": args.f_tt if variant == "F" else None, "f_guess": args.f_guess if variant == "F" else None,
                                     "compiler_version": summary["tools"][language]["version"]}
                if root_source_contract is not None and ((language == "c" and args.structural_compact) or (language == "rust" and args.rust_structural_compact)):
                    generation_config["fixed_root_structural_source_contract"] = root_source_contract
                record["generation_config"] = generation_config
                record["generation_config_sha256"] = digest(json.dumps(generation_config, sort_keys=True, separators=(",", ":")).encode())
                forms = [("original", files), ("compact", compact)]
                repeated_forms = {"original": files, "compact": {name: compact_source(data, language) for name, data in files.items()}}
                if language == "rust" and args.rust_structural_compact:
                    generator_path = recipe_root / "engines/compact/rust/generate.py"
                    generator = load_module("rove_frozen_rust_structural", generator_path)
                    structured, changes = generator.specialize_rust(dict(files), configuration=dict(fixed_env))
                    if fixed_root_structural and (not isinstance(changes, dict) or changes.get("producer") != "rust-A-fixed-root-structural-v1" or changes.get("guards", {}).get("parallel") != "root"):
                        raise ValueError("fixed root Rust structural producer did not establish its source contract")
                    rust_record_key = "rust_root_structural_compaction" if fixed_root_structural else "rust_structural_compaction"
                    rust_form = "rust-root-structural-specialized" if fixed_root_structural else "rust-structural-specialized"
                    record[rust_record_key] = {"preparation": changes,
                        "generator_inputs": [{"path": str(path.relative_to(recipe_root)), "sha256": digest(path.read_bytes())}
                                             for path in sorted(generator_path.parent.rglob("*"))
                                             if path.is_file() and path.suffix in (".py", ".h", ".in")]}
                    forms += [(rust_form, structured),
                              (rust_form + "-compact", {name: compact_source(data, "rust") for name, data in structured.items()})]
                    if args.reproduce:
                        again, _ = generator.specialize_rust(dict(files), configuration=dict(fixed_env))
                        record[rust_record_key]["source_reproduction_identical"] = structured == again
                        repeated_forms[rust_form] = again
                        repeated_forms[rust_form + "-compact"] = {name: compact_source(data, "rust") for name, data in again.items()}
                if language == "c" and (not args.no_pack or args.identifier_compact):
                    environment = os.environ.copy()
                    environment.update(fixed_env)
                    specialized, observations = specialize_c(files, base / "preprocessor", command, environment)
                    specialized = {name: compact_source(data, "c") for name, data in specialized.items()}
                    record["specialization"] = observations
                    forms.append(("specialized", specialized))
                    if args.reproduce:
                        again, _ = specialize_c(files, base / "preprocessor-repeat", command, environment)
                        repeated_forms["specialized"] = {name: compact_source(data, "c") for name, data in again.items()}
                if language == "c" and args.structural_compact:
                    generator_path = recipe_root / "engines/compact/c/generate.py"
                    generator = load_module("rove_structural_compact", generator_path)
                    environment = os.environ.copy()
                    environment.update(fixed_env)
                    structural_forms = [("root-structural-specialized", "root_structural_compaction", {})] if fixed_root_structural else [("structural-specialized", "structural_compaction", {})]
                    if args.structural_search:
                        structural_forms.append(("structural-search-specialized", "structural_search_compaction", {"compact_search": True}))
                    if args.small_worker:
                        structural_forms.append(("structural-small-worker-specialized", "small_worker_compaction", {"compact_search": True, "small_worker": True}))
                    if args.shipping_operations:
                        structural_forms.append(("structural-shipping-operations-specialized", "shipping_operations_compaction", {"compact_search": True, "small_worker": True, "shipping_operations": True}))
                    for label, record_key, options in structural_forms:
                        def generate_structural(destination):
                            prepared, changes = generator.prepare_sources(files, variant=variant,
                                                parallel=("loose", "root", "groups", "pals", "hybrid").index(args.parallel),
                                                development=profile["development"], model=args.model, **options)
                            if fixed_root_structural and sum(1 for change in changes if isinstance(change, dict) and change.get("applied") is True and change.get("operation") == "fixed-root-source-specialization") != 1:
                                raise ValueError("fixed root C structural producer did not apply its source contract")
                            prepared, observations = specialize_c(prepared, destination, command, environment)
                            post_changes = []
                            if options.get("shipping_operations"):
                                prepared, post_changes = generator.specialize_shipping_operations(prepared, variant=variant,
                                                    development=profile["development"], parallel=0)
                            prepared, pruning = generator.prune_sources(prepared)
                            return {name: compact_source(data, "c") for name, data in prepared.items()}, changes, observations, pruning, post_changes
                        structured, changes, observations, pruning, post_changes = generate_structural(base / (label + "-preprocessor"))
                        record[record_key] = {"preparation": changes, "specialization": observations, "pruning": pruning,
                                             "post_specialization_operations": post_changes,
                                             "generator_inputs": [{"path": str(path.relative_to(recipe_root)), "sha256": digest(path.read_bytes())}
                                                                  for path in sorted(generator_path.parent.rglob("*"))
                                                                  if path.is_file() and path.suffix in (".py", ".h", ".in")]}
                        forms.append((label, structured))
                        if args.reproduce:
                            repeated_forms[label], _, _, _, _ = generate_structural(base / (label + "-preprocessor-repeat"))
                if language == "c" and args.identifier_compact:
                    renamer = load_module("rove_frozen_rename", recipe_root / "engines/scripts/rename_c.py")
                    input_label, identifier_inputs = forms[-1]
                    def identity_callback(destination):
                        def compile_identity(candidate_files, trial):
                            trial_path = destination / str(trial)
                            try:
                                result = compile_files(candidate_files, trial_path, command, fixed_env)
                                (trial_path / "compile.json").write_text(json.dumps(result, indent=2) + "\n")
                                return result["sha256"]
                            except Exception as error:
                                trial_path.mkdir(parents=True, exist_ok=True)
                                failure = trial_path / "failure.json"
                                failure.write_text(str(error) + "\n")
                                raise RuntimeError("native compilation rejected; preserved diagnostic: " + str(failure)) from error
                        return compile_identity
                    renamed, rename_record = renamer.compact_identifiers(identifier_inputs,
                                                identity_callback(base / "identifier-trials"), max_trials=args.identifier_trials)
                    rename_record["input_form"] = input_label
                    record["identifier_compaction"] = rename_record
                    forms.append(("identifier-specialized", renamed))
                    if args.reproduce:
                        again, _ = renamer.compact_identifiers(identifier_inputs,
                                                identity_callback(base / "identifier-trials-repeat"), max_trials=args.identifier_trials)
                        repeated_forms["identifier-specialized"] = again
                original_hash = None
                for form, inputs in forms:
                    record.setdefault("generated_sources", {})[form] = [{"path": name, "bytes": len(data), "sha256": digest(data)}
                                                                       for name, data in sorted(inputs.items())]
                    native = compile_files(inputs, base / form, command, fixed_env)
                    native["format"] = "native-elf"
                    native["category"] = "4k-elf"
                    native["under_4096_bytes"] = native["bytes"] <= 4096
                    native["rules_eligibility"] = "unproven_requires_runtime_and_full_rules_review"
                    native["source_form"] = form
                    if original_hash is None:
                        original_hash = native["sha256"]
                    native["byte_identical_to_original_native"] = native["sha256"] == original_hash
                    native["runtime"] = smoke(Path(native["path"]), runtime_environment) if execute else {"passed": None, "reason": "not executed"}
                    if args.reproduce:
                        native["source_reproduction_identical"] = repeated_forms[form] == inputs
                        if not native["source_reproduction_identical"]:
                            raise RuntimeError(identifier + " " + form + " source generation was not byte-identical")
                        other = compile_files(repeated_forms[form], base / (form + "-repeat"), command, fixed_env)
                        native["reproduction"] = {"sha256": other["sha256"], "path": other["path"],
                                                  "identical": other["sha256"] == native["sha256"]}
                        if not native["reproduction"]["identical"]:
                            raise RuntimeError(identifier + " " + form + " rebuild was not byte-identical")
                    record["artifacts"].append(native)
                    if form == "original":
                        record["command"] = [native["path"]]
                        record["cwd"] = str(base / form)
                        record["expected_program_sha256"] = native["sha256"]
                    if not args.no_pack:
                        # Runtime compiler resolves from the tournament PATH,
                        # independent from this workstation's installation path.
                        runtime_command = list(command)
                        runtime_command[0] = "cc" if language == "c" else "rustc"
                        packages = write_launchers(inputs, base / (form + "-source"), command=runtime_command, compiler_group=transform_bootstrap,
                                                   environment=fixed_env)
                        packages += write_launchers({"x": Path(native["path"]).read_bytes()},
                                                    base / (form + "-native"), native_backend=args.native_backend,
                                                    elf_admission=native_elf_admission)
                        if args.self_elf:
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
                        if args.reproduce:
                            repeated = write_launchers(inputs, base / (form + "-source-repeat"),
                                                       command=runtime_command, compiler_group=transform_bootstrap, environment=fixed_env)
                            repeated += write_launchers({"x": Path(other["path"]).read_bytes()},
                                                        base / (form + "-native-repeat"), native_backend=args.native_backend,
                                                        elf_admission=native_elf_admission)
                            if args.self_elf:
                                repeated_elf = base / (form + "-self-elf-repeat") / "x"
                                repeated_elf.parent.mkdir(parents=True, exist_ok=True)
                                packed_again = pack_elf(Path(other["path"]), repeated_elf, cc=args.cc)
                                packed_again["path"] = str(repeated_elf)
                                packed_again["sha256"] = digest(repeated_elf.read_bytes())
                                repeated.append(packed_again)
                            for package, duplicate in zip(packages, repeated, strict=True):
                                package["reproduction"] = {"path": duplicate["path"], "sha256": duplicate["sha256"],
                                                           "identical": package["sha256"] == duplicate["sha256"]}
                                if not package["reproduction"]["identical"]:
                                    raise RuntimeError(identifier + " " + form + " packaged file was not byte-identical")
                        for package in packages:
                            package["source_form"] = form
                            package["runtime"] = smoke(Path(package["path"]), runtime_environment) if execute else {"passed": None, "reason": "not executed"}
                            record["artifacts"].append(package)
                record["smallest_observed_complete_file"] = min(record["artifacts"], key=lambda item: item["bytes"])["path"]
                record["size_eligible_count"] = sum(item["under_4096_bytes"] for item in record["artifacts"])
                print(identifier + ": " + ", ".join(str(item["bytes"]) + "B " + item["format"]
                      for item in record["artifacts"]), flush=True)
        summary["generation_complete"] = True
        runtime_results = [item["runtime"].get("passed") for engine in summary["engines"] for item in engine["artifacts"]]
        summary["runtime_summary"] = {"passed": runtime_results.count(True), "failed": runtime_results.count(False),
                                      "not_executed": runtime_results.count(None)}
        if False in runtime_results:
            raise RuntimeError("artifact generation finished, but " + str(runtime_results.count(False)) + " final artifact UCI startup checks failed")
        summary["complete"] = True
    except Exception as error:
        summary["failure"] = str(error)
        raise
    finally:
        (out / "build.json").write_text(json.dumps(summary, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
