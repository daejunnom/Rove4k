#!/usr/bin/env python3
"""Native decoder parity fixtures stop before entry; arbitrary data never runs.

These are diagnostic ELF images, not engine candidates. The same production C
decoder/mapping code restores into the real guarded TinyD span. SIGSTOP occurs
after checksum, range termination, BCJ inverse, model unmap and RX protection.
The parent checks every byte and kills/reaps each diagnostic without resuming.
"""
import argparse
import hashlib
import json
from pathlib import Path
import random
import shutil
import subprocess
import time

import codec
import native_support as support
import test_runtime as runtime

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--cc",default="cc")
    args = parser.parse_args()
    out = args.out.resolve()
    if not args.out.is_absolute() or out.exists() or any((p/".git").exists() for p in (out,*out.parents)):
        parser.error("--out must be new, absolute and outside Git")
    args.out = out
    build = json.loads(args.build.read_text())
    layout = build["engines"][0]["layout"]
    recipe = args.build.parent/"recipe"
    args.out.mkdir(parents=True)
    shutil.copyfile(HERE/"test_native.py",args.out/"test_native.py")
    rng = random.Random(20261020)
    fixtures = (b"",b"\0",b"\xff",bytes(range(256)),bytes(range(255,-1,-1)),
                b"\0"*4096,b"\xff"*4096,rng.randbytes(8192),
                b"\xe8\0\0\0\0\xe9\xff\xff\xff\xff"*500)
    report = {"complete":False,"validator_sha256":support.sha(Path(__file__).read_bytes()),
              "build_sha256":support.sha(args.build.read_bytes()),"parity":[],"negative":[],
              "diagnostic_only":True,"arbitrary_fixture_execution":False,"all_owned_processes_reaped":False}
    started = time.monotonic()
    try:
        for profile in codec.PROFILES:
            for number,data in enumerate(fixtures):
                fixture_layout = {**layout,"image_size":len(data)}
                frame = codec.encode(codec.bcj(data),profile)
                candidate = support.compile_loader(args.out/(profile+"-"+str(number)),recipe,frame,fixture_layout,profile,args.cc,checkpoint=True)
                process = subprocess.Popen([candidate["path"]],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
                try:
                    runtime.stopped(process)
                    evidence = runtime.inspect(process.pid,fixture_layout,support.sha(data),initial=True)
                    report["parity"].append({"profile":profile,"fixture":number,"raw_bytes":len(data),
                                             "image_sha256":support.sha(data),"passed":True,"pre_entry":evidence})
                finally:
                    runtime.cleanup(process)
            small = codec.encode(b"\0\xff",profile)
            # Every truncation prefix of a valid short frame, including the
            # frame/body boundary and initial five range bytes, fails closed.
            for cut in range(len(small)):
                candidate = support.compile_loader(args.out/(profile+"-truncated-"+str(cut)),recipe,small[:cut],
                                                   {**layout,"image_size":2},profile,args.cc)
                process = subprocess.Popen([candidate["path"]],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
                try:
                    stdout,stderr = process.communicate(b"",timeout=5)
                    if process.returncode != 126 or stdout:
                        raise ValueError("native truncation not rejected: "+str((profile,cut,process.returncode,stdout,stderr)))
                    report["negative"].append({"profile":profile,"truncated_at":cut,"passed":True,"returncode":126})
                finally:
                    runtime.cleanup(process)
        report["complete"] = True
        report["all_owned_processes_reaped"] = True
    except Exception as error:
        report["failure"] = repr(error)
        raise
    finally:
        report["wall_seconds"] = time.monotonic()-started
        (args.out/"native.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"complete":report["complete"],"parity":len(report["parity"]),"truncation_rejections":len(report["negative"]),
                      "all_owned_processes_reaped":report["all_owned_processes_reaped"],"wall_seconds":report["wall_seconds"]}))


if __name__ == "__main__":
    main()
