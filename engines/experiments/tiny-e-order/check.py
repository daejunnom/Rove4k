#!/usr/bin/env python3
"""Check the model and actual DEV/shipping capture-priority consumers."""
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
    contract=recipe/"experiments/tiny-e-order/contract.c"
    try:
        command=[sys.executable,"-B",str(recipe/"compact/tiny-ce/check.py"),"--build",str(args.build),"--out",str(args.out/"model")]
        subprocess.run(command,check=True,timeout=120)
        for form,dev in (("dev",1),("original",0),("compact",0)):
            source=args.build.parent/form/"main.c"
            entry=next(e for e in build["engines"] if e["id"]=="tiny-E-"+form)
            if sha(source)!=entry["source_sha256"]:raise ValueError("producer source changed")
            # Test-only observer reads the numeric score after the unchanged
            # production assignment and unchanged model addition. Its oracle
            # does not re-evaluate a reconstructed search implementation.
            text=source.read_text()
            sites=("static int search(","scores[i]+=tiny_order(p,m);")
            if form=="compact":
                sites=("static int search(","scores[i]+=tiny_order(p,m);")
            for site in sites:
                if text.count(site)!=1:raise ValueError("observer site changed: "+site)
            text=text.replace(sites[0],"static void observed_priority(Worker*,const Board*,Move,Move,Move,int);\n"+sites[0])
            text=text.replace(sites[1],sites[1]+"observed_priority(w,p,m,tt,previous,scores[i]);")
            observed=args.out/(form+"-observed.c");observed.write_text(text)
            for kind,flags in (("optimized",["-O2"]),("asan-ubsan",["-O1","-fsanitize=address,undefined","-fno-omit-frame-pointer"])):
                binary=args.out/(form+"-"+kind)
                command=["cc","-std=c11","-pthread","-DWORKERS=1","-DTT_BITS=10",f"-DDEV={dev}",
                         "-DORDER_MODEL="+str(int(build["ordering_overlay"]["policy_change"])),
                         *flags,'-DTINY_E_SOURCE='+json.dumps(str(observed)),str(contract),"-o",str(binary)]
                subprocess.run(command,check=True,timeout=120)
                result=subprocess.run([str(binary)],capture_output=True,text=True,timeout=120)
                if result.returncode or result.stderr:raise AssertionError({"form":form,"kind":kind,"returncode":result.returncode,"stderr":result.stderr})
                record=json.loads(result.stdout)
                report["runs"].append({"form":form,"kind":kind,"compile":command,"program_sha256":sha(binary),
                    "source_sha256":sha(source),"observed_source_sha256":sha(observed),
                    "test_only_instrumentation":"one forward declaration and one post-assignment score observer",
                    "results":record})
        comparable=[{k:v for k,v in r["results"].items() if k!="board_bytes"} for r in report["runs"]]
        if any(record!=comparable[0] for record in comparable):raise AssertionError("DEV/shipping production consumer contracts differ")
        report["passed"]=True
    finally:(args.out/"results.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"passed":True,"runs":len(report["runs"]),"results":report["runs"][-1]["results"]}))

if __name__=="__main__":main()
