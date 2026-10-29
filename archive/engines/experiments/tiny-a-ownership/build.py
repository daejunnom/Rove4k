#!/usr/bin/env python3
"""One selected-A ownership/query candidate under the exact selected recipe.

No source, flag, spelling, codec or resource search is performed. Raw and LF
inputs are frozen before helper imports. The control must reproduce every
selected source/native/bootstrap/whole expectation; both forms have two fresh
generation attempts and a complete stripped-native transformation gate.
"""
import argparse
import ast
import difflib
import hashlib
import importlib.util
import json
import lzma
import os
from pathlib import Path
import platform
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SELECTED = HERE / "control"
CONTROL_INPUT_SHA256 = {
    "engine.c": "321ab861fe8e8ebc1791cbd389edbecc53091ede195e172e9983f2455ee12c6d",
    "recipe.json": "749b6e102a581efe419de14e40bd7346afff18b5bc8b46c145084b11bb89456a",
    "bootstrap.py.in": "898bf1f24168f6e99a7ffb9b0ba9e805af0c7627ea115d47ac687c1389d015ba",
    "launcher.sh": "a6fd458f0dec9193341bfe2ea128b0e4cba9aa3409822f85d2ca0f435734f50a",
    "build.py": "b8d524e7248b3bda5b0b2c82aa2511dce1071e6d1858f0eb7603b658b554d09e",
}
CONTROL = {
    "readable_sha256": "321ab861fe8e8ebc1791cbd389edbecc53091ede195e172e9983f2455ee12c6d",
    "source_bytes": 11148,
    "source_sha256": "5e0e77321110371aec3a7a06f93290e7581f08f721fc9bb07fcef26c406429b7",
    "native_bytes": 22664,
    "native_sha256": "d39167146236aafde21b59439b853bd10561f04e9186c18b839c2f84f2e16e12",
    "whole_bytes": 5207,
    "whole_sha256": "085fcf6bd411a59111aaebbdc6bd59e2687a5c38de2ce28f0ad9643882633e36",
    "bootstrap_sha256": "11679fb20e24e7cb777cb49e4bee5a7ee7ea999278651fbba6d622320e751d44",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def lf(data):
    result = data.replace(b"\r\n", b"\n")
    require(b"\r" not in result, "lone CR in owned text input")
    return result


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def compile_c(command, source, directory):
    directory.mkdir()
    (directory / "main.c").write_bytes(source)
    process = subprocess.run(command, input=source, cwd=directory,
                             capture_output=True, timeout=90)
    (directory / "compiler.stdout").write_bytes(process.stdout)
    (directory / "compiler.stderr").write_bytes(process.stderr)
    record = {"command": command, "source_sha256": sha(source), "source_bytes": len(source),
              "returncode": process.returncode, "directory": str(directory),
              "stdout_sha256": sha(process.stdout), "stderr_sha256": sha(process.stderr)}
    save(directory / "compile.json", record)
    if process.returncode:
        raise RuntimeError("compiler failed; complete evidence retained in " + str(directory))
    native = (directory / "x").read_bytes()
    record.update(native_bytes=len(native), native_sha256=sha(native))
    save(directory / "compile.json", record)
    return native, record


def literal_value(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, bytes)):
        return node.value
    if (isinstance(node, ast.Call) and not node.args and not node.keywords
            and isinstance(node.func, ast.Attribute) and node.func.attr == "encode"
            and isinstance(node.func.value, ast.Constant) and isinstance(node.func.value.value, str)):
        return node.func.value.value.encode()
    raise ValueError("unexpected nonliteral source expression")


def boundary_receipt(control, candidate):
    think = b"void think("
    tail = b"    w->length=game_length;"
    pool = b"static pthread_mutex_t mutex="
    require(control.count(think) == candidate.count(think) == 1, "think boundary changed")
    a, b = control.index(think), candidate.index(think)
    require(control[:a] == candidate[:b], "board/hash/search prefix changed")
    require(control.count(tail) == candidate.count(tail) == 1, "think entry boundary changed")
    aa, bb = control.index(tail), candidate.index(tail)
    ap, bp = control.index(pool, aa), candidate.index(pool, bb)
    require(control[aa:ap] == candidate[bb:bp], "think iterative search body changed")
    return {"board_hash_search_prefix_bytes": a, "board_hash_search_prefix_sha256": sha(control[:a]),
            "board_hash_search_prefix_exact": True,
            "think_from_history_copy_sha256": sha(control[aa:ap]), "think_from_history_copy_exact": True,
            "allowed_think_difference": "entry resets only; best now reset by its worker",
            "remaining_changes": "private legal query, replay/fallback callers and GO reset ownership; full readable diff retained"}


def build(out, development=False):
    out = out.resolve()
    require(not out.exists() and out != REPO and REPO not in out.parents
            and not any((parent / ".git").exists() for parent in (out, *out.parents)),
            "new absolute output outside any Git checkout required")
    require(platform.system() == "Linux" and platform.machine() in ("x86_64", "amd64"),
            "fixed measured target is Linux x86-64")
    recipe_bytes = lf((SELECTED / "recipe.json").read_bytes())
    require(sha(recipe_bytes) == CONTROL_INPUT_SHA256["recipe.json"], "archived control recipe changed")
    recipe = json.loads(recipe_bytes)
    require(recipe["format"] == 1 and recipe["profile"] ==
            {"workers": 2, "tt_bits": 18, "ply": 128, "dev_default": False}, "selected profile changed")
    require(all(recipe["expected"][key] == value for key, value in CONTROL.items()),
            "selected control expectations changed")
    require(recipe["compiler"] == ["cc", "-Os", "-x", "c", "-", "-o", "x", "-s"],
            "selected compiler recipe changed")
    require(recipe["compression"] == {"format": "xz", "filter": "LZMA2", "preset": 9,
            "extreme": True, "lc": 2, "lp": 0, "pb": 0, "check": "CRC64"}, "compression recipe changed")
    out.mkdir(parents=True)
    inputs = out / "inputs"
    report = {"format": 1, "complete": False,
              "scope": "one selected-A runtime ownership/query candidate; no runtime QA or 4KiB acceptance",
              "resources": recipe["profile"], "inputs": {}, "forms": [], "engines": [],
              "diagnostic_requested": development,
              "control_source_closure": {
                "repository_directory": str(SELECTED.relative_to(REPO)),
                "LF_sha256": CONTROL_INPUT_SHA256,
                "archived_build_py_role": "provenance snapshot only; never imported or executed",
                "canonical_entry_dependency": False},
              "selected_historical_receipt": {"data": recipe["qualified_receipt"],
                "scope": "provenance only; this producer does not execute or infer qualification receipts"}}
    def publish():
        save(out / "build.json", report)
        save(out / "validation-manifest.json", {"engines": report["engines"]})
    publish()
    try:
        def freeze(category, name, path, expected=None):
            raw = path.read_bytes()
            normalized = lf(raw)
            if expected is not None:
                require(sha(normalized) == expected, "pinned LF input changed: " + str(path))
            for form, data in (("raw", raw), ("LF", normalized)):
                target = inputs / form / category / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            report["inputs"][category + "/" + name] = {
                "repository_path": str(path.relative_to(REPO)), "raw_bytes": len(raw), "raw_sha256": sha(raw),
                "LF_bytes": len(normalized), "LF_sha256": sha(normalized), "normalized_CRLF": raw != normalized}
            return normalized
        for name, expected in recipe["local_input_sha256"].items():
            require(expected == CONTROL_INPUT_SHA256[name], "archived control input recipe changed: " + name)
            freeze("selected", name, SELECTED / name, expected)
        for name in ("recipe.json", "build.py"):
            freeze("selected", name, SELECTED / name, CONTROL_INPUT_SHA256[name])
        for name in ("build.py", "transform.py"):
            freeze("experiment", name, HERE / name)
        if (HERE / "design.md").is_file():
            freeze("experiment", "design.md", HERE / "design.md")
        helper_names = set()
        for relative, expected in recipe["helper_sha256"].items():
            path = REPO / relative
            require(path.name not in helper_names, "helper basename collision")
            helper_names.add(path.name)
            freeze("helpers", path.name, path, expected)
        publish()
        save(out / "provenance.json", {"inputs": report["inputs"],
              "normalization": "raw bytes preserved; CRLF-to-LF is explicit and lone CR is rejected",
              "recipe_scope": "the selected recipe, fixed token maps/compiler/template/prefix/XZ parameters without a sweep"})
        selected = inputs / "LF/selected"
        helpers = inputs / "LF/helpers"
        specialize = module("ownership_specialize", helpers / "specialize.py").specialize_c
        compact = module("ownership_minify", helpers / "minify.py").compact_source
        strip = module("ownership_counter_strip", helpers / "stitch.py").strip_dev_counters
        replace = module("ownership_tokens", helpers / "rename_c.py")._replace
        literal = module("ownership_literal", helpers / "pack_stream.py").source_literal
        transform = module("ownership_transform", inputs / "LF/experiment/transform.py").transform
        control = (selected / "engine.c").read_bytes()
        require(sha(control) == CONTROL["readable_sha256"], "selected readable control changed")
        candidate, details = transform(control)
        require(isinstance(candidate, bytes) and candidate != control, "expected one changed candidate")
        report["transformation"] = details
        report["body_boundary_receipt"] = boundary_receipt(control, candidate)
        (out / "readable.diff").write_text("".join(difflib.unified_diff(
            control.decode().splitlines(True), candidate.decode().splitlines(True),
            fromfile="control.c", tofile="candidate.c")), encoding="utf-8")
        template = (selected / "bootstrap.py.in").read_bytes()
        prefix = (selected / "launcher.sh").read_bytes()
        marker = b"__ROVE_SOURCE_LITERAL__"
        require(template.count(marker) == 1 and len(prefix) == 75, "selected bootstrap recipe changed")
        report["tools"] = {name: subprocess.check_output(command, text=True).splitlines()[0]
                           for name, command in {"cc": ["cc", "--version"], "ld": ["ld", "--version"],
                           "python": ["python3", "--version"], "xz": ["xz", "--version"]}.items()}
        raw_command = recipe["preprocessor"] + ["-DDEV=0", "-x", "c", "-", "-o", "x", "-s"]
        dev_command = ["cc", "-Os", "-pthread", "-DWORKERS=2", "-DTT_BITS=18", "-x", "c", "-", "-o", "x"]
        for name, readable in (("control", control), ("candidate", candidate)):
            form = {"name": name, "complete": False, "readable_bytes": len(readable),
                    "readable_sha256": sha(readable), "attempts": []}
            report["forms"].append(form)
            directory = out / name
            directory.mkdir()
            (directory / "engine.c").write_bytes(readable)
            first = None
            first_dev = None
            for attempt in (1, 2):
                target = directory / ("attempt-" + str(attempt))
                target.mkdir()
                row = {"attempt": attempt, "complete": False}
                form["attempts"].append(row)
                publish()
                active, observations = specialize({"main.c": readable}, target / "preprocess",
                    recipe["preprocessor"] + ["-DDEV=0"], os.environ.copy())
                (target / "specialized.c").write_bytes(active["main.c"])
                compacted = compact(active["main.c"], "c")
                (target / "compact.c").write_bytes(compacted)
                stripped, counter_record = strip(compacted)
                (target / "counter-stripped.c").write_bytes(stripped)
                files = {"main.c": stripped}
                for old, new in recipe["fixed_renames"] + recipe["resource_literals"] + recipe["function_spellings"]:
                    files = replace(files, old, new)
                source = files["main.c"]
                (target / "main.c").write_bytes(source)
                row.update(source_bytes=len(source), source_sha256=sha(source),
                           preprocessor=observations, counter_recipe=counter_record)
                publish()
                if name == "control":
                    require(len(source) == CONTROL["source_bytes"] and sha(source) == CONTROL["source_sha256"],
                            "control compact C identity mismatch")
                raw_native, raw_gate = compile_c(raw_command, readable, target / "original")
                native, native_gate = compile_c(recipe["compiler"], source, target / "native")
                require(raw_native == native, "source transformations changed complete stripped native: " + name)
                if name == "control":
                    require(len(native) == CONTROL["native_bytes"] and sha(native) == CONTROL["native_sha256"],
                            "control native identity mismatch")
                expression, kind = literal(source)
                script = template.replace(marker, expression.encode())
                tree = ast.parse(script)
                calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                         and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
                         and node.func.value.id == "p" and node.func.attr == "communicate"]
                require(len(calls) == 1 and len(calls[0].args) == 1
                        and literal_value(calls[0].args[0]) == source, "source literal restoration mismatch")
                payload = lzma.compress(script, format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64,
                    filters=[{"id": lzma.FILTER_LZMA2, "preset": 9 | lzma.PRESET_EXTREME, "lc": 2, "lp": 0, "pb": 0}])
                require(lzma.decompress(payload) == script, "XZ restoration mismatch")
                whole = prefix + payload
                if name == "control":
                    require(len(whole) == CONTROL["whole_bytes"] and sha(whole) == CONTROL["whole_sha256"]
                            and sha(script) == CONTROL["bootstrap_sha256"], "control complete launcher identity mismatch")
                (target / "x").write_bytes(whole)
                (target / "x").chmod(0o755)
                (target / "bootstrap.py").write_bytes(script)
                current = (source, native, whole, script)
                require(first is None or current == first, "independent generation bytes differ: " + name)
                first = current
                row.update(native_bytes=len(native), native_sha256=sha(native), whole_bytes=len(whole),
                           whole_sha256=sha(whole), bootstrap_sha256=sha(script), source_literal=kind,
                           raw_native_gate=raw_gate, encoded_native_gate=native_gate, source_restored_exactly=True)
                if development:
                    active_dev, dev_observations = specialize({"main.c": readable}, target / "preprocess-dev",
                        recipe["preprocessor"] + ["-DDEV=1"], os.environ.copy())
                    dev_source = compact(active_dev["main.c"], "c")
                    dev_native, dev_gate = compile_c(dev_command, dev_source, target / "dev")
                    if name == "control":
                        require(sha(dev_source) == recipe["expected"]["dev_source_sha256"]
                                and sha(dev_native) == recipe["expected"]["dev_native_sha256"], "control DEV identity mismatch")
                    require(first_dev is None or (dev_source, dev_native) == first_dev, "DEV bytes did not reproduce")
                    first_dev = (dev_source, dev_native)
                    row["dev"] = {"source_sha256": sha(dev_source), "native_sha256": sha(dev_native),
                                  "compile": dev_gate, "preprocessor": dev_observations}
                row["complete"] = True
                publish()
            for filename, data in (("main.c", first[0]), ("x", first[2]), ("bootstrap.py", first[3])):
                (directory / filename).write_bytes(data)
            (directory / "x").chmod(0o755)
            (directory / "native").mkdir()
            (directory / "native/x").write_bytes(first[1])
            (directory / "native/x").chmod(0o755)
            variants = [("selected", "shipping", directory / "x", first[2]),
                        ("native", "shipping", directory / "native/x", first[1])]
            if first_dev:
                (directory / "dev").mkdir()
                (directory / "dev/main.c").write_bytes(first_dev[0])
                (directory / "dev/x").write_bytes(first_dev[1])
                (directory / "dev/x").chmod(0o755)
                variants.append(("dev", "dev", directory / "dev/x", first_dev[1]))
            for variant, profile, path, data in variants:
                spec = {"id": name + "-" + variant, "profile": profile, "command": [str(path)],
                        "cwd": str(path.parent), "workers": 2, "startup_threads": 3,
                        "expected_program_sha256": sha(data)}
                if variant == "selected":
                    spec["startup_timeout"] = 60
                report["engines"].append(spec)
            form.update(complete=True, source_reproduced=True, native_reproduced=True, whole_reproduced=True,
                        source_bytes=len(first[0]), source_sha256=sha(first[0]), native_bytes=len(first[1]),
                        native_sha256=sha(first[1]), whole_bytes=len(first[2]), whole_sha256=sha(first[2]),
                        bootstrap_sha256=sha(first[3]), whole_path=str(directory / "x"),
                        native_path=str(directory / "native/x"), diagnostic_reproduced=bool(first_dev),
                        under_4096_bytes=len(first[2]) <= 4096)
            publish()
            print(json.dumps({key: form[key] for key in ("name", "source_bytes", "native_bytes", "whole_bytes", "whole_sha256")}), flush=True)
        report["complete"] = True
        publish()
        return report
    except Exception as error:
        report["error"] = type(error).__name__ + ": " + str(error)
        publish()
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--dev", action="store_true", help="also generate each form's DEV source/native twice")
    args = parser.parse_args()
    if not args.out.is_absolute():
        parser.error("--out must be absolute")
    build(args.out, args.dev)


if __name__ == "__main__":
    main()
