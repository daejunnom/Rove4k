#!/usr/bin/env python3
"""One exact-owner startup diagnostic: status counters versus mapping walks.

No GO, qualifier retry, threshold change, memory-content read or environment
inspection occurs. A frozen original Host owns one driver and its inherited
process group through natural quit. Failed historical runtime stays failed.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
HOST = "engines/experiments/tcec-scope/build.py"
HOST_SHA = "5fa10c6f8f032be374bf3a86bbe6ca558076630a2cc3170b41890f691688f563"
PROGRAM = {"bytes":5373,"sha256":"1f187ed7b618674e9b6be78fac83f46223631beb8af83c1dacf5f4ca49554450"}
NATIVE = {"bytes":7360,"sha256":"cfa7b5d045d5f1e6e2232942e38d79cd8b8812e9e3ed7702fb4df50ab71296f4"}

DRIVER = r'''import hashlib,json,os,re,select,subprocess,sys,time
from pathlib import Path
program,out=Path(sys.argv[1]),Path(sys.argv[2]);expected=json.loads(sys.argv[3])
report=dict(kind="D-owner-one-startup-RSS-diagnostic-v1",complete=False,GO_sent=False,
 engine_started=False,engine_reaped=False,forced_cleanup=False,snapshots=[],events=[])
child=None;buffer=b"";deadline=time.monotonic()+25
def save():(out/"diagnostic.json").write_text(json.dumps(report,indent=2)+"\n")
def pin(d):return dict(bytes=len(d),sha256=hashlib.sha256(d).hexdigest())
def identity():
 fields=(Path('/proc')/str(child.pid)/'stat').read_text().rsplit(')',1)[1].split()
 return dict(pid=child.pid,pgid=os.getpgid(child.pid),start_ticks=int(fields[19]),state=fields[0])
def send(data):child.stdin.write(data);child.stdin.flush();report['events'].append(dict(send=data.decode()));save()
def until(marker):
 global buffer
 while True:
  if b'\n' in buffer:
   line,buffer=buffer.split(b'\n',1);line+=b'\n';report['events'].append(dict(receive=line.decode()));save()
   if line==marker:return
   continue
  left=deadline-time.monotonic()
  if left<=0:raise TimeoutError('bounded startup dialogue')
  if select.select([child.stdout],[],[],min(left,.2))[0]:
   data=os.read(child.stdout.fileno(),4096)
   if not data:raise EOFError('startup EOF before ready')
   buffer+=data
   if len(buffer)>65536:raise ValueError('bounded startup output exceeded')
def values(text):
 result={}
 for line in text.splitlines():
  key,sep,tail=line.partition(':')
  fields=tail.split()
  if sep and len(fields)==2 and fields[1]=='kB' and fields[0].isdigit():result[key]=int(fields[0])*1024
 return result
def mappings(text):
 result=[];current=None
 for line in text.splitlines():
  if re.match(r'^[0-9a-f]+-[0-9a-f]+ ',line):
   fields=line.split(None,5);begin,end=(int(n,16) for n in fields[0].split('-'))
   current=dict(header=line,begin=begin,end=end,extent=end-begin,permissions=fields[1],path=fields[5] if len(fields)>5 else '',fields={})
   result.append(current)
  elif current is not None:current['fields'].update(values(line))
 return result
def snapshot(label):
 before=identity();root=Path('/proc')/str(child.pid);directory=out/label;directory.mkdir()
 raw={};started=time.monotonic_ns()
 for name in ('status','smaps_rollup','smaps','numa_maps'):
  raw[name]=(root/name).read_bytes();(directory/name.replace('_','-')).write_bytes(raw[name])
 status_after=(root/'status').read_bytes();(directory/'status-after').write_bytes(status_after)
 actual=(root/'exe').read_bytes()
 if pin(actual)!=expected:raise ValueError('actual native /proc/exe identity differs')
 tasks=sorted(int(p.name) for p in (root/'task').iterdir() if p.name.isdecimal())
 after=identity()
 if before['pid']!=after['pid'] or before['pgid']!=after['pgid'] or before['start_ticks']!=after['start_ticks'] or before['start_ticks']!=report['original_identity']['start_ticks']:raise ValueError('original engine identity changed during snapshot')
 maps=mappings(raw['smaps'].decode());v=values(raw['status'].decode());roll=values(raw['smaps_rollup'].decode());accurate=sum(m['fields'].get('Rss',0) for m in maps)
 candidates=[m for m in maps if m['permissions']=='rw-p' and not m['path'] and m['extent']>=134217728]
 row=dict(label=label,started_monotonic_ns=started,ended_monotonic_ns=time.monotonic_ns(),identity_before=before,identity_after=after,
  original_PID_starttick_held=True,native=pin(actual),tasks=tasks,raw={n:pin(d) for n,d in raw.items()},status_after=pin(status_after),
  status_bytes=v,status_after_bytes=values(status_after.decode()),rollup_bytes=roll,smaps_Rss_sum_bytes=accurate,
  VmRSS_deficit_to_rollup_bytes=roll.get('Rss',0)-v.get('VmRSS',0),VmRSS_deficit_to_smaps_bytes=accurate-v.get('VmRSS',0),
  large_anonymous_RW_candidates=candidates,exact_TT_sized_mapping_observed=any(m['extent']==134217728 for m in candidates),
  merged_mapping_individual_TT_RSS_inferred=False,smaps_includes_engine_stacks_and_other_mappings=True)
 report['snapshots'].append(row);save()
def group_members():
 result=[]
 for entry in Path('/proc').iterdir():
  if not entry.name.isdecimal():continue
  try:
   fields=(entry/'stat').read_text().rsplit(')',1)[1].split()
   if int(fields[2])==os.getpgrp() and int(entry.name) not in (os.getpid(),child.pid):result.append(int(entry.name))
  except FileNotFoundError:continue
 return sorted(result)
def settle():
 until_exit=time.monotonic()+5
 while os.waitid(os.P_PID,child.pid,os.WEXITED|os.WNOHANG|os.WNOWAIT) is None:
  if time.monotonic()>=until_exit:raise TimeoutError('engine did not naturally quit')
  time.sleep(.01)
 others=group_members();tasks=sorted(int(p.name) for p in (Path('/proc')/str(child.pid)/'task').iterdir() if p.name.isdecimal())
 if others or tasks!=[child.pid]:raise ValueError('other original group members/tasks remain before reap')
 report['identity_before_reap']=identity();report['other_group_members_before_reap']=others
 report['original_identity_retained_until_other_members_absent']=True
 code=child.wait();report.update(engine_reaped=True,returncode=code)
 if code:raise ValueError('engine natural status differs')
try:
 save();child=subprocess.Popen([str(program)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=None,bufsize=0)
 report.update(engine_started=True,pid=child.pid,driver_pid=os.getpid(),owner_pgid=os.getpgrp(),original_identity=identity())
 if os.getpgid(child.pid)!=os.getpgrp():raise ValueError('engine escaped original driver group')
 send(b'uci\n');until(b'uciok\n');send(b'isready\n');until(b'readyok\n');snapshot('after-first-ready')
 send(b'isready\n');until(b'readyok\n');snapshot('after-second-ready')
 send(b'quit\n');child.stdin.close();child.stdin=None;settle()
 if child.stdout.read():raise ValueError('unexpected terminal startup output')
 report.update(complete=True,natural_termination=True,qualifier_retried=False,threshold_changed=False,
  counter_difference_observed=any(s['VmRSS_deficit_to_rollup_bytes']>=4096 or s['VmRSS_deficit_to_smaps_bytes']>=4096 for s in report['snapshots']))
except BaseException as error:
 report['failure']=dict(type=type(error).__name__,message=str(error))
 if child is not None and not report['engine_reaped']:
  try:
   if child.stdin is not None:send(b'quit\n');child.stdin.close();child.stdin=None
   settle()
  except BaseException as cleanup:report['cleanup_failure']=dict(type=type(cleanup).__name__,message=str(cleanup))
 save();raise
finally:save()
'''


def pin(data):
    return {"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()}


def checked(path, expected):
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
        raise ValueError("regular unlinked diagnostic input required")
    data = path.read_bytes()
    if pin(data) != expected:
        raise ValueError("immutable diagnostic input identity differs")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--carrier", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    carrier, out = args.carrier.resolve(), args.out.resolve()
    if (sys.platform != "linux" or platform.machine() != "x86_64" or
        not args.carrier.is_absolute() or not args.out.is_absolute() or out.exists() or
        any((p/".git").exists() for p in (out,*out.parents))):
        parser.error("absolute exact owner carrier and new external Linux x86-64 output required")
    program = checked(carrier/"program", PROGRAM)
    native = checked(carrier/"native/image", NATIVE)
    host_data = (ROOT/HOST).read_bytes().replace(b"\r\n",b"\n")
    if pin(host_data)["sha256"] != HOST_SHA:
        raise ValueError("original command owner differs")
    own = Path(__file__).read_bytes().replace(b"\r\n",b"\n")
    out.mkdir();(out/"inputs").mkdir();(out/"session").mkdir()
    for name, data in (("host.py",host_data),("probe_owner_rss.py",own),("packed",program),("native",native),("driver.py",DRIVER.encode())):
        (out/"inputs"/name).write_bytes(data)
    (out/"inputs/packed").chmod(0o700)
    spec=importlib.util.spec_from_file_location("D_owner_RSS_original_Host",out/"inputs/host.py")
    hostmod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=hostmod;spec.loader.exec_module(hostmod)
    hostmod.LIMITS={**hostmod.LIMITS,"aggregate_wall":60,"per_command_wall":40,
        "parent_CPU":30,"parent_CPU_hard":35,"child_CPU":20}
    report={"kind":"D-owner-one-startup-RSS-diagnostic-supervisor-v1","complete":False,
        "commands":[],"program":PROGRAM,"native":NATIVE,"TT_contract_bytes":128<<20,
        "instances":1,"GO_sent":False,"qualifier_retried":False,"threshold_changed":False,
        "inputs":{"host.py":pin(host_data),"probe_owner_rss.py":pin(own),"driver.py":pin(DRIVER.encode())}}
    def save():(out/"results.json").write_text(json.dumps(report,indent=2)+"\n")
    save();host=hostmod.Host(out,report,save)
    try:
        host.run([sys.executable,"-I","-B",str(out/"inputs/driver.py"),str(out/"inputs/packed"),str(out/"session"),json.dumps(NATIVE)],cwd=out,kind="one-exact-owner-startup-RSS-diagnostic")
        result=json.loads((out/"session/diagnostic.json").read_text())
        if result.get("complete") is not True or result.get("engine_reaped") is not True or result.get("forced_cleanup") or result.get("returncode")!=0:
            raise ValueError("diagnostic engine did not naturally settle")
        checked(carrier/"program",PROGRAM);checked(carrier/"native/image",NATIVE)
        report.update(complete=True,diagnostic=pin((out/"session/diagnostic.json").read_bytes()),
            counter_difference_observed=result["counter_difference_observed"],original_carrier_unchanged=True,
            runtime_qualified=False,rules_qualified=False,selected=False)
    except BaseException as error:
        report["failure"]={"type":type(error).__name__,"message":str(error)}
        raise
    finally:
        try:host.close()
        except BaseException as error:
            report["complete"]=False;report["cleanup_failure"]={"type":type(error).__name__,"message":str(error)};raise
        finally:
            if report.get("host_cleanup",{}).get("errors") or report.get("host_cleanup",{}).get("unsettled_commands"):
                report["complete"]=False
            save()
    print(json.dumps({k:report[k] for k in ("complete","instances","GO_sent","counter_difference_observed","runtime_qualified","selected")}),flush=True)


if __name__=="__main__":
    main()
