#!/usr/bin/env python3
"""Check actual DEV and shipping consumers using the frozen producer recipe."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build",type=Path,required=True);parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    if not args.out.is_absolute():parser.error("--out must be a new absolute directory outside Git")
    args.out=args.out.resolve()
    if args.out.exists() or ROOT==args.out or ROOT in args.out.parents or any((p/".git").exists() for p in args.out.parents):
        parser.error("--out must be a new absolute directory outside Git")
    args.out.mkdir(parents=True)
    report={"passed":False,"build_sha256":sha(args.build),"runs":[]}
    build=json.loads(args.build.read_bytes());recipe=args.build.parent/"recipe/engines"
    # Every executed checker, oracle and production source is saved by build.py.
    for name,digest in build["input_sha256"].items():
        if sha(args.build.parent/"recipe"/name)!=digest:raise ValueError("frozen recipe changed: "+name)
    contract=recipe/"experiments/tiny-e-state/contract.c"
    try:
        command=[sys.executable,"-B",str(recipe/"compact/tiny-ce/check.py"),"--build",str(args.build),"--out",str(args.out/"model")]
        subprocess.run(command,check=True,timeout=120)
        for form,dev in (("dev",1),("original",0),("compact",0)):
            source=args.build.parent/form/"main.c"
            entry=next(e for e in build["engines"] if e["id"]=="tiny-E-"+form)
            if sha(source)!=entry["source_sha256"]:raise ValueError("producer source changed")
            for kind,flags in (("optimized",["-O2"]),("asan-ubsan",["-O1","-fsanitize=address,undefined","-fno-omit-frame-pointer"])):
                binary=args.out/(form+"-"+kind)
                command=["cc","-std=c11","-pthread","-DWORKERS=1","-DTT_BITS=10",f"-DDEV={dev}",*flags,'-DTINY_E_SOURCE='+json.dumps(str(source)),str(contract),"-o",str(binary)]
                subprocess.run(command,check=True,timeout=120)
                result=subprocess.run([str(binary)],capture_output=True,text=True,timeout=120)
                if result.returncode or result.stderr:raise AssertionError({"form":form,"kind":kind,"returncode":result.returncode,"stderr":result.stderr})
                record=json.loads(result.stdout)
                report["runs"].append({"form":form,"kind":kind,"compile":command,"program_sha256":sha(binary),"source_sha256":sha(source),"results":record})
        comparable=[{k:v for k,v in r["results"].items() if k!="board_bytes"} for r in report["runs"]]
        if any(record!=comparable[0] for record in comparable):raise AssertionError("DEV/shipping production consumer contracts differ")
        report["passed"]=True
    finally:(args.out/"results.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"passed":True,"runs":len(report["runs"]),"results":report["runs"][-1]["results"]}))

if __name__=="__main__":main()
