#!/usr/bin/env python3
"""One fixed F scope-name plus already-frozen codec composition; no sourcegen or native build."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
API={'build.py':'7f5d2d3a52b5f3b4b3410cfad5919a7ec28b94baae8a331cbbf8c102b5adaa90',
     'decode.py':'c43303b6524321b24dfba069afc9a135998e408503740ea8d9fbcfb9bb5e9f5a',
     'launcher.sh':'78c5b572036e14ed33098fa4fb10fd10f4e061305e158f1609bae95d41e60301'}
COMPILER=['cc','-Os','-pthread','-x','c','-','-o','x','-s']

def sha(data):return hashlib.sha256(data).hexdigest()

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result);return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve()
    if not args.out.is_absolute() or out.exists() or any((p/'.git').exists() for p in (out,*out.parents)):
        parser.error('new absolute external output outside Git required')
    raw=(HERE/'composition.json').read_bytes();fixed=json.loads(raw)
    if fixed['stage']!='F5051-scope-names-plus-one-fixed-codec' or fixed['repetitions']!=2 or fixed['nice_len']!=32:
        raise ValueError('fixed single composition scope changed')
    if sha((HERE/'compose.py').read_bytes())!=fixed['producer_sha256'] or fixed['API']!=API:
        raise ValueError('literal producer/API pins changed')
    if fixed['compiler_argv']!=COMPILER:raise ValueError('original F5051 compiler argv changed')
    if fixed['base_F5051']!={'source_sha256':'c63a450245ff4ca703a5abe2dc75d840c7c7e936bb2a30a726c30014e3a92e90','whole_bytes':5051}:
        raise ValueError('composition base is not the separate newer F5051')
    ordinary={}
    for name,pin in API.items():
        data=(HERE/name).read_bytes()
        if sha(data)!=pin:raise ValueError('frozen codec API changed: '+name)
        ordinary[name]=data
    reused={}
    if set(fixed['inputs'])!={'source','bootstrap','scope_whole_1','scope_whole_2','names_receipt'}:
        raise ValueError('explicit reuse input set changed')
    for name,pin in fixed['inputs'].items():
        path=Path(pin['path'])
        if not path.is_absolute():raise ValueError('explicit absolute prior input required')
        data=path.read_bytes()
        if {'bytes':len(data),'sha256':sha(data)}!={k:pin[k] for k in ('bytes','sha256')}:
            raise ValueError('explicit scope-name artifact pin changed: '+name)
        reused[name]=data
    if reused['scope_whole_1']!=reused['scope_whole_2']:raise ValueError('prior original-codec scope whole repeats differ')
    out.mkdir(parents=True);inputs=out/'inputs';inputs.mkdir()
    for name,data in ordinary.items():(inputs/name).write_bytes(data)
    for name in ('compose.py','composition.json'):(inputs/name).write_bytes((HERE/name).read_bytes())
    prior=out/'reused';prior.mkdir()
    for name,data in reused.items():(prior/name).write_bytes(data)
    report={'complete':False,'stage':fixed['stage'],'explicit_prior_inputs':fixed['inputs'],'API':API,
            'base_F5051':fixed['base_F5051'],'attempts':[],'codec_compressions':0,'strict_pure_decodes':0,
            'sourcegen':0,'preprocessing':0,'native_compiles':0,'engine_runs':0,'bootstrap_runs':0,
            'prior_name_qualification_referenced_not_reexecuted':True,'native_identity_or_runtime_acceptance':False}
    def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        codec=module('composition_fixed_codec',inputs/'build.py');decoder=module('composition_fixed_decoder',inputs/'decode.py')
        prefix=ordinary['launcher.sh'];source=reused['source'];script=reused['bootstrap'];first=None
        for index in (1,2):
            report['codec_compressions']+=1;save()
            payload=codec.encode(script,codec.SETTINGS,32);whole=prefix+payload
            report['strict_pure_decodes']+=1
            proof=decoder.verify(whole,prefix,source,fixed['compiler_argv'],script,expected_format='alone')
            attempt=out/('attempt-'+str(index));attempt.mkdir();(attempt/'x').write_bytes(whole);(attempt/'x').chmod(0o755)
            proof_raw=(json.dumps(proof,indent=2)+'\n').encode();(attempt/'decode-proof.json').write_bytes(proof_raw)
            report['attempts'].append({'attempt':index,'whole_bytes':len(whole),'whole_sha256':sha(whole),
                'prefix_bytes':len(prefix),'payload_bytes':len(payload),'decode_proof_sha256':sha(proof_raw)})
            if first is None:first=whole
            elif whole!=first:raise ValueError('independent combined codec output differs')
            save()
        (out/'x').write_bytes(first);(out/'x').chmod(0o755)
        report.update(complete=True,whole_bytes=len(first),whole_sha256=sha(first),source_bytes=len(source),source_sha256=sha(source),
            bootstrap_bytes=len(script),bootstrap_sha256=sha(script),compiler_argv=fixed['compiler_argv'],
            scope_original_codec_whole_bytes=len(reused['scope_whole_1']),codec_saved_from_scope_bytes=len(reused['scope_whole_1'])-len(first),
            combined_saved_from_F5051_bytes=5051-len(first),remaining_over4096=len(first)-4096,
            independent_complete_bytes_equal=True,strict_actual_source_and_argv_recovery=True,
            runtime_normal_or_maintained_acceptance=False,checksum_note='LZMA-alone has no container checksum; analysis recovery does not preserve XZ CRC64 corruption detection')
        save();print(json.dumps({k:report[k] for k in ['complete','whole_bytes','whole_sha256','codec_saved_from_scope_bytes',
            'combined_saved_from_F5051_bytes','remaining_over4096','native_compiles','engine_runs']}),flush=True)
        return 0
    except BaseException as error:
        report.update(complete=False,error=repr(error))
        try:save()
        except BaseException:pass
        raise

if __name__=='__main__':raise SystemExit(main())
