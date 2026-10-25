"""Pure query-work projections for the fixed full 7f711448 TCEC C sources.

TT cutoffs, draw/ply-limit handling, exact-horizon/mate normalization and
publication are unchanged. Only unused local move-list/evaluation queries are
deferred. The optional QS edit stops after the first accepted legal move when
stand-pat already cuts off; B's side-effecting SEE ranking remains untouched.
The baseline-coordinate edit API permits explicit composition with disjoint
source stages without accepting unknown generated inputs.
"""
import hashlib
import re

SCHEMA = 'rove4k.tcec-search-queries.v1'
INPUTS = {
    'A': (7869, '248479972fb803223e353b37fbe85f95248d469b4c1c3382babeb15625b0aa72'),
    'B': (8770, '23d9de0788b0058c0a11744290bdf2d39582b16d6af48501d9021bbb57f54bfe'),
    'C': (8486, 'ade8c284fdc5e116e6efd5607a18ba018dbdabf4110675d5eb920eb50fd6aa15'),
    'E': (8063, '80f7c14239baffca5ab1cca8a2f4777691f3dfc7d068b511dc022332590889e5'),
    'F': (6901, '46bd9a21026afb7e289acbec67078235563534685f9413fbb989664f7728ea22'),
    'F8': (7049, 'ef538c8d400dcb0fb50e16a4e80886ff7ef192ea4d44a480d49031d71c109e5e'),
}
START = {'A': b'static L h(M*w,', 'B': b'J I P(zd*w,',
         'C': b'static int h(ai*w,', 'E': b'static L h(ai*w,',
         'F': b'aa S qr(X*w,', 'F8': b'static S qr(X*w,'}
TT_END = {
    'A': b'if(d&&K&&k>=(C>0?C:0)&&(K==1||(K==2&&l>=a)||(K==3&&l<=G)))J l;',
    'B': b'if(n&&zo&&yz>=(a>0?a:0)&&(zo==1||(zo==2&&yl>=f)||(zo==3&&yl<=d)))l yl;',
    'C': b'if(d&&K&&L>=(C>0?C:0)&&(K==1||(K==2&&l>=a)||(K==3&&l<=G)))return l;',
    'E': b'if(d&&K&&k>=(C>0?C:0)&&(K==1||(K==2&&l>=a)||(K==3&&l<=G)))J l;',
    'F': b'if(f&&(F>>33)==a*2+2+(u<d))H u;',
    'F8': b'if(f&&(F>>33)==a*2+2+(u<d))H u;',
}
GEN = {'A': b'z=T(p,B)', 'B': b'Z=c(p,X,0,p->s)', 'C': b'z=T(p,B)',
       'E': b'z=T(p,B)', 'F': b'A=T(p,x,0,p->s)', 'F8': b'A=T(p,x,0,p->s)'}
EVAL = {'A': b'F=p->s*p->v', 'B': b'zF=p->s*p->v', 'C': b'F=p->s*U(p)',
        'E': b'F=p->s*S(p)', 'F': b'D=p->s*p->v', 'F8': b'D=p->s*p->v'}


def pin(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def _family(family):
    if family == 'F2':
        family = 'F'
    if family not in INPUTS:
        raise ValueError('explicit known full C family required')
    return family


def _admit(source, family):
    if type(source) is not bytes or (len(source), hashlib.sha256(source).hexdigest()) != INPUTS[family]:
        raise ValueError('fixed full TCEC search-query input differs')


def edits_for(source, *, family, tt='gen-eval', qs=False):
    """Return exact baseline-coordinate edits for a known admitted source.

    Rows contain bytes and are an internal composition API, not JSON. A caller
    must apply them to this admitted baseline and reject overlapping edits.
    """
    family = _family(family)
    _admit(source, family)
    if tt not in ('control', 'gen', 'gen-eval', 'gen-eval-decl') or type(qs) is not bool:
        raise ValueError('explicit query/QS policy required')
    if tt == 'gen-eval-decl' and family == 'B':
        raise ValueError('B terminal path requires the separate list declaration')
    begin = source.index(START[family])
    end = source.index(b'void i(' if family in ('B', 'F', 'F8') else b'void C(', begin)
    body = source[begin:end]
    rows = []

    def add(role, old, new):
        if body.count(old) != 1:
            raise ValueError('unique search-query span missing: ' + role)
        rows.append({'role': role, 'begin': begin + body.index(old), 'before': old, 'after': new})

    if tt == 'gen-eval-decl':
        first = body.index(b'Y x[' if family in ('F', 'F8') else b'Y B[')
        last = body.index(b'W E=' if family in ('F', 'F8') else b'W I=', first)
        declaration = body[first:last]
        if GEN[family] not in declaration or EVAL[family] not in declaration:
            raise ValueError('full query declaration roles differ')
        add('defer-query-declaration', declaration, b'')
        add('declaration-after-unchanged-TT-cutoff', TT_END[family], TT_END[family] + declaration)
    elif tt != 'control':
        add('defer-move-list-query', GEN[family], GEN[family].split(b'=')[0])
        if family == 'B':
            # B's separate terminal path consumes the list before the TT path.
            add('B-terminal-list-preserved', b'if(L||n==127){za q;',
                b'if(L||n==127){za q;' + GEN[family] + b';')
        delayed = GEN[family] + b';'
        if tt == 'gen-eval':
            add('defer-pure-evaluation', EVAL[family], EVAL[family].split(b'=')[0])
            delayed += EVAL[family] + b';'
        add('query-after-unchanged-TT-cutoff', TT_END[family], TT_END[family] + delayed)
    if family == 'C' and tt in ('gen-eval', 'gen-eval-decl'):
        # C's SIMD evaluator U must stay visible at the delayed call. Z is
        # unused in this scope; its outer Entry type is not consumed here.
        if re.search(rb'\bZ\b', body):
            raise ValueError('C TT-data replacement binder is occupied')
        matches = list(re.finditer(rb'\bU\b(?!\s*\()', body))
        if len(matches) != 7 or body.count(b'U(p)') != 1:
            raise ValueError('C TT-data binder/call roles differ')
        for i, match in enumerate(matches):
            rows.append({'role': 'C-TT-data-binder-' + str(i),
                         'begin': begin + match.start(), 'before': b'U', 'after': b'Z'})
    if qs:
        if family in ('F', 'F8'):
            if body.count(b'if(K&&C>=d)break;if(K&&!P)continue;') != 1:
                raise ValueError('existing F first-legal QS cutoff differs')
        elif family == 'B':
            add('QS-first-accepted-legal-cutoff', b'if(ye&&(!yu||d>=f))continue;',
                b'if(ye&&d>=f)break;if(ye&&!yu)continue;')
        else:
            add('QS-first-accepted-legal-cutoff', b'if(M&&(!Q||G>=a))continue;',
                b'if(M&&G>=a)break;if(M&&!Q)continue;')
    rows.sort(key=lambda row: row['begin'])
    for left, right in zip(rows, rows[1:]):
        if left['begin'] + len(left['before']) > right['begin']:
            raise ValueError('search-query edits overlap')
    return rows


# The integrator consumes this explicit baseline-coordinate spelling.
source_edits = edits_for


def transform_source(source, *, family, tt='gen-eval', qs=False):
    family = _family(family)
    rows = edits_for(source, family=family, tt=tt, qs=qs)
    parts, edits, gaps = [], [], []
    used = emitted = 0
    for row in rows:
        at, old, new = row['begin'], row['before'], row['after']
        if source[at:at + len(old)] != old:
            raise ValueError('query baseline coordinate differs')
        gap = source[used:at]
        parts.extend((gap, new))
        gaps.append({'input_begin': used, 'output_begin': emitted, **pin(gap)})
        emitted += len(gap)
        edits.append({'role': row['role'], 'input_begin': at, 'output_begin': emitted,
                      'before': old.decode('ascii'), 'after': new.decode('ascii')})
        used, emitted = at + len(old), emitted + len(new)
    gap = source[used:]
    parts.append(gap)
    gaps.append({'input_begin': used, 'output_begin': emitted, **pin(gap)})
    candidate = b''.join(parts)
    proof = dict(schema=SCHEMA, family=family, tt=tt, qs=qs,
                 input=pin(source), output=pin(candidate), edits=edits, protected_gaps=gaps,
                 full_inverse=True, root_cutoff_predicate_unchanged=True,
                 draw_plycap_terminal_order_preserved=True,
                 B_excluded_TT_and_SEE_rank_side_effects_preserved=True,
                 F_horizon_mate_witness_and_existing_QS_preserved=True,
                 pure_query_counts_and_timing_may_change=True,
                 no_exact_SMP_trace_or_Elo_claim=True)
    if restore_source(candidate, proof, _replay=False) != source:
        raise ValueError('query whole inverse differs')
    return candidate, proof


def restore_source(candidate, proof, _replay=True):
    if type(candidate) is not bytes or proof.get('schema') != SCHEMA or pin(candidate) != proof['output']:
        raise ValueError('query output/proof differs')
    source = candidate
    for row in reversed(proof['edits']):
        at, old, new = row['output_begin'], row['before'].encode('ascii'), row['after'].encode('ascii')
        if source[at:at + len(new)] != new:
            raise ValueError('query inverse span differs')
        source = source[:at] + old + source[at + len(new):]
    family = _family(proof['family'])
    _admit(source, family)
    if pin(source) != proof['input']:
        raise ValueError('query inverse input differs')
    if _replay:
        replay, expected = transform_source(source, family=family, tt=proof['tt'], qs=proof['qs'])
        if replay != candidate or expected != proof:
            raise ValueError('query proof replay differs')
    return source
