"""One B-only count/domain adapter; original public policies remain frozen."""
import json
from pathlib import Path
import sys
sys.dont_write_bytecode=True
from cost_tools import module,sha
POLICY_SHA256='c3a7c7ba51526b4ed1a16fa55adbdefadaa72219473fe8aa9099c16dfc94bac5'
def require(value,label):
    if not value:raise ValueError(label)
def binding(raw,row,label):
    require(isinstance(raw,bytes) and len(raw)==row['bytes'] and sha(raw)==row['sha256'],label)
def transform(data,readable,root):
    root=Path(root);raw=(root/'cost-policy.json').read_bytes()
    require(sha(raw)==POLICY_SHA256,'sole B literal domain changed');fixed=json.loads(raw)
    require(fixed['format']==1 and fixed['family']=='B','B-only literal domain')
    a=module('B_core_frozen_shared89',root/'normal/engines/scripts/fixed_shipping_alpha.py')
    s=module('B_core_frozen_storage18',root/'normal/engines/compact/tiny-entry-b/shipping_storage.py')
    lexer=module('B_core_frozen_lexer',root/'normal/engines/scripts/rename_c.py')
    af=json.loads(a._POLICY_BYTES);sf=json.loads(s._POLICY_BYTES)
    require(sha(a._POLICY_BYTES)==a._POLICY_SHA256==fixed['baseline_alpha_policy_sha256'],'original shared89 literal policy')
    require(sha(s._POLICY_BYTES)==s._POLICY_SHA256==fixed['baseline_storage_policy_sha256'],'original B storage literal policy')
    mapping=fixed['alpha_mapping'];resources=fixed['alpha_resources'];storage=fixed['storage_mapping']
    require(mapping==af['mapping'] and resources==af['resource_literals'] and storage==sf['mapping'],'exact original maps/resources')
    require(len(mapping)==89 and len(set(mapping.values()))==89 and resources=={'WORKERS':'2','TT_BITS':'18'},'shared89 shape')
    require(not set(mapping)&set(resources) and not set(mapping)&set(af['symbol_bearing_spellings_retained']),'retained function/symbol decisions')
    require(len(storage)==18 and len(set(storage.values()))==18 and not set(storage)&set(sf['protected_shipping_names']),'storage18 protection')
    require(not set(mapping.values())&set(storage.values()),'separate injective alias sets')
    binding(readable,fixed['readable'],'exact B canonical candidate')
    words=set(a._WORD.findall(readable.decode()))|set(a._WORD.findall(a._logical(readable.decode())[0]))
    require(not words&(set(mapping.values())|set(storage.values())),'B raw/phase2 readable alias freshness')
    original=sha(data);rows=[]
    for kind,names,numbers in (('alpha',mapping,resources),('storage',storage,{})):
        expected=fixed[kind];binding(data,expected['source'],kind+' exact input')
        candidate,counts,opaque=a._rewrite(data,{**names,**numbers},lexer=lexer)
        ply=sum(token=='PLY' for _,_,token in lexer._identifier_spans(data.decode()))
        actual={'source':expected['source'],'candidate':expected['candidate'],
            'alpha_counts':{old:counts[old] for old in names},'resource_counts':{old:counts[old] for old in numbers},
            'mapping_used':sum(counts[old]>0 for old in names),
            'alpha_saved_bytes':sum((len(old)-len(new))*counts[old] for old,new in names.items()),
            'resource_saved_bytes':sum((len(old)-len(new))*counts[old] for old,new in numbers.items()),
            'source_saved_bytes':len(data)-len(candidate),'source_edits_count':sum(counts.values()),
            'retained_directive_bytes':sum(len(part.encode()) for part_type,part in opaque if part_type=='directive'),
            'opaque_regions_preserved':len(opaque),'preserved_PLY_code_uses':ply}
        require(actual==expected,kind+' literal count/arithmetic/opaque domain')
        require(ply==9==sum(token=='PLY' for _,_,token in lexer._identifier_spans(candidate.decode())),'PLY9 preserved')
        binding(candidate,expected['candidate'],kind+' exact output')
        rows.append({'stage':kind,**actual});data=candidate
    return data,{'policy_sha256':POLICY_SHA256,'exact_original89_and18_maps':True,
        'original_public_transforms_called':False,'original_input_sha256':original,'readable_raw_phase2_freshness':True,
        'independent_opaque_and_lexer_rewrite_checks':True,'old_native_identity_required':False,'stages':rows}, {**mapping,**storage}
