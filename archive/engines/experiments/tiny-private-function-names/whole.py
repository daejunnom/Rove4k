#!/usr/bin/env python3
"""Package the three fixed static-only sources once with their original codec.

The accepted native metadata class is recorded separately. There is no native
compile, wrapper execution, codec search, or mutation of normal build guards.
"""

import argparse
import ast
import hashlib
import importlib.util
import json
import lzma
from pathlib import Path
import subprocess

PREPARED_SHA = "556bdff95f1e208141cb214e5866794beff695685ac1c05d8d6998d1adc29b9e"
NATIVE_SHA = "56a5159fa430e8e19a5ba024ccf8e4bf4de51d59cb904b4edeb63fb79208aaaa"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def identity(data):
    return {"bytes": len(data), "sha256": sha(data)}


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def source_argument(tree):
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Attribute) and node.func.attr == "communicate" and len(node.args) == 1]
    if len(calls) != 1:
        raise ValueError("one fixed compile-input communicate argument required")
    value = calls[0].args[0]
    if isinstance(value, ast.Constant) and isinstance(value.value, bytes):
        return value.value
    if (isinstance(value, ast.Call) and not value.args and not value.keywords
            and isinstance(value.func, ast.Attribute) and value.func.attr == "encode"
            and isinstance(value.func.value, ast.Constant) and isinstance(value.func.value.value, str)):
        return value.func.value.value.encode()
    raise ValueError("unsupported source literal expression")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", required=True, type=Path)
    parser.add_argument("--native", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    prepared, native, out = args.prepared.resolve(), args.native.resolve(), args.out.resolve()
    prep_raw, native_raw = (prepared / "prepare.json").read_bytes(), (native / "native.json").read_bytes()
    if sha(prep_raw) != PREPARED_SHA or sha(native_raw) != NATIVE_SHA:
        raise ValueError("fixed source/native observation receipt mismatch")
    prep, native_report = json.loads(prep_raw), json.loads(native_raw)
    if not prep["complete"] or not native_report["complete"] or not args.out.is_absolute() or out.exists():
        raise ValueError("complete fixed inputs and new absolute output required")
    if any((p / ".git").exists() for p in (out, *out.parents)):
        raise ValueError("external output required")
    out.mkdir(parents=True)
    report = {"complete": False, "scope": __doc__, "prepared_sha256": sha(prep_raw), "native_observation_sha256": sha(native_raw),
              "metadata_class": "root admitted observed PHDR/code/data/dynamic/reloc equality, allocated build-ID descriptor and e_shoff plus nonallocated metadata differences only",
              "full_native_equality": False, "normal_guard_changed": False,
              "families": {}, "codec_encode_calls": 0, "native_compiles": 0, "engine_executions": 0}
    def save():
        (out / "whole.json").write_bytes((json.dumps(report, indent=2) + "\n").encode())
    save()
    try:
        config_raw = (prepared / "producer-prepare.py").read_bytes()
        if identity(config_raw) != prep["producer"]["prepare.py"]:
            raise ValueError("fixed Git-source reader changed")
        config = module(prepared / "producer-prepare.py", "private_whole_source_reader")
        for family, prepared_row in prep["families"].items():
            entry = "engines/compact/tiny-entry-" + family.lower() + "/"
            recipe_raw = (prepared / "inputs" / entry / "recipe.json").read_bytes()
            if identity(recipe_raw) != prep["inputs"][entry + "recipe.json"]:
                raise ValueError("fixed source recipe changed")
            recipe = json.loads(recipe_raw)
            source = (prepared / family / "candidate.c").read_bytes()
            if identity(source) != prepared_row["after"]:
                raise ValueError("fixed static-only source changed")
            directory = out / family
            directory.mkdir()
            inputs = {}
            for relative in (entry + "bootstrap.py.in", entry + "launcher.sh", "engines/compact/tiny-a/pack_stream.py"):
                data = config.git_source(prep["git_read_command"], relative)
                expected = (recipe["local_input_sha256"].get(Path(relative).name)
                            if relative.startswith(entry) else recipe["helper_sha256"][relative])
                if sha(data) != expected:
                    raise ValueError("original packaging input differs: " + relative)
                (directory / Path(relative).name).write_bytes(data)
                inputs[relative] = identity(data)
            prefix, template = (directory / "launcher.sh").read_bytes(), (directory / "bootstrap.py.in").read_bytes()
            marker = b"__ROVE_SOURCE_LITERAL__"
            if len(prefix) != 75 or template.count(marker) != 1:
                raise ValueError("original prefix/template shape changed")
            literal = module(directory / "pack_stream.py", "private_literal_" + family).source_literal
            expression, kind = literal(source)
            script = template.replace(marker, expression.encode())
            tree = ast.parse(script)
            popens = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                      and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
                      and node.func.value.id == "subprocess" and node.func.attr == "Popen"]
            if len(popens) != 1 or ast.literal_eval(popens[0].args[0]) != recipe["compiler"]:
                raise ValueError("strict compiler argv restoration differs")
            if source_argument(tree) != source:
                raise ValueError("strict source literal restoration differs")
            codec = recipe["compression"]
            if codec != {"format": "xz", "filter": "LZMA2", "preset": 9, "extreme": True,
                         "lc": 3, "lp": 0, "pb": 2, "check": "CRC64"}:
                raise ValueError("original fixed BCE codec changed")
            payload = lzma.compress(script, format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64,
                                    filters=[{"id": lzma.FILTER_LZMA2, "preset": 9 | lzma.PRESET_EXTREME,
                                              "lc": 3, "lp": 0, "pb": 2}])
            report["codec_encode_calls"] += 1
            decoder = lzma.LZMADecompressor(format=lzma.FORMAT_XZ)
            if decoder.decompress(payload) != script or not decoder.eof or decoder.unused_data:
                raise ValueError("strict original-codec restoration failed")
            decoded = subprocess.run(["xz", "-dc"], input=payload, capture_output=True, timeout=15)
            if decoded.returncode or decoded.stderr or decoded.stdout != script:
                raise ValueError("independent CLI XZ restoration failed")
            whole = prefix + payload
            (directory / "bootstrap.py").write_bytes(script)
            (directory / "x").write_bytes(whole)
            (directory / "x").chmod(0o755)
            report["families"][family] = {"source": identity(source), "bootstrap": identity(script),
                "whole": identity(whole), "baseline_whole_bytes": recipe["expected"]["whole_bytes"],
                "gain_bytes": recipe["expected"]["whole_bytes"] - len(whole), "original_codec": codec,
                "packaging_inputs": inputs, "literal_kind": kind,
                "source_and_compiler_argv_restored_exactly": True, "Python_strict_and_CLI_restore_exact": True,
                "no_wrapper_or_native_executed": True}
            save()
            print(json.dumps({"family": family, "whole": identity(whole),
                              "gain": report["families"][family]["gain_bytes"]}), flush=True)
        report["complete"] = True
        save()
    except Exception as error:
        report["error"] = repr(error)
        save()
        raise


if __name__ == "__main__":
    main()
