"""Fixed C-only build primitives; no engine execution or variant selection."""
import ast
from collections import Counter
import hashlib
import importlib.util
import json
import lzma
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
COMMANDS=[]

def sha(data):return hashlib.sha256(data).hexdigest()

def read(path):
    raw=Path(path).read_bytes();data=raw.replace(b'\r\n',b'\n')
    if b'\r' in data:raise ValueError('lone CR in source input')
    return data

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

def group_members(group):
    members=[]
    for path in Path('/proc').iterdir():
        if not path.name.isdecimal():continue
        try:
            rest=(path/'stat').read_text().rsplit(')',1)[1].split()
            if int(rest[2])==group:members.append({'pid':int(path.name),'state':rest[0]})
        except (FileNotFoundError,ProcessLookupError,PermissionError):pass
    return members

def run(command,directory,input_data=None,timeout=120):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    process=subprocess.Popen(command,cwd=directory,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
        start_new_session=True,env={**os.environ,'LC_ALL':'C','TZ':'UTC','SOURCE_DATE_EPOCH':'0'})
    row={'command':command,'leader':process.pid,'terminal':False,'group_absent':False};COMMANDS.append(row)
    original=None;stdout=stderr=b''
    try:
        stdout,stderr=process.communicate(input_data,timeout=timeout)
        if group_members(process.pid):raise RuntimeError('tool leader exited with descendant group remaining')
    except BaseException as error:
        original=error
        for action in (signal.SIGTERM,signal.SIGKILL):
            try:os.killpg(process.pid,action)
            except ProcessLookupError:pass
            try:stdout,stderr=process.communicate(timeout=3)
            except subprocess.TimeoutExpired:continue
            until=time.monotonic()+3
            while group_members(process.pid) and time.monotonic()<until:time.sleep(.02)
            if not group_members(process.pid):break
    finally:
        row.update(returncode=process.poll(),terminal=process.poll() is not None,group_absent=not group_members(process.pid),
            stdout_sha256=sha(stdout),stderr_sha256=sha(stderr))
    if original is not None:raise original
    if not row['terminal'] or not row['group_absent']:raise RuntimeError('tool ownership did not settle')
    return subprocess.CompletedProcess(command,process.returncode,stdout,stderr)

def closure(destination):
    destination=Path(destination);destination.mkdir(parents=True)
    manifest=json.loads(read(HERE/'inputs.json'));rows={}
    for name,pin in manifest['control_files'].items():
        data=read(HERE/'control'/name)
        if len(data)!=pin['bytes'] or sha(data)!=pin['sha256']:raise ValueError('frozen C control changed: '+name)
        target=destination/'control'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        rows['control/'+name]={'bytes':len(data),'sha256':sha(data)}
    for name,pin in manifest['producer_files'].items():
        data=read(HERE/name)
        if len(data)!=pin['bytes'] or sha(data)!=pin['sha256']:raise ValueError('literal producer input changed: '+name)
        (destination/name).write_bytes(data);rows[name]={'bytes':len(data),'sha256':sha(data)}
    for name in ('inputs.json','build.py'):
        data=read(HERE/name);(destination/name).write_bytes(data);rows[name]={'bytes':len(data),'sha256':sha(data)}
    return manifest,rows

def generate(root,directory):
    # The pinned helper launches cc itself. Enclose the whole specialization
    # child in our owned group so its cc1 descendants remain owned if it exits.
    root=Path(root);directory=Path(directory)
    result=run([sys.executable,'-I','-B',str(root/'preprocess.py'),'--root',str(root),'--out',str(directory)],directory.parent,timeout=150)
    (directory.parent/'preprocess.stdout').write_bytes(result.stdout)
    (directory.parent/'preprocess.stderr').write_bytes(result.stderr)
    if result.returncode:raise ValueError('owned candidate specialization failed')
    metadata=json.loads((directory/'generation.json').read_text())
    data=(directory/'pre-alpha.c').read_bytes()
    if sha(data)!=metadata['source_sha256']:raise ValueError('specialization envelope output changed')
    return data,metadata['observations'],metadata['counters']

def header_gate(source,candidate,recipe,mapping,lexer,directory,readable):
    fixed=['cc','-std=c11','-Os','-pthread','-DWORKERS=2','-DTT_BITS=18','-mavx2','-DDEV=0','-x','c','-','-o','x']
    if recipe['compiler']!=fixed:raise ValueError('fixed C compiler changed')
    base=fixed[:-2];directory=Path(directory);outputs={};rows={}
    configured=recipe['preprocessor']+['-DDEV=0','-x','c','-','-E','-dM']
    probe=run(configured,directory,readable)
    (directory/'configured-macros.txt').write_bytes(probe.stdout)
    if probe.returncode:raise ValueError('configured C macro probe failed')
    def resources(data):
        values={}
        for line in data.decode().splitlines():
            if line.startswith('#define '):
                parts=line.split(None,2)
                if parts[1] in ('WORKERS','TT_BITS','PLY'):values[parts[1]]=parts[2] if len(parts)>2 else ''
        return values
    expected={'WORKERS':'2','TT_BITS':'18','PLY':'128'}
    if resources(probe.stdout)!=expected:raise ValueError('configured resources changed')
    for name,data in (('before',source),('after',candidate)):
        for kind,flags in (('expanded',['-E','-P']),('macros',['-E','-dM'])):
            command=base+flags;result=run(command,directory,data)
            (directory/(name+'-'+kind+'.txt')).write_bytes(result.stdout)
            (directory/(name+'-'+kind+'.stderr')).write_bytes(result.stderr)
            if result.returncode:raise ValueError('full compiler preprocessing failed')
            outputs[name,kind]=result.stdout
            rows[name+'_'+kind]={'command':command,'bytes':len(result.stdout),'sha256':sha(result.stdout)}
    macro_names={line.split(None,2)[1].split('(',1)[0] for line in outputs['before','macros'].decode().splitlines() if line.startswith('#define ')}
    expanded_names={t for _,_,t in lexer._identifier_spans(outputs['before','expanded'].decode())}
    captures=set(mapping.values())&(macro_names|expanded_names)
    if captures:raise ValueError('fixed aliases collide with actual C headers/macros')
    # GCC -dM iteration order can change when identifier spelling changes its
    # internal symbol-table order. Preserve every definition's raw bytes and
    # multiplicity, but do not mistake dump order for a macro definition.
    macro_raw_equal=outputs['before','macros']==outputs['after','macros']
    same_definitions=Counter(outputs['before','macros'].splitlines(keepends=True))==Counter(outputs['after','macros'].splitlines(keepends=True))
    if not same_definitions or resources(outputs['before','macros'])!=expected:
        raise ValueError('full final macro definition/resource inventory changed')
    inverse={'expanded.c':outputs['after','expanded']}
    for old,new in mapping.items():inverse=lexer._replace(inverse,new,old)
    restored=inverse['expanded.c'];(directory/'inverse-expanded.txt').write_bytes(restored)
    if restored!=outputs['before','expanded']:raise ValueError('raw full-PP alias-only inverse differs')
    return {'pass':True,'alias_only_inverse':True,'numeric_inverse_replacements':0,'whitespace_normalization':False,
        'full_macro_definition_raw_lines_equal':True,'macro_definition_multiplicity_preserved':True,
        'raw_dump_equal':macro_raw_equal,'same_raw_definition_multiset':same_definitions,'order_only':not macro_raw_equal,
        'macro_dump_raw_order_equal':macro_raw_equal,'macro_dump_order_only_difference':not macro_raw_equal,
        'macro_comparison':'entire raw line multiset; no definition-content or whitespace normalization',
        'final_resource_values':expected,'separate_configured_resources':resources(probe.stdout),
        'actual_final_command_extra_flags_added':False,'only_removed_output_pair':['-o','x'],'observations':rows,
        'expanded_inverse_sha256':sha(restored),'configured_macro_sha256':sha(probe.stdout)}

def package(source,selected,recipe,literal,directory):
    if recipe['compression']!={'format':'xz','filter':'LZMA2','preset':9,'extreme':True,'lc':3,'lp':0,'pb':2,'check':'CRC64'}:
        raise ValueError('fixed C codec changed')
    template=read(selected/'bootstrap.py.in');prefix=read(selected/'launcher.sh');marker=b'__ROVE_SOURCE_LITERAL__'
    if template.count(marker)!=1 or len(prefix)!=75:raise ValueError('fixed C bootstrap/prefix changed')
    expression,kind=literal(source);script=template.replace(marker,expression.encode());ast.parse(script)
    payload=lzma.compress(script,format=lzma.FORMAT_XZ,check=lzma.CHECK_CRC64,
        filters=[{'id':lzma.FILTER_LZMA2,'preset':9|lzma.PRESET_EXTREME,'lc':3,'lp':0,'pb':2}])
    decoder=lzma.LZMADecompressor(format=lzma.FORMAT_XZ)
    if decoder.decompress(payload)!=script or not decoder.eof or decoder.unused_data:raise ValueError('strict XZ restoration differs')
    cli=run(['xz','-dc'],directory,payload,timeout=15)
    if cli.returncode or cli.stderr or cli.stdout!=script:raise ValueError('independent CLI XZ restoration differs')
    return prefix+payload,script,kind
