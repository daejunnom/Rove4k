#!/usr/bin/env python3
"""Two bounded dedicated TinyD image-restoration alternatives; no engine edits.

All inputs, recipes, diagnostics and generated files stay in a new absolute
directory outside Git. Only the two exact admitted shipping ELF images qualify.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import struct
import subprocess
import sys
import time
import zlib

HERE = Path(__file__).resolve().parent
INPUTS = {
    "scalar-shipping": (8540, "ef14e2839af96d111fa9ce1a2928749ceec518e3be652cc6d36ee8975cae47d0", 8806, 0x401fa6),
    "hq-shipping": (8928, "387a00209ffcc14446f662a56cc2ff778ae7873c2dfebebbee9906fd19e5cd0c", 9142, 0x4020e3),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def elf(data):
    if len(data) < 64 or data[:9] != b"\x7fELF\x02\x01\x01\0\0":
        raise ValueError("expected ELF64 little-endian System V ABI")
    kind, machine, version = struct.unpack_from("<HHI", data, 16)
    entry, phoff, shoff = struct.unpack_from("<QQQ", data, 24)
    flags, ehsize, phsize, phnum, shsize, shnum, shstr = struct.unpack_from("<IHHHHHH", data, 48)
    if (kind, machine, version, flags, ehsize, phoff, phsize) != (2, 62, 1, 0, 64, 64, 56):
        raise ValueError("unsupported ELF header")
    if not 1 <= phnum <= 3 or phoff + phnum*phsize > len(data):
        raise ValueError("invalid program header extent")
    segments = [dict(zip(("type", "flags", "offset", "vaddr", "paddr", "filesz", "memsz", "align"),
                         struct.unpack_from("<IIQQQQQQ", data, phoff+i*phsize))) for i in range(phnum)]
    return {"entry": entry, "section_offset": shoff, "section_size": shsize, "section_count": shnum,
            "section_names": shstr, "segments": segments}


def admit(data, form):
    size, expected, _, entry = INPUTS[form]
    if len(data) != size or sha(data) != expected:
        raise ValueError("unknown TinyD image bytes: " + form)
    parsed = elf(data)
    expected_segments = [
        {"type": 1, "flags": 5, "offset": 0, "vaddr": 0x400000, "paddr": 0x400000, "filesz": size, "memsz": size, "align": 4096},
        {"type": 1, "flags": 6, "offset": 0, "vaddr": 0x403000, "paddr": 0x403000, "filesz": 0, "memsz": 175092, "align": 4096},
        {"type": 0x6474e551, "flags": 6, "offset": 0, "vaddr": 0, "paddr": 0, "filesz": 0, "memsz": 0, "align": 8},
    ]
    if parsed["entry"] != entry or parsed["segments"] != expected_segments or any(parsed[key] for key in ("section_offset", "section_size", "section_count", "section_names")):
        raise ValueError("unadmitted layout/interpreter/TLS/dynamic/data/entry")
    image_pages = (size+4095)&-4096
    bss_pages = (175092+4095)&-4096
    if 0x400000+image_pages != 0x403000:
        raise ValueError("RX/RW pages overlap or layout changed")
    return {**parsed, "image_base": 0x400000, "image_size": size, "image_pages": image_pages,
            "bss_base": 0x403000, "bss_size": 175092, "bss_pages": bss_pages,
            "guard_base": 0x3ff000, "reserve_size": 4096+image_pages+bss_pages+4096,
            "upper_guard": 0x403000+bss_pages}


def run(command, *, timeout=120):
    started = time.monotonic()
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    try:
        stdout, stderr = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        stdout, stderr = p.communicate()
        raise RuntimeError("compiler/process timeout: " + json.dumps(list(map(str, command))))
    record = {"command": list(map(str, command)), "returncode": p.returncode, "wall_seconds": time.monotonic()-started,
              "stdout": stdout.decode(errors="replace"), "stderr": stderr.decode(errors="replace")}
    if p.returncode:
        raise RuntimeError(json.dumps(record))
    return record


def toolchain(compiler):
    compiler_path = shutil.which(compiler)
    if not compiler_path: raise FileNotFoundError(compiler)
    linker = run([compiler_path,"-print-prog-name=ld"])["stdout"].strip()
    linker_path = shutil.which(linker)
    if not linker_path: raise FileNotFoundError(linker)
    return {"compiler_requested":compiler,"compiler_path":compiler_path,
            "compiler_version":run([compiler_path,"--version"])["stdout"].strip(),
            "linker_path":linker_path,"linker_version":run([linker_path,"--version"])["stdout"].strip(),
            "python_executable":sys.executable,"python":sys.version,"platform":platform.platform(),
            "zlib_build_version":zlib.ZLIB_VERSION,"zlib_runtime_version":zlib.ZLIB_RUNTIME_VERSION}


def stripped_loader(data):
    parsed = elf(data)
    loads = [s for s in parsed["segments"] if s["type"] == 1]
    if len(loads) != 1 or len(parsed["segments"]) != 2 or loads[0]["flags"] != 5 or loads[0]["vaddr"] != 0x10000000:
        raise ValueError("loader must contain exactly one fixed RX image and nonexec stack")
    stack = next(s for s in parsed["segments"] if s["type"] == 0x6474e551)
    if stack["flags"] != 6 or any(s["flags"] & 3 == 3 for s in parsed["segments"]):
        raise ValueError("loader has executable writable mapping/stack")
    segment = loads[0]
    if segment["filesz"] != segment["memsz"] or segment["offset"]:
        raise ValueError("loader unexpectedly needs writable state")
    out = bytearray(data[:segment["filesz"]])
    struct.pack_into("<Q", out, 40, 0)
    struct.pack_into("<HHH", out, 58, 0, 0, 0)
    return bytes(out)


def compile_loader(directory, recipe, payload, layout, codec, compiler, checkpoint=False):
    directory.mkdir(parents=True)
    payload_path = directory / "payload.bin"
    payload_path.write_bytes(payload)
    quoted = str(payload_path).replace("\\", "\\\\").replace('"', '\\"')
    assembly = directory / "payload.S"
    assembly.write_text('.section .payload,"a",@progbits\n.global payload,payload_end\npayload:\n'
                        '.incbin "' + quoted + '"\npayload_end:\n.section .note.GNU-stack,"",@progbits\n')
    definitions = {"IMAGE_BASE": layout["image_base"], "IMAGE_SIZE": layout["image_size"], "IMAGE_PAGES": layout["image_pages"],
                   "IMAGE_ENTRY": layout["entry"], "BSS_BASE": layout["bss_base"], "BSS_PAGES": layout["bss_pages"],
                   "GUARD_BASE": layout["guard_base"], "RESERVE_SIZE": layout["reserve_size"],
                   "CODEC_FIXED": int(codec == "fixed"), "CHECKPOINT": int(checkpoint)}
    flags = ["-Oz", "-flto", "-nostdlib", "-static", "-no-pie", "-fno-pie", "-fno-pic", "-fno-builtin",
             "-fno-stack-protector", "-fno-asynchronous-unwind-tables", "-fno-unwind-tables", "-fno-ident",
             "-fcf-protection=none", "-ffunction-sections", "-fdata-sections", "-Wl,--gc-sections,--build-id=none,-s,-z,noexecstack"]
    command = [compiler, *flags, *[f"-D{name}={value}UL" for name,value in definitions.items()], str(recipe/"loader.c"), str(assembly),
               "-Wl,-T," + str(recipe/"image.ld"), "-o", str(directory/"linked")]
    record = run(command)
    (directory / "compile.json").write_text(json.dumps(record, indent=2)+"\n")
    data = stripped_loader((directory/"linked").read_bytes())
    target = directory / "x"
    target.write_bytes(data)
    target.chmod(0o755)
    return {"path": str(target), "bytes": len(data), "sha256": sha(data), "compile": record, "definitions": definitions,
            "payload_bytes": len(payload), "loader_and_headers_bytes": len(data)-len(payload)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cc", default="cc")
    args = parser.parse_args()
    if sys.platform != "linux" or platform.machine() != "x86_64":
        parser.error("requires Linux x86-64")
    out = args.out.resolve()
    if not args.out.is_absolute() or out.exists() or any((p/".git").exists() for p in (out,*out.parents)):
        parser.error("--out must be new, absolute and outside the checkout")
    input_root = args.input_root.resolve(strict=True)
    controls = json.loads((input_root/"build.json").read_text())
    selected = {r["id"].removeprefix("tiny-D-"):r for r in controls["engines"] if r["profile"] == "shipping"}
    if set(selected) != set(INPUTS):
        parser.error("expected exactly the two known TinyD shipping controls")
    frozen = {}
    for form, values in INPUTS.items():
        data = (input_root/form/"x").read_bytes()
        layout = admit(data, form)
        own = (input_root/form/"self.elf").read_bytes()
        if len(own) != values[2] or sha(own) != selected[form]["packing"]["output_sha256"]:
            raise ValueError("generic control changed")
        frozen[form] = (data, own, layout)
    out.mkdir(parents=True)
    tools = toolchain(args.cc)
    report = {"schema": 1, "complete": False, "input_root": str(input_root), "compiler": tools["compiler_version"], "tools":tools,
              "python": sys.version, "alternatives": ["lz+bcj+direct-image", "fixed-deflate+bcj+direct-image"], "engines": [],
              "negative_decoder_controls": [],
              "contract": "exact full original RX bytes at original virtual addresses; zero original BSS; fixed entry; W^X and surrounding guards; original initial stack",
              "requires_personality_read_implies_exec_clear": True,
              "excluded_observations": ["auxv AT_ENTRY/AT_PHDR/AT_EXECFN and /proc/self/exe identity remain the dedicated loader", "initial brk and loader mappings remain present; TinyD allocates with mmap", "privileged executable semantics"],
              "runtime_external_tools": [], "runtime_libraries": [], "rules_eligibility": "unproven; full file bytes still count"}
    try:
        recipe = out / "recipe"
        recipe.mkdir()
        for name in ("build.py", "loader.c", "image.ld", "codec.py", "test_runtime.py"):
            shutil.copyfile(HERE/name, recipe/name)
        report["recipe_sha256"] = {p.name:sha(p.read_bytes()) for p in sorted(recipe.iterdir())}
        spec = importlib.util.spec_from_file_location("tiny_d_codec_frozen", recipe/"codec.py")
        codecs = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(codecs)
        shutil.copyfile(input_root/"build.json", out/"control-build.json")
        sources = out/"control-sources"
        sources.mkdir()
        for name, expected in controls["source_sha256"].items():
            data = (input_root/"sources"/name).read_bytes()
            if sha(data) != expected: raise ValueError("control source changed: "+name)
            (sources/name).write_bytes(data)
        generic_recipe = out/"control-recipe"
        generic_recipe.mkdir()
        for name in ("elf_loader.py", "elf-loader/loader.c", "elf-loader/loader.ld"):
            target = generic_recipe/name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(input_root/"recipe/engines/scripts"/name, target)
        report["control_recipe_sha256"] = {str(p.relative_to(generic_recipe)):sha(p.read_bytes()) for p in sorted(generic_recipe.rglob("*")) if p.is_file()}
        for form, (data, control, layout) in frozen.items():
            base = out/form
            base.mkdir()
            (base/"native-control").write_bytes(data)
            (base/"generic-control").write_bytes(control)
            (base/"native-control").chmod(0o755)
            (base/"generic-control").chmod(0o755)
            filtered = codecs.bcj(data)
            entry = {"id":form, "layout":layout, "input_sha256":sha(data), "input_bytes":len(data),
                     "generic_control_bytes":len(control), "generic_control_sha256":sha(control), "candidates":[]}
            report["engines"].append(entry)
            for codec in ("lz", "fixed"):
                compressor, decompressor = ((codecs.lz_compress, codecs.lz_decompress) if codec == "lz" else (codecs.fixed_compress, codecs.fixed_decompress))
                payload = compressor(filtered)
                if codecs.bcj(decompressor(payload,len(data)), inverse=True) != data:
                    raise ValueError("codec image identity failed")
                candidate = compile_loader(base/codec, recipe, payload, layout, codec, args.cc)
                repeat = compile_loader(base/(codec+"-repeat"), recipe, compressor(codecs.bcj(bytes(data))), layout, codec, args.cc)
                if candidate["sha256"] != repeat["sha256"]:
                    raise ValueError("independent whole file reproduction failed")
                candidate.update({"codec":codec, "reproduction":repeat, "decoded_image_sha256":sha(data),
                                  "within4096":candidate["bytes"]<=4096, "delta_from_native":candidate["bytes"]-len(data),
                                  "delta_from_generic":candidate["bytes"]-len(control), "runtime_validation":"pending"})
                candidate["audit"] = compile_loader(base/(codec+"-audit"), recipe, payload, layout, codec, args.cc, checkpoint=True)
                entry["candidates"].append(candidate)
        negative_layout = frozen["scalar-shipping"][2]
        for name, codec, payload in (("zero-distance", "lz", b"\x80\0\0"), ("truncated-literal", "lz", b"\x7fA"),
                                     ("unsupported-block", "fixed", b"\0"), ("truncated-code", "fixed", b"\x03")):
            negative = compile_loader(out/("negative-"+name),recipe,payload,negative_layout,codec,args.cc)
            negative.update({"name":name,"codec":codec,"expected_returncode":126,"eligibility":"invalid diagnostic fixture, never a candidate"})
            report["negative_decoder_controls"].append(negative)
        report["complete"] = True
    except Exception as error:
        report["failure"] = str(error)
        raise
    finally:
        (out/"build.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps({"out":str(out), "forms":[{"form":e["id"], "native":e["input_bytes"], "generic":e["generic_control_bytes"],
          "candidates":[{"codec":c["codec"],"bytes":c["bytes"],"delta_native":c["delta_from_native"],"delta_generic":c["delta_from_generic"]} for c in e["candidates"]]} for e in report["engines"]]}, indent=2))


if __name__ == "__main__":
    main()
