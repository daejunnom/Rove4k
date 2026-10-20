#!/usr/bin/env python3
"""Index completed cold pairs without rewriting failed source campaigns.

Q1's false/timeout status and unpaired/failed attempts stay separate. An index
can complete declared pair coverage while its original campaigns retain their
own outcomes. It never turns a partial source campaign into a success.
"""
import argparse
import hashlib
import json
from pathlib import Path
import statistics


def require(condition,message):
    if not condition:raise AssertionError(message)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign",type=Path,action="append",required=True)
    parser.add_argument("--invariance",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    require(not args.out.exists(),"index output must be a new file")
    report={"schema":1,"scope":"bounded matched E completed pairs; no causal language/NPS/strength claim",
            "producer_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "source_campaigns":[],"pairs":[],"excluded_attempts":[],"coverage_complete":False}
    proof=json.loads(args.invariance.read_text())
    require(proof.get("frozen_input_metadata_identical"),"frozen input identity proof missing")
    core=proof.get("core_functions",{})
    require(len(core)==9 and all(item.get("identical")and item["before_sha256"]==item["after_sha256"]for item in core.values()),"measurement core-function invariance not proved")
    report["invariance_proof"]={"path":str(args.invariance),"sha256":hashlib.sha256(args.invariance.read_bytes()).hexdigest(),"data":proof}
    seen={};baseline=None
    for path in args.campaign:
        data=json.loads(path.read_text())
        if data["quiet_window"].endswith("Q1"):
            require(hashlib.sha256(path.read_bytes()).hexdigest()==proof["q1_immutable_report_sha256"],"original Q1 report was changed")
            require(data["passed"]is False,"original partial Q1 outcome changed")
            require(proof["q1_helper_sha256"]in data["helper_sha256"].values(),"Q1 helper identity mismatch")
        else:
            require(data["passed"]is True,"completion campaign did not pass")
            require(proof["q2_helper_sha256"]in data["helper_sha256"].values(),"Q2 helper identity mismatch")
        identity={key:data[key]for key in("manifests","affinity","native_environment","host")}
        require(baseline is None or baseline==identity,"runtime/source/native/resource identity changed across campaigns")
        baseline=identity
        campaign={"id":data["quiet_window"],"path":str(path),"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
                  "original_passed":data["passed"],"original_error":data.get("error"),
                  "helper_sha256":data["helper_sha256"],"invocation":data.get("invocation"),
                  "started_utc":data.get("campaign_started_utc"),"ended_utc":data.get("campaign_ended_utc")}
        report["source_campaigns"].append(campaign)
        for index,pair in enumerate(data["samples"]):
            pointer={"campaign":campaign["id"],"source_path":str(path),"json_pointer":"/samples/"+str(index)}
            records=pair.get("records",[])
            if not pair.get("passed")or len(records)!=2 or not all(r.get("passed")for r in records):
                successful=[r for r in records if r.get("passed")]
                missing=[engine for engine in pair["order"]if engine not in[r["engine"]for r in records]]
                report["excluded_attempts"].append({**pointer,"workers":pair["workers"],"case":pair["case"],"sample":pair["sample"],
                    "successful_unpaired_records":successful,"not_completed_engines":missing,
                    "not_completed_transcripts":[str(path.parent/f"w{pair['workers']}-{pair['case']}-s{pair['sample']}-{engine}.jsonl")for engine in missing],
                    "failure":data.get("error"),"reason":"source pair incomplete; excluded from every paired summary"})
                continue
            key=(pair["workers"],pair["case"],pair["sample"])
            require(key not in seen,"duplicate global sample index "+str(key))
            require({r["engine"]for r in records}=={"E-c","E-rust"},"pair lacks one language")
            require(pair.get("semantic_gate",{}).get("passed"),"semantic gate not proved")
            seen[key]=pointer
            report["pairs"].append({**pointer,**pair})
    expected={(workers,case,sample)for workers in(1,4)for case in("start","opening","kiwipete")for sample in range(3)}
    require(set(seen)==expected,"completed pair coverage differs from declared 18 samples")
    summaries=[]
    for workers in(1,4):
        for case in("start","opening","kiwipete"):
            for engine in("E-c","E-rust"):
                records=[r for p in report["pairs"]if p["workers"]==workers and p["case"]==case for r in p["records"]if r["engine"]==engine]
                row={"workers":workers,"case":case,"engine":engine,"paired_samples":len(records)}
                for metric in("search_wall_seconds","search_cpu_seconds","nodes_per_wall_second"):
                    values=[r["measurement"][metric]for r in records]
                    row[metric]={"median":statistics.median(values),"minimum":min(values),"maximum":max(values)}
                row["actual_nodes"]=[r["actual_nodes"]for r in records]
                row["startup_wall_seconds"]=[r["startup"]["launch_to_ready_wall_seconds"]for r in records]
                row["cpu_quantization_seconds"]=[r["measurement"]["cpu_endpoint_quantization_bound_seconds"]for r in records]
                row["postsearch_memory"]=[r["postsearch"]["status"]for r in records]
                summaries.append(row)
    report.update({"coverage_complete":True,"valid_pairs":len(seen),"valid_paired_runs":sum(len(p["records"])for p in report["pairs"]),
                   "successful_unpaired_runs":sum(len(a["successful_unpaired_records"])for a in report["excluded_attempts"]),
                   "not_completed_engine_attempts":sum(len(a["not_completed_engines"])for a in report["excluded_attempts"]),
                   "summaries":summaries,"runtime_identity":baseline})
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+"\n")
    print("indexed18 validpairs/36 pairedruns; source campaign outcomes preserved")
    return 0


if __name__=="__main__":raise SystemExit(main())
