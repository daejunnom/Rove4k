#!/usr/bin/env python3
"""Prepare explicit E representation source candidates from one frozen snapshot."""
import argparse
import hashlib
import json
from pathlib import Path

if __package__:
    from .generate import FORMATS, ROOT, generated_sources, load_model, metadata, sources, static_consumer
else:
    from generate import FORMATS, ROOT, generated_sources, load_model, metadata, sources, static_consumer


def transform_sources(files, *, representation, language, model):
    """Pure selected-format transform of explicit source bytes and model data.

    Names are engine-relative (c/model.h, rust/eval.rs, model/frozen.*). varint
    returns the input bytes unchanged after checking the canonical model header.
    static16 changes only the selected language's header and consumer. The caller
    loads/freezes model JSON and controls applicability, I/O, profiles and tools.
    """
    if representation not in ("varint", "static16"):
        raise ValueError("selected model format must be varint or static16")
    if language not in ("c", "rust"):
        raise ValueError("model format language must be c or rust")
    if any(type(name) is not str or type(data) is not bytes for name, data in files.items()):
        raise ValueError("source inputs must map string names to immutable bytes")
    header = "frozen.h" if language == "c" else "frozen.rs"
    header_name = "model/" + header
    if header_name not in files:
        raise ValueError("missing canonical model header: " + header_name)
    canonical = generated_sources(model)[header]
    if files[header_name].decode("utf-8").replace("\r\n", "\n") != canonical:
        raise ValueError("source does not use the exact canonical reference model: " + header_name)
    output = dict(files)
    if representation == "static16":
        consumer = "c/model.h" if language == "c" else "rust/eval.rs"
        if consumer not in files:
            raise ValueError("missing model consumer: " + consumer)
        output[header_name] = sources(representation, model)[header].encode("utf-8")
        output[consumer] = static_consumer(language, files[consumer].decode("utf-8")).encode("utf-8")
    record = metadata(representation, model)
    record["language"] = language
    record["changed_sources"] = [
        {"path": name, "original_sha256": hashlib.sha256(files[name]).hexdigest(),
         "sha256": hashlib.sha256(data).hexdigest()}
        for name, data in sorted(output.items()) if data != files[name]
    ]
    return output, record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True, help="frozen tree containing c/rust/model")
    parser.add_argument("--out", type=Path, required=True, help="new absolute directory outside checkout")
    parser.add_argument("--formats", default=",".join(FORMATS))
    args = parser.parse_args()
    formats = args.formats.split(",")
    if any(fmt not in FORMATS for fmt in formats) or len(set(formats)) != len(formats):
        parser.error("unknown or duplicate representation")
    if not args.out.is_absolute() or args.out.resolve().is_relative_to(ROOT) or args.out.exists():
        parser.error("--out must be a new absolute directory outside checkout")
    model = load_model()
    inputs = {}
    for folder, suffixes in (("c", {".c", ".h"}), ("rust", {".rs"}), ("model", {".h", ".rs"})):
        for path in sorted((args.source_root / folder).rglob("*")):
            if path.is_file() and path.suffix in suffixes:
                name = path.relative_to(args.source_root).as_posix()
                inputs[name] = path.read_bytes()
    canonical = generated_sources(model)
    for name in ("frozen.h", "frozen.rs"):
        data = inputs["model/" + name].decode("utf-8").replace("\r\n", "\n")
        if data != canonical[name]:
            raise ValueError("snapshot does not use the exact canonical reference model: " + name)
    input_hashes = {name: hashlib.sha256(data).hexdigest() for name, data in inputs.items()}
    records = []
    for fmt in formats:
        output = dict(inputs)
        output.update({"model/" + name: text.encode("utf-8") for name, text in sources(fmt, model).items()})
        if fmt == "static16":
            for language, name in (("c", "c/model.h"), ("rust", "rust/eval.rs")):
                output[name] = static_consumer(language, inputs[name].decode("utf-8")).encode("utf-8")
        directory = args.out / fmt / "sources"
        for name, data in output.items():
            path = directory / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        record = metadata(fmt, model)
        record.update({"frozen_source_root": str(args.source_root.resolve()),
                       "source_root": str(directory), "input_source_sha256": input_hashes,
                       "changed_sources": [{"path": name, "sha256": hashlib.sha256(data).hexdigest(),
                                            "original_sha256": input_hashes[name]}
                                           for name, data in output.items() if data != inputs[name]]})
        (directory.parent / "representation.json").write_text(json.dumps(record, indent=2) + "\n")
        records.append(record)
    (args.out / "prepared.json").write_text(json.dumps({"candidates": records}, indent=2) + "\n")
    print(json.dumps({"prepared": str(args.out), "formats": formats, "input_sources": len(inputs)}))


if __name__ == "__main__":
    main()
