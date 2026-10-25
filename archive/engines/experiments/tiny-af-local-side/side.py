"""One pinned A local-side candidate; no lexer, AST, naming or policy search."""
import hashlib
import re

CANONICAL = '71f9ff6ce1b7f555ad85c3bf49766381c0627315da94acf0c49eeee7bee4a734'
SHIPPING = 'a3414baa5034a62067f74f7f8fff9a1578827f37e6ca59b0db8e5bc1968df312'
# Canonical-local to shipping-local relations, scoped to these six expressions.
ALIASES = {'from':'o', 'to':'a', 'prom':'d', 'target':'f'}
# Canonical before/after, actual final shipping before/after; each occurs once.
EDITS = (
 ('int a=abs(p->b[from]);if(p->b[from]*s<=0)continue;',
  'int a=p->b[from]*s;if(a<=0)continue;',
  'int a=abs(p->b[o]);if(p->b[o]*s<=0)continue;',
  'int a=p->b[o]*s;if(a<=0)continue;'),
 ('int v=p->b[from],target=p->b[to];',
  'int v=p->b[from]*s,target=p->b[to];',
  'int v=p->b[o],f=p->b[a];', 'int v=p->b[o]*s,f=p->b[a];'),
 ('if(abs(v)==1){', 'if(v==1){', 'if(abs(v)==1){', 'if(v==1){'),
 ('if(prom)v=s*prom;', 'if(prom)v=prom;', 'if(d)v=s*d;', 'if(d)v=d;'),
 ('if(abs(v)==6&&abs(to-from)==2){', 'if(v==6&&abs(to-from)==2){',
  'if(abs(v)==6&&abs(a-o)==2){', 'if(v==6&&abs(a-o)==2){'),
 ('put(t,to,v);', 'put(t,to,v*s);', 'bf(t,a,v);', 'bf(t,a,v*s);'),
)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def _require(condition, message):
    if not condition:
        raise ValueError(message)

def _patch(data, pairs):
    spans = []
    for before, after in pairs:
        before, after = before.encode(), after.encode()
        _require(data.count(before) == 1, 'original expression count differs')
        offset = data.index(before)
        spans.append((offset, before, after))
    spans.sort()
    output, inverse, complement, cursor, offsets = [], [], [], 0, []
    for offset, before, after in spans:
        _require(offset >= cursor, 'overlapping expression edits')
        gap = data[cursor:offset]
        output.extend((gap, after)); inverse.extend((gap, before)); complement.append(gap)
        offsets.append({'offset':offset, 'before':before.decode(), 'after':after.decode()})
        cursor = offset + len(before)
    output.append(data[cursor:]); inverse.append(data[cursor:]); complement.append(data[cursor:])
    candidate = b''.join(output)
    _require(b''.join(inverse) == data, 'forward construction inverse differs')
    # Independently recover old bytes and unchanged gaps by candidate expressions.
    recovered, candidate_gaps, cursor = [], [], 0
    for _, before, after in spans:
        _require(candidate.count(after) == 1, 'candidate expression count differs')
        offset = candidate.index(after)
        _require(offset >= cursor, 'candidate expression order differs')
        gap = candidate[cursor:offset]
        recovered.extend((gap, before)); candidate_gaps.append(gap)
        cursor = offset + len(after)
    recovered.append(candidate[cursor:]); candidate_gaps.append(candidate[cursor:])
    _require(b''.join(recovered) == data, 'exact inverse differs')
    _require(candidate_gaps == complement, 'unchanged complement differs')
    return candidate, {'exact_inverse':True, 'complement_exact':True,
                       'complement_sha256':sha(b''.join(complement)), 'edits':offsets,
                       'before_bytes':len(data), 'after_bytes':len(candidate),
                       'before_sha256':sha(data), 'after_sha256':sha(candidate)}

def transform(canonical, shipping):
    _require(sha(canonical) == CANONICAL, 'canonical input differs')
    _require(len(shipping) == 9910 and sha(shipping) == SHIPPING, 'shipping input differs')
    for old, new, compact_old, compact_new in EDITS:
        for readable, compact in ((old, compact_old), (new, compact_new)):
            mapped = re.sub(r'\b[A-Za-z_]\w*\b', lambda m: ALIASES.get(m[0], m[0]), readable)
            mapped = mapped.replace('put(', 'bf(')
            _require(''.join(mapped.split()) == ''.join(compact.split()), 'fixed alias relation differs')
    # Assert literal function ownership without parsing or modifying any other body.
    owner = shipping.index(b'int ac(const E*p,Move m,E*t){')
    owner_end = shipping.index(b'static void bh(', owner)
    walker = shipping.index(b'static int bg(const E*p,Move*B,int f,int s){')
    walker_end = shipping.index(b'int ar(', walker)
    _require(walker <= shipping.index(EDITS[0][2].encode()) < walker_end, 'walk ownership differs')
    for edit in EDITS[1:]:
        _require(owner <= shipping.index(edit[2].encode()) < owner_end, 'make ownership differs')
    _, readable_proof = _patch(canonical, [(e[0], e[1]) for e in EDITS])
    candidate, shipping_proof = _patch(shipping, [(e[2], e[3]) for e in EDITS])
    return candidate, {'candidate_count':1, 'fixed_alias_relation':True,
                       'canonical':readable_proof, 'shipping':shipping_proof,
                       'semantics':'s is +/-1 and make accepts only gen members; absolute domains unchanged'}
