#!/usr/bin/env python3
"""One fixed currentCE cost stage: two packages each, no compiler or engine."""
import argparse
import hashlib
import importlib.util
import json
import lzma
from pathlib import Path
import platform
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
COMPRESSION={'format':'xz','filter':'LZMA2','preset':9,'extreme':True,'lc':3,'lp':0,'pb':2,'check':'CRC64'}
def sha(data):return hashlib.sha256(data).hexdigest()
def read(path):
    data=Path(path).read_bytes().replace(b'\r\n',b'\n')
    if b'\r' in data:raise ValueError('lone CR in ordinary source')
    return data
def bound(data,pin,label):
    if {'bytes':len(data),'sha256':sha(data)}!=pin:raise ValueError('literal pin changed: '+label)
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--native-prior',type=Path,required=True)
    parser.add_argument('--baseline-prior',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();native_prior=args.native_prior.resolve();baseline_prior=args.baseline_prior.resolve();out=args.out.resolve()
    if not all(p.is_absolute() for p in (args.native_prior,args.baseline_prior,args.out)) or not native_prior.is_dir() or not baseline_prior.is_dir():
        parser.error('explicit absolute prior directories and new absolute out required')
    if out.exists() or any(out==p or p in out.parents or out in p.parents for p in (native_prior,baseline_prior)) or any((p/'.git').exists() for p in (out,*out.parents)):
        parser.error('newout outsideGit and prior directories required')
    if platform.system()!='Linux' or platform.machine() not in ('x86_64','amd64'):parser.error('fixed Linux x86-64 target required')
    fixed=json.loads(read(HERE/'cost_recipe.json'))
    if fixed['stage']!='currentCE-one-fixed-whole-cost' or fixed['compression']!=COMPRESSION or fixed['package_limits']!={'C':2,'E':2} or fixed['compiler_engine_limit']!=0:
        raise ValueError('fixed cost scope changed')
    if len(fixed['prior_source_files'])!=42 or set(fixed['new_input_sha256'])!={'cost_decode.py','cost_stage.py'}:raise ValueError('ordinary closure changed')
    ordinary={}
    for name,pin in fixed['prior_source_files'].items():
        data=read(HERE/name);bound(data,pin,'frozen source42/'+name);ordinary[name]=data
    for name,pin in fixed['new_input_sha256'].items():
        data=read(HERE/name)
        if sha(data)!=pin:raise ValueError('newcost source changed: '+name)
        ordinary[name]=data
    ordinary['cost_recipe.json']=read(HERE/'cost_recipe.json')
    if len(ordinary)!=45:raise ValueError('cost ordinary45 changed')
    out.mkdir(parents=True);inputs=out/'inputs';inputs.mkdir();rows={}
    for name,data in ordinary.items():
        target=inputs/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);rows[name]={'bytes':len(data),'sha256':sha(data)}
    report={'complete':False,'stage':fixed['stage'],'mode':'explicit native/baseline prior reuse; no fresh native generation',
        'ordinary_inputs':rows,'reused_native_inputs':{},'reused_baseline_inputs':{},'families':{},'package_counts':{'C':0,'E':0},
        'compiler_runs':0,'native_compiles':0,'engine_runs':0,'DEV_runs':0,'runtime_tests':0,'candidate_old_full_native_equal':False,
        'original_direct_counter_failure_preserved':True,'encoder':COMPRESSION,'no_codec_flag_name_source_or_policy_variants':True}
    def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        for label,source,key in [('native',native_prior,'native_reuse_files'),('baseline',baseline_prior,'baseline_reuse_files')]:
            for name,pin in fixed[key].items():
                data=(source/name).read_bytes();bound(data,pin,label+'/'+name)
                target=out/'reused'/label/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
                report['reused_'+label+'_inputs'][name]={'bytes':len(data),'sha256':sha(data)}
        reused=out/'reused';native_report=json.loads((reused/'native/results.json').read_text())
        if not native_report['complete'] or native_report['new_native_compiles']!={'C':1,'E':2} or native_report['cumulative_candidate_native_compiles']!={'C':2,'E':2} or native_report['candidate_codec_calls']!=0 or native_report['engine_runs']!=0:
            raise ValueError('native prior scope changed')
        literal=module('cost_fixed_literal',inputs/'control/engines/compact/tiny-a/pack_stream.py').source_literal
        decoder=module('cost_strict_decoder',inputs/'cost_decode.py')
        for family in ('C','E'):
            selected=inputs/'control/engines/compact'/('tiny-entry-'+family.lower());original=json.loads((selected/'recipe.json').read_text());expected=original['expected']
            if original['compression']!=COMPRESSION or original['compiler']!=fixed['compiler'][family]:raise ValueError('original compiler/codec changed')
            source=(reused/'native'/fixed['candidate_sources'][family]).read_bytes();bound(source,fixed['candidate_source_pins'][family],family+' candidate source')
            native_paths=fixed['native_image_pairs'][family];first_image=(reused/'native'/native_paths[0]).read_bytes();second_image=(reused/'native'/native_paths[1]).read_bytes()
            bound(first_image,fixed['new_native_pins'][family],family+' firstnewimage');bound(second_image,fixed['new_native_pins'][family],family+' secondnewimage')
            if first_image!=second_image or sha(first_image)==expected['native_sha256']:raise ValueError('new native pair identity/reuse changed')
            baseline_dir=reused/'baseline'/('control-'+family);built=json.loads((baseline_dir/'build.json').read_text())
            if not built['complete'] or len(built['attempts'])!=2:raise ValueError('baseline2 receipt incomplete')
            old_wholes=[]
            for index in (1,2):
                old=(baseline_dir/('attempt-'+str(index))/'x').read_bytes()
                if len(old)!=expected['whole_bytes'] or sha(old)!=expected['whole_sha256'] or built['attempts'][index-1]['whole_sha256']!=expected['whole_sha256']:
                    raise ValueError('baseline completewhole identity differs')
                old_wholes.append(old)
            if old_wholes[0]!=old_wholes[1]:raise ValueError('baseline2 completebytes differ')
            old_source=(reused/'native'/('reused/control-'+family+'/main.c')).read_bytes()
            if len(old_source)!=expected['source_bytes'] or sha(old_source)!=expected['source_sha256']:raise ValueError('baseline source reuse changed')
            row={'status':'started','baseline_source_bytes':len(old_source),'source_bytes':len(source),'source_sha256':sha(source),'source_saved_bytes':len(old_source)-len(source),
                'baseline_whole_bytes':len(old_wholes[0]),'baseline_whole_sha256':sha(old_wholes[0]),'baseline_whole_independent_attempts_reused':2,
                'new_native_bytes':len(first_image),'new_full_native_sha256':sha(first_image),'old_full_native_sha256':expected['native_sha256'],'old_full_native_equal':False,
                'native_pair_independent_attempts_reused':2,'attempts':[],'engine_runs':0};report['families'][family]=row;save()
            template=read(selected/'bootstrap.py.in');prefix=read(selected/'launcher.sh');marker=b'__ROVE_SOURCE_LITERAL__'
            if template.count(marker)!=1 or len(prefix)!=75:raise ValueError('original bootstrap/prefix domain changed')
            first=None;directory=out/family;directory.mkdir();(directory/'main.c').write_bytes(source)
            for index in (1,2):
                expression,kind=literal(source);script=template.replace(marker,expression.encode())
                report['package_counts'][family]+=1;save()
                payload=lzma.compress(script,format=lzma.FORMAT_XZ,check=lzma.CHECK_CRC64,
                    filters=[{'id':lzma.FILTER_LZMA2,'preset':9|lzma.PRESET_EXTREME,'lc':3,'lp':0,'pb':2}])
                whole=prefix+payload;proof=decoder.verify(whole,prefix,source,original['compiler'],script)
                attempt=directory/('attempt-'+str(index));attempt.mkdir();(attempt/'x').write_bytes(whole);(attempt/'x').chmod(0o755);(attempt/'bootstrap.py').write_bytes(script)
                proof_raw=(json.dumps(proof,indent=2)+'\n').encode();(attempt/'decode-proof.json').write_bytes(proof_raw)
                item={'attempt':index,'whole_bytes':len(whole),'whole_sha256':sha(whole),'prefix_bytes':len(prefix),'payload_bytes':len(payload),
                    'bootstrap_bytes':len(script),'bootstrap_sha256':sha(script),'source_literal_kind':kind,'decode_proof_sha256':sha(proof_raw)}
                row['attempts'].append(item)
                current=(whole,script)
                if first is None:first=current
                elif current!=first:raise ValueError('independent complete package bytes differ')
                save()
            (directory/'x').write_bytes(first[0]);(directory/'x').chmod(0o755);(directory/'bootstrap.py').write_bytes(first[1])
            gain=len(old_wholes[0])-len(first[0]);row.update(status='gain_runtime_not_authorized' if gain>0 else 'equal_or_loss_stop',
                independent_whole_attempts=2,whole_bytes=len(first[0]),whole_sha256=sha(first[0]),whole_saved_bytes=gain,
                bootstrap_sha256=sha(first[1]),under4096=len(first[0])<=4096,strict_decode_and_AST_stdin_exact=True)
            save();print(json.dumps({'family':family,'status':row['status'],'source_saved_bytes':row['source_saved_bytes'],'baseline_whole_bytes':len(old_wholes[0]),
                'whole_bytes':len(first[0]),'whole_saved_bytes':gain,'whole_sha256':sha(first[0]),'new_full_native_sha256':sha(first_image),'native_compiles':0,'engine_runs':0}),flush=True)
            if gain<=0:
                report.update(complete=True,stop_after_family=family,stop_reason='equal/loss fixedcandidate; no furtherpackages');save();return 0
        report.update(complete=True,all_two_whole_bytes_reproduced=True,functional_runtime_or_promotion_acceptance=False)
        save();print(json.dumps({'complete':True,'package_counts':report['package_counts'],'compiler_runs':0,'engine_runs':0,'results_sha256':sha((out/'results.json').read_bytes())}),flush=True)
        return 0
    except BaseException as error:
        report.update(complete=False,failure_recorded=True,error=repr(error))
        try:save()
        except BaseException:pass
        raise
if __name__=='__main__':raise SystemExit(main())
