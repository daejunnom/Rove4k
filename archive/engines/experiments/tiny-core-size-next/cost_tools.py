"""Owned subprocess primitive for this one B attacker composition."""
import hashlib
import importlib.util
import os
from pathlib import Path
import signal
import subprocess
import time

COMMANDS=[]
def sha(data):return hashlib.sha256(data).hexdigest()
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj
def group_members(group):
    members=[]
    for path in Path('/proc').iterdir():
        if not path.name.isdecimal():continue
        try:
            rest=(path/'stat').read_text().rsplit(')',1)[1].split()
            if int(rest[2])==group:members.append({'pid':int(path.name),'state':rest[0]})
        except (FileNotFoundError,ProcessLookupError,PermissionError):pass
    return members
def run(command,directory,input_data=None,timeout=180):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    row={'command':command,'terminal':False,'group_absent':False}
    original=None;stdout=stderr=b''
    process=subprocess.Popen(command,cwd=directory,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
        start_new_session=True,env={**os.environ,'LC_ALL':'C','TZ':'UTC','SOURCE_DATE_EPOCH':'0'})
    try:
        row['leader']=process.pid;COMMANDS.append(row)
        stdout,stderr=process.communicate(input_data,timeout=timeout)
        if group_members(process.pid):raise RuntimeError('tool leader exited with descendant group remaining')
    except BaseException as error:
        original=error
        for action in (signal.SIGTERM,signal.SIGKILL):
            try:os.killpg(process.pid,action)
            except ProcessLookupError:pass
            try:stdout,stderr=process.communicate(timeout=3)
            except subprocess.TimeoutExpired:continue
            until=time.monotonic()+3
            while group_members(process.pid) and time.monotonic()<until:time.sleep(.02)
            if not group_members(process.pid):break
    finally:
        row.update(returncode=process.poll(),terminal=process.poll() is not None,group_absent=not group_members(process.pid),
            stdout_sha256=sha(stdout),stderr_sha256=sha(stderr))
    if original is not None:raise original
    if not row['terminal'] or not row['group_absent']:raise RuntimeError('tool ownership did not settle')
    return subprocess.CompletedProcess(command,process.returncode,stdout,stderr)
