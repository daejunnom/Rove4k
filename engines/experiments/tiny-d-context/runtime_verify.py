#!/usr/bin/env python3
"""Narrow runtime adapter for exactly two context own-ELFs.

Reuses pinned, unchanged production/inspection/cleanup helpers. Does not call
or weaken their old main/EXPECTED admission. No pre-entry audit or RIE/ptrace
fixture, compiler, codec, source mutation, or auxiliary program is invoked.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import struct
import sys
import time

HERE=Path(__file__).resolve().parent
HELPER_SHA='4806dbcc87cf5150a6501770f743e3ff63646e3b4da1bb23281ac10d9b551be6'
ORACLE_SHA='aea285b5b5f07602c829595840d5270fa8dc25683ccd26c63607435679024db8'
BUILD_SHA='432ec934af089db4d23edf4c3b269ee5e86941634aeb77e88f037c96f232f7a9'
FIXED={
    'scalar-shipping':(6401,'7e8f405c40ae5a64f3420f23d77a179d4154e5b9bd9e9c67aea1c83a18d238da',8092,'59829299f667cdb6682c5ed4a955fb50b76a5584209caf9e4bddf1c0ee2cd160'),
    'hq-shipping':(6614,'be6a45a21895b204550cc0ae7a9a73928d6f4df1313757bad68db4dd97c4f358',8480,'f1d6558ec5a13e400c2d6df182b01b3236bf1ee1e99f686e47f144a32d222c5c'),
}

def sha(raw):return hashlib.sha256(raw).hexdigest()
def need(condition,message):
    if not condition:raise ValueError(message)

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    return module

def outer_header(raw):
    need(raw[:9]==b'\x7fELF\x02\x01\x01\0\0' and len(raw)>=176,'context ELF64 LE header')
    need(struct.unpack_from('<HHI',raw,16)==(2,62,1),'context x86-64 executable')
    need(struct.unpack_from('<QQQ',raw,24)==(0x100000b0,64,0),'literal outer entry/PHDR/stripped header')
    need(struct.unpack_from('<IHHHHHH',raw,48)==(0,64,56,2,0,0,0),'literal outer header fields')
    actual=[struct.unpack_from('<IIQQQQQQ',raw,64+56*i) for i in range(2)]
    need(actual==[(1,5,0,0x10000000,0x10000000,len(raw),len(raw),4096),
        (0x6474e551,6,0,0,0,0,0,8)],'exact context RX/nonexec-stack PHDRs')

def extra_mapping_observation(helper,row):
    observations=[]
    for name in ('before_uci','during_active_search'):
        maps=row[name]['maps']
        helper.covers(maps,0x10000000,8192,'r-x')
        large=[item for item in maps if item['permissions'][:3]=='rw-' and item['end']-item['start']>=33554432]
        need(not large,'large RW interval remains in local two-worker profile')
        observations.append({'stage':name,'outer_two_page_RX_observed':True,
            'RW_intervals_at_least_32MiB':large,
            'scope':'observed absence of a large contiguous RW interval in this local profile; not a context-address or causal munmap trace'})
    row['context_mapping_observations']=observations

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--helper',type=Path,default=HERE.parents[1]/'compact/tiny-entry-d/verify.py')
    parser.add_argument('--oracle',type=Path,default=HERE.parents[1]/'tests/chess_oracle.py')
    parser.add_argument('--budget',type=int,default=120)
    args=parser.parse_args();out=args.out.resolve();buildpath=args.build.resolve()
    need(args.out.is_absolute() and not out.exists() and not any((p/'.git').exists() for p in (out,*out.parents)),'new absolute external output required')
    need(sys.platform.startswith('linux') and 30<=args.budget<=180,'Linux and bounded runtime budget required')
    out.mkdir(parents=True);started=time.monotonic();helper=None;phase='admission'
    report={'complete':False,'scope':__doc__,'results':[],'failures':[],'cleanup':[],
        'pre_entry_BSS_or_CHECKPOINT_qualification':False,'RIE_or_ptrace_fixture':False,
        'normal_encoder_qualification':False,'large_RW_observation_is_not_address_or_causal_release_proof':True}
    prior=None
    try:
        own=Path(__file__).read_bytes();rawbuild=buildpath.read_bytes();rawhelper=args.helper.read_bytes();raworacle=args.oracle.read_bytes()
        need(sha(rawbuild)==BUILD_SHA,'exact context first-cost build receipt')
        need(sha(rawhelper)==HELPER_SHA,'unchanged maintained production verifier helper')
        normalized_oracle=raworacle.replace(b'\r\n',b'\n')
        need(sha(normalized_oracle)==ORACLE_SHA,'exact independent chess oracle')
        build=json.loads(rawbuild)
        need(build['complete'] and not build['failures'] and not build['cleanup'],'first-cost build incomplete')
        need(len(build['forms'])==2 and {r['id'] for r in build['forms']}==set(FIXED),'exact two forms required')
        sources=out/'source';sources.mkdir()
        for name,raw in (('runtime_verify.py',own),('production_helper.py',rawhelper),('chess_oracle.py',normalized_oracle)):
            (sources/name).write_bytes(raw)
        report['source_sha256']={'adapter':sha(own),'unchanged_helper':sha(rawhelper),'oracle':sha(normalized_oracle)}
        report['build_sha256']=sha(rawbuild)
        helper=load('context_pinned_runtime_helper',sources/'production_helper.py')
        oracle=load('context_pinned_legal_oracle',sources/'chess_oracle.py')
        budget=helper.Budget(args.budget)
        prior=signal.signal(signal.SIGTERM,helper.terminated)
        admitted=[]
        for row in build['forms']:
            form=row['id'];size,digest,native_size,native_digest=FIXED[form]
            old=helper.EXPECTED[form];layout=row['native_layout']
            need((old['native_bytes'],old['native_sha256'])==(native_size,native_digest),'unchanged native helper admission')
            need(layout==old['layout'],'exact per-form native layout')
            native=Path(row['native_input']['path']);program=Path(row['whole']['path'])
            need(native.is_absolute() and program.is_absolute(),'absolute admitted target paths')
            native_bytes=native.read_bytes();whole=program.read_bytes()
            need((len(native_bytes),sha(native_bytes))==(native_size,native_digest),'actual qualified native identity')
            need((len(whole),sha(whole))==(size,digest),'actual context own-ELF identity')
            need((row['whole']['bytes'],row['whole']['sha256'])==(size,digest),'build own identity metadata')
            outer_header(whole)
            candidate={'path':str(program),'bytes':size,'sha256':digest}
            admitted.append((form,candidate,layout,native_digest))
        report['all_two_exact_targets_admitted_before_launch']=True
        report['shipping_protocol']=helper.SHIPPING_PROTOCOL
        for form,candidate,layout,native_digest in admitted:
            entry={'id':form,'whole':candidate,'native_sha256':native_digest,'sessions':[]};report['results'].append(entry)
            for shutdown in ('quit','EOF'):
                phase=form+'/'+shutdown;case={};entry['sessions'].append(case)
                directory=out/form/shutdown
                helper.production(candidate,layout,native_digest,directory,budget,oracle,shutdown,case)
                extra_mapping_observation(helper,case)
        report['complete']=True
    except BaseException as error:
        report['complete']=False;report['failures'].append({'phase':phase,'type':type(error).__name__,'message':str(error)})
    finally:
        mask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGTERM})
        try:
            if helper is not None:
                for owned in list(helper.OWNED):
                    report['complete']=False
                    try:report['cleanup'].append(owned.cleanup())
                    except BaseException as error:report['failures'].append({'phase':phase+'/cleanup','type':type(error).__name__,'message':str(error)})
            report['elapsed_seconds']=time.monotonic()-started
            path=out/'results.json';path.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
        finally:
            if prior is not None:signal.signal(signal.SIGTERM,prior)
            signal.pthread_sigmask(signal.SIG_SETMASK,mask)
    print(json.dumps({'complete':report['complete'],'report':str(path),'sha256':sha(path.read_bytes()),'forms':len(report['results']),'failures':report['failures']}))
    return 0 if report['complete'] else 1

if __name__=='__main__':raise SystemExit(main())
