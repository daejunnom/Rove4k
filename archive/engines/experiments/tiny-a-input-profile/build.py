"""One exact prepared A input-profile cost; compile once and package once.

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

PROFILE = '2ac763843ac3098f989860464ee053cb41197cc0c888a318694346319c82d15c'
RECIPE = 'eacdc4d5e30728094ac41ba1b7c8d206d23c32d5a8c71b0748f29351fc76d95b'
PREPARE = '4e85117645aaed7a201c342fd574025a33c8ba113bd5814a55c17628f8bbe9bc'
PINS = {
 'main.c':(9910,'a3414baa5034a62067f74f7f8fff9a1578827f37e6ca59b0db8e5bc1968df312'),
 'bootstrap.py':(10900,'d73d24f699811253492ad8bab152907835763a68d7a35962e83d14156840cb47'),
 'native/x':(22672,'84ce7fd107783474af8f39aeec7b95c244d475ab797eefd2627b9741b265210a'),
 'x':(4846,'1227e4ba99a986d52a33f6b901f3be117d1b522001f2f86f6da07e4c27a74c9d'),
}
CANONICAL = '71f9ff6ce1b7f555ad85c3bf49766381c0627315da94acf0c49eeee7bee4a734'
TEMPLATE = '898bf1f24168f6e99a7ffb9b0ba9e805af0c7627ea115d47ac687c1389d015ba'
PREFIX = '78c5b572036e14ed33098fa4fb10fd10f4e061305e158f1609bae95d41e60301'
COMPILER = ['cc','-Os','-x','c','-','-o','x','-s']
MARKER = b'__ROVE_SOURCE_LITERAL__'
COMMAND = b"subprocess.Popen('cc -Os -x c - -o x -s'.split(),"
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
    parser.add_argument('--prepared',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args = parser.parse_args()
    require(os.name == 'posix' and all(p.is_absolute() for p in
            (args.baseline,args.canonical,args.template,args.prepared,args.out)), 'absolute Linux paths required')
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
        for name in ('build.py','profile.py','prepare.py','recipe.json','.gitattributes'):
            raw = (Path(__file__).parent/name).read_bytes()
            (producer/name).write_bytes(raw)
            report['inputs'][name] = {'bytes':len(raw),'sha256':sha(raw)}
        require(report['inputs']['profile.py']['sha256'] == PROFILE, 'transformer differs')
        require(report['inputs']['recipe.json']['sha256'] == RECIPE, 'prepared recipe differs')
        require(report['inputs']['prepare.py']['sha256'] == PREPARE, 'pure preparer differs')
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
        spec = importlib.util.spec_from_file_location('fixed_A_input_profile',producer/'profile.py')
        transformer = importlib.util.module_from_spec(spec);spec.loader.exec_module(transformer)
        readable,candidate,report['transform'] = transformer.transform(canonical,controls['main.c'])
        require(len(candidate)==9713 and sha(candidate)=='1f4097d43c5f6e84d7cbd17906100354da25be205d44ca08fbf52732e63b624c',
                'fixed prepared source differs')
        require(len(readable)==27687 and sha(readable)=='63821a63cbf6507393e0617da9f611b778ada46c9a89b49fdefc8996bb461e2c',
                'fixed prepared readable differs')
        require(candidate==(args.prepared/'main.c').read_bytes() and
                readable==(args.prepared/'readable.c').read_bytes(), 'prepared output bytes differ')
        report['prepared_byte_reproduction']={'main.c':True,'readable.c':True,'path':str(args.prepared)}
        (args.out/'readable.c').write_bytes(readable)
        report['readable']={'bytes':len(readable),'sha256':sha(readable),'DEV_compiled':False}
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
            filters=[{'id':lzma.FILTER_LZMA1,'preset':9|lzma.PRESET_EXTREME,'lc':2,'lp':0,'pb':0}])
        report['codec_compressions'] = 1
        whole = prefix+payload
        restored, report['candidate_decode'] = strict_decode(whole,prefix,template,candidate)
        require(restored == script, 'candidate script differs')
        (args.out/'bootstrap.py').write_bytes(script);(args.out/'x').write_bytes(whole)
        report.update(complete=True, source={'bytes':len(candidate),'sha256':sha(candidate)},
                      bootstrap={'bytes':len(script),'sha256':sha(script)},
                      whole={'bytes':len(whole),'sha256':sha(whole),'prefix_bytes':77,
                             'payload_bytes':len(payload),'delta_from_4846':len(whole)-4846},
                      runtime_qualified=False, native_identity_required_for_cost=False,
                      codec='unchanged A LZMA1/ALONE preset9extreme lc2 lp0 pb0; no container checksum',
                      live_compiler_handles=0)
    except BaseException as error:
        report['error'] = {'type':type(error).__name__,'message':str(error)}
        raise
    finally:
        save()
    print(json.dumps({'source':report['source'],'native':report['native'],'whole':report['whole']}))

if __name__ == '__main__':
    main()
