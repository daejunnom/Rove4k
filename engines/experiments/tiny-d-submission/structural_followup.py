"""Reproduce the bounded PR #21 follow-up portfolio from canonical sources.

Named cases distinguish work-saving transformations, deferred first touch and
deliberately expensive alternatives. A measured minimum is not a selected
production artifact. Each complete native and every loader byte is counted.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode=True
D=Path(__file__).resolve().parent
_spec=importlib.util.spec_from_file_location('D_followup_base',D/'structural_size.py')
h=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(h)


def modules():
    return {name:h.load('D_followup_'+name,D/('structural_'+name+'.py'))
            for name in ('board_next','search_next','platform','codec')}


def selections(m):
    board=m['board_next'].BEST
    search=m['search_next'].BEST
    platform=('fixed-worker-entry','abort-startup','nul-tokens')
    return {
        'control':{},
        'board-only':{'board_next':board},
        'search-only':{'search_next':search},
        'platform-only':{'platform':platform},
        'board-search':{'board_next':board,'search_next':search},
        'board-platform':{'board_next':board,'platform':platform},
        'search-platform':{'search_next':search,'platform':platform},
        'fast-span':{'board_next':board,'search_next':search,'platform':platform[:2]},
        'fast':{'board_next':board,'search_next':search,'platform':platform},
        'fast-union':{'board_next':board,'search_next':(*search,'order_union'),'platform':platform},
        'fast-capacity':{'board_next':board,'search_next':(*search,'capacity413'),'platform':platform},
        'fast-plain-root':{'board_next':board,'search_next':search[:1],'platform':platform},
        'lazy-first-touch':{'board_next':board,'search_next':search,'platform':(*platform,'lazy-tt-zero')},
        'known-child-check':{'board_next':board,'search_next':(*search,'known_child_check'),'platform':platform},
        'slow-board':{'board_next':('mode-sign-sentinel','fused-walk-rebuild')},
        'slow-order':{'search_next':('order_recompute',)},
        'slow-board-shared':{'board_next':('mode-sign-sentinel','fused-walk-rebuild'),
                             'search_next':search,'platform':platform},
        'slow-order-shared':{'board_next':board,'search_next':('root_current','order_recompute'),
                             'platform':platform},
    }


def generate(profile='test-p4'):
    base,chain=h.prepare_baseline(profile)
    old=h.transforms()
    previous=h.candidate(base,{name:module.BEST for name,module in old.items()},old)
    return previous,chain,old


def apply(previous,selection,m):
    result=dict(previous)
    for name in ('board_next','search_next','platform'):
        result=m[name].apply(result,selection.get(name,()))
    return result


def run(out,profile,cases,*,repeat=True,check=False,codecs=False):
    out=Path(out)
    if not out.is_absolute() or out.exists() or any((p/'.git').exists() for p in (out,*out.parents)):
        raise ValueError('new absolute external output required')
    if check and profile!='test-p4':raise ValueError('semantic observer is P4 only')
    previous,chain,old=generate(profile)
    m=modules();choices=selections(m)
    if any(name not in choices for name in cases):raise ValueError('unknown follow-up case')
    out.mkdir(parents=True)
    (out/'source-chain.json').write_text(json.dumps(chain,indent=2)+'\n')
    summary={'complete':False,'profile':profile,'previous_full':h.inventory(previous),'cases':[],
             'selected':False,'runtime_qualified':False,
             'tools':{str(Path(t.__file__).relative_to(h.ROOT)):h.pin(Path(t.__file__).read_bytes())
                      for t in (h,*old.values(),*m.values())},'driver':h.pin(Path(__file__).read_bytes())}
    def save():(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    try:
        for name in dict.fromkeys(('control',*cases) if check else cases):
            selection=choices[name]
            files=apply(previous,selection,m)
            report=h.measure(files,out/name,label=name,repeat=repeat,profile=profile)
            row={'name':name,'options':selection,'source':h.inventory(files),
                 'native':report['native_runs'][0]['native'],
                 'whole':{key:value['bytes'] for key,value in report['packages'].items()}}
            summary['cases'].append(row);save()
            print(json.dumps({key:row[key] for key in ('name','options','native','whole')}),flush=True)
            if codecs:
                encoded=m['codec'].compare(out/name,out/(name+'-codec'))
                row['codec_best']=encoded['best'];row['codec_unnamed']=encoded['unnamed'];save()
            if check:
                checker=h.load('D_followup_checks',D/'structural_checks.py')
                comparison=out/'control-checks'
                checker.check(out/name,out/(name+'-checks'),
                    control=comparison if name!='control' else None)
        summary['complete']=True
    except BaseException as error:
        summary['failure']={'type':type(error).__name__,'message':str(error)}
        raise
    finally:save()
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--profile',choices=('test-p4','test-p28','tcec-provisional'),default='test-p4')
    parser.add_argument('--case',action='append',choices=tuple(selections(modules())))
    parser.add_argument('--single-build',action='store_true',help='cost sweep only; omit the repeated native build')
    parser.add_argument('--check',action='store_true',help='run actual rules/search/board observers; P4 only')
    parser.add_argument('--codecs',action='store_true',help='compare finite CRC64 XZ parameters for each native')
    args=parser.parse_args()
    run(args.out,args.profile,args.case or ('control','fast'),repeat=not args.single_build,
        check=args.check,codecs=args.codecs)
