#!/usr/bin/env python3
"""Five existing controlled schedules adapted to the exact new shipping C."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
CANDIDATE='15999279c5bd4690db7129bda032c6b5962acbd814236719cda40755ae31794b'

def sha(data):return hashlib.sha256(data).hexdigest()

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);sys.modules[name]=result;spec.loader.exec_module(result);return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args();out=args.out.resolve()
    if not args.out.is_absolute() or out.exists() or any((p/'.git').exists() for p in (out,*out.parents)):
        parser.error('new absolute output outside Git required')
    out.mkdir(parents=True);frozen=out/'frozen';frozen.mkdir()
    report={'complete':False,'scope':'actual C DEV0 five controlled startup-only schedules, real pthread create/entry/arrival/join/free; no new A execution reuse',
        'cases':[],'inputs':{},'profile':{'workers':2,'tt_bits':18,'DEV':0,'ISA':'AVX2'},
        'excluded':['shipping whole image execution','query/search/board proof','new join-failure safety','TSAN/SAN race proof','performance','variant sweep']}
    def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        manifest=json.loads((HERE/'inputs.json').read_text())
        for prefix,key in (('control','control_files'),('reference','reference_files')):
            for name,pin in manifest[key].items():
                raw=(HERE/prefix/name).read_bytes();data=raw.replace(b'\r\n',b'\n')
                if b'\r' in data or len(data)!=pin['bytes'] or sha(data)!=pin['sha256']:raise ValueError('frozen proof input changed: '+name)
                dest=frozen/prefix/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
                report['inputs'][prefix+'/'+name]={'bytes':len(data),'sha256':sha(data)}
        for name in ('phase-check.py','phase-contract.c','inputs.json'):
            data=(HERE/name).read_bytes();(frozen/name).write_bytes(data)
            report['inputs'][name]={'bytes':len(data),'sha256':sha(data)}
        candidate=(frozen/'control/candidate.c').read_bytes()
        if sha(candidate)!=CANDIDATE:raise ValueError('new C source pin changed')
        old=(frozen/'control/control/engines/compact/tiny-entry-c/engine.c').read_bytes()
        transformed,bindings=module('phase_C_transform',frozen/'control/transform.py').transform(old)
        if transformed!=candidate:raise ValueError('new C is not exact seven-site composition')
        original_fixture=(frozen/'reference/engines/experiments/tiny-a-startup/phase-contract.c').read_bytes()
        adapted=original_fixture.replace(b'71f9ff6ce1b7f555ad85c3bf49766381c0627315da94acf0c49eeee7bee4a734',CANDIDATE.encode())
        if original_fixture.count(b'71f9ff6ce1b7f555ad85c3bf49766381c0627315da94acf0c49eeee7bee4a734')!=1 or adapted!=(frozen/'phase-contract.c').read_bytes():
            raise ValueError('phase fixture differs beyond C source event identity')
        reference=module('phase_C_assertions',frozen/'reference/engines/experiments/tiny-a-startup/phase-check.py')
        reference.CANDIDATE=CANDIDATE
        tools=module('phase_C_owned_tools',frozen/'control/support.py')
        command=['cc','-std=c11','-Os','-pthread','-DDEV=0','-DWORKERS=2','-DTT_BITS=18','-mavx2',
            '-DPRODUCTION_SOURCE="'+str(frozen/'control/candidate.c')+'"',str(frozen/'phase-contract.c'),'-o',str(out/'phase-contract')]
        report.update(source_transform=bindings,compile_command=command,source_sha256=CANDIDATE,
            fixture_adaptation='exact original scheduling/interposition source; only literal source-event hash changed; C -mavx2 added')
        save()
        result=tools.run(command,out,timeout=90)
        (out/'compile.stdout').write_bytes(result.stdout);(out/'compile.stderr').write_bytes(result.stderr)
        report['compile_returncode']=result.returncode;report['tool_commands']=tools.COMMANDS
        if result.returncode:raise ValueError('C phase diagnostic failed to compile')
        report['diagnostic_native_sha256']=sha((out/'phase-contract').read_bytes());save()
        for name in reference.CASES:
            row=reference.run_case(out/'phase-contract',name,out)
            if tools.group_members(row['pid']):raise ValueError('diagnostic group remains after case')
            row['owned_group_absent']=True
            report['cases'].append(row);save()
            print(json.dumps({'case':name,'passed':row['passed'],'returncode':row.get('returncode')}),flush=True)
            if not row['passed']:raise ValueError('C phase case failed: '+name)
        report.update(complete=True,passed_count=5,total=5,owned_live_handles=0)
        save();print(json.dumps({'complete':True,'out':str(out),'results_sha256':sha((out/'results.json').read_bytes())}),flush=True)
    except BaseException as error:
        report['error']=repr(error);save();raise

if __name__=='__main__':main()
