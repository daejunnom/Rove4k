#!/usr/bin/env python3
"""Focused actual shipping4 + publication2 proof; no compiler, stubs, audits or fresh."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import struct
import sys
import time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
NORMAL=HERE.parents[2]/'compact/tiny-entry-d'
COST_SHA='c89c7ec1a595ded61c11844352e80f244149eb29088eaa62b3ec6499ce9d2063'
HELPER_SHA='1bff60b6fac7cb5a3c4212550375341881d984881d44b55f865e675e5877b3d4'
PACKER_SHA='26c1e9660cbe834dd67391dd309e8223391d8137ba199101399c5cc87b629f1e'
ADMISSION_SHA='070c0c0fa4d87d603cfde8407f518044ca212df784bb319a8a883ceed8ba3bfd'
CASE_SHA='78b67ed9d8c76a829b46c8a1837df54591d2ab15bfa5b7e873cbe13667cf9d36'
ORACLE_SHA='aea285b5b5f07602c829595840d5270fa8dc25683ccd26c63607435679024db8'
FIXED={
 'scalar-shipping':(6387,'4c2f7a8839f2d97c19631bf010050fccf3c90df67b7aef5e321cf1412d4b0df8',
                    8060,'381fd1f478b090372365371d39337920c11fee4ab04ed59ab8616d0286b125d1'),
 'hq-shipping':(6580,'07bedfa1707c302fe29d776f0c25b3a63c5bc560a8de4cd08abb96db90ede3a8',
                8448,'215ee72678b41032e7f3283bf40fda752f385833df46d2b430bfc2d5c5f89008')}


def sha(raw):return hashlib.sha256(raw).hexdigest()
def need(ok,message):
 if not ok:raise ValueError(message)
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec)
 sys.modules[name]=m;spec.loader.exec_module(m);return m

def outer(raw):
 need(raw[:9]==b'\x7fELF\x02\x01\x01\0\0','ELF64 LE SystemV')
 need(struct.unpack_from('<HHI',raw,16)==(2,62,1),'x86-64 ET_EXEC')
 need(struct.unpack_from('<QQQ',raw,24)==(0x100000b0,64,0),'literal outer entry/PHDR/sectionless')
 need(struct.unpack_from('<IHHHHHH',raw,48)==(0,64,56,2,0,0,0),'literal ELF header')
 need([struct.unpack_from('<IIQQQQQQ',raw,64+56*i)for i in range(2)]==[
  (1,5,0,0x10000000,0x10000000,len(raw),len(raw),4096),(0x6474e551,6,0,0,0,0,0,8)],'literal outer RX/NXstack')

def main():
 cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('--cost',required=True,type=Path)
 cli.add_argument('--out',required=True,type=Path);args=cli.parse_args();out=args.out.resolve()
 need(args.out.is_absolute()and not out.exists()and not any((p/'.git').exists()for p in (out,*out.parents)),'new absolute external output')
 need(sys.platform.startswith('linux'),'Linux positive observer required')
 out.mkdir();source=out/'source';source.mkdir();helper=None;prior=None;started=time.monotonic();phase='admission'
 report={'complete':False,'scope':'actual worker-reset shipping and output-ownership observations; no previous runtime proof inherited',
  'production':[],'publication':[],'failures':[],'cleanup':[],
  'diagnostic_stub_compiler_audit_fresh_negative':0,'target_memory_register_personality_writes':0,
  'limits':'not general race freedom, zero-iteration sentinel proof, actual first-node deadline causality, strength or normal promotion'}
 try:
  rawcost=args.cost.read_bytes();need(sha(rawcost)==COST_SHA,'exact whole cost receipt')
  cost=json.loads(rawcost);need(cost['complete']and not cost.get('failure')and cost['encodes']==cost['loader_compile_count']==2,'cost complete')
  need(cost['native_compile_count']==cost['control_compile_or_copy']==cost['target_audit_fresh_negative']==0,'cost scope')
  need(len(cost['candidates'])==2 and {c['form']for c in cost['candidates']}==set(FIXED),'two exact forms')
  blobs={'helper.py':(NORMAL/'verify.py').read_bytes(),'packer.py':(NORMAL/'packer.py').read_bytes(),
         'admission.py':(HERE.parent/'whole.py').read_bytes(),'publication_case.py':(HERE/'publication_case.py').read_bytes(),
         'chess_oracle.py':(HERE.parents[2]/'tests/chess_oracle.py').read_bytes().replace(b'\r\n',b'\n')}
  for name,digest in [('helper.py',HELPER_SHA),('packer.py',PACKER_SHA),('admission.py',ADMISSION_SHA),('publication_case.py',CASE_SHA),('chess_oracle.py',ORACLE_SHA)]:
   need(sha(blobs[name])==digest,'pinned source differs: '+name)
  for name,raw in blobs.items():(source/name).write_bytes(raw)
  (source/'qualify.py').write_bytes(Path(__file__).read_bytes());(source/'cost.json').write_bytes(rawcost)
  report['source_sha256']={n:sha(b)for n,b in blobs.items()};report['cost_sha256']=COST_SHA
  helper=load('worker_reset_positive_helper',source/'helper.py');packer=load('worker_reset_elf',source/'packer.py')
  admission=load('worker_reset_literal_admission',source/'admission.py')
  publication=load('worker_reset_publication',source/'publication_case.py');oracle=load('worker_reset_oracle',source/'chess_oracle.py')
  budget=helper.Budget(120);prior=signal.signal(signal.SIGTERM,helper.terminated);admitted=[]
  for item in cost['candidates']:
   form=item['form'];size,digest,nsize,ndigest=FIXED[form]
   program=Path(item['whole']['path']);native=Path(item['native_path']);raw=program.read_bytes();nativebytes=native.read_bytes()
   need(program.is_absolute()and native.is_absolute(),'absolute exact targets')
   need((len(raw),sha(raw))==(size,digest)and(len(nativebytes),sha(nativebytes))==(nsize,ndigest),'actual new whole/native differs')
   layout=admission.admit(nativebytes,form,packer);need(layout==item['layout'],'exact new class/layout differs')
   need(item['whole']['definitions']['CHECKPOINT']==0,'shipping only');outer(raw)
   candidate={'path':str(program),'bytes':size,'sha256':digest}
   fixed={'whole_bytes':size,'whole_sha256':digest,'native_bytes':nsize,'native_sha256':ndigest,
          'entry':layout['entry'],'image_pages':layout['image_pages'],'bss_base':layout['bss_base'],'upper_guard':layout['upper_guard']}
   publication_item={'id':form,'whole_repeats':[{'path':str(program),'native_path':str(native),'checkpoint':False,
                     'definitions':item['whole']['definitions']}]}
   admitted.append((form,candidate,layout,ndigest,publication_item,fixed))
  report['all_two_exact_targets_admitted_before_launch']=True
  for form,candidate,layout,ndigest,item,fixed in admitted:
   row={'form':form,'whole':candidate,'native_sha256':ndigest,'sessions':[]};report['production'].append(row)
   for shutdown in ('quit','EOF'):
    phase=form+'/production/'+shutdown;case={};row['sessions'].append(case)
    helper.production(candidate,layout,ndigest,out/'production'/form/shutdown,budget,oracle,shutdown,case)
  pubout=out/'publication';pubout.mkdir()
  for form,candidate,layout,ndigest,item,fixed in admitted:
   phase=form+'/publication';first_go=b'go\n'if form=='hq-shipping'else b'go wtime 0 btime 0\n'
   row=publication.case(item,fixed,oracle,pubout,first_go);report['publication'].append(row)
   need(row['complete']and not row['forced_cleanup'],'publication did not settle')
  report.update(complete=True,shipping_sessions=6,production_sessions=4,production_GO_epochs=12,
   publication_sessions=2,publication_GO_epochs=4,publication_zero_clock_GO_inputs=3,publication_bare_GO_inputs=1,
   bare_GO_scope='bare token followed by position fence/cancellation, not an uncancelled default-budget timing test',
   new_best_reset_scope='actual legal per-root completion/ownership plus exact runtime/HB source proof; private zero-iteration sentinel not observed')
 except BaseException as error:
  report['complete']=False;report['failures'].append({'phase':phase,'type':type(error).__name__,'message':str(error)})
 finally:
  mask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGTERM})
  try:
   if helper is not None:
    for owned in list(helper.OWNED):
     report['complete']=False
     try:report['cleanup'].append(owned.cleanup())
     except BaseException as error:report['failures'].append({'phase':phase+'/cleanup','message':str(error)})
   report['elapsed_seconds']=time.monotonic()-started;(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
  finally:
   if prior is not None:signal.signal(signal.SIGTERM,prior)
   signal.pthread_sigmask(signal.SIG_SETMASK,mask)
 print(json.dumps({'complete':report['complete'],'receipt_sha256':sha((out/'results.json').read_bytes()),'failures':report['failures']}))
 return 0 if report['complete']else 1

if __name__=='__main__':raise SystemExit(main())
