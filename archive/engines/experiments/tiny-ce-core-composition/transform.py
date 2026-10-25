"""Paired literal core edits; retain the already qualified shipping spellings."""
import hashlib
import re


def sha(data):
    return hashlib.sha256(data).hexdigest()


def apply(source, rules, view):
    edits = []
    for rule in rules:
        old, new = rule[view+'_before'].encode(), rule[view+'_after'].encode()
        if not old or source.count(old) != 1:
            raise ValueError('sole exact '+view+' fragment missing: '+rule['label'])
        start = source.index(old)
        edits.append((start, start+len(old), new, rule['label']))
    edits.sort();parts = [];complement = [];position = 0;new_position = 0;rows = []
    for start, end, replacement, label in edits:
        if start < position:
            raise ValueError('overlapping edit')
        gap = source[position:start];parts.extend((gap, replacement));complement.append(gap)
        new_position += len(gap)
        rows.append({'label': label, 'old_offset': start, 'old_bytes': end-start,
                     'new_offset': new_position, 'new_bytes': len(replacement),
                     'before_sha256': sha(source[start:end]), 'after_sha256': sha(replacement)})
        new_position += len(replacement);position = end
    parts.append(source[position:]);complement.append(source[position:]);candidate = b''.join(parts)
    inverse = [];candidate_complement = [];position = 0
    for row in rows:
        start = row['new_offset'];end = start+row['new_bytes'];old = row['old_offset']
        inverse.extend((candidate[position:start], source[old:old+row['old_bytes']]))
        candidate_complement.append(candidate[position:start]);position = end
        if sha(candidate[start:end]) != row['after_sha256']:
            raise ValueError('candidate edit extent differs')
    inverse.append(candidate[position:]);candidate_complement.append(candidate[position:])
    if b''.join(inverse) != source or complement != candidate_complement:
        raise ValueError('position inverse or protected complement differs')
    return candidate, {'input_bytes': len(source), 'input_sha256': sha(source),
        'output_bytes': len(candidate), 'output_sha256': sha(candidate), 'edits': rows,
        'position_inverse_exact': True, 'protected_complement_exact': True,
        'protected_complement_bytes': sum(map(len, complement)),
        'protected_complement_sha256': sha(b''.join(complement))}


def paired_bindings(rules, tokens, keywords):
    """Use the pinned existing C lexer, not a new parser, AST or name allocator."""
    identifier = re.compile(r'[A-Za-z_][A-Za-z_0-9]*\Z')
    report = []
    for rule in rules:
        correspondence = {};rows = []
        for phase in ('before', 'after'):
            readable = list(tokens(rule['canonical_'+phase], 'c'))
            shipping = list(tokens(rule['shipping_'+phase], 'c'))
            if len(readable) != len(shipping):
                raise ValueError('paired token arity differs: '+rule['label'])
            edges = []
            for index, (left, right) in enumerate(zip(readable, shipping)):
                if left == right:
                    continue
                if not identifier.fullmatch(left) or not identifier.fullmatch(right) or left in keywords or right in keywords:
                    raise ValueError('nonidentifier spelling change in paired edit')
                member = index > 0 and readable[index-1] == '->'
                role = (left, member)
                if phase == 'before':
                    if role in correspondence and correspondence[role] != right:
                        raise ValueError('ambiguous identifier role inside paired edit')
                    correspondence[role] = right
                elif correspondence.get(role) != right:
                    raise ValueError('new/different identifier spelling in candidate')
                edges.append({'token_index': index, 'canonical': left, 'shipping': right,
                              'member': member})
            rows.append({'phase': phase, 'token_count': len(readable), 'existing_spelling_edges': edges})
        report.append({'label': rule['label'], 'phases': rows,
                       'operators_literals_and_keywords_unchanged_between_views': True})
    return report


def transform(canonical, shipping, family_recipe, tokens, keywords):
    if sha(canonical) != family_recipe['canonical_sha256'] or sha(shipping) != family_recipe['expected']['source_sha256']:
        raise ValueError('exact current canonical/shipping input required')
    if b'\r' in canonical or b'\r' in shipping:
        raise ValueError('LF input required')
    bindings = paired_bindings(family_recipe['rules'], tokens, keywords)
    readable, readable_receipt = apply(canonical, family_recipe['rules'], 'canonical')
    packed, packed_receipt = apply(shipping, family_recipe['rules'], 'shipping')
    if sha(readable) != family_recipe['candidate_canonical_sha256'] or sha(packed) != family_recipe['candidate_shipping_sha256']:
        raise ValueError('fixed combined candidate differs')
    return readable, packed, {'canonical': readable_receipt, 'shipping': packed_receipt,
        'paired_existing_identifier_bindings': bindings, 'new_names_allocated': 0,
        'existing_public_alpha_scope_guards_modified': False, 'C_AST_runs': 0,
        'query_startup_reset_source_complement_preserved': True,
        'domain': family_recipe['semantic_domain'], 'runtime_equivalence_not_yet_qualified': True}
