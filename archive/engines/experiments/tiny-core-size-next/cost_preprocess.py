#!/usr/bin/env python3
"""One fixed B core DEV0 specialization; caller owns this process and compiler children."""
import argparse
import json
import os
from pathlib import Path
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from cost_tools import module,sha
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',required=True,type=Path);parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args();root=args.root.resolve();out=args.out.resolve();assert not out.exists()
    baseline=json.loads((root/'cost-normal.json').read_bytes());transform=json.loads((root/'transform.json').read_bytes())
    for name,row in baseline['normal_files'].items():
        raw=(root/'normal'/name).read_bytes();assert len(raw)==row['bytes'] and sha(raw)==row['sha256'],name
    source=(root/'candidate.c').read_bytes();assert len(source)==transform['candidate']['bytes'] and sha(source)==transform['candidate']['sha256']
    selected=root/'normal/engines/compact/tiny-entry-b';recipe=json.loads((selected/'recipe.json').read_bytes())
    special=module('B_ray_specialize',root/'normal/engines/scripts/specialize.py')
    compact=module('B_ray_minify',root/'normal/engines/scripts/minify.py')
    strip=module('B_ray_counter_strip',root/'normal/engines/compact/tiny-b/generate.py').strip_counters
    active,observations=special.specialize_c({'main.c':source},out,
        recipe['preprocessor']+['-DDEV=0','main.c','-o','x'],os.environ.copy())
    data=compact.compact_source(active['main.c'],'c');data,counters=strip(data)
    (out/'pre-alpha.c').write_bytes(data)
    report={'source_bytes':len(data),'source_sha256':sha(data),'readable_sha256':sha(source),'observations':observations,
        'counter_removal':{'original_helper_metadata':counters,'removed_noop_counter_calls':counters['removed_noop_counter_calls'],
            'historical_native_identity_gate_not_applied':True,'structurally_new_candidate':True},
        'profile':recipe['profile'],'resource_and_function_decisions_unchanged':True,'native_compiles':0,'engine_executions':0}
    (out/'generation.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
    print(json.dumps({'complete':True,'pre_alpha':report['source_sha256']}))
if __name__=='__main__':main()
