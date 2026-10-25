#!/usr/bin/env python3
"""One fixed B core source composition first-cost: at most one final native/whole, no engine."""
import argparse
import ast
from collections import Counter
import json
import lzma
from pathlib import Path
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import cost_tools as tools

def require(value,label):
    if not value:raise ValueError(label)
def identity(raw):return {'bytes':len(raw),'sha256':tools.sha(raw)}
def macro_resources(raw):
    values={}
    for line in raw.decode().splitlines():
        if line.startswith('#define '):
            words=line.split(None,2)
            if words[1] in ('WORKERS','TT_BITS','PLY'):values[words[1]]=words[2] if len(words)>2 else ''
    return values
def header_gate(before,after,readable,recipe,mapping,lexer,directory):
    directory.mkdir()
    fixed=['cc','-std=c11','-Os','-pthread','-DWORKERS=2','-DTT_BITS=18','-DDEV=0','-x','c','-','-o','x']
    require(recipe['compiler']==fixed,'original actual shipping compiler')
    base=fixed[:-2];outputs={};rows={}
    configured=recipe['preprocessor']+['-DDEV=0','-x','c','-','-E','-dM']
    probe=tools.run(configured,directory,readable)
    (directory/'configured-macros.txt').write_bytes(probe.stdout);(directory/'configured-macros.stderr').write_bytes(probe.stderr)
    require(probe.returncode==0 and macro_resources(probe.stdout)=={'WORKERS':'2','TT_BITS':'18','PLY':'128'},'configured resources')
    for name,data in (('before',before),('after',after)):
        for kind,flags in (('expanded',['-E','-P']),('macros',['-E','-dM'])):
            command=base+flags;result=tools.run(command,directory,data)
            (directory/(name+'-'+kind+'.txt')).write_bytes(result.stdout)
            (directory/(name+'-'+kind+'.stderr')).write_bytes(result.stderr)
            require(result.returncode==0,'actual compiler complete PP')
            outputs[name,kind]=result.stdout;rows[name+'_'+kind]={'command':command,**identity(result.stdout)}
    macro_names={line.split(None,2)[1].split('(',1)[0] for line in outputs['before','macros'].decode().splitlines() if line.startswith('#define ')}
    words={token for _,_,token in lexer._identifier_spans(outputs['before','expanded'].decode())}
    require(not set(mapping.values())&(macro_names|words),'actual full-header alias freshness')
    equal=outputs['before','macros']==outputs['after','macros']
    same=Counter(outputs['before','macros'].splitlines(keepends=True))==Counter(outputs['after','macros'].splitlines(keepends=True))
    require(same and macro_resources(outputs['before','macros'])==macro_resources(outputs['after','macros'])=={'WORKERS':'2','TT_BITS':'18','PLY':'128'},'raw final macro definitions/resources')
    inverse={'source.c':outputs['after','expanded']}
    for old,new in mapping.items():inverse=lexer._replace(inverse,new,old)
    (directory/'inverse-expanded.txt').write_bytes(inverse['source.c'])
    require(inverse['source.c']==outputs['before','expanded'],'raw full-PP alias-only inverse')
    return {'complete':True,'raw_dump_equal':equal,'same_raw_definition_multiset':same,'order_only':not equal,
      'comparison':'Counter of entire raw logical line bytes with duplicate counts; no whitespace/numeric normalization',
      'alias_only_raw_inverse':True,'numeric_inverse_replacements':0,'configured_resources':macro_resources(probe.stdout),
      'actual_final_resources':macro_resources(outputs['before','macros']),'actual_compiler_flags_retained':True,'removed_output_pair_only':['-o','x'],'observations':rows}
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--repository-root',required=True,type=Path)
    args=parser.parse_args();out=args.out.resolve()
    require(args.out.is_absolute() and not out.exists() and not any((p/'.git').exists() for p in (out,*out.parents)),'new absolute output outside Git')
    manifest_raw=(HERE/'cost-inputs.json').read_bytes();manifest=json.loads(manifest_raw)
    repository=args.repository_root.resolve()
    out.mkdir();frozen=out/'frozen';frozen.mkdir()
    report={'complete':False,'scope':__doc__,'source_files':{},'baseline_evidence_reused':manifest['baseline_evidence_reused'],
      'attempts':[],'tool_commands':tools.COMMANDS,'engine_executions':0,'candidate_DEV_builds':0,
      'old_native_identity_required':False,'candidate_native_compiles':0,'other_variants':0,
      'native_attempt_accounting':'attempted calls counted before tools.run; actual launches and terminal results in tool_commands; at most one call'}
    def save():(out/'cost.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
    save()
    try:
        for name,pin in manifest['source_files'].items():
            source=repository/name[7:] if name.startswith('normal/') else HERE/name
            raw=source.read_bytes();require(identity(raw)==pin,'literal ordinary input '+name)
            dest=frozen/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
            report['source_files'][name]=pin
        (frozen/'cost-inputs.json').write_bytes(manifest_raw)
        selected=frozen/'normal/engines/compact/tiny-entry-b'
        recipe=json.loads((selected/'recipe.json').read_bytes())
        require(recipe['profile']=={'workers':2,'tt_bits':18,'ply':128,'dev_default':False},'fixed B profile')
        require(recipe['compression']=={'format':'xz','filter':'LZMA2','preset':9,'extreme':True,'lc':3,'lp':0,'pb':2,'check':'CRC64'},'fixed B codec')
        template=(selected/'bootstrap.py.in').read_bytes();prefix=(selected/'launcher.sh').read_bytes()
        marker=b'__ROVE_SOURCE_LITERAL__';require(template.count(marker)==1 and len(prefix)==75,'fixed original launcher/template')
        readable=(frozen/'candidate.c').read_bytes()
        fixed_policy=json.loads((frozen/'cost-policy.json').read_bytes())
        lexer=tools.module('B_core_cost_lexer',frozen/'normal/engines/scripts/rename_c.py')
        literal=tools.module('B_core_cost_literal',frozen/'normal/engines/compact/tiny-a/pack_stream.py').source_literal
        # Use the frozen producer, not any mutable experiment outside this closure.
        fixed_transform=tools.module('B_core_cost_fixed_policy',frozen/'cost_policy.py').transform
        first=None
        for index in (1,):
            directory=out/('candidate-'+str(index));directory.mkdir()
            command=[sys.executable,'-I','-B',str(frozen/'cost_preprocess.py'),'--root',str(frozen),'--out',str(directory/'preprocess')]
            result=tools.run(command,directory)
            (directory/'preprocess.stdout').write_bytes(result.stdout);(directory/'preprocess.stderr').write_bytes(result.stderr)
            require(result.returncode==0,'candidate owned preprocessing')
            generation=json.loads((directory/'preprocess/generation.json').read_bytes())
            require(generation['profile']==recipe['profile'] and generation['resource_and_function_decisions_unchanged'],'fixed B specialization profile')
            before=(directory/'preprocess/pre-alpha.c').read_bytes()
            shipping,metadata,mapping=fixed_transform(before,readable,frozen)
            gate=header_gate(before,shipping,readable,recipe,mapping,lexer,directory/'header')
            (directory/'main.c').write_bytes(shipping)
            native_dir=directory/'native';native_dir.mkdir()
            report['candidate_native_compiles']+=1
            compiled=tools.run(recipe['compiler'],native_dir,shipping,timeout=90)
            (native_dir/'compiler.stdout').write_bytes(compiled.stdout);(native_dir/'compiler.stderr').write_bytes(compiled.stderr)
            require(compiled.returncode==0,'candidate native compile')
            native=(native_dir/'x').read_bytes()
            expression,kind=literal(shipping);script=template.replace(marker,expression.encode());ast.parse(script)
            whole=prefix+lzma.compress(script,format=lzma.FORMAT_XZ,check=lzma.CHECK_CRC64,
                filters=[{'id':lzma.FILTER_LZMA2,'preset':9|lzma.PRESET_EXTREME,'lc':3,'lp':0,'pb':2}])
            (directory/'bootstrap.py').write_bytes(script);(directory/'x').write_bytes(whole);(directory/'x').chmod(0o755)
            current=(shipping,native,script,whole)
            if first is None:first=current
            else:require(current==first,'unexpected second candidate attempt')
            report['attempts'].append({'attempt':index,'shipping':identity(shipping),'native':identity(native),'bootstrap':identity(script),'whole':identity(whole),
              'literal_kind':kind,'counter_schema':generation['counter_removal'],'resource_counts':fixed_policy['alpha']['resource_counts'],
              'spelling_policy':metadata,'actual_header_gate':gate,'native_executed':False})
            save()
        for name,pin in manifest['source_files'].items():
            source=repository/name[7:] if name.startswith('normal/') else HERE/name
            require(identity(source.read_bytes())==pin,'ordinary input changed during build '+name)
        require((HERE/'cost-inputs.json').read_bytes()==(frozen/'cost-inputs.json').read_bytes()==manifest_raw,'manifest changed during build')
        expected=manifest['expected']
        report.update(complete=True,shipping_reproduced=False,native_reproduced=False,whole_reproduced=False,independent_repetition_required=False,
            whole_gain_bytes=expected['whole_bytes']-len(first[3]),compact_gain_bytes=expected['source_bytes']-len(first[0]),
            native_delta_bytes=len(first[1])-expected['native_bytes'],gap_to_4096=len(first[3])-4096,
            old_native_equal=tools.sha(first[1])==expected['native_sha256'],owned_live_handles=0,
            disposition='report gain and required qualification' if len(first[3])<expected['whole_bytes'] else 'stop; whole image did not improve')
        save();print(json.dumps({'complete':True,'out':str(out),'whole':identity(first[3]),'native':identity(first[1]),'whole_gain':report['whole_gain_bytes'],'cost_sha256':tools.sha((out/'cost.json').read_bytes())}))
    except BaseException as error:
        report['error']=repr(error);save();raise
if __name__=='__main__':main()
