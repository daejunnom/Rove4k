#!/usr/bin/env python3
"""Measure ONE frozen startup-counter candidate and exact A5140 control twice.

Historical control files and helpers live beside this producer. No maintained
entry, mutable shared helper, prior artifact, flag/identifier/codec search, or
engine execution is an input. All produced artifacts remain outside Git.
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
import subprocess
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent


def sha(data):return hashlib.sha256(data).hexdigest()


def normalized(data):
    data=data.replace(b'\r\n',b'\n')
    if b'\r' in data:raise ValueError('lone CR in source input')
    return data


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args();out=args.out.resolve()
    if not args.out.is_absolute() or out.exists() or any((p/'.git').exists() for p in (out,*out.parents)):
        parser.error('a new absolute output outside Git is required')
    if platform.system()!='Linux' or platform.machine() not in ('x86_64','amd64'):
        parser.error('qualified target is Linux x86-64')
    out.mkdir(parents=True);inputs=out/'inputs';inputs.mkdir()
    report={'complete':False,'scope':'one fixed startup-counter first cost; no engine execution or 4KiB acceptance',
            'inputs':{},'forms':{},'attempts':[],'private_difference':'after main startup wait, stopped is 1 rather than initial 0; GO already clears it',
            'tools':{name:subprocess.check_output(command,text=True).splitlines()[0] for name,command in
                     {'cc':['cc','--version'],'ld':['ld','--version'],'python':['python3','--version'],
                      'xz':['xz','--version'],'lzma':['lzma','--version']}.items()}}
    def save():(out/'build.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        manifest=json.loads((HERE/'control-inputs.json').read_text())
        paths=sorted(manifest['files'])+['.gitattributes','control-inputs.json','build.py','transform.py']
        for relative in paths:
            raw=(HERE/relative).read_bytes();data=normalized(raw)
            if relative in manifest['files']:
                expected=manifest['files'][relative]
                if sha(data)!=expected['LF_sha256']:raise ValueError('frozen closure changed: '+relative)
            target=inputs/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            report['inputs'][relative]={'raw_sha256':sha(raw),'LF_sha256':sha(data),'bytes':len(data),'LF_normalization':raw!=data}
        recipe=json.loads((inputs/'control/recipe.json').read_text())
        if recipe['profile']!={'workers':2,'tt_bits':18,'ply':128,'dev_default':False}:raise ValueError('fixed profile changed')
        if recipe['compiler']!=['cc','-Os','-x','c','-','-o','x','-s']:raise ValueError('fixed native argv changed')
        if recipe['compression']!={'format':'lzma-alone','filter':'LZMA1','preset':9,'extreme':True,'lc':2,'lp':0,'pb':0,
                                  'check':'NONE','dictionary_bytes':67108864,'header_hex':'0200000004ffffffffffffffff'}:
            raise ValueError('fixed transport changed')
        for relative,pin in recipe['helper_sha256'].items():
            if sha((inputs/'helpers'/Path(relative).name).read_bytes())!=pin:raise ValueError('helper pin changed')
        specialize=module('startup_specialize',inputs/'helpers/specialize.py').specialize_c
        compact=module('startup_compact',inputs/'helpers/minify.py').compact_source
        strip=module('startup_counter_strip',inputs/'helpers/stitch.py').strip_dev_counters
        replace=module('startup_tokens',inputs/'helpers/rename_c.py')._replace
        literal=module('startup_literal',inputs/'helpers/pack_stream.py').source_literal
        rewrite=module('startup_transform',inputs/'transform.py').transform
        control=(inputs/'control/engine.c').read_bytes();candidate=rewrite(control)
        template=(inputs/'control/bootstrap.py.in').read_bytes();prefix=(inputs/'control/launcher.sh').read_bytes()
        for name,pin in recipe['local_input_sha256'].items():
            if sha((inputs/'control'/name).read_bytes())!=pin:raise ValueError('control pin changed: '+name)
        marker=b'__ROVE_SOURCE_LITERAL__'
        if template.count(marker)!=1 or len(prefix)!=77:raise ValueError('bootstrap input changed')
        report['fixed_recipe']={'compiler':recipe['compiler'],'preprocessor':recipe['preprocessor'],
                                'profile':recipe['profile'],'compression':recipe['compression']}
        report['historical_qualified_receipt_reuse']=recipe['qualified_receipt']
        def generate(readable,directory):
            active,observations=specialize({'main.c':readable},directory,recipe['preprocessor']+['-DDEV=0'],os.environ.copy())
            data,_=strip(compact(active['main.c'],'c'));files={'main.c':data}
            for old,new in recipe['fixed_renames']+recipe['resource_literals']+recipe['function_spellings']:
                files=replace(files,old,new)
            return files['main.c'],observations
        def compile_c(source,directory):
            directory.mkdir()
            result=subprocess.run(recipe['compiler'],input=source,cwd=directory,capture_output=True,timeout=90)
            (directory/'compiler.stderr').write_bytes(result.stderr)
            if result.returncode:raise RuntimeError('compiler failed: '+str(directory))
            return (directory/'x').read_bytes()
        def package(source):
            expression,kind=literal(source);script=template.replace(marker,expression.encode());ast.parse(script)
            stream=lzma.compress(script,format=lzma.FORMAT_ALONE,check=lzma.CHECK_NONE,
                filters=[{'id':lzma.FILTER_LZMA1,'preset':9|lzma.PRESET_EXTREME,'lc':2,'lp':0,'pb':0}])
            if stream[:13]!=bytes.fromhex('0200000004ffffffffffffffff'):raise ValueError('ALONE header changed')
            decoder=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
            if decoder.decompress(stream)!=script or not decoder.eof or decoder.unused_data:raise ValueError('strict decode mismatch')
            cli=subprocess.run(['lzma','-dc'],input=stream,capture_output=True,timeout=15)
            if cli.returncode or cli.stderr or cli.stdout!=script:raise ValueError('CLI decode mismatch')
            return prefix+stream,script,kind
        expected=recipe['expected']
        for name,readable in (('control',control),('candidate',candidate)):
            root=out/name;root.mkdir();(root/'engine.c').write_bytes(readable);first=None
            for index in (1,2):
                directory=root/('attempt-'+str(index));directory.mkdir()
                source,observations=generate(readable,directory/'preprocess')
                native=compile_c(source,directory/'native');whole,script,kind=package(source)
                current=(source,native,whole,script)
                actual={'readable_bytes':len(readable),'readable_sha256':sha(readable),
                        'source_bytes':len(source),'source_sha256':sha(source),'native_bytes':len(native),'native_sha256':sha(native),
                        'whole_bytes':len(whole),'whole_sha256':sha(whole),'bootstrap_sha256':sha(script)}
                if name=='control':
                    for key,value in actual.items():
                        if key in expected and value!=expected[key]:raise ValueError('exact A5140 control differs: '+key)
                (directory/'main.c').write_bytes(source);(directory/'x').write_bytes(whole);(directory/'x').chmod(0o755)
                (directory/'bootstrap.py').write_bytes(script)
                if first is None:first=current
                elif current!=first:raise ValueError('independent same-recipe outputs differ')
                report['attempts'].append({'form':name,'attempt':index,**actual,'preprocessor':observations,'literal':kind});save()
            (root/'main.c').write_bytes(first[0]);(root/'native').mkdir();(root/'native/x').write_bytes(first[1]);(root/'native/x').chmod(0o755)
            (root/'x').write_bytes(first[2]);(root/'x').chmod(0o755);(root/'bootstrap.py').write_bytes(first[3])
            report['forms'][name]={**actual,'independent_identical_attempts':2,'exact_expected_control':name=='control'};save()
        before=report['forms']['control'];after=report['forms']['candidate']
        report.update(complete=True,deltas={key:after[key]-before[key] for key in ('readable_bytes','source_bytes','native_bytes','whole_bytes')},
                      qualifies_for_narrow_runtime=after['whole_bytes']<before['whole_bytes'],under_4096_bytes=after['whole_bytes']<=4096,
                      engine_executions=0)
        save();print(json.dumps({'complete':True,'out':str(out),'forms':report['forms'],'deltas':report['deltas'],
                                 'qualifies_for_narrow_runtime':report['qualifies_for_narrow_runtime']}),flush=True)
    except Exception as error:
        report['error']=repr(error);save();raise


if __name__=='__main__':main()
