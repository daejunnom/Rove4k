#!/usr/bin/env python3
"""Prove exact admission and rejection of changed headers and image contents."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import build


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    if not args.out.is_absolute() or args.out.exists() or any((p/".git").exists() for p in (args.out.resolve(),*args.out.resolve().parents)):
        parser.error("--out must be new, absolute and outside Git")
    results=[]
    for form in build.INPUTS:
        original=(args.input_root/form/"x").read_bytes()
        admitted=build.admit(original,form)
        assert admitted["image_size"]==len(original)
        results.append({"form":form,"case":"exact-positive","passed":True})
        mutations={}
        for name,offset,value,fmt in (("writable-code",68,7,"I"),("nonzero-initialized-data",152,1,"Q"),
                                      ("different-entry",24,0x403000,"Q"),("unexpected-segment",64,7,"I")):
            data=bytearray(original);struct.pack_into("<"+fmt,data,offset,value);mutations[name]=bytes(data)
        data=bytearray(original);data[-1]^=1;mutations["same-layout-content-drift"]=bytes(data)
        mutations["truncated-image"]=original[:-1]
        for case,data in mutations.items():
            try: build.admit(data,form)
            except ValueError as error: results.append({"form":form,"case":case,"passed":True,"rejection":str(error)})
            else: raise AssertionError("unadmitted image accepted: "+case)
    args.out.mkdir(parents=True)
    report={"passed":True,"cases":len(results),"test_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"results":results}
    (args.out/"results.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"passed":True,"cases":len(results)}))


if __name__=="__main__":main()
