#!/usr/bin/env python3
"""One fixed shipping alpha/resource policy against three frozen controls.

No live maintained entry is a dependency. Each exact control is reproduced
twice by its unchanged frozen builder. Candidate names/flags/codec are fixed;
preprocessor disagreement or a complete native SHA mismatch stops that family.
This command never launches a chess engine.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
import lzma
import os
from pathlib import Path
import platform
import signal
import struct
import subprocess
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent


def sha(data):return hashlib.sha256(data).hexdigest()


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


def read_owned(path):
    raw=path.read_bytes();data=raw.replace(b'\r\n',b'\n')
    if b'\r' in data:raise ValueError('lone CR in owned input: '+str(path))
    return data


def run(command,directory,input_data=None,timeout=180):
    directory.mkdir(parents=True,exist_ok=True)
    process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
        cwd=directory,start_new_session=True,env={**os.environ,'LC_ALL':'C','TZ':'UTC','SOURCE_DATE_EPOCH':'0'})
    try:
        stdout,stderr=process.communicate(input_data,timeout=timeout)
    except BaseException:
        try:os.killpg(process.pid,signal.SIGTERM)
        except ProcessLookupError:pass
        try:process.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            process.communicate()
        raise
    return subprocess.CompletedProcess(command,process.returncode,stdout,stderr)


def first_difference(a,b):
    return next((i for i,(x,y) in enumerate(zip(a,b)) if x!=y), min(len(a),len(b)))


def elf_sections(data):
    if data[:6]!=b'\x7fELF\x02\x01':return {}
    offset=struct.unpack_from('<Q',data,40)[0]
    stride,count,names_index=struct.unpack_from('<HHH',data,58)
    records=[struct.unpack_from('<IIQQQQIIQQ',data,offset+i*stride) for i in range(count)]
    names=records[names_index];strings=data[names[4]:names[4]+names[5]]
    output={}
    for row in records:
        end=strings.find(b'\0',row[0]);name=strings[row[0]:end].decode('ascii','replace')
        content=b'' if row[1]==8 else data[row[4]:row[4]+row[5]]
        output[name]={'type':row[1],'flags':row[2],'address':row[3],'offset':row[4],
                      'size':row[5],'sha256':sha(content)}
    return output


def header_gate(source,candidate,compiler,mapping,lexer,directory):
    """Strict full-PP byte equality after identifier-only alpha inversion.

    Macro final-state capture is an additional check, not a claim to enumerate
    every transient macro definition. No inverse numeric replacement is used.
    All original compiler options except the output path remain unchanged.
    """
    if compiler[-2:]!=['-o','x'] or compiler[-5:-2]!=['-x','c','-']:
        raise ValueError('unexpected fixed compiler output/stdin layout')
    base=compiler[:-2]
    outputs={};observations={}
    for name,data in (('control',source),('candidate',candidate)):
        pp_command=base+['-E','-P']
        macro_command=base+['-E','-dM']
        for kind,command in (('expanded',pp_command),('macros',macro_command)):
            process=run(command,directory,data,90)
            (directory/(name+'-'+kind+'.stderr')).write_bytes(process.stderr)
            (directory/(name+'-'+kind+'.txt')).write_bytes(process.stdout)
            if process.returncode:raise ValueError('header preprocessing failed: '+name+'/'+kind)
            outputs[name,kind]=process.stdout
            observations[name+'_'+kind]={'command':command,'bytes':len(process.stdout),'sha256':sha(process.stdout)}
    macro_values={}
    macro_names=set()
    for line in outputs['control','macros'].decode().splitlines():
        if line.startswith('#define '):
            parts=line.split(None,2)
            macro_names.add(parts[1].split('(',1)[0])
            if parts[1] in ('WORKERS','TT_BITS','PLY'):
                macro_values[parts[1]]=parts[2] if len(parts)>2 else ''
    if macro_values!={'WORKERS':'2','TT_BITS':'18','PLY':'128'}:
        raise ValueError('actual compiler resource macro values differ')
    fresh=set(mapping.values())
    expanded_names={token for _,_,token in lexer._identifier_spans(outputs['control','expanded'].decode())}
    captures=sorted(fresh & (expanded_names|macro_names))
    if captures:raise ValueError('fresh alias already belongs to actual headers/macros: '+','.join(captures))
    if sorted(outputs['control','macros'].splitlines())!=sorted(outputs['candidate','macros'].splitlines()):
        raise ValueError('complete final macro definitions changed')
    inverse={'expanded.c':outputs['candidate','expanded']}
    for old,new in mapping.items():
        inverse=lexer._replace(inverse,new,old)
    original=outputs['control','expanded'];restored=inverse['expanded.c']
    (directory/'candidate-expanded-inverse.txt').write_bytes(restored)
    if restored!=original:
        raise ValueError('strict expanded-byte alpha equality failed at '+str(first_difference(original,restored)))
    return {'pass':True,'resource_macro_values':macro_values,'fresh_alias_capture':captures,
            'strict_full_preprocessed_alpha_inverse_bytes_equal':True,
            'expanded_control_sha256':sha(original),'expanded_inverse_sha256':sha(restored),
            'numeric_inverse_replacements':0,'final_macro_definitions_equal':True,
            'macro_history_coverage':'final definitions only; actual expansion plus full native identity are separate decisive gates',
            'observations':observations}


def package(source,template,prefix,source_literal,compression):
    expected={'format':'xz','filter':'LZMA2','preset':9,'extreme':True,'lc':3,'lp':0,'pb':2,'check':'CRC64'}
    if compression!=expected:raise ValueError('fixed control codec changed')
    expression,_=source_literal(source)
    marker=b'__ROVE_SOURCE_LITERAL__'
    if template.count(marker)!=1 or len(prefix)!=75:raise ValueError('fixed bootstrap/prefix changed')
    script=template.replace(marker,expression.encode());ast.parse(script)
    payload=lzma.compress(script,format=lzma.FORMAT_XZ,check=lzma.CHECK_CRC64,
                          filters=[{'id':lzma.FILTER_LZMA2,'preset':9|lzma.PRESET_EXTREME,'lc':3,'lp':0,'pb':2}])
    if lzma.decompress(payload,format=lzma.FORMAT_XZ)!=script:raise ValueError('fixed payload decode differs')
    return prefix+payload,script


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve()
    if not args.out.is_absolute() or out.exists() or any((p/'.git').exists() for p in (out,*out.parents)):
        parser.error('new absolute output outside any Git checkout required')
    if platform.system()!='Linux' or platform.machine() not in ('x86_64','amd64'):
        parser.error('the fixed target is Linux x86-64')
    out.mkdir(parents=True);frozen=out/'recipe';frozen.mkdir()
    recipe=json.loads(read_owned(HERE/'recipe.json'))
    if recipe['format']!=1 or recipe['control_file_count']!=35 or recipe['live_canonical_dependencies']:
        raise ValueError('unsupported closed recipe')
    report={'complete':False,'scope':'one fixed 89-alias/two-resource policy; no engine execution',
            'source_checkpoint':recipe['source_checkpoint'],'producer_inputs':{},'control_inputs':{},
            'families':{},'engine_runs':0,'native_identity_policy':'exact full original native SHA; no ELF/build-ID exception',
            'candidate_runtime_authorization':'only whole gain and native exact; separate literal-pinned verifier',
            'tools':{name:subprocess.check_output(command,text=True).splitlines()[0] for name,command in
                     {'cc':['cc','--version'],'ld':['ld','--version'],'python':['python3','--version'],
                      'xz':['xz','--version']}.items()}}
    def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        for name in ('recipe.json','build.py','policy.py','policy.json'):
            data=read_owned(HERE/name)
            if name in recipe['policy_files'] and sha(data)!=recipe['policy_files'][name]:
                raise ValueError('fixed policy source changed: '+name)
            (frozen/name).write_bytes(data);report['producer_inputs'][name]={'bytes':len(data),'sha256':sha(data)}
        if set(recipe['policy_files'])!={'policy.py','policy.json'}:
            raise ValueError('both fixed policy inputs must be explicitly pinned')
        for relative,expected in recipe['control_files'].items():
            path=Path(relative)
            if path.is_absolute() or '..' in path.parts:raise ValueError('bad closed input path')
            data=read_owned(HERE/'control'/path)
            if len(data)!=expected['bytes'] or sha(data)!=expected['sha256']:
                raise ValueError('historical control source changed: '+relative)
            target=frozen/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            report['control_inputs'][relative]={'bytes':len(data),'sha256':sha(data)}
        policy=module('alpha_frozen_policy',frozen/'policy.py')
        lexer=module('alpha_frozen_lexer',frozen/'engines/scripts/rename_c.py')
        source_literal=module('alpha_frozen_stream',frozen/'engines/compact/tiny-a/pack_stream.py').source_literal
        fixed=json.loads((frozen/'policy.json').read_text())
        if sha((frozen/'engines/scripts/rename_c.py').read_bytes())!=fixed['lexer_sha256']:
            raise ValueError('actual frozen lexer differs from fixed policy')
        mapping=fixed['mapping']
        for family in ('B','C','E'):
            row={'status':'started','control':{},'candidate':{},'native_identity_required':True}
            report['families'][family]=row;save()
            try:
                entry=frozen/('engines/compact/tiny-entry-'+family.lower())
                original=json.loads((entry/'recipe.json').read_text());expected=original['expected']
                if expected!=recipe['control_expected'][family]:raise ValueError('control expected identities changed')
                control=out/('control-'+family)
                command=[sys.executable,'-B',str(entry/'build.py'),'--out',str(control),'--dev']
                process=run(command,out,timeout=240)
                (out/('control-'+family+'.stdout')).write_bytes(process.stdout)
                (out/('control-'+family+'.stderr')).write_bytes(process.stderr)
                if process.returncode:raise ValueError('unchanged control builder failed; original stderr preserved')
                control_report=json.loads((control/'build.json').read_text())
                if not control_report['complete'] or len(control_report['attempts'])!=2:
                    raise ValueError('two control reproductions were not completed')
                source=(control/'main.c').read_bytes();native=(control/'native/x').read_bytes();whole=(control/'x').read_bytes()
                for data,key in ((source,'source'),(native,'native'),(whole,'whole')):
                    if sha(data)!=expected[key+'_sha256']:raise ValueError('exact control identity differs: '+key)
                row['control']={'complete':True,'independent_attempts':2,'build_json_sha256':sha((control/'build.json').read_bytes()),
                                'source_sha256':sha(source),'native_sha256':sha(native),'whole_sha256':sha(whole),
                                'whole_bytes':len(whole),'DEV':'unchanged control source/native independently reproduced twice',
                                'dev_source_sha256':expected['dev_source_sha256'],'dev_native_sha256':expected['dev_native_sha256']}
                candidate,metadata=policy.transform_source(source,family=family,lexer=lexer)
                candidate_root=out/('candidate-'+family);candidate_root.mkdir()
                row['candidate']['policy']=metadata
                row['header_gate']=header_gate(source,candidate,original['compiler'],mapping,lexer,candidate_root/'header')
                attempts=[];compiled=[]
                first=None
                for attempt in (1,2):
                    repeated,repeated_meta=policy.transform_source(source,family=family,lexer=lexer)
                    if repeated!=candidate or repeated_meta!=metadata:raise ValueError('pure candidate regeneration differs')
                    directory=candidate_root/('attempt-'+str(attempt));directory.mkdir()
                    (directory/'main.c').write_bytes(repeated)
                    native_dir=directory/'native';native_dir.mkdir()
                    process=run(original['compiler'],native_dir,repeated,90)
                    (native_dir/'compiler.stderr').write_bytes(process.stderr)
                    if process.returncode:raise ValueError('candidate compilation failed')
                    built=(native_dir/'x').read_bytes()
                    item={'attempt':attempt,'source_bytes':len(repeated),'source_sha256':sha(repeated),
                          'native_bytes':len(built),'native_sha256':sha(built),'compiler':original['compiler']}
                    attempts.append(item);row['candidate']['attempts']=attempts;save()
                    if sha(built)!=expected['native_sha256']:
                        item['identity_failure']={'expected':expected['native_sha256'],'first_differing_byte':first_difference(native,built),
                                                  'old_sections':elf_sections(native),'candidate_sections':elf_sections(built),
                                                  'exception_or_guard_weakening':False}
                        raise ValueError('candidate complete native SHA differs; family stopped before codec/runtime')
                    compiled.append((directory,repeated,built,item))
                # Both native reproductions must pass before any candidate
                # codec operation, and a later failure retains all evidence.
                for directory,repeated,built,item in compiled:
                    packed,script=package(repeated,(entry/'bootstrap.py.in').read_bytes(),(entry/'launcher.sh').read_bytes(),
                                          source_literal,original['compression'])
                    (directory/'x').write_bytes(packed);(directory/'x').chmod(0o755)
                    (directory/'bootstrap.py').write_bytes(script)
                    item.update(whole_bytes=len(packed),whole_sha256=sha(packed),bootstrap_sha256=sha(script))
                    current=(repeated,built,packed,script)
                    if first is None:first=current
                    elif current!=first:raise ValueError('two full candidate artifacts do not reproduce')
                (candidate_root/'main.c').write_bytes(first[0]);(candidate_root/'native').mkdir()
                (candidate_root/'native/x').write_bytes(first[1]);(candidate_root/'native/x').chmod(0o755)
                (candidate_root/'x').write_bytes(first[2]);(candidate_root/'x').chmod(0o755)
                (candidate_root/'bootstrap.py').write_bytes(first[3])
                row['candidate'].update(independent_attempts=2,source_bytes=len(first[0]),source_sha256=sha(first[0]),
                    native_bytes=len(first[1]),native_sha256=sha(first[1]),whole_bytes=len(first[2]),whole_sha256=sha(first[2]),
                    bootstrap_sha256=sha(first[3]),full_native_exact=True,complete_file_reproduced=True,
                    whole_saved_bytes=len(whole)-len(first[2]),source_saved_bytes=len(source)-len(first[0]),
                    DEV='not transformed; exact unchanged control DEV is separate',under_4096_bytes=len(first[2])<=4096)
                row['status']='gain_native_exact_runtime_pending' if len(first[2])<len(whole) else 'no_gain_stopped_without_runtime'
                print(json.dumps({'family':family,'status':row['status'],'control_whole_bytes':len(whole),
                                  'candidate_whole_bytes':len(first[2]),'whole_saved_bytes':len(whole)-len(first[2]),
                                  'candidate_native_exact':True}),flush=True)
            except Exception as error:
                row.update(status='stopped',error=repr(error),engine_runs=0)
                print(json.dumps({'family':family,'status':'stopped','error':repr(error)}),flush=True)
            save()
        report['complete']=True;save()
        print(json.dumps({'complete':True,'out':str(out),'results_sha256':sha((out/'results.json').read_bytes())}),flush=True)
    except Exception as error:
        report['error']=repr(error);save();raise


if __name__=='__main__':main()
