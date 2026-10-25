#!/usr/bin/env python3
"""Cold-process semantic gate for the real matched E production engines.

Node equality is required only with one worker. Timing is deliberately absent.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"engines/tests"))
from chess_oracle import Board
from verify import Engine, require, search

CASES=(
    ("start",None,(),4),
    ("opening",None,("e2e4","e7e5","g1f3","b8c6","f1b5","a7a6"),4),
    ("kiwipete","r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",(),3),
    ("quiet-pawns","8/6pk/8/8/8/8/PK6/8 w - - 0 1",(),5),
    ("legal-ep","4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1",(),4),
    ("pinned-ep","k7/8/8/4KPpr/8/8/8/8 w - g6 0 1",(),3),
)


def integer_hash(value):return int(value,16)if isinstance(value,str)else value


def process_memory(pid):
    result={}
    for line in(Path("/proc")/str(pid)/"status").read_text().splitlines():
        key,_,value=line.partition(":")
        if key in("VmPeak","VmSize","VmHWM","VmRSS","VmData","VmStk","Threads"):result[key]=value.strip()
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    require(not args.out.exists()and not args.out.resolve().is_relative_to(ROOT),"output must be new and outside repository")
    args.out.mkdir(parents=True)
    manifest=json.loads(args.manifest.read_text())
    require(manifest["contract"]=="matched-c-policy-v1","wrong source contract")
    require(len(manifest["engines"])==2,"two actual compiled engines required")
    workers=manifest["policy"]["search_workers"]
    report={"schema":1,"contract":manifest["contract"],"generation_sha256":hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
            "workers":workers,"scope":"semantic/resource checks only; no timing or language-effect claim","cases":[],"passed":False}
    try:
        for label,fen,moves,depth in CASES:
            board=Board.from_fen(fen)if fen else Board.from_fen()
            for move in moves:board=board.play(move)
            records=[]
            for spec in manifest["engines"]:
                require(hashlib.sha256(Path(spec["command"][0]).read_bytes()).hexdigest()==spec["native"]["sha256"],"native bytes changed")
                engine=Engine(spec,args.out,label+"-"+spec["id"],30)
                try:
                    engine.initialize();engine.position(fen,moves)
                    state=engine.state()
                    legal=set(engine.dev("legal","legal").split()[1:])
                    require(legal=={str(m)for m in board.legal_moves()},"legal move set differs from independent oracle")
                    result=search(engine,board,f"go depth {depth}")
                    require(result["info"][-1]["depth"]==depth,"nonmate fixture did not complete requested depth")
                    stats=engine.stats()
                    require(stats.get("tt_bytes",4194304)==4194304,"C actual TT bytes differ from resource contract")
                    records.append({"engine":spec["id"],"state":state,"legal":sorted(legal),"result":result,"stats":stats,
                                    "startup_threads":sorted(engine.startup_task_ids or()),"os_memory":process_memory(engine.process.pid)})
                finally:engine.close()
            left,right=records
            for field in("hash","pawn_hash"):
                require(integer_hash(left["state"][field])==integer_hash(right["state"][field]),"cross-engine "+field+" differs")
            require(left["state"]["eval"]==right["state"]["eval"],"raw E model differs")
            require([item["depth"]for item in left["result"]["info"]]==list(range(1,depth+1)),"C omitted an iterative depth")
            require([item["depth"]for item in right["result"]["info"]]==list(range(1,depth+1)),"Rust omitted an iterative depth")
            for a,b in zip(left["result"]["info"],right["result"]["info"]):
                require((a["depth"],a["kind"],a["score"])==(b["depth"],b["kind"],b["score"]),"completed depth value differs")
                if workers==1:require(a["nodes"]==b["nodes"],f"one-worker tree differs at depth {a['depth']}: C {a['nodes']} / Rust {b['nodes']}")
            if workers==1:
                require(left["result"]["bestmove"]==right["result"]["bestmove"],"one-worker attaining move differs")
                require(left["stats"]["nodes"]==right["stats"]["nodes"],"one-worker total nodes differ")
            report["cases"].append({"id":label,"records":records,"passed":True})
            print(label+": model/hash/legal/depth values"+("/nodes/bestmove"if workers==1 else"")+" PASS",flush=True)
        report["passed"]=True
    finally:(args.out/"results.json").write_text(json.dumps(report,indent=2)+"\n")
    return 0


if __name__=="__main__":raise SystemExit(main())
