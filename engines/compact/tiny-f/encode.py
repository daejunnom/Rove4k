#!/usr/bin/env python3
"""Two bounded TinyF encodings, admitted by full stripped native identity.

This is secondary to the F source design: no algorithm or bootstrap operation
is removed. The fixed profile and predetermined function spellings are rendered
more compactly only when this exact compiler produces the same entire ELF.
"""
import argparse
import ast
import hashlib
import importlib.util
import itertools
import json
import lzma
from pathlib import Path
import re
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def sha(data):return hashlib.sha256(data).hexdigest()


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


def argv_argument(script):
    matches=[node.args[0] for node in ast.walk(ast.parse(script)) if isinstance(node,ast.Call)
             and isinstance(node.func,ast.Attribute) and node.func.attr=="Popen"
             and isinstance(node.func.value,ast.Name) and node.func.value.id=="subprocess"]
    if len(matches)!=1:raise ValueError("one compiler Popen required")
    return matches[0]


def compact_argv(script,command):
    node=argv_argument(script)
    if ast.literal_eval(node)!=command:raise ValueError("compiler argv expression changed")
    if any(any(char.isspace() for char in arg) for arg in command):raise ValueError("fixed argv cannot contain whitespace")
    starts=[0]+[match.end() for match in re.finditer(b"\n",script)]
    begin=starts[node.lineno-1]+node.col_offset;end=starts[node.end_lineno-1]+node.end_col_offset
    expression=repr(" ".join(command))+".split()"
    result=script[:begin]+expression.encode()+script[end:]
    actual=argv_argument(result)
    if not (isinstance(actual,ast.Call) and isinstance(actual.func,ast.Attribute)
            and actual.func.attr=="split" and isinstance(actual.func.value,ast.Constant)
            and not actual.args and not actual.keywords and actual.func.value.value.split()==command):
        raise ValueError("compact compiler argv changed")
    return result


def fixed_source(source,lexer,profile):
    text=source.decode();counts={name:0 for name in profile};pieces=[];previous=0
    for begin,end,token in lexer._identifier_spans(text):
        if token in profile:
            pieces.extend((text[previous:begin],str(profile[token])));previous=end;counts[token]+=1
    pieces.append(text[previous:])
    if not all(counts.values()):raise ValueError("fixed resource tokens missing")
    changed={"main.c":"".join(pieces).encode()}
    names=("attacked","make","think","value","start","dead","mix","gen","now","search","probe","capture",
           "claim","learn","piece_index","quiet_score","first","parse","go","result","read_line","set_position",
           "number","work","wait","clear","text","rights","piece","state","ep","put","walk","add")
    used=set(re.findall(r"[A-Za-z_$][A-Za-z_0-9$]*",changed["main.c"].decode()))
    fresh=(a+b for a,b in itertools.product("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",repeat=2));mapping={}
    for name in names:
        if name not in used:continue
        alias=next(item for item in fresh if item not in used);used.add(alias)
        changed=lexer._replace(changed,name,alias);mapping[name]=alias
    return changed["main.c"],{"fixed_profile":profile,"resource_token_counts":counts,"function_spellings":mapping}


def execute(args):
    frozen=args.out/"frozen";inputs=json.loads((frozen/"inputs.json").read_text())
    if set(inputs)!={"encode.py","rename_c.py","pack_stream.py","compiler_group.py","main.c","input-build.json"}:
        raise ValueError("unknown frozen encoding input set")
    for name,digest in inputs.items():
        if sha((frozen/name).read_bytes())!=digest:raise ValueError("frozen encoding input changed: "+name)
    source=(frozen/"main.c").read_bytes();build=json.loads((frozen/"input-build.json").read_text())
    owner=module("tiny_f_encoding_compiler_group",frozen/"compiler_group.py")
    stream=module("tiny_f_encoding_stream",frozen/"pack_stream.py");lexer=module("tiny_f_encoding_lexer",frozen/"rename_c.py")
    flags=build["fixed_flags"];profile={name:int(next(flag.split("=",1)[1] for flag in flags if flag.startswith("-D"+name+"=")))
                                          for name in ("WORKERS","TT_BITS","PLY")}
    expected=["-std=c11","-Os","-pthread",*("-D"+name+"="+str(value) for name,value in profile.items())]
    if flags!=expected:raise ValueError("unknown TinyF fixed flags")
    command=[args.cc,*flags,"-DDEV=0","-x","c","-","-o","x","-s"]
    directory=args.out/"native";directory.mkdir()
    def compile_source(content,argv,label):
        result=subprocess.run(argv,cwd=directory,input=content,capture_output=True,timeout=60)
        if result.returncode:raise RuntimeError(result.stderr.decode(errors="replace"))
        binary=(directory/"x").read_bytes();(directory/(label+".elf")).write_bytes(binary)
        return {"command":argv,"bytes":len(binary),"sha256":sha(binary)}
    reference=compile_source(source,command,"reference")
    changed,policy=fixed_source(source,lexer,profile)
    reduced=[args.cc,"-Os","-pthread","-x","c","-","-o","x","-s"]
    actual=compile_source(changed,reduced,"fixed")
    if actual["sha256"]!=reference["sha256"]:raise RuntimeError("fixed encoding changed complete stripped native bytes")
    (frozen/"fixed-main.c").write_bytes(changed)
    script,kind=stream.bootstrap(changed,reduced);script=compact_argv(script,reduced)
    old_script=script
    script,_ownership=owner.transform_bootstrap(script)
    (frozen/"bootstrap.py").write_bytes(script)
    old=stream.bootstrap
    stream.bootstrap=lambda content,argv:(old_script,"tiny-f-fixed-representation")
    artifacts=stream.write_stream(changed,args.out/"packed",reduced,compiler_group=owner.transform_bootstrap)
    repeated=stream.write_stream(changed,args.out/"repeated",reduced,compiler_group=owner.transform_bootstrap)
    for first,second in zip(artifacts,repeated):
        if Path(first["path"]).read_bytes()!=Path(second["path"]).read_bytes():raise RuntimeError("whole-file encoding reproduction differs")
        first["reproduced"]=True
    stream.bootstrap=old
    baseline=next(record for record in artifacts if record["codec"]=="xz")
    data=Path(baseline["path"]).read_bytes();offset=data.index(b"\xfd7zXZ\0");prefix=data[:offset]
    if lzma.decompress(data[offset:])!=script:raise ValueError("encoded source/bootstrap restoration changed")
    encoded=lzma.compress(script,format=lzma.FORMAT_XZ,check=lzma.CHECK_CRC64,
                          filters=[{"id":lzma.FILTER_LZMA2,"preset":9|lzma.PRESET_EXTREME,"lc":2,"lp":0,"pb":0}])
    second=lzma.compress(script,format=lzma.FORMAT_XZ,check=lzma.CHECK_CRC64,
                         filters=[{"id":lzma.FILTER_LZMA2,"preset":9|lzma.PRESET_EXTREME,"lc":2,"lp":0,"pb":0}])
    if encoded!=second or lzma.decompress(encoded)!=script:raise RuntimeError("bounded XZ repetition/restoration differs")
    if subprocess.check_output(["xz","-dc"],input=encoded)!=script:raise RuntimeError("external xz restoration differs")
    alternative=prefix+encoded;path=args.out/"xz-lc2-pb0/x";path.parent.mkdir();path.write_bytes(alternative);path.chmod(0o755)
    artifacts.append({**baseline,"path":str(path),"bytes":len(alternative),"payload_bytes":len(encoded),"sha256":sha(alternative),
                      "xz_parameters":{"lc":2,"lp":0,"pb":0,"preset":"9e","check":"CRC64"},"reproduced":True})
    selected=min(artifacts,key=lambda item:item["bytes"])
    report={"passed":True,"scope":"local native-identity-gated representation; no source policy removal or 4K eligibility claim",
            "input_hashes":inputs,"input_source_sha256":sha(source),"transformed_source_sha256":sha(changed),
            "transformed_source_bytes":len(changed),"representation":policy,"reference_native":reference,"actual_native":actual,
            "compiler":subprocess.check_output([args.cc,"--version"],text=True).splitlines()[0],"bootstrap_sha256":sha(script),
            "bootstrap_operations":"compiler-group settlement before reap; preserved command/source/private TMPDIR/fd-exec",
            "artifacts":artifacts,"selected":selected,"eligible_4k":selected["bytes"]<=4096,"runtime_qualified":False}
    (args.out/"results.json").write_text(json.dumps(report,indent=2)+"\n")
    validation={"engines":[{"id":"tiny-F-encoding-selected","profile":"shipping","command":[selected["path"]],
                             "cwd":str(Path(selected["path"]).parent),"workers":profile["WORKERS"],
                             "startup_threads":profile["WORKERS"]+1,"startup_timeout":60,"expected_program_sha256":selected["sha256"]}]}
    (args.out/"validation-manifest.json").write_text(json.dumps(validation,indent=2)+"\n")
    print(json.dumps({"selected_bytes":selected["bytes"],"sha256":selected["sha256"],"native_identity":actual,
                      "eligible_4k":report["eligible_4k"]}),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--cc",default="cc")
    parser.add_argument("--execute-frozen",action="store_true",help=argparse.SUPPRESS)
    args=parser.parse_args()
    if not args.out.is_absolute():parser.error("absolute external output required")
    if args.execute_frozen:
        if HERE!=args.out/"frozen":parser.error("frozen encoding must run from its owned recipe")
        execute(args);return
    if args.out.exists() or ROOT==args.out or ROOT in args.out.parents:parser.error("new external output required")
    build_data=args.build.read_bytes();build=json.loads(build_data)
    record=next(record for record in build["engines"] if record["id"]=="tiny-F-compact")
    source=(Path(record["cwd"])/"main.c").read_bytes()
    if sha(source)!=record["source_sha256"]:parser.error("build compact source changed")
    files={"encode.py":Path(__file__).read_bytes(),"rename_c.py":(ROOT/"engines/scripts/rename_c.py").read_bytes(),
           "pack_stream.py":(ROOT/"engines/compact/tiny-a/pack_stream.py").read_bytes(),
           "compiler_group.py":(ROOT/"engines/scripts/compiler_group.py").read_bytes(),"main.c":source,"input-build.json":build_data}
    frozen=args.out/"frozen";frozen.mkdir(parents=True)
    for name,content in files.items():(frozen/name).write_bytes(content)
    (frozen/"inputs.json").write_text(json.dumps({name:sha(content) for name,content in files.items()},indent=2)+"\n")
    subprocess.run([sys.executable,"-I","-B",str(frozen/"encode.py"),*sys.argv[1:],"--execute-frozen"],check=True)


if __name__=="__main__":main()
