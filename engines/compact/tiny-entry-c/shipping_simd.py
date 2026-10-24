"""One exact shipping residual-vector SIMD stage, after the fixed core stage.

The ordinary local literals own the readable witness and shipping rewrite.
No experiment, generated source, receipt, parser or external artifact is read.
DEV never enters this stage. Existing alpha/scope/core domains stay unchanged.
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


FIXED = {'canonical_sha256': '15999279c5bd4690db7129bda032c6b5962acbd814236719cda40755ae31794b', 'rules': [{'label': 'PSQT/constructor/gather to local color-residual signed16 dot', 'canonical_before': 'static int32_t tiny_table[13*64];\n#if DEV\nstatic atomic_uint_fast64_t tiny_leaf_calls,tiny_order_calls,tiny_init_calls;\nstatic int tiny_scalar(const Board *p){\n    int score=0;\n    for(int q=0;q<128;q++)if(!(q&0x88)&&p->b[q])score+=value(p->b[q],q);\n    return score;\n}\n#endif\nstatic void __attribute__((constructor)) tiny_eval_init(void){\n#if DEV\n    atomic_fetch_add_explicit(&tiny_init_calls,1,memory_order_relaxed);\n#endif\n    for(int v=-6;v<=6;v++)for(int q=0;q<64;q++)tiny_table[(v+6)*64+q]=value(v,(q/8)*16+q%8);\n}\nstatic int tiny_raw(const Board *p){\n    __m256i sum=_mm256_setzero_si256(),base=_mm256_setr_epi32(384,385,386,387,388,389,390,391);\n#if DEV\n    atomic_fetch_add_explicit(&tiny_leaf_calls,1,memory_order_relaxed);\n#endif\n    for(int q=0;q<128;q+=16){\n        __m256i pieces=_mm256_cvtepi8_epi32(_mm_loadl_epi64((const __m128i *)(p->b+q)));\n        __m256i index=_mm256_add_epi32(base,_mm256_slli_epi32(pieces,6));\n        sum=_mm256_add_epi32(sum,_mm256_i32gather_epi32(tiny_table,index,4));\n        base=_mm256_add_epi32(base,_mm256_set1_epi32(8));\n    }\n    __m128i half=_mm_add_epi32(_mm256_castsi256_si128(sum),_mm256_extracti128_si256(sum,1));\n    half=_mm_hadd_epi32(half,half);\n    return _mm_cvtsi128_si32(_mm_hadd_epi32(half,half));\n}\n', 'canonical_after': '#if DEV\nstatic int32_t tiny_table[13*64];\n#if DEV\nstatic atomic_uint_fast64_t tiny_leaf_calls,tiny_order_calls,tiny_init_calls;\nstatic int tiny_scalar(const Board *p){\n    int score=0;\n    for(int q=0;q<128;q++)if(!(q&0x88)&&p->b[q])score+=value(p->b[q],q);\n    return score;\n}\n#endif\nstatic void __attribute__((constructor)) tiny_eval_init(void){\n#if DEV\n    atomic_fetch_add_explicit(&tiny_init_calls,1,memory_order_relaxed);\n#endif\n    for(int v=-6;v<=6;v++)for(int q=0;q<64;q++)tiny_table[(v+6)*64+q]=value(v,(q/8)*16+q%8);\n}\nstatic int tiny_raw(const Board *p){\n    __m256i sum=_mm256_setzero_si256(),base=_mm256_setr_epi32(384,385,386,387,388,389,390,391);\n#if DEV\n    atomic_fetch_add_explicit(&tiny_leaf_calls,1,memory_order_relaxed);\n#endif\n    for(int q=0;q<128;q+=16){\n        __m256i pieces=_mm256_cvtepi8_epi32(_mm_loadl_epi64((const __m128i *)(p->b+q)));\n        __m256i index=_mm256_add_epi32(base,_mm256_slli_epi32(pieces,6));\n        sum=_mm256_add_epi32(sum,_mm256_i32gather_epi32(tiny_table,index,4));\n        base=_mm256_add_epi32(base,_mm256_set1_epi32(8));\n    }\n    __m128i half=_mm_add_epi32(_mm256_castsi256_si128(sum),_mm256_extracti128_si256(sum,1));\n    half=_mm_hadd_epi32(half,half);\n    return _mm_cvtsi128_si32(_mm_hadd_epi32(half,half));\n}\n#else\nstatic int tiny_raw(const Board *p){\n    static const int16_t w[16]={100,320,330,500,900,0,1,0,-100,-320,-330,-500,-900,0,-1,0};\n    int16_t x[16]={0};\n    for(int q=0;q<128;q++)if(!(q&0x88)){\n        int v=p->b[q];\n        if(v){\n            int k=abs(v),o=8*(v<0),t=value(v,q);\n            x[o+k-1]++;\n            x[o+6]+=(v>0?t:-t)-w[k-1];\n        }\n    }\n    __m256i y=_mm256_madd_epi16(_mm256_loadu_si256((const __m256i *)x),_mm256_loadu_si256((const __m256i *)w));\n    __m128i z=_mm_add_epi32(_mm256_castsi256_si128(y),_mm256_extracti128_si256(y,1));\n    z=_mm_hadd_epi32(z,z);\n    return _mm_cvtsi128_si32(_mm_hadd_epi32(z,z));\n}\n#endif\n', 'active_before': 'static int32_t tiny_table[13*64];\nstatic void __attribute__((constructor)) tiny_eval_init(void){\n    for(int v=-6;v<=6;v++)for(int q=0;q<64;q++)tiny_table[(v+6)*64+q]=value(v,(q/8)*16+q%8);\n}\nstatic int tiny_raw(const Board *p){\n    __m256i sum=_mm256_setzero_si256(),base=_mm256_setr_epi32(384,385,386,387,388,389,390,391);\n    for(int q=0;q<128;q+=16){\n        __m256i pieces=_mm256_cvtepi8_epi32(_mm_loadl_epi64((const __m128i *)(p->b+q)));\n        __m256i index=_mm256_add_epi32(base,_mm256_slli_epi32(pieces,6));\n        sum=_mm256_add_epi32(sum,_mm256_i32gather_epi32(tiny_table,index,4));\n        base=_mm256_add_epi32(base,_mm256_set1_epi32(8));\n    }\n    __m128i half=_mm_add_epi32(_mm256_castsi256_si128(sum),_mm256_extracti128_si256(sum,1));\n    half=_mm_hadd_epi32(half,half);\n    return _mm_cvtsi128_si32(_mm_hadd_epi32(half,half));\n}\n', 'active_after': 'static int tiny_raw(const Board *p){\n    static const int16_t w[16]={100,320,330,500,900,0,1,0,-100,-320,-330,-500,-900,0,-1,0};\n    int16_t x[16]={0};\n    for(int q=0;q<128;q++)if(!(q&0x88)){\n        int v=p->b[q];\n        if(v){\n            int k=abs(v),o=8*(v<0),t=value(v,q);\n            x[o+k-1]++;\n            x[o+6]+=(v>0?t:-t)-w[k-1];\n        }\n    }\n    __m256i y=_mm256_madd_epi16(_mm256_loadu_si256((const __m256i *)x),_mm256_loadu_si256((const __m256i *)w));\n    __m128i z=_mm_add_epi32(_mm256_castsi256_si128(y),_mm256_extracti128_si256(y,1));\n    z=_mm_hadd_epi32(z,z);\n    return _mm_cvtsi128_si32(_mm_hadd_epi32(z,z));\n}\n', 'shipping_before': 'static int32_t tiny_table[13*64];static void __attribute__((constructor))tiny_eval_init(void){for(int v=-6;v<=6;v++)for(int q=0;q<64;q++)tiny_table[(v+6)*64+q]=value(v,(q/8)*16+q%8);}static int U(const za*p){__m256i yt=_mm256_setzero_si256(),a=_mm256_setr_epi32(384,385,386,387,388,389,390,391);for(int q=0;q<128;q+=16){__m256i d=_mm256_cvtepi8_epi32(_mm_loadl_epi64((const __m128i*)(p->b+q)));__m256i index=_mm256_add_epi32(a,_mm256_slli_epi32(d,6));yt=_mm256_add_epi32(yt,_mm256_i32gather_epi32(tiny_table,index,4));a=_mm256_add_epi32(a,_mm256_set1_epi32(8));}__m128i f=_mm_add_epi32(_mm256_castsi256_si128(yt),_mm256_extracti128_si256(yt,1));f=_mm_hadd_epi32(f,f);return _mm_cvtsi128_si32(_mm_hadd_epi32(f,f));}\n', 'shipping_after': 'static int U(const za*p){static const int16_t w[16]={100,320,330,500,900,0,1,0,-100,-320,-330,-500,-900,0,-1,0};int16_t x[16]={0};for(int q=0;q<128;q++)if(!(q&0x88)){int v=p->b[q];if(v){int k=abs(v),o=8*(v<0),t=value(v,q);x[o+k-1]++;x[o+6]+=(v>0?t:-t)-w[k-1];}}__m256i y=_mm256_madd_epi16(_mm256_loadu_si256((const __m256i*)x),_mm256_loadu_si256((const __m256i*)w));__m128i z=_mm_add_epi32(_mm256_castsi256_si128(y),_mm256_extracti128_si256(y,1));z=_mm_hadd_epi32(z,z);return _mm_cvtsi128_si32(_mm_hadd_epi32(z,z));}\n'}], 'DEV_witness_spans': ['#if DEV\nstatic atomic_uint_fast64_t tiny_leaf_calls,tiny_order_calls,tiny_init_calls;\nstatic int tiny_scalar(const Board *p){\n    int score=0;\n    for(int q=0;q<128;q++)if(!(q&0x88)&&p->b[q])score+=value(p->b[q],q);\n    return score;\n}\n#endif\n', '#if DEV\n    atomic_fetch_add_explicit(&tiny_init_calls,1,memory_order_relaxed);\n#endif\n', '#if DEV\n    atomic_fetch_add_explicit(&tiny_leaf_calls,1,memory_order_relaxed);\n#endif\n'], 'candidate': {'readable_bytes': 27350, 'readable_sha256': 'd508688149f2ed45d9ae316ee61bb5708fcdcd8d142dbee14e01ceb17d260a4f', 'source_bytes': 11086, 'source_sha256': '90a566c5e814cf87dd38f92f40ce8fe7115c4d4d07f75d9ff0981ffaae1fbc28'}, 'profile': {'workers': 2, 'tt_bits': 18, 'ply': 128, 'DEV': False}, 'input_source_bytes': 11284, 'input_source_sha256': '68ad43dec85adcfff6e65bba0f457738e33ff545d786d43c3c3a7b53e618f02c', 'canonical_bytes': 26692}

def transform_source(source, *, readable, profile, tokens, keywords):
    if profile != {'workers':2,'tt_bits':18,'ply':128,'dev_default':False}:
        raise ValueError('SIMD stage requires exact workers2/TT18/PLY128 shipping profile')
    if b'\r' in source or b'\r' in readable:
        raise ValueError('SIMD stage requires LF inputs')
    if len(readable)!=FIXED['canonical_bytes'] or sha(readable)!=FIXED['canonical_sha256']:
        raise ValueError('SIMD canonical domain changed')
    if len(source)!=FIXED['input_source_bytes'] or sha(source)!=FIXED['input_source_sha256']:
        raise ValueError('SIMD exact post-core source changed')
    rule=FIXED['rules'][0]
    witness=rule['canonical_before'].encode()
    for span in FIXED['DEV_witness_spans']:
        span=span.encode()
        if witness.count(span)!=1:raise ValueError('literal DEV witness changed')
        witness=witness.replace(span,b'')
    if witness!=rule['active_before'].encode():raise ValueError('paired active readable witness changed')
    correspondence=dict(rule,canonical_before=rule['active_before'],canonical_after=rule['active_after'])
    bindings=paired_bindings([correspondence],tokens,keywords)
    explained,r=apply(readable,FIXED['rules'],'canonical')
    result,s=apply(source,FIXED['rules'],'shipping')
    expected=FIXED['candidate']
    if len(explained)!=expected['readable_bytes'] or sha(explained)!=expected['readable_sha256']:
        raise ValueError('paired readable SIMD result changed')
    if len(result)!=expected['source_bytes'] or sha(result)!=expected['source_sha256']:
        raise ValueError('fixed shipping SIMD result changed')
    return result,{'canonical':r,'shipping':s,'paired_roles':bindings,
        'DEV_original_readable_block_preserved':True,'new_alias_allocation':False,
        'Board_put_make_search_complement_preserved':True,'profile':profile,
        'feature':'two colors x (six counts, own positional residual, zero), signed16 madd/i32 sum',
        'scope':'source-only fixed stage; exact-native SIMD/functional receipts are metadata in recipe'}
