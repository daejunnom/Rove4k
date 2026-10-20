#!/usr/bin/env python3
"""Run unchanged search/board/OS bodies on a raw-clone guarded 1MiB stack.

This is an explicitly distinct no_std diagnostic ELF, not the shipping image.
The exact production search prefix receives one external qualification appendix.
There is no std allocator or allocating container in this image. A syscall
tracer may additionally verify that all mappings precede the deep-begin marker.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess

HERE=Path(__file__).resolve().parent
DRIVER=r'''#![no_std]
#![no_main]
mod board;mod search;mod os;
use core::sync::atomic::{AtomicI32,AtomicU32,Ordering};
pub const HQ:bool=ROVE_HQ;
static TID:AtomicI32=AtomicI32::new(0);
static DONE:AtomicU32=AtomicU32::new(0);
#[panic_handler]fn panic(_:&core::panic::PanicInfo)->!{os::fatal(134)}
#[unsafe(no_mangle)]extern "C" fn worker_entry(_:*mut u8){
 let mut worker=search::Worker::new(0);let table=search::Table::new(18);let control=search::Control::new();
 os::output(b"deep begin\n");
 let nodes=search::qualification_deep_path(&mut worker,&table,&control);
 assert!(nodes==128);os::output(b"deep nodes 128\n");
 DONE.store(1,Ordering::Release);os::wake(&DONE);
}
#[unsafe(no_mangle)]extern "C" fn engine_main()->!{
 let stack=os::stack();unsafe{os::spawn(stack,&TID,core::ptr::null_mut());}
 while DONE.load(Ordering::Acquire)==0{os::wait(&DONE,0);}
 os::join(&TID);unsafe{os::release(stack,os::STACK_MAP);}
 os::output(b"deep joined\n");os::fatal(0)
}
'''
def sha(x):return hashlib.sha256(x).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--build",type=Path,required=True);ap.add_argument("--out",type=Path,required=True);a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    initial={"passed":False,"phase":"source admission before compilation","runner_sha256":sha(Path(__file__).read_bytes()),"build":str(a.build)}
    (a.out/"report.json").write_text(json.dumps(initial,indent=2)+"\n")
    build=json.loads(a.build.read_text());snapshot=Path(build["builds"][0]["cwd"])
    files={n:(snapshot/n).read_bytes()for n in("board.rs","search.rs","os.rs","link.ld")}
    for n,data in files.items():assert sha(data)==build["source_sha256"][n],n
    test=(HERE/"tests/search.rs").read_bytes();start=b"// RAW_DEEP_BEGIN";end=b"// RAW_DEEP_END"
    assert test.count(start)==test.count(end)==1
    appendix=test.split(start)[1].split(end)[0]
    (a.out/"fixture-origin.rs").write_bytes(test)
    for n,data in files.items():(a.out/n).write_bytes(data+appendix if n=="search.rs"else data)
    driver=DRIVER.replace("ROVE_HQ",str(build["hq"]=="hq").lower()).encode();(a.out/"main.rs").write_bytes(driver)
    command=list(build["builds"][0]["command"]);command=[command[0],"--remap-path-prefix",str(a.out)+"=.",*command[3:]]
    env=os.environ.copy();env.update(build["compiler_environment"])
    compilation=subprocess.run(command,cwd=a.out,env=env,capture_output=True,text=True,timeout=120)
    report={**initial,"passed":False,"phase":"compiled diagnostic","shipping_image_executed":False,"diagnostic_image_class":"no_std raw clone, exact production component prefixes plus external search appendix",
        "production_source_sha256":{n:sha(v)for n,v in files.items()},"appendix_sha256":sha(appendix),"test_origin_sha256":sha(test),"driver_sha256":sha(driver),
        "compile_command":command,"compile_returncode":compilation.returncode,"compile_stdout":compilation.stdout,"compile_stderr":compilation.stderr}
    (a.out/"report.json").write_text(json.dumps(report,indent=2)+"\n");assert compilation.returncode==0,compilation.stderr
    binary=a.out/"x";report.update(actual_executed_elf_sha256=sha(binary.read_bytes()),actual_executed_elf_bytes=binary.stat().st_size)
    p=subprocess.Popen([str(binary)],cwd=a.out,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    try:
        stdout,stderr=p.communicate(timeout=10)
        assert len(stdout)<4096 and len(stderr)<4096
        report.update(pid=p.pid,returncode=p.returncode,stdout=stdout.decode(errors="replace"),stderr=stderr.decode(errors="replace"))
        assert p.returncode==0 and stdout==b"deep begin\ndeep nodes 128\ndeep joined\n",report
        report.update(passed=True,actual_guarded_worker_stack_bytes=1048576,search_nodes=128,max_ply=127,abort_is_none=True,partial_bound_not_published=True,
            recursive_heap_scope="actual no_std image has no heap allocator; production hook uses fixed arrays and search prefix is unchanged; mapping trace is a separate proof")
    finally:
        if p.poll()is None:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=3)
        (a.out/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:report[k]for k in("passed","actual_executed_elf_sha256","actual_guarded_worker_stack_bytes","search_nodes","returncode")}))
if __name__=="__main__":main()
