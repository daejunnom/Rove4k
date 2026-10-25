"""Candidate-specific literal domain; the frozen public policies stay unchanged."""
from collections import Counter
import json
from pathlib import Path
import sys
sys.dont_write_bytecode=True
from tools import module,sha

POLICY_SHA256='749133a23382dbaaf74fdd46e80d3b3c963688430502e14e84d0d63832870a04'
def require(value,label):
    if not value:raise ValueError(label)
def binding(raw,row,label):
    require(isinstance(raw,bytes) and len(raw)==row['bytes'] and sha(raw)==row['sha256'],label)
def transform(data,readable,root):
    root=Path(root);raw=(root/'policy.json').read_bytes()
    require(sha(raw)==POLICY_SHA256,'fixed candidate literal policy changed');fixed=json.loads(raw)
    require(fixed['format']==1 and fixed['family']=='F','F-only policy')
    a=module('F_frozen_alpha_generic',root/'control/engines/compact/tiny-entry-f/shipping_alpha.py')
    s=module('F_frozen_storage_generic',root/'control/engines/scripts/fixed_shipping_storage.py')
    lexer=module('F_frozen_lexer',root/'control/engines/scripts/rename_c.py')
    af=json.loads(a.POLICY_BYTES);sf=json.loads(s._POLICY_BYTES)
    require(a.POLICY_SHA256==fixed['baseline_alpha_policy_sha256'] and sha(a.POLICY_BYTES)==a.POLICY_SHA256,'original alpha policy changed')
    require(s._POLICY_SHA256==fixed['baseline_storage_policy_sha256'] and sha(s._POLICY_BYTES)==s._POLICY_SHA256,'original storage policy changed')
    amap=fixed['alpha_mapping'];resources=fixed['alpha_resources'];smap=fixed['storage_mapping']
    require(amap==af['mapping'] and resources==af['resource_literals'] and smap==sf['mapping'],'same exact original spelling maps required')
    require(len(amap)==73 and sorted(amap)==af['allowed_shipping_names'] and not set(amap)&set(af['protected_shipping_names']),'alpha default-deny/protection')
    require(len(smap)==18 and sorted(smap)==sf['allowed_shipping_names'] and not set(smap)&set(sf['protected_shipping_names']),'storage default-deny/protection')
    require(resources=={'WORKERS':'2','TT_BITS':'18','PLY':'128'} and not sf['resource_literals'] and sf['numeric_inverse_replacements']==0,'resource boundary')
    require(all(len(old)>2 and a._IDENTIFIER.fullmatch(new) and len(new)==2 for old,new in amap.items()),'alpha alias shape')
    require(all(len(old)>2 and s.re.fullmatch(r'q[a-r]',new) for old,new in smap.items()),'storage alias shape')
    require(len(set(amap.values()))==73 and len(set(smap.values()))==18 and not set(amap.values())&set(smap.values()),'injective separate aliases')
    binding(readable,fixed['readable'],'candidate canonical readable identity')
    own_words=set(a._WORD.findall(readable.decode()))|set(a._WORD.findall(a._logical(readable.decode())[0]))
    require(not set(amap.values())&own_words,'alpha readable freshness')
    reserved=('\n'.join(sorted(s._READABLE_RESERVED))+'\n').encode()
    require(sha(reserved)==s._READABLE_RESERVED_SHA256 and own_words.issubset(s._READABLE_RESERVED),'unchanged embedded readable union')
    require(not set(smap.values())&(s._READABLE_RESERVED|own_words),'storage readable freshness')
    original=sha(data);rows=[]
    for kind,mapping,numbers in (('alpha',amap,resources),('storage',smap,{})):
        row=fixed[kind];binding(data,row['source'],kind+' exact input')
        if kind=='alpha':candidate,counts,opaque=a._rewrite(data,{**mapping,**numbers},lexer=lexer)
        else:candidate,counts,opaque=s._rewrite(data,mapping)
        actual={'source':row['source'],'candidate':row['candidate'],
          'alpha_counts':{old:counts[old] for old in mapping},'resource_counts':{old:counts[old] for old in numbers},
          'mapping_used':sum(counts[old]>0 for old in mapping),
          'alpha_saved_bytes':sum((len(old)-len(new))*counts[old] for old,new in mapping.items()),
          'resource_saved_bytes':sum((len(old)-len(new))*counts[old] for old,new in numbers.items()),
          'source_saved_bytes':len(data)-len(candidate),'source_edits_count':sum(counts.values()),
          'retained_directive_bytes':sum(len(part.encode()) for part_type,part in opaque if part_type=='directive'),
          'opaque_regions_preserved':len(opaque)}
        require(actual==row,kind+' literal counts/arithmetic/opaque domain')
        binding(candidate,row['candidate'],kind+' exact output')
        require(not any(actual['resource_counts'].values()),'numeric inverse is forbidden')
        if kind=='storage':
            before=sum(token=='PLY' for _,_,token in s._identifier_spans(data.decode()))
            after=sum(token=='PLY' for _,_,token in s._identifier_spans(candidate.decode()))
            require(before==after==fixed['preserved_PLY_code_uses'],'PLY uses preserved')
        rows.append({'stage':kind,**actual});data=candidate
    return data,{'policy_sha256':POLICY_SHA256,'same_alpha73_and_storage18_maps':True,
        'original_public_transforms_called':False,'original_input_sha256':original,
        'F_only_current_readable_freshness':True,'original_storage_reservation_union_preserved':True,
        'independent_opaque_and_lexer_rewrite_checks':True,'stages':rows}, {**amap,**smap}
