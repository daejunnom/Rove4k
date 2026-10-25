#!/usr/bin/env python3
"""Apply the other owner's one fixed local-name allocator to static-only C.

The allocator is raw-pinned and frozen externally before import. No alternate
AST allocator, native compile, source preprocessing, codec or engine is used.
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

API_SHA = "02ca17d1c251945f1c021e3482272ef891485c2227a90b4712a36b987d29f08b"
PREPARED_SHA = "556bdff95f1e208141cb214e5866794beff695685ac1c05d8d6998d1adc29b9e"
NATIVE_SHA = "56a5159fa430e8e19a5ba024ccf8e4bf4de51d59cb904b4edeb63fb79208aaaa"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def identity(data):
    return {"bytes": len(data), "sha256": sha(data)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", required=True, type=Path)
    parser.add_argument("--native", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    prepared, native, out = args.prepared.resolve(), args.native.resolve(), args.out.resolve()
    prep_raw, native_raw = (prepared / "prepare.json").read_bytes(), (native / "native.json").read_bytes()
    if sha(prep_raw) != PREPARED_SHA or sha(native_raw) != NATIVE_SHA:
        raise ValueError("fixed static source/native observation receipts differ")
    prep, native_report = json.loads(prep_raw), json.loads(native_raw)
    if not prep["complete"] or not native_report["complete"] or not args.out.is_absolute() or out.exists():
        raise ValueError("complete exact inputs and new absolute output required")
    if any((p / ".git").exists() for p in (out, *out.parents)):
        raise ValueError("external output required")
    api_path = Path(__file__).resolve().parents[1] / "tiny-scope-names/rename.py"
    api_raw = api_path.read_bytes()
    if sha(api_raw) != API_SHA:
        raise ValueError("other owner's fixed independent allocator changed")
    out.mkdir(parents=True)
    dependency = out / "allocator.py"
    dependency.write_bytes(api_raw)
    spec = importlib.util.spec_from_file_location("private_fixed_scoped_allocator", dependency)
    allocator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(allocator)
    config_path = prepared / "producer-prepare.py"
    if identity(config_path.read_bytes()) != prep["producer"]["prepare.py"]:
        raise ValueError("fixed tool configuration changed")
    spec = importlib.util.spec_from_file_location("private_composed_tool_config", config_path)
    config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config)
    report = {"complete": False, "scope": __doc__, "prepared_receipt_sha256": sha(prep_raw),
              "static_native_receipt_sha256": sha(native_raw), "allocator": identity(api_raw),
              "families": {}, "native_compiles": 0, "codec_calls": 0, "engine_executions": 0}
    def save():
        (out / "compose.json").write_bytes((json.dumps(report, indent=2) + "\n").encode())
    save()
    try:
        for family, row in prep["families"].items():
            source = (prepared / family / "candidate.c").read_bytes()
            if identity(source) != row["after"]:
                raise ValueError("fixed static-only source changed")
            relative = "engines/compact/tiny-entry-" + family.lower() + "/recipe.json"
            recipe_raw = (prepared / "inputs" / relative).read_bytes()
            if identity(recipe_raw) != prep["inputs"][relative]:
                raise ValueError("fixed compiler recipe changed")
            recipe = json.loads(recipe_raw)
            arguments = recipe["compiler"][1:recipe["compiler"].index("-x")]
            if not any(arg.startswith("-std=") for arg in arguments):
                arguments += ["-std=gnu17"]
            candidate, metadata = allocator.rewrite(source, clang_site=config.LIB,
                resource_dir=config.RESOURCE, arguments=arguments)
            if not metadata["protected_declaration_shapes_equal"]:
                raise ValueError("scoped-local declaration graph gate failed")
            directory = out / family
            directory.mkdir()
            (directory / "candidate.c").write_bytes(candidate)
            (directory / "allocator.json").write_bytes((json.dumps(metadata, indent=2) + "\n").encode())
            report["families"][family] = {"static_source": identity(source), "combined_source": identity(candidate),
                "static_native": native_report["families"][family]["candidate"],
                "static_native_path": native_report["families"][family]["candidate_path"],
                "compiler": recipe["compiler"], "AST_arguments": arguments,
                "allocator_metadata_sha256": sha((directory / "allocator.json").read_bytes())}
            save()
        if api_path.read_bytes() != api_raw:
            raise ValueError("other owner's source changed during use")
        report["complete"] = True
        save()
        print(json.dumps({family: row["combined_source"] for family, row in report["families"].items()}), flush=True)
    except Exception as error:
        report["error"] = repr(error)
        save()
        raise


if __name__ == "__main__":
    main()
