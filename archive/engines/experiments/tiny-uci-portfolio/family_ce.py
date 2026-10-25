"""Frozen C-startup-PSQT/E-cache adapters for one shipping UCI policy.

Only the already qualified 6015-byte C and 6095-byte E selected source streams
are admitted. This module regenerates their readable source from the archived
core/overlays, preserves their compiler/source recipe, and never invokes the old
producer's wrapper portfolio. Policy changes belong to the common transform.
"""
import ast
import hashlib
import importlib.util
import json
import lzma
import os
from pathlib import Path
import re
import sys


PINS = {
    "C": {
        "report": "fc2eed0df7e29a4455a5f154fc7d33c7782120fb4330c055a5795918d5671dcc",
        "readable": "8d951ec4e451bccf89064f30aaead77e49410017d825536d65c9c7e39a4cdb96",
        "source": "d210e0cd885bd2265ccb252937e31b43a80133e7a490920ac5c8f9809261d266",
        "wrapper": "4033f5ae69d7333b5a2f536760187fb9c73f883a2471b353324b1a732091bc3b",
        "native": "9f3ba6d0550567ac9ac0ddf32783564a7433e51a1903e6869b5b376e0dd06f89",
        "whole_bytes": 6015,
    },
    "E": {
        "report": "55e72d5c2ebf3644006d1aceb4c8c7be66082f62c994881798a0d55be3eb0b86",
        "readable": "09e67b5a2b4b17f04f08eebeb1b70421eb47eb235f7027099d1ff8ad5173b5e1",
        "source": "83393315f529bf2ccb50627ed5cbecd4f9742ba682e6f95b3cd92dac6e13a3b4",
        "wrapper": "283f639687c80ddfc5859178ed1a3ce19d4b42b4a9ed5e488d96420811759167",
        "native": "dc755d8f60e53d4526e6b0c09b6501156fa1a6f089c6de57d0a3827b8d811057",
        "whole_bytes": 6095,
    },
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def relative(name):
    path = Path(name)
    require(not path.is_absolute() and ".." not in path.parts and "\\" not in name,
            "unsafe archived recipe path")
    return path


def body(source, name):
    """Hash fixed owned feature bodies without parsing/changing engine code."""
    text = source.decode()
    matches = list(re.finditer(r"(?m)^[^\n;{}]*\b"+re.escape(name)+r"\([^\n;{}]*\)\s*\{", text))
    require(len(matches) == 1, "fixed protected function shape changed: "+name)
    begin = matches[0].start()
    at = text.index("{", begin)+1
    depth = 1
    while depth:
        require(at < len(text), "unterminated protected function: "+name)
        if text.startswith("//", at):
            end = text.find("\n", at)
            at = len(text) if end < 0 else end+1
        elif text.startswith("/*", at):
            at = text.index("*/", at+2)+2
        elif text[at] in ("'", '"'):
            quote = text[at]
            at += 1
            while text[at] != quote:
                at += 2 if text[at] == "\\" else 1
            at += 1
        else:
            depth += (text[at] == "{")-(text[at] == "}")
            at += 1
    return sha(text[begin:at].encode())


def prepare(family, control_paths, frozen):
    require(family in PINS, "C/E adapter admits only C or E")
    pin = PINS[family]
    manifest_path = Path(control_paths[family]).resolve(strict=True)
    raw_report = manifest_path.read_bytes()
    require(sha(raw_report) == pin["report"], "unknown qualified "+family+" control report")
    report = json.loads(raw_report)
    require(report["features"]["variant"] == family, "control family differs")
    root = manifest_path.parent
    selected = report["selected"]
    require(selected["format"] == "sh-python3-source-stream-single" and selected["codec"] == "xz" and
            selected["source_literal"] == "raw-single" and selected["bytes"] == pin["whole_bytes"] and
            selected["sha256"] == pin["wrapper"] and selected["restored_native_sha256"] == pin["native"],
            "qualified selected stream identity differs")
    records = {item["id"]: item for item in report["engines"]}
    original = records["tiny-"+family+"-original"]
    compact_record = records["tiny-"+family+"-compact"]
    dev_record = records["tiny-"+family+"-dev"]
    flags = ["-std=c11", "-Os", "-pthread", "-DWORKERS=2", "-DTT_BITS=18"]
    if family == "C":
        flags.append("-mavx2")
    compiler_argv = ["cc", *flags, "-DDEV=0", "-x", "c", "-", "-o", "x"]
    dev_argv = ["cc", *flags, "-DDEV=1", "-x", "c", "-", "-o", "x"]
    require(original["compile"] == ["cc", *flags, "-DDEV=0", "main.c", "-o", "x"] and
            compact_record["compile"] == original["compile"] and
            dev_record["compile"] == ["cc", *flags, "-DDEV=1", "main.c", "-o", "x"],
            "qualified compiler/resource flags differ")
    readable = (root / "original/main.c").read_bytes()
    source = (root / "compact/main.c").read_bytes()
    native = (root / "compact/x.stdin").read_bytes()
    file_native = (root / "original/x").read_bytes()
    dev_native = (root / "dev/x").read_bytes()
    # Resolve the selected path relative to the original recorded producer root,
    # allowing an identical archived control tree to be moved without trusting
    # stale absolute paths embedded in its unchanged JSON receipt.
    recorded_root = Path(original["command"][0]).parent.parent
    selected_relative = Path(selected["path"]).relative_to(recorded_root)
    require(selected_relative == Path("compact/stream/xz/x"), "selected source linkage changed")
    wrapper = (root / selected_relative).read_bytes()
    for data, expected, label in ((readable, pin["readable"], "readable"), (source, pin["source"], "source"),
                                  (native, pin["native"], "stdin native"), (wrapper, pin["wrapper"], "wrapper"),
                                  (file_native, original["native_sha256"], "file native"),
                                  (dev_native, dev_record["native_sha256"], "DEV native")):
        require(sha(data) == expected, "qualified "+family+" "+label+" bytes changed")
    require(readable == (root / "dev/main.c").read_bytes() and len(wrapper) == pin["whole_bytes"],
            "qualified readable/DEV or whole-file length differs")
    frozen = Path(frozen)
    require(frozen.is_absolute(), "adapter snapshot must be absolute")
    frozen = frozen.resolve()
    require(not any((p / ".git").exists() for p in (frozen, *frozen.parents)), "adapter snapshot must be outside Git")
    local = frozen / ("family-"+family)
    require(not local.exists(), "family snapshot already exists")
    local.mkdir(parents=True)
    inputs = {}

    def write(name, data):
        path = local / relative(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        inputs[str(path.relative_to(frozen))] = sha(data)

    write("build.json", raw_report)
    for name, expected in report["input_sha256"].items():
        data = (root / "recipe" / relative(name)).read_bytes()
        require(sha(data) == expected, "qualified recipe input changed: "+name)
        write("recipe/"+name, data)
    for name, data in (("original/main.c", readable), ("compact/main.c", source),
                       ("compact/x.stdin", native), ("original/x", file_native),
                       ("dev/main.c", readable), ("dev/x", dev_native), (str(selected_relative), wrapper)):
        write(name, data)
    recipe = local / "recipe"
    scripts = recipe / "engines/scripts"
    ce = recipe / "engines/compact/tiny-ce"
    tiny_a = recipe / "engines/compact/tiny-a"
    tag = "tiny_uci_ce_"+family+"_"+sha(str(local).encode())[:12]
    stitch = load(tag+"_stitch", tiny_a / "stitch.py")
    overlay = load(tag+"_overlay", ce / "generate.py")
    specializer = load(tag+"_specialize", scripts / "specialize.py")
    minifier = load(tag+"_minify", scripts / "minify.py")
    stream = load(tag+"_stream", tiny_a / "pack_stream.py")
    names = ("tiny.h", "board.c", "search.c", "main.c")
    core = {name: (ce / "core" / name).read_bytes() for name in names}
    provenance = json.loads((ce / "core/provenance.json").read_bytes())
    entries = provenance["inputs"]
    require(len(entries) == 4 and {entry["frozen"] for entry in entries} == {"core/"+name for name in names},
            "fixed core provenance shape differs")
    for entry in entries:
        data = core[entry["frozen"].removeprefix("core/")]
        require(sha(data) == entry["sha256"] and len(data) == entry["bytes"], "fixed core provenance changed")
    rebuilt, layout = stitch.stitch(core, names, True)
    rebuilt, features = overlay.overlay(rebuilt, family, (ce / (family.lower()+"-eval.c.in")).read_bytes(),
                                        (ce / "frozen.json").read_bytes())
    state_record = None
    if family == "E":
        state = load(tag+"_state", recipe / "engines/experiments/tiny-e-state/generate.py")
        rebuilt, state_record = state.overlay(rebuilt, "state")
        require(state_record == report["state_overlay"], "state-overlay provenance differs")
    require(rebuilt == readable and features == report["features"] and layout == report["source_layout"],
            "canonical core/overlay regeneration differs from qualified readable source")
    # Bind actual selected bootstrap/source/compiler bytes before the common
    # builder performs its own whole-file baseline reconstruction.
    offset = selected["payload_offset_1based"]-1
    script = lzma.decompress(wrapper[offset:])
    expected_script, kind = stream.bootstrap(source, compiler_argv)
    require(script == expected_script and kind == "raw-single", "selected bootstrap/source/compiler linkage differs")
    tree = ast.parse((tiny_a / "pack_stream.py").read_text())
    make = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "make_stream")
    calls = [node for node in ast.walk(make) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
             and isinstance(node.func.value, ast.Name) and node.func.value.id == "lzma" and node.func.attr == "compress"]
    require(len(calls) == 1, "frozen XZ producer shape differs")
    keywords = {item.arg: ast.unparse(item.value) for item in calls[0].keywords}
    require(keywords == {"format": "lzma.FORMAT_XZ", "preset": "9 | lzma.PRESET_EXTREME"},
            "frozen selected compression profile differs")

    def generate(combined, directory, dev=False):
        directory = Path(directory)
        require(directory.is_absolute() and not directory.exists(), "fresh absolute specialization directory required")
        invocation = ["cc", *flags, "-DDEV="+str(int(dev)), "main.c", "-o", "x"]
        active, observations = specializer.specialize_c({"main.c": combined}, directory, invocation, os.environ.copy())
        result = minifier.compact_source(active["main.c"], "c")
        stripping = None
        if not dev:
            result, stripping = stitch.strip_dev_counters(result)
        (directory / "generation.json").write_text(json.dumps({"source_sha256": sha(combined), "dev": bool(dev),
                    "observations": observations, "counter_recipe": stripping, "result_sha256": sha(result)}, indent=2)+"\n")
        return result

    protected = ("value", "put", "ep", "make", "gen", "dead", "tiny_raw", "tiny_order", "probe", "claim",
                 "search", "think", "work", "wait", "clear", "set_position", "read_line", "result")
    if family == "C":
        protected += ("tiny_eval_init",)
    else:
        protected += ("tiny_center", "tiny_white")
    return {"family": family, "readable": readable, "source": source, "wrapper": wrapper,
            "expected_native_sha256": pin["native"], "compiler_argv": compiler_argv, "dev_argv": dev_argv,
            "compression": {"format": "xz", "preset": 9 | lzma.PRESET_EXTREME, "lc": 3, "lp": 0, "pb": 2, "check": "CRC64"},
            "input_sha256": inputs,
            "provenance": {"qualified_control_report_sha256": pin["report"], "qualified_control_path": str(manifest_path),
                           "readable_regenerated_exactly": True, "selected_source_bootstrap_exact": True,
                           "qualified_file_native_sha256": original["native_sha256"],
                           "qualified_DEV_native_sha256": dev_record["native_sha256"],
                           "features": features, "state_overlay": state_record, "core_provenance": provenance,
                           "protected_function_sha256": {name: body(readable, name) for name in protected},
                           "source_layout": layout, "source_generation": "frozen specialize/minify/strip; no identifier or codec sweep",
                           "feature_receipt_reuse_scope": "unchanged source bodies/core/model/flags; fresh policy runtime qualification remains separate"}}, generate
