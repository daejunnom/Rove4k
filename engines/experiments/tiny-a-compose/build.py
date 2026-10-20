#!/usr/bin/env python3
"""Measure one ownership-source/LZMA-alone composition after exact controls.

This cost-stage producer admits immutable control artifacts by literal hashes;
it does not compile or execute an engine. Canonical regeneration and selected
physical runtime qualification are separate. There is no preset/name search.
"""
import argparse
import ast
import hashlib
import json
import lzma
from pathlib import Path
import subprocess
import sys

PINS={
 'control':{'main.c':'5e0e77321110371aec3a7a06f93290e7581f08f721fc9bb07fcef26c406429b7',
            'bootstrap.py':'11679fb20e24e7cb777cb49e4bee5a7ee7ea999278651fbba6d622320e751d44',
            'native/x':'d39167146236aafde21b59439b853bd10561f04e9186c18b839c2f84f2e16e12',
            'x':'085fcf6bd411a59111aaebbdc6bd59e2687a5c38de2ce28f0ad9643882633e36'},
 'ownership':{'engine.c':'79284c72b64d087aa3127ea65b461aef8c7776355ea1c4ab9b2f81e59b4b48ed',
              'main.c':'5ed00fd936cf6228ec7f73d6c1fddd0f18bfe899aff82b5aa695732240079b59',
              'bootstrap.py':'833d83371cd7ddb11a4a940801fe99c4e2ffc11fc2da32482ee264f20883b095',
              'native/x':'6d9a3c192078f22914e17a0332ef2f0dbd134050833c1fceb0ccb221ecba34e2',
              'x':'9a4911a0364c881e88764dbf41832c051eead2961160cae97136668405cbfa7b',
              'dev/main.c':'60e40bfa24ae06afdafbdfffacda2576b7056d22dffb12e70a22d0d8c3142942',
              'dev/x':'ff29baa1648f68812424f6e1f718f5e44b9037813e74dc2492a3e4425c88cb0f'},
 'transport':{'x':'4f1562199786596c4addb36c1b47ecdcee143ca0338e8c986d350fe5639d1f8c'}
}
SUMMARY_SHA='671717f28b8efdf6417c2d660aac1a2a9bde0dff3661cb22caff3b4b78090407'
PREFIX=b'#!/bin/sh\np=$(tail -c+76 "$0"|xz -dc)||exit\nexec python3 -c "$p" "$0" "$@"\n'
ALONE_PREFIX=b'#!/bin/sh\np=$(tail -c+78 "$0"|lzma -dc)||exit\nexec python3 -c "$p" "$0" "$@"\n'
COMPILER=['cc','-Os','-x','c','-','-o','x','-s']


def sha(data):return hashlib.sha256(data).hexdigest()


def require(value,message):
    if not value:raise ValueError(message)


def source_from_bootstrap(data):
    tree=ast.parse(data)
    calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
           and isinstance(n.func.value,ast.Name) and n.func.value.id=='p' and n.func.attr=='communicate']
    require(len(calls)==1 and len(calls[0].args)==1,'unknown source restore shape')
    node=calls[0].args[0]
    if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='encode':
        require(not node.args and not node.keywords,'source encode args changed')
        source=ast.literal_eval(node.func.value).encode()
    else:source=ast.literal_eval(node)
    require(isinstance(source,bytes),'source is not bytes')
    spawns=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
            and isinstance(n.func.value,ast.Name) and n.func.value.id=='subprocess' and n.func.attr=='Popen']
    require(len(spawns)==1 and spawns[0].args,'unknown compiler spawn')
    arg=spawns[0].args[0]
    require(isinstance(arg,ast.Call) and isinstance(arg.func,ast.Attribute) and arg.func.attr=='split'
            and not arg.args and not arg.keywords,'compiler representation changed')
    require(ast.literal_eval(arg.func.value).split()==COMPILER,'compiler argv changed')
    return source


def encode(script,alone):
    return lzma.compress(script,format=lzma.FORMAT_ALONE if alone else lzma.FORMAT_XZ,
        check=lzma.CHECK_NONE if alone else lzma.CHECK_CRC64,
        filters=[{'id':lzma.FILTER_LZMA1 if alone else lzma.FILTER_LZMA2,
                  'preset':9|lzma.PRESET_EXTREME,'lc':2,'lp':0,'pb':0}])


def decoded(payload,alone):
    decoder=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE if alone else lzma.FORMAT_XZ)
    data=decoder.decompress(payload)
    require(decoder.eof and not decoder.unused_data,'compressed stream incomplete or has trailing bytes')
    command=['lzma' if alone else 'xz','-dc']
    cli=subprocess.run(command,input=payload,capture_output=True,timeout=15)
    require(cli.returncode==0 and not cli.stderr and cli.stdout==data,'independent CLI decoder mismatch')
    return data


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('control','ownership','transport','ownership-summary','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve()
    require(args.out.is_absolute() and not out.exists() and not any((p/'.git').exists() for p in (out,*out.parents)),
            'new absolute output outside Git required')
    require(sys.platform=='linux','recorded Linux decoder target required')
    out.mkdir(parents=True);frozen=out/'inputs';frozen.mkdir()
    report={'complete':False,'scope':'one fixed first-cost composition, all three raw controls preserved; no engine/compiler execution',
            'compiler_run':False,'runtime_qualified':False,'inputs':{},'controls':[],'attempts':[]}
    def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    def retain(name,data):
        path=frozen/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        report['inputs'][name]={'bytes':len(data),'sha256':sha(data)}
    save()
    try:
        summary=args.ownership_summary.read_bytes();require(sha(summary)==SUMMARY_SHA,'unknown ownership qualification')
        retain('ownership-summary.json',summary);retain('producer.py',Path(__file__).read_bytes())
        objects={}
        for form,pins in PINS.items():
            root=getattr(args,form).resolve(strict=True);objects[form]={}
            for name,expected in pins.items():
                data=(root/name).read_bytes();require(sha(data)==expected,'unknown '+form+' input '+name)
                objects[form][name]=data;retain(form+'/'+name,data)
        require(len(PREFIX)==75 and len(ALONE_PREFIX)==77,'fixed prefix changed')
        for form,alone,script in (('control',False,objects['control']['bootstrap.py']),
                                 ('transport',True,objects['control']['bootstrap.py']),
                                 ('ownership',False,objects['ownership']['bootstrap.py'])):
            prefix=ALONE_PREFIX if alone else PREFIX;whole=objects[form]['x']
            source=objects['ownership' if form=='ownership' else 'control']['main.c']
            require(whole.startswith(prefix) and source_from_bootstrap(script)==source,'prefix/source restoration mismatch')
            for _ in (1,2):
                require(prefix+encode(script,alone)==whole,'pinned complete control did not re-encode exactly')
                require(decoded(whole[len(prefix):],alone)==script,'pinned control did not strictly decode')
            report['controls'].append({'form':form,'bytes':len(whole),'sha256':sha(whole),'exact_reencodes':2,'strict_and_CLI_decodes':2})
        script=objects['ownership']['bootstrap.py'];first=None
        for index in (1,2):
            payload=encode(script,True);whole=ALONE_PREFIX+payload
            require(payload[:13]==bytes.fromhex('0200000004ffffffffffffffff'),'fixed LZMA-alone header changed')
            require(decoded(payload,True)==script,'combined bootstrap restoration mismatch')
            if first is None:first=whole
            else:require(whole==first,'combined complete bytes did not reproduce')
            directory=out/('attempt-'+str(index));directory.mkdir()
            (directory/'x').write_bytes(whole);(directory/'x').chmod(0o755)
            (directory/'bootstrap.py').write_bytes(script)
            report['attempts'].append({'attempt':index,'bytes':len(whole),'whole_sha256':sha(whole),
                                      'bootstrap_sha256':sha(script),'source_sha256':sha(objects['ownership']['main.c']),
                                      'native_sha256':sha(objects['ownership']['native/x'])});save()
        report.update(complete=True,combined_bytes=len(first),combined_sha256=sha(first),
                      smaller_than_both_qualified_alternatives=len(first)<min(len(objects['transport']['x']),len(objects['ownership']['x'])),
                      delta_vs_5163=len(first)-len(objects['transport']['x']),delta_vs_5183=len(first)-len(objects['ownership']['x']),
                      source_unchanged_from_ownership=True,bootstrap_unchanged_from_ownership=True)
        save();print(json.dumps({key:report[key] for key in ('complete','combined_bytes','combined_sha256',
            'smaller_than_both_qualified_alternatives','delta_vs_5163','delta_vs_5183')}))
    except Exception as error:
        report['error']=repr(error);save();raise


if __name__=='__main__':main()
