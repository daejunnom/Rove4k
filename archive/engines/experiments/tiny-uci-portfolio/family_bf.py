"""Pinned B/F control adapters for one shared shipping UCI policy experiment.

``prepare`` freezes the qualified receipts, complete readable-source lineage and
selected encoding inputs under an already-created, family-owned external root.
It reruns only pure overlay/stitch preparation before returning. The supplied
generator later runs the same fixed preprocessor/minifier/counter/spelling
recipe; it performs no compiler, spelling, resource or codec search. The shared
builder owns baseline source/native/whole reproduction, policy transformation,
DEV byte comparisons, core-body equality receipts and runtime qualification.
"""

import hashlib
import importlib.util
import json
import lzma
import os
from pathlib import Path, PurePosixPath


DEFAULT_PATHS = {
    "B": {
        "build": "/home/stemxstudio/rove4k-tiny-b-final-20261020/build.json",
        "validation": "/home/stemxstudio/rove4k-tiny-b-final-20261020/validation-manifest.json",
        "identity": "/home/stemxstudio/rove4k-tiny-b-image-20261020/results.json",
    },
    "F": {
        "build": "/home/stemxstudio/rove4k-tiny-f-structural-20261020/build.json",
        "encoding": "/home/stemxstudio/rove4k-tiny-f-encoding-v2-20261020/results.json",
        "qualification": "/home/stemxstudio/rove4k-tiny-f-final-proof-v3-20261020/results.json",
    },
}
REPORT_PINS = {
    "B": {
        "build": "f506e50eaf165dd5b9bbd7c030104d372a39064903849ef1d5f05a95107221bc",
        "validation": "784e2b22107e2a0d51463d6ff17d9eb7773618dab217fc81d849edb72f786a5b",
        "identity": "d2bddfc0aa7721ff56a6320b35b992f0c4a57b9d2aa799edd34430de3861654b",
    },
    "F": {
        "build": "efd7f328b8839a9d2a1025268c349224f3269bba83f2f11b42afbde3d33518fa",
        "encoding": "6dcc89d8d11303181e5fad38e7a5d9187d7c3ca2b6e05e7a57ba7676e2b5cc7d",
        "qualification": "62b04e0c5eddaf6d1adcf25b18315dfad43437d20efb6fd0d06b37cde600e173",
    },
}
CONTROL_PINS = {
    "B": {
        "readable": "8130f0cde0c30679c84e6ec8c5bb6967e9d9b8ed19223c3856a05126cee4fa7c",
        "source": "14b8da672881a480d85dd7a5ea3c3f746ba48b55236f2e579c17c400ff7b65c8",
        "wrapper": "58ade8a95d80e89d84bf0f638844aa8befb45feae292b20ae0839abe34e79cb6",
        # The file-compiled ELF is a different identity class. This is the
        # actually restored compiler-stdin image admitted by qualify.py.
        "native": "95d2e80ef1675f669a2c81860de3768271e5118b5d0d5771e7af787777f59362",
    },
    "F": {
        "readable": "ccc7a4b232cebdad7f00c5fe6b0dbff718b51c895db0c9996467679841af59a3",
        "source": "1c1ef488085da1022357ca1ae1ddd29c53039c3dc5557653f714c8d291117709",
        "wrapper": "5b61c8cc14a21de3c8ac446439d4d90ebb8ea909e9e3d3d0161c692fb2ab6082",
        "native": "71b9b39ceb59024fce3fdc87b1a4c22d38af5ef88e89a5f841e96e4ca8ecdb4b",
    },
}
_LAYOUT = ("tiny.h", "board-generated.c.in", "search.c", "main.c")


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _engine(build, name):
    records = [record for record in build["engines"] if record["id"] == name]
    if len(records) != 1:
        raise ValueError("expected one qualified engine: " + name)
    return records[0]


def _stdin(command):
    if command.count("main.c") != 1:
        raise ValueError("expected one main.c compiler input")
    result = []
    for item in command:
        result.extend(["-x", "c", "-"] if item == "main.c" else [item])
    return result


def prepare(family, control_paths, frozen):
    """Return ``(control, generate)`` using the fixed, qualified B/F receipts.

    ``control_paths`` has exactly the keys in ``DEFAULT_PATHS[family]``; relocated
    identical receipts are accepted. ``frozen`` must be an existing absolute
    directory owned exclusively by this family call. No existing different
    file is overwritten. Callback signature: ``generate(combined, directory,
    dev=False) -> bytes``. Only that callback invokes the C preprocessor.
    """
    if family not in REPORT_PINS or set(control_paths) != set(REPORT_PINS[family]):
        raise ValueError("unsupported family or control receipt set")
    frozen = Path(frozen)
    if not frozen.is_absolute() or not frozen.is_dir():
        raise ValueError("existing absolute family-owned frozen directory required")
    input_hashes = {}

    def retain(name, data):
        relative = PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts or "\\" in name:
            raise ValueError("unsafe frozen input name")
        target = frozen.joinpath(*relative.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.read_bytes() != data:
            raise ValueError("existing frozen input differs: " + name)
        target.write_bytes(data)
        input_hashes[name] = _sha(data)
        return data

    def admitted(path, expected, name):
        data = Path(path).read_bytes()
        if _sha(data) != expected:
            raise ValueError("qualified input drift: " + str(path))
        return retain(name, data)

    raw_reports, reports = {}, {}
    for name, expected in REPORT_PINS[family].items():
        raw_reports[name] = admitted(control_paths[name], expected, "receipts/" + name + ".json")
        reports[name] = json.loads(raw_reports[name])
    build = reports["build"]
    build_directory = Path(control_paths["build"]).parent
    recipe_inputs = build["recipe_sha256"] if family == "B" else {
        name: record["sha256"] for name, record in build["recipe_inputs"].items()}
    for name, expected in recipe_inputs.items():
        relative = PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts or "\\" in name:
            raise ValueError("unsafe source recipe path")
        admitted(build_directory / "recipe" / name, expected, "source-recipe/" + name)

    source_recipe = frozen / "source-recipe"
    compact_root = source_recipe / "engines/compact"
    scripts = source_recipe / "engines/scripts"
    specialize = _module("tiny_uci_" + family + "_specialize", scripts / "specialize.py").specialize_c
    compact = _module("tiny_uci_" + family + "_minify", scripts / "minify.py").compact_source
    if family == "B":
        directory = compact_root / "tiny-b"
        overlay = _module("tiny_uci_B_overlay", directory / "generate.py")
        stitch = _module("tiny_uci_B_stitch", directory / "base/stitch.py").stitch
        stream = _module("tiny_uci_B_stream", directory / "base/pack_stream.py")
        generated_readable, layout = stitch(overlay.sources(), _LAYOUT, True)
        compact_record = _engine(build, "tiny-B-compact")
        readable_record = _engine(build, "tiny-B-dev")
        readable = admitted(build_directory / "combined.c", CONTROL_PINS[family]["readable"], "control/readable.c")
        source = admitted(Path(compact_record["cwd"]) / "main.c", CONTROL_PINS[family]["source"], "control/source.c")
        selected = reports["validation"]["selected"]
        identity = reports["identity"]
        if (not identity["passed"] or selected["bytes"] != 6283 or selected["codec"] != "xz" or
                identity["whole_file_sha256"] != CONTROL_PINS[family]["wrapper"] or
                identity["source_sha256"] != CONTROL_PINS[family]["source"] or
                identity["native_sha256"] != CONTROL_PINS[family]["native"]):
            raise ValueError("qualified B wrapper/STDIN identity binding differs")
        compiler_argv = identity["compiler_stdin_argv"]
        expected_command = ["cc", "-std=c11", "-Os", "-pthread", "-DWORKERS=2", "-DTT_BITS=18", "-DDEV=0", "-x", "c", "-", "-o", "x"]
        flags = ["-std=c11", "-Os", "-pthread", "-DWORKERS=2", "-DTT_BITS=18"]
        compression = {"format": "xz", "preset": 9 | lzma.PRESET_EXTREME,
                       "lc": 3, "lp": 0, "pb": 2, "check": "CRC64"}
        encoding_policy = None
    else:
        directory = compact_root / "tiny-f"
        overlay = _module("tiny_uci_F_overlay", directory / "overlay.py")
        stitch = _module("tiny_uci_F_stitch", compact_root / "tiny-a/stitch.py").stitch
        original = {name: (compact_root / "tiny-a" / name).read_bytes() for name in overlay.EXPECTED}
        generated_sources = overlay.transform(original, (directory / "search.c").read_bytes())
        generated_sources, structure = overlay.co_design(generated_sources)
        if structure != build["structure"]:
            raise ValueError("qualified F structural recipe changed")
        generated_readable, layout = stitch(generated_sources, _LAYOUT, True)
        readable_record = _engine(build, "tiny-F-dev")
        compact_record = _engine(build, "tiny-F-compact")
        readable = admitted(Path(readable_record["cwd"]) / "main.c", CONTROL_PINS[family]["readable"], "control/readable.c")
        encoding, qualification = reports["encoding"], reports["qualification"]
        binding = qualification["encoding_binding"]
        if (not encoding["passed"] or not qualification["passed"] or
                binding["build_manifest_sha256"] != _sha(raw_reports["build"]) or
                binding["encoding_report_sha256"] != _sha(raw_reports["encoding"]) or
                binding["compact_source_sha256"] != compact_record["source_sha256"] or
                encoding["input_source_sha256"] != compact_record["source_sha256"] or
                encoding["reference_native"]["sha256"] != CONTROL_PINS[family]["native"] or
                encoding["actual_native"]["sha256"] != CONTROL_PINS[family]["native"]):
            raise ValueError("qualified F build/encoding/native binding differs")
        encoding_root = Path(control_paths["encoding"]).parent
        if set(encoding["input_hashes"]) != {"encode.py", "rename_c.py", "pack_stream.py", "main.c", "input-build.json"}:
            raise ValueError("qualified F encoding input set changed")
        for name, expected in encoding["input_hashes"].items():
            admitted(encoding_root / "frozen" / name, expected, "encoding-recipe/" + name)
        if encoding["input_hashes"]["input-build.json"] != _sha(raw_reports["build"]):
            raise ValueError("F encoding belongs to another build")
        source = admitted(encoding_root / "frozen/fixed-main.c", CONTROL_PINS[family]["source"], "control/source.c")
        lexer = _module("tiny_uci_F_lexer", frozen / "encoding-recipe/rename_c.py")
        stream = _module("tiny_uci_F_stream", frozen / "encoding-recipe/pack_stream.py")
        encoding_policy = encoding["representation"]
        selected = encoding["selected"]
        if selected["bytes"] != 5551 or selected["xz_parameters"] != {"lc": 2, "lp": 0, "pb": 0, "preset": "9e", "check": "CRC64"}:
            raise ValueError("qualified F selected XZ representation changed")
        compiler_argv = encoding["actual_native"]["command"]
        expected_command = ["cc", "-Os", "-pthread", "-x", "c", "-", "-o", "x", "-s"]
        flags = build["fixed_flags"]
        if flags != ["-std=c11", "-Os", "-pthread", "-DWORKERS=2", "-DTT_BITS=18", "-DPLY=128"]:
            raise ValueError("qualified F fixed resource recipe changed")
        if encoding_policy["fixed_profile"] != {"WORKERS": 2, "TT_BITS": 18, "PLY": 128}:
            raise ValueError("qualified F fixed source profile changed")
        compression = {"format": "xz", "preset": 9 | lzma.PRESET_EXTREME,
                       "lc": 2, "lp": 0, "pb": 0, "check": "CRC64"}
    if compiler_argv != expected_command:
        raise ValueError("qualified compiler-stdin argv changed")
    if generated_readable != readable or readable_record["source_sha256"] != CONTROL_PINS[family]["readable"]:
        raise ValueError("frozen readable source lineage did not reproduce")
    wrapper = admitted(selected["path"], CONTROL_PINS[family]["wrapper"], "control/wrapper")
    if len(wrapper) != selected["bytes"] or selected["sha256"] != CONTROL_PINS[family]["wrapper"]:
        raise ValueError("qualified selected wrapper differs")

    def generate(combined, directory, dev=False):
        command = ["cc", *flags, "-DDEV=" + str(int(dev)), "main.c", "-o", "x"]
        active, _ = specialize({"main.c": combined}, directory, command, os.environ.copy())
        result = compact(active["main.c"], "c")
        if dev:
            return result
        result, _ = overlay.strip_counters(result)
        if family == "F":
            files = {"main.c": result}
            for name, value in encoding_policy["fixed_profile"].items():
                count = sum(token == name for _, _, token in lexer._identifier_spans(files["main.c"].decode()))
                if count != encoding_policy["resource_token_counts"][name]:
                    raise ValueError("F fixed resource token count changed: " + name)
                files = lexer._replace(files, name, str(value))
            for name, alias in encoding_policy["function_spellings"].items():
                files = lexer._replace(files, name, alias)
            result = files["main.c"]
        return result

    provenance = {"qualified_reports": {name: {"path": str(control_paths[name]), "sha256": expected}
                                         for name, expected in REPORT_PINS[family].items()},
                  "readable_lineage_reproduced": True, "source_layout": layout,
                  "readable_sha256": _sha(readable), "selected_source_sha256": _sha(source),
                  "selected_wrapper_sha256": _sha(wrapper), "selected_wrapper_bytes": len(wrapper),
                  "native_identity_class": "actual restored compiler-stdin executable",
                  "fixed_spelling_policy": encoding_policy,
                  "historical_algorithm_proofs": "reuse requires shared builder's actual unchanged core/DEV equality receipts"}
    control = {"family": family, "readable": readable, "source": source, "wrapper": wrapper,
               "expected_native_sha256": CONTROL_PINS[family]["native"],
               "compiler_argv": list(compiler_argv), "dev_argv": _stdin(readable_record["compile"]),
               "compression": compression, "source_literal": stream.source_literal,
               "input_sha256": dict(sorted(input_hashes.items())), "provenance": provenance}
    return control, generate
