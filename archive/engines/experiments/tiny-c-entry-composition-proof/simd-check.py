#!/usr/bin/env python3
"""Read-only AVX2 placement audit of the exact first-cost standalone C ELF."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
NATIVE='cc67f03a58f350a1bd0ab1f07e774c13cf8f6b628b469107834da6f505f7cf00'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve();native=args.native.resolve()
    if not args.out.is_absolute() or out.exists() or any((p/'.git').exists() for p in (out,*out.parents)):parser.error('new external output required')
    raw=native.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=NATIVE:raise ValueError('exact standalone native changed')
    out.mkdir(parents=True)
    path=HERE/'control/support.py';spec=importlib.util.spec_from_file_location('standalone_SIMD_tools',path)
    tools=importlib.util.module_from_spec(spec);spec.loader.exec_module(tools)
    result=tools.run(['objdump','-d',str(native)],out,timeout=30)
    (out/'disassembly.txt').write_bytes(result.stdout);(out/'objdump.stderr').write_bytes(result.stderr)
    if result.returncode:raise ValueError('objdump failed')
    current=None;observed=[]
    for line in result.stdout.decode().splitlines():
        match=re.match(r'^[0-9a-f]+ <([^>]+)>:',line)
        if match:current=match.group(1)
        if any(op in line for op in ('vpgatherdd','vphaddd')):
            observed.append({'function':current,'instruction':line.strip()})
    if not any(r['function'].startswith('search') and 'vpgatherdd' in r['instruction'] for r in observed):raise ValueError('actual search AVX2 gather not found')
    if not any(r['function'].startswith('search') and 'vphaddd' in r['instruction'] for r in observed):raise ValueError('actual search AVX2 reduction not found')
    if native.read_bytes()!=raw:raise ValueError('native changed during disassembly')
    report={'complete':True,'scope':'static disassembly of exact standalone shipping native; no ELF execution or parity inferred from disassembly',
        'native_sha256':NATIVE,'observed':observed,'tool_commands':tools.COMMANDS,'engine_runs':0,'owned_live_handles':0}
    data=(json.dumps(report,indent=2)+'\n').encode();(out/'results.json').write_bytes(data)
    print(json.dumps({'complete':True,'observed_AVX2_instructions':len(observed),'results_sha256':hashlib.sha256(data).hexdigest()}))

if __name__=='__main__':main()
