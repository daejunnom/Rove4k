#!/usr/bin/env python3
"""Regenerate pinned B/C/E shipping C and propose one AST function-name map.

This source-only producer invokes the existing real preprocessor. It does not
compile native executables, pack streams, run engines, or change maintained code.
"""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
HEAD = "71a0791c1a2a52c42537ef5e39788f617e1f1de8"
PREFIX = Path("/mnt/c/Users/강민수/Documents/Codex/rove4k-pr12-size-reference-20261020/toolchain")
LIB = PREFIX / "libclang-18.1.1/site-v2"
RESOURCE = PREFIX / "clang18-headers/root/usr/lib/llvm-18/lib/clang/18"
TOOL_PINS = {
    "libclang-18.1.1/installation-v2.json": "34774b478aa3c57a4851596f85796b476baea2a238a8fbee9159143631f12e89",
    "clang18-headers/installation.json": "d0a453bc55f1156a8fcbf3d5137c77bd32ef4256819e58c650c88f111ba752bf",
}
EXPECTED = {
    "B": {"bytes": 13071, "sha256": "96e6e330e5289d1c404dac0402e8b672a89c52e193a9d4f9aebb02e0c9042ffa"},
    "C": {"bytes": 12224, "sha256": "20f06b6ed9ada03db6f8719f05ecdf9cb52802ab0a1acc8999627999db899046"},
    "E": {"bytes": 12641, "sha256": "af0ab88d9f4ce25154b3fda909fc00b9eca0cda8d8784b4b07e4926015a2c330"},
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def identity(data):
    return {"bytes": len(data), "sha256": sha(data)}


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def git_source(git_command, relative):
    result = subprocess.run(git_command + ["show", HEAD + ":" + relative],
                            capture_output=True, timeout=20)
    if result.returncode:
        raise ValueError("pinned Git source unavailable: " + relative + ": " + result.stderr.decode(errors="replace"))
    data = result.stdout
    if b"\r" in data:
        raise ValueError("pinned source is not LF: " + relative)
    return data


def source_stage(root, family, directory):
    selected = root / "engines/compact" / ("tiny-entry-" + family.lower())
    recipe = json.loads((selected / "recipe.json").read_bytes())
    helpers = root / "engines/scripts"
    specialize = module(helpers / "specialize.py", "private_specialize_" + family).specialize_c
    compact = module(helpers / "minify.py", "private_minify_" + family).compact_source
    lexer = module(helpers / "rename_c.py", "private_lexer_" + family)
    reference = module(helpers / "fixed_shipping_alpha.py", "private_reference_" + family)
    canonical = (selected / "engine.c").read_bytes()
    if sha(canonical) != recipe["expected"]["readable_sha256"]:
        raise ValueError("canonical readable mismatch")
    arguments = recipe["preprocessor"] + ["-DDEV=0"]
    if family == "B":
        arguments += ["main.c", "-o", "x"]
    active, observations = specialize({"main.c": canonical}, directory, arguments, os.environ.copy())
    data = compact(active["main.c"], "c")
    if family == "B":
        strip = module(root / "engines/compact/tiny-b/generate.py", "private_B_strip").strip_counters
    else:
        strip = module(root / "engines/compact/tiny-a/stitch.py", "private_strip_" + family).strip_dev_counters
    data, _ = strip(data)
    if family == "C":
        alpha = module(selected / "shipping_alpha.py", "private_C_alpha").transform_source
        data, _ = alpha(data, family="C", lexer=lexer, reference=reference, readable=canonical)
    else:
        data, _ = reference.transform_source(data, family=family, lexer=lexer)
    if family == "B":
        storage = module(selected / "shipping_storage.py", "private_B_storage").transform_source
        data, _ = storage(data, family="B", lexer=lexer, reference=reference, readable=canonical)
    if identity(data) != EXPECTED[family]:
        raise ValueError("qualified shipping source mismatch: " + family)
    return data, recipe, lexer, reference, observations


def ast_arguments(recipe):
    arguments = recipe["compiler"][1:]
    index = arguments.index("-o")
    if arguments[index:index + 2] != ["-o", "x"]:
        raise ValueError("fixed output pair changed")
    arguments = arguments[:index] + arguments[index + 2:]
    arguments = [value for value in arguments if value not in ("-", "-s")]
    return arguments + ["-resource-dir", str(RESOURCE)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--git-program", default="git")
    parser.add_argument("--git-repository", help="Explicit path for the selected Git host; no config changes")
    args = parser.parse_args()
    repo, out = args.repo.resolve(), args.out.resolve()
    git_command = [args.git_program, "-C", args.git_repository or str(repo)]
    if not args.out.is_absolute() or out.exists() or any((p / ".git").exists() for p in (out, *out.parents)):
        parser.error("new absolute output outside a Git checkout required")
    out.mkdir(parents=True)
    frozen = out / "inputs"
    frozen.mkdir()
    report = {"complete": False, "scope": "real-PP and AST source-only private static-function proposal",
              "git_commit": HEAD, "git_read_command": git_command, "inputs": {}, "tool_receipts": {}, "families": {},
              "native_compiles": 0, "codec_calls": 0, "engine_executions": 0}
    def save():
        (out / "prepare.json").write_bytes((json.dumps(report, indent=2) + "\n").encode())
    save()
    try:
        for relative, pin in TOOL_PINS.items():
            data = (PREFIX / relative).read_bytes()
            if sha(data) != pin:
                raise ValueError("external real AST tool receipt changed")
            report["tool_receipts"][relative] = identity(data)
        for family in EXPECTED:
            entry = "engines/compact/tiny-entry-" + family.lower() + "/"
            recipe_bytes = git_source(git_command, entry + "recipe.json")
            recipe = json.loads(recipe_bytes)
            if {"bytes": recipe["expected"]["source_bytes"], "sha256": recipe["expected"]["source_sha256"]} != EXPECTED[family]:
                raise ValueError("literal baseline differs from pinned recipe")
            sources = {entry + "recipe.json": (recipe_bytes, None),
                       entry + "engine.c": (None, recipe["expected"]["readable_sha256"])}
            for relative, pin in recipe["helper_sha256"].items():
                # Pack-stream code is not executed or needed for source preparation.
                if relative.endswith("/pack_stream.py"):
                    continue
                sources[relative] = (None, pin)
            for relative, (data, pin) in sources.items():
                data = git_source(git_command, relative) if data is None else data
                if pin is not None and sha(data) != pin:
                    raise ValueError("pinned ordinary helper differs: " + relative)
                if relative in report["inputs"] and report["inputs"][relative] != identity(data):
                    raise ValueError("shared ordinary input conflict")
                destination = frozen / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(data)
                report["inputs"][relative] = identity(data)
        for name in ("prepare.py", "rename.py"):
            data = Path(__file__).with_name(name).read_bytes()
            (out / ("producer-" + name)).write_bytes(data)
            report.setdefault("producer", {})[name] = identity(data)
        sys.path.insert(0, str(LIB))
        from clang import cindex
        cindex.Config.set_library_file(str(LIB / "clang/native/libclang.so"))
        renamer = module(out / "producer-rename.py", "private_function_renamer")
        for family in EXPECTED:
            directory = out / family
            directory.mkdir()
            data, recipe, lexer, reference, observations = source_stage(frozen, family, directory / "preprocess")
            (directory / "before.c").write_bytes(data)
            arguments = ast_arguments(recipe)
            candidate, metadata = renamer.propose(data, cindex=cindex, arguments=arguments,
                lexer=lexer, opaque=reference, filename=str(directory / "ast.c"))
            (directory / "candidate.c").write_bytes(candidate)
            (directory / "mapping.json").write_bytes((json.dumps(metadata, indent=2) + "\n").encode())
            report["families"][family] = {"before": identity(data), "after": identity(candidate),
                "mapping": metadata["mapping"], "AST_signature_sha256": metadata["AST_signature_sha256"],
                "arguments": arguments, "source_preprocessing": observations,
                "mapped_functions": len(metadata["mapping"]), "AST_edits": len(metadata["edits"])}
            save()
        report["complete"] = True
        save()
        print(json.dumps({family: {"after": row["after"], "mapped_functions": row["mapped_functions"]}
                          for family, row in report["families"].items()}), flush=True)
    except Exception as error:
        report["error"] = repr(error)
        save()
        raise


if __name__ == "__main__":
    main()
