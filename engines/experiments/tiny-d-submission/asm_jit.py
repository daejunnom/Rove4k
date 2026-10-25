#!/usr/bin/env python3
"""Fresh canonical-C LTO machine-assembly JIT experiment, not C-source JIT.

Historical images are hash references only. Actual LTRANS .s units and order
come from fresh gold-matching C links. Reassembly uses its explicit ASM recipe;
every admitted candidate matches both linked/native images before 2x costing.
No engine or target allocation is started; Jammy assembler admission is separate.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import lzma
from pathlib import Path
import platform
import re
import shlex
import shutil
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
LINKED_SHA = "e5d54f2f9b918316efcb171631cf4745bf97f7dfacfb55faff6a5ee9aa71128f"
NATIVE_SHA = "e06bce0d9998fa14cb85f135d3c5f54f9972d3dea533cede1f44ed28618e3337"
ASM_FLAGS = ["-m64", "-nostdlib", "-static", "-no-pie", "-Wl,--gc-sections,--build-id=none,-s,-z,noexecstack"]
WORD = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")
REG = re.compile(r"(?:r(?:[89]|1[0-5])(?:b|w|d)?|r[abcd]x|r[sd]i|r[bs]p|rip|e[abcd]x|e[sd]i|e[bs]p|[abcd][lhx]|[sd]il|[bs]pl|[abcd]x|[sb]p|[sd]i|[cdefgs]s|[xyz]mm[0-9]+|mm[0-7])\Z")


def pin(data):
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def asm_tokens(text):
    """ASM identifiers outside double-quoted data and # comments, with offsets."""
    pos = 0
    while pos < len(text):
        if text[pos] == '"':
            end = pos + 1
            while end < len(text):
                if text[end] == "\\":
                    end += 2
                elif text[end] == '"':
                    end += 1
                    break
                else:
                    end += 1
            else:
                raise ValueError("unterminated assembly string")
            pos = end
        elif text[pos] == "#":
            end = text.find("\n", pos)
            pos = len(text) if end < 0 else end
        elif text[pos] == "'":
            raise ValueError("unsupported unquoted GAS character constant")
        else:
            match = WORD.match(text, pos)
            if match:
                yield pos, match.end(), match.group()
                pos = match.end()
            else:
                pos += 1


def clean_asm(data, projection, *, metadata=False):
    """Keep all instruction/data/layout directives; remove explicit metadata only."""
    text, edits, offset = data.decode(), [], 0
    for line in text.splitlines(keepends=True):
        quote, escape, comment = False, False, len(line)
        for i, char in enumerate(line):
            if escape:
                escape = False
            elif quote and char == "\\":
                escape = True
            elif char == '"':
                quote = not quote
            elif char == "#" and not quote:
                comment = i
                break
        if quote:
            raise ValueError("multiline assembly string is outside this recipe")
        code = line[:comment].strip()
        if metadata and re.match(r"\.(?:file|ident)(?:\s|$)", code):
            code = ""
        compact, quoted, escaped = [], False, False
        for char in code:
            if quoted:
                compact.append(char)
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    quoted = False
            elif char == '"':
                compact.append(char)
                quoted = True
            elif char in " \t":
                if not compact or compact[-1] != " ":
                    compact.append(" ")
            else:
                compact.append(char)
        code = "".join(compact)
        after = (code + "\n").encode() if code else b""
        before = line.encode()
        if after != before:
            edits.append((offset, offset + len(before), after))
        offset += len(before)
    return projection.splice(data, edits)


def alias_asm(files, predefines, projection, *, mnemonics=False, registers=False):
    used = set(WORD.findall(predefines.decode())) | {"L", "u", "U", "u8", "R"}
    occurrences, counts = {}, Counter()
    for name, data in files.items():
        text = data.decode()
        used.update(WORD.findall(text))
        if not name.endswith(".s"):
            continue
        if not text.isascii():
            raise ValueError("CPP ASM alias offsets require the declared ASCII source cohort")
        positions, line_start = [], 0
        for line in text.splitlines(keepends=True):
            stripped = line.lstrip()
            instruction = bool(stripped and not stripped.startswith(".") and not re.match(r"[A-Za-z_.$][A-Za-z_0-9.$]*:", stripped))
            first = True
            for a, b, token in asm_tokens(line):
                kind = None
                if registers and a and line[a - 1] == "%" and REG.fullmatch(token):
                    kind = "register"
                elif mnemonics and instruction and first:
                    kind = "mnemonic"
                if first and token not in ("rep", "repe", "repne", "lock"):
                    first = False
                if kind:
                    positions.append((line_start + a, line_start + b, (kind, token)))
                    counts[(kind, token)] += 1
            line_start += len(line)
        occurrences[name] = positions
    # Fresh CPP identifiers, including all labels/symbols/quoted words and S/ld.
    def names():
        alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for char in alphabet:
            yield char
        for a in alphabet:
            for b in alphabet + "0123456789":
                yield a + b
    fresh, aliases = names(), {}
    for key in sorted(counts, key=lambda k: (-(len(k[1]) - 1) * counts[k], k)):
        new = next(n for n in fresh if n not in used)
        used.add(new)
        declarations = sum(any(k == key for _, _, k in p) for p in occurrences.values())
        if (len(key[1]) - len(new)) * counts[key] > declarations * len(f"#define {new} {key[1]}\n"):
            aliases[key] = new
    result, proofs = {}, {}
    for name, data in files.items():
        if name not in occurrences:
            result[name] = data
            continue
        selected = {key for _, _, key in occurrences[name] if key in aliases}
        prefix = "".join(f"#define {aliases[k]} {k[1]}\n" for k in sorted(selected)).encode()
        edits = [(a, b, aliases[k].encode()) for a, b, k in occurrences[name] if k in aliases]
        body, proof = projection.splice(data, edits)
        output_name = name[:-2] + ".S"
        result[output_name] = prefix + body
        proofs[name] = dict(prefix=prefix.decode(), body=proof, output=pin(prefix + body))
        if projection.restore(body, proof) != data:
            raise ValueError("ASM aliases failed full inverse")
    return result, dict(aliases={k[0] + ":" + k[1]: v for k, v in aliases.items()}, files=proofs)


def local_labels(files, machine_names, predefines, projection):
    """Direct per-unit .L* renames, preserving GAS-local binding and literals."""
    pattern = re.compile(r"(?<![A-Za-z_0-9.])\.L[A-Za-z_0-9.$]+")
    used = set(WORD.findall(predefines.decode()))
    spans, definitions, external = {}, {}, set()
    for name, data in files.items():
        text = data.decode()
        used.update(WORD.findall(text))
        positions, pos = [], 0
        while pos < len(text):
            if text[pos] == '"':
                end = pos + 1
                while end < len(text):
                    if text[end] == "\\":
                        end += 2
                    elif text[end] == '"':
                        end += 1
                        break
                    else:
                        end += 1
                else:
                    raise ValueError("unterminated local-label literal")
                pos = end
            elif text[pos] == "#":
                end = text.find("\n", pos)
                pos = len(text) if end < 0 else end
            else:
                match = pattern.match(text, pos)
                if match:
                    positions.append((pos, match.end(), match.group()))
                    pos = match.end()
                else:
                    pos += 1
        spans[name] = positions
        definitions[name] = {token for _, end, token in positions if re.match(r"[ \t]*:", text[end:])}
        for line in text.splitlines():
            if re.match(r"\s*\.(?:global|globl|weak|extern|hidden|protected|symver)\b", line):
                external.update(pattern.findall(line))
        if name not in machine_names:
            external.update(token for _, _, token in positions)
    result, proofs = dict(files), {}
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for name in machine_names:
        text = files[name].decode()
        counts = Counter(token for _, _, token in spans[name])
        protected = set(external)
        for other in machine_names:
            if other != name:
                protected.update(token for _, _, token in spans[other] if token not in definitions[other])
        def names():
            for a in alphabet:
                yield ".L" + a
            for a in alphabet:
                for b in alphabet + "0123456789":
                    yield ".L" + a + b
        fresh, renames = names(), {}
        for old in sorted(definitions[name] - protected, key=lambda n: (-(len(n) - 2) * counts[n], n)):
            new = next(n for n in fresh if n[1:] not in used)
            used.add(new[1:])
            if len(new) <= len(old):
                renames[old] = new
        edits = [(a, b, renames[token].encode()) for a, b, token in spans[name] if token in renames]
        result[name], inverse = projection.splice(files[name], edits)
        proofs[name] = dict(renames=renames, protected=sorted(protected), projection=inverse)
        if projection.restore(result[name], inverse) != files[name]:
            raise ValueError("unit-local label inverse differs")
    return result, proofs


def link_order(directory, map_data, compiler_log):
    """LOAD order, not lexical filename order; only fresh compiler-owned objects."""
    order, machine, ignored = [], {}, []
    for line in map_data.decode().splitlines():
        if not line.startswith("LOAD "):
            continue
        path = Path(line[5:].strip()).resolve(strict=False)
        if path.parent != directory.resolve() or path.suffix != ".o":
            raise ValueError("unknown input in fresh compiler link map: " + str(path))
        if re.search(r"\.ltrans[0-9]+\.ltrans\.o$", path.name):
            source = path.with_suffix(".s")
            data = source.read_bytes()
            if b".gnu.lto_" in data:
                raise ValueError("LTO IR is not machine assembly")
            assembled, emitted = [], []
            for command_line in compiler_log.decode().splitlines():
                if not command_line.startswith(" "):
                    continue
                try:
                    command = shlex.split(command_line)
                except ValueError:
                    continue
                if not command or "-o" not in command or command.index("-o") + 1 >= len(command):
                    continue
                output = Path(command[command.index("-o") + 1]).resolve(strict=False)
                if Path(command[0]).name in ("as", "x86_64-linux-gnu-as") and output == path and str(source) in command:
                    assembled.append(command)
                if Path(command[0]).name == "lto1" and output == source:
                    emitted.append(command)
            if len(assembled) != 1 or len(emitted) != 1:
                raise ValueError("fresh LTRANS assembler/LTO emission command witness differs")
            name = f"a{len(machine)}.s"
            machine[name] = data
            order.append(dict(role="machine", unit=name, object=str(path), object_retained=path.exists(),
                              source=str(source), assembler_command=assembled[0], lto_emit_command=emitted[0], **pin(data)))
        elif path.name == "x-start.o":
            order.append(dict(role="entry", unit="e.S", object=str(path)))
        elif path.name == "x-main.o" and b".gnu.lto_" in path.read_bytes():
            ignored.append(dict(role="consumed-LTO-IR-object-not-reassembly-input", path=str(path), **pin(path.read_bytes())))
        else:
            raise ValueError("unrecognized fresh link-map object role: " + path.name)
    if not 1 <= len(machine) <= 4 or sum(r["role"] == "entry" for r in order) != 1 or len(ignored) != 1:
        raise ValueError("unsupported fresh LTRANS/entry/IR object geometry")
    return machine, order, ignored


def snapshot_inputs():
    """Freeze source preparation's complete recipe closure before execution."""
    source_inputs = load("D_asm_source_inputs", HERE / "source_inputs.py")
    recipe_data = (ROOT / source_inputs.RECIPE).read_bytes().replace(b"\r\n", b"\n")
    recipe = json.loads(recipe_data)
    names = source_inputs.source_names(recipe) + (
        source_inputs.SELF, "engines/compact/tiny-entry-d/packer.py",
        "engines/experiments/tcec-scope/build.py", *tuple("engines/experiments/tiny-d-submission/" + n for n in
            ("asm_jit.py", "storage.py", "build.py", "packaging.py", "directives.py")))
    frozen = {n: (ROOT / n).read_bytes().replace(b"\r\n", b"\n") for n in names}
    frozen[source_inputs.RECIPE] = recipe_data
    return frozen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if (sys.platform != "linux" or platform.machine() != "x86_64" or not args.out.is_absolute() or out.exists()
            or any((p / ".git").exists() for p in (out, *out.parents))):
        parser.error("new absolute output outside Git on Linux x86-64 required")
    frozen = snapshot_inputs()
    out.mkdir()
    for name, data in frozen.items():
        path = out / "inputs" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    executing = load("D_asm_jit_frozen", out / "inputs/engines/experiments/tiny-d-submission/asm_jit.py")
    executing.run(out, frozen)


def run(out, frozen):
    source = load("D_asm_source", HERE / "source.py")
    storage = load("D_asm_storage", HERE / "storage.py")
    builder = load("D_asm_builder", HERE / "build.py")
    projection = load("D_asm_projection", HERE / "directives.py")
    package = load("D_asm_package", HERE / "packaging.py")
    packer = load("D_asm_packer", source.CANONICAL / "packer.py")
    owner = load("D_asm_owner", ROOT / source.HOST)
    if pin(source.normalized(ROOT / source.HOST))["sha256"] != source.HOST_SHA:
        raise ValueError("bounded original owner differs")
    owner.LIMITS = {**owner.LIMITS, "aggregate_wall": 300, "per_command_wall": 60,
                    "parent_CPU": 180, "parent_CPU_hard": 200, "child_CPU": 45, "tool_output_bytes": 8 << 20}
    report = dict(kind="D-fresh-C-LTRANS-machine-ASM-JIT-v1", complete=False, commands=[],
                  inputs={n: pin(d) for n, d in frozen.items()}, generations=[], candidates=[], tools={}, dependencies=[],
                  engine_executed=False, target_TT_allocated=False, Jammy_assembler_proven=False,
                  source_format="fresh-canonical-C-LTO-machine-assembly+original-entry/linker", asm_flags=ASM_FLAGS)
    def save():
        (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    save()
    host = owner.Host(out, report, save)
    try:
        profile = source.production().resource_profile("test-p4")
        files, proof = source.prepare(profile)
        files, storage_proof = storage.transform(files, prefix=True, dense=False)
        if {n: pin(d)["sha256"] for n, d in files.items()} != projection.PREPARED:
            raise ValueError("fresh canonical P4 eq+prefix differs from gold source cohort")
        report.update(resource=profile.to_record(16), source=proof, storage=storage_proof)
        flags = builder.native_flags(profile)
        report["c_flags"] = flags
        prepared = out / "prepared"
        prepared.mkdir()
        for name, data in files.items():
            (prepared / name).write_bytes(data)
        work = out / "c-generation"
        work.mkdir()
        (work / "main.c").write_bytes(b'#include "board.c"\n#include "search.c"\n#include "runtime.c"\n')
        cc = Path(shutil.which("cc")).resolve(strict=True)
        for name, query in (("cc", None), ("as", "-print-prog-name=as"), ("ld", "-print-prog-name=ld"),
                            ("cc1", "-print-prog-name=cc1"), ("lto1", "-print-prog-name=lto1"),
                            ("lto-wrapper", "-print-prog-name=lto-wrapper"), ("collect2", "-print-prog-name=collect2"),
                            ("liblto_plugin", "-print-file-name=liblto_plugin.so")):
            text = str(cc) if query is None else host.run([str(cc), query], cwd=out, kind="locate-" + name).decode().strip()
            path = Path(text if Path(text).is_absolute() else shutil.which(text)).resolve(strict=True)
            data = path.read_bytes()
            target = out / "tool-snapshots" / name
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(data)
            report["tools"][name] = dict(path=str(path), **pin(data))
        report["compiler_version"] = host.run([str(cc), "--version"], cwd=out, kind="compiler-version").decode().splitlines()[0]
        report["assembler_version"] = host.run([report["tools"]["as"]["path"], "--version"], cwd=out, kind="assembler-version").decode().splitlines()[0]
        dependency_output = host.run([str(cc), "-M", *flags, "-I", str(prepared), str(work / "main.c")],
                                     cwd=out, kind="canonical-C-dependencies")
        _, separator, tail = dependency_output.decode().replace("\\\n", " ").partition(":")
        if not separator:
            raise ValueError("unknown fresh canonical dependency format")
        for token in dict.fromkeys(shlex.split(tail)):
            path = Path(token).resolve(strict=True)
            if path == work / "main.c":
                continue
            if path.parent == prepared:
                if path.name not in files or path.read_bytes() != files[path.name]:
                    raise ValueError("fresh prepared dependency differs")
                continue
            if (path.suffix != ".h" or not any(path.is_relative_to(p) for p in (Path("/usr/lib"), Path("/usr/include")))
                    or len(report["dependencies"]) >= 128):
                raise ValueError("unexpected/unbounded canonical system-header dependency")
            data = path.read_bytes()
            target = out / "header-snapshots" / path.relative_to("/")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            report["dependencies"].append(dict(path=str(path), frozen=str(target), **pin(data)))
        predefines = host.run([str(cc), "-dM", "-E", "-x", "assembler-with-cpp", *ASM_FLAGS, "-"],
                             cwd=out, kind="ASM-CPP-predefines", data=b"")
        (out / "asm-predefines.txt").write_bytes(predefines)
        machine_runs = []
        for generation in (1, 2):
            binary, map_path = work / "x", work / "x.map"
            host.run([str(cc), *flags, "-I", str(prepared), "-save-temps=obj", "-v", str(work / "main.c"),
                      str(prepared / "start.S"), "-Wl,-T," + str(prepared / "image.ld"), "-Wl,-Map," + str(map_path), "-o", str(binary)],
                     cwd=work, kind="fresh-C-LTO-link-" + str(generation))
            linked = binary.read_bytes()
            native = packer.strip_native(linked)
            if pin(linked)["sha256"] != LINKED_SHA or pin(native)["sha256"] != NATIVE_SHA:
                raise ValueError("fresh canonical C build does not match exact v8 linked/native gold")
            compiler_log = Path(report["commands"][-1]["stderr"]["path"]).read_bytes()
            machine, order, ignored = link_order(work, map_path.read_bytes(), compiler_log)
            archive = out / ("generation-" + str(generation))
            archive.mkdir()
            for path in work.iterdir():
                if path.is_file():
                    if path.stat().st_size > 64 << 20:
                        raise ValueError("compiler temporary-file cap")
                    (archive / path.name).write_bytes(path.read_bytes())
            report["generations"].append(dict(generation=generation, linked=pin(linked), native=pin(native),
                map=pin(map_path.read_bytes()), order=order, consumed_IR=ignored, machine={n: pin(d) for n, d in machine.items()}))
            machine_runs.append((machine, order))
            save()
        if machine_runs[0] != machine_runs[1]:
            raise ValueError("fresh LTRANS assembly/order did not independently reproduce")
        variants = []
        for machine, order in machine_runs:
            base = {**machine, "e.S": files["start.S"], "image.ld": files["image.ld"]}
            units = [r["unit"] for r in order]
            clean, minimal, clean_proof, minimal_proof = dict(base), dict(base), {}, {}
            for name in machine:
                clean[name], clean_proof[name] = clean_asm(base[name], projection)
                minimal[name], minimal_proof[name] = clean_asm(base[name], projection, metadata=True)
            current = [("raw", base, units, {}), ("comments", clean, units, clean_proof), ("metadata", minimal, units, minimal_proof)]
            for label, mnemonic, register in (("CPP-control", False, False), ("mnemonics", True, False), ("registers", False, True), ("both", True, True)):
                candidate, alias_proof = alias_asm(minimal, predefines, projection, mnemonics=mnemonic, registers=register)
                cpp_units = [n[:-2] + ".S" if n.endswith(".s") else n for n in units]
                current.append((label, candidate, cpp_units, alias_proof))
            local, local_proof = local_labels(candidate, tuple(n[:-2] + ".S" for n in machine), predefines, projection)
            current.append(("both-local-labels", local, cpp_units, local_proof))
            variants.append(current)
        assembly_work = out / "asm-compilation"
        assembly_work.mkdir()
        for index, (label, candidate, units, transform_proof) in enumerate(variants[0]):
            other_label, other_files, other_units, _ = variants[1][index]
            if (label, candidate, units) != (other_label, other_files, other_units):
                raise ValueError("ASM source variant did not independently regenerate")
            directory = out / label
            directory.mkdir()
            for name, data in candidate.items():
                (directory / name).write_bytes(data)
                (assembly_work / name).write_bytes(data)
            binary = assembly_work / "x"
            host.run([str(cc), *ASM_FLAGS, *[str(assembly_work / n) for n in units],
                      "-Wl,-T," + str(assembly_work / "image.ld"), "-o", str(binary)],
                     cwd=assembly_work, kind="reassemble-" + label)
            linked = binary.read_bytes()
            native = packer.strip_native(linked)
            (directory / "linked").write_bytes(linked)
            (directory / "native").write_bytes(native)
            equal = pin(linked)["sha256"] == LINKED_SHA and pin(native)["sha256"] == NATIVE_SHA
            row = dict(name=label, units=units, source={n: pin(d) for n, d in candidate.items()},
                       transform=transform_proof, linked=pin(linked), native=pin(native), native_identity=equal,
                       status="admitted" if equal else "rejected-native-differs", source_regenerated=True,
                       asm_native_builds=1)
            if label == "raw" and not equal:
                report["candidates"].append(row)
                raise ValueError("fresh raw LTRANS reassembly control differs; no ASM size admission")
            if equal:
                observations = []
                for repeat, data_files in enumerate((candidate, other_files), 1):
                    bundle = json.dumps(dict(format="D-machine-ASM-JIT-v1", files={n: d.decode() for n, d in sorted(data_files.items())},
                                             flags=ASM_FLAGS, units=units), separators=(",", ":")).encode()
                    payload = package.encode(bundle, "alone")
                    decoded = json.loads(lzma.decompress(payload))
                    if (lzma.decompress(payload) != bundle or decoded["format"] != "D-machine-ASM-JIT-v1" or
                            {n: d.encode() for n, d in decoded["files"].items()} != data_files or
                            decoded["flags"] != ASM_FLAGS or decoded["units"] != units):
                        raise ValueError("ASM bundle/source/payload inverse differs")
                    whole, header = package.envelope(package.SOURCE_CODE, payload)
                    (directory / ("whole-" + str(repeat))).write_bytes(whole)
                    (directory / ("payload-" + str(repeat))).write_bytes(payload)
                    observations.append(dict(source_bundle=pin(bundle), payload=pin(payload), whole=pin(whole), header=pin(header)))
                if observations[0] != observations[1]:
                    raise ValueError("ASM package/payload/whole did not independently reproduce")
                row.update(package_reproduced=True, package_rebuilds=observations, source_inverse=True,
                           whole=observations[0]["whole"])
            report["candidates"].append(row)
            save()
        for item in report["tools"].values():
            if pin(Path(item["path"]).read_bytes()) != {k: item[k] for k in ("bytes", "sha256")}:
                raise ValueError("consumed compiler/LTO/assembler/linker tool changed")
        for item in report["dependencies"]:
            if pin(Path(item["path"]).read_bytes()) != {k: item[k] for k in ("bytes", "sha256")}:
                raise ValueError("consumed canonical system header changed")
        winner = min((r for r in report["candidates"] if r["native_identity"]), key=lambda r: r["whole"]["bytes"])
        report.update(selected=winner["name"], selected_whole=winner["whole"], source_reproduced=True, native_gold=True)
    except BaseException as error:
        report["failure"] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        try:
            host.close()
        except BaseException as error:
            report["cleanup_failure"] = dict(type=type(error).__name__, message=str(error))
            raise
        finally:
            save()
    cleanup = report.get("host_cleanup", {})
    if cleanup.get("errors") or cleanup.get("unsettled_commands"):
        raise ValueError("ASM experiment ownership cleanup incomplete")
    report["complete"] = True
    save()
    print(json.dumps(dict(complete=True, selected=report["selected"], whole=report["selected_whole"],
                          engine_executed=False, Jammy_assembler_proven=False)), flush=True)


if __name__ == "__main__":
    main()
