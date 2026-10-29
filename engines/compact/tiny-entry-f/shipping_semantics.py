"""Exact F EP-to-make semantics for the maintained source pipeline.

The readable literal is the semantic source of truth. Its shipping counterpart
is bound by one fixed role projection and exact before/after identities. This
module imports no repository module and reads no experiment or evidence file.
"""
import hashlib

CANONICAL_BYTES = 25755
CANONICAL_SHA256 = 'ec39b5641ac9fc5ab19a0c919c05e0d68169b461cc1d32afeee83274926becbd'
READABLE_BYTES = 25720
READABLE_SHA256 = 'f9ca456f55ef34c83af9e2e605026415126c9ba0f6eedf10db479a6467c0b357'
SHIPPING_INPUT_BYTES = 9954
SHIPPING_INPUT_SHA256 = '00239e23500d41c45801cdb19c4e7c8cc8b22cf29bebd7e4fbc8fdd1e08c7916'
SHIPPING_BYTES = 9925
SHIPPING_SHA256 = '3549063cbdca22c83536e0879b5e7baff8c7cbef3b5911f4152850732c86300c'

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
READABLE_PROBE_OLD = (
    b'Board t=*p;t.b[q]=t.b[p->e-p->s*16]=0;t.b[p->e]=(int8_t)p->s;\n'
    b'            if(!attacked(&t,p->k[p->s<0],-p->s))return;')
READABLE_PROBE_NEW = b'Board t;if(make(p,MOVE(q,p->e,0),&t))return;'
READABLE_NEW = READABLE_OLD.replace(READABLE_PROBE_OLD, READABLE_PROBE_NEW)
READABLE_DECL = b'int make(const Board *,Move,Board *);\n'

OLD = b'static void aE(za*p){if(p->e<0)return;for(int d=-1;d<=1;d+=2){int q=p->e-p->s*16+d;if(!(q&0x88)&&p->b[q]==p->s){za t=*p;t.b[q]=t.b[p->e-p->s*16]=0;t.b[p->e]=(int8_t)p->s;if(!aa(&t,p->k[p->s<0],-p->s))return;}}p->e=-1;}'
NEW = b'static void aE(za*p){if(p->e<0)return;for(int d=-1;d<=1;d+=2){int q=p->e-p->s*16+d;if(!(q&0x88)&&p->b[q]==p->s){za t;if(ab(p,MOVE(q,p->e,0),&t))return;}}p->e=-1;}'
DECL = b'int ab(const za*,Move,za*);'


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _need(value, message):
    if not value:
        raise ValueError(message)


def _binding(data, size, digest, label):
    _need(type(data) is bytes and len(data) == size and _sha(data) == digest,
          label + ' exact bytes/SHA-256 required')


def _projected(data):
    # Only these fixed comment/string-free snippets; not a general C renamer.
    for old, new in ((b'Board', b'za'), (b'attacked', b'aa'),
                     (b'make', b'ab'), (b'ep', b'aE')):
        data = data.replace(old, new)
    return b''.join(data.split())


def _literal_relation():
    _need(READABLE_OLD.count(READABLE_PROBE_OLD) == 1,
          'one readable EP probe required')
    _need(_projected(READABLE_OLD) == b''.join(OLD.split()) and
          _projected(READABLE_NEW) == b''.join(NEW.split()) and
          _projected(READABLE_DECL) == b''.join(DECL.split()),
          'fixed readable/shipping semantic role relation changed')


def _splice(data, old, replacement):
    _need(data.count(old) == 1 and data.count(replacement) == 0,
          'one original semantic literal and no replacement required')
    before, after = data.split(old)
    result = before + replacement + after
    _need(result.count(replacement) == 1 and
          result.replace(replacement, old) == data,
          'exact semantic raw inverse failed')
    return result, {'protected_complement_bytes': len(before) + len(after),
                    'protected_complement_sha256': _sha(before + after)}


def transform_readable(readable):
    """Apply the one canonical EP change before DEV specialization only."""
    _binding(readable, CANONICAL_BYTES, CANONICAL_SHA256, 'F canonical base')
    _literal_relation()
    _need(READABLE_DECL not in readable, 'semantic forward declaration already present')
    result, complement = _splice(readable, READABLE_OLD, READABLE_DECL + READABLE_NEW)
    _binding(result, READABLE_BYTES, READABLE_SHA256, 'F semantic readable')
    return result, {'stage': 'readable-before-DEV-specialization',
                    'canonical_base_sha256': CANONICAL_SHA256,
                    'semantic_readable_sha256': READABLE_SHA256,
                    'input_bytes': len(readable), 'output_bytes': len(result),
                    'readable_ep_old_bytes': len(READABLE_OLD),
                    'readable_ep_new_bytes': len(READABLE_NEW),
                    'readable_declaration_bytes': len(READABLE_DECL),
                    'source_saved_bytes': len(readable) - len(result),
                    'fixed_alias_role_projection': True, 'exact_inverse': True,
                    'old_DEV_identity_claimed': False, **complement}


def transform_source(source, *, readable):
    """Apply the same semantics after all unchanged shipping spelling guards."""
    semantic_readable, readable_metadata = transform_readable(readable)
    _binding(source, SHIPPING_INPUT_BYTES, SHIPPING_INPUT_SHA256, 'F post-member source')
    _need(DECL not in source, 'shipping semantic declaration already present')
    result, complement = _splice(source, OLD, DECL + NEW)
    _binding(result, SHIPPING_BYTES, SHIPPING_SHA256, 'F semantic shipping source')
    return result, {'stage': 'shipping-after-members',
                    'input_sha256': SHIPPING_INPUT_SHA256,
                    'output_sha256': SHIPPING_SHA256,
                    'input_bytes': len(source), 'output_bytes': len(result),
                    'shipping_ep_old_bytes': len(OLD), 'shipping_ep_new_bytes': len(NEW),
                    'shipping_declaration_bytes': len(DECL),
                    'source_saved_bytes': len(source) - len(result),
                    'canonical_base_sha256': CANONICAL_SHA256,
                    'semantic_readable_sha256': _sha(semantic_readable),
                    'readable_relation': readable_metadata,
                    'fixed_alias_role_projection': True, 'exact_inverse': True,
                    'preexisting_spelling_guards_replaced': False,
                    'old_native_identity_required': False,
                    'private_contract': 'EP boolean trial only; discarded noncanonical h/r; e=-1 bounds recursion',
                    **complement}
