#!/usr/bin/env python3
"""Compile each fixed B/C/E candidate once and read physical ELF differences.

No baseline is recompiled; no native program or package is executed. This
reports observations without admitting a metadata exception in advance.
"""

import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

PREPARE_SHA = "556bdff95f1e208141cb214e5866794beff695685ac1c05d8d6998d1adc29b9e"
BASELINES = {
    "B": ("/home/stemxstudio/rove4k-tiny-b-attacker-first-ray-control-20261020/control-cost/native/x", 26496,
          "5a315a66f86ff81f9b0feb679b25f919c5aaf63bb9db2d157040a5b7ce6bbb4b"),
    "C": ("/home/stemxstudio/rove4k-tiny-storage-ce-current-native-20261020/control-C/native/x", 26424,
          "cc67f03a58f350a1bd0ab1f07e774c13cf8f6b628b469107834da6f505f7cf00"),
    "E": ("/home/stemxstudio/rove4k-tiny-storage-ce-current-native-20261020/control-E/native/x", 26408,
          "5429f2d80521f775bac6802ec4940e8e0ff1b344464ed8e9a0629ba6650eb675"),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def identity(data):
    return {"bytes": len(data), "sha256": sha(data)}


def elf(data):
    if data[:7] != b"\x7fELF\x02\x01\x01":
        raise ValueError("ELF64 little-endian version1 required")
    header = dict(zip(("ident", "type", "machine", "version", "entry", "phoff", "shoff", "flags",
                       "ehsize", "phentsize", "phnum", "shentsize", "shnum", "shstrndx"),
                      struct.unpack_from("<16sHHIQQQIHHHHHH", data)))
    header["ident"] = header["ident"].hex()
    if (header["machine"] != 62 or header["ehsize"] != 64 or header["phentsize"] != 56
            or header["shentsize"] != 64 or header["shnum"] == 0):
        raise ValueError("unsupported fixed x86-64 ELF layout")
    programs = [dict(zip(("type", "flags", "offset", "vaddr", "paddr", "filesz", "memsz", "align"),
                         struct.unpack_from("<IIQQQQQQ", data, header["phoff"] + index * 56)))
                for index in range(header["phnum"])]
    sections = [dict(zip(("name_index", "type", "flags", "addr", "offset", "size", "link", "info", "align", "entsize"),
                         struct.unpack_from("<IIQQQQIIQQ", data, header["shoff"] + index * 64)))
                for index in range(header["shnum"])]
    names = sections[header["shstrndx"]]
    strings = data[names["offset"]:names["offset"] + names["size"]]
    for section in sections:
        start = section["name_index"]
        section["name"] = strings[start:strings.index(b"\0", start)].decode("ascii")
        raw = b"" if section["type"] == 8 else data[section["offset"]:section["offset"] + section["size"]]
        if section["type"] != 8 and len(raw) != section["size"]:
            raise ValueError("ELF section outside file")
        section["file_data"] = identity(raw)
    return {"header": header, "programs": programs, "sections": sections}


def region(parsed, offset):
    header = parsed["header"]
    if offset < header["ehsize"]:
        return "ELF header"
    if header["phoff"] <= offset < header["phoff"] + header["phnum"] * header["phentsize"]:
        return "program-header table"
    if header["shoff"] <= offset < header["shoff"] + header["shnum"] * header["shentsize"]:
        return "section-header table"
    for section in parsed["sections"]:
        if section["type"] != 8 and section["offset"] <= offset < section["offset"] + section["size"]:
            return section["name"] or "null section"
    return "file gap/padding"


def loaded(parsed, offset):
    return any(p["type"] == 1 and p["offset"] <= offset < p["offset"] + p["filesz"] for p in parsed["programs"])


def compare(before, after):
    old, new = elf(before), elf(after)
    old_sections = {s["name"]: s for s in old["sections"]}
    new_sections = {s["name"]: s for s in new["sections"]}
    if len(old_sections) != len(old["sections"]) or len(new_sections) != len(new["sections"]):
        raise ValueError("duplicate ELF section names")
    sections = []
    for name in sorted(set(old_sections) | set(new_sections)):
        a, b = old_sections.get(name), new_sections.get(name)
        sections.append({"name": name, "before": a, "after": b,
                         "equal": a == b, "allocated": bool((a or b)["flags"] & 2)})
    runs, position, changed = [], 0, 0
    while position < max(len(before), len(after)):
        if position < min(len(before), len(after)) and before[position] == after[position]:
            position += 1
            continue
        start = position
        label = (region(old, position) if position < len(before) else "past EOF",
                 region(new, position) if position < len(after) else "past EOF",
                 loaded(old, position), loaded(new, position))
        while position < max(len(before), len(after)):
            if position < min(len(before), len(after)) and before[position] == after[position]:
                break
            current = (region(old, position) if position < len(before) else "past EOF",
                       region(new, position) if position < len(after) else "past EOF",
                       loaded(old, position), loaded(new, position))
            if current != label:
                break
            position += 1
        a, b = before[start:position], after[start:position]
        runs.append({"start": start, "end": position, "before_region": label[0], "after_region": label[1],
                     "before_PT_LOAD": label[2], "after_PT_LOAD": label[3],
                     "before": a.hex() if len(a) <= 64 else identity(a),
                     "after": b.hex() if len(b) <= 64 else identity(b)})
        changed += position - start
    allocated = [s for s in sections if s["allocated"] and not s["equal"]]
    linkage = [s for s in sections if s["name"] in (".dynsym", ".dynstr", ".dynamic")
               or (s["before"] or s["after"])["type"] in (4, 9)]
    return {"baseline": identity(before), "candidate": identity(after), "full_native_equal": before == after,
        "ELF_header_differences": {key: [old["header"][key], new["header"][key]]
                                   for key in old["header"] if old["header"][key] != new["header"][key]},
        "program_headers_equal": old["programs"] == new["programs"],
        "baseline_program_headers": old["programs"], "candidate_program_headers": new["programs"],
        "all_section_comparisons": sections, "allocated_different_sections": [s["name"] for s in allocated],
        "dynamic_symbols_strings_and_relocations_equal": all(s["equal"] for s in linkage),
        "all_file_byte_difference_ranges": runs, "positional_different_bytes": changed,
        "PT_LOAD_different_bytes": sum(r["end"] - r["start"] for r in runs if r["before_PT_LOAD"] or r["after_PT_LOAD"]),
        "no_difference_range_masked_or_preaccepted": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    prepared, out = args.prepared.resolve(), args.out.resolve()
    raw = (prepared / "prepare.json").read_bytes()
    if sha(raw) != PREPARE_SHA:
        raise ValueError("literal fixed source proposal receipt differs")
    proposal = json.loads(raw)
    if not proposal["complete"] or not args.out.is_absolute() or out.exists():
        raise ValueError("complete exact proposal and new absolute output required")
    if any((p / ".git").exists() for p in (out, *out.parents)):
        raise ValueError("external output required")
    out.mkdir(parents=True)
    report = {"complete": False, "scope": __doc__, "prepared_receipt_sha256": sha(raw), "families": {},
              "candidate_native_compiles": 0, "control_compiles": 0, "codec_calls": 0, "engine_executions": 0,
              "metadata_class_admitted": False}
    def save():
        (out / "native.json").write_bytes((json.dumps(report, indent=2) + "\n").encode())
    save()
    try:
        for family, (path, size, pin) in BASELINES.items():
            baseline = Path(path).read_bytes()
            if len(baseline) != size or sha(baseline) != pin:
                raise ValueError("literal qualified baseline native differs: " + family)
            source = (prepared / family / "candidate.c").read_bytes()
            if identity(source) != proposal["families"][family]["after"]:
                raise ValueError("literal fixed candidate source differs")
            recipe_path = prepared / "inputs/engines/compact" / ("tiny-entry-" + family.lower()) / "recipe.json"
            recipe_raw = recipe_path.read_bytes()
            relative = "engines/compact/tiny-entry-" + family.lower() + "/recipe.json"
            if identity(recipe_raw) != proposal["inputs"][relative]:
                raise ValueError("fixed source recipe changed")
            recipe = json.loads(recipe_raw)
            if recipe["expected"]["native_bytes"] != size or recipe["expected"]["native_sha256"] != pin:
                raise ValueError("baseline no longer matches fixed recipe")
            directory = out / family
            directory.mkdir()
            result = subprocess.run(recipe["compiler"], input=source, cwd=directory,
                                    capture_output=True, timeout=90)
            report["candidate_native_compiles"] += 1
            (directory / "compiler.stdout").write_bytes(result.stdout)
            (directory / "compiler.stderr").write_bytes(result.stderr)
            if result.returncode:
                raise ValueError("candidate native compile failed: " + family)
            candidate = (directory / "x").read_bytes()
            for label, target in (("baseline", path), ("candidate", str(directory / "x"))):
                readback = subprocess.run(["readelf", "-W", "-h", "-l", "-S", "-r", "-s", "-d", "-n", target],
                                          capture_output=True, timeout=15)
                (directory / (label + "-readelf.txt")).write_bytes(readback.stdout)
                (directory / (label + "-readelf.stderr")).write_bytes(readback.stderr)
                if readback.returncode:
                    raise ValueError("ELF readback failed")
            observation = compare(baseline, candidate)
            (directory / "comparison.json").write_bytes((json.dumps(observation, indent=2) + "\n").encode())
            report["families"][family] = {"baseline_path": path, "candidate_path": str(directory / "x"),
                "command": recipe["compiler"], "source": identity(source),
                "baseline": identity(baseline), "candidate": identity(candidate),
                "full_native_equal": observation["full_native_equal"],
                "program_headers_equal": observation["program_headers_equal"],
                "ELF_header_differences": observation["ELF_header_differences"],
                "allocated_different_sections": observation["allocated_different_sections"],
                "dynamic_symbols_strings_and_relocations_equal": observation["dynamic_symbols_strings_and_relocations_equal"],
                "PT_LOAD_different_bytes": observation["PT_LOAD_different_bytes"]}
            save()
            print(json.dumps({"family": family, **report["families"][family]}), flush=True)
        report["complete"] = True
        save()
    except Exception as error:
        report["error"] = repr(error)
        save()
        raise


if __name__ == "__main__":
    main()
