#!/usr/bin/env python3
"""Reproduce one document-specified codec per frozen source class, without native compilation."""
import argparse
import hashlib
import importlib.util
import json
import lzma
import os
from pathlib import Path
import platform
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
HEAD='a3546f1f409337bc0cf176cdfefc14bbdd1a3693'
NICE={'head-A':273,'head-B':32,'head-C':64,'head-E':32,'head-F':32,'current-F5051':32}
SETTINGS={'format':'lzma-alone','filter':'LZMA1','preset':9,'extreme':True,'lc':2,'lp':0,'pb':0,
          'mf':'BT4','check':'NONE','dictionary_bytes':67108864,'prefix_bytes':77,
          'header_hex':'0200000004ffffffffffffffff'}

def sha(data):return hashlib.sha256(data).hexdigest()

def read(path):
    raw=path.read_bytes();data=raw.replace(b'\r\n',b'\n')
    if b'\r' in data:raise ValueError('lone CR in ordinary input: '+str(path))
    return data

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result);return result

def source(case,root,directory):
    """The original fixed source operations; no native compiler or builder main."""
    tree=root/case['control'];entry=tree/case['entry'];recipe=json.loads(read(entry/'recipe.json'))
    if recipe['expected']!=case['baseline_expected']:raise ValueError('frozen expected class changed')
    for name,pin in recipe['local_input_sha256'].items():
        if sha(read(entry/name))!=pin:raise ValueError('local source pin: '+name)
    for name,pin in recipe['helper_sha256'].items():
        if sha(read(tree/name))!=pin:raise ValueError('source helper pin: '+name)
    tag=case['label'].replace('-','_');family=case['family']
    specialize=module(tag+'_specialize',tree/'engines/scripts/specialize.py').specialize_c
    compact=module(tag+'_minify',tree/'engines/scripts/minify.py').compact_source
    lexer=module(tag+'_lexer',tree/'engines/scripts/rename_c.py')
    canonical=read(entry/'engine.c')
    command=recipe['preprocessor']+['-DDEV=0']
    if family=='B':command+=['main.c','-o','x']
    active,observations=specialize({'main.c':canonical},directory,command,os.environ.copy())
    data=compact(active['main.c'],'c');details={}
    if family=='B':
        strip=module(tag+'_strip',tree/'engines/compact/tiny-b/generate.py').strip_counters
        data,details['counters']=strip(data)
        reference=module(tag+'_reference',tree/'engines/scripts/fixed_shipping_alpha.py')
        data,details['alpha']=reference.transform_source(data,family='B',lexer=lexer)
        storage=module(tag+'_storage',entry/'shipping_storage.py').transform_source
        data,details['storage']=storage(data,family='B',lexer=lexer,reference=reference,readable=canonical)
    elif family=='F':
        strip=module(tag+'_builder',entry/'build.py').strip_counters
        data,details['counters']=strip(data);files={'main.c':data}
        for old,new in recipe['resource_literals']:
            count=sum(token==old for _,_,token in lexer._identifier_spans(files['main.c'].decode()))
            if count!=recipe['resource_token_counts'][old]:raise ValueError('fixed F resource count: '+old)
            files=lexer._replace(files,old,new)
        for old,new in recipe['function_spellings']:files=lexer._replace(files,old,new)
        data=files['main.c'];alpha=module(tag+'_alpha',entry/'shipping_alpha.py').transform_source
        data,details['alpha']=alpha(data,family='F',lexer=lexer,readable=canonical)
        storage_path=entry/'shipping_storage.py' if case['label']=='current-F5051' else tree/'engines/scripts/fixed_shipping_storage.py'
        storage=module(tag+'_storage',storage_path).transform_source
        data,details['storage']=storage(data,family='F',readable=canonical)
    else:
        strip=module(tag+'_strip',tree/'engines/compact/tiny-a/stitch.py').strip_dev_counters
        data,details['counters']=strip(data)
        if family=='A':
            files={'main.c':data}
            for old,new in recipe['fixed_renames']+recipe['resource_literals']+recipe['function_spellings']:
                files=lexer._replace(files,old,new)
            data=files['main.c'];alpha=module(tag+'_alpha',entry/'shipping_alpha.py').transform_source
            data,details['alpha']=alpha(data,family='A',lexer=lexer,readable=canonical)
            storage=module(tag+'_storage',tree/'engines/scripts/fixed_shipping_storage.py').transform_source
            data,details['storage']=storage(data,family='A',readable=canonical)
        else:
            reference=module(tag+'_reference',tree/'engines/scripts/fixed_shipping_alpha.py')
            if family=='C':
                alpha=module(tag+'_alpha',entry/'shipping_alpha.py').transform_source
                data,details['alpha']=alpha(data,family='C',lexer=lexer,reference=reference,readable=canonical)
            elif family=='E':data,details['alpha']=reference.transform_source(data,family='E',lexer=lexer)
            else:raise ValueError('unsupported fixed family')
    expected=case['baseline_expected']
    if len(data)!=expected['source_bytes'] or sha(data)!=expected['source_sha256']:
        raise ValueError('actual shipping source differs from fixed normal recipe: '+case['label'])
    return data,recipe,observations,details

def encode(script,compression,nice=None):
    alone=compression['format']=='lzma-alone'
    if compression['format'] not in ('xz','lzma-alone'):raise ValueError('unsupported frozen codec')
    settings={'id':lzma.FILTER_LZMA1 if alone else lzma.FILTER_LZMA2,'preset':9|lzma.PRESET_EXTREME,
              'lc':compression['lc'],'lp':compression['lp'],'pb':compression['pb']}
    if nice is not None:settings.update(dict_size=67108864,mf=lzma.MF_BT4,nice_len=nice)
    payload=lzma.compress(script,format=lzma.FORMAT_ALONE if alone else lzma.FORMAT_XZ,
                          check=lzma.CHECK_NONE if alone else lzma.CHECK_CRC64,filters=[settings])
    if alone and payload[:13]!=bytes.fromhex(SETTINGS['header_hex']):raise ValueError('LZMA-alone header changed')
    return payload

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve()
    if not args.out.is_absolute() or out.exists() or any((p/'.git').exists() for p in (out,*out.parents)):
        parser.error('a new absolute external output outside Git is required')
    if platform.system()!='Linux' or platform.machine() not in ('x86_64','amd64'):parser.error('fixed Linux x86-64 target required')
    fixed=json.loads(read(HERE/'admission.json'))
    if fixed['head']!=HEAD or fixed['candidate']!=SETTINGS or fixed['repetitions']!=2 or fixed['native_compile_limit']!=0 or fixed['engine_limit']!=0 or fixed['codec_sweep']:
        raise ValueError('fixed codec scope changed')
    if {c['label']:c['candidate_nice_len'] for c in fixed['cases']}!=NICE or len(fixed['cases'])!=6:
        raise ValueError('fixed six source classes/nice lengths changed')
    files={}
    for name,pin in fixed['source_files'].items():
        data=read(HERE/name)
        if {'bytes':len(data),'sha256':sha(data)}!=pin:raise ValueError('ordinary source changed: '+name)
        files[name]=data
    for name,pin in fixed['new_source_sha256'].items():
        data=read(HERE/name)
        if sha(data)!=pin:raise ValueError('fixed new producer source changed: '+name)
        files[name]=data
    if set(fixed['new_source_sha256'])!={'build.py','decode.py'} or len(files)!=51:raise ValueError('ordinary source closure changed')
    files['admission.json']=read(HERE/'admission.json')
    out.mkdir(parents=True);inputs=out/'inputs';inputs.mkdir()
    report={'complete':False,'stage':fixed['stage'],'head':HEAD,'ordinary_inputs':{},'cases':{},
            'C_preprocessor_invocations':0,'native_compiles':0,'engine_runs':0,'DEV_runs':0,
            'bootstrap_runs':0,'games':0,'benchmarks':0,'codec_compressions':0,'strict_pure_decodes':0,
            'variant_count_per_source_class':1,'no_spelling_or_source_changes':True,
            'native_identity_or_runtime_acceptance':False,'codec_checksum_contract_changed':True}
    def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    for name,data in files.items():
        target=inputs/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        report['ordinary_inputs'][name]={'bytes':len(data),'sha256':sha(data)}
    save()
    try:
        decoder=module('codec_strict_decoder',inputs/'decode.py');prefix=read(inputs/'launcher.sh')
        if len(prefix)!=77:raise ValueError('candidate prefix must include all77bytes')
        for case in fixed['cases']:
            label=case['label'];directory=out/label;directory.mkdir()
            data,recipe,observations,details=source(case,inputs,directory/'preprocess')
            report['C_preprocessor_invocations']+=len(observations)
            entry=inputs/case['control']/case['entry'];template=read(entry/'bootstrap.py.in');marker=b'__ROVE_SOURCE_LITERAL__'
            if template.count(marker)!=1:raise ValueError('exact bootstrap marker count changed')
            literal=module(label.replace('-','_')+'_literal',inputs/case['control']/'engines/compact/tiny-a/pack_stream.py').source_literal
            expression,kind=literal(data);script=template.replace(marker,expression.encode());expected=case['baseline_expected']
            if sha(script)!=expected['bootstrap_sha256']:raise ValueError('baseline bootstrap exact identity changed')
            (directory/'main.c').write_bytes(data);(directory/'bootstrap.py').write_bytes(script)
            row={'family':case['family'],'source_class':case['source_class'],'source_bytes':len(data),'source_sha256':sha(data),
                 'bootstrap_bytes':len(script),'bootstrap_sha256':sha(script),'compiler_argv':recipe['compiler'],
                 'source_literal_kind':kind,'preprocessor':observations,'fixed_source_generation':details,
                 'baseline':{'compression':recipe['compression'],'attempts':[]},
                 'candidate':{'compression':{**SETTINGS,'nice_len':case['candidate_nice_len']},'attempts':[]},
                 'native_compiles':0,'engine_runs':0}
            report['cases'][label]=row;save()
            for mode in ('baseline','candidate'):
                selected=row[mode];old=mode=='baseline';launcher=read(entry/'launcher.sh') if old else prefix
                first=None
                for index in (1,2):
                    report['codec_compressions']+=1;save()
                    payload=encode(script,selected['compression'],None if old else case['candidate_nice_len'])
                    whole=launcher+payload
                    if old and (len(whole)!=expected['whole_bytes'] or sha(whole)!=expected['whole_sha256']):raise ValueError('baseline complete whole pin differs: '+label)
                    report['strict_pure_decodes']+=1
                    proof=decoder.verify(whole,launcher,data,recipe['compiler'],script,expected_format='alone' if selected['compression']['format']=='lzma-alone' else 'xz')
                    attempt=directory/mode/('attempt-'+str(index));attempt.mkdir(parents=True)
                    (attempt/'x').write_bytes(whole);(attempt/'x').chmod(0o755)
                    proof_raw=(json.dumps(proof,indent=2)+'\n').encode();(attempt/'decode-proof.json').write_bytes(proof_raw)
                    selected['attempts'].append({'attempt':index,'whole_bytes':len(whole),'whole_sha256':sha(whole),
                        'prefix_bytes':len(launcher),'payload_bytes':len(payload),'payload_sha256':sha(payload),
                        'decode_proof_sha256':sha(proof_raw)})
                    if first is None:first=whole
                    elif whole!=first:raise ValueError('independent complete codec output differs: '+label+'/'+mode)
                    save()
                selected.update(whole_bytes=len(first),whole_sha256=sha(first),independent_whole_reproduced=True)
                (directory/mode/'x').write_bytes(first);(directory/mode/'x').chmod(0o755)
            gain=row['baseline']['whole_bytes']-row['candidate']['whole_bytes']
            row.update(whole_saved_bytes=gain,remaining_over4096=row['candidate']['whole_bytes']-4096,
                       exact_same_source_bootstrap_and_argv=True,qualified_runtime=False)
            save();print(json.dumps({'label':label,'baseline':row['baseline']['whole_bytes'],'candidate':row['candidate']['whole_bytes'],
                'saved':gain,'whole_sha256':row['candidate']['whole_sha256'],'source_sha256':sha(data),'native_compiles':0,'engine_runs':0}),flush=True)
        report.update(complete=True,all_fixed_sources_and_baseline_wholes_exact=True,all_independent_wholes_reproduced=True,
                      checksum_note='LZMA-alone has no container checksum; strict normal-file restoration does not preserve XZ CRC64 corruption detection')
        save();print(json.dumps({'complete':True,'results_sha256':sha((out/'results.json').read_bytes()),
                               'preprocessor_invocations':report['C_preprocessor_invocations'],'native_compiles':0,'engine_runs':0}),flush=True)
        return 0
    except BaseException as error:
        report.update(complete=False,error=repr(error))
        try:save()
        except BaseException:pass
        raise

if __name__=='__main__':raise SystemExit(main())
