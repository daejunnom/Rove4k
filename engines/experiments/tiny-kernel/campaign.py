#!/usr/bin/env python3
"""Produce one fixed Tiny A kernel comparison; no spelling or codec search.

The committed control, ordered spelling recipe and current helper hashes are
pinned before imports. Every native stage is independently compiled twice.
Shipping transformations require complete stripped-ELF byte equality per form;
the baseline additionally has exact historical source/native/bootstrap/wrapper
hash gates. Correctness and strength qualification are separate work.
"""
import argparse
import hashlib
import importlib.util
import json
import lzma
import os
from pathlib import Path
import re
import subprocess
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SHIPPING = ["cc", "-std=c11", "-Os", "-pthread", "-DWORKERS=2", "-DTT_BITS=18",
            "-DDEV=0", "-x", "c", "-", "-o", "x", "-s"]
ENCODED = ["cc", "-Os", "-x", "c", "-", "-o", "x", "-s"]
DEVELOPMENT = ["cc", "-std=c11", "-Os", "-pthread", "-DWORKERS=2", "-DTT_BITS=18",
               "-DDEV=1", "-x", "c", "-", "-o", "x"]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def compile_twice(source, command, directory):
    directory.mkdir()
    (directory / "main.c").write_bytes(source)
    record = {"source_sha256": sha(source), "source_bytes": len(source),
              "command": command, "directory": str(directory), "runs": []}
    previous = None
    for number in (1, 2):
        process = subprocess.run(command, input=source, cwd=directory,
                                 capture_output=True, timeout=60)
        (directory / f"compile-{number}.stdout").write_bytes(process.stdout)
        (directory / f"compile-{number}.stderr").write_bytes(process.stderr)
        item = {"returncode": process.returncode,
                "stdout_sha256": sha(process.stdout), "stderr_sha256": sha(process.stderr)}
        record["runs"].append(item)
        save(directory / "compile.json", record)
        if process.returncode:
            raise RuntimeError("compiler failed; see " + str(directory / "compile.json"))
        image = (directory / "x").read_bytes()
        item.update(native_bytes=len(image), native_sha256=sha(image))
        if previous is not None:
            require(image == previous, "independent native bytes differ: " + str(directory))
        previous = image
    record.update(native_bytes=len(image), native_sha256=sha(image), reproduced=True)
    save(directory / "compile.json", record)
    return image, record


def identifier_spans(text, lexer, macro_bodies=False):
    """Include only owned K_* macro bodies in the kernel's lexical domain.

    The shared historical lexer intentionally excludes directives. Its ordinary
    spans stay unchanged for baseline. A K_EMIT body shares function-local names
    and must follow their fixed spelling; quotes/comments still use that same
    lexer. Continued physical macro lines retain original offsets.
    """
    spans = list(lexer._identifier_spans(text))
    if macro_bodies:
        for definition in re.finditer(r"(?m)^[ \t]*#[ \t]*define[ \t]+K_[A-Za-z_0-9]+", text):
            end = text.find("\n", definition.end())
            while end >= 0 and text[:end].endswith("\\"):
                end = text.find("\n", end + 1)
            if end < 0:
                end = len(text)
            for begin, finish, token in lexer._identifier_spans(text[definition.end():end]):
                spans.append((definition.end() + begin, definition.end() + finish, token))
    return sorted(spans)


def strip_kernel_counters(source, lexer):
    """Replace exact diagnostic calls with empty statements, preserving grammar.

    A counter under if/else must not expose the following production statement
    to that condition. Empty statements retain that control-flow shape; the
    mandatory complete-native gate decides whether the removal is admissible.
    """
    text, definitions = re.subn(r"(?m)^#define COUNT\(w,f\) \(\(void\)0\)\n", "", source.decode())
    require(definitions == 1, "expected one known no-op COUNT definition")
    noop_macros = {}
    for name, pattern in (
            ("K_OBSERVE", r"(?m)^#define K_OBSERVE\(w,m,stage,rank\) \(\(void\)0\)\n"),
            ("K_COLLECTED", r"(?m)^#define K_COLLECTED\(\)\s*\n")):
        text, removed = re.subn(pattern, "", text)
        require(removed == 1, "expected exact no-op definition: " + name)
        noop_macros[name] = {"definitions": removed}
    observer = (r"\bK_OBSERVE\s*\(\s*w\s*,\s*m\s*,\s*stage\s*,\s*"
                r"ranks\s*\[\s*count\s*-\s*1\s*\]\s*\)\s*;")
    for name, pattern in (("K_OBSERVE", observer), ("K_COLLECTED", r"\bK_COLLECTED\s*\(\s*\)\s*;")):
        text, removed = re.subn(pattern, ";", text)
        require(removed == 1, "expected exact no-op invocation: " + name)
        noop_macros[name]["calls"] = removed
    text, removed = re.subn(r"(?m)^#undef K_COLLECTED\n", "", text)
    require(removed == 1, "expected collection macro cleanup")
    noop_macros["K_COLLECTED"]["undefs"] = removed
    edits, calls = [], []
    for begin, end, token in identifier_spans(text, lexer, True):
        if token != "COUNT":
            continue
        match = re.match(r"\(\s*([A-Za-z_]\w*)\s*,\s*([A-Za-z_]\w*)\s*\)\s*;", text[end:])
        require(match is not None, "unknown COUNT invocation shape")
        edits.append((begin, end + match.end()))
        calls.append({"worker": match[1], "field": match[2]})
    for begin, end in reversed(edits):
        text = text[:begin] + ";" + text[end:]
    require(not any(token in ("COUNT", "K_OBSERVE", "K_COLLECTED")
                    for _, _, token in identifier_spans(text, lexer, True)),
            "unremoved diagnostic token")
    return text.encode(), {"recipe": "exact-noop-macro-and-simple-calls-to-empty-statements",
                           "removed_definitions": definitions, "calls": calls,
                           "noop_macros": noop_macros,
                           "removed_noop_counter_calls": len(calls),
                           "required_native_byte_identity": True}


def fixed_spellings(source, recipe, lexer, macro_bodies=False):
    changes = []
    groups = (("accepted-identifiers", [(item["identifier"], item["replacement"])
                                       for item in recipe["ordered_identifier_steps"]]),
              ("fixed-resources", list(recipe["resource_literals"].items())),
              ("manual-functions", list(recipe["manual_function_spellings"].items())))
    for group, steps in groups:
        for old, new in steps:
            text = source.decode()
            spans = identifier_spans(text, lexer, macro_bodies)
            tokens = [token for _, _, token in spans]
            count = tokens.count(old)
            if count and new != old and re.fullmatch(r"[A-Za-z_]\w*", new):
                require(new not in tokens, f"fixed spelling collision: {old}->{new}")
            for begin, end, token in reversed(spans):
                if token == old:
                    text = text[:begin] + new + text[end:]
            source = text.encode()
            changes.append({"group": group, "identifier": old, "replacement": new,
                            "occurrences": count})
    return source, changes


def package(source, recipe, producer, expression):
    script, kind = producer.bootstrap(source, recipe["compiler"])
    script = expression.replace_argument(script, "subprocess", "Popen",
                                         repr(" ".join(recipe["compiler"])) + ".split()")
    require(expression.value(expression.argument(script, "p", "communicate")) == source,
            "bootstrap compiler stdin differs from exact C source")
    require(expression.value(expression.argument(script, "subprocess", "Popen")) == recipe["compiler"],
            "bootstrap compiler argv differs from fixed command")
    offset = 1
    while True:
        prefix = (f'#!/bin/sh\np=$(tail -c+{offset} "$0"|xz -dc)||exit\n'
                  'exec python3 -c "$p" "$0" "$@"\n').encode()
        if offset == len(prefix) + 1:
            break
        offset = len(prefix) + 1
    filters = [{"id": lzma.FILTER_LZMA2, "preset": 9 | lzma.PRESET_EXTREME,
                "lc": 2, "lp": 0, "pb": 0}]
    payload = lzma.compress(script, format=lzma.FORMAT_XZ,
                            check=lzma.CHECK_CRC64, filters=filters)
    require(lzma.decompress(payload) == script, "lossless XZ restoration failed")
    whole = prefix + payload
    return whole, script, {"codec": "xz-lc2-lp0-pb0", "source_literal": kind,
                           "argv_representation": "split", "launcher_bytes": len(prefix),
                           "payload_bytes": len(payload), "decoded_bytes": len(script),
                           "decoded_sha256": sha(script), "bytes": len(whole), "sha256": sha(whole),
                           "external_programs": ["sh", "tail", "xz", "python3", "cc"]}


def produce(output, reference_wrapper=None):
    output = output.resolve()
    require(not output.exists() and output != ROOT and ROOT not in output.parents,
            "new absolute external output required")
    recipe_bytes = (HERE / "spelling.json").read_bytes()
    recipe = json.loads(recipe_bytes)
    require(recipe["schema"] == 1 and recipe["profile"] == {"workers": 2, "tt_bits": 18},
            "only the frozen two-worker TT18 recipe is supported")
    require(recipe["compiler"] == ENCODED and recipe["argv_representation"] == "split",
            "fixed compiler recipe changed")
    require(recipe["compression"] == {"codec": "xz", "preset": 9, "extreme": True,
                                       "lc": 2, "lp": 0, "pb": 0, "check": "CRC64"},
            "fixed compression recipe changed")
    inputs = {name: (HERE / name).read_bytes()
              for name in ("campaign.py", "spelling.json", "control.c.in", "kernel.c.in", "emit.c.in", "transform.py")}
    require(sha(inputs["control.c.in"]) == recipe["control"]["readable_sha256"],
            "committed readable control changed")
    for name, metadata in recipe["helpers"].items():
        data = (ROOT / metadata["path"]).read_bytes()
        require(sha(data) == metadata["sha256"], "pinned helper changed: " + name)
        require(name not in inputs, "helper filename collision")
        inputs[name] = data
    if reference_wrapper is not None:
        inputs["reference-wrapper"] = reference_wrapper.read_bytes()
        require(sha(inputs["reference-wrapper"]) == recipe["control"]["whole_sha256"],
                "declared historical wrapper changed")
    output.mkdir(parents=True)
    frozen = output / "frozen"
    frozen.mkdir()
    for name, data in inputs.items():
        (frozen / name).write_bytes(data)
    report = {"schema": 1, "passed": False, "workers": 2, "tt_bits": 18,
              "scope": "one fixed kernel source prototype; no runtime, strength, 4K acceptance or canonical adoption claim",
              "policy": None, "input_sha256": {name: sha(data) for name, data in inputs.items()},
              "helper_bindings": recipe["helpers"], "forms": [], "engines": []}
    save(output / "results.json", report)
    save(output / "provenance.json", {"input_sha256": report["input_sha256"],
                                      "historical_recipe_provenance": recipe["provenance"],
                                      "reference_wrapper": str(reference_wrapper) if reference_wrapper else None,
                                      "reference_equality_basis": "actual bytes and SHA" if reference_wrapper else "pinned SHA-256"})
    try:
        transform = module("kernel_frozen_transform", frozen / "transform.py")
        specialize = module("kernel_frozen_specialize", frozen / "specialize.py")
        minifier = module("kernel_frozen_minifier", frozen / "minify.py")
        stitch = module("kernel_frozen_stitch", frozen / "stitch.py")
        lexer = module("kernel_frozen_lexer", frozen / "rename_c.py")
        producer = module("kernel_frozen_producer", frozen / "pack_stream.py")
        expression = module("kernel_frozen_expression", frozen / "encoding_campaign.py")
        readable = inputs["control.c.in"]
        changed, policy = transform.transform(readable)
        require(isinstance(changed, bytes) and changed != readable, "kernel transformation must return changed C bytes")
        report["policy"] = policy
        report["compiler"] = subprocess.check_output(["cc", "--version"], text=True).splitlines()[0]
        report["glibc"] = subprocess.check_output(["getconf", "GNU_LIBC_VERSION"], text=True).strip()
        for name, combined in (("baseline", readable), ("kernel", changed)):
            directory = output / name
            directory.mkdir()
            (directory / "combined.c").write_bytes(combined)
            raw_native, raw_gate = compile_twice(combined, SHIPPING, directory / "original")
            active, observations = specialize.specialize_c(
                {"main.c": combined}, directory / "preprocess", SHIPPING, os.environ.copy())
            compact = minifier.compact_source(active["main.c"], "c")
            (directory / "specialized.c").write_bytes(active["main.c"])
            (directory / "compact.c").write_bytes(compact)
            compact_native, compact_gate = compile_twice(compact, SHIPPING, directory / "compact")
            require(compact_native == raw_native, "specialization/compaction changed full native bytes: " + name)
            if name == "baseline":
                stripped, counters = stitch.strip_dev_counters(compact)
                counters["recipe"] = "frozen-baseline-eight-call-strip"
            else:
                stripped, counters = strip_kernel_counters(compact, lexer)
            (directory / "counter-stripped.c").write_bytes(stripped)
            stripped_native, counter_gate = compile_twice(stripped, SHIPPING, directory / "counter-stripped")
            require(stripped_native == raw_native, "counter removal changed full native bytes: " + name)
            source, spellings = fixed_spellings(stripped, recipe, lexer, name == "kernel")
            (directory / "main.c").write_bytes(source)
            encoded_native, encoded_gate = compile_twice(source, ENCODED, directory / "encoded")
            require(encoded_native == raw_native, "fixed spelling/resource/compiler recipe changed full native bytes: " + name)
            (directory / "x").write_bytes(encoded_native)
            (directory / "x").chmod(0o755)
            whole, script, artifact = package(source, recipe, producer, expression)
            repeated, repeated_script, repeated_artifact = package(source, recipe, producer, expression)
            require((whole, script, artifact) == (repeated, repeated_script, repeated_artifact),
                    "independent complete source-wrapper generation differs: " + name)
            if name == "baseline":
                expected = recipe["control"]
                require(len(source) == expected["encoded_source_bytes"] and sha(source) == expected["encoded_source_sha256"],
                        "historical baseline encoded C did not reproduce")
                require(len(encoded_native) == expected["native_bytes"] and sha(encoded_native) == expected["native_sha256"],
                        "historical baseline native image did not reproduce")
                require(sha(script) == expected["bootstrap_sha256"], "historical baseline bootstrap did not reproduce")
                require(len(whole) == expected["whole_bytes"] and sha(whole) == expected["whole_sha256"],
                        "historical 5283-byte complete wrapper did not reproduce")
                if reference_wrapper is not None:
                    require(whole == inputs["reference-wrapper"], "actual historical wrapper bytes differ")
            (directory / "wrapper").write_bytes(whole)
            (directory / "wrapper").chmod(0o755)
            (directory / "bootstrap.py").write_bytes(script)
            dev_native, dev_gate = compile_twice(combined, DEVELOPMENT, directory / "dev")
            artifact.update(path=str(directory / "wrapper"), reproduced=True,
                            under_4096_bytes=len(whole) <= 4096, rules_eligibility="unproven")
            row = {"id": name, "readable_sha256": sha(combined), "readable_bytes": len(combined),
                   "shipping_source_bytes": len(stripped), "source_bytes": len(source), "source_sha256": sha(source),
                   "native_bytes": len(encoded_native), "native_sha256": sha(encoded_native),
                   "whole_bytes": len(whole), "whole_sha256": sha(whole), "artifact": artifact,
                   "command": ENCODED, "preprocessor": observations, "counter_recipe": counters,
                   "fixed_spellings": spellings, "native_reproduced": True, "whole_reproduced": True,
                   "gates": {"original": raw_gate, "compact": compact_gate,
                             "counter-stripped": counter_gate, "encoded": encoded_gate, "dev": dev_gate},
                   "wrapper": str(directory / "wrapper"), "dev": str(directory / "dev/x")}
            report["forms"].append(row)
            for variant, profile, path, image in (("dev", "dev", directory / "dev/x", dev_native),
                                                  ("native", "shipping", directory / "x", encoded_native),
                                                  ("selected", "shipping", directory / "wrapper", whole)):
                spec = {"id": name + "-" + variant, "profile": profile,
                        "command": [str(path)], "cwd": str(path.parent), "workers": 2,
                        "startup_threads": 3, "expected_program_sha256": sha(image)}
                if variant == "selected":
                    spec["startup_timeout"] = 60
                report["engines"].append(spec)
            save(output / "results.json", report)
            save(output / "validation-manifest.json", {"engines": report["engines"]})
            print(json.dumps({key: row[key] for key in ("id", "source_bytes", "native_bytes", "whole_bytes", "whole_sha256")}), flush=True)
        report["passed"] = True
    except Exception as error:
        report["error"] = type(error).__name__ + ": " + str(error)
        save(output / "results.json", report)
        raise
    save(output / "results.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--reference-wrapper", type=Path,
                        help="optional original 5283-byte wrapper; pinned SHA and actual bytes must match")
    args = parser.parse_args()
    if not args.out.is_absolute():
        parser.error("--out must be absolute")
    if args.reference_wrapper is not None and (not args.reference_wrapper.is_absolute() or not args.reference_wrapper.is_file()):
        parser.error("--reference-wrapper must be an absolute existing file")
    produce(args.out, args.reference_wrapper)


if __name__ == "__main__":
    main()
