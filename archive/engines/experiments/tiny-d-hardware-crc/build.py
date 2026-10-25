#!/usr/bin/env python3
"""One fixed hardware CRC experiment; output must be new and outside Git."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,signal,struct,subprocess,time

HERE=Path(__file__).resolve().parent
NORMAL=HERE.parents[2]/'engines/compact/tiny-entry-d'
def sha(b):return hashlib.sha256(b).hexdigest()
def pin(b):return {'bytes':len(b),'sha256':sha(b)}
def sections(b):
 h=struct.unpack_from('<16sHHIQQQIHHHHHH',b)
 ss=[struct.unpack_from('<IIQQQQIIQQ',b,h[6]+i*h[11])for i in range(h[12])]
 strings=b[ss[h[13]][4]:ss[h[13]][4]+ss[h[13]][5]]
 return {strings[s[0]:].split(b'\0',1)[0].decode():{'address':s[3],'offset':s[4],**pin(b[s[4]:s[4]+s[5]])}for s in ss if strings[s[0]:].split(b'\0',1)[0]in[b'.text',b'.rodata',b'.payload']}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 out=a.out.resolve()
 if not a.out.is_absolute()or out.exists()or any((x/'.git').exists()for x in[out,*out.parents]):p.error('new absolute output outside Git required')
 recipe=json.loads((HERE/'recipe.json').read_bytes());assert recipe['format']==1
 for n,e in recipe['normal21'].items():assert pin((NORMAL/n).read_bytes())==e,n
 for n,e in recipe['owned_inputs'].items():assert pin((HERE/n).read_bytes())==e,n
 cpu=[line.split(':',1)[1].split()for line in Path('/proc/cpuinfo').read_text().splitlines()if line.startswith('flags')]
 assert cpu and all('sse4_2'in f for f in cpu),'SSE4.2-advertised CPU required'
 out.mkdir();frozen=out/'inputs';frozen.mkdir();(frozen/'loader').mkdir();(frozen/'normal').mkdir()
 owned={n:pin((HERE/n).read_bytes())for n in['.gitattributes','README.md','build.py','recipe.json','decoder.h','diagnostic.c']}
 for n in owned:(frozen/n).write_bytes((HERE/n).read_bytes())
 for n in['loader/loader.c','loader/image.ld']:(frozen/n).write_bytes((NORMAL/n).read_bytes())
 (frozen/'loader/decoder.h').write_bytes((HERE/'decoder.h').read_bytes())
 for n in['packer.py','recipe.json']:(frozen/'normal'/n).write_bytes((NORMAL/n).read_bytes())
 original=json.loads((frozen/'normal/recipe.json').read_bytes())
 assert recipe['loader_flags']==original['loader_flags']
 report={'complete':False,'scope':'one SSE4.2 CRC byte function; fixed native/packet/loader/model/flags; isolated positive diagnostics and static complete ELF cost only','owned_source6':owned,'normal21_before':recipe['normal21'],'ISA':'Linux x86-64 with SSE4.2 CRC32 r32,r/m8 required; no dispatch/fallback','cpu_feature_advertised':True,'commands':[],'forms':[],'native_compiles':0,'encoder_runs':0,'control_compiles':0,'shipping_audit_engine_runs':0,'negative_fault_RIE_ptrace_register_personality_campaigns':0,'terminal_handles':0}
 deadline=time.monotonic()+90
 def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
 def run(command,kind):
  remaining=min(30,deadline-time.monotonic());assert remaining>0
  child=subprocess.Popen([str(x)for x in command],stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
  report['terminal_handles']=1;record={'kind':kind,'command':[str(x)for x in command],'pid':child.pid,'forced_cleanup':False};stdout=stderr=b'';save()
  try:
   stdout,stderr=child.communicate(timeout=remaining)
  except BaseException:
   record['forced_cleanup']=True
   try:os.killpg(child.pid,signal.SIGKILL)
   except ProcessLookupError:pass
   stdout,stderr=child.communicate(timeout=3)
   raise
  finally:
   record['returncode']=child.returncode
   try:os.killpg(child.pid,0);record['group_absent']=False
   except ProcessLookupError:record['group_absent']=True
   if child.poll()is not None and record['group_absent']:report['terminal_handles']=0
   record['stdout']=stdout.decode(errors='replace');record['stderr']=stderr.decode(errors='replace')
   report['commands'].append(record);save()
  if record['returncode']or not record['group_absent']:raise RuntimeError('first command failure; no retry')
  return record
 save()
 try:
  crc=out/'crc-only';crc.mkdir()
  run(['cc','-O2','-std=c11','-DCRC_ONLY=1','-DMODEL_WMASK=0x0101127e',frozen/'diagnostic.c','-o',crc/'check'],'CRC diagnostic compile')
  checked=run([crc/'check'],'CRC function only')
  report['CRC_diagnostic']=json.loads(checked['stdout']);assert report['CRC_diagnostic']['complete']and report['CRC_diagnostic']['comparisons']==5673
  spec=importlib.util.spec_from_file_location('hardware_crc_fixed_packer',frozen/'normal/packer.py');packer=importlib.util.module_from_spec(spec);spec.loader.exec_module(packer)
  for form,inputs in recipe['forms'].items():
   expected=original['expected'][form];native=Path(inputs['native']['path']).read_bytes();packet=Path(inputs['packet']['path']).read_bytes()
   assert pin(native)=={k:inputs['native'][k]for k in['bytes','sha256']}
   assert pin(packet)=={k:inputs['packet'][k]for k in['bytes','sha256']}
   layout=packer.admit(native,expected,sha)
   directory=out/form
   built=packer.compile_loader(directory/'shipping',frozen/'loader',packet,layout,recipe['loader_flags'],lambda command:run(command,'shipping loader compile'),sha,model_wmask=expected['model_wmask'],checkpoint=False)
   whole=Path(built['path']).read_bytes();parsed=packer.elf(whole)
   assert parsed['entry']==0x100000b0 and parsed['section_count']==parsed['section_offset']==parsed['section_names']==0
   assert whole[-len(packet):]==packet
   linked=(directory/'shipping/linked').read_bytes();cost=sections(linked)
   dumped=run(['objdump','-d',directory/'shipping/linked'],'static loader ISA decode')
   (directory/'objdump.txt').write_text(dumped['stdout']);crc_lines=[s for s in dumped['stdout'].splitlines()if 'crc32'in s]
   assert crc_lines,'hardware instruction absent'
   current={'form':form,'native':pin(native),'packet':pin(packet),'native_layout':layout,'whole':built,'whole_ELF':parsed,'sections':cost,'CRC32_disassembly':crc_lines,'old_whole_bytes':expected['whole_bytes'],'whole_delta_bytes':len(whole)-expected['whole_bytes']}
   report['forms'].append(current);save()
   diag=directory/'decode';diag.mkdir()
   run(['cc','-O2','-std=c11','-DCRC_ONLY=0',f'-DMODEL_WMASK={expected["model_wmask"]}u',frozen/'diagnostic.c','-o',diag/'check'],'packet diagnostic compile')
   checked=run([diag/'check',directory/'shipping/payload.bin',inputs['native']['path'],diag/'decoded.bcj',diag/'decoded.native'],'isolated actual packet decode')
   current['decode']=json.loads(checked['stdout']);assert current['decode']['complete']
   current['decoded_bcj']=pin((diag/'decoded.bcj').read_bytes());current['decoded_native']=pin((diag/'decoded.native').read_bytes());assert current['decoded_native']==pin(native)
   save()
  for n,e in recipe['normal21'].items():assert pin((NORMAL/n).read_bytes())==e,n
  for n,e in owned.items():assert pin((HERE/n).read_bytes())==e,n
  report['normal21_unchanged']=True;report['owned_source6_unchanged']=True
  report['complete']=True;report['both_forms_gain']=all(f['whole_delta_bytes']<0 for f in report['forms'])
 except BaseException as error:
  report['complete']=False;report['failure']={'type':type(error).__name__,'message':str(error)};raise
 finally:save()
 print(json.dumps({'complete':True,'results':pin((out/'results.json').read_bytes()),'forms':[{k:f[k]for k in['form','whole_delta_bytes']}for f in report['forms']],'terminal_handles':report['terminal_handles']}))
if __name__=='__main__':main()
