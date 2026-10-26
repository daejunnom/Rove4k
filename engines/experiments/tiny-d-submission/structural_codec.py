"""Finite whole-ELF XZ comparisons; native bytes and CRC64 are preserved."""
import lzma
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import time


def settings():
    """75 bounded literal/position alternatives, then explicit match variants."""
    return [dict(lc=lc, lp=lp, pb=pb, mf=lzma.MF_BT4, nice_len=273, depth=0)
            for lc in range(5) for lp in range(5-lc) for pb in range(5)]


def encode(native, config):
    if type(native) is not bytes or not 64<=len(native)<=262144:
        raise ValueError('bounded complete native image required')
    if set(config)!={'lc','lp','pb','mf','nice_len','depth'}:
        raise ValueError('explicit finite LZMA configuration required')
    if not (0<=config['lc']<=4 and 0<=config['lp']<=4 and
            config['lc']+config['lp']<=4 and 0<=config['pb']<=4 and
            config['mf'] in (lzma.MF_HC3,lzma.MF_HC4,lzma.MF_BT2,lzma.MF_BT3,lzma.MF_BT4) and
            config['nice_len'] in (32,64,128,273) and config['depth'] in (0,64,512,4096)):
        raise ValueError('configuration is outside the finite portfolio')
    dictionary=max(8192,1<<(len(native)-1).bit_length())
    payload=lzma.compress(native,format=lzma.FORMAT_XZ,check=lzma.CHECK_CRC64,
        filters=[{'id':lzma.FILTER_X86},{'id':lzma.FILTER_LZMA2,
            'preset':9|lzma.PRESET_EXTREME,'dict_size':dictionary,**config}])
    if lzma.decompress(payload)!=native:
        raise ValueError('complete ELF inverse differs')
    return payload


def package(native,config,packaging,*,unnamed=False):
    code=packaging.NATIVE_CODE
    if unnamed:
        before='os.memfd_create("Rove4k-D",1)'
        if code.count(before)!=1:raise ValueError('memfd diagnostic-name boundary differs')
        code=code.replace(before,'os.memfd_create("",1)',1)
    payload=encode(native,config)
    whole,header=packaging.envelope(code,payload)
    return whole,dict(header_bytes=len(header),payload_bytes=len(payload),
        codec='xz-bcj',check='CRC64',config=dict(config),unnamed_memfd=unnamed,
        dict_size=max(8192,1<<(len(native)-1).bit_length()),
        native_argv0='Rove4k-D',environment_preserved=True,descriptor_close_on_exec=True,
        complete_native_restored=True)


def compare(case,out):
    """Measure 155 alternatives with a soft 60-second between-encode budget.

    Compression runs in this process; callers must supply an external hard
    wall limit because a running encode is not interrupted by this clock check.
    """
    path=Path(__file__).with_name('structural_size.py')
    spec=importlib.util.spec_from_file_location('codec_cost_tools',path)
    h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
    case,out=Path(case),h.new_output(out)
    native=(case/'native/native').read_bytes()
    receipt=(case/'result.json').read_bytes()
    source=json.loads(receipt)
    h.require_settled_cost(source)
    if h.pin(native)!=source['native_runs'][0]['native']:
        raise ValueError('complete measured native required')
    out.mkdir(parents=True)
    packaging=h.modules()['packaging']
    report={'complete':False,'source_cost':h.pin(receipt),
        'native':h.pin(native),'rows':[],'engine_executed':False,'runtime_qualified':False,
        # This portfolio executes only in-process encodes and owns no commands.
        'command_owner':None,
        'host_cleanup':{'unsettled_commands':0,'errors':[]},
        'selected':False,'tools':{str(Path(p).name):h.pin(Path(p).read_bytes())
                                for p in (__file__,path,packaging.__file__)}}
    def save():(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    began=time.monotonic()
    configs=settings()
    body_error=None
    try:
        for phase in range(2):
            for config in configs:
                if time.monotonic()-began>60:raise TimeoutError('finite codec portfolio budget')
                at=time.monotonic();whole,detail=package(native,config,packaging)
                row={**h.pin(whole),**detail,'encode_seconds':time.monotonic()-at}
                report['rows'].append(row)
                if 'best' not in report or row['bytes']<report['best']['bytes']:
                    report['best']=row;(out/'best').write_bytes(whole)
            best=report['best']['config']
            configs=[{**best,'mf':mf,'nice_len':nice,'depth':depth}
                     for mf in (lzma.MF_HC3,lzma.MF_HC4,lzma.MF_BT2,lzma.MF_BT3,lzma.MF_BT4)
                     for nice in (32,64,128,273) for depth in (0,64,512,4096)]
            save()
        whole,detail=package(native,report['best']['config'],packaging,unnamed=True)
        (out/'best-unnamed').write_bytes(whole)
        report['unnamed']={**h.pin(whole),**detail}
    except BaseException as error:
        body_error=error
        report['failure']={'type':type(error).__name__,'message':str(error)}
        raise
    finally:
        report['seconds']=time.monotonic()-began
        h.finish_report(None,report,save,body_error)
    return report


if __name__=='__main__':
    sys.dont_write_bytecode=True
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    result=compare(args.case,args.out)
    print(json.dumps({k:result[k] for k in ('complete','native','best','unnamed','seconds')}))
