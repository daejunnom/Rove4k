#!/usr/bin/env python3
"""First full-file cost for one fixed C cache candidate, including control."""
import argparse
import ast
import hashlib
import importlib.util
import json
import lzma
import os
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def sha(data):return hashlib.sha256(data).hexdigest()


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


def normalized(path):
    data=path.read_bytes().replace(b'\r\n',b'\n')
    if b'\r' in data:raise ValueError('lone CR input: '+str(path))
    return data


def compile(command,source,directory):
    directory.mkdir()
    result=subprocess.run(command,input=source,cwd=directory,capture_output=True,timeout=90)
    (directory/'compiler.stderr').write_bytes(result.stderr)
    if result.returncode:raise RuntimeError('compiler failed: '+str(directory/'compiler.stderr'))
    return (directory/'x').read_bytes()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve()
    if not args.out.is_absolute() or out.exists() or out==ROOT or ROOT in out.parents or any((p/'.git').exists() for p in (out,*out.parents)):
        parser.error('new absolute external output required')
    out.mkdir(parents=True);frozen=out/'inputs';frozen.mkdir()
    recipe=json.loads(normalized(HERE/'inputs.json'))
    if recipe['family']!='C' or recipe['profile']!={'workers':2,'tt_bits':18,'ply':128,'dev_default':False}:
        raise ValueError('fixed C control profile differs')
    report={'complete':False,'scope':'one first-cost shipping HCE-cache removal; no selection sweep',
            'inputs':{},'forms':[],'tools':{name:subprocess.check_output(argv,text=True).splitlines()[0] for name,argv in
                {'cc':['cc','--version'],'ld':['ld','--version'],'python':['python3','--version'],'xz':['xz','--version']}.items()},
            'qualified_control_receipts':recipe['qualified_receipt']}
    def save():(out/'build.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        for name in ('build.py','generate.py','inputs.json','control.c','bootstrap.py.in','launcher.sh'):
            data=normalized(HERE/name);(frozen/name).write_bytes(data)
            report['inputs'][name]={'sha256':sha(data),'bytes':len(data)}
        for relative,pin in recipe['helper_sha256'].items():
            data=normalized(ROOT/relative)
            if sha(data)!=pin:raise ValueError('pinned helper changed: '+relative)
            (frozen/Path(relative).name).write_bytes(data)
            report['inputs'][relative]={'sha256':sha(data),'bytes':len(data)}
        control=(frozen/'control.c').read_bytes()
        for name in ('bootstrap.py.in','launcher.sh'):
            if sha((frozen/name).read_bytes())!=recipe['local_input_sha256'][name]:raise ValueError('fixed selected launcher input differs')
        expected=recipe['expected']
        if sha(control)!=expected['readable_sha256']:raise ValueError('fixed readable control differs')
        candidate,change=module('state_transform',frozen/'generate.py').transform(control)
        report['change']=change
        specializer=module('state_specialize',frozen/'specialize.py').specialize_c
        compact=module('state_minify',frozen/'minify.py').compact_source
        strip=module('state_strip',frozen/'stitch.py').strip_dev_counters
        literal=module('state_literal',frozen/'pack_stream.py').source_literal
        template=(frozen/'bootstrap.py.in').read_bytes();prefix=(frozen/'launcher.sh').read_bytes()
        marker=b'__ROVE_SOURCE_LITERAL__'
        if template.count(marker)!=1 or len(prefix)!=75:raise ValueError('fixed bootstrap shape differs')
        calls=[node for node in ast.walk(ast.parse(template)) if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and
               isinstance(node.func.value,ast.Name) and node.func.value.id=='subprocess' and node.func.attr=='Popen']
        if len(calls)!=1 or ast.literal_eval(calls[0].args[0])!=recipe['compiler']:raise ValueError('compiler recipe/bootstrap differ')
        def generate(source,directory,dev):
            active,observations=specializer({'main.c':source},directory,recipe['preprocessor']+['-DDEV='+str(int(dev))],os.environ.copy())
            result=compact(active['main.c'],'c')
            if not dev:result,_=strip(result)
            return result,observations
        def package(source):
            expression,_=literal(source);script=template.replace(marker,expression.encode());ast.parse(script)
            return prefix+lzma.compress(script,format=lzma.FORMAT_XZ,check=lzma.CHECK_CRC64,
                       filters=[{'id':lzma.FILTER_LZMA2,'preset':9|lzma.PRESET_EXTREME,'lc':3,'lp':0,'pb':2}]),script
        baseline_dev=None
        for label,readable in (('control',control),('candidate',candidate)):
            work=out/label;work.mkdir();(work/'combined.c').write_bytes(readable)
            first=None;attempts=[]
            for attempt in (1,2):
                directory=work/('attempt-'+str(attempt));directory.mkdir()
                source,observations=generate(readable,directory/'preprocess',False)
                (directory/'main.c').write_bytes(source)
                native=compile(recipe['compiler'],source,directory/'native')
                whole,script=package(source)
                dev,dev_observations=generate(readable,directory/'preprocess-dev',True)
                dev_native=compile(recipe['dev_compiler'],dev,directory/'dev')
                if sha(dev)!=expected['dev_source_sha256'] or sha(dev_native)!=expected['dev_native_sha256']:
                    raise ValueError('DEV exact source/native control changed')
                if label=='control' and (len(source)!=expected['source_bytes'] or sha(source)!=expected['source_sha256'] or
                    len(native)!=expected['native_bytes'] or sha(native)!=expected['native_sha256'] or
                    len(whole)!=expected['whole_bytes'] or sha(whole)!=expected['whole_sha256'] or sha(script)!=expected['bootstrap_sha256']):
                    raise ValueError('C5955 control did not reproduce')
                current=(source,native,whole,script,dev,dev_native)
                if first is None:first=current
                elif first!=current:raise ValueError('independent source/native/whole/DEV reproduction differs')
                attempts.append({'attempt':attempt,'source_sha256':sha(source),'native_sha256':sha(native),'whole_sha256':sha(whole),
                    'DEV_source_sha256':sha(dev),'DEV_native_sha256':sha(dev_native),'preprocessor':observations,'DEV_preprocessor':dev_observations})
            for name,data in zip(('main.c','native','x','bootstrap.py','dev.c','dev'),first):
                (work/name).write_bytes(data)
                if name in ('native','x','dev'):(work/name).chmod(0o755)
            report['forms'].append({'id':label,'readable':str(work/'combined.c'),'readable_sha256':sha(readable),
                'source':str(work/'main.c'),'source_bytes':len(first[0]),'source_sha256':sha(first[0]),
                'native':str(work/'native'),'native_bytes':len(first[1]),'native_sha256':sha(first[1]),
                'whole':str(work/'x'),'whole_bytes':len(first[2]),'whole_sha256':sha(first[2]),
                'bootstrap_sha256':sha(first[3]),'DEV_source_sha256':sha(first[4]),'DEV_native_sha256':sha(first[5]),
                'attempts':attempts,'independent_attempts':2,'DEV_exact_control':True})
            save()
        old,new=report['forms'];delta={key:new[key]-old[key] for key in ('source_bytes','native_bytes','whole_bytes')}
        report.update(complete=True,delta=delta,strict_source_cost_gain=delta['whole_bytes']<0,
                      runtime_qualified=False,eligible_4k=False,selected_fixed_resources=recipe['profile'])
        save();print(json.dumps({'complete':True,'delta':delta,'whole_bytes':new['whole_bytes'],'gain':delta['whole_bytes']<0}))
    except Exception as error:
        report['error']=repr(error);save();raise


if __name__=='__main__':main()
