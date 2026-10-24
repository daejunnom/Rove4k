#!/usr/bin/env python3
"""Build and measure the independent source-first Tiny Rust A candidate.

Linux x86-64 only. All source snapshots, executables, launchers and reports go
in a new absolute directory outside the checkout. No external crates are used.
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
import traceback


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PRODUCTION = ("main.rs", "board.rs", "search.rs", "runtime.rs")
_ACTIVE_OUTPUT = None


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SYNTAX = load("tiny_rust_syntax", HERE.parent / "rust" / "syntax.py")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _groups(tokens):
    pos = 0
    while pos < len(tokens):
        yield pos
        pos = SYNTAX.matching(tokens, pos) + 1 if tokens[pos] in ("(", "[", "{") else pos + 1


def _cfg(tokens, development):
    if tokens == ["tiny_dev"]:
        return development
    if tokens == ["test"]:
        return False  # Unit fixtures are never part of these runtime archives.
    if len(tokens) >= 3 and tokens[1] == "(" and SYNTAX.matching(tokens, 1) == len(tokens) - 1:
        name, inside = tokens[0], tokens[2:-1]
        if name == "not":
            return not _cfg(inside, development)
        if name in ("all", "any"):
            parts, begin = [], 0
            for pos in _groups(inside):
                if inside[pos] == ",":
                    parts.append(inside[begin:pos])
                    begin = pos + 1
            if begin < len(inside):
                parts.append(inside[begin:])
            values = [_cfg(part, development) for part in parts]
            return all(values) if name == "all" else any(values)
    raise ValueError("unsupported runtime cfg: " + SYNTAX.render(tokens))


def _target_end(tokens, pos):
    """Find the end of this producer's cfg-controlled item/field/block.

    This deliberately accepts the small attributed-source contract rather than
    guessing at an arbitrary Rust grammar. In particular, cfg-controlled runtime
    statement sequences are enclosed in a standalone block.
    """
    if pos >= len(tokens):
        raise ValueError("cfg attribute has no target")
    if tokens[pos] == "{":
        end = SYNTAX.matching(tokens, pos) + 1
        return end + (tokens[end:end + 1] == [";"])
    if tokens[pos] in ("if", "while", "for", "loop", "match", "unsafe", "async", "move"):
        raise ValueError("cfg-controlled runtime expressions must use a standalone attributed block")
    header, cursor = [], pos
    while cursor < len(tokens):
        token = tokens[cursor]
        if token in (";", ","):
            return cursor + 1
        if token == "{":
            close = SYNTAX.matching(tokens, cursor)
            if any(word in header for word in ("fn", "struct", "impl", "enum", "trait", "mod", "union")):
                return close + 1
            cursor = close + 1
            continue
        if token in ("(", "["):
            cursor = SYNTAX.matching(tokens, cursor) + 1
            continue
        header.append(token)
        cursor += 1
    # A final struct field may omit its comma. Other unterminated targets fail.
    field = tokens[pos:]
    if ":" in field[:4] and not any(word in field for word in ("let", "const", "static")):
        return len(tokens)
    raise ValueError("unsupported unterminated cfg target: " + SYNTAX.render(tokens[pos:]))


def _strip(tokens, development, changes):
    output, pos = [], 0
    while pos < len(tokens):
        if tokens[pos:pos + 2] == ["cfg", "!"]:
            raise ValueError("cfg! expressions are outside the explicit attributed-block contract")
        if tokens[pos:pos + 2] == ["#", "["]:
            attrs, cursor, keep = [], pos, True
            # Keep unrelated preceding attrs attached to their own target. If
            # any cfg is false, remove the complete attribute chain and target.
            while tokens[cursor:cursor + 2] == ["#", "["]:
                close = SYNTAX.matching(tokens, cursor + 1)
                attribute = tokens[cursor + 2:close]
                if attribute[:1] == ["cfg_attr"]:
                    raise ValueError("cfg_attr is outside this producer's source contract")
                if attribute[:2] == ["cfg", "("] and attribute[-1:] == [")"]:
                    keep = _cfg(attribute[2:-1], development) and keep
                    changes["evaluated_cfg_attributes"] += 1
                else:
                    attrs.extend(tokens[cursor:close + 1])
                cursor = close + 1
            if not keep:
                pos = _target_end(tokens, cursor)
                changes["removed_cfg_targets"] += 1
                continue
            output.extend(attrs)
            pos = cursor
            continue
        if tokens[pos] in ("(", "[", "{"):
            close = SYNTAX.matching(tokens, pos)
            output.extend([tokens[pos], *_strip(tokens[pos + 1:close], development, changes), tokens[close]])
            pos = close + 1
        else:
            output.append(tokens[pos])
            pos += 1
    return output


def specialize(files, *, development=False):
    """Return physically cfg-pruned runtime sources and exact provenance.

    The input mapping and its bytes are immutable. Only the four production
    paths and optional dev.rs are accepted; test inputs cannot enter an archive.
    This function performs no I/O after the module's lexical helper is loaded.
    """
    if not isinstance(development, bool):
        raise ValueError("development must be a bool")
    if not isinstance(files, dict) or set(files) - {*PRODUCTION, "dev.rs"} or not set(PRODUCTION) <= set(files):
        raise ValueError("expected exactly the four production Rust files and optional dev.rs")
    if any(not isinstance(data, bytes) for data in files.values()):
        raise ValueError("runtime source values must be bytes")
    if development and "dev.rs" not in files:
        raise ValueError("development archive requires dev.rs")
    output, changes = {}, {"evaluated_cfg_attributes": 0, "removed_cfg_targets": 0}
    for name in (*PRODUCTION, *(("dev.rs",) if development else ())):
        tokens = SYNTAX.tokenize(files[name].decode("utf-8"))
        tokens = [token for token in tokens if not token.startswith(("///", "//!", "/**", "/*!", "#!"))]
        tokens = _strip(tokens, development, changes)
        if any(token in ("tiny_dev", "cfg_attr") for token in tokens):
            raise ValueError("unprocessed conditional configuration remains in " + name)
        data = (SYNTAX.render(tokens) + "\n").encode()
        if SYNTAX.tokenize(data.decode()) != tokens:
            raise ValueError("Rust token rendering changed token spellings in " + name)
        output[name] = data
    return output, {"producer": "tiny-rust-attributed-source-v1", "development": development,
                    "input_sha256": {name: sha(data) for name, data in sorted(files.items())},
                    "output_sha256": {name: sha(data) for name, data in sorted(output.items())},
                    "input_bytes": sum(map(len, files.values())), "output_bytes": sum(map(len, output.values())),
                    "output_files": sorted(output), "changes": changes,
                    "test_sources_present": False, "external_crates": False}


def lexical(files):
    result = {}
    for name, data in files.items():
        tokens = SYNTAX.tokenize(data.decode("utf-8"))
        # Comments are not compiler recipe inputs. Removing documentation attrs
        # here is valid for this crate, which has no procedural macros.
        tokens = [token for token in tokens if not token.startswith(("///", "//!", "/**", "/*!", "#!"))]
        value = (SYNTAX.render(tokens) + "\n").encode()
        if SYNTAX.tokenize(value.decode()) != tokens:
            raise ValueError("lexical rendering changed token spellings in " + name)
        result[name] = value
    return result


def write_files(files, directory):
    directory.mkdir(parents=True, exist_ok=True)
    for name, data in sorted(files.items()):
        target = directory / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def run(command, *, cwd=None, env=None, timeout=180, data=None):
    started = time.monotonic()
    child = subprocess.Popen(list(map(str, command)), cwd=cwd, env=env, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    try:
        stdout, stderr = child.communicate(input=data, timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(child.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            stdout, stderr = child.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            stdout, stderr = child.communicate()
        raise RuntimeError("command timeout: " + repr(command) + "\n" + stderr.decode(errors="replace"))
    record = {"command": list(map(str, command)), "returncode": child.returncode,
              "wall_seconds": time.monotonic() - started, "stdout": stdout.decode(errors="replace"),
              "stderr": stderr.decode(errors="replace")}
    if child.returncode:
        raise RuntimeError(json.dumps(record, indent=2))
    return record


def recipe(compiler, *, development, workers, tt_bits):
    command = [compiler, "--edition=2024", "-C", "opt-level=z", "-C", "lto=fat", "-C", "codegen-units=1",
               "-C", "panic=abort", "-C", "strip=symbols", "-C", "debuginfo=0", "-C", "link-arg=-Wl,--build-id=none",
               "--check-cfg", "cfg(tiny_dev)"]
    if development:
        command += ["--cfg", "tiny_dev"]
    command += ["main.rs", "-o", "x"]
    fixed = {"ROVE_WORKERS": str(workers), "ROVE_TT_BITS": str(tt_bits),
             "SOURCE_DATE_EPOCH": "0", "LC_ALL": "C", "TZ": "UTC"}
    return command, fixed


def compile_files(files, directory, command, fixed):
    write_files(files, directory)
    environment = os.environ.copy()
    environment.update(fixed)
    actual = [command[0], "--remap-path-prefix", str(directory) + "=.", *command[1:]]
    record = run(actual, cwd=directory, env=environment)
    binary = directory / "x"
    data = binary.read_bytes()
    if data[:4] != b"\x7fELF":
        raise ValueError("compiler did not produce a Linux ELF")
    record.update({"path": str(binary), "bytes": len(data), "sha256": sha(data)})
    return record


def smoke(path, environment=None):
    record = run([path], data=b"uci\nisready\nquit\n", timeout=60, env=environment)
    lines = record["stdout"].splitlines()
    record["passed"] = "uciok" in lines and "readyok" in lines
    if not record["passed"]:
        raise RuntimeError("UCI startup smoke did not observe both responses: " + json.dumps(record))
    return record


def main():
    global SYNTAX, _ACTIVE_OUTPUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--tt-bits", type=int, default=18)
    parser.add_argument("--rustc", default="rustc")
    parser.add_argument("--dev", action="store_true")
    parser.add_argument("--reproduce", action="store_true")
    parser.add_argument("--no-pack", action="store_true")
    parser.add_argument("--no-smoke", action="store_true")
    args = parser.parse_args()
    if sys.platform != "linux" or platform.machine().lower() not in ("x86_64", "amd64"):
        parser.error("run on Linux x86-64, including WSL Ubuntu")
    if not args.out.is_absolute():
        parser.error("--out must be absolute")
    args.out = args.out.resolve()
    if args.out == ROOT or ROOT in args.out.parents or args.out.exists():
        parser.error("--out must be a new directory outside the checkout")
    if not 1 <= args.workers <= 512 or not 8 <= args.tt_bits <= 26:
        parser.error("workers 1..512; TT bits 8..26")
    compiler_path = shutil.which(args.rustc)
    if compiler_path is None:
        parser.error("Rust compiler is not executable: " + args.rustc)
    compiler_path = os.path.abspath(compiler_path)
    _ACTIVE_OUTPUT = args.out
    names = (*PRODUCTION, *(("dev.rs",) if args.dev else ()))
    source = {name: (HERE / name).read_bytes() for name in names}
    inputs = {"engines/compact/tiny-rust/" + name: data for name, data in source.items()}
    inputs["engines/compact/tiny-rust/build.py"] = Path(__file__).read_bytes()
    inputs["engines/compact/rust/syntax.py"] = (HERE.parent / "rust" / "syntax.py").read_bytes()
    inputs["engines/scripts/pack.py"] = (ROOT / "engines" / "scripts" / "pack.py").read_bytes()
    inputs["engines/scripts/compiler_group.py"] = (ROOT / "engines/scripts/compiler_group.py").read_bytes()
    # All later imports and builds consume the frozen producer/helper/input bytes.
    frozen_root = args.out / "recipe"
    write_files(inputs, frozen_root)
    frozen_here = frozen_root / "engines" / "compact" / "tiny-rust"
    frozen_build = load("tiny_rust_frozen_build", frozen_here / "build.py")
    SYNTAX = frozen_build.SYNTAX
    pack = load("tiny_rust_frozen_pack", frozen_root / "engines" / "scripts" / "pack.py")
    owner = load("tiny_rust_compiler_group", frozen_root / "engines/scripts/compiler_group.py")
    transformed, observations = frozen_build.specialize(source, development=args.dev)
    source_forms = {"original": source, "lexical": frozen_build.lexical(source)}
    if not args.dev:
        source_forms["shipping"] = transformed
    # DEV forms have the same cfg pruning available, but never become shipping.
    else:
        source_forms["dev-specialized"] = transformed
    command, fixed = frozen_build.recipe(compiler_path, development=args.dev, workers=args.workers, tt_bits=args.tt_bits)
    # The target resolves its own compiler. Host-specific paths are evidence
    # metadata only and never enter a complete source artifact's recipe.
    runtime_command = ["rustc", *command[1:]]
    if any(Path(argument).is_absolute() for argument in runtime_command):
        raise ValueError("source package compiler recipe must contain no host absolute paths")
    verification_path = os.pathsep.join(dict.fromkeys((str(Path(compiler_path).parent), "/usr/local/bin", "/usr/bin", "/bin")))
    target_environment = os.environ.copy()
    target_environment["PATH"] = verification_path
    records = []
    source_packages = []
    native_packages = []
    original_native = None
    for form, files in source_forms.items():
        directory = args.out / form
        build = frozen_build.compile_files(files, directory, command, fixed)
        native = Path(build["path"]).read_bytes()
        if original_native is None:
            original_native = native
        entry = {"id": "tiny-rust-A-" + form, "source_form": form, "command": [build["path"]],
                 "cwd": str(directory), "profile": "dev" if args.dev else "shipping",
                 "workers": args.workers, "startup_threads": args.workers + 1,
                 "expected_program_sha256": build["sha256"], "native_bytes": build["bytes"],
                 "native_sha256": build["sha256"], "source_bytes": sum(map(len, files.values())),
                 "source_sha256": {name: sha(data) for name, data in sorted(files.items())},
                 "compile": build, "native_equals_original": native == original_native}
        if not args.no_smoke:
            entry["smoke"] = frozen_build.smoke(build["path"])
        else:
            entry["smoke"] = {"passed": None, "reason": "explicit --no-smoke"}
        if args.reproduce:
            if form == "original":
                repeated_files = dict(source)
            elif form == "lexical":
                repeated_files = frozen_build.lexical(dict(source))
            else:
                repeated_files, repeated_observations = frozen_build.specialize(dict(source), development=args.dev)
                if repeated_observations != observations:
                    raise RuntimeError("independent source metadata reproduction differs")
            if repeated_files != files:
                raise RuntimeError(form + " independent source generation differs")
            second = frozen_build.compile_files(repeated_files, args.out / "reproduction" / form, command, fixed)
            if Path(second["path"]).read_bytes() != native:
                raise RuntimeError(form + " complete native reproduction differs")
            entry["source_reproduced"] = True
            entry["native_reproduced"] = True
        if not args.no_pack and form in ("shipping", "dev-specialized"):
            entry["launchers"] = pack.write_launchers(files, directory / "packed-source", command=runtime_command, environment=fixed, compiler_group=owner.transform_bootstrap)
            entry["native_launchers"] = pack.write_launchers({"x": native}, directory / "packed-native")
            if args.reproduce:
                repeated = pack.write_launchers(files, args.out / "reproduction" / form / "packed-source", command=runtime_command, environment=fixed, compiler_group=owner.transform_bootstrap)
                repeated += pack.write_launchers({"x": native}, args.out / "reproduction" / form / "packed-native")
                for first, other in zip([*entry["launchers"], *entry["native_launchers"]], repeated):
                    if Path(first["path"]).read_bytes() != Path(other["path"]).read_bytes():
                        raise RuntimeError(form + " complete launcher reproduction differs")
                    first["reproduced"] = True
            source_packages.extend((entry, artifact) for artifact in entry["launchers"])
            native_packages.extend((entry, artifact) for artifact in entry["native_launchers"])
        records.append(entry)
    chosen = min(source_packages, key=lambda pair: pair[1]["bytes"]) if source_packages else None
    selected = chosen[1] if chosen else None
    selected_native = min(native_packages, key=lambda pair: pair[1]["bytes"])[1] if native_packages else None
    package_smokes = {}
    if not args.no_smoke:
        for label, artifact in (("selected_source", selected), ("selected_native", selected_native)):
            if artifact:
                package_smokes[label] = frozen_build.smoke(artifact["path"], target_environment)
    report = {"candidate": "independent source-first Rust A", "development": args.dev,
              "workers": args.workers, "tt_bits": args.tt_bits, "startup_threads": args.workers + 1,
              "input_sha256": {name: sha(data) for name, data in sorted(source.items())},
              "recipe_sha256": {name: sha(data) for name, data in sorted(inputs.items())},
              "compiler": run([compiler_path, "--version", "--verbose"])["stdout"].strip(),
              "compiler_command": command, "compiler_environment": fixed, "specialization": observations,
              "source_package_command": runtime_command,
              "target_compiler_scope": {"command": "rustc", "resolution": "target caller PATH",
                                        "host_build_compiler": compiler_path,
                                        "controlled_verification_PATH": verification_path,
                                        "host_path_embedded_in_source_recipe": False},
              "engines": records, "selected": selected, "selected_native": selected_native,
              "package_smokes": package_smokes, "reproduction_requested": args.reproduce,
              "eligible_4k": False, "under_4096_bytes": selected is not None and selected["bytes"] <= 4096,
              "eligibility": "unproven_requires_full_rules_and_runtime_review"}
    manifest = dict(report)
    manifest["engines"] = list(records)
    if chosen:
        origin, artifact = chosen
        manifest["engines"].append({"id": "tiny-rust-A-selected", "command": [artifact["path"]],
                                     "cwd": str(Path(artifact["path"]).parent), "profile": origin["profile"],
                                     "workers": args.workers, "startup_threads": args.workers + 1,
                                     "startup_timeout": 60, "expected_program_sha256": artifact["sha256"],
                                     "selected_from": origin["id"], "selected_artifact": artifact})
    for name, value in (("build.json", report), ("validation-manifest.json", manifest)):
        (args.out / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(args.out), "forms": [{key: entry[key] for key in ("id", "source_bytes", "native_bytes", "native_equals_original")} for entry in records],
                      "minimum_complete_source_bytes": selected["bytes"] if selected else None,
                      "eligible_4k": False}))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        if _ACTIVE_OUTPUT is not None and _ACTIVE_OUTPUT.is_dir():
            (_ACTIVE_OUTPUT / "failure.json").write_text(json.dumps({"passed": False,
                "exception": type(error).__name__, "error": str(error), "traceback": traceback.format_exc()}, indent=2) + "\n", encoding="utf-8")
        raise
