#!/usr/bin/env python3
"""Measure complete shipping files for the four matched production F modes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"engines/tests"))
from chess_oracle import Board
from verify import Engine, require, search

MODES=(("paired","previous"),("paired","parity"),("single","previous"),("single","parity"))


def selected_runtime(record,artifact,label,out):
    board=Board.from_fen()
    spec={"id":label,"command":[artifact["path"]],"profile":"shipping",
          "configuration":record["configuration"],"startup_timeout":60}
    checks=[]
    for ending in ("quit","EOF"):
        engine=Engine(spec,out,label+"-"+ending,10)
        try:
            engine.initialize()
            engine.position()
            bounded=search(engine,board,"go wtime 1000 btime 1000 winc 0 binc 0",require_info=False)
            engine.position()
            zero=search(engine,board,"go wtime 0 btime 0 winc 0 binc 0",require_info=False)
            engine.position()
            engine.send("go wtime 600000 btime 600000 winc 0 binc 0")
            time.sleep(.04)
            ready=engine.ready()
            require(not any(line.startswith("bestmove ")for line in ready),"clocked go ended before active cancellation")
            engine.send("stop")
            stopped=engine.until(lambda line:line.startswith("bestmove "))
            best=[line.split()[1]for line in stopped if line.startswith("bestmove ")]
            require(len(best)==1,"active stop must publish exactly one move")
            board.play(best[0])
            require(not any(line.startswith("bestmove ")for line in engine.quiet()),"duplicate move after active stop")
            engine.assert_threads_stable()
            engine.position()
            engine.send("go wtime 600000 btime 600000 winc 0 binc 0")
            time.sleep(.04)
            ready=engine.ready()
            require(not any(line.startswith("bestmove ")for line in ready),"clocked go ended before active "+ending)
            engine.close(eof=ending=="EOF")
            final=engine.drain()
            best=[line.split()[1]for line in final if line.startswith("bestmove ")]
            require(len(best)==1,"active "+ending+" must publish exactly one move")
            board.play(best[0])
            checks.append({"ending":ending,"clocked_bestmove":bounded["bestmove"],
                "zero_clock_bestmove":zero["bestmove"],"active_stop_bestmove":stopped[-1].split()[1],
                "active_shutdown_bestmove":best[0],"startup_threads":sorted(engine.startup_task_ids or ())})
        finally:
            if engine.process.poll()is None:engine.terminate()
            elif not engine.log.closed:engine.close()
    return checks


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root",required=True,type=Path,help="frozen engines directory from campaign.py")
    parser.add_argument("--out",required=True,type=Path)
    parser.add_argument("--cc",default="cc")
    parser.add_argument("--rustc",default="rustc")
    args=parser.parse_args()
    out=args.out.resolve()
    require(not out.exists()and not out.is_relative_to(ROOT),"output must be new and outside repository")
    out.mkdir(parents=True)
    os.environ["PATH"]=str(Path(args.rustc).resolve().parent)+os.pathsep+os.environ.get("PATH","")
    report={"schema":1,"profile":"local-ship","scope":"complete shipping file and TT memory cost; no speed/strength claim",
            "source_root":str(args.source_root.resolve()),"commands":[],"engines":[],"complete":False}
    source_hashes={}
    builder=ROOT/"engines/scripts/build.py"
    frozen_tooling=None
    try:
        for table,guess in MODES:
            label=table+"-"+guess
            destination=out/label
            command=[sys.executable,str(builder),"--source-root",str(args.source_root.resolve()),
                     "--out",str(destination),"--profile","local-ship","--languages","c,rust","--variants","F",
                     "--parallel","loose","--f-tt",table,"--f-guess",guess,"--cc",args.cc,"--rustc",args.rustc,
                     "--no-smoke","--reproduce"]
            report["commands"].append(command)
            subprocess.run(command,check=True,cwd=ROOT)
            manifest=json.loads((destination/"build.json").read_text())
            require(manifest["complete"],"shipping build incomplete")
            tooling=sorted((item["path"],item["sha256"])for item in manifest["tooling_inputs"])
            require(frozen_tooling is None or frozen_tooling==tooling,"shipping tooling changed across experiment")
            frozen_tooling=tooling
            if label=="paired-previous":builder=destination/"recipe/engines/scripts/build.py"
            for record in manifest["engines"]:
                language=record["id"].split("-")[1]
                hashes=sorted((item["path"],item["sha256"])for item in record["sources"])
                require(language not in source_hashes or source_hashes[language]==hashes,"shipping inputs differ")
                source_hashes[language]=hashes
                selected=min(record["artifacts"],key=lambda item:item["bytes"])
                require(hashlib.sha256(Path(selected["path"]).read_bytes()).hexdigest()==selected["sha256"],"selected file hash mismatch")
                require(selected["reproduction"]["identical"],"selected file not reproducible")
                runtime=selected_runtime(record,selected,label+"-"+language,out)
                slot=16 if table=="single"else(32 if language=="c"else 24)
                entry={"mode":label,"language":language,"selected_complete_file":selected,
                       "native_original_bytes":next(x["bytes"]for x in record["artifacts"]if x["format"]=="native-elf"and x["source_form"]=="original"),
                       "tt_slot_bytes":slot,"tt_total_bytes":slot*(1<<int(record["configuration"]["ROVE_TT_BITS"])),
                       "configuration":record["configuration"],"runtime":runtime}
                report["engines"].append(entry)
                print(label+"-"+language+": "+str(selected["bytes"])+"B "+selected["format"]+" selected full file; clocked/zero/active stop/quit/EOF PASS",flush=True)
        report["source_hashes"]=source_hashes
        report["complete"]=True
    finally:
        (out/"cost.json").write_text(json.dumps(report,indent=2)+"\n")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
