"""Literal E-only composition domain; the shared fixed89 gate stays intact."""
from collections import Counter
import hashlib
import json

def sha(data):return hashlib.sha256(data).hexdigest()
def need(v,m):
    if not v:raise ValueError(m)

def observe(data,reference,lexer):
    policy=json.loads(reference._POLICY_BYTES)
    need(len(policy['mapping'])==89 and policy['resource_literals']=={'TT_BITS':'18','WORKERS':'2'},'old map/resource drift')
    logical=reference._logical(data.decode())[0]
    reserved=set(reference._WORD.findall(data.decode()))|set(reference._WORD.findall(logical))
    need(not set(policy['mapping'].values())&reserved,'alias already in canonical input')
    result,counts,opaque=reference._rewrite(data,{**policy['mapping'],**policy['resource_literals']},lexer=lexer)
    observed={'alpha_counts':{n:counts[n]for n in policy['mapping']},
        'resource_counts':{n:counts[n]for n in policy['resource_literals']},
        'mapping_used':sum(counts[n]>0 for n in policy['mapping']),
        'source_edits_count':sum(counts.values()),
        'alpha_saved_bytes':sum((len(n)-len(v))*counts[n]for n,v in policy['mapping'].items()),
        'resource_saved_bytes':sum((len(n)-len(v))*counts[n]for n,v in policy['resource_literals'].items()),
        'total_saved_bytes':len(data)-len(result),
        'retained_PLY_count':Counter(t for _,_,t in lexer._identifier_spans(data.decode()))['PLY'],
        'retained_directive_bytes':sum(len(v.encode())for k,v in opaque if k=='directive'),
        'opaque_regions':len(opaque)}
    return result,observed,policy['mapping']

def transform_source(data,recipe,reference,lexer):
    fixed=recipe['candidate_admission']
    need(sha(reference._POLICY_BYTES)==recipe['fixed_policy_sha256'],'fixed policy bytes changed')
    need(len(data)==fixed['pre_alpha_bytes']and sha(data)==fixed['pre_alpha_sha256'],'unknown E pre-alpha input')
    result,observed,mapping=observe(data,reference,lexer)
    need(observed==fixed['alpha'],'E literal count/opaque domain mismatch')
    need(len(result)==fixed['alpha_bytes']and sha(result)==fixed['alpha_sha256'],'E literal alpha result mismatch')
    return result,{'literal_domain':fixed,'original89_map_unchanged':True,'shared_admission_broadened':False},mapping
