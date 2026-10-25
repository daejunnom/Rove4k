"""Existing positive stdout-publication observer, with only parent cleanup and fixed GO input changes.

No old main/EXPECTED admission is used. No target writes, extra signals,
ptrace/personality/register changes, stub search or compiler are introduced.
"""
import fcntl
import hashlib
import os
from pathlib import Path
import select
import signal
import struct
import subprocess
import time
import json

def sha(data):return hashlib.sha256(data).hexdigest()
def need(value,message):
    if not value:raise AssertionError(message)
def absent_group(pid):
    try:os.killpg(pid,0);return False
    except ProcessLookupError:return True
def tids(pid):return sorted(int(p.name) for p in Path(f'/proc/{pid}/task').iterdir())
def syscall(pid,tid):
    raw=Path(f'/proc/{pid}/task/{tid}/syscall').read_text().strip()
    if raw in ('running','-1'):return None
    fields=raw.split()
    return {'number':int(fields[0]),'args':[int(v,0) for v in fields[1:7]],'raw':raw}
def physical(pid,fixed):
    rows=[]
    for line in Path(f'/proc/{pid}/maps').read_text().splitlines():
        span,permission,*_=line.split();start,end=(int(v,16) for v in span.split('-'))
        need(not ('w' in permission and 'x' in permission),'writable executable mapping')
        if '[stack]' in line:need('x' not in permission,'executable main stack')
        rows.append((start,end,permission[:3],line))
    def covers(start,size,permission):
        end=start+size
        for a,b,p,_ in rows:
            if b<=start:continue
            if a>start:break
            need(p==permission,'mapping permission')
            start=min(end,b)
            if start==end:return
        raise AssertionError('mapping range absent')
    covers(4190208,4096,'---');covers(4194304,fixed['image_pages'],'r-x')
    covers(fixed['bss_base'],176128,'rw-');covers(fixed['upper_guard'],4096,'---')
    with open(f'/proc/{pid}/mem','rb',buffering=0) as mem:
        image=os.pread(mem.fileno(),fixed['native_bytes'],4194304)
        padding=os.pread(mem.fileno(),fixed['image_pages']-fixed['native_bytes'],4194304+fixed['native_bytes'])
    need(sha(image)==fixed['native_sha256'] and not any(padding),'restored native/padding differs')
    return {'native_sha256':sha(image),'RX_and_BSS_permissions':True,'guards':True,'no_WX':True,
            'RX_padding_zero':True,'initial_BSS_zero_observed':False,'maps':[r[3] for r in rows]}

def case(item,fixed,oracle,out,first_go):
    selected=item['whole_repeats'][0]
    for row in item['whole_repeats']:
        need(len(Path(row['path']).read_bytes())==fixed['whole_bytes'] and sha(Path(row['path']).read_bytes())==fixed['whole_sha256'],'whole identity')
        need(len(Path(row['native_path']).read_bytes())==fixed['native_bytes'] and sha(Path(row['native_path']).read_bytes())==fixed['native_sha256'],'native identity')
        need(row['checkpoint'] is False and row['definitions']['CHECKPOINT']==0,'shipping only')
        need(row['definitions']['IMAGE_ENTRY']==fixed['entry'],'entry identity')
    readfd,writefd=os.pipe()
    process=None;forced=False;stdout=bytearray();buffer=bytearray();report={'complete':False,'id':item['id'],'forced_cleanup':False}
    started=time.monotonic();deadline=started+15
    def left(cap=3):
        value=min(cap,deadline-time.monotonic())
        need(value>0,'aggregate publication deadline')
        return value
    def send(data):
        need(process.poll() is None,'target exited before input')
        need(os.write(process.stdin.fileno(),data)==len(data),'short stdin write')
    def receive():
        ready,_,_=select.select([readfd],[],[],left())
        need(ready,'stdout deadline')
        data=os.read(readfd,65536)
        need(data,'unexpected stdout EOF')
        stdout.extend(data);buffer.extend(data)
    def line():
        while b'\n' not in buffer:receive()
        end=buffer.index(10)+1;raw=bytes(buffer[:end]);del buffer[:end]
        return raw
    try:
        need(first_go in (b'go\n',b'go wtime 0 btime 0\n'),'fixed first GO mode')
        creation_mask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGTERM})
        try:
            process=subprocess.Popen([selected['path']],stdin=subprocess.PIPE,stdout=writefd,stderr=subprocess.PIPE,
                start_new_session=True,bufsize=0,
                preexec_fn=lambda:signal.pthread_sigmask(signal.SIG_SETMASK,creation_mask))
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK,creation_mask)
        report['pid']=process.pid
        send(b'uci\nisready\n')
        need(line()==b'uciok\n' and line()==b'readyok\n' and not buffer,'minimal initialization differs')
        original_tids=tids(process.pid);need(len(original_tids)==3,'startup TIDs')
        need(sha(Path(f'/proc/{process.pid}/exe').read_bytes())==fixed['whole_sha256'],'own-loader identity')
        report['physical']=physical(process.pid,fixed)
        report['initial_tids']=original_tids
        report['file_descriptors']=sorted(int(p.name) for p in Path(f'/proc/{process.pid}/fd').iterdir())
        need(report['file_descriptors']==[0,1,2],'unexpected target descriptors')
        # Keep the parent's duplicate writer blocking. Nonblocking status on
        # that open file description would also alter the engine's stdout.
        capacity=fcntl.fcntl(writefd,fcntl.F_GETPIPE_SZ)
        need(0<capacity<=1048576,'bounded pipe capacity')
        need(os.write(writefd,b'X'*capacity)==capacity,'filler did not fill empty stdout pipe')
        report['GO_inputs']=[first_go.decode().strip(),'go wtime 0 btime 0']
        send(first_go+b'position startpos moves e2e4\ngo wtime 0 btime 0\n')
        gate=None;gate_deadline=time.monotonic()+left()
        while time.monotonic()<gate_deadline:
            need(process.poll() is None,'target exited under backpressure')
            current=tids(process.pid);need(current==original_tids,'startup TIDs replaced')
            main=syscall(process.pid,process.pid)
            writers=[]
            for tid in current:
                if tid==process.pid:continue
                call=syscall(process.pid,tid)
                if call and call['number']==1 and call['args'][0]==1:writers.append((tid,call))
            if main and main['number']==202 and main['args'][1]==128 and main['args'][2] in (1,2,3) and len(writers)==1:
                address=main['args'][0]
                need(fixed['bss_base']<=address<=fixed['bss_base']+175092-4,'pending address outside BSS')
                with open(f'/proc/{process.pid}/mem','rb',buffering=0) as mem:
                    count=struct.unpack('<i',os.pread(mem.fileno(),4,address))[0]
                    writer_tid,write_call=writers[0];length=write_call['args'][2]
                    need(0<length<=64,'bounded bestmove write')
                    reply=os.pread(mem.fileno(),length,write_call['args'][1])
                if count==1:
                    need(reply.startswith(b'bestmove ') and reply.endswith(b'\n'),'blocked write is not result')
                    gate={'pending_address':address,'pending_value':count,'main_futex':main,'result_writer_tid':writer_tid,
                          'result_write':write_call,'blocked_reply':reply.decode(),'TIDs':current}
                    break
            time.sleep(.002)
        need(gate is not None,'main/result pending1 gate not observed')
        report['publication_gate']=gate
        # Remove only our filler. Output begins afterwards, without target
        # memory writes, register changes, extra signals or patched code.
        remaining=capacity
        while remaining:
            ready,_,_=select.select([readfd],[],[],left());need(ready,'filler drain deadline')
            data=os.read(readfd,remaining);need(data and data==b'X'*len(data),'filler bytes differ')
            remaining-=len(data)
        white=oracle.Board.from_fen();black=white.play('e2e4');moves=[]
        for board in (white,black):
            raw=line();parts=raw.decode().strip().split()
            need(len(parts)==2 and parts[0]=='bestmove' and parts[1] in {str(m) for m in board.legal_moves()},'ordered result is not legal on expected root')
            moves.append(parts[1])
        need(not buffer,'extra output after two epochs')
        zero_deadline=time.monotonic()+left()
        while time.monotonic()<zero_deadline:
            with open(f'/proc/{process.pid}/mem','rb',buffering=0) as mem:
                count=struct.unpack('<i',os.pread(mem.fileno(),4,gate['pending_address']))[0]
            if count==0:break
            time.sleep(.002)
        need(count==0,'completion did not release zero')
        need(tids(process.pid)==original_tids,'TIDs replaced after second epoch')
        send(b'quit\n');process.wait(timeout=left())
        os.close(writefd);writefd=None
        _,stderr=process.communicate(timeout=left())
        tail=os.read(readfd,65536)
        need(tail==b'' and process.returncode==0 and not stderr,'exit/output differs')
        need(not Path(f'/proc/{process.pid}').exists() and absent_group(process.pid),'process/group remains')
        report.update(complete=True,GO_epochs=2,legal_ordered_results=moves,pending_zero_observed=True,
                      filler_bytes=capacity,returncode=0,stdout=stdout.decode(),stderr='',physical_exit=True,
                      root_fence_scope='main observed blocked in the actual pending wait while old result write blocked; old/new-root results legal',
                      cancellation_causality='unproven',target_memory_or_register_writes=0)
    except BaseException as error:
        report['complete']=False
        report['error']={'type':type(error).__name__,'message':str(error)}
        raise
    finally:
        cleanup_mask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGTERM})
        try:
            if process is not None:
                try:os.killpg(process.pid,signal.SIGKILL);forced=True
                except ProcessLookupError:pass
            if writefd is not None:os.close(writefd)
            if process is not None:
                try:process.communicate(timeout=3)
                except BaseException as error:report['cleanup_error']=repr(error)
            os.close(readfd)
            report['forced_cleanup']=forced
            if forced or report.get('cleanup_error'):report['complete']=False
            (out/(item['id']+'.json')).write_text(json.dumps(report,indent=2)+'\n')
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK,cleanup_mask)
    return report
