"""One literal new source domain, with the unchanged original A31/storage18 maps."""
from collections import Counter
import hashlib
import json
from pathlib import Path

PIN = '0fd239be0d5e98c866a78cd41da3a108ff725ed0d010fb96ca61fecc8657fafd'


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def binding(data, pin, label):
    require(len(data) == pin['bytes'] and sha(data) == pin['sha256'], label + ' exact identity differs')


def transform(source, readable, *, alpha, storage, lexer):
    raw = Path(__file__).with_name('candidate-domain.json').read_bytes()
    require(sha(raw) == PIN, 'literal candidate domain changed')
    domain = json.loads(raw)
    binding(readable, domain['readable'], 'candidate readable')
    require(sha(alpha.POLICY_BYTES) == domain['original_alpha_policy_sha256'] and
            sha(storage._POLICY_BYTES) == domain['original_storage_policy_sha256'], 'original policy drift')
    af, sf = json.loads(alpha.POLICY_BYTES), json.loads(storage._POLICY_BYTES)
    require(len(af['mapping']) == 31 and af['resource_literals'] == {'WORKERS': '2', 'TT_BITS': '18'} and
            len(sf['mapping']) == 18 and sf['resource_literals'] == {} and sf['numeric_inverse_replacements'] == 0,
            'original mapping/resource shape changed')
    for fixed in (af, sf):
        require(sorted(fixed['mapping']) == fixed['allowed_shipping_names'] and
                not (set(fixed['mapping']) & set(fixed['protected_shipping_names'])), 'original protected boundary changed')
    reserved_bytes = ('\n'.join(sorted(storage._READABLE_RESERVED)) + '\n').encode()
    require(sha(reserved_bytes) == storage._READABLE_RESERVED_SHA256, 'original reservation union changed')
    words = set(alpha._WORD.findall(readable.decode())) | set(alpha._WORD.findall(alpha._logical(readable.decode())[0]))
    require(sorted(words - storage._READABLE_RESERVED) == domain['new_readable_words'], 'new readable word domain changed')
    aliases = set(af['mapping'].values()) | set(sf['mapping'].values())
    require(not aliases.intersection(words | storage._READABLE_RESERVED), 'alias capture in candidate readable/old union')
    require('PLY' not in af['mapping'] and 'PLY' not in af['resource_literals'] and 'PLY' not in sf['mapping'],
            'PLY substitution forbidden')
    metadata = []
    for name, fixed, module in (('alpha', af, alpha), ('storage', sf, storage)):
        row = domain[name]
        binding(source, row['source'], name + ' input')
        substitutions = {**fixed['mapping'], **fixed['resource_literals']}
        if name == 'alpha':
            result, counts, opaque = module._rewrite(source, substitutions, lexer=lexer)
            spans = lexer._identifier_spans
        else:
            result, counts, opaque = module._rewrite(source, substitutions)
            spans = storage._identifier_spans
        observed = {'alpha_counts': {n: counts[n] for n in fixed['mapping']},
                    'resource_counts': {n: counts[n] for n in fixed['resource_literals']},
                    'mapping_used': sum(counts[n] > 0 for n in fixed['mapping']),
                    'source_edits_count': sum(counts.values()),
                    'alpha_saved_bytes': sum((len(n)-len(v))*counts[n] for n, v in fixed['mapping'].items()),
                    'resource_saved_bytes': sum((len(n)-len(v))*counts[n] for n, v in fixed['resource_literals'].items()),
                    'source_saved_bytes': len(source)-len(result),
                    'retained_directive_bytes': sum(len(t.encode()) for k, t in opaque if k == 'directive'),
                    'opaque_regions_preserved': len(opaque),
                    'preserved_PLY_code_uses': sum(t == 'PLY' for _, _, t in spans(source.decode()))}
        require(all(observed[key] == row[key] for key in observed), name + ' literal counts/arithmetic differ')
        require(observed['preserved_PLY_code_uses'] == 8 and
                sum(t == 'PLY' for _, _, t in spans(result.decode())) == 8, 'PLY uses changed')
        binding(result, row['candidate'], name + ' output')
        metadata.append({'stage': name, **observed, 'original_maps_unchanged': True,
                         'independent_opaque_and_rewrite_checks': True})
        source = result
    return source, metadata
