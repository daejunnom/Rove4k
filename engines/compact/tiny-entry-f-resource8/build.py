#!/usr/bin/env python3
"""Late fixed full-F workers8/TT18 profile from an exact ordinary base source."""
import argparse,ast,hashlib,importlib.util,json,lzma,os,platform,resource,shutil,signal,subprocess,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]

def sha(data):return hashlib.sha256(data).hexdigest()
def require(value,message):
    if not value:raise ValueError(message)
def normalized(path):
    data=path.read_bytes().replace(b'\r\n',b'\n')
    require(b'\r' not in data,'lone CR in source: '+str(path));return data
def identity(path):
    data=path.read_bytes();return {'path':str(path),'bytes':len(data),'sha256':sha(data)}
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec)
    sys.modules[name]=result;spec.loader.exec_module(result);return result

def source_closure():
    """Current project code provenance plus this separate profile and normal helpers."""
    recipe=json.loads(normalized(HERE/'recipe.json'));result={}
    for name,expected in {**recipe['base_source_closure_sha256'],**recipe['positive_helper_sha256']}.items():
        actual=sha(normalized(REPO/name));require(actual==expected,'project source closure changed: '+name);result[name]=actual
    for name in ('build.py','recipe.json','specialize.py','README.md','verify.py'):
        path=HERE/name;result[str(path.relative_to(REPO))]=sha(normalized(path))
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-source',type=Path,required=True,help='exact full-F2/18 compact C from its ordinary producer')
    parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();out=args.out.resolve()
    if sys.platform!='linux' or platform.machine()!='x86_64':parser.error('Linux x86-64 required')
    if not args.base_source.is_absolute() or not args.out.is_absolute() or out.exists() or out==REPO or REPO in out.parents or any((p/'.git').exists() for p in (out,*out.parents)):
        parser.error('absolute base source and new external output required')
    recipe_raw=normalized(HERE/'recipe.json');recipe=json.loads(recipe_raw)
    require(recipe['class']=='full-F-fixed-resource8-TT18-v1' and recipe['profile']=={'workers':8,'tt_bits':18,'ply':128,'native_TIDs':9},'one fixed resource profile only')
    require(recipe['compiler']==['cc','-Os','-pthread','-x','c','-','-o','x','-s'],'fixed compiler arguments differ')
    require(recipe['compression']=={'format':'lzma-alone','filter':'LZMA1','preset':6,'extreme':False,'lc':2,'lp':0,'pb':0,'check':'NONE','mf':'BT2','dictionary_bytes':16384,'nice_len':24},'fixed full-F codec differs')
    base=args.base_source.read_bytes();require({'bytes':len(base),'sha256':sha(base)}==recipe['base_source'] and b'\r' not in base,'unknown ordinary full-F2 source')
    closure=source_closure();limits=recipe['limits'];out.mkdir()
    report={'complete':False,'class':recipe['class'],'profile':recipe['profile'],'base_profile':recipe['base_profile'],
        'base_source':identity(args.base_source),'source_closure':closure,'recipe_sha256':sha(recipe_raw),'limits':limits,
        'commands':[],'attempts':[],'counts':{'candidate_compile':0,'candidate_encode':0,'strict_Python_restore':0,'baseline_compile':0,'baseline_encode':0,'separate_PP':0,'ELF_execution':0},
        'runtime_qualified':False,'final_4k_allocation':'unknown','rules_eligibility':'unproven','authority':'exact base C and project code closure; no historical research JSON/native inputs'}
    active=None;deadline=time.monotonic()+limits['aggregate_wall'];env={**os.environ,'LC_ALL':'C','TZ':'UTC','PYTHONDONTWRITEBYTECODE':'1'}
    def save():(out/'build.json').write_text(json.dumps(report,indent=2)+'\n')
    def stop(sig,frame):raise TimeoutError('bounded builder signal '+str(sig))
    handled=(signal.SIGTERM,signal.SIGINT,signal.SIGALRM,signal.SIGXCPU);saved_signal_handlers={sig:signal.signal(sig,stop) for sig in handled}
    resource.setrlimit(resource.RLIMIT_AS,(limits['parent_AS'],)*2);resource.setrlimit(resource.RLIMIT_CPU,(limits['parent_CPU'],)*2);signal.alarm(limits['aggregate_wall'])
    def run(command,cwd=out,data=None,kind='metadata'):
        nonlocal active
        row={'kind':kind,'command':[str(x) for x in command],'cwd':str(cwd),'started':False};report['commands'].append(row);save()
        mask=signal.pthread_sigmask(signal.SIG_BLOCK,set(handled))
        def setup():
            resource.setrlimit(resource.RLIMIT_AS,(limits['child_AS'],)*2);resource.setrlimit(resource.RLIMIT_CPU,(limits['child_CPU'],)*2);signal.pthread_sigmask(signal.SIG_SETMASK,mask)
        try:
            try:
                active=subprocess.Popen(row['command'],cwd=cwd,env=env,stdin=subprocess.PIPE if data is not None else subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,preexec_fn=setup)
                row.update(started=True,pid=active.pid,pgid=active.pid);save()
            finally:signal.pthread_sigmask(signal.SIG_SETMASK,mask)
            output,error=active.communicate(data,timeout=min(limits['per_command_wall'],max(.1,deadline-time.monotonic())))
            row.update(returncode=active.returncode,terminal=True,stdout_bytes=len(output),stdout_sha256=sha(output),stderr=error.decode(errors='replace'))
            require(len(output)+len(error)<=limits['tool_output_bytes'],'tool output cap');require(active.returncode==0,'tool failed: '+kind);return output
        finally:
            if active is not None:
                if active.poll() is None or active.returncode:
                    try:os.killpg(active.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                    output,error=active.communicate(timeout=5);row.setdefault('stdout_bytes',len(output));row.setdefault('stdout_sha256',sha(output));row.setdefault('stderr',error.decode(errors='replace'))
                row.update(returncode=active.returncode,terminal=active.poll() is not None)
                try:os.killpg(active.pid,0);row['forced_group_cleanup']=True;os.killpg(active.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                try:os.killpg(active.pid,0);row['owned_group_absent']=False
                except ProcessLookupError:row['owned_group_absent']=True
                active=None
            save()
    try:
        frozen=out/'inputs'
        for name,pinned in closure.items():
            raw=normalized(REPO/name);require(sha(raw)==pinned,'source changed during freeze: '+name)
            target=frozen/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
        (out/'base-source.c').write_bytes(base);own=frozen/HERE.relative_to(REPO)
        packaging={name:frozen/path for name,path in recipe['packaging_paths'].items()}
        names=module('fixed_full_F_names',packaging['shipping_names.py'])
        named,name_proof=names.transform_source(base)
        (out/'source-names-proof.json').write_text(json.dumps(name_proof,indent=2)+'\n');report['source_names_proof']=identity(out/'source-names-proof.json')
        require(sha((own/'specialize.py').read_bytes())==recipe['specialize_sha256'],'pure six-role helper changed')
        specialize=module('fixed_resource8_specialize',own/'specialize.py');source,proof=specialize.transform_source(named)
        require({'bytes':len(source),'sha256':sha(source)}=={'bytes':recipe['expected']['source_bytes'],'sha256':recipe['expected']['source_sha256']} and proof['full_inverse'] and proof['raw_delta']==0 and [x['role'] for x in proof['edits']]==recipe['source_roles'],'source/profile proof differs')
        (out/'source-proof.json').write_text(json.dumps(proof,indent=2)+'\n');report['source_proof']=identity(out/'source-proof.json')
        literal=module('fixed_resource8_literal',packaging['pack_stream.py']).source_literal
        common=module('fixed_resource8_common',packaging['shipping_common.py']);template=packaging['bootstrap.py.in'].read_bytes();prefix=packaging['launcher.sh'].read_bytes();marker=b'__ROVE_SOURCE_LITERAL__'
        require(template.count(marker)==1 and len(prefix)==77,'fixed legacy marker/prefix differs')
        full_template=module('fixed_full_F_template',packaging['bootstrap_full.py'])
        source_package=module('fixed_source_package',packaging['source_package.py'])
        template=full_template.prepare_template(template);prefix=source_package.XZ_STDIN_HEADER
        require(len(prefix)==recipe['prefix_bytes']==73,'fixed selected prefix differs')
        tools={'cc':run(['cc','--version']).decode().splitlines()[0],'ld':run(['ld','--version']).decode().splitlines()[0],'python':run([sys.executable,'--version']).decode().strip(),'lzma':run(['lzma','--version']).decode().splitlines()[0]}
        require(tools==recipe['tools'],'selected tool version differs');report['tools']=tools
        for label in ('first','repeat'):
            local=out/label;local.mkdir();(local/'main.c').write_bytes(source);native_dir=local/'native';native_dir.mkdir();report['counts']['candidate_compile']+=1
            run(recipe['compiler'],native_dir,source,'candidate8-'+label);native=(native_dir/'x').read_bytes();expected=recipe['expected']
            require(len(native)==expected['native_bytes'] and sha(native)==expected['native_sha256'],'literal resource8 native differs')
            expression,kind=common.source_literal(source,literal);script=template.replace(marker,expression.encode());ast.parse(script)
            require(len(script)==expected['bootstrap_bytes'] and sha(script)==expected['bootstrap_sha256'],'literal resource8 bootstrap differs')
            report['counts']['candidate_encode']+=1;whole=source_package.package(script,recipe['compression'],prefix=prefix);payload=whole[len(prefix):]
            require(payload[:13].hex()==recipe['ALONE_header_hex'],'ALONE header changed');decoder=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE);restored=decoder.decompress(payload,max_length=len(script)+1);report['counts']['strict_Python_restore']+=1
            require(restored==script and decoder.eof and not decoder.unused_data,'strict ALONE restoration failed')
            require(len(whole)==expected['whole_bytes'] and sha(whole)==expected['whole_sha256'],'literal resource8 whole differs')
            (local/'bootstrap.py').write_bytes(script);(local/'payload.lzma').write_bytes(payload);(local/'x').write_bytes(whole);(local/'x').chmod(0o755)
            report['attempts'].append({'source':identity(local/'main.c'),'native':identity(native_dir/'x'),'bootstrap':identity(local/'bootstrap.py'),'whole':identity(local/'x'),'payload':identity(local/'payload.lzma'),'literal_kind':kind,'strict_restore':True});save()
        first,repeat=report['attempts'];require(all(Path(first[k]['path']).read_bytes()==Path(repeat[k]['path']).read_bytes() for k in ('source','native','bootstrap','whole','payload')),'independent normal bytes differ')
        require(source_closure()==closure and args.base_source.read_bytes()==base,'source closure/base changed during build')
        require(all(c.get('terminal') and c.get('owned_group_absent') and not c.get('forced_group_cleanup',False) for c in report['commands']),'tool cleanup needed intervention')
        report.update(complete=True,source_reproduced=True,native_reproduced=True,bootstrap_reproduced=True,whole_reproduced=True)
    except BaseException as error:report['first_failure']={'type':type(error).__name__,'message':str(error)};raise
    finally:
        signal.alarm(0);report['owned_active_tool']=None if active is None else active.pid;save()
        for sig,handler in saved_signal_handlers.items():signal.signal(sig,handler)
        print(json.dumps({'out':str(out),'complete':report['complete'],'counts':report['counts'],'first_failure':report.get('first_failure')}))

if __name__=='__main__':main()
