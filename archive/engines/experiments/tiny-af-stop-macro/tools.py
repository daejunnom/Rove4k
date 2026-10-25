"""Bounded owned compiler/PP/codec tool runner; never launches engines."""
import hashlib
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

def sha(data):return hashlib.sha256(data).hexdigest()
def need(v,m):
    if not v:raise ValueError(m)
def absent(pid):
    try:os.killpg(pid,0);return False
    except ProcessLookupError:return True

def create(out,report,save,deadline):
    RAW=set()
    def run(command,directory,input_data=None,timeout=180):
        directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
        row={'command':command,'pid':None,'returncode':None,'forced_cleanup':False,'cleanup_errors':[]}
        report['commands'].append(row);index=len(report['commands']);remaining=min(timeout,deadline-time.monotonic())
        need(remaining>0,'aggregate build deadline')
        mask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGTERM,signal.SIGINT})
        try:
            p=subprocess.Popen(command,cwd=directory,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                start_new_session=True,preexec_fn=lambda:signal.pthread_sigmask(signal.SIG_SETMASK,mask),
                env={**os.environ,'LC_ALL':'C','TZ':'UTC','SOURCE_DATE_EPOCH':'0'})
            RAW.add(p);row['pid']=p.pid
        finally:signal.pthread_sigmask(signal.SIG_SETMASK,mask)
        stdout=stderr=b'';failure=None;drained=False
        try:
            stdout,stderr=p.communicate(input_data,timeout=remaining);drained=True
            row.update(returncode=p.returncode,input_bytes=len(input_data)if input_data is not None else 0,
                       input_sha256=sha(input_data)if input_data is not None else None)
            need(p.returncode==0,'tool failed; see external logs')
        except BaseException as error:
            failure=sys.exc_info();row['tool_error']={'type':type(error).__name__,'message':str(error)}
            stdout=getattr(error,'output',None)or stdout;stderr=getattr(error,'stderr',None)or stderr
        finally:
            if p.poll()is None or not absent(p.pid):
                try:os.killpg(p.pid,signal.SIGKILL);row['forced_cleanup']=True
                except ProcessLookupError:pass
                except BaseException as error:row['cleanup_errors'].append({'action':'kill','error':repr(error)})
            if not drained:
                try:stdout,stderr=p.communicate(timeout=3);drained=True
                except BaseException as error:
                    row['cleanup_errors'].append({'action':'drain','error':repr(error)})
                    stdout=getattr(error,'output',None)or stdout;stderr=getattr(error,'stderr',None)or stderr
            logs=out/'tool-logs';logs.mkdir(exist_ok=True)
            (logs/(str(index)+'.stdout.bin')).write_bytes(stdout);(logs/(str(index)+'.stderr.bin')).write_bytes(stderr)
            row.update(returncode=p.returncode,group_absent=absent(p.pid),terminal=p.returncode is not None,
                       pipes_drained=drained,stdout_sha256=sha(stdout),stderr_sha256=sha(stderr))
            if row['group_absent']and row['terminal']and drained:RAW.discard(p)
            save()
        # Preserve the original operation failure; cleanup status never overwrites it.
        if failure is not None:raise failure[1].with_traceback(failure[2])
        need(row['group_absent']and row['terminal']and drained and not row['forced_cleanup']and not row['cleanup_errors'],
             'tool cleanup intervention or incomplete settlement; see command receipt')
        return subprocess.CompletedProcess(command,p.returncode,stdout,stderr)
    def cleanup():
        report['outer_cleanup']=[]
        for p in list(RAW):
            report['complete']=False;cleanup={'pid':p.pid,'errors':[]};stdout=stderr=b'';drained=False
            try:os.killpg(p.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            except BaseException as error:cleanup['errors'].append({'action':'kill','error':repr(error)})
            try:stdout,stderr=p.communicate(timeout=3);drained=True
            except BaseException as error:
                cleanup['errors'].append({'action':'drain','error':repr(error)})
                stdout=getattr(error,'output',None)or b'';stderr=getattr(error,'stderr',None)or b''
            logs=out/'tool-logs';logs.mkdir(exist_ok=True)
            (logs/('outer-'+str(p.pid)+'.stdout.bin')).write_bytes(stdout)
            (logs/('outer-'+str(p.pid)+'.stderr.bin')).write_bytes(stderr)
            cleanup.update(returncode=p.returncode,group_absent=absent(p.pid),pipes_drained=drained,
                           stdout_sha256=sha(stdout),stderr_sha256=sha(stderr))
            report['outer_cleanup'].append(cleanup)
            if cleanup['group_absent']and p.returncode is not None and drained:RAW.discard(p)
        report['live_owned_handles_after_cleanup']=len(RAW)
        if RAW or report['outer_cleanup']:report['complete']=False
        save()

    return run,cleanup,RAW
