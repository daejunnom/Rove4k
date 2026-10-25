"""One literal F9954 EP-to-make change; no lexer, AST, rename or model search."""
import hashlib

SOURCE_SHA = '00239e23500d41c45801cdb19c4e7c8cc8b22cf29bebd7e4fbc8fdd1e08c7916'
CANONICAL_SHA = 'ec39b5641ac9fc5ab19a0c919c05e0d68169b461cc1d32afeee83274926becbd'
OLD = b'static void aE(za*p){if(p->e<0)return;for(int d=-1;d<=1;d+=2){int q=p->e-p->s*16+d;if(!(q&0x88)&&p->b[q]==p->s){za t=*p;t.b[q]=t.b[p->e-p->s*16]=0;t.b[p->e]=(int8_t)p->s;if(!aa(&t,p->k[p->s<0],-p->s))return;}}p->e=-1;}'
NEW = b'static void aE(za*p){if(p->e<0)return;for(int d=-1;d<=1;d+=2){int q=p->e-p->s*16+d;if(!(q&0x88)&&p->b[q]==p->s){za t;if(ab(p,MOVE(q,p->e,0),&t))return;}}p->e=-1;}'
DECL = b'int ab(const za*,Move,za*);'
READABLE_OLD = b'''static void ep(Board *p){
    if(p->e<0)return;
    for(int d=-1;d<=1;d+=2){
        int q=p->e-p->s*16+d;
        if(!(q&0x88)&&p->b[q]==p->s){
            Board t=*p;t.b[q]=t.b[p->e-p->s*16]=0;t.b[p->e]=(int8_t)p->s;
            if(!attacked(&t,p->k[p->s<0],-p->s))return;
        }
    }
    p->e=-1;
}
'''
READABLE_NEW = READABLE_OLD.replace(
    b'Board t=*p;t.b[q]=t.b[p->e-p->s*16]=0;t.b[p->e]=(int8_t)p->s;\n'
    b'            if(!attacked(&t,p->k[p->s<0],-p->s))return;',
    b'Board t;if(make(p,MOVE(q,p->e,0),&t))return;')
READABLE_DECL = b'int make(const Board *,Move,Board *);\n'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def need(value, message):
    if not value:
        raise ValueError(message)


def projected(data):
    # Only these fixed, comment/string-free snippets. Not a generic C transform.
    for old, new in ((b'Board', b'za'), (b'attacked', b'aa'),
                     (b'make', b'ab'), (b'ep', b'aE')):
        data = data.replace(old, new)
    return b''.join(data.split())


def transform(source, canonical):
    need(sha(source) == SOURCE_SHA and len(source) == 9954 and source.count(OLD) == 1,
         'exact F9954 source and one old EP literal required')
    need(sha(canonical) == CANONICAL_SHA and canonical.count(READABLE_OLD) == 1,
         'exact current canonical F and one readable EP required')
    need(projected(READABLE_OLD) == b''.join(OLD.split()) and
         projected(READABLE_NEW) == b''.join(NEW.split()) and
         projected(READABLE_DECL) == b''.join(DECL.split()),
         'fixed readable/shipping alias-role relation differs')
    candidate = source.replace(OLD, DECL + NEW)
    need(candidate.count(DECL + NEW) == 1 and
         candidate.replace(DECL + NEW, OLD) == source, 'exact raw inverse failed')
    before, after = source.split(OLD)
    need(candidate == before + DECL + NEW + after, 'protected complement changed')
    need(len(candidate) == 9925 and sha(candidate) ==
         '3549063cbdca22c83536e0879b5e7baff8c7cbef3b5911f4152850732c86300c',
         'sole candidate identity differs')
    return candidate, {
        'source_sha256': sha(source), 'candidate_sha256': sha(candidate),
        'shipping_ep_old_bytes': len(OLD), 'shipping_ep_new_bytes': len(NEW),
        'shipping_declaration_bytes': len(DECL), 'shipping_delta': len(candidate)-len(source),
        'readable_ep_old_bytes': len(READABLE_OLD), 'readable_ep_new_bytes': len(READABLE_NEW),
        'readable_declaration_bytes': len(READABLE_DECL), 'readable_literal_delta': -35,
        'canonical_read_only': True, 'fixed_alias_role_projection': True, 'exact_inverse': True,
        'protected_complement_bytes': len(before)+len(after),
        'protected_complement_sha256': sha(before+after),
        'old_native_equality_required': False,
        'private_contract': 'EP boolean trial only: discarded noncanonical h/r; e=-1 bounds recursion',
        'normal_guard_bypass': False,
        'normal_pipeline_run': False,
    }
