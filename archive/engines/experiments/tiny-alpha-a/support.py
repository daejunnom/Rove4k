"""Frozen A-only producer primitives; no artifact/report inputs or alias search."""
import ast
import hashlib
import importlib.util
import json
import lzma
import os
from pathlib import Path
import signal
import subprocess
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent


def sha(data):return hashlib.sha256(data).hexdigest()


def read(path):
    raw=Path(path).read_bytes();data=raw.replace(b'\r\n',b'\n')
    if b'\r' in data:raise ValueError('lone CR: '+str(path))
    return data


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


def run(command,directory,input_data=None,timeout=90):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    process=subprocess.Popen(command,cwd=directory,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
        start_new_session=True,env={**os.environ,'LC_ALL':'C','TZ':'UTC','SOURCE_DATE_EPOCH':'0'})
    try:stdout,stderr=process.communicate(input_data,timeout=timeout)
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


def closure(destination):
    destination=Path(destination);destination.mkdir(parents=True)
    recipe=json.loads(read(HERE/'recipe.json'));rows={}
    for group,prefix in (('control_files','control'),('reference_files','reference')):
        for relative,pin in recipe[group].items():
            data=read(HERE/prefix/relative)
            if len(data)!=pin['bytes'] or sha(data)!=pin['sha256']:raise ValueError('frozen input changed: '+relative)
            target=destination/prefix/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            rows[prefix+'/'+relative]={'bytes':len(data),'sha256':sha(data)}
    for name in ('recipe.json','support.py'):
        data=read(HERE/name);(destination/name).write_bytes(data);rows[name]={'bytes':len(data),'sha256':sha(data)}
    return recipe,rows


def entry(root,family):return Path(root)/'control/engines/compact'/('tiny-entry-'+family.lower())


def generate(root,family,directory):
    """Exact existing shipping generation, preprocessing only; no native build."""
    root=Path(root);selected=entry(root,family);recipe=json.loads(read(selected/'recipe.json'))
    helpers=root/'control/engines/scripts'
    specialize=module('af_specialize_'+family,helpers/'specialize.py').specialize_c
    compact=module('af_compact_'+family,helpers/'minify.py').compact_source
    lexer=module('af_lexer_'+family,helpers/'rename_c.py')
    source=read(selected/'engine.c')
    if sha(source)!=recipe['expected']['readable_sha256']:raise ValueError('readable pin changed')
    active,observations=specialize({'main.c':source},directory,recipe['preprocessor']+['-DDEV=0'],os.environ.copy())
    data=compact(active['main.c'],'c')
    if family!='A':raise ValueError('only frozen A input admitted')
    strip=module('a_stitch',root/'control/engines/compact/tiny-a/stitch.py').strip_dev_counters
    data,_=strip(data);pairs=recipe['fixed_renames']+recipe['resource_literals']+recipe['function_spellings']
    files={'main.c':data}
    for old,new in pairs:files=lexer._replace(files,old,new)
    data=files['main.c']
    if len(data)!=recipe['expected']['source_bytes'] or sha(data)!=recipe['expected']['source_sha256']:
        raise ValueError('exact historical shipping source differs')
    return data,observations


def header_gate(source,candidate,compiler,mapping,lexer,directory,*,family,configured_preprocessor,readable):
    """Full PP inverse: identifiers only, preserving exact numeric spellings."""
    if compiler!=['cc','-Os','-x','c','-','-o','x','-s'] or compiler.count('-o')!=1:raise ValueError('unexpected fixed compiler argv')
    index=compiler.index('-o')
    if compiler[index:index+2]!=['-o','x']:raise ValueError('unexpected compiler output pair')
    base=compiler[:index]+compiler[index+2:]
    outputs={};observations={};directory=Path(directory)
    expected_configuration=['cc','-std=c11','-Os','-pthread','-DWORKERS=2','-DTT_BITS=18']
    if family!='A' or configured_preprocessor!=expected_configuration:
        raise ValueError('configured preprocessing profile changed')
    # This is a SEPARATE profile probe of the unchanged readable input. The
    # final native compiler/PP command below receives no additional -D flags.
    probe_command=configured_preprocessor+['-DDEV=0','-x','c','-','-E','-dM']
    probe=run(probe_command,directory,readable)
    (directory/'configured-profile-macros.txt').write_bytes(probe.stdout)
    (directory/'configured-profile-macros.stderr').write_bytes(probe.stderr)
    if probe.returncode:raise ValueError('configured resource probe failed')
    profile_values={}
    for line in probe.stdout.decode().splitlines():
        if line.startswith('#define '):
            parts=line.split(None,2)
            if parts[1] in ('WORKERS','TT_BITS','PLY'):profile_values[parts[1]]=parts[2] if len(parts)>2 else ''
    if profile_values!={'WORKERS':'2','TT_BITS':'18','PLY':'128'}:
        raise ValueError('configured resource macro values changed')
    for name,data in (('control',source),('candidate',candidate)):
        for kind,flags in (('expanded',['-E','-P']),('macros',['-E','-dM'])):
            command=base+flags;result=run(command,directory,data)
            (directory/(name+'-'+kind+'.stderr')).write_bytes(result.stderr)
            (directory/(name+'-'+kind+'.txt')).write_bytes(result.stdout)
            if result.returncode:raise ValueError('full preprocessing failed: '+name+'/'+kind)
            outputs[name,kind]=result.stdout
            observations[name+'_'+kind]={'command':command,'bytes':len(result.stdout),'sha256':sha(result.stdout)}
    macro_values={};macro_names=set()
    for line in outputs['control','macros'].decode().splitlines():
        if line.startswith('#define '):
            parts=line.split(None,2);macro_names.add(parts[1].split('(',1)[0])
            if parts[1] in ('WORKERS','TT_BITS','PLY'):macro_values[parts[1]]=parts[2] if len(parts)>2 else ''
    # Earlier specialization consumed command-line resource definitions; their
    # uses were already made literal by the historical builders. Do not add
    # definitions to the actual final compiler to manufacture their presence.
    expected_final={'PLY':'128'}
    if macro_values!=expected_final:raise ValueError('literal final resource macro boundary changed')
    expanded_names={token for _,_,token in lexer._identifier_spans(outputs['control','expanded'].decode())}
    captures=sorted(set(mapping.values())&(expanded_names|macro_names))
    if captures:raise ValueError('fixed alias captured by actual headers/macros: '+','.join(captures))
    if sorted(outputs['control','macros'].splitlines())!=sorted(outputs['candidate','macros'].splitlines()):
        raise ValueError('complete final macro definitions changed')
    inverse={'expanded.c':outputs['candidate','expanded']}
    for old,new in mapping.items():inverse=lexer._replace(inverse,new,old)
    restored=inverse['expanded.c'];original=outputs['control','expanded']
    (directory/'candidate-expanded-inverse.txt').write_bytes(restored)
    if restored!=original:
        offset=next((i for i,(a,b) in enumerate(zip(restored,original)) if a!=b),min(len(restored),len(original)))
        raise ValueError('strict full-PP inverse mismatch at '+str(offset))
    return {'pass':True,'removed_output_pair_only':['-o','x'],'retained_compiler_options':base,
            'final_resource_macro_values':macro_values,'expected_final_resource_macros':expected_final,
            'separate_configured_profile_probe':{'command':probe_command,'resource_macro_values':profile_values,
                'bytes':len(probe.stdout),'sha256':sha(probe.stdout),'actual_native_compiler_modified':False},
            'fresh_alias_capture':captures,'full_preprocessed_bytes_inverse_equal':True,
            'numeric_inverse_replacements':0,'final_macro_definitions_equal':True,
            'macro_history_coverage':'final definitions only; exact expansion and full-native gates are independent',
            'expanded_sha256':sha(original),'inverse_sha256':sha(restored),'observations':observations}


def package(source,selected,recipe,literal):
    template=read(Path(selected)/'bootstrap.py.in');prefix=read(Path(selected)/'launcher.sh');compression=recipe['compression']
    marker=b'__ROVE_SOURCE_LITERAL__'
    if template.count(marker)!=1:raise ValueError('source literal marker changed')
    expression,kind=literal(source);script=template.replace(marker,expression.encode());ast.parse(script)
    expected={'format':'lzma-alone','filter':'LZMA1','preset':9,'extreme':True,'lc':2,'lp':0,'pb':0,'check':'NONE',
              'dictionary_bytes':67108864,'header_hex':'0200000004ffffffffffffffff'}
    if compression!=expected or len(prefix)!=77:raise ValueError('fixed A codec/prefix changed')
    payload=lzma.compress(script,format=lzma.FORMAT_ALONE,check=lzma.CHECK_NONE,
        filters=[{'id':lzma.FILTER_LZMA1,'preset':9|lzma.PRESET_EXTREME,'lc':2,'lp':0,'pb':0}])
    if payload[:13]!=bytes.fromhex(expected['header_hex']):raise ValueError('ALONE header changed')
    format=lzma.FORMAT_ALONE;command=['lzma','-dc']
    decoder=lzma.LZMADecompressor(format=format)
    if decoder.decompress(payload)!=script or not decoder.eof or decoder.unused_data:raise ValueError('strict payload decode differs')
    cli=subprocess.run(command,input=payload,capture_output=True,timeout=15)
    if cli.returncode or cli.stderr or cli.stdout!=script:raise ValueError('independent CLI decode differs')
    return prefix+payload,script,kind
