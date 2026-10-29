#!/usr/bin/env python3
"""Build two fixed original range algorithms against exact frozen TinyD RX."""
import argparse
import json
from pathlib import Path
import platform
import shutil
import sys

import codec
import native_support as support
import reference

HERE = Path(__file__).resolve().parent
RECIPE = ("build.py", "codec.py", "reference.py", "native_support.py", "loader.c", "image.ld",
          "test_codec.py", "test_native.py", "test_runtime.py", "startup.py")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cc", default="cc")
    args = parser.parse_args()
    if sys.platform != "linux" or platform.machine() != "x86_64":
        parser.error("requires Linux x86-64")
    out = args.out.resolve()
    if not args.out.is_absolute() or out.exists() or any((p/".git").exists() for p in (out, *out.parents)):
        parser.error("--out must be new, absolute and outside Git")
    args.out = out
    controls = {}
    for form in support.INPUTS:
        data = (args.input_root/form/"native-control").read_bytes()
        controls[form] = (data, support.admit(data, form))
    args.out.mkdir(parents=True)
    recipe = args.out/"recipe"
    recipe.mkdir()
    for name in RECIPE:
        shutil.copyfile(HERE/name, recipe/name)
    report = {"complete": False, "algorithm": "original-online-binary-range", "profiles": list(codec.PROFILES),
              "compiler": support.run([args.cc, "--version"])["stdout"].splitlines()[0],
              "recipe_sha256": {name:support.sha((recipe/name).read_bytes()) for name in RECIPE},
              "runtime_external_tools": [], "runtime_libraries": [], "engines": [], "negative_decoder_controls": [],
              "status": "size study only; no qualifying4KiB claim; runtime pending",
              "model_ram_bytes": {"order1": 131072, "mix2": 262656},
              "model_lifetime": "anonymous RW, initialized32768, unmapped before decoded image entry",
              "training": "none; adaptive probability state updates are intrinsic lossless decoding"}
    try:
        for form, (data, layout) in controls.items():
            base = args.out/form
            base.mkdir()
            (base/"native-control").write_bytes(data)
            (base/"native-control").chmod(0o755)
            engine = {"id":form,"layout":layout,"input_bytes":len(data),"input_sha256":support.sha(data),"candidates":[]}
            report["engines"].append(engine)
            for profile in codec.PROFILES:
                frame = codec.encode(codec.bcj(data),profile)
                if codec.bcj(reference.decode(frame),inverse=True) != data:
                    raise ValueError("independent restored RX mismatch")
                item = support.compile_loader(base/profile,recipe,frame,layout,profile,args.cc)
                repeat = support.compile_loader(base/(profile+"-repeat"),recipe,codec.encode(codec.bcj(bytes(data)),profile),layout,profile,args.cc)
                if item["sha256"] != repeat["sha256"]:
                    raise ValueError("whole ELF reproduction mismatch")
                item.update({"codec":profile,"reproduction":repeat,"within4096":item["bytes"]<=4096,
                             "frame_sha256":support.sha(frame),"decoded_image_sha256":support.sha(data),
                             "delta_from_native":item["bytes"]-len(data),"runtime_validation":"pending"})
                item["audit"] = support.compile_loader(base/(profile+"-audit"),recipe,frame,layout,profile,args.cc,checkpoint=True)
                engine["candidates"].append(item)
        data, layout = controls["scalar-shipping"]
        for profile in codec.PROFILES:
            good = codec.encode(codec.bcj(data),profile)
            corrupt = bytearray(good); corrupt[16] ^= 1
            length = bytearray(good); length[8:12] = (0xffffffff).to_bytes(4,"little")
            termination = bytearray(good); termination[-1] ^= 1
            for label, frame in (("truncated",good[:-1]),("checksum",bytes(corrupt)),("length",bytes(length)),("termination",bytes(termination))):
                invalid = support.compile_loader(args.out/("negative-"+profile+"-"+label),recipe,frame,layout,profile,args.cc)
                invalid.update({"name":profile+"-"+label,"expected_returncode":126,"eligibility":"invalid fixture"})
                report["negative_decoder_controls"].append(invalid)
        report["complete"] = True
    finally:
        (args.out/"build.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"out":str(args.out),"forms":[{"id":e["id"],"candidates":[{k:c[k] for k in ("codec","bytes","payload_bytes","loader_and_headers_bytes","within4096")} for c in e["candidates"]]} for e in report["engines"]]},indent=2))


if __name__ == "__main__":
    main()
