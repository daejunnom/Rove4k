#!/usr/bin/env python3
"""Prepare one fixed LVA-ordering source; no compiler, codec or target run."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def info(data):
    return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}


def require(value,message):
    if not value:raise ValueError(message)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--input',type=Path,help='relocate identical approved input-profile C bytes')
    args=parser.parse_args();out=args.out.resolve()
    require(args.out.is_absolute() and not out.exists() and not any((p/'.git').exists() for p in (out,*out.parents)),'fresh absolute non-Git output required')
    raw=(HERE/'recipe.json').read_bytes();recipe=json.loads(raw)
    for name,pin in recipe['owned_executable_pins'].items():
        require(info((HERE/name).read_bytes())==pin,'owned executable changed: '+name)
    path=(args.input or Path(recipe['input_source'])).resolve();source=path.read_bytes()
    require(info(source)==recipe['input_pin'],'exact approved B input-profile source required')
    spec=importlib.util.spec_from_file_location('fixed_legal_LVA_order',HERE/'transform.py')
    transform=importlib.util.module_from_spec(spec);spec.loader.exec_module(transform)
    candidate,metadata=transform.transform(source,recipe['literal_domain'])
    require(info(candidate)==recipe['output_pin'],'one fixed output identity differs')
    require(info(path.read_bytes())==recipe['input_pin'],'input source changed during preparation')
    out.mkdir(parents=True);(out/'candidate.c').write_bytes(candidate)
    report={'complete':True,'scope':'source-only legal LVA ordering after fixed B input profile',
        'input_path':str(path),'input':info(source),'output':info(candidate),'source_delta':len(candidate)-len(source),
        'recipe':info(raw),'producer':info(Path(__file__).read_bytes()),'transform':metadata,
        'policy_changed':True,'full_minimax_equivalence':False,'QS_SEE_pruning_disabled':True,
        'old_DEV_visits_stack_evidence_inherited':False,'native_compiles':0,'codec_calls':0,'AST':0,'PP':0,
        'engine_or_oracle_runs':0,'native_whole_cost_known':False,'normal_promotion':False,'live_handles':0}
    (out/'source.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('complete','input','output','source_delta','policy_changed','native_whole_cost_known')}))


if __name__=='__main__':main()
