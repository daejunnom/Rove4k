#!/usr/bin/env python3
"""Separate fixed B new-image qualification/cost; never old full-native equality."""
import argparse
import ast
import importlib.util
import json
import lzma
from pathlib import Path
import platform
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
_spec=importlib.util.spec_from_file_location('bce_metadata_support',HERE/'support.py')
support=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(support)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve()
    if not args.out.is_absolute() or out.exists() or any((p/'.git').exists() for p in (out,*out.parents)):
        parser.error('new absolute output outside Git required')
    if platform.system()!='Linux' or platform.machine() not in ('x86_64','amd64'):parser.error('fixed Linux x86-64 target required')
    fixed_raw=support.read(HERE/'metadata_recipe.json');fixed=json.loads(fixed_raw)
    if fixed['family']!='B' or fixed['candidate_native_limit']!=2 or fixed['candidate_codec_limit']!=2 or fixed['engine_run_limit']!=0:
        raise ValueError('fixed Bmetadata scope changed')
    if support.sha(support.read(HERE/'recipe.json'))!=fixed['original_producer_recipe_sha256']:
        raise ValueError('original first-native producer recipe changed')
    for name,pin in fixed['new_input_sha256'].items():
        if support.sha(support.read(HERE/name))!=pin:raise ValueError('reviewed new metadata input changed: '+name)
    if len(fixed['original_source_files'])!=52:raise ValueError('frozen firstphase source52 changed')
    for name,pin in fixed['original_source_files'].items():
        data=support.read(HERE/name)
        if {'bytes':len(data),'sha256':support.sha(data)}!=pin:raise ValueError('immutable original source changed: '+name)
    out.mkdir(parents=True);inputs=out/'inputs';recipe,rows=support.closure(inputs)
    report={'complete':False,'scope':'separateBmetadata newimage qualification + fixedwholecost; no engine execution',
        'comparison_class':'newfullSHA with explicit ELF metadata boundary; original full-native failure stays failed',
        'original_full_native_gate_reinterpreted':False,'inputs':rows,'baseline':{},'candidate':{},'attempts':[],
        'candidate_native_compiles':0,'candidate_codec_calls':0,'engine_runs':0,'C_candidate_native_compiles':0,'E_candidate_native_compiles':0,
        'source_checkpoint':recipe['source_checkpoint'],'runtime':'not authorized in this stage'}
    def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        if set(recipe['policy_files'])!={'policy.py','policy.json','ownership.json','support.py','elf_observe.py'}:
            raise ValueError('original frozen policy closure changed')
        for name,pin in recipe['policy_files'].items():
            data=support.read(HERE/name)
            if support.sha(data)!=pin:raise ValueError('frozen original producer input changed: '+name)
            (inputs/name).write_bytes(data);report['inputs'][name]={'bytes':len(data),'sha256':support.sha(data)}
        for name,pin in fixed['original_source_files'].items():
            data=support.read(HERE/name);target=inputs/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            report['inputs'][name]={'bytes':len(data),'sha256':support.sha(data)}
        for name in ['build.py','metadata.py','metadata_recipe.json','metadata_build.py']:
            data=support.read(HERE/name);(inputs/name).write_bytes(data)
            report['inputs'][name]={'bytes':len(data),'sha256':support.sha(data)}
        if len(report['inputs'])!=fixed['producer_input_file_count']:raise ValueError('closed production input count changed')
        policy=support.module('B_metadata_source_policy',inputs/'policy.py')
        qualifier=support.module('B_metadata_qualifier',inputs/'metadata.py')
        lexer=support.module('B_metadata_lexer',inputs/'control/engines/scripts/rename_c.py')
        literal=support.module('B_metadata_literal',inputs/'control/engines/compact/tiny-a/pack_stream.py').source_literal
        selected=support.entry(inputs,'B');original=json.loads((selected/'recipe.json').read_text());expected=original['expected']
        if expected!=recipe['control_expected']['B'] or original['compiler']!=fixed['compiler'] or original['compression']!=fixed['compression']:
            raise ValueError('original fixed B profile/compiler/codec changed')
        # Regenerate two ORIGINAL shipping outputs first. DEV is not transformed or compiled here.
        control=out/'control-B';command=[sys.executable,'-I','-B',str(selected/'build.py'),'--out',str(control)]
        process=support.run(command,out,timeout=180)
        (out/'control-B.stdout').write_bytes(process.stdout);(out/'control-B.stderr').write_bytes(process.stderr)
        if process.returncode:raise ValueError('unchanged Bcontrol builder failed')
        built=json.loads((control/'build.json').read_text())
        if not built['complete'] or len(built['attempts'])!=2 or built['diagnostic_exact_control']:
            raise ValueError('original two shipping controls incomplete or unexpected DEV compile')
        source=(control/'main.c').read_bytes();old_native=(control/'native/x').read_bytes();old_whole=(control/'x').read_bytes()
        for data,key in [(source,'source'),(old_native,'native'),(old_whole,'whole')]:
            if support.sha(data)!=expected[key+'_sha256'] or len(data)!=expected[key+'_bytes']:raise ValueError('exact original Bcontrol changed')
        report['baseline']={'independent_attempts':2,'full_native_sha256':support.sha(old_native),'native_bytes':len(old_native),
            'whole_sha256':support.sha(old_whole),'whole_bytes':len(old_whole),'source_sha256':support.sha(source),'source_bytes':len(source),
            'receipt_sha256':support.sha((control/'build.json').read_bytes()),'DEV':'unchanged ordinarysource; priorphase2reproduction reused, not compiled in newstage'}
        print(json.dumps({'baseline':'B5955twice_exact','native':support.sha(old_native)}),flush=True);save()
        candidate,source_proof=policy.transform_source(source,family='B',lexer=lexer)
        candidate_root=out/'candidate-B';candidate_root.mkdir();(candidate_root/'main.c').write_bytes(candidate)
        if {'bytes':len(candidate),'sha256':support.sha(candidate)}!=fixed['candidate_source']:
            raise ValueError('sole frozen Bcandidate source changed')
        report['source_proof']=source_proof
        report['header_gate']=support.header_gate(source,candidate,original['compiler'],json.loads(policy.POLICY_BYTES)['mapping'],lexer,candidate_root/'header',
            family='B',configured_preprocessor=original['preprocessor'],readable=(selected/'engine.c').read_bytes(),reference=policy.reference)
        compiled=[]
        for index in (1,2):
            directory=candidate_root/('attempt-'+str(index));directory.mkdir();(directory/'main.c').write_bytes(candidate)
            native_dir=directory/'native';native_dir.mkdir();report['candidate_native_compiles']+=1;save()
            process=support.run(original['compiler'],native_dir,candidate)
            (native_dir/'compiler.stdout').write_bytes(process.stdout);(native_dir/'compiler.stderr').write_bytes(process.stderr)
            if process.returncode:raise ValueError('newimage Bcompiler failed')
            native=(native_dir/'x').read_bytes()
            proof=qualifier.qualify(old_native,native,fixed['qualification'])
            proof_raw=(json.dumps(proof,indent=2)+'\n').encode();(directory/'metadata-proof.json').write_bytes(proof_raw)
            item={'attempt':index,'compiler':original['compiler'],'source_bytes':len(candidate),'source_sha256':support.sha(candidate),
                'native_bytes':len(native),'new_full_native_sha256':support.sha(native),'old_full_native_equal':native==old_native,
                'metadata_qualification_pass':True,'metadata_proof_sha256':support.sha(proof_raw)}
            report['attempts'].append(item);compiled.append((directory,native,item));save()
        if compiled[0][1]!=compiled[1][1]:raise ValueError('independent new full-native bytes did not reproduce')
        # Both new-image native gates precede either candidate codec call.
        template=support.read(selected/'bootstrap.py.in');prefix=support.read(selected/'launcher.sh');marker=b'__ROVE_SOURCE_LITERAL__'
        if len(prefix)!=75 or template.count(marker)!=1:raise ValueError('original bootstrap domain changed')
        first=None
        for directory,native,item in compiled:
            expression,kind=literal(candidate);script=template.replace(marker,expression.encode());ast.parse(script)
            report['candidate_codec_calls']+=1;save()
            whole=prefix+lzma.compress(script,format=lzma.FORMAT_XZ,check=lzma.CHECK_CRC64,
                filters=[{'id':lzma.FILTER_LZMA2,'preset':9|lzma.PRESET_EXTREME,'lc':original['compression']['lc'],'lp':original['compression']['lp'],'pb':original['compression']['pb']}])
            (directory/'x').write_bytes(whole);(directory/'x').chmod(0o755);(directory/'bootstrap.py').write_bytes(script)
            item.update(whole_bytes=len(whole),whole_sha256=support.sha(whole),bootstrap_sha256=support.sha(script),literal=kind)
            current=(native,whole,script)
            if first is None:first=current
            elif first!=current:raise ValueError('independent complete newimage package bytes differ')
        (candidate_root/'native').mkdir();(candidate_root/'native/x').write_bytes(first[0]);(candidate_root/'native/x').chmod(0o755)
        (candidate_root/'x').write_bytes(first[1]);(candidate_root/'x').chmod(0o755);(candidate_root/'bootstrap.py').write_bytes(first[2])
        report['candidate']={'independent_native_attempts':2,'independent_whole_attempts':2,'source_bytes':len(candidate),'source_sha256':support.sha(candidate),
            'native_bytes':len(first[0]),'new_full_native_sha256':support.sha(first[0]),'old_full_native_equal':False,'metadata_qualification_pass':True,
            'whole_bytes':len(first[1]),'whole_sha256':support.sha(first[1]),'bootstrap_sha256':support.sha(first[2]),
            'source_saved_bytes':len(source)-len(candidate),'whole_saved_bytes':len(old_whole)-len(first[1]),'under4096':len(first[1])<=4096}
        report.update(complete=True,status='newimage_metadata_gain_runtime_not_authorized' if len(first[1])<len(old_whole) else 'newimage_metadata_no_whole_gain_stop',
            original_full_native_gate_still_failed=True)
        save();print(json.dumps({'complete':True,'status':report['status'],'source_bytes':len(candidate),'whole_bytes':len(first[1]),
            'whole_saved_bytes':len(old_whole)-len(first[1]),'new_native_sha256':support.sha(first[0]),'old_native_equal':False,'engine_runs':0,
            'results_sha256':support.sha((out/'results.json').read_bytes())}),flush=True)
        return 0
    except BaseException as error:
        report['error']=repr(error);save();raise


if __name__=='__main__':raise SystemExit(main())
