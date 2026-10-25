"""Exact full-PP gate bodies from pinned project alpha producer; run is injected.

Only compiler/preprocessor tools are used; no engine is launched.
"""
import hashlib

def sha(data):return hashlib.sha256(data).hexdigest()

def first_difference(a,b):
    return next((i for i,(x,y) in enumerate(zip(a,b)) if x!=y), min(len(a),len(b)))


def header_gate(source,candidate,compiler,mapping,lexer,directory):
    """Strict full-PP byte equality after identifier-only alpha inversion.

    Macro final-state capture is an additional check, not a claim to enumerate
    every transient macro definition. No inverse numeric replacement is used.
    All original compiler options except the output path remain unchanged.
    """
    if compiler[-2:]!=['-o','x'] or compiler[-5:-2]!=['-x','c','-']:
        raise ValueError('unexpected fixed compiler output/stdin layout')
    base=compiler[:-2]
    outputs={};observations={}
    for name,data in (('control',source),('candidate',candidate)):
        pp_command=base+['-E','-P']
        macro_command=base+['-E','-dM']
        for kind,command in (('expanded',pp_command),('macros',macro_command)):
            process=run(command,directory,data,90)
            (directory/(name+'-'+kind+'.stderr')).write_bytes(process.stderr)
            (directory/(name+'-'+kind+'.txt')).write_bytes(process.stdout)
            if process.returncode:raise ValueError('header preprocessing failed: '+name+'/'+kind)
            outputs[name,kind]=process.stdout
            observations[name+'_'+kind]={'command':command,'bytes':len(process.stdout),'sha256':sha(process.stdout)}
    macro_values={}
    macro_names=set()
    for line in outputs['control','macros'].decode().splitlines():
        if line.startswith('#define '):
            parts=line.split(None,2)
            macro_names.add(parts[1].split('(',1)[0])
            if parts[1] in ('WORKERS','TT_BITS','PLY'):
                macro_values[parts[1]]=parts[2] if len(parts)>2 else ''
    if macro_values!={'WORKERS':'2','TT_BITS':'18','PLY':'128'}:
        raise ValueError('actual compiler resource macro values differ')
    fresh=set(mapping.values())
    expanded_names={token for _,_,token in lexer._identifier_spans(outputs['control','expanded'].decode())}
    macro_text=outputs['control','macros'].decode()
    macro_words=set(lexer._ANY_WORD.findall(macro_text))
    captures=sorted(fresh & (expanded_names|macro_names|macro_words))
    if captures:raise ValueError('fresh alias already belongs to actual headers/macros: '+','.join(captures))
    if sorted(outputs['control','macros'].splitlines(keepends=True))!=sorted(outputs['candidate','macros'].splitlines(keepends=True)):
        raise ValueError('complete final macro definitions changed')
    inverse={'expanded.c':outputs['candidate','expanded']}
    for old,new in mapping.items():
        inverse=lexer._replace(inverse,new,old)
    original=outputs['control','expanded'];restored=inverse['expanded.c']
    (directory/'candidate-expanded-inverse.txt').write_bytes(restored)
    if restored!=original:
        raise ValueError('strict expanded-byte alpha equality failed at '+str(first_difference(original,restored)))
    return {'pass':True,'resource_macro_values':macro_values,'fresh_alias_capture':captures,
            'strict_full_preprocessed_alpha_inverse_bytes_equal':True,
            'expanded_control_sha256':sha(original),'expanded_inverse_sha256':sha(restored),
            'numeric_inverse_replacements':0,'final_macro_definitions_equal':True,
            'macro_history_coverage':'final definitions only; actual expansion plus full native identity are separate decisive gates',
            'observations':observations}
