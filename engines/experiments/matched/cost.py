#!/usr/bin/env python3
"""Shipping whole-file costs of the immutable matched E production overlay.

DEV timing artifacts are separate inputs/provenance, never relabeled shipping.
Only each role's actual minimum file is executed; every candidate is measured
and independently regenerated. No generic language effect is inferred.
"""
import argparse
import ast
import base64
import bz2
import hashlib
import importlib.util
import io
import json
import lzma
import os
from pathlib import Path
import shutil
import struct
import sys
import time
import zipfile
import zlib

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"engines/tests"))
from chess_oracle import Board
from verify import Engine,require,search


def sha(data):return hashlib.sha256(data).hexdigest()


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);sys.modules[name]=result;spec.loader.exec_module(result);return result


def payload_identity(path,record,files):
    """Decode actual selected launcher bytes without executing bootstrap code."""
    data=Path(path).read_bytes()
    if record["transport"]=="zip":
        with zipfile.ZipFile(io.BytesIO(data))as archive:
            require(sorted(archive.namelist())==["__main__.py","p"],"unexpected ZIP entries")
            raw=archive.read("p")
    else:
        tree=ast.parse(data.decode())
        assignments=[n for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=="b"for t in n.targets)]
        require(len(assignments)==1,"launcher payload assignment missing")
        expression=assignments[0].value
        require(isinstance(expression,ast.Call)and isinstance(expression.func,ast.Attribute)and expression.func.attr=="decompress","unsupported decoder expression")
        encoded=ast.literal_eval(expression.args[0].args[0])
        raw={"zlib":zlib.decompress,"bz2":bz2.decompress,"lzma":lzma.decompress}[record["codec"]](base64.b85decode(encoded))
    require(len(raw)>=4,"truncated archive")
    count=struct.unpack_from("<I",raw)[0];at=4;decoded={}
    for _ in range(count):
        require(at+6<=len(raw),"truncated member header")
        n,s=struct.unpack_from("<HI",raw,at);at+=6
        require(at+n+s<=len(raw),"truncated member")
        name=raw[at:at+n].decode();at+=n
        require(name not in decoded and not Path(name).is_absolute()and".."not in Path(name).parts,"unsafe member")
        decoded[name]=raw[at:at+s];at+=s
    require(at==len(raw)and decoded==files,"decoded file map differs from encoder input")
    return {"passed":True,"archive_sha256":sha(raw),"members":[{"path":n,"sha256":sha(d),"bytes":len(d)}for n,d in sorted(decoded.items())]}


def runtime(selected,label,out,workers,expected_native):
    spec={"id":label,"command":[selected["path"]],"profile":"shipping","startup_timeout":60,
          "startup_threads":workers+1}
    engine=Engine(spec,out,label,10);board=Board.from_fen()
    try:
        engine.initialize()
        image=sha((Path("/proc")/str(engine.process.pid)/"exe").read_bytes())
        if selected["role"]!="source-general":require(image==expected_native,"actual restored native bytes differ")
        engine.position();bounded=search(engine,board,"go wtime 1000 btime 1000 winc 0 binc 0",require_info=False)
        engine.position();zero=search(engine,board,"go wtime 0 btime 0 winc 0 binc 0",require_info=False)
        engine.position();engine.send("go wtime 600000 btime 600000 winc 0 binc 0");time.sleep(.04)
        before=engine.ready();require(not any(s.startswith("bestmove ")for s in before),"search ended before active stop")
        engine.send("stop");stopped=engine.until(lambda s:s.startswith("bestmove "))
        choices=[s.split()[1]for s in stopped if s.startswith("bestmove ")];require(len(choices)==1,"stop must emit one move");board.play(choices[0])
        require(not any(s.startswith("bestmove ")for s in engine.quiet()),"duplicate stopped move")
        engine.assert_threads_stable()
        engine.position();engine.send("go wtime 600000 btime 600000 winc 0 binc 0");time.sleep(.04)
        require(not any(s.startswith("bestmove ")for s in engine.ready()),"search ended before active quit")
        engine.close();final=[s.split()[1]for s in engine.drain()if s.startswith("bestmove ")]
        require(len(final)==1,"quit must emit one move");board.play(final[0])
        return {"passed":True,"runtime_image_sha256":image,"matches_host_native":image==expected_native,
                "clocked":bounded["bestmove"],"zero_clock":zero["bestmove"],"active_stop":choices[0],"active_quit":final[0],
                "startup_threads":sorted(engine.startup_task_ids or())}
    finally:
        if engine.process.poll()is None:engine.terminate()
        elif not engine.log.closed:engine.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest",action="append",type=Path,required=True,help="stable DEV generation manifests, workers1 and4")
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--cc",default="cc")
    parser.add_argument("--rustc",default="rustc")
    args=parser.parse_args();out=args.out.resolve()
    require(not out.exists()and not out.is_relative_to(ROOT),"output must be new and outside repository");out.mkdir(parents=True)
    recipe=out/"recipe";helpers={}
    for path in sorted((ROOT/"engines/scripts").rglob("*")):
        if path.is_file()and path.suffix in(".py",".c",".ld"):
            relative=path.relative_to(ROOT);data=path.read_bytes();target=recipe/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            helpers[str(relative)]={"sha256":sha(data),"bytes":len(data)}
    sys.path.insert(0,str(recipe/"engines/scripts"))
    build=module("matched_cost_build",recipe/"engines/scripts/build.py")
    pack=module("matched_cost_pack",recipe/"engines/scripts/pack.py")
    elf=module("matched_cost_elf",recipe/"engines/scripts/elf_loader.py")
    minify=module("matched_cost_minify",recipe/"engines/scripts/minify.py")
    specialize=module("matched_cost_specialize",recipe/"engines/scripts/specialize.py")
    compiler_dirs=[str(Path(shutil.which(tool)or tool).resolve().parent)for tool in(args.cc,args.rustc)]
    # rustup shims need their requested directory, rather than just resolved
    # executable parent; no credential/configuration file is read.
    compiler_dirs+=[str(Path(tool).parent)for tool in(args.cc,args.rustc)if Path(tool).is_absolute()]
    os.environ["PATH"]=os.pathsep.join(compiler_dirs+[os.environ.get("PATH","")])
    report={"schema":1,"contract":"matched-c-policy-v1","producer_sha256":sha(Path(__file__).read_bytes()),
            "scope":"shipping whole-file costs; separate from DEV timing; no language-effect/NPS/strength claim",
            "helpers":helpers,"tools":{lang:{"requested":tool,"resolved":str(Path(shutil.which(tool)or tool).resolve()),"version":build.tool_version(tool)}for lang,tool in(("c",args.cc),("rust",args.rustc))},
            "engines":[],"complete":False}
    try:
        workers_seen=set()
        for manifest_path in args.manifest:
            manifest=json.loads(manifest_path.read_text());workers=manifest["policy"]["search_workers"]
            require(manifest["contract"]=="matched-c-policy-v1"and workers in(1,4)and workers not in workers_seen,"wrong/duplicate profile")
            workers_seen.add(workers)
            require(manifest["policy"]["tt_total_bytes"]==4194304 and manifest["policy"]["startup_tt_clear_prefault"],"resource contract drift")
            source={}
            for item in manifest["sources"]:
                data=(manifest_path.parent/"source"/item["path"]).read_bytes();require(sha(data)==item["sha256"],"frozen runtime bytes changed");source[item["path"]]=data
            profile={"search_workers":workers,"expected_total_threads":workers+1,"tt_bits":18,"development":False}
            for language in("c","rust"):
                base=out/(str(workers)+"-"+language)
                files={name:data for name,data in source.items()if name.startswith(language+"/")or name.startswith("model/")and name.endswith(".h"if language=="c"else".rs")}
                command,environment=build.compiler_recipe(language,"E",profile,"size",compiler=args.cc if language=="c"else args.rustc,files=files,parallel=0,c_lto=True,f_tt="single")
                # The general CLI correctly restricts F-specific switches. This
                # experiment directly selects its guarded, already proved E
                # single backend; it never changes or weakens that CLI guard.
                environment["ROVE_F_SINGLE"]="1"
                if language=="rust":command[1:1]=["--cfg","rove_f_single","--cfg","rove_matched_c_policy"]
                runtime_command=list(command);runtime_command[0]="cc"if language=="c"else"rustc"
                forms={"original":files,"lexical":{n:minify.compact_source(d,language)for n,d in files.items()}}
                if language=="c":
                    specialized,observations=specialize.specialize_c(files,base/"preprocessor",command,dict(os.environ,**environment))
                    forms["specialized"]={n:minify.compact_source(d,"c")for n,d in specialized.items()}
                entry={"workers":workers,"language":language,"development":False,"profile":profile,"configuration":environment,
                       "dev_provenance_manifest":str(manifest_path),"dev_provenance_sha256":sha(manifest_path.read_bytes()),
                       "command":command,"runtime_command":runtime_command,"compiler_recipe_f_tt":"single",
                       "sources":[{"path":n,"sha256":sha(d)}for n,d in sorted(files.items())],"artifacts":[],"selected":{}}
                report["engines"].append(entry)
                payloads={};elf_by_hash={}
                for form,inputs in forms.items():
                    native=build.compile_files(inputs,base/form,command,environment)
                    # Recreate the source transformation independently too.
                    if form=="original":again=files
                    elif form=="lexical":again={n:minify.compact_source(d,language)for n,d in files.items()}
                    else:
                        again,_=specialize.specialize_c(files,base/"preprocessor-repeat",command,dict(os.environ,**environment));again={n:minify.compact_source(d,"c")for n,d in again.items()}
                    require(again==inputs,"source transformation failed reproduction")
                    repeat=build.compile_files(again,base/(form+"-repeat"),command,environment)
                    require(native["sha256"]==repeat["sha256"],"independent shipping native differs")
                    native.update({"role":"native-elf","form":form,"reproduction_sha256":repeat["sha256"],"reproduced":True})
                    entry["artifacts"].append(native);payloads[native["path"]]={"native_sha256":native["sha256"]}
                    for role,encoded,compile_command in(("source-general",inputs,runtime_command),("native-general",{"x":Path(native["path"]).read_bytes()},None)):
                        records=pack.write_launchers(encoded,base/(form+"-"+role),command=compile_command,environment=environment if compile_command else None)
                        duplicates=pack.write_launchers(encoded,base/(form+"-"+role+"-repeat"),command=compile_command,environment=environment if compile_command else None)
                        for record,duplicate in zip(records,duplicates):
                            require(record["sha256"]==duplicate["sha256"],"independent whole-file launcher differs")
                            record.update({"role":role,"form":form,"reproduced":True,"reproduction_sha256":duplicate["sha256"]})
                            entry["artifacts"].append(record);payloads[record["path"]]={"files":encoded,"native_sha256":native["sha256"]}
                    if native["sha256"]not in elf_by_hash:
                        target=base/(form+"-own-elf")/"x"
                        packed=elf.pack_elf(native["path"],target,cc=args.cc,filter="auto")
                        duplicate=elf.pack_elf(repeat["path"],base/(form+"-own-elf-repeat")/"x",cc=args.cc,filter="auto")
                        require(packed["output_sha256"]==duplicate["output_sha256"],"independent own ELF differs")
                        packed.update({"path":packed["output"],"bytes":packed["output_bytes"],"sha256":packed["output_sha256"],"role":"own-elf","form":form,
                                       "reproduced":True,"reproduction_sha256":duplicate["output_sha256"]})
                        entry["artifacts"].append(packed);payloads[packed["path"]]={"native_sha256":native["sha256"]};elf_by_hash[native["sha256"]]=packed
                for role in("source-general","native-general","native-elf","own-elf"):
                    selected=min((a for a in entry["artifacts"]if a["role"]==role),key=lambda a:a["bytes"])
                    require(sha(Path(selected["path"]).read_bytes())==selected["sha256"],"selected file drift")
                    encoded=payloads[selected["path"]]
                    if"files"in encoded:selected["payload_identity"]=payload_identity(selected["path"],selected,encoded["files"])
                    else:selected["payload_identity"]={"native_input_sha256":encoded["native_sha256"],"actual_process_image_checked":True}
                    selected["runtime"]=runtime(selected,str(workers)+"-"+language+"-"+role,out,workers,encoded["native_sha256"])
                    entry["selected"][role]=selected
                    print(str(workers)+"-"+language+" "+role+": "+str(selected["bytes"])+"B reproduced/payload/runtime PASS",flush=True)
                (out/"cost.json").write_text(json.dumps(report,indent=2)+"\n")
        require(workers_seen=={1,4},"both one- and four-worker profiles are required")
        report["complete"]=True
    finally:(out/"cost.json").write_text(json.dumps(report,indent=2)+"\n")
    return 0


if __name__=="__main__":raise SystemExit(main())
