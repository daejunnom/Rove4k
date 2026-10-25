#!/usr/bin/env python3
"""Finite unit-window equivalence and two actual selected-wrapper sessions.

The reference always receives alpha=beta-1. The candidate uses its real beta-
only API. Actual compact DEV0 shipping inputs are included by O2/SAN fixtures;
readable DEV fixtures separately exercise the real MTD driver and node/ply stop.
No wide-window result is reused as candidate proof, and no broad games/NPS run.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
sys.dont_write_bytecode=True
QUIET=("8/6pk/8/8/8/8/PK6/8 w - - 0 1","8/6pk/8/8/8/P7/1K6/8 b - - 0 1","8/7k/6p1/8/8/P7/1K6/8 w - - 0 1")


def sha(data):return hashlib.sha256(data).hexdigest()


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec)
    sys.modules[name]=result;spec.loader.exec_module(result);return result


def evaluate(board):
    values={"p":100,"n":320,"b":330,"r":500,"q":900,"k":0};total=0
    for q,piece in enumerate(board.cells):
        if piece==".":continue
        rank,file=divmod(q,8);advance=rank if piece.isupper() else 7-rank
        center=7-abs(2*file-7)-abs(2*rank-7);kind=piece.lower()
        positional={"p":advance*7+center*2,"n":center*9,"b":center*5,"r":advance*2,"q":center*2,"k":-center*3}[kind]
        total+=(1 if piece.isupper() else -1)*(values[kind]+positional)
    return total*(1 if board.turn else -1)


def minimax(board,depth,ply=0):
    moves=list(board.legal_moves())
    if not moves:return -30000+ply if board.in_check() else 0
    if depth==0:
        if board.in_check() or any(board.cells[m.dst]!="." or m.promotion or
             board.cells[m.src].lower()=="p" and m.dst==board.ep for m in moves):
            raise ValueError("independent quiet fixture no longer has a quiet frontier")
        return evaluate(board)
    return max(-minimax(board.apply(m),depth-1,ply+1) for m in moves)


def uci(move):
    if not move:return "0000"
    f,t=move&127,(move>>7)&127;p=(move>>14)&7
    return chr(97+(f&7))+str(1+(f>>4))+chr(97+(t&7))+str(1+(t>>4))+("  nbrq"[p] if p else "")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cost",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve();cost_path=args.cost.resolve()
    if not args.out.is_absolute() or out.exists() or REPO==out or REPO in out.parents:
        parser.error("new absolute external output required")
    cost_raw=cost_path.read_bytes();cost=json.loads(cost_raw)
    if not(cost["complete"] and cost["control_exact"] and cost["candidate_reproduced"] and cost["delta_complete_bytes"]<0):
        parser.error("a successful smaller fixed-cost candidate is required")
    records=cost["forms"]
    if [r["kind"] for r in records]!=["control","candidate","candidate"]:raise ValueError("fixed first-cost inventory changed")
    out.mkdir(parents=True);frozen=out/"inputs";frozen.mkdir()
    report={"complete":False,"scope":"finite integer-window/core equivalence and physical selected-wrapper sessions; no broad board/games/NPS claim",
            "cost_sha256":sha(cost_raw),"inputs":{},"compilations":[],"comparisons":[],"fresh_sessions":[]}
    def save():(out/"proof.json").write_text(json.dumps(report,indent=2)+"\n")
    def retain(name,content):
        path=frozen/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
        report["inputs"][name]=sha(content);return path
    retain("cost.json",cost_raw)
    for name in ("proof.py","contract.c"):retain(name,(HERE/name).read_bytes())
    checks=json.loads((HERE/"checks/inputs.json").read_text())
    if set(checks)!={"verify.py","chess_oracle.py"}:raise ValueError("unknown checker closure")
    for name,pin in checks.items():
        content=(HERE/"checks"/name).read_bytes().replace(b"\r\n",b"\n")
        if sha(content)!=pin:raise ValueError("pinned checker drift: "+name)
        retain("checks/"+name,content)
    sys.path.insert(0,str(frozen/"checks"));oracle=module("f_zero_oracle",frozen/"checks/chess_oracle.py")
    cases=[]
    for index,fen in enumerate(QUIET):
        board=oracle.Board.from_fen(fen)
        for depth in (1,3):
            value=minimax(board,depth)
            thresholds=sorted(set(([value,value+1] if depth==1 else [-29999,-1,0,1,30000,value,value+1])))
            for beta in thresholds:cases.append({"fen":fen,"depth":depth,"beta":beta,"quiet":True,"expected":value,"quiet_index":index})
    specials=(
        ("7k/6Q1/5K2/8/8/8/8/8 b - - 100 1",-30000),
        ("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1",0),
        ("7k/8/8/8/8/8/8/K7 w - - 0 1",0),
        ("7k/8/8/8/8/8/1Q6/K7 w - - 100 1",0),
        ("4k3/8/8/8/8/8/4r3/4K3 w - - 0 1",None))
    for fen,value in specials:
        for depth in (0,2):
            for beta in (0,1):cases.append({"fen":fen,"depth":depth,"beta":beta,"quiet":False,"expected":value})
    for depth in (0,2):
        cases.append({"fen":specials[1][0],"depth":depth,"beta":-29999,"quiet":False,"expected":0})
    for beta in (evaluate(oracle.Board.from_fen(QUIET[0])),evaluate(oracle.Board.from_fen(QUIET[0]))+1):
        cases.append({"fen":QUIET[0],"depth":0,"beta":beta,"quiet":False,"expected":evaluate(oracle.Board.from_fen(QUIET[0]))})
    header="typedef struct{const char *fen;int depth,beta;} Case;\nstatic const Case cases[]={\n"+"".join("{"+json.dumps(c["fen"])+","+str(c["depth"])+","+str(c["beta"])+"},\n" for c in cases)+"};\n#define CASE_COUNT "+str(len(cases))+"\nstatic const char *quiet_fens[]={"+",".join(json.dumps(f) for f in QUIET)+"};\n"
    retain("cases.h",header.encode());report["windows"]=cases
    for index,record in enumerate(records):
        directory=cost_path.parent/(["control","candidate-1","candidate-2"][index])
        if Path(record["directory"]).resolve()!=directory:raise ValueError("cost output path is not its owned fixed form")
        for filename,key in (("engine.c","readable"),("main.c","source"),("native/x","native"),("x","whole")):
            content=(directory/filename).read_bytes()
            if sha(content)!=record[key+"_sha256"]:raise ValueError("cost artifact drift: "+filename)
            if index<2:retain(("control" if index==0 else "candidate")+"/"+filename,content)
    for name in ("control","candidate"):
        (frozen/name/"x").chmod(0o755);(frozen/name/"native/x").chmod(0o755)
    old=(frozen/"control/engine.c").read_bytes();new=(frozen/"candidate/engine.c").read_bytes()
    old_prefix,old_tail=old.split(b"static int search(",1)[0],old.split(b"void think(",1)[1]
    new_prefix,new_tail=new.split(b"static int search(",1)[0],new.split(b"void think(",1)[1]
    adjusted=new_tail.replace(b"score=search(w,p,depth,beta,0,6,&move);",b"score=search(w,p,depth,beta-1,beta,0,6,&move);")
    if old_prefix!=new_prefix or old_tail!=adjusted:raise ValueError("unrelated board/TT/driver/pool/parser bytes changed")
    report["body_reuse"]={"unchanged_prefix_sha256":sha(old_prefix),"driver_runtime_except_api_call_sha256":sha(old_tail),
                           "scope":"board, coherent TT primitive, leaf helpers, MTD driver except root API argument, pool and parser byte identity"}
    save()
    try:
        outputs={}
        configs=(("shipping-O2",0,128,["-O2"]),("shipping-SAN",0,128,["-O1","-g","-fsanitize=address,undefined","-fno-omit-frame-pointer"]),
                 ("DEV-O2",1,128,["-O2"]),("DEV-SAN",1,128,["-O1","-g","-fsanitize=address,undefined","-fno-omit-frame-pointer"]),
                 ("PLY4-O2",1,4,["-O2"]))
        for label,dev,ply,flags in configs:
            for name,zero in (("control",0),("candidate",1)):
                directory=out/(label+"-"+name);directory.mkdir()
                source=frozen/name/("engine.c" if dev else "main.c")
                command=["cc","-std=c11",*flags,"-pthread","-DWORKERS=2","-DTT_BITS=18","-DPLY="+str(ply),
                         "-DDEV="+str(dev),"-DFIXTURE_SHIPPING="+str(1-dev),"-DZERO="+str(zero),
                         '-DENGINE_SOURCE="'+str(source)+'"',"-I"+str(frozen),str(frozen/"contract.c"),"-o",str(directory/"x")]
                built=subprocess.run(command,capture_output=True,timeout=90)
                (directory/"compiler.stderr").write_bytes(built.stderr)
                if built.returncode:raise RuntimeError("fixture compile failed: "+str(directory))
                ran=subprocess.run([str(directory/"x")],capture_output=True,text=True,timeout=60)
                (directory/"stdout.jsonl").write_text(ran.stdout);(directory/"stderr.txt").write_text(ran.stderr)
                if ran.returncode:raise RuntimeError("fixture execution failed: "+str(directory))
                rows=[json.loads(line) for line in ran.stdout.splitlines()];outputs[label,name]=rows
                report["compilations"].append({"label":label,"form":name,"command":command,"source_sha256":sha(source.read_bytes()),
                                               "binary_sha256":sha((directory/"x").read_bytes()),"rows":len(rows),"stderr":ran.stderr})
                save()
            if outputs[label,"control"]!=outputs[label,"candidate"]:raise AssertionError("unit-window state/output differs: "+label)
            for row in outputs[label,"candidate"]:
                if row["group"]=="window":
                    case=cases[row["index"]];value=case["expected"]
                    if value is not None:
                        score=row["score"];beta=case["beta"]
                        if not ((beta<=score<=value) if value>=beta else (value<=score<beta)):
                            raise AssertionError("directional bound excludes independent value")
                        if case["quiet"] and beta in (value,value+1) and score!=value:raise AssertionError("adjacent threshold is not exact")
                        if case["quiet"] and case["depth"]>0:
                            board=oracle.Board.from_fen(case["fen"]);move=uci(row["move"])
                            if move not in {str(m) for m in board.legal_moves()}:raise AssertionError("root unit probe move is illegal")
                            if score>=beta and -minimax(board.play(move),case["depth"]-1,1)<score:raise AssertionError("fail-high move does not attain its lower bound")
                elif row["group"]=="iteration":
                    index,repeat=divmod(row["index"],4);depth=(3,3,1,2)[repeat];board=oracle.Board.from_fen(QUIET[index]);value=minimax(board,depth)
                    if row["score"]!=value or -minimax(board.play(uci(row["move"])),depth-1,1)!=value:raise AssertionError("converged MTD score/witness differs from independent minimax")
            report["comparisons"].append({"label":label,"equal":True,"rows":len(outputs[label,"candidate"])})
            save()
        for dev in ("DEV-O2","DEV-SAN"):
            for name in ("control","candidate"):
                common=[r for r in outputs[dev,name] if r["group"] in ("window","tt","half","repeat","ordering")]
                shipping=outputs["shipping-"+("SAN" if dev.endswith("SAN") else "O2"),name]
                if common!=shipping:raise AssertionError("DEV vs actual shipping core unit results differ")
        shared=module("f_zero_shared_verify",frozen/"checks/verify.py")
        selected=records[1];program=frozen/"candidate/x"
        for eof in (False,True):
            engine=shared.Engine({"id":"F-zero","command":[str(program)],"profile":"shipping",
                                  "startup_threads":3,"max_threads":3,"startup_timeout":5,
                                  "expected_program_sha256":selected["whole_sha256"]},out,"eof" if eof else "quit",5)
            try:
                if engine.initialize()!=["uciok"]:raise AssertionError("minimal shipping UCI differs")
                proc=Path("/proc")/str(engine.process.pid);image=(proc/"exe").read_bytes();link=(proc/"exe").readlink()
                if sha(image)!=selected["native_sha256"]:raise AssertionError("actual restored image differs from cost native")
                native_path=Path(str(link).removesuffix(" (deleted)"))
                if not str(link).endswith(" (deleted)") or native_path.exists() or native_path.parent.exists():raise AssertionError("owned restoration path remains")
                children={str(tid):(proc/"task"/str(tid)/"children").read_text().split() for tid in engine.task_ids()}
                if any(children.values()):raise AssertionError("compiler helper remains at UCI-ready")
                row={"termination":"EOF" if eof else "quit","actual_native_sha256":sha(image),"startup_tids":sorted(engine.startup_task_ids),
                     "private_path_absent":True,"children_by_tid":children,"legal_clocked_moves":[]}
                for moves in ([],["e2e4"]):
                    board=shared.Board.from_fen()
                    for move in moves:board=board.play(move)
                    engine.position(moves=moves);engine.send("go wtime 0 btime 0")
                    lines=engine.until(lambda line:line.startswith("bestmove "),3);answers=[line.split()[1] for line in lines if line.startswith("bestmove ")]
                    if len(answers)!=1 or answers[0] not in {str(m) for m in board.legal_moves()}:raise AssertionError("clocked result is not exactly one legal move")
                    if engine.quiet(.03):raise AssertionError("duplicate or unexpected final output")
                    engine.assert_threads_stable();row["legal_clocked_moves"].append(answers[0])
                engine.position();board=shared.Board.from_fen();_,activity=shared.begin_lifecycle_search(engine,{"development":False})
                if not activity["active_before_signal"]:raise AssertionError("closing epoch was not observed active")
                engine.close(eof=eof)
                answers=[(stamp,line) for stamp,line in engine.stdout_events if stamp>=activity["go_posted_seconds"] and line.startswith("bestmove ")]
                if len(answers)!=1 or answers[0][1].split()[1] not in {str(m) for m in board.legal_moves()}:raise AssertionError("closing epoch lost/duplicated/invalid witness")
                if any(reader.is_alive() for reader in engine.readers) or proc.exists():raise AssertionError("physical process/readers did not finish")
                row.update(activity=activity,cancellation_causality="unproven",exactly_one_closing_bestmove=True,
                           process_absent=True,readers_finished=True,returncode=engine.process.returncode)
                report["fresh_sessions"].append(row);save()
            finally:
                if engine.process.poll() is None:engine.terminate()
        report.update(complete=True,shipping_window_cases=len(cases),real_mtd_witness_cases=12,physical_sessions=2)
        save();print(json.dumps({"complete":True,"window_cases":len(cases),"comparisons":len(report["comparisons"]),"physical_sessions":2}),flush=True)
    except Exception as error:report["error"]=repr(error);save();raise


if __name__=="__main__":main()
