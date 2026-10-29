#!/usr/bin/env python3
"""Exact currentCE shipping C preparation only; no native/codec/engine."""
import argparse,importlib.util,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
_spec=importlib.util.spec_from_file_location('ce_prepare_support',HERE/'support.py')
support=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(support)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out.resolve()
    if not a.out.is_absolute() or out.exists() or any((x/'.git').exists() for x in (out,*out.parents)):p.error('newexternalabsoluteout required')
    out.mkdir(parents=True);recipe,rows=support.closure(out/'inputs')
    report={'complete':False,'scope':'currentCE exactsource preparation only','inputs':rows,'families':{},'native_compiles':0,'codec_calls':0,'engine_runs':0}
    def save():(out/'prepare.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    for family in ('C','E'):
        data,observations=support.generate(out/'inputs',family,out/('preprocess-'+family));(out/(family+'.c')).write_bytes(data)
        report['families'][family]={'bytes':len(data),'sha256':support.sha(data),'preprocessor':observations};save()
    report['complete']=True;save();print(json.dumps(report['families']))
if __name__=='__main__':main()
