"""One exact F go-field sharing transform after immutable normal spelling maps."""
import hashlib

SOURCE_SHA = '00239e23500d41c45801cdb19c4e7c8cc8b22cf29bebd7e4fbc8fdd1e08c7916'
CANONICAL_SHA = 'ec39b5641ac9fc5ab19a0c919c05e0d68169b461cc1d32afeee83274926becbd'
CLOCK = rb'''if(!strcmp(t,"wtime")||!strcmp(t,"btime")){int side=*t=='w'?1:-1;uint64_t n=number(strtok_r(NULL," \t",&save));if(side==position.s){clock=n;present=1;}}'''
INC = rb'''else if(!strcmp(t,"winc")||!strcmp(t,"binc")){int side=*t=='w'?1:-1;uint64_t n=number(strtok_r(NULL," \t",&save));if(side==position.s)inc=n;}'''
READABLE_OLD = b'        '+CLOCK+b'\n        '+INC
READABLE_NEW = rb'''        if(!strcmp(t,"wtime")||!strcmp(t,"btime")||!strcmp(t,"winc")||!strcmp(t,"binc")){
            int side=*t=='w'?1:-1;uint64_t n=number(strtok_r(NULL," \t",&save));
            if(side==position.s){if(t[1]=='t'){clock=n;present=1;}else inc=n;}
        }'''
SHIPPING_OLD = rb'''if(!strcmp(t,"wtime")||!strcmp(t,"btime")){int j=*t=='w'?1:-1;uint64_t n=aw(strtok_r(NULL," \t",&i));if(j==ql.s){a=n;g=1;}}else if(!strcmp(t,"winc")||!strcmp(t,"binc")){int l=*t=='w'?1:-1;uint64_t n=aw(strtok_r(NULL," \t",&i));if(l==ql.s)d=n;}'''
NAMES = (('clock','a'), ('inc','d'), ('present','g'), ('save','i'), ('position','ql'), ('number','aw'))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def need(value, message):
    if not value:
        raise ValueError(message)


def mapped(fragment, side, compact, lexer):
    result = compact(fragment, 'c')
    need(result.endswith(b'\n'), 'existing minifier final LF differs')
    result = result[:-1]
    for old, new in (*NAMES, ('side', side)):
        result = lexer._replace({'snippet.c': result}, old, new)['snippet.c']
    return result


def transform(source, canonical, *, compact, lexer):
    need(type(source) is bytes and len(source) == 9954 and sha(source) == SOURCE_SHA, 'exact normal F9954 required')
    need(type(canonical) is bytes and sha(canonical) == CANONICAL_SHA and b'\r' not in canonical, 'exact canonical F LF source required')
    need(canonical.count(READABLE_OLD) == 1, 'canonical parser literal differs')
    old = mapped(CLOCK, 'j', compact, lexer)+mapped(INC, 'l', compact, lexer)
    need(old == SHIPPING_OLD and source.count(old) == 1, 'readable-to-shipping original literal differs')
    new = mapped(READABLE_NEW, 'j', compact, lexer)
    start = source.index(old)
    need(source.rfind(b'static void as(char*s)', 0, start) >= 0 and start < source.index(b'int main(void)'), 'literal is outside the actual go function')
    candidate = source[:start]+new+source[start+len(old):]
    need(candidate[:start]+old+candidate[start+len(new):] == source, 'span inverse does not restore exact input')
    number_start = canonical.index(b'static uint64_t number(')
    number_end = canonical.index(b'static int read_line(', number_start)
    number = mapped(canonical[number_start:number_end], 'j', compact, lexer)
    need(source.count(number) == 1 and candidate.count(number) == 1, 'number implementation differs')
    readable_start = canonical.index(READABLE_OLD)
    return candidate, {
        'input_bytes': len(source), 'input_sha256': sha(source),
        'candidate_bytes': len(candidate), 'candidate_sha256': sha(candidate),
        'source_saved_bytes': len(source)-len(candidate),
        'shipping_start': start, 'old_bytes': len(old), 'new_bytes': len(new),
        'shipping_old_literal': old.decode(), 'shipping_new_literal': new.decode(),
        'readable_old_literal': READABLE_OLD.decode(), 'readable_new_literal': READABLE_NEW.decode(),
        'canonical_sha256': sha(canonical), 'canonical_start': readable_start,
        'unchanged_canonical_prefix_sha256': sha(canonical[:readable_start]),
        'unchanged_canonical_suffix_sha256': sha(canonical[readable_start+len(READABLE_OLD):]),
        'unchanged_shipping_prefix_sha256': sha(source[:start]),
        'unchanged_shipping_suffix_sha256': sha(source[start+len(old):]),
        'number_compact_literal_sha256': sha(number), 'position_bound_inverse_exact': True,
        'existing_minifier_and_token_lexer_only': True, 'old_spelling_maps_replayed_or_changed': False,
        'own_side_nests_both_time_and_inc': True,
        'comparison_order': ['wtime', 'btime', 'winc', 'binc'],
        'value_consumption': 'one following token for all recognized own/opponent fields; none for unknown fields',
        'parser_runtime_or_AST_executed': False,
    }
