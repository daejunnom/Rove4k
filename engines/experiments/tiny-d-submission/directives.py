#!/usr/bin/env python3
"""Standalone, closed-cohort D source-JIT system-prefix experiment.

The compiler retains own macros with -fdirectives-only. One exact prefix is
replaced before the first own prototype; its TINY_H definition and original
four includes are restored. Every byte after that prototype is protected before
the existing token minifier. Only complete linked AND stripped-native equality
admits a candidate to actual whole-package costing. No engine is executed.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import re
import sys

sys.dont_write_bytecode = True
ANCHOR = b"void *memcpy(void *,const void *,size_t);\n"
INCLUDES = b"#include <stdint.h>\n#include <stddef.h>\n#include <stdatomic.h>\n#include <limits.h>\n"
PREPARED = {
    "board.c": "ecd9d567a1f6c5ee185012a70915ab63c741bbf68b7a294d1604334c59db4e62",
    "image.ld": "38756c865914b52432572864446fcc58b791dfb508af8a33156d5c190c01044b",
    "runtime.c": "a0230b6a155b54366bc36eff65d3d850d8f6ab3bae9ef83fd64097f9b6ac4955",
    "search.c": "2cb4632e29635d114680f8b21c21137545143f3c033546d3f8ac7c4307163194",
    "start.S": "4a6021518cfe67bee9e42806b596f4f0837e3e93487b1acfa115158ea019ba5b",
    "tiny.h": "f918331fbc2bc140362ebe883fca7d897c97b3226bb10e8ce9918bc1eb233ce9",
}
EXPECTED_LINKED = "e5d54f2f9b918316efcb171631cf4745bf97f7dfacfb55faff6a5ee9aa71128f"
EXPECTED_NATIVE = "e06bce0d9998fa14cb85f135d3c5f54f9972d3dea533cede1f44ed28618e3337"


def pin(data):
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def splice(data, edits):
    """Disjoint byte roles with a full inverse and all complement pins."""
    parts, rows, gaps, at, target = [], [], [], 0, 0
    for begin, end, after in sorted(edits):
        if not at <= begin < end <= len(data):
            raise ValueError("invalid/overlapping directives projection role")
        gap, before = data[at:begin], data[begin:end]
        parts.extend((gap, after))
        gaps.append(pin(gap))
        target += len(gap)
        rows.append(dict(begin=begin, target=target, before=before.decode(), after=after.decode()))
        target += len(after)
        at = end
    parts.append(data[at:])
    gaps.append(pin(data[at:]))
    output = b"".join(parts)
    proof = dict(input=pin(data), output=pin(output), edits=rows, protected_gaps=gaps)
    if restore(output, proof) != data:
        raise ValueError("directives projection inverse differs")
    return output, proof


def restore(output, proof):
    if pin(output) != proof["output"]:
        raise ValueError("directives projection output differs")
    parts, gaps, at, source_at = [], [], 0, 0
    for row in proof["edits"]:
        begin, before, after = row["target"], row["before"].encode(), row["after"].encode()
        if begin < at or output[begin:begin + len(after)] != after:
            raise ValueError("directives projection role differs")
        gap = output[at:begin]
        if source_at + len(gap) != row["begin"]:
            raise ValueError("directives original offset differs")
        parts.extend((gap, before))
        gaps.append(pin(gap))
        source_at += len(gap) + len(before)
        at = begin + len(after)
    parts.append(output[at:])
    gaps.append(pin(output[at:]))
    original = b"".join(parts)
    if pin(original) != proof["input"] or gaps != proof["protected_gaps"]:
        raise ValueError("directives protected complement differs")
    return original


def project(data, tiny_header):
    """Replace only the compiler prefix; retain its entire own-source suffix."""
    if pin(tiny_header)["sha256"] != PREPARED["tiny.h"] or tiny_header.count(ANCHOR) != 1:
        raise ValueError("exact own header/first-prototype cohort required")
    if data.count(ANCHOR) != 1:
        raise ValueError("unique exact first own prototype required")
    boundary = data.index(ANCHOR)
    prefix, suffix = data[:boundary], data[boundary:]
    guards = re.findall(rb"(?m)^#define TINY_H[ \t]*\n", prefix)
    if len(guards) != 1:
        raise ValueError("exactly one consumed own TINY_H guard required")
    header_prefix = tiny_header[:tiny_header.index(ANCHOR)]
    if header_prefix.count(INCLUDES) != 1:
        raise ValueError("original four-system-include boundary differs")
    inserted = guards[0] + INCLUDES
    output, inverse = splice(data, [(0, boundary, inserted)])
    if output[len(inserted):] != suffix:
        raise ValueError("own suffix changed")
    return output, dict(kind="D-directives-system-prefix-and-consumed-header-preamble-v1",
                        projection=inverse, removed_prefix=pin(prefix), protected_suffix=pin(suffix),
                        inserted_prefix=inserted.decode(), own_header_prefix=pin(header_prefix),
                        own_TINY_H_definition_preserved=True, all_suffix_bytes_preserved=True)


def alpha(files, removed_prefix, lexical):
    """One lexical batch; protected names excluded on BOTH rename sides."""
    reserved = set(lexical._KEYWORDS) | {"main", "spawn", "memcpy", "memset", "memcmp", "abort",
                                       "L", "u", "U", "u8", "R", "LR", "uR", "UR", "u8R"}
    reserved.update(lexical._ANY_WORD.findall(removed_prefix.decode()))
    counts, spans, used = Counter(), {}, set(reserved)
    for name, data in files.items():
        text = data.decode()
        used.update(lexical._ANY_WORD.findall(text))
        if not name.endswith(".c"):
            reserved.update(lexical._ANY_WORD.findall(text))
            continue
        spans[name] = list(lexical._identifier_spans(text))
        at = 0
        for begin, end, token in spans[name]:
            # Lexer-opaque gaps include every directive, quoted literal and
            # asm string: their spellings must not be renamed at C use sites.
            reserved.update(lexical._ANY_WORD.findall(text[at:begin]))
            counts[token] += 1
            at = end
        reserved.update(lexical._ANY_WORD.findall(text[at:]))
    used.update(reserved)
    names, renames = lexical._short_names(), {}
    for old in sorted((n for n in counts if len(n) > 1 and n not in reserved and
                       lexical._ASCII_IDENTIFIER.fullmatch(n)),
                      key=lambda n: (-(len(n) - 1) * counts[n], n)):
        new = next(n for n in names if n not in used)
        used.add(new)
        if len(new) < len(old):
            renames[old] = new
    output, proofs = dict(files), {}
    for name, positions in spans.items():
        text = files[name].decode()
        edits = [(len(text[:a].encode()), len(text[:b].encode()), renames[token].encode())
                 for a, b, token in positions if token in renames]
        output[name], proofs[name] = splice(files[name], edits)
    if any(old in reserved or new in reserved for old, new in renames.items()):
        raise ValueError("protected dictionary name renamed")
    return output, dict(kind="single-batch-alpha-protected-system-directive-literal-S-ld-v1",
                        reserved=sorted(reserved), renames=renames, projections=proofs,
                        input={n: pin(d) for n, d in files.items()},
                        output={n: pin(d) for n, d in output.items()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out, baseline = args.out.resolve(), args.baseline.resolve()
    if (sys.platform != "linux" or platform.machine() != "x86_64" or not args.out.is_absolute()
            or not args.baseline.is_absolute() or out.exists()
            or any((p / ".git").exists() for p in (out, *out.parents))):
        parser.error("Linux x86-64, explicit baseline, new absolute output outside Git required")
    build_data = (baseline / "build.json").read_bytes()
    build = json.loads(build_data)
    if (build["complete"] is not True or build["storage"] != "prefix" or build["source_reduced"]
            or build["native"]["sha256"] != EXPECTED_NATIVE
            or build["source_jit_native"]["sha256"] != EXPECTED_LINKED):
        raise ValueError("exact complete v8 eq+prefix baseline required")
    out.mkdir()
    (out / "baseline-build.json").write_bytes(build_data)
    inputs = {"directives.py": Path(__file__).read_bytes().replace(b"\r\n", b"\n")}
    for name, logical in {
        "minify.py": "engines/scripts/minify.py", "lexical.py": "engines/scripts/rename_c.py",
        "packaging.py": "engines/experiments/tiny-d-submission/packaging.py",
        "packer.py": "engines/compact/tiny-entry-d/packer.py",
        "host.py": "engines/experiments/tcec-scope/build.py",
    }.items():
        data = (baseline / "inputs" / logical).read_bytes()
        if pin(data) != build["inputs"][logical]:
            raise ValueError("frozen consumed producer differs: " + logical)
        inputs[name] = data
    (out / "inputs").mkdir()
    for name, data in inputs.items():
        (out / "inputs" / name).write_bytes(data)
    (out / "prepared").mkdir()
    for name, expected in PREPARED.items():
        data = (baseline / "generated-readable" / name).read_bytes()
        if pin(data)["sha256"] != expected or pin(data) != build["proof"]["storage"]["output"][name]:
            raise ValueError("prepared eq+prefix cohort differs: " + name)
        (out / "prepared" / name).write_bytes(data)
    (out / "unchanged").mkdir()
    for name, expected in build["shipping_inputs"].items():
        if name not in ("main.c", "start.S", "image.ld"):
            raise ValueError("baseline source-JIT unit boundary differs")
        data = (baseline / "shipping-inputs" / name).read_bytes()
        if pin(data) != expected:
            raise ValueError("baseline shipping bytes differ")
        (out / "unchanged" / name).write_bytes(data)
    frozen = load("D_directives_frozen_execution", out / "inputs/directives.py")
    frozen.run(out, build, inputs)


def run(out, build, inputs):
    hostmod = load("D_directives_owner", out / "inputs/host.py")
    minifier = load("D_directives_minify", out / "inputs/minify.py")
    lexical = load("D_directives_lexical", out / "inputs/lexical.py")
    package = load("D_directives_package", out / "inputs/packaging.py")
    packer = load("D_directives_packer", out / "inputs/packer.py")
    hostmod.LIMITS = {**hostmod.LIMITS, "aggregate_wall": 180, "per_command_wall": 40,
                      "parent_CPU": 90, "parent_CPU_hard": 100, "child_CPU": 30}
    report = dict(kind="D-v8-directives-system-prefix-source-JIT-v1", complete=False, commands=[],
                  inputs={n: pin(d) for n, d in inputs.items()}, prepared=PREPARED,
                  baseline_build=pin((out / "baseline-build.json").read_bytes()),
                  flags=build["flags"], units=build["units"], candidates=[],
                  compiler_flags_unchanged=True, engine_executed=False,
                  target_TT_allocated=False, toolchain_system_headers_required=True)
    def save():
        (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    save()
    host = hostmod.Host(out, report, save)
    try:
        flags, units = list(build["flags"]), list(build["units"])
        prepared = out / "prepared"
        report["compiler"] = host.run(["cc", "--version"], cwd=out, kind="compiler-version").decode().splitlines()[0]
        driver = b''.join(b'#include "' + n.encode() + b'"\n' for n in ("board.c", "search.c", "runtime.c"))
        expanded = host.run(["cc", "-E", "-fdirectives-only", "-P", *flags, "-I", str(prepared), "-x", "c", "-"],
                            cwd=out, kind="preprocess-directives", data=driver)
        (out / "directives-full.c").write_bytes(expanded)
        projected, proof = project(expanded, (prepared / "tiny.h").read_bytes())
        report["prefix_projection"] = proof
        (out / "directives-projected.c").write_bytes(projected)
        compacted = minifier.compact_source(projected, "c")
        assembly = host.run(["cc", "-E", "-P", "-x", "assembler-with-cpp", str(prepared / "start.S")],
                            cwd=out, kind="preprocess-entry")
        unchanged = {n: (out / "unchanged" / n).read_bytes() for n in build["shipping_inputs"]}
        if assembly != unchanged["start.S"] or (prepared / "image.ld").read_bytes() != unchanged["image.ld"]:
            raise ValueError("S/linker boundary differs")
        candidate = dict(unchanged, **{"main.c": compacted})
        removed = proof["projection"]["edits"][0]["before"].encode()
        renamed, alpha_proof = alpha(candidate, removed, lexical)
        report["alpha"] = alpha_proof
        report["minification"] = dict(input=pin(projected), output=pin(compacted),
                                      original_suffix_preserved_before_token_compaction=True)
        work = out / "compile-work"
        work.mkdir()
        source_baseline = next(c for c in build["candidates"] if c["representation"] == "source-jit")
        for name, files in (("unchanged", unchanged), ("directives", candidate), ("directives-alpha", renamed)):
            directory = out / ("candidate-" + name)
            directory.mkdir()
            for n, data in files.items():
                (directory / n).write_bytes(data)
                (work / n).write_bytes(data)
            binary = work / "x"
            host.run(["cc", *flags, *[str(work / n) for n in units], "-Wl,-T," + str(work / "image.ld"), "-o", str(binary)],
                     cwd=work, kind="compile-" + name)
            linked = binary.read_bytes()
            native = packer.strip_native(linked)
            (directory / "linked").write_bytes(linked)
            (directory / "native").write_bytes(native)
            equal = pin(linked) == {k: build["source_jit_native"][k] for k in ("bytes", "sha256")} and pin(native) == {
                k: build["native"][k] for k in ("bytes", "sha256")}
            row = dict(name=name, linked=pin(linked), native=pin(native), native_identity=equal,
                       source={n: pin(d) for n, d in files.items()}, status="admitted" if equal else "rejected-native-differs")
            if name == "unchanged" and not equal:
                raise ValueError("fresh baseline linked/native identity differs")
            if equal:
                whole, metadata = package.package_source(files, flags, units)
                (directory / "whole").write_bytes(whole)
                row.update(whole=pin(whole), package=metadata)
                if name == "unchanged" and pin(whole) != {k: source_baseline[k] for k in ("bytes", "sha256")}:
                    raise ValueError("unchanged whole package differs")
            report["candidates"].append(row)
            save()
        admitted = [c for c in report["candidates"] if c["native_identity"]]
        winner = min(admitted, key=lambda c: c["whole"]["bytes"])
        report.update(selected=winner["name"], selected_whole=winner["whole"],
                      whole_saving=admitted[0]["whole"]["bytes"] - winner["whole"]["bytes"])
    except BaseException as error:
        report["complete"] = False
        report["failure"] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        try:
            host.close()
        except BaseException as error:
            report["complete"] = False
            report["cleanup_failure"] = dict(type=type(error).__name__, message=str(error))
            raise
        finally:
            cleanup = report.get("host_cleanup", {})
            if cleanup.get("errors") or cleanup.get("unsettled_commands"):
                report["complete"] = False
            save()
    if cleanup.get("errors") or cleanup.get("unsettled_commands"):
        raise ValueError("directives ownership cleanup incomplete")
    report["complete"] = True
    save()
    print(json.dumps(dict(complete=True, selected=report["selected"], whole=report["selected_whole"],
                          whole_saving=report["whole_saving"], engine_executed=False)), flush=True)


if __name__ == "__main__":
    main()
