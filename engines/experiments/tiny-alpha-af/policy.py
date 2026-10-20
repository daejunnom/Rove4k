"""One literal AF shipping spelling policy; never discovers or refreshes aliases."""
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
POLICY_SHA256='4bf1b189e9073aa994c29c07f64bcf05b1b3e749a0a172150cac68c1971d7d92'
POLICY_BYTES=(HERE/'policy.json').read_bytes()
if hashlib.sha256(POLICY_BYTES).hexdigest()!=POLICY_SHA256:raise ValueError('reviewed AF literal policy changed')
_spec=importlib.util.spec_from_file_location('af_reference_opaque',HERE/'reference/policy.py')
reference=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(reference)


def sha(data):return hashlib.sha256(data).hexdigest()


def binding(data,pin,label):
    if len(data)!=pin['bytes'] or sha(data)!=pin['sha256']:raise ValueError(label+' exact bytes changed')


def transform_source(data,*,family,lexer):
    fixed=json.loads(POLICY_BYTES)
    if family not in ('A','F'):raise ValueError('unknown fixed AF family')
    row=fixed['families'][family];binding(data,row['source'],family+' shipping source')
    mapping=fixed['mapping'];resources=fixed['resource_literals']
    if resources!={'WORKERS':'2','TT_BITS':'18','PLY':'128'}:raise ValueError('fixed resources changed')
    if sorted(mapping)!=fixed['allowed_shipping_names'] or set(mapping)&set(fixed['protected_shipping_names']):
        raise ValueError('protected or unaudited old spelling admitted')
    if any(len(old)<=2 or not re.fullmatch(r'[A-Za-z][A-Za-z0-9]*',new) or len(new)!=2 for old,new in mapping.items()):
        raise ValueError('unexpected alias rule')
    aliases=set(mapping.values())
    if len(aliases)!=len(mapping):raise ValueError('noninjective AF aliases')
    for name,pin in fixed['readable_inputs'].items():
        raw=(HERE/'control'/name).read_bytes().replace(b'\r\n',b'\n');binding(raw,pin,'readable reserved words')
        reserved=set(reference._WORD.findall(raw.decode()))|set(reference._WORD.findall(reference._logical(raw.decode())[0]))
        if aliases&reserved:raise ValueError('alias occurs in frozen readable source')
    substitutions={**mapping,**resources}
    before=sha(data);candidate,counts,opaque=reference._rewrite(data,substitutions,lexer=lexer)
    alpha_counts={old:counts[old] for old in mapping};resource_counts={old:counts[old] for old in resources}
    if alpha_counts!=row['alpha_counts'] or resource_counts!=row['resource_counts']:
        raise ValueError('literal AF token occurrence counts changed')
    alpha_saved=sum((len(old)-len(new))*counts[old] for old,new in mapping.items())
    resource_saved=sum((len(old)-len(new))*counts[old] for old,new in resources.items())
    directive_bytes=sum(len(raw.encode()) for kind,raw in opaque if kind=='directive')
    used=sum(counts[old]>0 for old in mapping)
    if (alpha_saved!=row['alpha_saved_bytes'] or resource_saved!=row['resource_saved_bytes']
            or len(data)-len(candidate)!=row['source_saved_bytes'] or used!=row['mapping_used']
            or sum(counts.values())!=row['source_edits_count'] or directive_bytes!=row['retained_directive_bytes']):
        raise ValueError('literal AF arithmetic or opaque count changed')
    binding(candidate,row['candidate'],family+' sole candidate')
    if sha(data)!=before:raise ValueError('source mutated')
    return candidate,{'family':family,'policy_sha256':POLICY_SHA256,'mapping':mapping,'mapping_used':used,
        'alpha_counts':alpha_counts,'resource_literals':resources,'resource_counts':resource_counts,
        'alpha_saved_bytes':alpha_saved,'resource_saved_bytes':resource_saved,'source_saved_bytes':len(data)-len(candidate),
        'source_edits_count':sum(counts.values()),'retained_directive_bytes':directive_bytes,'opaque_regions_preserved':len(opaque),
        'independent_opaque_and_rewrite_checks':True,'source_only_proof':True,'native_or_package_gate_executed':False}
