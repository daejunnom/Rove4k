#!/usr/bin/env python3
"""Build the independent pure-bitboard D structural experiment outside Git.

The final file is either a directly executable static ELF or the repository's
own self-restoring ELF. Both have no interpreter and no external runtime tool.
The size claim always counts the complete file. No candidate is accepted merely
because it compiles or has small source text.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import struct
import subprocess

HERE = Path(__file__).resolve().parent
ENGINE = HERE.parents[1]
NAMES = ("tiny.h", "board.c", "search.c", "runtime.c", "hq.h", "hq.c", "start.S", "image.ld", "build.py")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def strip_sections(data):
    """Strip only section metadata from our freshly linked known-layout ELF.

    Keep every PT_LOAD file byte, not an arbitrary trailing-zero heuristic.
    The kernel's load program headers remain unchanged.
    """
    data = bytearray(data)
    if data[:7] != b"\x7fELF\x02\x01\x01":
        raise ValueError("expected ELF64 little endian")
    phoff = struct.unpack_from("<Q", data, 32)[0]
    phentsize, count = struct.unpack_from("<HH", data, 54)
    end = 64
    for at in range(phoff, phoff + count * phentsize, phentsize):
        kind, _, offset, _, _, size, _, _ = struct.unpack_from("<IIQQQQQQ", data, at)
        if kind == 3:
            raise ValueError("standalone D must have no interpreter")
        if kind == 1:
            end = max(end, offset + size)
    struct.pack_into("<Q", data, 40, 0)
    struct.pack_into("<HHH", data, 58, 0, 0, 0)
    return bytes(data[:end])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--workers", default=2, type=int)
    parser.add_argument("--tt-bits", default=18, type=int)
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--no-pack", action="store_true")
    args = parser.parse_args()
    if args.out.is_absolute():
        args.out = args.out.resolve()
    if not args.out.is_absolute() or args.out.exists() or ENGINE.parent in args.out.parents:
        parser.error("--out must be a new absolute directory outside the checkout")
    if not 1 <= args.workers <= 512 or not 8 <= args.tt_bits <= 28:
        parser.error("workers 1..512 and TT bits 8..28")
    args.out.mkdir(parents=True)
    source = args.out / "sources"
    source.mkdir()
    for name in NAMES:
        shutil.copyfile(HERE / name, source / name)
    packer = ENGINE / "scripts/elf_loader.py"
    dependencies = [packer, ENGINE / "scripts/elf-loader/loader.c", ENGINE / "scripts/elf-loader/loader.ld",
                    ENGINE / "scripts/pack.py", ENGINE / "scripts/minify.py",
                    ENGINE / "scripts/compiler_group.py"]
    if not args.no_pack:
        for path in dependencies:
            target = args.out / "recipe/engines" / path.relative_to(ENGINE)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
        spec = importlib.util.spec_from_file_location("tiny_d_elf_loader", args.out / "recipe/engines/scripts/elf_loader.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        def load(name):
            spec = importlib.util.spec_from_file_location("tiny_d_bb_"+name, args.out / ("recipe/engines/scripts/"+name+".py"))
            result = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(result)
            return result
        source_packer, minifier = load("pack"), load("minify")
        compiler_group = load("compiler_group")
    flags = ["-Oz", "-flto", "-std=c11", "-nostdlib", "-static", "-no-pie", "-fno-pie", "-fno-pic",
             "-fno-stack-protector", "-fno-builtin", "-fno-asynchronous-unwind-tables", "-fno-unwind-tables",
             "-fno-ident", "-fcf-protection=none", "-ffunction-sections", "-fdata-sections",
             "-Wl,--gc-sections,--build-id=none,-s,-z,noexecstack", f"-DWORKERS={args.workers}", f"-DTT_BITS={args.tt_bits}"]
    records = []
    for hq in (0, 1):
        for dev in (1, 0):
            form = ("hq" if hq else "scalar") + ("-dev" if dev else "-shipping")
            directory = args.out / form
            directory.mkdir()
            command = [args.cc, *flags, f"-DD_HQ={hq}", f"-DDEV={dev}",
                       *[str(source / name) for name in ("board.c", "search.c", "runtime.c", "hq.c", "start.S")],
                       "-Wl,-T," + str(source / "image.ld"), "-o", str(directory / "linked")]
            subprocess.run(command, check=True, timeout=120)
            original = (directory / "linked").read_bytes()
            binary = strip_sections(original)
            target = directory / "x"
            target.write_bytes(binary)
            target.chmod(0o755)
            subprocess.run(command[:-1] + [str(directory / "linked-second")], check=True, timeout=120)
            if strip_sections((directory / "linked-second").read_bytes()) != binary:
                raise RuntimeError("native reproduction failed")
            record = {"id": "tiny-D-BB-" + form, "command": [str(target)], "cwd": str(directory),
                      "profile": "dev" if dev else "shipping", "workers": args.workers,
                      "startup_threads": args.workers + 1, "native_bytes": len(binary),
                      "native_sha256": digest(binary), "native_reproduced": True,
                      "linked_bytes": len(original), "compile": command, "runtime_external_tools": [],
                      "runtime_libraries": [], "launchers": []}
            if not dev and not args.no_pack:
                packed = module.pack_elf(target, directory / "self.elf", cc=args.cc, filter="auto")
                repeated = module.pack_elf(target, directory / "self-second.elf", cc=args.cc, filter="auto")
                if Path(packed["output"]).read_bytes() != Path(repeated["output"]).read_bytes():
                    raise RuntimeError("whole ELF reproduction failed")
                record["launchers"] = [{"path": packed["output"], "bytes": packed["output_bytes"],
                                        "sha256": packed["output_sha256"], "format": packed["format"],
                                        "reproduced": True}]
                record["packing"] = packed
                # Source packages are a general-4K cost control. D's eligible
                # target remains an ELF, with no runtime compiler/decoder tool.
                compact_dir = directory / "compact-source"
                compact_dir.mkdir()
                files = {}
                for name in NAMES:
                    if name == "build.py":
                        continue
                    data = (source / name).read_bytes()
                    if name.endswith((".c", ".h")):
                        data = minifier.compact_source(data, "c")
                    files[name] = data
                    (compact_dir / name).write_bytes(data)
                compact_command = [arg.replace(str(source), str(compact_dir)) for arg in command[:-1]]
                subprocess.run(compact_command + [str(compact_dir / "linked")], check=True, timeout=120)
                if strip_sections((compact_dir / "linked").read_bytes()) != binary:
                    raise RuntimeError("lexical source compaction changed whole native ELF bytes")
                source_command = [args.cc, *flags, f"-DD_HQ={hq}", "-DDEV=0", "board.c", "search.c", "runtime.c", "hq.c", "start.S",
                                  "-Wl,-T,image.ld", "-o", "x"]
                wrappers = source_packer.write_launchers(files, directory / "source-packages", command=source_command,
                                                        compiler_group=compiler_group.transform_bootstrap)
                again = source_packer.write_launchers(files, directory / "source-packages-repeated", command=source_command,
                                                     compiler_group=compiler_group.transform_bootstrap)
                for one, two in zip(wrappers, again):
                    if Path(one["path"]).read_bytes() != Path(two["path"]).read_bytes():
                        raise RuntimeError("complete source package reproduction differs")
                    one["reproduced"] = True
                record["source_launchers"] = wrappers
                record["source_compaction"] = {"native_whole_byte_identity": True,
                    "source_sha256": {name: digest(data) for name, data in files.items()},
                    "source_bytes": sum(len(data) for data in files.values()), "compile": source_command,
                    "underlying_complete_elf_sha256": digest((compact_dir / "linked").read_bytes())}
            records.append(record)
    report = {"candidate": "D pure 64-bitboard authority; absolute coordinates/colors; raw syscall runtime; actual scalar/HQ sliders",
              "engine_family": "D", "source_sha256": {name: digest((source / name).read_bytes()) for name in NAMES},
              "compiler": subprocess.check_output([args.cc, "--version"], text=True).splitlines()[0],
              "runtime": "Linux x86-64 raw syscalls; fixed clone/futex startup pool; no libc/TLS/interpreter",
              "engines": records, "runtime_validation": "not_yet_executed",
              "within_size_limit": all(min([r["native_bytes"]] + [p["bytes"] for p in r["launchers"]]) <= 4096
                                       for r in records if r["profile"] == "shipping")}
    (args.out / "build.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"out": str(args.out), "forms": [{"id": r["id"], "native_bytes": r["native_bytes"],
                       "self_elf_bytes": next((p["bytes"] for p in r["launchers"]), None)} for r in records]}))


if __name__ == "__main__":
    main()
