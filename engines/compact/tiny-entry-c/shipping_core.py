"""One exact shipping-only core composition after the fixed spelling stages.

Ordinary local literals own both canonical/readable and final shipping edits.
No engine/parser/model/PLY generalization, new identifiers, external receipts,
or generated artifacts are consumed. DEV never enters this stage.
"""
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


PROFILE = {'workers': 2, 'tt_bits': 18, 'ply': 128, 'dev_default': False}
FIXED = {'canonical_sha256': '15999279c5bd4690db7129bda032c6b5962acbd814236719cda40755ae31794b', 'candidate_canonical_sha256': 'e523b22bf0e0a9a8b0e729ea1f8fe0c7e5512ab8f6b5d6a0d8805cf0fa92b5f1', 'candidate_shipping_sha256': '68ad43dec85adcfff6e65bba0f457738e33ff545d786d43c3c3a7b53e618f02c', 'rules': [{'label': 'TT probe two-argument signature', 'canonical_before': 'probe(uint64_t key,int write,uint64_t data)', 'canonical_after': 'probe(uint64_t key,uint64_t data)', 'shipping_before': 'J(uint64_t a,int d,uint64_t f)', 'shipping_after': 'J(uint64_t a,uint64_t f)'}, {'label': 'nonzero store sentinel', 'canonical_before': 'if(write)e->key=key,e->data=data;', 'canonical_after': 'if(data)e->key=key,e->data=data;', 'shipping_before': 'if(d)e->zP=a,e->zA=f;', 'shipping_after': 'if(f)e->zP=a,e->zA=f;'}, {'label': 'TT read caller', 'canonical_before': 'data=probe(key,0,0);', 'canonical_after': 'data=probe(key,0);', 'shipping_before': 'zA=J(zP,0,0);', 'shipping_after': 'zA=J(zP,0);'}, {'label': 'TT write caller', 'canonical_before': 'probe(key,1,data);return best;', 'canonical_after': 'probe(key,data);return best;', 'shipping_before': 'J(zP,1,zA);return zi;', 'shipping_after': 'J(zP,zA);return zi;'}, {'label': 'consumed selection prefix', 'canonical_before': '        Move m=moves[j];moves[j]=moves[i];moves[i]=m;\n        int t=scores[j];scores[j]=scores[i];scores[i]=t;\n', 'canonical_after': '        Move m=moves[j];moves[j]=moves[i];scores[j]=scores[i];\n', 'shipping_before': 'Move m=B[j];B[j]=B[i];B[i]=m;int t=L[j];L[j]=L[i];L[i]=t;', 'shipping_after': 'Move m=B[j];B[j]=B[i];L[j]=L[i];'}, {'label': 'inactive outer evaluation clamp', 'canonical_before': '    if(evaluation>MATE-PLY-1)evaluation=MATE-PLY-1;\n    if(evaluation< -MATE+PLY+1)evaluation=-MATE+PLY+1;\n', 'canonical_after': '', 'shipping_before': 'if(zF>MATE-PLY-1)zF=MATE-PLY-1;if(zF< -MATE+PLY+1)zF=-MATE+PLY+1;', 'shipping_after': ''}, {'label': 'zero-order function', 'canonical_before': 'static int tiny_order(const Board *p,Move m){(void)p;(void)m;return 0;}\n', 'canonical_after': '', 'shipping_before': 'static int T(const za*p,Move m){(void)p;(void)m;return 0;}', 'shipping_after': ''}, {'label': 'zero-order call', 'canonical_before': '        scores[i]+=tiny_order(p,m);\n', 'canonical_after': '', 'shipping_before': 'L[i]+=T(p,m);', 'shipping_after': ''}], 'semantic_domain': {'workers': 2, 'tt_bits': 18, 'PLY': 128, 'MATE': 30000, 'outer_threshold': 29871, 'raw_abs_upper': 29120, 'normal_side': [-1, 1], 'production_TT_store_bound': [1, 2, 3], 'bound_shift': 41, 'TT_depth_comparison': 'at least requested', 'C_actual_AVX2_preserved': True, 'E_inner_clamp_and_21_coefficients_preserved': False, 'query_startup_reset_changes_added': False, 'DEV_generated': False}, 'expected': {'source_sha256': 'f70cd11e8cdd1a3d2503255189e80ca9070cf310777d2ff8a89ec9beff732f82'}, 'input_bytes': 11455, 'output_bytes': 11284, 'readable_bytes': 26692}

def transform_source(source, *, readable, profile, tokens, keywords):
    if profile != PROFILE:
        raise ValueError('shipping core requires exact workers2/TT18/PLY128 profile')
    if b'\r' in source or b'\r' in readable:
        raise ValueError('shipping core requires LF input')
    if len(readable) != FIXED['readable_bytes'] or sha(readable) != FIXED['canonical_sha256']:
        raise ValueError('shipping core canonical domain differs')
    if len(source) != FIXED['input_bytes'] or sha(source) != FIXED['expected']['source_sha256']:
        raise ValueError('shipping core exact post-scope input differs')
    bindings = paired_bindings(FIXED['rules'], tokens, keywords)
    explained, readable_receipt = apply(readable, FIXED['rules'], 'canonical')
    packed, packed_receipt = apply(source, FIXED['rules'], 'shipping')
    if sha(explained) != FIXED['candidate_canonical_sha256']:
        raise ValueError('shipping core paired readable result differs')
    if len(packed) != FIXED['output_bytes'] or sha(packed) != FIXED['candidate_shipping_sha256']:
        raise ValueError('shipping core candidate differs')
    return packed, {'canonical': readable_receipt, 'shipping': packed_receipt,
        'paired_existing_identifier_bindings': bindings, 'new_names_allocated': 0,
        'existing_public_alpha_scope_guards_modified': False, 'C_AST_runs': 0,
        'query_startup_reset_source_complement_preserved': True,
        'domain': FIXED['semantic_domain'], 'DEV_stage': False,
        'scope': 'fixed shipping-only source stage; qualification hashes in recipe are metadata'}
