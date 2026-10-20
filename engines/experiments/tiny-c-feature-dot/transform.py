"""One exact C shipping SIMD representation; no generic model/name rewrite."""
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


def transform(canonical, shipping, recipe, tokens, keywords):
    if sha(canonical) != recipe['canonical_sha256'] or sha(shipping) != recipe['control']['source']['sha256']:
        raise ValueError('exact current C canonical/shipping inputs required')
    if b'\r' in canonical or b'\r' in shipping:
        raise ValueError('LF input required')
    rule=recipe['rules'][0]
    witness=rule['canonical_before'].encode()
    for span in recipe['DEV_witness_spans']:
        span=span.encode()
        if witness.count(span)!=1:raise ValueError('known literal DEV witness changed')
        witness=witness.replace(span,b'')
    if witness!=rule['active_before'].encode():raise ValueError('readable shipping witness changed')
    correspondence=dict(rule,canonical_before=rule['active_before'],canonical_after=rule['active_after'])
    bindings=paired_bindings([correspondence],tokens,keywords)
    readable,r=apply(canonical,recipe['rules'],'canonical')
    candidate,s=apply(shipping,recipe['rules'],'shipping')
    expected=recipe['candidate']
    if len(readable)!=expected['readable_bytes'] or sha(readable)!=expected['readable_sha256'] or len(candidate)!=expected['source_bytes'] or sha(candidate)!=expected['source_sha256']:
        raise ValueError('fixed candidate identity differs')
    return readable,candidate,{'canonical':r,'shipping':s,'paired_roles':bindings,'DEV_original_block_preserved':True,'literal_DEV_witness_spans':len(recipe['DEV_witness_spans']),'C_preprocessor_or_AST':False,'unchanged_board_put_search':True}
