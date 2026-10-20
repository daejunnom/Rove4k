#!/usr/bin/env python3
"""Freeze and compile independent no_std Rust D; never execute the ELF.

The complete ELF is the measured native artifact. No existing compressed-image
loader is invoked or assigned to this new image class.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import struct
import subprocess
import sys

HERE=Path(__file__).resolve().parent
FILES=("main.rs","board.rs","search.rs","runtime.rs","os.rs","link.ld","build.py")
def sha(data):return hashlib.sha256(data).hexdigest()
def save(path,value):path.write_text(json.dumps(value,indent=2)+"\n")
def allocated(image):
    offset=struct.unpack_from("<Q",image,40)[0]
    size,count,names_index=struct.unpack_from("<HHH",image,58)
    headers=[struct.unpack_from("<IIQQQQIIQQ",image,offset+i*size)for i in range(count)]
    h=headers[names_index];names=image[h[4]:h[4]+h[5]]
    return {(names[h[0]:names.index(b"\0",h[0])].decode(),h[3]):
        (h[1],h[5],image[h[4]:h[4]+h[5]]if h[1]!=8 else b"")for h in headers if h[2]&2}
def run(command,cwd,environment):
    p=subprocess.run(command,cwd=cwd,env=environment,capture_output=True,text=True,timeout=120)
    record={"command":command,"cwd":str(cwd),"returncode":p.returncode,"stdout":p.stdout,"stderr":p.stderr}
    if p.returncode:raise RuntimeError(record)
    return record
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--out",required=True,type=Path)
    ap.add_argument("--rustc",default="rustc");ap.add_argument("--workers",type=int,default=2)
    ap.add_argument("--tt-bits",type=int,default=18);ap.add_argument("--hq",choices=("scalar","hq"),default="hq")
    ap.add_argument("--reproduce",action="store_true");a=ap.parse_args()
    root=HERE.parents[2];out=a.out.resolve()
    if sys.platform!="linux" or platform.machine().lower() not in ("x86_64","amd64"):ap.error("Linux x86-64 required")
    if not a.out.is_absolute() or out.exists() or out==root or root in out.parents:ap.error("new absolute external output required")
    if not 1<=a.workers<=512 or not 8<=a.tt_bits<=26:ap.error("workers1..512, TTbits8..26")
    compiler=shutil.which(a.rustc)
    if not compiler:ap.error("Rust compiler unavailable")
    sources={name:(HERE/name).read_bytes()for name in FILES};out.mkdir()
    fixed={"ROVE_WORKERS":str(a.workers),"ROVE_TT_BITS":str(a.tt_bits),"ROVE_HQ":str(int(a.hq=="hq")),"LC_ALL":"C","TZ":"UTC","SOURCE_DATE_EPOCH":"0"}
    env=os.environ.copy();env.update(fixed)
    flags=["--edition=2024","-C","opt-level=z","-C","lto=fat","-C","codegen-units=1","-C","panic=abort",
        "-C","force-unwind-tables=no","-C","relocation-model=static","-C","default-linker-libraries=no",
        "-C","debuginfo=0","-C","strip=symbols","--check-cfg","cfg(tiny_dev)","--check-cfg","cfg(tiny_shipping)","--cfg","tiny_shipping",
        "-C","link-arg=-nostdlib","-C","link-arg=-static","-C","link-arg=-no-pie",
        "-C","link-arg=-Wl,--build-id=none","-C","link-arg=-Wl,--no-dynamic-linker","-C","link-arg=-Wl,-T,link.ld",
        "--crate-name","rove4k_tiny_d","main.rs","-o","x"]
    builds=[]
    for label in (("first","repeat")if a.reproduce else("first",)):
        local=out/label;local.mkdir()
        for name,data in sources.items():(local/name).write_bytes(data)
        command=[compiler,"--remap-path-prefix",str(local)+"=.",*flags]
        record=run(command,local,env);image=(local/"x").read_bytes();assert image[:6]==b"\x7fELF\x02\x01"
        record.update(bytes=len(image),sha256=sha(image),path=str(local/"x"));builds.append(record)
    if a.reproduce and Path(builds[0]["path"]).read_bytes()!=Path(builds[1]["path"]).read_bytes():raise RuntimeError("independent native bytes differ")
    # A stripped symbol table is insufficient evidence for no unresolved
    # runtime. Inspect an auxiliary unstripped link and prove all allocatable
    # sections, including addresses and BSS sizes, match the selected ELF.
    audit_command=["strip=none"if part=="strip=symbols"else part for part in builds[0]["command"]]
    audit_command[-1]="x.unstripped"
    audit=run(audit_command,out/"first",env)
    unstripped=out/"first/x.unstripped"
    undefined=run(["nm","-u",str(unstripped)],out,env)
    defined=run(["nm","--defined-only",str(unstripped)],out,env)
    (out/"unstripped-defined.txt").write_text(defined["stdout"])
    audit.update(path=str(unstripped),sha256=sha(unstripped.read_bytes()),undefined_symbols=undefined["stdout"],
        allocatable_sections_identical=allocated(Path(builds[0]["path"]).read_bytes())==allocated(unstripped.read_bytes()))
    native=builds[0]["path"];checks={}
    for label,command in (("program_headers",["readelf","-lW",native]),("dynamic",["readelf","-dW",native]),
                         ("sections",["readelf","-SW",native]),("undefined",["nm","-u",native]),("disassembly",["objdump","-d",native])):
        r=run(command,out,env);(out/(label+".txt")).write_text(r["stdout"]);checks[label]=r["stdout"]
    gates={"no_interpreter":"INTERP" not in checks["program_headers"],"no_tls_segment":" TLS " not in checks["program_headers"],
           "no_dynamic_dependencies":"NEEDED" not in checks["dynamic"],"no_undefined_symbols":not undefined["stdout"].strip(),
           "unstripped_audit_load_image_identical":audit["allocatable_sections_identical"],
           "no_unwind_sections":not re.search(r"\.(eh_frame|gcc_except_table)",checks["sections"]),
           "no_fs_gs_memory_operands":not re.search(r"%[fg]s:",checks["disassembly"]),
           "non_executable_stack":bool(re.search(r"GNU_STACK.* RW ",checks["program_headers"]))}
    report={"scope":"independent no_std Rust D first native build only","executed":False,"architecture_review_required_before_runtime":True,
        "source_sha256":{n:sha(d)for n,d in sources.items()},"source_bytes":sum(len(d)for n,d in sources.items()if n.endswith(".rs")),
        "workers":a.workers,"tt_bits":a.tt_bits,"hq":a.hq,"startup_threads":a.workers+1,"compiler_environment":fixed,
        "compiler":run([compiler,"--version","--verbose"],out,env)["stdout"],"builds":builds,"unstripped_audit":audit,"reproduced":a.reproduce,"artifact_gates":gates,
        "complete_native_bytes":builds[0]["bytes"],"complete_native_sha256":builds[0]["sha256"],
        "under_4096_bytes":builds[0]["bytes"]<=4096,"compressed_loader_admitted":False,"rules_eligibility":"unproven",
        "validation_performed":["compile/link","independent bytes if requested","static ELF inspection"],
        "validation_not_performed":["startup","clone/futex/join","UCI","board/HQ oracle","search contracts","deep stack","faults","performance"]}
    save(out/"build.json",report)
    if not all(gates.values()):raise RuntimeError("ELF artifact gate failed: "+str(gates))
    print(json.dumps({"out":str(out),"native_bytes":builds[0]["bytes"],"sha256":builds[0]["sha256"],"artifact_gates":gates,"executed":False}))
if __name__=="__main__":main()
