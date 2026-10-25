#!/usr/bin/env python3
"""Reproduce the frozen B5851 shipping control twice, never execute it."""
import argparse
import json
from pathlib import Path
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import tools

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve()
    assert args.out.is_absolute() and not out.exists() and not any((p/'.git').exists() for p in (out,*out.parents))
    out.mkdir();frozen=out/'frozen';frozen.mkdir()
    manifest=json.loads((HERE/'baseline.json').read_bytes())
    report={'complete':False,'scope':__doc__,'source_files':{},'commands':tools.COMMANDS,'engine_executions':0,'candidate_compiles':0}
    def save():(out/'control.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
    save()
    try:
        for name,pin in manifest['control_files'].items():
            data=(HERE/'control'/name).read_bytes();assert len(data)==pin['bytes'] and tools.sha(data)==pin['sha256'],name
            dest=frozen/'control'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
            report['source_files']['control/'+name]={'bytes':len(data),'sha256':tools.sha(data)}
        for name in ('tools.py','build-control.py','baseline.json'):
            data=(HERE/name).read_bytes();(frozen/name).write_bytes(data)
            report['source_files'][name]={'bytes':len(data),'sha256':tools.sha(data)}
        command=[sys.executable,'-I','-B',str(frozen/'control/engines/compact/tiny-entry-b/build.py'),'--out',str(out/'control-cost')]
        result=tools.run(command,out)
        (out/'control.stdout').write_bytes(result.stdout);(out/'control.stderr').write_bytes(result.stderr)
        assert result.returncode==0,'baseline build failed'
        receipt=(out/'control-cost/build.json').read_bytes();build=json.loads(receipt)
        assert build['complete'] and len(build['attempts'])==2 and not build['diagnostic_exact_control']
        expected=manifest['expected']
        for row in build['attempts']:
            for key in ('source_bytes','source_sha256','native_bytes','native_sha256','whole_bytes','whole_sha256','bootstrap_sha256'):
                assert row[key]==expected[key],key
        report.update(complete=True,old_shipping_reproductions=2,old_DEV_reproductions=0,
            baseline_build_sha256=tools.sha(receipt),baseline_expected=expected,owned_live_handles=0)
        save();print(json.dumps({'complete':True,'out':str(out),'control_sha256':tools.sha((out/'control.json').read_bytes()),'whole_bytes':expected['whole_bytes']}))
    except BaseException as error:
        report['error']=repr(error);save();raise

if __name__=='__main__':main()
