#!/usr/bin/env python3
"""One candidate compile/package; two strict decodes; never executes an engine."""
import argparse,ast,hashlib,importlib.util,json,lzma,os,signal,subprocess
from pathlib import Path
from transform import transform
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def sha(data):return hashlib.sha256(data).hexdigest()
def normalized(path):return path.read_bytes().replace(b'\r\n',b'\n')
def identity(data,expected,prefix):
    if len(data)!=expected[prefix+'_bytes'] or sha(data)!=expected[prefix+'_sha256']:
        raise ValueError(prefix+' identity mismatch')
def strict_decode(whole,source,template,prefix,command,literal):
    if not whole.startswith(prefix):raise ValueError('prefix mismatch')
    payload=whole[len(prefix):]
    if payload[0]!=2 or int.from_bytes(payload[1:5],'little')!=67108864:raise ValueError('ALONE lc2/lp0/pb0/dict differs')
    decoder=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    script=decoder.decompress(payload)
    if not decoder.eof or decoder.unused_data:raise ValueError('incomplete/trailing stream')
    tree=ast.parse(script);calls=[n for n in ast.walk(tree)if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)]
    popen=[n for n in calls if n.func.attr=='Popen'and isinstance(n.func.value,ast.Name)and n.func.value.id=='subprocess']
    communicate=[n for n in calls if n.func.attr=='communicate'and isinstance(n.func.value,ast.Name)and n.func.value.id=='p']
    if len(popen)!=1 or ast.literal_eval(popen[0].args[0])!=command or len(communicate)!=1:raise ValueError('compiler/source consumer differs')
    node=communicate[0].args[0]
    if isinstance(node,ast.Call)and isinstance(node.func,ast.Attribute)and node.func.attr=='encode'and not node.args and not node.keywords:
        recovered=ast.literal_eval(node.func.value).encode()
    else:recovered=ast.literal_eval(node)
    expression,_=literal(source)
    if recovered!=source or script!=template.replace(b'__ROVE_SOURCE_LITERAL__',expression.encode()):raise ValueError('restored source/bootstrap differs')
    return {'source_sha256':sha(recovered),'bootstrap_bytes':len(script),'bootstrap_sha256':sha(script),'eof':True,'unused_bytes':0,'compiler_argv_equal':True}
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,type=Path);parser.add_argument('--control-dir',required=True,type=Path);args=parser.parse_args()
    out=args.out.resolve();control=args.control_dir.resolve()
    if not args.out.is_absolute()or out.exists()or out==ROOT or ROOT in out.parents:parser.error('new absolute output outside Git required')
    out.mkdir();report={'complete':False,'candidate_compile_count':0,'candidate_package_count':0,'strict_decode_count':0,'control_compile_count':0,'engine_count':0,'fixed_variants':1,'active_compiler':False}
    def save():(out/'cost.json').write_text(json.dumps(report,indent=2)+'\n')
    try:
        cfg=json.loads((HERE/'config.json').read_text());entry=ROOT/'engines/compact/tiny-entry-c';recipe=json.loads((entry/'recipe.json').read_text())
        if recipe['profile']!=cfg['profile']or recipe['compiler']!=cfg['compiler']or recipe['compression']!=cfg['compression']:raise ValueError('current fixed C recipe differs')
        source=(control/'main.c').read_bytes();native=(control/'native/x').read_bytes();whole=(control/'x').read_bytes();meta=json.loads((control/'build.json').read_text())
        for data,kind in ((source,'source'),(native,'native'),(whole,'whole')):identity(data,cfg['baseline'],kind)
        if meta['actual']['source_sha256']!=sha(source)or meta['actual']['native_sha256']!=sha(native)or meta['actual']['whole_sha256']!=sha(whole):raise ValueError('actual control metadata mismatch')
        template=normalized(entry/'bootstrap.py.in');prefix=normalized(entry/'launcher.sh');helper=ROOT/'engines/compact/tiny-a/pack_stream.py'
        if sha(template)!=cfg['template_sha256']or len(prefix)!=77 or sha(prefix)!=cfg['prefix_sha256']or sha(normalized(helper))!=cfg['literal_helper_sha256']:raise ValueError('closing input changed')
        snapshots={p:p.read_bytes()for p in [entry/'recipe.json',entry/'bootstrap.py.in',entry/'launcher.sh',helper,*sorted(HERE.glob('*.py')),HERE/'config.json']}
        inputs=out/'inputs';inputs.mkdir()
        for index,(path,data)in enumerate(snapshots.items()):(inputs/(str(index)+'-'+path.name)).write_bytes(data)
        report['source_inputs']=[{'path':str(p),'bytes':len(d),'sha256':sha(d)}for p,d in snapshots.items()]
        spec=importlib.util.spec_from_file_location('signed_vector_cost_literal',helper);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);literal=module.source_literal
        report['baseline_decode']=strict_decode(whole,source,template,prefix,cfg['compiler'],literal);report['strict_decode_count']+=1
        if report['baseline_decode']['bootstrap_sha256']!=cfg['baseline']['bootstrap_sha256']:raise ValueError('baseline bootstrap identity differs')
        candidate=transform(source);identity(candidate,cfg['candidate'],'source');(out/'main.c').write_bytes(candidate)
        report['compiler_version']=subprocess.check_output(['cc','--version'],text=True).splitlines()[0]
        if report['compiler_version']!=meta['tools']['cc']:raise ValueError('compiler identity differs from actual control')
        directory=out/'native';directory.mkdir();report['candidate_compile_count']=1;report['active_compiler']=True;save()
        process=subprocess.Popen(cfg['compiler'],cwd=directory,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        try:stdout,stderr=process.communicate(candidate,timeout=90)
        except BaseException:
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            stdout,stderr=process.communicate();raise
        finally:report['active_compiler']=process.poll()is None
        (out/'compiler.stdout').write_bytes(stdout);(out/'compiler.stderr').write_bytes(stderr)
        if process.returncode:raise ValueError('candidate compile failed: '+str(process.returncode))
        try:os.killpg(process.pid,0);raise ValueError('owned compiler group remains')
        except ProcessLookupError:pass
        image=(directory/'x').read_bytes()
        if image[:4]!=b'\x7fELF':raise ValueError('candidate is not ELF')
        expression,_=literal(candidate);script=template.replace(b'__ROVE_SOURCE_LITERAL__',expression.encode())
        package=prefix+lzma.compress(script,format=lzma.FORMAT_ALONE,check=lzma.CHECK_NONE,filters=[{'id':lzma.FILTER_LZMA1,'preset':9|lzma.PRESET_EXTREME,'lc':2,'lp':0,'pb':0,'mf':lzma.MF_BT4,'dict_size':67108864,'nice_len':64}]);report['candidate_package_count']=1
        (out/'x').write_bytes(package);(out/'bootstrap.py').write_bytes(script)
        report['candidate_decode']=strict_decode(package,candidate,template,prefix,cfg['compiler'],literal);report['strict_decode_count']+=1
        for p,data in snapshots.items():
            if p.read_bytes()!=data:raise ValueError('upstream/source input drift')
        report.update(complete=True,baseline=cfg['baseline'],candidate={'source_bytes':len(candidate),'source_sha256':sha(candidate),'native_bytes':len(image),'native_sha256':sha(image),'whole_bytes':len(package),'whole_sha256':sha(package),'bootstrap_bytes':len(script),'bootstrap_sha256':sha(script)},delta={'source_bytes':len(candidate)-len(source),'native_bytes':len(image)-len(native),'whole_bytes':len(package)-len(whole)},result='gain'if len(package)<len(whole)else'loss'if len(package)>len(whole)else'tie',upstream_inputs_unchanged=True,semantic_or_layout_validation=False,old_board_state_proof_inherited=False,old_AVX2_256_leaf_instruction_claim_inherited=False,intrinsic_minimum_ISA='SSE2 madd+SSSE3 hadd; fixed -mavx2 compiler unchanged',actual_runtime_SIMD_qualified=False)
    except BaseException as error:report['error']=repr(error);raise
    finally:save()
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
