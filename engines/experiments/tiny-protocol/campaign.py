#!/usr/bin/env python3
"""Frozen Tiny A source and Tiny D ELF protocol architecture comparison.

Only new external snapshots are written. No identifier sweep or compiler-setting
sweep is run: the selected A -Os command and D -Oz/-flto command are preserved.
All source transformations are separate from baseline native identity claims.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
import lzma
import os
from pathlib import Path
import re
import shutil
import subprocess

HERE=Path(__file__).resolve().parent


def sha(data):return hashlib.sha256(data).hexdigest()


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


def bootstrap_argument(script):
    matches=[n for n in ast.walk(ast.parse(script)) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
             and isinstance(n.func.value,ast.Name) and n.func.value.id=='p' and n.func.attr=='communicate']
    if len(matches)!=1 or len(matches[0].args)!=1:raise ValueError('expected one source-restoration call')
    node=matches[0].args[0];starts=[0]+[m.end() for m in re.finditer(rb'\r\n|\r|\n',script)]
    return starts[node.lineno-1]+node.col_offset,starts[node.end_lineno-1]+node.end_col_offset


def execute(command,*,cwd,input=None):
    p=subprocess.run(command,cwd=cwd,input=input,capture_output=True,timeout=90)
    if p.returncode:raise RuntimeError(json.dumps({'command':command,'cwd':str(cwd),'code':p.returncode,'stderr':p.stderr.decode(errors='replace')}))
    return p


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--a-readable',type=Path,required=True)
    parser.add_argument('--a-reference',type=Path,required=True)
    parser.add_argument('--a-search-rename',type=Path,required=True)
    parser.add_argument('--a-encoding',type=Path,required=True)
    parser.add_argument('--a-wrapper',type=Path,required=True)
    parser.add_argument('--d-build',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--no-own-elf',action='store_true')
    args=parser.parse_args()
    if not args.out.is_absolute() or args.out.exists():parser.error('new absolute external output required')
    args.out.mkdir(parents=True)
    frozen=args.out/'recipe';frozen.mkdir()
    for name in ('transform.py','span.c.in','position.c.in','go-loop.c.in'):
        (frozen/name).write_bytes((HERE/name).read_bytes())
    for name in ('specialize.py','minify.py','stitch.py'):
        (frozen/name).write_bytes((args.a_reference.parent/'frozen'/name).read_bytes())
    for name in ('rename_c.py','pack_stream.py'):
        (frozen/name).write_bytes((args.a_search_rename.parent/'frozen'/name).read_bytes())
    for name,path in (('a-readable.c',args.a_readable),('a-search-rename.json',args.a_search_rename),
                      ('a-encoding.json',args.a_encoding),('a-wrapper',args.a_wrapper),('d-build.json',args.d_build)):
        (frozen/name).write_bytes(path.read_bytes())
    transform=module('protocol_transform',frozen/'transform.py').transform
    specialize=module('protocol_specialize',frozen/'specialize.py').specialize_c
    compact=module('protocol_compact',frozen/'minify.py').compact_source
    strip=module('protocol_counter_strip',frozen/'stitch.py').strip_dev_counters
    lexer=module('protocol_lexer',frozen/'rename_c.py')
    source_literal=module('protocol_literal',frozen/'pack_stream.py').source_literal
    spelling=json.loads(args.a_search_rename.read_text())
    fixed=[x for x in spelling['rename']['trials'] if x['status']=='accepted' and x['trial']<=spelling['selected']['trial']]
    enc=json.loads(args.a_encoding.read_text());selected=next(x for x in enc['records'] if x['case']=='combined-fixed-stripped')
    resources={'WORKERS':'2','TT_BITS':'18'}
    readable=args.a_readable.read_bytes()
    if sha(readable)!='109fa749bc2a137fc1384a9afa429d3734249df908f057a58c1fe105f0c43504':
        raise ValueError('unknown readable A reference')
    wrapper=args.a_wrapper.read_bytes();offset=wrapper.index(b'\xfd7zXZ\0');prefix=wrapper[:offset]
    bootstrap=lzma.decompress(wrapper[offset:]);begin,end=bootstrap_argument(bootstrap)
    filters=[{'id':lzma.FILTER_LZMA2,'preset':9|lzma.PRESET_EXTREME,'lc':2,'lp':0,'pb':0}]
    def package(source):
        expression,_=source_literal(source)
        script=bootstrap[:begin]+expression.encode()+bootstrap[end:]
        data=prefix+lzma.compress(script,format=lzma.FORMAT_XZ,check=lzma.CHECK_CRC64,filters=filters)
        return data,script
    report={'scope':'independent span/direct-move protocol implementation; no external engine source copied',
            'compiler_settings':['A selected cc -Os -x c - -o x -s','D selected -Oz -flto freestanding static ELF'],
            'compiler':subprocess.check_output(['cc','--version'],text=True).splitlines()[0],
            'input_sha256':{p.name:sha(p.read_bytes()) for p in frozen.iterdir() if p.is_file()},'A':[],'D':[]}
    command=selected['command']
    for form,combined in (('baseline',readable),('protocol',transform(readable,family='A')[0])):
        directory=args.out/('A-'+form);directory.mkdir();(directory/'combined.c').write_bytes(combined)
        active,_=specialize({'main.c':combined},directory/'preprocess',['cc','-std=c11','-Os','-pthread','-DWORKERS=2','-DTT_BITS=18','-DDEV=0'],os.environ.copy())
        source=compact(active['main.c'],'c');source,_=strip(source)
        files={'main.c':source}
        for x in fixed:files=lexer._replace(files,x['identifier'],x['replacement'])
        for name,literal in resources.items():files=lexer._replace(files,name,literal)
        for name,alias in selected['manual_function_spellings'].items():files=lexer._replace(files,name,alias)
        source=files['main.c'];(directory/'main.c').write_bytes(source)
        execute(command,cwd=directory,input=source);native=(directory/'x').read_bytes()
        execute(command,cwd=directory,input=source)
        if (directory/'x').read_bytes()!=native:raise ValueError('A native reproduction failed')
        packed,script=package(source);repeated,_=package(source)
        if packed!=repeated:raise ValueError('A whole source reproduction failed')
        if form=='baseline' and (sha(source)!=selected['source_sha256'] or packed!=wrapper or sha(native)!=selected['native_gate']['native_sha256']):
            raise ValueError('selected A control did not reproduce exact source/native/whole bytes')
        (directory/'wrapper').write_bytes(packed);(directory/'wrapper').chmod(0o755)
        (directory/'bootstrap.py').write_bytes(script)
        dev=directory/'dev';dev.mkdir();(dev/'main.c').write_bytes(combined)
        execute(['cc','-std=c11','-Os','-pthread','-DWORKERS=2','-DTT_BITS=18','-DDEV=1','main.c','-o','x'],cwd=dev)
        record={'form':form,'source_bytes':len(source),'source_sha256':sha(source),'readable_sha256':sha(combined),
                'native_bytes':len(native),'native_sha256':sha(native),'whole_bytes':len(packed),'whole_sha256':sha(packed),
                'native_reproduced':True,'whole_reproduced':True,'command':command,'wrapper':str(directory/'wrapper'),
                'dev':str(dev/'x'),'script_sha256':sha(script)}
        report['A'].append(record);print(json.dumps({'A':record}),flush=True)
        (args.out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    # Freeze exactly the already qualified D source/own-loader recipe. The
    # canonical TinyD folder and shared packer are not read during candidate build.
    dmanifest=json.loads(args.d_build.read_text());droot=args.d_build.parent
    drecipe=frozen/'D';drecipe.mkdir()
    for name,expected in dmanifest['source_sha256'].items():
        data=(droot/'sources'/name).read_bytes()
        if sha(data)!=expected:raise ValueError('D frozen source mismatch: '+name)
        (drecipe/name).write_bytes(data)
    loader_recipe=args.out/'loader-recipe';shutil.copytree(droot/'recipe',loader_recipe)
    builder=module('protocol_D_builder',drecipe/'build.py')
    loader=module('protocol_D_loader',loader_recipe/'engines/scripts/elf_loader.py')
    for form in ('baseline','protocol'):
        directory=args.out/('D-'+form);directory.mkdir();sources=directory/'sources';sources.mkdir()
        for path in drecipe.iterdir():
            if path.is_file():shutil.copyfile(path,sources/path.name)
        if form=='protocol':
            runtime,policy=transform((sources/'runtime.c').read_bytes(),family='D');(sources/'runtime.c').write_bytes(runtime)
        else:policy='unchanged frozen reference'
        for engine in dmanifest['engines']:
            dest=directory/engine['id'];dest.mkdir()
            invocation=[x.replace(str(droot/'sources'),str(sources)) for x in engine['compile'][:-1]]+[str(dest/'linked')]
            execute(invocation,cwd=dest);native=builder.strip_sections((dest/'linked').read_bytes())
            execute(invocation,cwd=dest)
            if builder.strip_sections((dest/'linked').read_bytes())!=native:raise ValueError('D native reproduction failed')
            if form=='baseline' and sha(native)!=engine['native_sha256']:raise ValueError('D exact frozen control did not reproduce')
            target=dest/'x';target.write_bytes(native);target.chmod(0o755)
            packed=None
            if engine['profile']=='shipping' and not args.no_own_elf:
                packed=loader.pack_elf(target,dest/'self.elf',cc='cc',filter='auto')
                repeated=loader.pack_elf(target,dest/'self-second.elf',cc='cc',filter='auto')
                if Path(packed['output']).read_bytes()!=Path(repeated['output']).read_bytes():raise ValueError('D own ELF reproduction failed')
            record={'form':form,'id':engine['id'],'profile':engine['profile'],'source_sha256':{p.name:sha(p.read_bytes()) for p in sources.iterdir() if p.is_file()},
                    'compile':invocation,'native_bytes':len(native),'native_sha256':sha(native),'native_reproduced':True,
                    'command':[str(target)],'packing':packed,'policy':policy}
            report['D'].append(record);print(json.dumps({'D':{k:record[k] for k in ('form','id','native_bytes','native_sha256')}}),flush=True)
            (args.out/'results.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
