#!/usr/bin/env python3
"""One frozen Tiny A fixed-stage fusion whole-source experiment, no sweep."""
import argparse
import ast
import hashlib
import importlib.util
import json
import lzma
import os
from pathlib import Path
import re
import subprocess

HERE=Path(__file__).resolve().parent


def sha(data):return hashlib.sha256(data).hexdigest()


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def argument(script):
    calls=[n for n in ast.walk(ast.parse(script)) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
           and isinstance(n.func.value,ast.Name) and n.func.value.id=='p' and n.func.attr=='communicate']
    if len(calls)!=1 or len(calls[0].args)!=1:raise ValueError('unknown source bootstrap')
    n=calls[0].args[0];starts=[0]+[m.end() for m in re.finditer(rb'\r\n|\r|\n',script)]
    return starts[n.lineno-1]+n.col_offset,starts[n.end_lineno-1]+n.end_col_offset


def run(command,cwd,source=None):
    p=subprocess.run(command,input=source,cwd=cwd,capture_output=True,timeout=60)
    if p.returncode:raise RuntimeError(json.dumps({'command':command,'code':p.returncode,'stderr':p.stderr.decode(errors='replace')}))
    return p


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('readable','reference','search-rename','encoding','wrapper','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if not args.out.is_absolute() or args.out.exists():parser.error('new absolute external directory required')
    args.out.mkdir(parents=True)
    recipe=args.out/'recipe';recipe.mkdir()
    for name in ('campaign.py','transform.py'):(recipe/name).write_bytes((HERE/name).read_bytes())
    for path in HERE.glob('*.c.in'):(recipe/path.name).write_bytes(path.read_bytes())
    for name in ('specialize.py','minify.py','stitch.py'):
        (recipe/name).write_bytes((args.reference.parent/'frozen'/name).read_bytes())
    for name in ('rename_c.py','pack_stream.py'):
        (recipe/name).write_bytes((args.search_rename.parent/'frozen'/name).read_bytes())
    for name,path in (('readable.c',args.readable),('reference.json',args.reference),
                      ('search-rename.json',args.search_rename),('encoding.json',args.encoding),('wrapper',args.wrapper)):
        (recipe/name).write_bytes(path.read_bytes())
    transform=module('ranked_transform',recipe/'transform.py').transform
    specialize=module('ranked_specialize',recipe/'specialize.py').specialize_c
    compact=module('ranked_compact',recipe/'minify.py').compact_source
    strip=module('ranked_strip',recipe/'stitch.py').strip_dev_counters
    lexer=module('ranked_lexer',recipe/'rename_c.py')
    literal=module('ranked_literal',recipe/'pack_stream.py').source_literal
    rename=json.loads(args.search_rename.read_text())
    fixed=[x for x in rename['rename']['trials'] if x['status']=='accepted' and x['trial']<=rename['selected']['trial']]
    selected=next(x for x in json.loads(args.encoding.read_text())['records'] if x['case']=='combined-fixed-stripped')
    readable=args.readable.read_bytes();changed,policy=transform(readable)
    wrapper=args.wrapper.read_bytes();offset=wrapper.index(b'\xfd7zXZ\0');prefix=wrapper[:offset]
    bootstrap=lzma.decompress(wrapper[offset:]);begin,end=argument(bootstrap)
    filters=[{'id':lzma.FILTER_LZMA2,'preset':9|lzma.PRESET_EXTREME,'lc':2,'lp':0,'pb':0}]
    def package(source):
        expression,_=literal(source);script=bootstrap[:begin]+expression.encode()+bootstrap[end:]
        return prefix+lzma.compress(script,format=lzma.FORMAT_XZ,check=lzma.CHECK_CRC64,filters=filters),script
    report={'scope':'one fixed-stage fusion; frozen resource, spelling, compiler and stream recipe',
            'compiler':subprocess.check_output(['cc','--version'],text=True).splitlines()[0],
            'policy':policy,'input_sha256':{p.name:sha(p.read_bytes()) for p in recipe.iterdir() if p.is_file()},'forms':[]}
    for name,combined in (('baseline',readable),('fused',changed)):
        dest=args.out/name;dest.mkdir();(dest/'combined.c').write_bytes(combined)
        active,_=specialize({'main.c':combined},dest/'preprocess',['cc','-std=c11','-Os','-pthread','-DWORKERS=2','-DTT_BITS=18','-DDEV=0'],os.environ.copy())
        source=compact(active['main.c'],'c');source,_=strip(source);files={'main.c':source}
        for r in fixed:files=lexer._replace(files,r['identifier'],r['replacement'])
        for key,value in {'WORKERS':'2','TT_BITS':'18'}.items():files=lexer._replace(files,key,value)
        for key,value in selected['manual_function_spellings'].items():files=lexer._replace(files,key,value)
        source=files['main.c'];(dest/'main.c').write_bytes(source)
        run(selected['command'],dest,source);native=(dest/'x').read_bytes()
        run(selected['command'],dest,source)
        if (dest/'x').read_bytes()!=native:raise ValueError('native reproduction mismatch')
        packed,script=package(source);repeat,_=package(source)
        if repeat!=packed:raise ValueError('whole-file reproduction mismatch')
        if name=='baseline' and (sha(source)!=selected['source_sha256'] or sha(native)!=selected['native_gate']['native_sha256'] or packed!=wrapper):
            raise ValueError('frozen best A did not reproduce')
        (dest/'wrapper').write_bytes(packed);(dest/'wrapper').chmod(0o755);(dest/'bootstrap.py').write_bytes(script)
        dev=dest/'dev';dev.mkdir();(dev/'main.c').write_bytes(combined)
        run(['cc','-std=c11','-Os','-pthread','-DWORKERS=2','-DTT_BITS=18','-DDEV=1','main.c','-o','x'],dev)
        row={'id':name,'readable_sha256':sha(combined),'source_bytes':len(source),'source_sha256':sha(source),
             'native_bytes':len(native),'native_sha256':sha(native),'whole_bytes':len(packed),'whole_sha256':sha(packed),
             'command':selected['command'],'native_reproduced':True,'whole_reproduced':True,
             'wrapper':str(dest/'wrapper'),'dev':str(dev/'x')}
        report['forms'].append(row);(args.out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(row),flush=True)


if __name__=='__main__':main()
