#!/usr/bin/env python3
"""Build the maintained minimal F entry from Git source and fixed decisions.

There are no experiment-directory, old build.json or executable inputs. The
single shipping profile is fixed; --dev adds the separately pinned semantic diagnostic form.
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
import re
import subprocess
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]


def sha(data):return hashlib.sha256(data).hexdigest()


def normalized(path):
    data=path.read_bytes().replace(b'\r\n',b'\n')
    if b'\r' in data:raise ValueError('lone CR in owned text input: '+str(path))
    return data


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


COUNTER_SCHEMA={'noop_definitions':1,'conditional_calls':{'hits':1,'qs':1,'corr_uses':1},
                'unconditional_calls':['ply_aborts','hist_updates','cont_updates','corr_updates','f_probes',
                                       'f_lower','f_upper','f_converged','f_conflicts'],
                'shipping_pvs_calls':0,'total_calls_removed':12}


def strip_counters(source):
    """Admit exactly the qualified beta-only DEV=0 no-op counter schema."""
    text=source.decode()
    text,definitions=re.subn(r'(?m)^#define COUNT\(w,f\) \(\(void\)0\)\n','',text)
    for statement in ('if(bound)COUNT(w,hits);','if(depth<=0)COUNT(w,qs);','if(correction)COUNT(w,corr_uses);'):
        if text.count(statement)!=1:raise ValueError('beta-only conditional counter schema changed: '+statement)
        text=text.replace(statement,'')
    allowed=set(COUNTER_SCHEMA['unconditional_calls']);found=re.findall(r'COUNT\(w,(\w+)\);',text)
    if set(found)!=allowed or len(found)!=len(allowed) or definitions!=1:
        raise ValueError('beta-only shipping diagnostic schema changed')
    text=re.sub(r'COUNT\(w,\w+\);','',text)
    if 'COUNT(' in text:raise ValueError('unexpected diagnostic call remains')
    return text.encode(),{'removed_noop_counter_calls':len(found)+3,'shipping_pvs_calls':0}


def compile_c(command,source,directory):
    directory.mkdir()
    result=subprocess.run(command,input=source,cwd=directory,capture_output=True,timeout=90)
    (directory/'compiler.stderr').write_bytes(result.stderr)
    if result.returncode:raise RuntimeError('compiler failed; stderr preserved in '+str(directory))
    return (directory/'x').read_bytes()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--dev',action='store_true',help='also reproduce the separately pinned semantic diagnostic C and ELF')
    args=parser.parse_args();out=args.out.resolve()
    if not args.out.is_absolute() or out.exists() or out==REPO or REPO in out.parents or any((p/'.git').exists() for p in (out,*out.parents)):
        parser.error('a new absolute output outside any Git checkout is required')
    if platform.system()!='Linux' or platform.machine() not in ('x86_64','amd64'):
        parser.error('the qualified fixed target is Linux x86-64')
    recipe=json.loads((HERE/'recipe.json').read_text())
    if recipe['format']!=1 or recipe['family']!='F' or recipe['profile']!={'workers':2,'tt_bits':18,'ply':128,'dev_default':False}:
        raise ValueError('unsupported entry recipe/profile')
    if recipe['counter_schema']!=COUNTER_SCHEMA:raise ValueError('unsupported beta-only counter schema')
    out.mkdir(parents=True);frozen=out/'inputs';frozen.mkdir()
    report={'complete':False,'family':'F','scope':'maintained F EP and shipping input pipeline; fixed reviewed identities, not 4KiB acceptance',
            'resources':recipe['profile'],'inputs':{},'attempts':[],
            'qualified_receipt_reuse':recipe['qualified_receipt'],
            'tools':{name:subprocess.check_output(command,text=True).splitlines()[0] for name,command in
                     {'cc':['cc','--version'],'ld':['ld','--version'],'python':['python3','--version'],'lzma':['lzma','--version']}.items()}}
    def save():(out/'build.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        for name,expected in recipe['local_input_sha256'].items():
            data=normalized(HERE/name)
            if sha(data)!=expected:raise ValueError('entry input differs from qualified recipe: '+name)
            (frozen/name).write_bytes(data);report['inputs'][name]={'bytes':len(data),'sha256':sha(data)}
        for name in ('recipe.json','build.py'):
            data=normalized(HERE/name);(frozen/name).write_bytes(data)
            report['inputs'][name]={'bytes':len(data),'sha256':sha(data)}
        for relative,expected in recipe['helper_sha256'].items():
            path=REPO/relative;raw=path.read_bytes();data=normalized(path)
            if sha(data)!=expected:raise ValueError('tracked helper version changed: '+relative)
            (frozen/path.name).write_bytes(data)
            report['inputs'][relative]={'bytes':len(data),'sha256':sha(data),'working_bytes_sha256':sha(raw),'LF_normalization':raw!=data}
        specialize=module('entry_specialize',frozen/'specialize.py').specialize_c
        compact=module('entry_minify',frozen/'minify.py').compact_source
        lexer=module('entry_fixed_tokens',frozen/'rename_c.py')
        literal=module('entry_literal',frozen/'pack_stream.py').source_literal
        alpha=module('entry_fixed_F_alpha',frozen/'shipping_alpha.py').transform_source
        storage=module('entry_fixed_F_storage',frozen/'shipping_storage.py').transform_source
        scope_module=module('entry_bound_F_scope',frozen/'shipping_scope.py')
        scope=scope_module.transform_source;members=scope_module.transform_members
        semantics=module('entry_fixed_F_semantics',frozen/'shipping_semantics.py')
        input_profile=module('entry_fixed_F_input',frozen/'shipping_input.py')
        declarations=module('entry_fixed_F_declarations',frozen/'shipping_declarations.py').transform_source
        hce=module('entry_fixed_F_HCE',frozen/'shipping_hce.py').transform_source
        # Keep this base for every unchanged shipping readable/spelling guard.
        canonical=(frozen/'engine.c').read_bytes();template=(frozen/'bootstrap.py.in').read_bytes();prefix=(frozen/'launcher.sh').read_bytes()
        marker=b'__ROVE_SOURCE_LITERAL__'
        if template.count(marker)!=1 or len(prefix)!=77:raise ValueError('bootstrap recipe changed')
        compression={'format':'lzma-alone','filter':'LZMA1','preset':9,'extreme':True,
                     'lc':2,'lp':0,'pb':0,'check':'NONE','mf':'BT4',
                     'dictionary_bytes':67108864,'nice_len':32}
        if recipe['compression']!=compression:raise ValueError('fixed LZMA1 recipe changed')
        expected=recipe['expected']
        def generate(directory,dev=False):
            preprocess_source=canonical;semantic_metadata=None;input_metadata=None
            if dev:
                preprocess_source,semantic_metadata=semantics.transform_readable(canonical)
                preprocess_source,input_metadata=input_profile.transform_readable(preprocess_source)
            active,observations=specialize({'main.c':preprocess_source},directory,recipe['preprocessor']+['-DDEV='+str(int(dev))],os.environ.copy())
            data=compact(active['main.c'],'c')
            counters=None;alpha_metadata=None;storage_metadata=None;scope_metadata=None;member_metadata=None;declaration_metadata=None;hce_metadata=None
            if not dev:
                data,counters=strip_counters(data);files={'main.c':data}
                for old,new in recipe['resource_literals']:
                    count=sum(token==old for _,_,token in lexer._identifier_spans(files['main.c'].decode()))
                    if count!=recipe['resource_token_counts'][old]:raise ValueError('fixed resource token count changed: '+old)
                    files=lexer._replace(files,old,new)
                for old,new in recipe['function_spellings']:
                    files=lexer._replace(files,old,new)
                data=files['main.c']
                data,alpha_metadata=alpha(data,family='F',lexer=lexer,readable=canonical)
                data,storage_metadata=storage(data,family='F',readable=canonical)
                data,scope_metadata=scope(data)
                data,member_metadata=members(data)
                data,semantic_metadata=semantics.transform_source(data,readable=canonical)
                semantic_readable,_=semantics.transform_readable(canonical)
                data,input_metadata=input_profile.transform_source(data,readable=semantic_readable)
                data,declaration_metadata=declarations(data,readable=canonical)
                data,hce_metadata=hce(data)
            return data,observations,counters,alpha_metadata,storage_metadata,scope_metadata,member_metadata,semantic_metadata,input_metadata,declaration_metadata,hce_metadata
        def package(source):
            expression,_=literal(source);script=template.replace(marker,expression.encode())
            ast.parse(script)
            data=prefix+lzma.compress(script,format=lzma.FORMAT_ALONE,check=lzma.CHECK_NONE,
                                     filters=[{'id':lzma.FILTER_LZMA1,'preset':9|lzma.PRESET_EXTREME,
                                               'lc':2,'lp':0,'pb':0,'mf':lzma.MF_BT4,
                                               'dict_size':67108864,'nice_len':32}])
            return data,script
        first=None;first_dev=None
        for index in (1,2):
            directory=out/('attempt-'+str(index));directory.mkdir()
            source,observations,counters,alpha_metadata,storage_metadata,scope_metadata,member_metadata,semantic_metadata,input_metadata,declaration_metadata,hce_metadata=generate(directory/'preprocess')
            if len(source)!=expected['source_bytes'] or sha(source)!=expected['source_sha256']:raise ValueError('compact C identity mismatch')
            (directory/'main.c').write_bytes(source)
            native=compile_c(recipe['compiler'],source,directory/'native')
            if len(native)!=expected['native_bytes'] or sha(native)!=expected['native_sha256']:raise ValueError('native ELF identity mismatch')
            whole,script=package(source)
            if len(whole)!=expected['whole_bytes'] or sha(whole)!=expected['whole_sha256'] or sha(script)!=expected['bootstrap_sha256']:
                raise ValueError('complete launcher identity mismatch')
            (directory/'x').write_bytes(whole);(directory/'x').chmod(0o755);(directory/'bootstrap.py').write_bytes(script)
            current=(source,native,whole,script)
            if first is None:first=current
            elif current!=first:raise ValueError('independent generation did not reproduce bytes')
            row={'attempt':index,'source_bytes':len(source),'source_sha256':sha(source),'native_bytes':len(native),'native_sha256':sha(native),
                 'whole_bytes':len(whole),'whole_sha256':sha(whole),'bootstrap_sha256':sha(script),'preprocessor':observations,
                 'counter_removal':counters,'shipping_alpha':alpha_metadata,'shipping_storage':storage_metadata,
                 'shipping_scope':scope_metadata,'shipping_members':member_metadata,'shipping_semantics':semantic_metadata,'shipping_input':input_metadata,'shipping_declarations':declaration_metadata,'shipping_hce':hce_metadata}
            if args.dev:
                dev,dev_observations,_,dev_alpha,dev_storage,dev_scope,dev_members,dev_semantics,dev_input,dev_declarations,dev_hce=generate(directory/'preprocess-dev',True)
                if dev_alpha is not None or dev_storage is not None or dev_scope is not None or dev_members is not None or dev_declarations is not None or dev_hce is not None:raise ValueError('diagnostic source entered shipping spelling stage')
                if dev_semantics is None or dev_semantics['stage']!='readable-before-DEV-specialization':raise ValueError('diagnostic semantic stage missing')
                if dev_input is None or dev_input['stage']!='readable-before-DEV-specialization' or dev_input['shipping_relation_checked']:
                    raise ValueError('diagnostic input-profile stage differs')
                if sha(dev)!=expected['dev_source_sha256']:raise ValueError('diagnostic C differs from current semantic recipe')
                dev_command=recipe['dev_compiler']
                dev_native=compile_c(dev_command,dev,directory/'dev');(directory/'dev/main.c').write_bytes(dev)
                if sha(dev_native)!=expected['dev_native_sha256']:raise ValueError('diagnostic ELF differs from current semantic recipe')
                if first_dev is None:first_dev=(dev,dev_native)
                elif first_dev!=(dev,dev_native):raise ValueError('diagnostic bytes did not reproduce')
                row['dev']={'source_sha256':sha(dev),'native_sha256':sha(dev_native),'command':dev_command,'preprocessor':dev_observations,
                            'expected_identity_match':True,'old_DEV_identity_claimed':False,'semantic':dev_semantics,
                            'input_profile':dev_input,'prior_EP_DEV_identity_verified':True}
            report['attempts'].append(row);save()
        (out/'main.c').write_bytes(first[0]);(out/'native').mkdir();(out/'native/x').write_bytes(first[1]);(out/'native/x').chmod(0o755)
        (out/'x').write_bytes(first[2]);(out/'x').chmod(0o755);(out/'bootstrap.py').write_bytes(first[3])
        if first_dev:
            (out/'dev').mkdir();(out/'dev/main.c').write_bytes(first_dev[0]);(out/'dev/x').write_bytes(first_dev[1]);(out/'dev/x').chmod(0o755)
        report.update(complete=True,source_reproduced=True,native_reproduced=True,whole_reproduced=True,
                      actual={'command':[str(out/'x')],'native':str(out/'native/x'),'source':str(out/'main.c'),
                              'whole_sha256':sha(first[2]),'native_sha256':sha(first[1]),'source_sha256':sha(first[0])},
                      diagnostic_exact_control=bool(first_dev),
                      diagnostic_identity_scope='current literal DEV source and ELF reproduced; prior EP diagnostic tuple compared exactly, not assumed',under_4096_bytes=False)
        save();print(json.dumps({'complete':True,'out':str(out),'whole_bytes':len(first[2]),'source_sha256':sha(first[0]),
                                'native_sha256':sha(first[1]),'whole_sha256':sha(first[2]),'diagnostic_exact_control':bool(first_dev)}),flush=True)
    except Exception as error:
        report['error']=repr(error);save();raise


if __name__=='__main__':main()
