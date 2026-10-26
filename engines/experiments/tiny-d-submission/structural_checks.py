"""Existing independent rules and actual-search observers for fresh D inputs."""
import json
import importlib.util
from pathlib import Path
import sys
_spec = importlib.util.spec_from_file_location('D_structural_cost_checks', Path(__file__).with_name('structural_size.py'))
h = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = h
_spec.loader.exec_module(h)


def check(case, out, *, control=None):
    case, out = Path(case), h.new_output(out)
    cost=json.loads((case/'result.json').read_text())
    h.require_settled_cost(cost)
    files={n:(case/'generated-readable'/n).read_bytes() for n in h.FILES}
    if h.inventory(files)!=cost['input']:
        raise ValueError('observed source differs from measured source')
    m=h.modules()
    rules=h.load('structural_rules',h.ROOT/'engines/experiments/tcec-next/profile_rules.py')
    storage=h.load('structural_storage_probe',h.D/'check_storage.py')
    probe=h.load('structural_search_probe',h.D/'probe_search_compact.py')
    variants=h.transforms()
    search_next=h.load('structural_search_next_checks',h.D/'structural_search_next.py')
    baseline=h.load_baseline()
    cases,coverage=rules.fixture_cases()
    out.mkdir()
    report={'complete':False,'cost_report':h.pin((case/'result.json').read_bytes()),
            'observer':h.pin(Path(__file__).read_bytes()),
            'input':h.inventory(files),'coverage':coverage,'commands':[],'rules':[],'search':[],
            'board_lifecycle':[], 'runtime_helpers':[],
            'runtime_qualified':False,'selected':False,
            'tools':{str(Path(t.__file__).relative_to(h.ROOT)):h.pin(Path(t.__file__).read_bytes()) for t in (rules,storage,probe,search_next,*variants.values())}}
    def save(): (out/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
    hostmod=m['host']
    hostmod.LIMITS={**hostmod.LIMITS,'aggregate_wall':300,'per_command_wall':90,'child_CPU':80,
                   'parent_CPU':1200,'parent_CPU_hard':1260,'tool_output_bytes':8<<20}
    host=None
    body_error=None
    try:
        host=hostmod.Host(out,report,save)
        raw=case/'generated-readable'
        cpp=host.run(['cc','-E','-P',*cost['flags'],str(raw/'board.c')],cwd=raw,kind='actual-board-cpp')
        board=m['minifier'].compact_source(cpp,'c').rstrip(b'\n')
        names=dict(m['probe_d_square_successor'].LEGACY)
        for old,new in names.items():
            board=m['lexical']._replace({'main.c':board},old,new)['main.c']
        for stage in cost['reduction']['stages']:
            if stage['status']!='accepted': continue
            if stage['kind']=='unused-scalar-typedefs':
                for round in stage['rounds']:
                    pieces=[];at=0
                    for edit in round.get('main.c',{}).get('removed',[]):
                        begin,end=edit['begin'],edit['end']
                        if begin>=len(board): continue
                        if end>len(board) or board[begin:end]!=edit['declaration'].encode():
                            raise ValueError('actual board typedef removal differs')
                        pieces.append(board[at:begin]);at=end
                    pieces.append(board[at:]);board=b''.join(pieces)
            elif stage['kind']=='batch-alpha':
                mapping=stage['renames'];text=board.decode();pieces=[];at=0
                for begin,end,token in m['lexical']._identifier_spans(text):
                    if token in mapping:
                        pieces.extend((text[at:begin],mapping[token]));at=end
                pieces.append(text[at:]);board=''.join(pieces).encode()
                names={key:mapping.get(value,value) for key,value in names.items()}
                names.update({key:value for key,value in mapping.items() if key not in names})
            else: raise ValueError('unknown accepted source reduction')
        shipping=(case/'shipping-inputs/main.c').read_bytes()
        if not shipping.startswith(board):
            raise ValueError('rules board is not the actual shipping prefix')
        size=names.get('size_t','size_t')
        declarations=(('\ntypedef '+size+' size_t;\n').encode() if size!='size_t' else b'\n')
        declarations+=b'extern size_t strlen(const char *);extern int strcmp(const char *,const char *);extern char *strtok_r(char *,const char *,char **);extern int printf(const char *,...);extern int puts(const char *);extern char *strcpy(char *,const char *);\n'
        fixture=rules.render_bound_fixture(board,{'board':names.get('Board','Board'),
            'start':names.get('start','start'),'generate':names.get('gen','gen'),
            'make':names.get('make','make'),'four_args':False},cases,declarations)
        (out/'rules.c').write_bytes(fixture)
        report['actual_shipping_board_prefix']=h.pin(board)
        (out/'rules-cases.json').write_text(json.dumps([{k:v for k,v in row.items() if k!='board'} for row in cases],indent=2)+'\n')
        semantic={'output':h.inventory(files),'options':['previous-piece','unsigned-history'],
                  'kind':'structural-cost-experiment-observation-only','cost':report['cost_report']}
        generated,driver,proof=probe.render(files,m['source'],storage,
            reference_board=baseline['board.c'],variant_proof=semantic,
            previous_index=True,unsigned_history=True)
        driver=search_next.adapt_root_observer(driver,files)
        # The terminal-query candidate calls the actual runtime resolver. Its
        # measured definitions join the actual-search fixture before search.c;
        # no duplicate test algorithm or fabricated resolver stands in for it.
        dependencies=search_next.runtime_dependencies(files)
        if dependencies:
            marker=b'#include "search.c"'
            if driver.count(marker)!=1:
                raise ValueError('actual search fixture include boundary differs')
            driver=driver.replace(marker,dependencies+b'\n'+marker,1)
        report['runtime_search_dependencies']=h.pin(dependencies)
        report['actual_search_driver']=h.pin(driver)
        testdir=out/'actual-search';testdir.mkdir()
        for name,data in generated.items(): (testdir/name).write_bytes(data)
        (testdir/'driver.c').write_bytes(driver)
        report['search_fixture']=proof
        lifecycle=variants['board'].render_lifecycle_probe(baseline['board.c'],
            [' '.join(case['moves']) for case in cases])
        (out/'board-lifecycle.c').write_bytes(lifecycle)
        board_flags=['-DCHECK_MATERIAL'] if b'material;' in files['tiny.h'] else []
        lifecycle_control=(Path(control)/'board-plain.stdout').read_bytes() if control else None
        normalized_control=None
        if control is not None:
            normalized_control=(Path(control)/'search-plain.normalized').read_bytes()
        for mode,flags in (('plain',[]),('ubsan',['-fsanitize=undefined','-fno-sanitize-recover=all'])):
            binary=out/('rules-'+mode)
            host.run(['cc','-std=c11','-O1',*flags,str(out/'rules.c'),'-o',str(binary)],cwd=out,kind='rules-compile-'+mode)
            observed=host.run([str(binary)],cwd=out,kind='rules-run-'+mode)
            (out/('rules-'+mode+'.stdout')).write_bytes(observed)
            report['rules'].append({'mode':mode,'binary':h.pin(binary.read_bytes()),**rules._compare_output(observed,cases)})
            binary=testdir/('search-'+mode)
            host.run(['cc','-std=c11','-O2','-msse4.2','-mcx16','-DDEV=0','-DD_HQ=0','-DWORKERS=4','-DTT_BITS=12',
                      '-DCASE_PREFIX=1','-DCASE_DENSE=0','-DCASE_UNSIGNED_HISTORY=1',*flags,str(testdir/'driver.c'),'-o',str(binary)],cwd=testdir,kind='search-compile-'+mode)
            observed=host.run([str(binary)],cwd=testdir,kind='search-run-'+mode)
            normalized,details=probe.verify_output(observed)
            if normalized_control is None: normalized_control=normalized
            if normalized!=normalized_control:
                raise ValueError('actual search observations differ from control')
            (out/('search-'+mode+'.normalized')).write_bytes(normalized)
            report['search'].append({'mode':mode,'binary':h.pin(binary.read_bytes()),**details,'equal_to_control':True})
            binary=out/('board-'+mode)
            host.run(['cc','-std=c11','-O2','-DDEV=0','-DD_HQ=0',*board_flags,*flags,
                      '-I',str(raw),str(out/'board-lifecycle.c'),'-o',str(binary)],cwd=out,kind='board-compile-'+mode)
            observed=host.run([str(binary)],cwd=out,kind='board-run-'+mode)
            if lifecycle_control is None:lifecycle_control=observed
            if observed!=lifecycle_control:raise ValueError('board lifecycle/state differs from control')
            (out/('board-'+mode+'.stdout')).write_bytes(observed)
            report['board_lifecycle'].append({'mode':mode,'output':h.pin(observed),'summary':observed.decode().strip(),'equal_to_control':True})
            save()
        if files['runtime.c'] != baseline['runtime.c']:
            helper=variants['runtime'].render_helper_probe(baseline,files)
            (out/'runtime-helpers.c').write_bytes(helper)
            binary=out/'runtime-helpers'
            # ASan's sparse shadow needs a separate large-virtual-address
            # runner. Keep the shared finite 2-GiB child contract unchanged.
            host.run(['cc','-std=c11','-O1','-fsanitize=undefined','-fno-sanitize-recover=all',
                      str(out/'runtime-helpers.c'),'-o',str(binary)],cwd=out,kind='runtime-helpers-compile')
            observed=host.run([str(binary)],cwd=out,kind='runtime-helpers-run')
            report['runtime_helpers'].append({'source':h.pin(helper),'output':h.pin(observed),'summary':observed.decode().strip(),'sanitizer':'undefined'})
            if report['commands'][-1]['stderr']['bytes']:
                raise ValueError('runtime helper sanitizer emitted diagnostics')
    except BaseException as error:
        body_error=error
        report['failure']={'type':type(error).__name__,'message':str(error)}
        raise
    finally:
        h.finish_report(host,report,save,body_error)
    return report


if __name__=='__main__':
    report=check(sys.argv[1],sys.argv[2],control=sys.argv[3] if len(sys.argv)>3 else None)
    print(json.dumps({'complete':report['complete'],'rules':report['rules'],'search':[{k:v for k,v in row.items() if k in ('mode','totals','learners','order','equal_to_control','normalized')} for row in report['search']]}))
