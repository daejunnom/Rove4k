"""Closed BCE baseline/PP primitives; no candidate codec or engine path."""
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
FAMILIES=('B','C','E')


def sha(data):return hashlib.sha256(data).hexdigest()


def read(path):
    data=Path(path).read_bytes().replace(b'\r\n',b'\n')
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
    if recipe['control_file_count']!=36 or len(recipe['control_files'])!=36 or len(recipe['reference_files'])!=5:
        raise ValueError('closed ordinary inventory changed')
    for group,prefix in [('control_files','control'),('reference_files','reference')]:
        for relative,pin in recipe[group].items():
            data=read(HERE/prefix/relative)
            if len(data)!=pin['bytes'] or sha(data)!=pin['sha256']:raise ValueError('frozen input changed: '+relative)
            target=destination/prefix/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            rows[prefix+'/'+relative]={'bytes':len(data),'sha256':sha(data)}
    for name in ['recipe.json','support.py']:
        data=read(HERE/name);(destination/name).write_bytes(data);rows[name]={'bytes':len(data),'sha256':sha(data)}
    return recipe,rows


def entry(root,family):
    if family not in FAMILIES:raise ValueError('unknown BCE family')
    return Path(root)/'control/engines/compact'/('tiny-entry-'+family.lower())


def generate(root,family,directory):
    root=Path(root);selected=entry(root,family);recipe=json.loads(read(selected/'recipe.json'));helpers=root/'control/engines/scripts'
    specialize=module('bce_specialize_'+family,helpers/'specialize.py').specialize_c
    compact=module('bce_compact_'+family,helpers/'minify.py').compact_source
    lexer=module('bce_lexer_'+family,helpers/'rename_c.py');source=read(selected/'engine.c')
    if sha(source)!=recipe['expected']['readable_sha256']:raise ValueError('readable pin changed')
    argv=recipe['preprocessor']+['-DDEV=0']+(['main.c','-o','x'] if family=='B' else [])
    active,observations=specialize({'main.c':source},directory,argv,os.environ.copy());data=compact(active['main.c'],'c')
    if family=='B':strip=module('bce_B_strip',root/'control/engines/compact/tiny-b/generate.py').strip_counters
    else:strip=module('bce_CE_strip',root/'control/engines/compact/tiny-a/stitch.py').strip_dev_counters
    data,_=strip(data);alpha=module('bce_baseline89_'+family,helpers/'fixed_shipping_alpha.py').transform_source
    data,_=alpha(data,family=family,lexer=lexer)
    if len(data)!=recipe['expected']['source_bytes'] or sha(data)!=recipe['expected']['source_sha256']:
        raise ValueError('maintained final shipping source differs')
    return data,observations


def macro_records(raw,reference):
    """Recognize directives with the independent comment/literal-aware scanner.

    Preserve each full phase-two logical definition and its multiplicity.
    Per-name sequences retain differing duplicate-definition order separately.
    """
    if b'\r' in raw:raise ValueError('unexpected CR in compiler macro dump')
    text=raw.decode();cursor=0;definitions=[];names={}
    for kind,part in reference._opaque_parts(text):
        if kind!='directive':raise ValueError('opaque text outside macro directive')
        start=text.find(part,cursor);gap=text[cursor:start]
        if start<cursor or gap.strip():raise ValueError('non-directive macro dump text')
        prefix=gap.rsplit('\n',1)[-1]
        logical=reference._logical(prefix+part)[0]
        if logical.endswith('\n'):logical=logical[:-1]
        match=re.match(r'^[ \t]*#[ \t]*define[ \t]+([A-Za-z_][A-Za-z0-9_]*)',logical)
        if not match:raise ValueError('non-definition compiler directive')
        definition=logical.encode();definitions.append(definition)
        names.setdefault(match[1],[]).append(definition);cursor=start+len(part)
    if text[cursor:].strip():raise ValueError('trailing non-directive macro text')
    return definitions,Counter(definitions),names


def resources(definitions):
    values={name:[] for name in ['WORKERS','TT_BITS','PLY','DEV']}
    for line in definitions:
        match=re.fullmatch(rb'#define (WORKERS|TT_BITS|PLY|DEV) (.*)',line)
        if match:values[match[1].decode()].append(match[2].decode())
    if values!={'WORKERS':['2'],'TT_BITS':['18'],'PLY':['128'],'DEV':['0']}:
        raise ValueError('resource values/counts changed: '+repr(values))
    return values


def header_gate(source,candidate,compiler,mapping,lexer,directory,*,family,configured_preprocessor,readable,reference):
    expected=['cc','-std=c11','-Os','-pthread','-DWORKERS=2','-DTT_BITS=18']+(['-mavx2'] if family=='C' else [])
    if family not in FAMILIES or configured_preprocessor!=expected or compiler!=expected+['-DDEV=0','-x','c','-','-o','x']:
        raise ValueError('original unstripped compiler/profile changed')
    base=compiler[:-2];directory=Path(directory);outputs={};observations={}
    probe_command=configured_preprocessor+['-DDEV=0','-x','c','-','-E','-dM'];probe=run(probe_command,directory,readable)
    (directory/'configured-profile-macros.txt').write_bytes(probe.stdout);(directory/'configured-profile-macros.stderr').write_bytes(probe.stderr)
    if probe.returncode:raise ValueError('separate profile probe failed')
    profile_defs,_,_=macro_records(probe.stdout,reference);profile=resources(profile_defs)
    for name,data in [('control',source),('candidate',candidate)]:
        for kind,flags in [('expanded',['-E','-P']),('macros',['-E','-dM'])]:
            command=base+flags;result=run(command,directory,data)
            (directory/(name+'-'+kind+'.txt')).write_bytes(result.stdout);(directory/(name+'-'+kind+'.stderr')).write_bytes(result.stderr)
            if result.returncode:raise ValueError('actual preprocessing failed: '+name+'/'+kind)
            outputs[name,kind]=result.stdout;observations[name+'_'+kind]={'command':command,'bytes':len(result.stdout),'sha256':sha(result.stdout)}
    defs,counts,byname=macro_records(outputs['control','macros'],reference)
    other_defs,other_counts,other_byname=macro_records(outputs['candidate','macros'],reference)
    values=resources(defs);resources(other_defs)
    expanded={token for _,_,token in lexer._identifier_spans(outputs['control','expanded'].decode())}
    macro_words={x.decode() for x in re.findall(rb'[A-Za-z_][A-Za-z0-9_]*',b'\n'.join(defs))}
    captures=sorted(set(mapping.values())&(expanded|macro_words))
    if captures:raise ValueError('fixed alias captured by header/macro words: '+','.join(captures))
    if counts!=other_counts or byname!=other_byname:raise ValueError('complete raw logical definition Counter/per-name order changed')
    inverse={'expanded.c':outputs['candidate','expanded']}
    for old,new in mapping.items():inverse=lexer._replace(inverse,new,old)
    restored=inverse['expanded.c'];original=outputs['control','expanded'];(directory/'candidate-expanded-inverse.txt').write_bytes(restored)
    if restored!=original:raise ValueError('strict full-PP alias inverse mismatch')
    counter=[{'definition_hex':key.hex(),'count':value} for key,value in sorted(counts.items())]
    return {'pass':True,'original_unstripped_compiler_unchanged':True,'removed_output_pair_only':['-o','x'],
        'fresh_alias_capture':captures,'full_preprocessed_bytes_inverse_equal':True,'numeric_inverse_replacements':0,
        'final_macro_raw_logical_definition_Counter_equal':True,'per_name_definition_sequence_equal':True,
        'definitions':len(defs),'unique_definitions':len(counts),'duplicate_occurrences':sum(v-1 for v in counts.values()),
        'definition_counter_sha256':sha(json.dumps(counter,sort_keys=True).encode()),
        'raw_macro_order_equal':outputs['control','macros']==outputs['candidate','macros'],'logical_macro_order_equal':defs==other_defs,
        'final_resource_values_and_counts':values,'separate_profile_probe':{'command':probe_command,'resource_values_and_counts':profile,'sha256':sha(probe.stdout)},
        'expanded_sha256':sha(original),'inverse_sha256':sha(restored),'observations':observations}
