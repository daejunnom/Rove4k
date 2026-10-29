"""One literal18 same-TU storage spelling policy; no alias discovery or retry."""
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
POLICY_SHA256='1256f5017753b43a3fd78a16bdc766a21b86f19ebf400ad61d72a35c4169a84d'
POLICY_BYTES=(HERE/'policy.json').read_bytes()
if hashlib.sha256(POLICY_BYTES).hexdigest()!=POLICY_SHA256:raise ValueError('reviewed literal storage policy changed')
_spec=importlib.util.spec_from_file_location('bce_reference_opaque',HERE/'reference/policy.py')
reference=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(reference)


def sha(data):return hashlib.sha256(data).hexdigest()


def binding(data,pin,label):
    if len(data)!=pin['bytes'] or sha(data)!=pin['sha256']:raise ValueError(label+' exact bytes changed')


def transform_source(data,*,family,lexer):
    fixed=json.loads(POLICY_BYTES)
    if family not in ('B','C','E'):raise ValueError('unknown fixed BCE family')
    row=fixed['families'][family];binding(data,row['source'],family+' baseline final shipping source')
    mapping=fixed['mapping'];resources=fixed['resource_literals']
    if resources or len(mapping)!=18:raise ValueError('fixed18 object-only policy changed')
    if sorted(mapping)!=fixed['allowed_shipping_names'] or set(mapping)&set(fixed['protected_shipping_names']):
        raise ValueError('protected or unaudited old spelling admitted')
    if any(len(old)<=2 or not re.fullmatch(r'q[a-r]',new) for old,new in mapping.items()):
        raise ValueError('unexpected alias rule')
    aliases=set(mapping.values())
    if len(aliases)!=18:raise ValueError('noninjective fixed storage aliases')
    for name,pin in fixed['readable_inputs'].items():
        raw=(HERE/'control'/name).read_bytes().replace(b'\r\n',b'\n');binding(raw,pin,'readable reserved words')
        reserved=set(reference._WORD.findall(raw.decode()))|set(reference._WORD.findall(reference._logical(raw.decode())[0]))
        if aliases&reserved:raise ValueError('alias occurs in frozen readable source')
    substitutions={**mapping,**resources}
    before=sha(data);candidate,counts,opaque=reference._rewrite(data,substitutions,lexer=lexer)
    alpha_counts={old:counts[old] for old in mapping};resource_counts={old:counts[old] for old in resources}
    if alpha_counts!=row['alpha_counts'] or resource_counts:
        raise ValueError('literal storage token occurrence counts changed')
    alpha_saved=sum((len(old)-len(new))*counts[old] for old,new in mapping.items())
    resource_saved=sum((len(old)-len(new))*counts[old] for old,new in resources.items())
    directive_bytes=sum(len(raw.encode()) for kind,raw in opaque if kind=='directive')
    used=sum(counts[old]>0 for old in mapping)
    if (alpha_saved!=row['alpha_saved_bytes'] or resource_saved!=0
            or len(data)-len(candidate)!=row['source_saved_bytes'] or used!=row['mapping_used']
            or sum(counts.values())!=row['source_edits_count'] or directive_bytes!=row['retained_directive_bytes']
            or len(opaque)!=row['opaque_regions_preserved']):
        raise ValueError('literal storage arithmetic or opaque count changed')
    ply_before=sum(token=='PLY' for _,_,token in lexer._identifier_spans(data.decode()))
    ply_after=sum(token=='PLY' for _,_,token in lexer._identifier_spans(candidate.decode()))
    if ply_before!=row['preserved_PLY_code_uses'] or ply_after!=ply_before:raise ValueError('PLY code uses changed')
    binding(candidate,row['candidate'],family+' sole storage candidate')
    if sha(data)!=before:raise ValueError('source mutated')
    return candidate,{'family':family,'policy_sha256':POLICY_SHA256,'mapping':mapping,'mapping_used':used,
        'alpha_counts':alpha_counts,'resource_literals':resources,'resource_counts':resource_counts,
        'alpha_saved_bytes':alpha_saved,'resource_saved_bytes':resource_saved,'source_saved_bytes':len(data)-len(candidate),
        'source_edits_count':sum(counts.values()),'retained_directive_bytes':directive_bytes,'opaque_regions_preserved':len(opaque),
        'preserved_PLY_code_uses':ply_after,'prior_BCE89_decisions_unchanged':True,
        'independent_opaque_and_rewrite_checks':True,'source_only_proof':True,'native_or_package_gate_executed':False}
