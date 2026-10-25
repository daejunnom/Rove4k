#!/usr/bin/env python3
"""One fixed C composition first cost; compiler/codec tools only, no engine run."""
import argparse
import json
from pathlib import Path
import platform
import sys

sys.dont_write_bytecode=True
import importlib.util
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('composition_support',HERE/'support.py')
support=importlib.util.module_from_spec(spec);spec.loader.exec_module(support)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve()
    if not args.out.is_absolute() or out.exists() or any((p/'.git').exists() for p in (out,*out.parents)):
        parser.error('new absolute output outside any Git checkout required')
    if platform.system()!='Linux' or platform.machine() not in ('x86_64','amd64'):parser.error('qualified target is Linux x86-64')
    out.mkdir(parents=True);inputs=out/'inputs'
    report={'complete':False,'scope':'single C query/reset/startup composition first cost, no semantic/engine execution',
        'engine_runs':0,'semantic_tests':0,'old_native_equality_required_for_structural_change':False,
        'control':{},'candidate':{},'tool_commands':support.COMMANDS}
    def save():(out/'cost.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        manifest,rows=support.closure(inputs);report['inputs']=rows;save()
        selected=inputs/'control/engines/compact/tiny-entry-c';recipe=json.loads(support.read(selected/'recipe.json'))
        if recipe['expected']!=manifest['control_expected'] or recipe['compiler']!=manifest['compiler'] or recipe['preprocessor']!=manifest['preprocessor'] or recipe['compression']!=manifest['compression'] or recipe['profile']!=manifest['profile']:
            raise ValueError('fixed control/compiler/profile/codec changed')
        transform=support.module('composition_literal_transform',inputs/'transform.py').transform
        candidate_readable=support.read(inputs/'candidate.c');expected_readable,transform_meta=transform(support.read(selected/'engine.c'))
        if candidate_readable!=expected_readable:raise ValueError('candidate differs outside seven literal sites')
        report['candidate']['source_transform']=transform_meta
        control=out/'control'
        command=[sys.executable,'-I','-B',str(selected/'build.py'),'--out',str(control),'--dev']
        result=support.run(command,out,timeout=240)
        (out/'control.stdout').write_bytes(result.stdout);(out/'control.stderr').write_bytes(result.stderr)
        if result.returncode:raise ValueError('unchanged control reproduction failed')
        built=json.loads((control/'build.json').read_text())
        if not built['complete'] or len(built['attempts'])!=2 or not built['diagnostic_exact_control']:raise ValueError('old control repeated builds incomplete')
        report['control']={'complete':True,'independent_attempts':2,'DEV_independent_attempts':2,
            'expected':recipe['expected'],'build_receipt_sha256':support.sha((control/'build.json').read_bytes())};save()
        policy=support.module('composition_literal_alpha',inputs/'policy.py')
        lexer=support.module('composition_fixed_lexer',inputs/'control/engines/scripts/rename_c.py')
        literal=support.module('composition_literal_pack',inputs/'control/engines/compact/tiny-a/pack_stream.py').source_literal
        fixed=json.loads((inputs/'policy.json').read_text());first=None;attempts=[];qualified=[]
        for index in (1,2):
            directory=out/('candidate-'+str(index));directory.mkdir()
            before,observations,counters=support.generate(inputs,directory/'preprocess')
            after,metadata=policy.transform_source(before,lexer=lexer,readable=candidate_readable)
            (directory/'before-alpha.c').write_bytes(before);(directory/'main.c').write_bytes(after)
            row={'attempt':index,'preprocess':observations,'counter_removal':counters,'alpha':metadata,
                'source_bytes':len(after),'source_sha256':support.sha(after),'before_alpha_bytes':len(before),'before_alpha_sha256':support.sha(before)}
            attempts.append(row);report['candidate']['attempts']=attempts;save()
            if index==1:
                report['candidate']['header_gate']=support.header_gate(before,after,recipe,fixed['mapping'],lexer,directory/'header',candidate_readable);save()
            natives=[]
            for label,data in (('before',before),('after',after)):
                native_dir=directory/label;native_dir.mkdir()
                result=support.run(recipe['compiler'],native_dir,data)
                (native_dir/'compiler.stderr').write_bytes(result.stderr)
                if result.returncode:raise ValueError('candidate compile failed: '+label)
                natives.append((native_dir/'x').read_bytes())
            if natives[0]!=natives[1]:raise ValueError('candidate before/after-alpha full-native identity differs')
            row.update(native_bytes=len(natives[1]),native_sha256=support.sha(natives[1]),alpha_full_native_equal=True,
                old_native_equal=natives[1]==(control/'native/x').read_bytes())
            qualified.append((directory,after,natives[1],row));save()
        # Codec starts only after both independent alias/native boundary checks.
        for directory,after,native,row in qualified:
            whole,script,kind=support.package(after,selected,recipe,literal,directory/'decoder')
            (directory/'x').write_bytes(whole);(directory/'x').chmod(0o755);(directory/'bootstrap.py').write_bytes(script)
            row.update(whole_bytes=len(whole),whole_sha256=support.sha(whole),bootstrap_bytes=len(script),bootstrap_sha256=support.sha(script),literal=kind)
            current=(after,native,whole,script)
            if first is None:first=current
            elif current!=first:raise ValueError('independent sole candidate outputs differ')
        selected_out=out/'selected';selected_out.mkdir();(selected_out/'native').mkdir()
        for name,data in (('main.c',first[0]),('native/x',first[1]),('x',first[2]),('bootstrap.py',first[3])):(selected_out/name).write_bytes(data)
        report['candidate'].update(independent_attempts=2,readable_bytes=len(candidate_readable),readable_sha256=support.sha(candidate_readable),
            source_bytes=len(first[0]),source_sha256=support.sha(first[0]),native_bytes=len(first[1]),native_sha256=support.sha(first[1]),
            whole_bytes=len(first[2]),whole_sha256=support.sha(first[2]),bootstrap_sha256=support.sha(first[3]),
            source_saved_bytes=recipe['expected']['source_bytes']-len(first[0]),whole_saved_bytes=recipe['expected']['whole_bytes']-len(first[2]),
            shipping_core_runtime_qualified=False,DEV_candidate_compiles=0,engine_runs=0,under_4096_bytes=len(first[2])<=4096)
        if any(not row['terminal'] or not row['group_absent'] for row in support.COMMANDS):raise ValueError('owned tool group still live')
        report.update(complete=True,owned_live_handles=0,semantic_tests=0,engine_runs=0)
        save();print(json.dumps({'complete':True,'out':str(out),'control_whole_bytes':recipe['expected']['whole_bytes'],
            'candidate_whole_bytes':len(first[2]),'whole_saved_bytes':recipe['expected']['whole_bytes']-len(first[2]),
            'source_bytes':len(first[0]),'native_bytes':len(first[1]),'engine_runs':0,'cost_sha256':support.sha((out/'cost.json').read_bytes())}),flush=True)
    except BaseException as error:
        report['error']=repr(error);save();raise

if __name__=='__main__':main()
