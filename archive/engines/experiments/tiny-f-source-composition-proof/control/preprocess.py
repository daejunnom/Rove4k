#!/usr/bin/env python3
"""One candidate DEV0 specialization inside its caller-owned process group."""
import argparse
import json
import os
from pathlib import Path
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from tools import module,sha

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();root=args.root.resolve();out=args.out.resolve();assert not out.exists()
    manifest=json.loads((root/'baseline.json').read_bytes());transform=json.loads((root/'transform.json').read_bytes())
    for name,pin in manifest['control_files'].items():
        raw=(root/'control'/name).read_bytes();assert len(raw)==pin['bytes'] and sha(raw)==pin['sha256'],name
    source=(root/'candidate.c').read_bytes();assert len(source)==transform['candidate']['bytes'] and sha(source)==transform['candidate']['sha256']
    selected=root/'control/engines/compact/tiny-entry-f'
    recipe=json.loads((selected/'recipe.json').read_bytes())
    special=module('F_composition_specialize',root/'control/engines/scripts/specialize.py')
    compact=module('F_composition_minify',root/'control/engines/scripts/minify.py')
    lexer=module('F_composition_lexer',root/'control/engines/scripts/rename_c.py')
    original_builder=module('F_original_builder',selected/'build.py')
    active,observations=special.specialize_c({'main.c':source},out,recipe['preprocessor']+['-DDEV=0'],os.environ.copy())
    data=compact.compact_source(active['main.c'],'c');data,counters=original_builder.strip_counters(data)
    observed={}
    for old,new in recipe['resource_literals']:
        observed[old]=sum(token==old for _,_,token in lexer._identifier_spans(data.decode()))
        data=lexer._replace({'main.c':data},old,new)['main.c']
    for old,new in recipe['function_spellings']:
        data=lexer._replace({'main.c':data},old,new)['main.c']
    (out/'pre-alpha.c').write_bytes(data)
    report={'source_bytes':len(data),'source_sha256':sha(data),'readable_sha256':sha(source),
        'resource_token_counts_before_literals':observed,'observations':observations,'counters':counters,
        'profile':recipe['profile'],'function_spellings_unchanged':True,'counter_schema_unchanged':True,
        'native_compiles':0,'engine_executions':0}
    (out/'generation.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
    print(json.dumps({'complete':True,'pre_alpha':report['source_sha256'],'resource_counts':observed}))
if __name__=='__main__':main()
