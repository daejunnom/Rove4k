#!/usr/bin/env python3
"""Finish numeric admission, transform guards and exact artifact reproduction."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--measure',type=Path,required=True)
    parser.add_argument('--rename',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if not args.out.is_absolute() or args.out.exists():parser.error('new absolute evidence directory required')
    args.out.mkdir(parents=True)
    measurement=json.loads(args.measure.read_text());frozen=args.measure.parent/'frozen'
    sources={name:(frozen/name).read_bytes() for name in measurement['source_sha256']}
    representation=module('tiny_guarded_representation',HERE/'represent.py')
    state=module('tiny_guarded_state',HERE/'state.py')
    choices=('discard','prior','bounded-eval')
    transformed=representation.apply(sources,choices)
    transformed,_=state.transform(transformed,operations=('probe-marker','positive-bonus'))
    combined=(frozen/'reference-combined.c').read_bytes()
    original=sources['search.c'].replace(b'#include "tiny.h"',b'')
    changed=transformed['search.c'].replace(b'#include "tiny.h"',b'')
    regenerated=combined.replace(original,changed)
    expected=(args.measure.parent/'winner-state/combined.c').read_bytes()
    if regenerated!=expected:raise ValueError('current stronger producer guards changed qualified source')
    checks=[]
    for name,mutation in (
        ('evaluator-coefficients',lambda s:{**s,'board-generated.c.in':s['board-generated.c.in'].replace(b'0,100,320,330,500,900,0',b'0,100,320,330,500,1900,0')}),
        ('piece-admission',lambda s:{**s,'board-generated.c.in':s['board-generated.c.in'].replace(b'counts[v<0]>16',b'counts[v<0]>32')}),
        ('mate-scale',lambda s:{**s,'tiny.h':s['tiny.h'].replace(b'#define MATE 30000',b'#define MATE 20000')})):
        try:representation.apply(mutation(sources),('bounded-eval',))
        except ValueError:checks.append({'name':name,'rejected':True})
        else:raise ValueError('unsafe HCE mutation admitted: '+name)
    fixture=(b'#define main tiny_application_main\n#include "subject.c"\n#undef main\n'
             b'int main(void){int maximum=0,count=0;for(int p=-6;p<=6;p++)if(p)for(int q=0;q<128;q++)if(!(q&0x88)){int x=abs(value(p,q));if(x>maximum)maximum=x;count++;}printf("{\\\"piece_square_values\\\":%d,\\\"max_abs\\\":%d,\\\"sum_bound\\\":%d}\\n",count,maximum,32*maximum);return maximum!=910||count!=768;}\n')
    # Keep the fixture readable without introducing shell quoting or source
    # substitution. The escaped JSON format is a C string in this byte literal.
    fixture=fixture.replace(b'\\\\',b'\\')
    (args.out/'subject.c').write_bytes(expected)
    (args.out/'bounds.c').write_bytes(fixture)
    command=['cc','-std=c11','-O2','-pthread','-DWORKERS=1','-DTT_BITS=18','-DDEV=1','bounds.c','-o','bounds']
    built=subprocess.run(command,cwd=args.out,capture_output=True,text=True,timeout=30)
    if built.returncode:raise RuntimeError(built.stderr)
    run=subprocess.run([str(args.out/'bounds')],capture_output=True,text=True,timeout=5)
    if run.returncode:raise RuntimeError(run.stdout+run.stderr)
    numeric=json.loads(run.stdout)
    bad=subprocess.run(['cc','-std=c11','-pthread','-DDEV=1','-DPLY=900','-E','subject.c'],
                       cwd=args.out,capture_output=True,text=True,timeout=30)
    if not bad.returncode or 'admitted HCE exceeds static bound' not in bad.stderr:
        raise ValueError('unsafe PLY profile did not reject at preprocessing')
    renamed=json.loads(args.rename.read_text());record=renamed['minimum_complete']
    source=(args.rename.parent/'selected/main.c').read_bytes()
    pack=module('tiny_selected_pack_repeat',args.rename.parent/'frozen/pack_stream.py')
    repeated,metadata=pack.make_stream(source,renamed['compiler_stdin'],'xz')
    if repeated!=Path(record['path']).read_bytes():raise ValueError('selected complete artifact does not reproduce')
    (args.out/'x.repeated').write_bytes(repeated)
    repeated_native=subprocess.run(renamed['compiler_stdin'],input=source,cwd=args.out,capture_output=True,timeout=30)
    if repeated_native.returncode or sha((args.out/'x').read_bytes())!=renamed['baseline_program_sha256']:
        raise ValueError('selected full native program does not reproduce')
    report={'passed':True,'guarded_recipe_matches_qualified_input':True,
            'readable_winner_sha256':sha(expected),'numeric':numeric,'negative_guards':checks,
            'unsafe_ply_preprocess':{'returncode':bad.returncode,'stderr':bad.stderr},
            'artifact_repeated':{'bytes':len(repeated),'sha256':sha(repeated)},
            'native_repeated_sha256':sha((args.out/'x').read_bytes()),
            'proof':'At most32pieces; each absPSTvalue<=910; absHCE<=29120<MATE-PLY-1. Captures cannot increase piece count, promotions preserve it; dev admission enforces16/colour.'}
    (args.out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
