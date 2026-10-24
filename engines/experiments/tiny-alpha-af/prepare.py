#!/usr/bin/env python3
"""Reproduce only two exact shipping C inputs before freezing literal aliases."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode=True
_spec=importlib.util.spec_from_file_location('af_prepare_support',Path(__file__).with_name('support.py'))
support=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(support)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve()
    if not args.out.is_absolute() or out.exists() or any((p/'.git').exists() for p in (out,*out.parents)):
        parser.error('new external output required')
    out.mkdir(parents=True);recipe,rows=support.closure(out/'inputs')
    report={'complete':False,'scope':'fixed control C preparation only; no native compiler or engine execution',
            'inputs':rows,'families':{},'candidate_compiles':0,'native_compiles':0,'engine_runs':0}
    def save():(out/'prepare.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    for family in ('A','F'):
        data,observations=support.generate(out/'inputs',family,out/('preprocess-'+family))
        (out/(family+'.c')).write_bytes(data)
        report['families'][family]={'bytes':len(data),'sha256':support.sha(data),'preprocessor':observations};save()
    report['complete']=True;save();print(json.dumps(report['families']))


if __name__=='__main__':main()
