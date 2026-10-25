"""Owned child envelope for the unchanged conditional-specialization helper."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode=True

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',required=True,type=Path);parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args();root=args.root.resolve();out=args.out.resolve()
    if out.exists():parser.error('new owned specialization output required')
    selected=root/'control/engines/compact/tiny-entry-c'
    recipe=json.loads((selected/'recipe.json').read_text())
    specialize=module('owned_C_specialize',root/'control/engines/scripts/specialize.py').specialize_c
    compact=module('owned_C_minify',root/'control/engines/scripts/minify.py').compact_source
    strip=module('owned_C_strip',root/'control/engines/compact/tiny-a/stitch.py').strip_dev_counters
    active,observations=specialize({'main.c':(root/'candidate.c').read_bytes()},out,recipe['preprocessor']+['-DDEV=0'],os.environ.copy())
    data=compact(active['main.c'],'c');data,counters=strip(data)
    (out/'pre-alpha.c').write_bytes(data)
    import hashlib
    metadata={'source_sha256':hashlib.sha256(data).hexdigest(),'observations':observations,'counters':counters,
        'scope':'PP tool child, not an engine or semantic test'}
    (out/'generation.json').write_text(json.dumps(metadata,indent=2)+'\n')

if __name__=='__main__':main()
