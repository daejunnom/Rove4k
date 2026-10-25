"""One new literal C composition count domain; original89 spelling map only."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
POLICY_SHA256='9ac6fdd907a114d6748268c5777e5ee3fa54a53ce56ae07bd1d7fae37d1202c5'
POLICY_BYTES=(HERE/'policy.json').read_bytes()
if hashlib.sha256(POLICY_BYTES).hexdigest()!=POLICY_SHA256:raise ValueError('literal candidate policy changed')

def transform_source(data,*,lexer,readable):
    spec=importlib.util.spec_from_file_location('composition_reference_alpha',HERE/'control/engines/scripts/fixed_shipping_alpha.py')
    reference=importlib.util.module_from_spec(spec);spec.loader.exec_module(reference)
    original=json.loads(reference._POLICY_BYTES);fixed=json.loads(POLICY_BYTES)
    if reference._POLICY_SHA256!=fixed['original_policy_sha256'] or fixed['mapping']!=original['mapping']:
        raise ValueError('original89 alias map changed')
    mapping=fixed['mapping'];resources=fixed['resource_literals']
    if len(mapping)!=89 or resources!={'TT_BITS':'18','WORKERS':'2'} or fixed['symbol_bearing_spellings_retained']!=original['symbol_bearing_spellings_retained']:
        raise ValueError('original default-deny resource/symbol boundary changed')
    if set(mapping)&set(fixed['symbol_bearing_spellings_retained']):raise ValueError('symbol-bearing old name admitted')
    if hashlib.sha256(readable).hexdigest()!='15999279c5bd4690db7129bda032c6b5962acbd814236719cda40755ae31794b':
        raise ValueError('unknown sole candidate readable')
    aliases=set(mapping.values())
    reserved=set(reference._WORD.findall(readable.decode()))|set(reference._WORD.findall(reference._logical(readable.decode())[0]))
    if aliases&reserved:raise ValueError('fixed alias occurs in candidate readable')
    reference._binding(data,fixed['source'],'new composition shipping before alpha')
    candidate,counts,opaque=reference._rewrite(data,{**mapping,**resources},lexer=lexer)
    alpha_counts={name:counts[name] for name in mapping};resource_counts={name:counts[name] for name in resources}
    alpha_saved=sum((len(name)-len(mapping[name]))*count for name,count in alpha_counts.items())
    resource_saved=sum((len(name)-len(resources[name]))*count for name,count in resource_counts.items())
    ply=sum(token=='PLY' for _,_,token in lexer._identifier_spans(data.decode()))
    if (alpha_counts!=fixed['alpha_counts'] or resource_counts!=fixed['resource_counts']
        or alpha_saved!=fixed['alpha_saved_bytes'] or resource_saved!=fixed['resource_saved_bytes']
        or len(data)-len(candidate)!=fixed['source_saved_bytes'] or sum(counts.values())!=fixed['source_edits_count']
        or sum(v>0 for v in alpha_counts.values())!=fixed['mapping_used'] or ply!=fixed['retained_PLY_code_uses']
        or len(opaque)!=fixed['opaque_regions_preserved']
        or sum(len(raw.encode()) for kind,raw in opaque if kind=='directive')!=fixed['retained_directive_bytes']):
        raise ValueError('new literal candidate count/domain mismatch')
    if sum(token=='PLY' for _,_,token in lexer._identifier_spans(candidate.decode()))!=ply:raise ValueError('PLY code uses changed')
    reference._binding(candidate,fixed['candidate'],'sole C composition alpha result')
    return candidate,{'policy_sha256':POLICY_SHA256,'original89_mapping_unchanged':True,'alpha_counts':alpha_counts,
        'resource_counts':resource_counts,'source_saved_bytes':len(data)-len(candidate),'source_edits_count':sum(counts.values()),
        'retained_PLY_code_uses':ply,'opaque_regions_preserved':len(opaque),'independent_rewrite_opaque_checks':True}
