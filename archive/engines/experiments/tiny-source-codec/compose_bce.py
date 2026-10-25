#!/usr/bin/env python3
"""Three fixed private-static-plus-local source codec comparisons; no native build."""
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
     'launcher.sh':'78c5b572036e14ed33098fa4fb10fd10f4e061305e158f1609bae95d41e60301',
     'control-head/engines/compact/tiny-entry-b/launcher.sh':'a6fd458f0dec9193341bfe2ea128b0e4cba9aa3409822f85d2ca0f435734f50a'}
COMPILER=['cc','-std=c11','-Os','-pthread','-DWORKERS=2','-DTT_BITS=18','-DDEV=0','-x','c','-','-o','x']
OLD={'format':'xz','lc':3,'lp':0,'pb':2}
NICE={'B':32,'C':64,'E':32}

def sha(data):return hashlib.sha256(data).hexdigest()

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result);return result

def pinned(pin):
    path=Path(pin['path'])
    if not path.is_absolute():raise ValueError('absolute prior path required')
    data=path.read_bytes()
    if {'bytes':len(data),'sha256':sha(data)}!={k:pin[k] for k in ('bytes','sha256')}:
        raise ValueError('explicit prior artifact changed: '+str(path))
    return data

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve()
    if not args.out.is_absolute() or out.exists() or any((p/'.git').exists() for p in (out,*out.parents)):
        parser.error('new absolute external output outside Git required')
    raw=(HERE/'composition-bce.json').read_bytes();fixed=json.loads(raw)
    if fixed['stage']!='BCE-static-plus-locals-one-fixed-codec' or fixed['API']!=API or fixed['repetitions']!=2:
        raise ValueError('fixed BCE comparison scope changed')
    if sha((HERE/'compose_bce.py').read_bytes())!=fixed['producer_sha256'] or set(fixed['cases'])!=set(NICE):
        raise ValueError('literal producer/case pins changed')
    ordinary={name:(HERE/name).read_bytes() for name in API}
    for name,data in ordinary.items():
        if sha(data)!=API[name]:raise ValueError('frozen API changed: '+name)
    reused={name:pinned(pin) for name,pin in fixed['receipts'].items()};gate=json.loads(reused['native_gate'])
    bootstrap_receipt=json.loads(reused['bootstrap_gate'])
    if not gate['complete'] or not bootstrap_receipt['complete']:raise ValueError('prior gate is not complete')
    for family,case in fixed['cases'].items():
        compiler=COMPILER[:]
        if family=='C':compiler.insert(6,'-mavx2')
        if case['nice_len']!=NICE[family] or case['compiler_argv']!=compiler:raise ValueError('fixed family compiler/nice changed')
        for name in ('source','bootstrap'):reused[family+'/'+name]=pinned(case[name])
        if not gate['families'][family]['full_native_equal'] or gate['families'][family]['source']!={k:case['source'][k] for k in ('bytes','sha256')}:
            raise ValueError('prior native source binding changed')
        observed=bootstrap_receipt['families'][family]
        if observed['compiler']!=compiler or observed['source']!={k:case['source'][k] for k in ('bytes','sha256')} or observed['bootstrap']!={k:case['bootstrap'][k] for k in ('bytes','sha256')}:
            raise ValueError('prior bootstrap source/argv binding changed')
    out.mkdir(parents=True);inputs=out/'inputs';inputs.mkdir();prior=out/'reused';prior.mkdir()
    for name,data in ordinary.items():
        target=inputs/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    for name in ('compose_bce.py','composition-bce.json'):(inputs/name).write_bytes((HERE/name).read_bytes())
    for name,data in reused.items():
        target=prior/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    report={'complete':False,'stage':fixed['stage'],'API':API,'prior_receipts':fixed['receipts'],'cases':{},
        'sourcegen':0,'preprocessing':0,'native_compiles':0,'engine_runs':0,'bootstrap_runs':0,
        'codec_compressions':0,'strict_pure_decodes':0,'prior_native_gate_referenced_not_reexecuted':True,
        'maintained_full_native_equality_claimed':False,'normal_or_runtime_acceptance':False}
    def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        codec=module('bce_frozen_codec',inputs/'build.py');decoder=module('bce_frozen_decoder',inputs/'decode.py')
        prefix=ordinary['launcher.sh'];old_prefix=ordinary['control-head/engines/compact/tiny-entry-b/launcher.sh']
        for family,case in fixed['cases'].items():
            directory=out/family;directory.mkdir();source=reused[family+'/source'];script=reused[family+'/bootstrap']
            row={'source':case['source'],'bootstrap':case['bootstrap'],'compiler_argv':case['compiler_argv'],
                 'source_class':'private static function names plus actual local names','nice_len':case['nice_len'],'attempts':[]}
            report['cases'][family]=row;report['codec_compressions']+=1;save()
            original=old_prefix+codec.encode(script,OLD);report['strict_pure_decodes']+=1
            proof=decoder.verify(original,old_prefix,source,case['compiler_argv'],script,expected_format='xz')
            original_dir=directory/'original-xz';original_dir.mkdir();(original_dir/'x').write_bytes(original)
            (original_dir/'decode-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
            row['original_xz']={'whole_bytes':len(original),'whole_sha256':sha(original),'fresh_encodes':1,'prefix_bytes':len(old_prefix)};first=None
            for index in (1,2):
                report['codec_compressions']+=1;save()
                whole=prefix+codec.encode(script,codec.SETTINGS,case['nice_len']);report['strict_pure_decodes']+=1
                proof=decoder.verify(whole,prefix,source,case['compiler_argv'],script,expected_format='alone')
                attempt=directory/('attempt-'+str(index));attempt.mkdir();(attempt/'x').write_bytes(whole);(attempt/'x').chmod(0o755)
                proof_raw=(json.dumps(proof,indent=2)+'\n').encode();(attempt/'decode-proof.json').write_bytes(proof_raw)
                row['attempts'].append({'attempt':index,'whole_bytes':len(whole),'whole_sha256':sha(whole),
                    'prefix_bytes':len(prefix),'payload_bytes':len(whole)-len(prefix),'decode_proof_sha256':sha(proof_raw)})
                if first is None:first=whole
                elif first!=whole:raise ValueError('two complete fixed codec bytes differ: '+family)
                save()
            (directory/'x').write_bytes(first);(directory/'x').chmod(0o755)
            row.update(whole_bytes=len(first),whole_sha256=sha(first),codec_saved_from_actual_original_xz=len(original)-len(first),
                actual_saved_from_maintained_whole=case['maintained_whole_bytes']-len(first),remaining_over4096=len(first)-4096,
                independent_complete_bytes_equal=True,strict_source_and_argv_recovery=True)
            save();print(json.dumps({'family':family,'original_xz':len(original),'fixed_alone':len(first),
                'codec_saved':len(original)-len(first),'whole_sha256':sha(first),'native_compiles':0,'engine_runs':0}),flush=True)
        report.update(complete=True,checksum_note='LZMA-alone has no container checksum; exact analysis recovery does not preserve XZ CRC64 corruption detection')
        save();print(json.dumps({'complete':True,'results_sha256':sha((out/'results.json').read_bytes()),'native_compiles':0,'engine_runs':0}),flush=True)
        return 0
    except BaseException as error:
        report.update(complete=False,error=repr(error))
        try:save()
        except BaseException:pass
        raise

if __name__=='__main__':raise SystemExit(main())
