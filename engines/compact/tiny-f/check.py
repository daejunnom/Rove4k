#!/usr/bin/env python3
"""Independent exact-score/attaining-witness checks for actual TinyF binaries.

The quiet fixtures deliberately have no capture or check at their frontier.
Consequently independent full minimax equals this engine's full-depth QS score.
No TinyF search/TT or board helper is imported into the oracle.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/"engines/tests"))
from chess_oracle import Board
from verify import Engine,parse_info,require

QUIET=("8/6pk/8/8/8/8/PK6/8 w - - 0 1",
       "8/6pk/8/8/8/P7/1K6/8 b - - 0 1",
       "8/7k/6p1/8/8/P7/1K6/8 w - - 0 1")


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def evaluate(board):
    material={"p":100,"n":320,"b":330,"r":500,"q":900,"k":0}
    score=0
    for square,piece in enumerate(board.cells):
        if piece==".":continue
        rank,file=divmod(square,8);kind=piece.lower()
        advance=rank if piece.isupper() else 7-rank
        center=7-abs(2*file-7)-abs(2*rank-7)
        position={"p":advance*7+center*2,"n":center*9,"b":center*5,
                  "r":advance*2,"q":center*2,"k":-center*3}[kind]
        score+=(1 if piece.isupper() else -1)*(material[kind]+position)
    return score*(1 if board.turn else -1)


def minimax(board,depth,ply=0):
    moves=list(board.legal_moves())
    if not moves:return -30000+ply if board.in_check() else 0
    if depth==0:
        require(not board.in_check(),"independent frontier is in check")
        require(all(board.cells[m.dst]=="." and not m.promotion and
                    not(board.cells[m.src].lower()=="p" and m.dst==board.ep)
                    for m in moves),"independent frontier has a capture/promotion")
        return evaluate(board)
    return max(-minimax(board.apply(move),depth-1,ply+1) for move in moves)


def search(engine,board,command):
    engine.send(command)
    lines=engine.until(lambda line:line.startswith("bestmove "))
    moves=[line.split()[1] for line in lines if line.startswith("bestmove ")]
    require(len(moves)==1,"one result per accepted search")
    require(moves[0] in {str(move) for move in board.legal_moves()},"illegal result")
    info=parse_info(lines,board)
    require(len(info)==1,"TinyF reports one final completed iteration")
    require(not any(line.startswith("bestmove ") for line in engine.quiet()),"duplicate result")
    engine.assert_threads_stable()
    stats=engine.stats()
    require(stats["f_conflicts"]==0,"actual MTD bound conflict")
    return {"command":command,"bestmove":moves[0],"info":info[-1],"stats":stats}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    require(args.out.is_absolute() and not args.out.exists(),"new absolute external output directory required")
    require(ROOT!=args.out and ROOT not in args.out.parents,"reports stay outside checkout")
    args.out.mkdir(parents=True)
    manifest=json.loads(args.manifest.read_text())
    spec=next(record for record in manifest["engines"] if record["id"]=="tiny-F-dev")
    engine=Engine(spec,args.out,"tiny-F-dev",15)
    report={"passed":False,"artifact_sha256":digest(spec["command"][0]),
            "test_source_sha256":digest(__file__),"oracle_source_sha256":digest(ROOT/"engines/tests/chess_oracle.py"),
            "cases":[],"scope":"correctness; no timing, scaling, rating or strength inference"}
    try:
        engine.initialize()
        for index,fen in enumerate(QUIET):
            board=Board.from_fen(fen);engine.send("ucinewgame");engine.position(fen)
            for depth in (3,3,1,2):
                value=minimax(board,depth)
                result=search(engine,board,f"go depth {depth}")
                require(result["info"]["depth"]==depth and result["info"]["kind"]=="cp","requested iteration did not complete")
                require(result["info"]["score"]==value,"convergence differs from independent minimax")
                attained=-minimax(board.play(result["bestmove"]),depth-1,1)
                require(attained==value,"published lower-bound witness does not attain converged score")
                report["cases"].append({**result,"case":index,"expected":value,"attained":attained})
        engine.send("ucinewgame");engine.position();start=Board.from_fen()
        for _ in range(2):result=search(engine,start,"go depth 4")
        for field in ("pvs","qs","tt_hits","history_updates","continuation_updates","correction_updates","correction_uses",
                      "f_probes","f_lower","f_upper","f_converged"):
            require(result["stats"][field]>0,"unobserved actual feature: "+field)
        report["actual_features"]=result
        # A deliberately small node budget interrupts later probes. The C
        # contract additionally compares the exact saved depth/score/witness.
        engine.position()
        result=search(engine,start,"go nodes 1000 depth 30")
        require(0<result["info"]["depth"]<30,"node stop did not retain an earlier completed iteration")
        require(0<result["stats"]["nodes"]<=1000,"DEV shared node budget exceeded")
        report["cancellation"]=result
        scores=[]
        for fen in ("7k/8/8/8/8/8/1Q6/K7 w - - 99 1","7k/8/8/8/8/8/1Q6/K7 w - - 0 1"):
            board=Board.from_fen(fen);engine.position(fen)
            result=search(engine,board,"go depth 3");scores.append(result["info"]["score"])
        require(scores[0]==0 and scores[1]>0,"halfmove-context TT contamination")
        report["halfmove_context_scores"]=scores
        report["startup_task_ids"]=sorted(engine.startup_task_ids)
        report["passed"]=True
    finally:
        try:engine.close()
        finally:
            if engine.process.poll() is None:engine.terminate()
            (args.out/"results.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"passed":True,"independent_minimax_witness_cases":len(report["cases"]),
                      "actual_features":report["actual_features"]["stats"]}),flush=True)


if __name__=="__main__":main()
