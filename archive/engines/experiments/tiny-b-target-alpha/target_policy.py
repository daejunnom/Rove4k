"""Exact-target adapter; the original three-family alpha policy is unchanged."""
from collections import Counter
import hashlib
import json
from pathlib import Path

PIN = '055078a3751316a5cc489e5fda7c3cf57b34599896c0adfb431858184001c838'


def transform(data, *, original, lexer):
    raw = Path(__file__).with_name('target-policy.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != PIN:
        raise ValueError('literal target policy changed')
    fixed = json.loads(raw)
    original_raw = original._POLICY_BYTES
    if hashlib.sha256(original_raw).hexdigest() != fixed['original_policy_sha256']:
        raise ValueError('original policy differs')
    policy = json.loads(original_raw)
    if len(policy['mapping']) != 89 or policy['resource_literals'] != {'WORKERS': '2', 'TT_BITS': '18'}:
        raise ValueError('original mapping/resources differ')
    original._binding(data, fixed['source'], 'exact target source')
    substitutions = {**policy['mapping'], **policy['resource_literals']}
    candidate, counts, opaque = original._rewrite(data, substitutions, lexer=lexer)
    if {name: counts[name] for name in policy['mapping']} != fixed['alpha_counts']:
        raise ValueError('target alpha occurrence drift')
    if {name: counts[name] for name in policy['resource_literals']} != fixed['resource_counts']:
        raise ValueError('target resource occurrence drift')
    tokens = Counter(t for _, _, t in lexer._identifier_spans(data.decode()))
    if tokens['PLY'] != fixed['retained_PLY_count']:
        raise ValueError('target PLY count drift')
    for name, row in fixed['new_identifiers'].items():
        if name in substitutions or tokens[name] != row['occurrences']:
            raise ValueError('new target identifier drift: ' + name)
    alpha_saved = sum((len(old)-len(new))*counts[old] for old, new in policy['mapping'].items())
    resource_saved = sum((len(old)-len(new))*counts[old] for old, new in policy['resource_literals'].items())
    observed = {'mapping_used': sum(counts[n] > 0 for n in policy['mapping']),
                'source_edits_count': sum(counts.values()), 'alpha_saved_bytes': alpha_saved,
                'resource_saved_bytes': resource_saved, 'total_saved_bytes': len(data)-len(candidate),
                'retained_directive_bytes': sum(len(v.encode()) for k, v in opaque if k == 'directive')}
    if any(observed[key] != fixed[key] for key in observed):
        raise ValueError('target arithmetic/opaque policy drift')
    original._binding(candidate, fixed['candidate'], 'literal target alpha output')
    return candidate, {'policy_sha256': PIN, **observed, 'opaque_regions_preserved': len(opaque),
                       'new_identifier_spellings_retained': fixed['new_identifiers'],
                       'original_policy_unchanged': True, 'compiler_header_native_gates': False}
