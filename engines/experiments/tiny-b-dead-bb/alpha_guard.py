"""One literal B dead-bb input with unchanged fixed89 map; old gate is untouched."""
from collections import Counter
import hashlib
import json

def sha(data):return hashlib.sha256(data).hexdigest()
def need(value,message):
    if not value:raise ValueError(message)

def transform_source(data,recipe,original,lexer):
    expected=recipe['candidate_admission']
    need(isinstance(data,bytes) and len(data)==expected['pre_alpha_bytes'] and
         sha(data)==expected['pre_alpha_sha256'],'unknown dead-bb pre-alpha input')
    policy=json.loads(original._POLICY_BYTES)
    need(sha(original._POLICY_BYTES)==recipe['fixed_policy_sha256'] and
         len(policy['mapping'])==89 and policy['resource_literals']=={'TT_BITS':'18','WORKERS':'2'},
         'fixed mapping/resource policy drift')
    counts_expected=dict(policy['families']['B']['alpha_counts'])
    counts_expected.update(colors=0,knights=0,minors=0)
    need(expected['alpha']['alpha_counts']==counts_expected,'candidate count literals differ')
    substitutions={**policy['mapping'],**policy['resource_literals']}
    candidate,counts,opaque=original._rewrite(data,substitutions,lexer=lexer)
    actual={name:counts[name]for name in policy['mapping']}
    resources={name:counts[name]for name in policy['resource_literals']}
    source_counts=Counter(t for _,_,t in lexer._identifier_spans(data.decode()))
    observed={'alpha_counts':actual,'resource_counts':resources,
        'mapping_used':sum(counts[n]>0 for n in policy['mapping']),
        'source_edits_count':sum(counts.values()),
        'alpha_saved_bytes':sum((len(n)-len(v))*counts[n]for n,v in policy['mapping'].items()),
        'resource_saved_bytes':sum((len(n)-len(v))*counts[n]for n,v in policy['resource_literals'].items()),
        'total_saved_bytes':len(data)-len(candidate),'retained_PLY_count':source_counts['PLY'],
        'retained_directive_bytes':sum(len(v.encode())for k,v in opaque if k=='directive'),
        'opaque_regions':len(opaque)}
    need(observed==expected['alpha'],'literal candidate token/opaque arithmetic mismatch')
    need(len(candidate)==expected['alpha_bytes'] and sha(candidate)==expected['alpha_sha256'],
         'literal candidate alpha result mismatch')
    return candidate,{'class':recipe['class'],'original_helper_admission_broadened':False,
        'fixed_mapping_sha256':recipe['fixed_policy_sha256'],'counts':observed,
        'lexical_only_not_material_or_runtime_proof':True}
