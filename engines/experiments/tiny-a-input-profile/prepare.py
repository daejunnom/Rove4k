"""Pure A profile preparation. This producer cannot compile, pack or run targets."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def pin(path):
    raw=path.read_bytes()
    return {'path':str(path),'bytes':len(raw),'sha256':sha(raw)}

def require(value,message):
    if not value:raise ValueError(message)

def check(raw,expected,label):
    require(len(raw)==expected['bytes'] and sha(raw)==expected['sha256'],label+' pin differs')

def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--baseline',type=Path,required=True)
    cli.add_argument('--canonical',type=Path,required=True)
    cli.add_argument('--out',type=Path,required=True)
    args=cli.parse_args()
    require(all(p.is_absolute() for p in (args.baseline,args.canonical,args.out)), 'absolute paths required')
    args.out.mkdir()
    report={'complete':False,'stage':'source preparation only; first cost not authorized by this producer',
            'compiler_runs':0,'codec_runs':0,'engine_runs':0,'AST':0,'compiler_preprocessing':0,
            'control_artifact_copies':0,'control_compiles':0,'games':0,'benchmarks':0,'inputs':{}}
    def save():(args.out/'results.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
    save()
    try:
        producer=args.out/'producer';producer.mkdir()
        for name in ('prepare.py','profile.py','recipe.json','.gitattributes'):
            source=Path(__file__).parent/name
            raw=source.read_bytes();(producer/name).write_bytes(raw)
            report['inputs'][name]=pin(producer/name)
        recipe=json.loads((producer/'recipe.json').read_bytes())
        require(report['inputs']['profile.py']['sha256']==recipe['profile_sha256'],'profile source differs')
        controls={}
        for name,expected in recipe['baseline'].items():
            path=args.baseline/name;raw=path.read_bytes();check(raw,expected,name)
            controls[name]=raw;report['inputs'][name]=pin(path)
        canonical=args.canonical.read_bytes();check(canonical,recipe['canonical'],'A canonical')
        report['inputs']['canonical']=pin(args.canonical)
        spec=importlib.util.spec_from_file_location('prepared_fixed_A_profile',producer/'profile.py')
        profile=importlib.util.module_from_spec(spec);spec.loader.exec_module(profile)
        readable,shipping,proof=profile.transform(canonical,controls['main.c'])
        check(readable,recipe['candidate']['readable'],'candidate readable')
        check(shipping,recipe['candidate']['shipping'],'candidate shipping')
        require(b'}#else' not in readable and b'}#endif' not in readable,'directive boundary differs')
        (args.out/'readable.c').write_bytes(readable);(args.out/'main.c').write_bytes(shipping)
        report.update(complete=True,candidate_count=1,readable=pin(args.out/'readable.c'),
                      shipping=pin(args.out/'main.c'),transform=proof,policy=recipe['policy'],
                      shipping_source_delta=len(shipping)-len(controls['main.c']),
                      first_cost_GO_received=False,F_functional_GO_observed=False,
                      native_or_whole_candidate_measured=False,DEV_compilation_confirmed=False,
                      live_owned_handles=0)
    except BaseException as error:
        report['error']={'type':type(error).__name__,'message':str(error)}
        raise
    finally:
        save()
    print(json.dumps({'readable':report['readable'],'shipping':report['shipping'],
                      'shipping_source_delta':report['shipping_source_delta'],'compiler':0,'codec':0,'engine':0}))

if __name__=='__main__':main()
