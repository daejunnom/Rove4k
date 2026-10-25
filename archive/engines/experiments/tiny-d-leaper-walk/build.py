#!/usr/bin/env python3
"""One admitted leaper specialization: native2, then encoder2/loader2; target0."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import struct
import subprocess
import sys
import time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
NORMAL=HERE.parents[1]/'compact/tiny-entry-d'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def need(value,message):
 if not value:raise ValueError(message)
def pinned(path,digest):
 raw=path.read_bytes();need(sha(raw)==digest,'pinned input differs: '+str(path));return raw
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def absent(pid):
 try:os.killpg(pid,0);return False
 except ProcessLookupError:return True
def sections(raw):
 off=struct.unpack_from('<Q',raw,40)[0];size,count,names=struct.unpack_from('<HHH',raw,58)
 need(off and size==64 and 0<names<count and off+size*count<=len(raw),'linked ELF sections')
 rows=[struct.unpack_from('<IIQQQQIIQQ',raw,off+size*i)for i in range(count)]
 strings=raw[rows[names][4]:rows[names][4]+rows[names][5]];result={}
 for r in rows:
  end=strings.find(b'\0',r[0]);need(end>=r[0],'section name extent')
  name=strings[r[0]:end].decode('ascii');result[name]={'bytes':r[5],'type':r[1],'flags':r[2],'offset':r[4]}
 need(not any(r['bytes'] and r['type'] in (4,6,9,11)for r in result.values()),'relocation/dynamic section unsupported')
 return result
def admit_native(raw,form,packer):
 need(raw[:9]==b'\x7fELF\x02\x01\x01\0\0' and struct.unpack_from('<IHHHHHH',raw,48)==(0,64,56,3,0,0,0),'literal static native ELF header')
 parsed=packer.elf(raw);pages=(len(raw)+4095)//4096*4096
 need(pages in ((8192,)if form=='scalar-shipping'else(8192,12288)),'unknown per-form native RX class')
 bss=0x400000+pages;bp=176128
 need(0x400000+232<=parsed['entry']<0x400000+len(raw),'native entry outside RX code')
 expected=[{'type':1,'flags':5,'offset':0,'vaddr':0x400000,'paddr':0x400000,'filesz':len(raw),'memsz':len(raw),'align':4096},
  {'type':1,'flags':6,'offset':0,'vaddr':bss,'paddr':bss,'filesz':0,'memsz':175092,'align':4096},
  {'type':0x6474e551,'flags':6,'offset':0,'vaddr':0,'paddr':0,'filesz':0,'memsz':0,'align':8}]
 need(parsed['segments']==expected,'unknown exact native PHDR/BSS/NX class')
 return {**parsed,'image_base':0x400000,'image_size':len(raw),'image_pages':pages,'bss_base':bss,'bss_size':175092,'bss_pages':bp,
         'guard_base':0x3ff000,'reserve_size':pages+bp+8192,'upper_guard':bss+bp}
def outer(raw,packer):
 parsed=packer.elf(raw)
 need(struct.unpack_from('<IHHHHHH',raw,48)==(0,64,56,2,0,0,0),'sectionless whole ELF')
 need(parsed['entry']==0x100000b0 and parsed['segments']==[
  {'type':1,'flags':5,'offset':0,'vaddr':0x10000000,'paddr':0x10000000,'filesz':len(raw),'memsz':len(raw),'align':4096},
  {'type':0x6474e551,'flags':6,'offset':0,'vaddr':0,'paddr':0,'filesz':0,'memsz':0,'align':8}],'unknown whole RX/NX structure')
 return parsed
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();out=args.out.resolve()
 need(args.out.is_absolute()and not out.exists()and not any((p/'.git').exists()for p in(out,*out.parents)),'new absolute external output')
 need(sys.platform=='linux' and os.uname().machine=='x86_64','fixed Linux x86-64 target')
 out.mkdir();start=time.monotonic();deadline=start+180;phase='inputs'
 report={'complete':False,'scope':'sole native/whole first-cost; no target or functional qualification',
  'native_compile_attempts':0,'encoder_attempts':0,'loader_compile_attempts':0,'control_copy_compile':0,'target_audit_fresh_negative_stub_game_benchmark':0,
  'compiler_commands':[],'controls':[],'candidates':[],'failures':[]}
 def cancelled(signum,frame):raise TimeoutError('leaper cost cancelled')
 prior=signal.signal(signal.SIGTERM,cancelled)
 def save():(out/'cost.json').write_text(json.dumps(report,indent=2)+'\n')
 def run(command):
  p=None;failed=None;stdout=stderr=b'';forced=False
  try:
   left=min(45,deadline-time.monotonic());need(left>0,'aggregate cost deadline')
   mask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGTERM})
   def limits():
    signal.pthread_sigmask(signal.SIG_SETMASK,mask)
    resource.setrlimit(resource.RLIMIT_CPU,(30,30));resource.setrlimit(resource.RLIMIT_AS,(2147483648,2147483648))
   try:p=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,preexec_fn=limits)
   finally:signal.pthread_sigmask(signal.SIG_SETMASK,mask)
   stdout,stderr=p.communicate(timeout=left);need(p.returncode==0,'fixed compiler failed')
  except BaseException as error:failed=error
  finally:
   mask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGTERM})
   try:
    if p is not None:
     try:os.killpg(p.pid,signal.SIGKILL);forced=True
     except ProcessLookupError:pass
     if p.poll() is None:
      a,b=p.communicate(timeout=5);stdout+=a;stderr+=b
     record={'command':command,'returncode':p.returncode,'stdout_sha256':sha(stdout),'stderr_sha256':sha(stderr),'killpg_sent':forced,'owned_group_absent':absent(p.pid)}
     report['compiler_commands'].append(record);n=len(report['compiler_commands'])
     (out/f'compiler-{n}.stdout').write_bytes(stdout);(out/f'compiler-{n}.stderr').write_bytes(stderr)
     if forced or not record['owned_group_absent']:failed=failed or RuntimeError('compiler group needed cleanup')
    save()
   finally:signal.pthread_sigmask(signal.SIG_SETMASK,mask)
  if failed is not None:raise failed
  return record
 try:
  # These build resource limits do not change the engine profile or its ABI.
  resource.setrlimit(resource.RLIMIT_CPU,(150,150));resource.setrlimit(resource.RLIMIT_AS,(3221225472,3221225472))
  local=json.loads((HERE/'recipe.json').read_bytes())
  original_recipe=pinned(NORMAL/'recipe.json',local['normal_recipe_sha256']);normal=json.loads(original_recipe)
  need(normal['profile']==local['profile']=={'workers':2,'tt_bits':18,'ply':128,'dev':0},'fixed profile')
  own=out/'producer';own.mkdir()
  for name in ('.gitattributes','README.md','build.py','recipe.json','transform.py'):(own/name).write_bytes((HERE/name).read_bytes())
  report['producer5']={name:{'bytes':(own/name).stat().st_size,'sha256':sha((own/name).read_bytes())}for name in ('.gitattributes','README.md','build.py','recipe.json','transform.py')}
  tree=out/'inputs';tree.mkdir();(tree/'recipe.json').write_bytes(original_recipe)
  sourcepins={**normal['native_source_sha256'],**normal['loader_source_sha256'],'packer.py':local['normal_packer_sha256']}
  report['input_sources']={}
  for name,digest in sourcepins.items():
   raw=(NORMAL/name).read_bytes();data=raw.replace(b'\r\n',b'\n');need(b'\r'not in data and sha(data)==digest,'normal source differs '+name)
   p=tree/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
   report['input_sources'][name]={'bytes':len(data),'sha256':sha(data),'working_bytes_sha256':sha(raw)}
  transform=load('leaper_transform',own/'transform.py');oldboard=(tree/'native/board.c').read_bytes();board=transform.transform(oldboard);(tree/'native/board.c').write_bytes(board)
  report['board_transform']={'old_bytes':len(oldboard),'old_sha256':sha(oldboard),'new_bytes':len(board),'new_sha256':sha(board),'inverse_and_complement':True}
  report['candidate_source8']={name:{'bytes':(tree/name).stat().st_size,'sha256':sha((tree/name).read_bytes())}for name in normal['native_source_sha256']}
  packer=load('leaper_fixed_elf',tree/'packer.py')
  for form,e in normal['expected'].items():
   paths=local['controls'][form];item={'form':form}
   for name,size,digest in [('native',e['native_bytes'],e['native_sha256']),('whole',e['whole_bytes'],e['whole_sha256'])]:
    raw=pinned(Path(paths[name]),digest);need(len(raw)==size,'baseline size differs');item[name]={'path':paths[name],'bytes':size,'sha256':digest}
   linked_path=Path(paths['native']).with_name('linked');linked=linked_path.read_bytes()
   need(packer.strip_native(linked)==Path(paths['native']).read_bytes(),'control linked/native binding differs')
   item['linked']={'path':str(linked_path),'sha256':sha(linked),'sections':sections(linked)}
   report['controls'].append(item)
  for form,e in normal['expected'].items():
   phase=form+'/native';d=out/form/'native';d.mkdir(parents=True)
   command=['cc',*normal['native_flags'],f'-DD_HQ={e["hq"]}','-DDEV=0',*[str(tree/'native'/n)for n in normal['native_units']],'-Wl,-T,'+str(tree/'native/image.ld'),'-o',str(d/'linked')]
   report['native_compile_attempts']+=1;save();compiled=run(command)
   linked=(d/'linked').read_bytes();costs=sections(linked);native=packer.strip_native(linked);layout=admit_native(native,form,packer)
   need(not costs.get('.data',{}).get('bytes',0) and costs.get('.bss',{}).get('bytes')==175092,'native section data/BSS differs')
   p=d/'x';p.write_bytes(native)
   control=next(x for x in report['controls']if x['form']==form)
   report['candidates'].append({'form':form,'native':{'path':str(p),'bytes':len(native),'sha256':sha(native),'compile':compiled,'identical_to_control':sha(native)==e['native_sha256']},'sections':costs,'layout':layout,'native_byte_delta':len(native)-e['native_bytes'],'text_byte_delta':costs['.text']['bytes']-control['linked']['sections']['.text']['bytes']})
   save()
  # All new identities and both exact geometries are fixed before encoding.
  need(len(report['candidates'])==2,'both native classes required')
  codec=load('leaper_fixed_codec',tree/'loader/codec.py')
  for item in report['candidates']:
   form=item['form'];e=normal['expected'][form];phase=form+'/whole';native=Path(item['native']['path']).read_bytes()
   need(sha(native)==item['native']['sha256'],'candidate changed before whole')
   model=codec.load_models((tree/'loader/models.json').read_bytes(),form)
   need(time.monotonic()<deadline,'aggregate deadline before encoder');report['encoder_attempts']+=1;save()
   payload,encoding=codec.encode_native(native,model)
   need(time.monotonic()<deadline,'aggregate deadline after encoder');phase=form+'/loader';report['loader_compile_attempts']+=1;save()
   whole=packer.compile_loader(out/form/'context',tree/'loader',payload,item['layout'],normal['loader_flags'],run,sha,checkpoint=False)
   item['packet']={'bytes':len(payload),'sha256':sha(payload),'encoding':encoding};item['whole']=whole
   item['outer']=outer(Path(whole['path']).read_bytes(),packer);item['whole_byte_delta']=whole['bytes']-e['whole_bytes'];save()
  report['complete']=True
  report['selection']='first-cost only; positive gains need separately authorized qualification'if any(x['whole_byte_delta']<0 for x in report['candidates'])else'unselected tie/loss; stop without runtime'
 except BaseException as error:
  report['complete']=False;report['failures'].append({'phase':phase,'type':type(error).__name__,'message':str(error)})
 finally:
  mask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGTERM})
  try:report['elapsed_seconds']=time.monotonic()-start;save()
  finally:signal.signal(signal.SIGTERM,prior);signal.pthread_sigmask(signal.SIG_SETMASK,mask)
 print(json.dumps({'complete':report['complete'],'receipt_sha256':sha((out/'cost.json').read_bytes()),'forms':[{'form':i['form'],'native':i['native']['bytes'],'whole':i.get('whole',{}).get('bytes'),'delta':i.get('whole_byte_delta')}for i in report['candidates']],'failures':report['failures']}))
 return 0 if report['complete']else 1
if __name__=='__main__':raise SystemExit(main())
