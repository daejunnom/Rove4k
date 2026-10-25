#!/usr/bin/env python3
"""One fixed F zero-window cost, with the exact 5479-byte control first.

All generation uses this folder's pinned control closure, copied to the owned
external output before loading helpers. No maintained entry or old build output
is consulted. The candidate is independently generated twice, with fixed names,
compiler flags, resources, bootstrap and XZ settings.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
import lzma
import os
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
sys.dont_write_bytecode=True


def sha(data):return hashlib.sha256(data).hexdigest()


def normalized(path):
    data=path.read_bytes().replace(b"\r\n",b"\n")
    if b"\r" in data:raise ValueError("lone CR in owned text: "+str(path))
    return data


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result);return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve()
    if not args.out.is_absolute() or out.exists() or REPO==out or REPO in out.parents:
        parser.error("new absolute external output required")
    pins=json.loads((HERE/"control/inputs.json").read_text())
    # Only named, owned C/producer inputs are admitted. No arbitrary paths.
    names={"engine.c","recipe.json","bootstrap.py.in","launcher.sh","upstream-build.py",
           "specialize.py","minify.py","rename_c.py","overlay.py","pack_stream.py"}
    if set(pins)!=names:raise ValueError("pinned control closure changed")
    out.mkdir(parents=True);frozen=out/"inputs";frozen.mkdir()
    inputs={}
    for name,expected in pins.items():
        data=normalized(HERE/"control"/name)
        if sha(data)!=expected:raise ValueError("owned control drift: "+name)
        (frozen/name).write_bytes(data);inputs[name]=sha(data)
    for name in ("cost.py","transform.py"):
        data=normalized(HERE/name);(frozen/name).write_bytes(data);inputs[name]=sha(data)
    (frozen/"inputs.json").write_text(json.dumps(inputs,indent=2)+"\n")
    specialize=module("zero_f_specialize",frozen/"specialize.py").specialize_c
    compact=module("zero_f_minify",frozen/"minify.py").compact_source
    control_strip=module("zero_f_old_counter",frozen/"overlay.py").strip_counters
    lexer=module("zero_f_names",frozen/"rename_c.py")
    literal=module("zero_f_literal",frozen/"pack_stream.py").source_literal
    transform=module("zero_f_transform",frozen/"transform.py")
    recipe=json.loads((frozen/"recipe.json").read_text());control=(frozen/"engine.c").read_bytes()
    candidate,policy=transform.transform(control)
    template=(frozen/"bootstrap.py.in").read_bytes();prefix=(frozen/"launcher.sh").read_bytes()
    report={"complete":False,"scope":"ONE fixed source-axis candidate; no runtime/strength/performance claim",
            "inputs":inputs,"policy":policy,"control_expected":recipe["expected"],"forms":[],"tools":{
                "cc":subprocess.check_output(["cc","--version"],text=True).splitlines()[0],
                "python":sys.version.splitlines()[0],"xz":subprocess.check_output(["xz","--version"],text=True).splitlines()[0]}}
    def save():(out/"cost.json").write_text(json.dumps(report,indent=2)+"\n")
    def generate(readable,directory,kind):
        directory.mkdir();(directory/"engine.c").write_bytes(readable)
        specialized,observations=specialize({"main.c":readable},directory/"preprocess",recipe["preprocessor"]+["-DDEV=0"],os.environ.copy())
        source=compact(specialized["main.c"],"c")
        source,counters=(control_strip(source) if kind=="control" else transform.strip_candidate(source))
        files={"main.c":source}
        for old,new in recipe["resource_literals"]:
            count=sum(token==old for _,_,token in lexer._identifier_spans(files["main.c"].decode()))
            if count!=recipe["resource_token_counts"][old]:raise ValueError("resource occurrence count changed: "+old)
            files=lexer._replace(files,old,new)
        for old,new in recipe["function_spellings"]:files=lexer._replace(files,old,new)
        source=files["main.c"];(directory/"main.c").write_bytes(source)
        (directory/"native").mkdir()
        process=subprocess.run(recipe["compiler"],input=source,cwd=directory/"native",capture_output=True,timeout=90)
        (directory/"compiler.stderr").write_bytes(process.stderr)
        if process.returncode:raise RuntimeError("compile failed: "+str(directory))
        native=(directory/"native/x").read_bytes()
        expression,_=literal(source);script=template.replace(b"__ROVE_SOURCE_LITERAL__",expression.encode());ast.parse(script)
        whole=prefix+lzma.compress(script,format=lzma.FORMAT_XZ,check=lzma.CHECK_CRC64,
                                  filters=[{"id":lzma.FILTER_LZMA2,"preset":9|lzma.PRESET_EXTREME,"lc":2,"lp":0,"pb":0}])
        if lzma.decompress(whole[len(prefix):])!=script:raise ValueError("complete wrapper did not restore bootstrap")
        (directory/"bootstrap.py").write_bytes(script);(directory/"x").write_bytes(whole);(directory/"x").chmod(0o755)
        record={"kind":kind,"directory":str(directory),"readable_bytes":len(readable),"readable_sha256":sha(readable),
                "source_bytes":len(source),"source_sha256":sha(source),"native_bytes":len(native),"native_sha256":sha(native),
                "whole_bytes":len(whole),"whole_sha256":sha(whole),"bootstrap_sha256":sha(script),
                "compiler":recipe["compiler"],"counters":counters,"preprocessor":observations}
        report["forms"].append(record);save()
        return source,native,whole,script
    save()
    try:
        old=generate(control,out/"control","control")
        expected=recipe["expected"]
        for content,kind in zip(old,("source","native","whole","bootstrap")):
            if sha(content)!=expected[kind+"_sha256"]:raise ValueError("control does not reproduce qualified "+kind)
        if len(old[2])!=5479:raise ValueError("control is not the exact 5479-byte file")
        first=generate(candidate,out/"candidate-1","candidate")
        second=generate(candidate,out/"candidate-2","candidate")
        if first!=second:raise ValueError("independent candidate generation differs")
        report.update(complete=True,candidate_reproduced=True,control_exact=True,
                      delta_complete_bytes=len(first[2])-len(old[2]),runtime_executed=False,
                      proceed_to_focused_runtime=len(first[2])<len(old[2]))
        save();print(json.dumps({key:report[key] for key in ("complete","control_exact","candidate_reproduced","delta_complete_bytes","proceed_to_focused_runtime")}),flush=True)
        print(json.dumps([{key:record[key] for key in ("kind","source_bytes","native_bytes","whole_bytes","whole_sha256")} for record in report["forms"]]),flush=True)
    except Exception as error:report["error"]=repr(error);save();raise


if __name__=="__main__":main()
