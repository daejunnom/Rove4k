"""Qualify only the measured best Rust stream as an actual Linux process.

A transparent rustc PATH shim records its exact stdin and a whitelist of public
compile inputs, then execs the real Rust compiler with those same bytes. The
artifact is unchanged. This separately binds the selected stream to its stdin
image; it never assigns the four-file baseline's native hash to that image.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[3]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def load_oracle():
    spec=importlib.util.spec_from_file_location("r4_single_stream_oracle",ROOT/"engines/tests/chess_oracle.py")
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    return module


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--rustc",default=os.environ.get("RUSTC","rustc"))
    parser.add_argument("--process-suite",action="store_true",help="also run the independent full shipping suite; omit when its owner runs that separately")
    args=parser.parse_args();out=args.out.resolve()
    if out==ROOT or ROOT in out.parents:parser.error("external output required")
    if sys.platform!="linux":parser.error("Linux /proc verification required")
    rustc=shutil.which(args.rustc)
    if rustc is None:parser.error("actual Rust compiler required")
    out.mkdir(parents=True,exist_ok=False)
    build_path=args.build.resolve();build=json.loads(build_path.read_text())
    artifact=Path(build['selected']['path']);source=build_path.parent/'merged.stdin.rs'
    assert sha(artifact.read_bytes())==build['selected']['sha256']
    assert sha(source.read_bytes())==build['merged_source_sha256']
    assert build['selected']['source_sha256']==build['merged_source_sha256']
    assert build['stdin_native']['source_sha256']==build['merged_source_sha256']
    if build.get('resources',{}).get('enabled'):
        assert build['resources']['input_sha256']==build['pre_resource_source_sha256']
        assert build['resources']['output_sha256']==build['merged_source_sha256']
        assert sha((build_path.parent/'pre-resource.stdin.rs').read_bytes())==build['pre_resource_source_sha256']
    compiler_keys=tuple(build['compiler_environment'])
    five_keys=('ROVE_WORKERS','ROVE_TT_BITS','SOURCE_DATE_EPOCH','LC_ALL','TZ')
    if build.get('resource_environment_overrides_omitted',False):
        assert set(compiler_keys)==set(five_keys[2:]) and build.get('resources',{}).get('enabled')
        assert source.stat().st_size==22981 and build['merged_source_sha256']=='516aab3e2f9085dd4a95503cc4ebc1a02670034a0a2daee8350081957f056e0b'
    else:
        assert set(compiler_keys)==set(five_keys)
    expected_native=build['stdin_native']['sha256']
    assert sha(Path(build['stdin_native']['path']).read_bytes())==expected_native
    captures=out/'compiler-captures';captures.mkdir();capture_bin=out/'capture-bin';capture_bin.mkdir()
    shim=capture_bin/'rustc'
    shim.write_text('#!'+sys.executable+'\n'+
      "import hashlib,json,os,sys,tempfile\nfrom pathlib import Path\n"
      "data=sys.stdin.buffer.read();pid=os.getpid()\n"
      f"base=Path({str(captures)!r})\n"
      "(base/(str(pid)+'.stdin')).write_bytes(data)\n"
      "record={'pid':pid,'group':os.getpgrp(),'argv':sys.argv,'cwd':os.getcwd(),'TMPDIR':os.environ['TMPDIR'],'mode':os.stat(os.getcwd()).st_mode&511,'source_sha256':hashlib.sha256(data).hexdigest(),'source_bytes':len(data),'environment':{key:os.environ.get(key) for key in " + repr(compiler_keys) + "},'stdin_seekable':sys.stdin.buffer.seekable()}\n"
      "(base/(str(pid)+'.json')).write_text(json.dumps(record))\n"
      "input_file=tempfile.TemporaryFile();input_file.write(data);input_file.seek(0);os.dup2(input_file.fileno(),0)\n"
      f"os.execv({str(rustc)!r},[{str(rustc)!r},*sys.argv[1:]])\n",encoding='utf-8')
    shim.chmod(0o755)
    scratch=out/'scratch';scratch.mkdir()
    controlled=build['target_compiler_scope']['controlled_verification_PATH']
    env=dict(os.environ,PATH=str(capture_bin)+os.pathsep+controlled,TMPDIR=str(scratch),ROVE_WORKERS='999',ROVE_TT_BITS='7')
    transcript=[];events=queue.Queue()
    report={'passed':False,'build_json_sha256':sha(build_path.read_bytes()),'artifact_sha256':sha(artifact.read_bytes()),
            'merged_source_sha256':sha(source.read_bytes()),'expected_stdin_native_sha256':expected_native,
            'scope':'selected actual stream; source stdin and live native image; in-process chess oracle for two legal moves',
            'compiler_resolution':'transparent observing PATH shim then exec real compiler; artifact bytes unchanged'}
    process=None
    try:
        process=subprocess.Popen([str(artifact)],cwd=artifact.parent,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
        proc=Path('/proc')/str(process.pid)
        started=proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]
        def reader(pipe,stream):
            for line in pipe:events.put((stream,line.rstrip('\r\n'),time.monotonic()))
            events.put((stream,None,time.monotonic()))
        threads=[threading.Thread(target=reader,args=(process.stdout,'stdout'),daemon=True),threading.Thread(target=reader,args=(process.stderr,'stderr'),daemon=True)]
        for thread in threads:thread.start()
        def send(text):
            transcript.append({'at':time.monotonic(),'stream':'stdin','line':text});process.stdin.write(text+'\n');process.stdin.flush()
        received_bytes=0
        def receive(prefix,timeout):
            nonlocal received_bytes
            deadline=time.monotonic()+timeout
            while True:
                remaining=deadline-time.monotonic()
                assert remaining>0,f'no {prefix} within bounded deadline'
                try:stream,line,instant=events.get(timeout=remaining)
                except queue.Empty:raise AssertionError(f'no {prefix} within bounded deadline') from None
                transcript.append({'at':instant,'stream':stream,'line':line})
                if line is not None:received_bytes+=len(line.encode())
                assert received_bytes<=8*1024*1024,'combined output limit exceeded'
                if stream=='stdout' and line is None:raise AssertionError('stdout EOF before response')
                if stream=='stdout' and line.startswith(prefix):return line
        report['uci_queued_before_compiler_capture']=not list(captures.glob('*.json'))
        send('uci');send('isready')
        receive('uciok',60);receive('readyok',8)
        ids=sorted(p.name for p in (proc/'task').iterdir())
        assert len(ids)==build['startup_threads']
        live=(proc/'exe').read_bytes();assert sha(live)==expected_native,'live stream image differs from independent stdin compile'
        assert os.readlink(proc/'exe').endswith('/x (deleted)')
        status=dict(line.split(':',1) for line in (proc/'status').read_text().splitlines())
        assert int(status['PPid'])==os.getpid() and proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==started
        observed=list(captures.glob('*.json'));assert len(observed)==1
        compiler=json.loads(observed[0].read_text())
        assert compiler['source_sha256']==build['merged_source_sha256'] and compiler['source_bytes']==source.stat().st_size
        assert (captures/(str(compiler['pid'])+'.stdin')).read_bytes()==source.read_bytes()
        assert compiler['environment']==build['compiler_environment']
        if build.get('wrapper_policy')=='prepared-W1-W2-seek':assert compiler['stdin_seekable']
        assert compiler['argv'][1:]==build['runtime_compiler_command'][1:]
        assert compiler['cwd']==compiler['TMPDIR'] and Path(compiler['TMPDIR']).parent==scratch and compiler['mode']==0o700
        assert not Path(compiler['TMPDIR']).exists() and not list(scratch.iterdir())
        for task in ids:assert not (proc/'task'/task/'children').read_text().strip()
        oracle=load_oracle();board=oracle.Board.from_fen()
        send('position startpos');send('go wtime 0 btime 300000')
        white=receive('bestmove ',8).split()[1]
        assert white in {str(m) for m in board.legal_moves()}
        board=board.play('e2e4');send('position startpos moves e2e4');send('go wtime 300000 btime malformed')
        black=receive('bestmove ',8).split()[1]
        assert black in {str(m) for m in board.legal_moves()}
        assert sorted(p.name for p in (proc/'task').iterdir())==ids
        send('quit');assert process.wait(timeout=5)==0
        report['live_image']={'pid':process.pid,'process_starttime':started,'sha256':sha(live),'startup_thread_ids':ids,'compiler':compiler,'white':white,'black':black,'returncode':process.returncode}
        if args.process_suite:
            manifest={'engines':[{'id':'tiny-rust-stream-selected','command':[str(artifact)],'cwd':str(artifact.parent),'profile':'shipping','workers':build['workers'],'startup_threads':build['startup_threads'],'max_threads':build['startup_threads'],'startup_timeout':60,'expected_program_sha256':build['selected']['sha256']}]}
            save(out/'manifest.json',manifest)
            command=[sys.executable,'-B',str(ROOT/'engines/tests/verify.py'),'--manifest',str(out/'manifest.json'),'--suite','shipping','--out',str(out/'shipping'),'--plies','12']
            checks=subprocess.run(command,env=env,capture_output=True,text=True,timeout=300)
            save(out/'shipping-run.json',{'command':command,'returncode':checks.returncode,'stdout':checks.stdout,'stderr':checks.stderr})
            assert checks.returncode==0,checks.stdout+checks.stderr
            assert json.loads((out/'shipping/results.json').read_text())['passed']
        # Each invocation independently produced and consumed its exact source.
        for path in captures.glob('*.json'):
            capture=json.loads(path.read_text());assert capture['source_sha256']==build['merged_source_sha256']
            assert capture['environment']==build['compiler_environment'];assert not Path(capture['TMPDIR']).exists()
        assert not list(scratch.iterdir())
        report['compiler_invocations']=len(list(captures.glob('*.json')))
        report['shipping_results']=str(out/'shipping/results.json') if args.process_suite else 'not run here; separate owning validation track'
        report['passed']=True
    except Exception as error:
        report['error']=f'{type(error).__name__}: {error}';raise
    finally:
        if process is not None:
            if process.poll() is None:process.kill();process.wait(timeout=3)
            for pipe in (process.stdin,process.stdout,process.stderr):
                if pipe is not None and not pipe.closed:pipe.close()
        report['transcript']=transcript;save(out/'report.json',report)
    print(out/'report.json')


if __name__=='__main__':main()
