"""Actual D board/search contracts in explicitly separate std-adapter images.

The production board bytes are copied verbatim. Each copied search file begins
with the exact production search bytes, followed by private fixture hooks. The
adapter supplies startup storage and a monotonic clock, not the raw-OS runtime.
"""
from __future__ import annotations

if __name__ == "__main__":
    raise SystemExit("Rove4k Rust engine paths are retired; use C A-F")

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]

DRIVER=r'''use std::alloc::{GlobalAlloc,Layout,System};
use std::sync::atomic::{AtomicBool,AtomicUsize,Ordering};
pub static COUNTING:AtomicBool=AtomicBool::new(false);
pub static ALLOCATIONS:AtomicUsize=AtomicUsize::new(0);
struct Counting;
unsafe impl GlobalAlloc for Counting{
 unsafe fn alloc(&self,l:Layout)->*mut u8{if COUNTING.load(Ordering::Relaxed){ALLOCATIONS.fetch_add(1,Ordering::Relaxed);}unsafe{System.alloc(l)}}
 unsafe fn alloc_zeroed(&self,l:Layout)->*mut u8{if COUNTING.load(Ordering::Relaxed){ALLOCATIONS.fetch_add(1,Ordering::Relaxed);}unsafe{System.alloc_zeroed(l)}}
 unsafe fn realloc(&self,p:*mut u8,l:Layout,n:usize)->*mut u8{if COUNTING.load(Ordering::Relaxed){ALLOCATIONS.fetch_add(1,Ordering::Relaxed);}unsafe{System.realloc(p,l,n)}}
 unsafe fn dealloc(&self,p:*mut u8,l:Layout){unsafe{System.dealloc(p,l)}}
}
#[global_allocator]static ALLOCATOR:Counting=Counting;
pub const HQ:bool=match option_env!("ROVE_HQ"){Some(s)=>s.as_bytes()[0]==b'1',None=>true};
mod board;mod search;
mod os{
 pub fn allocate(bytes:usize)->*mut u8{let layout=std::alloc::Layout::from_size_align(bytes,4096).unwrap();let p=unsafe{std::alloc::alloc_zeroed(layout)};assert!(!p.is_null());p}
 pub fn millis()->u64{static ORIGIN:std::sync::OnceLock<std::time::Instant>=std::sync::OnceLock::new();ORIGIN.get_or_init(std::time::Instant::now).elapsed().as_millis().min(u64::MAX as u128)as u64}
}
fn main(){let(n,a,s,b,k)=search::qualification::standalone_probe();println!("{{\"deep_nodes\":{},\"recursive_allocations\":{},\"score\":{},\"best\":{},\"search_nodes\":{},\"board_bytes\":{},\"worker_bytes\":{},\"hq\":{}}}",n,a,s,b,k,core::mem::size_of::<board::Board>(),core::mem::size_of::<search::Worker>(),HQ);}
'''


def sha(data):return hashlib.sha256(data).hexdigest()
def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')


def run(command,local,environment,record,timeout=90):
    p=subprocess.Popen([str(v)for v in command],cwd=local,env=environment,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
    try:
        stdout,stderr=p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        import signal
        os.killpg(p.pid,signal.SIGKILL);stdout,stderr=p.communicate(timeout=5)
        save(record,{'command':[str(v)for v in command],'returncode':p.returncode,'stdout':stdout,'stderr':stderr,'timeout':True})
        raise AssertionError('bounded command timed out: '+str(record))
    evidence={'command':[str(v)for v in command],'returncode':p.returncode,'stdout':stdout,'stderr':stderr}
    save(record,evidence)
    assert p.returncode==0,'command failed; see '+str(record)
    return evidence


def cfa_record(assembly):
    text=assembly.read_text();records=[]
    for match in re.finditer(r'^\s*\.type\s+([^,]+),@function\s*$',text,re.M):
        name=match.group(1)
        if 'Worker'not in name or 'search'not in name:continue
        end=text.find('\n\t.size\t'+name,match.end())
        if end<0:end=text.find('\n\t.size '+name,match.end())
        body=text[match.end():end if end>=0 else len(text)]
        offsets=[int(v)for v in re.findall(r'\.cfi_def_cfa_offset\s+(\d+)',body)]
        records.append({'symbol':name,'maximum_numeric_CFA_offset':max(offsets,default=None),
                        'first_stack_subtractions':[int(v)for v in re.findall(r'subq\s+\$(\d+),\s*%rsp',body)[:4]]})
    return {'image_class':'std startup-allocation/clock adapter, appended fixture body; panic abort with forced unwind tables for readable CFA; not rawOS shipping ELF',
            'assembly_sha256':sha(assembly.read_bytes()),'functions':records}


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',required=True,type=Path)
    ap.add_argument('--rustc',default=os.environ.get('RUSTC','rustc'))
    ap.add_argument('--unit-only',action='store_true',help='run new unit assertions without repeating unchanged standalone probes')
    a=ap.parse_args();out=a.out.resolve()
    if out==ROOT or ROOT in out.parents or out.exists():ap.error('new external output required')
    if sys.platform!='linux':ap.error('Linux test environment required')
    rustc=shutil.which(a.rustc)
    if rustc is None:ap.error('Rust compiler unavailable')
    source={name:(HERE/name).read_bytes()for name in ['board.rs','search.rs','tests/search.rs']}
    out.mkdir(parents=True)
    hook=source['tests/search.rs'].decode().split('// RAW_DEEP_BEGIN\n',1)[1].split('// RAW_DEEP_END',1)[0]
    (out/'raw-deep-hook.rs').write_text(hook,encoding='utf-8')
    report={'passed':False,'scope':'actual unchanged D board/search bodies in std-adapter test images',
            'excluded':['raw OS syscall/clock correctness','raw clone/futex/TLS/guard-stack lifecycle','shipping native-image/CFA identity','throughput/strength/scaling'],
            'source_sha256':{name:sha(data)for name,data in source.items()},'raw_deep_hook_sha256':sha(hook.encode()),'profiles':[]}
    save(out/'report.json',report)
    try:
        for hq in (False,True):
            label='hq'if hq else'scalar';local=out/label;local.mkdir();(local/'tests').mkdir()
            (local/'board.rs').write_bytes(source['board.rs']);(local/'tests/search.rs').write_bytes(source['tests/search.rs'])
            appended=source['search.rs']+b'\n#[allow(dead_code)]pub mod qualification{include!("tests/search.rs");}\n'
            (local/'search.rs').write_bytes(appended);(local/'main.rs').write_text(DRIVER,encoding='utf-8')
            assert (local/'search.rs').read_bytes()[:len(source['search.rs'])]==source['search.rs']
            env=dict(os.environ,ROVE_HQ=str(int(hq)),LC_ALL='C',TZ='UTC',SOURCE_DATE_EPOCH='0')
            common=[rustc,'--edition=2024','-C','opt-level=z','-C','lto=fat','-C','codegen-units=1',
                    '-C','force-unwind-tables=yes','--check-cfg','cfg(tiny_dev)','--check-cfg','cfg(test)','--crate-name','rove4k_d_search_contract']
            tests=local/'unit-tests'
            run([*common,'--test','--cfg','tiny_dev','main.rs','-o',tests],local,env,local/'unit-compile.json')
            units=run([tests,'--test-threads=1','--nocapture'],local,env,local/'unit-run.json',timeout=45)
            if a.unit_only:
                report['profiles'].append({'hq':hq,'unit_output':units['stdout'],'unit_program_sha256':sha(tests.read_bytes()),
                  'search_body_prefix_sha256':sha((local/'search.rs').read_bytes()[:len(source['search.rs'])]),
                  'standalone_probe':'not repeated by explicit unit-only request; prior separate exact production-body probe retains its own image hash'})
                save(out/'report.json',report);continue
            probe=local/'probe'
            run([*common,'-C','panic=abort','--emit=link,asm','main.rs','-o',probe],local,env,local/'probe-compile.json')
            result=run([probe],local,env,local/'probe-run.json',timeout=30)
            actual=json.loads(result['stdout']);assert actual['deep_nodes']==128 and actual['recursive_allocations']==0 and actual['hq']==hq
            assembly=list(local.glob('*.s'));assert len(assembly)==1
            cfa=cfa_record(assembly[0]);save(local/'cfa.json',cfa)
            assert cfa['functions'],'Worker search CFA symbol was not found in adapter image'
            profile={'hq':hq,'unit_output':units['stdout'],'probe':actual,'program_sha256':sha(probe.read_bytes()),
                     'search_body_prefix_sha256':sha((local/'search.rs').read_bytes()[:len(source['search.rs'])]),
                     'appended_fixture_class_sha256':sha(appended),'cfa':cfa}
            report['profiles'].append(profile);save(out/'report.json',report)
        if not a.unit_only:
            left,right=[p['probe']for p in report['profiles']]
            assert all(left[k]==right[k]for k in ('deep_nodes','recursive_allocations','score','best','search_nodes','board_bytes','worker_bytes'))
        assert all((HERE/name).read_bytes()==data for name,data in source.items()),'production/fixture source drift during validation'
        report['HQ_scalar_probe_identity']=None if a.unit_only else True;report['passed']=True
    except Exception as error:
        report['error']=f'{type(error).__name__}: {error}';raise
    finally:save(out/'report.json',report)
    print(out/'report.json')


if __name__=='__main__':main()
