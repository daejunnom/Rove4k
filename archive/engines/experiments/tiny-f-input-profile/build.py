"""One F shipping input profile: reuse pinned controls, compile/package once.

No C/Python AST, preprocessor, engine, control compile/copy, alias or codec search.
"""
import argparse
import hashlib
import importlib.util
import json
import lzma
import os
from pathlib import Path
import signal
import subprocess

PROFILE = 'f5a5a0bcaa1845c05c7189765cd4f81856a464532d406f5bc2a93287e531b894'
SEMANTICS = '48c17a5b4998727189b4f5279ca0e526f6f6cef0fe5ff14e5b0bd13ea2b5112d'
PINS = {
 'main.c':(9925,'3549063cbdca22c83536e0879b5e7baff8c7cbef3b5911f4152850732c86300c'),
 'bootstrap.py':(10924,'886ede212e35c83c5f030c18aa662c58fe54a0e62e64ce17fc6f79260dd07f6e'),
 'native/x':(22672,'9b4ca00fd54b67c33c01e92389c4f9130751233633faa828b6eb46e3b20890db'),
 'x':(4808,'93377e104d934d5bde1e8c7a491b54b72d0a7a6e9d40b845f94f86bc0c2f6956'),
}
CANONICAL = 'ec39b5641ac9fc5ab19a0c919c05e0d68169b461cc1d32afeee83274926becbd'
TEMPLATE = '84608782831299a6f7b1010dea89501eb10e6e34ee1cdc8f3804d448354cf4c6'
PREFIX = '78c5b572036e14ed33098fa4fb10fd10f4e061305e158f1609bae95d41e60301'
COMPILER = ['cc','-Os','-pthread','-x','c','-','-o','x','-s']
MARKER = b'__ROVE_SOURCE_LITERAL__'
COMMAND = b"subprocess.Popen('cc -Os -pthread -x c - -o x -s'.split(),"
HEADER = bytes.fromhex('0200000004ffffffffffffffff')

def sha(data):
    return hashlib.sha256(data).hexdigest()

def require(condition, message):
    if not condition:
        raise ValueError(message)

def raw_literal(source):
    require(b'\r' not in source and b'\0' not in source and b"'''" not in source
            and not source.endswith((b"'",b'\\')), 'fixed raw-single source admission differs')
    require(source.decode().encode() == source, 'UTF-8 restoration differs')
    return b"r'''" + source + b"'''.encode()"

def strict_decode(whole, prefix, template, source):
    require(len(prefix) == 77 and whole.startswith(prefix), 'fixed prefix differs')
    payload = whole[77:]
    require(payload[:13] == HEADER, 'ALONE header differs')
    expected = template.replace(MARKER, raw_literal(source))
    decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    decoded = decoder.decompress(payload, max_length=len(expected)+1)
    require(decoded == expected and decoder.eof and not decoder.unused_data
            and decoder.check == lzma.CHECK_NONE, 'strict single-stream restoration differs')
    # Exact admitted template controls all Python syntax; recover raw literal and
    # fixed literal argv directly, without Python AST, eval or bootstrap execution.
    before, after = template.split(MARKER)
    start, end = before+b"r'''", b"'''.encode()"+after
    require(decoded.startswith(start) and decoded.endswith(end), 'source literal framing differs')
    recovered = decoded[len(start):-len(end)]
    require(recovered == source and b"'''" not in recovered, 'compiler stdin recovery differs')
    require(decoded.count(COMMAND) == 1, 'literal Popen argv binding differs')
    recovered_argv = COMMAND.split(b"'")[1].decode('ascii').split()
    require(recovered_argv == COMPILER, 'compiler argv recovery differs')
    return decoded, {'source_sha256':sha(recovered), 'compiler':recovered_argv,
                     'exact_template':True, 'raw_literal_exact':True, 'stream_count':1,
                     'unused_bytes':0, 'Python_AST':False, 'bootstrap_executed':False}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',type=Path,required=True)
    parser.add_argument('--canonical',type=Path,required=True)
    parser.add_argument('--template',type=Path,required=True)
    parser.add_argument('--semantics',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args = parser.parse_args()
    require(os.name == 'posix' and all(p.is_absolute() for p in
            (args.baseline,args.canonical,args.template,args.semantics,args.out)), 'absolute Linux paths required')
    args.out.mkdir()
    report = {'complete':False, 'candidate_count':1, 'compiler_runs':0,
              'codec_compressions':0, 'control_compiles':0, 'control_copies':0,
              'AST_runs':0, 'engine_runs':0, 'games':0, 'benchmarks':0, 'inputs':{}}
    def save():
        (args.out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        # Preserve the actual ordinary producer, not copies of the old controls.
        producer = args.out/'producer'; producer.mkdir()
        for name in ('build.py','profile.py','.gitattributes'):
            raw = (Path(__file__).parent/name).read_bytes()
            (producer/name).write_bytes(raw)
            report['inputs'][name] = {'bytes':len(raw),'sha256':sha(raw)}
        require(report['inputs']['profile.py']['sha256'] == PROFILE, 'transformer differs')
        semantic_raw=args.semantics.read_bytes()
        require(sha(semantic_raw)==SEMANTICS,'normal EP source helper differs')
        (producer/'semantics.py').write_bytes(semantic_raw)
        report['inputs']['semantics.py']={'path':str(args.semantics),'sha256':sha(semantic_raw)}
        controls = {}
        for name, (size, digest) in PINS.items():
            path = args.baseline/name; raw = path.read_bytes()
            require((len(raw),sha(raw)) == (size,digest), 'baseline input differs: '+name)
            controls[name] = raw
            report['inputs'][name] = {'path':str(path),'bytes':size,'sha256':digest}
        canonical, template = args.canonical.read_bytes(), args.template.read_bytes()
        require(sha(canonical) == CANONICAL and sha(template) == TEMPLATE, 'ordinary control differs')
        require(template.count(MARKER) == 1, 'template marker differs')
        report['inputs']['canonical'] = {'path':str(args.canonical),'sha256':sha(canonical)}
        report['inputs']['template'] = {'path':str(args.template),'sha256':sha(template)}
        prefix = controls['x'][:77]
        require(sha(prefix) == PREFIX, 'prefix differs')
        script, report['control_decode'] = strict_decode(controls['x'],prefix,template,controls['main.c'])
        require(script == controls['bootstrap.py'], 'baseline bootstrap differs')
        spec = importlib.util.spec_from_file_location('fixed_existing_EP',producer/'semantics.py')
        semantics = importlib.util.module_from_spec(spec);spec.loader.exec_module(semantics)
        semantic_readable,report['existing_EP'] = semantics.transform_readable(canonical)
        spec = importlib.util.spec_from_file_location('fixed_input_profile',producer/'profile.py')
        transformer = importlib.util.module_from_spec(spec);spec.loader.exec_module(transformer)
        readable,candidate,report['transform'] = transformer.transform(semantic_readable,controls['main.c'])
        require(len(candidate)==9728 and sha(candidate)=='845f731a0f1fabd62bae629ad191aadd39525d0db7d59628224e315f09c0519d',
                'fixed candidate source differs')
        (args.out/'readable.c').write_bytes(readable)
        report['readable']={'bytes':len(readable),'sha256':sha(readable),
                            'semantic_control_sha256':sha(semantic_readable),'DEV_compiled':False}
        (args.out/'main.c').write_bytes(candidate)
        directory = args.out/'native';directory.mkdir()
        process = subprocess.Popen(COMPILER,cwd=directory,stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        report['compiler_runs'] = 1
        try:
            stdout, stderr = process.communicate(candidate,timeout=45)
        except BaseException:
            if process.poll() is None:
                os.killpg(process.pid,signal.SIGKILL)
            process.communicate()
            raise
        (directory/'compiler.stdout').write_bytes(stdout)
        (directory/'compiler.stderr').write_bytes(stderr)
        report['compiler'] = {'argv':COMPILER,'cwd':str(directory),'returncode':process.returncode,
                              'stdin_sha256':sha(candidate),'stdout_bytes':len(stdout),'stderr_bytes':len(stderr)}
        require(process.returncode == 0, 'candidate compiler failed')
        native = (directory/'x').read_bytes()
        report['native'] = {'bytes':len(native),'sha256':sha(native),
                            'old_full_identity':native == controls['native/x']}
        script = template.replace(MARKER,raw_literal(candidate))
        payload = lzma.compress(script,format=lzma.FORMAT_ALONE,check=lzma.CHECK_NONE,
            filters=[{'id':lzma.FILTER_LZMA1,'preset':9|lzma.PRESET_EXTREME,'lc':2,'lp':0,'pb':0,
                      'mf':lzma.MF_BT4,'dict_size':67108864,'nice_len':32}])
        report['codec_compressions'] = 1
        whole = prefix+payload
        restored, report['candidate_decode'] = strict_decode(whole,prefix,template,candidate)
        require(restored == script, 'candidate script differs')
        (args.out/'bootstrap.py').write_bytes(script);(args.out/'x').write_bytes(whole)
        report.update(complete=True, source={'bytes':len(candidate),'sha256':sha(candidate)},
                      bootstrap={'bytes':len(script),'sha256':sha(script)},
                      whole={'bytes':len(whole),'sha256':sha(whole),'prefix_bytes':77,
                             'payload_bytes':len(payload),'delta_from_4808':len(whole)-4808},
                      runtime_qualified=False, native_identity_required_for_cost=False,
                      codec='unchanged F LZMA1/ALONE preset9extreme lc2 lp0 pb0 BT4 nice32; no container checksum',
                      live_compiler_handles=0)
    except BaseException as error:
        report['error'] = {'type':type(error).__name__,'message':str(error)}
        raise
    finally:
        save()
    print(json.dumps({'source':report['source'],'native':report['native'],'whole':report['whole']}))

if __name__ == '__main__':
    main()
