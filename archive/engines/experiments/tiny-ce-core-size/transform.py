"""One exact three-decision C/E core composition; no source-policy discovery."""
import hashlib

BASELINES = {'C': '15999279c5bd4690db7129bda032c6b5962acbd814236719cda40755ae31794b',
             'E': '0a7fe69022051e1893ffbd52ade7a2fbb3f342fe20b581bb786d6997b46fb712'}
COMMON = (
    ('probe signature', b'probe(uint64_t key,int write,uint64_t data)', b'probe(uint64_t key,uint64_t data)'),
    ('probe sentinel', b'if(write)e->key=key,e->data=data;', b'if(data)e->key=key,e->data=data;'),
    ('TT read caller', b'data=probe(key,0,0);', b'data=probe(key,0);'),
    ('TT write caller', b'probe(key,1,data);return best;', b'probe(key,data);return best;'),
    ('consumed selection prefix',
     b'        Move m=moves[j];moves[j]=moves[i];moves[i]=m;\n        int t=scores[j];scores[j]=scores[i];scores[i]=t;\n',
     b'        Move m=moves[j];moves[j]=moves[i];scores[j]=scores[i];\n'))
C_ONLY = (
    ('zero-order function', b'static int tiny_order(const Board *p,Move m){(void)p;(void)m;return 0;}\n', b''),
    ('zero-order caller', b'        scores[i]+=tiny_order(p,m);\n', b''))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def transform(source, family):
    if family not in BASELINES or sha(source) != BASELINES[family] or b'\r' in source:
        raise ValueError('exact LF maintained C/E source required')
    operations = list(COMMON) + (list(C_ONLY) if family == 'C' else [])
    edits = []
    for label, old, new in operations:
        if source.count(old) != 1:
            raise ValueError('sole exact fragment missing: '+label)
        start = source.index(old)
        edits.append((start, start+len(old), label, old, new))
    edits.sort()
    parts, complement, offset, rows = [], [], 0, []
    for start, end, label, old, new in edits:
        if start < offset:
            raise ValueError('overlapping source fragments')
        parts.extend((source[offset:start], new))
        complement.append(source[offset:start])
        rows.append({'label': label, 'start_byte': start, 'line': source[:start].count(b'\n')+1,
                     'old': old.decode(), 'new': new.decode(), 'old_bytes': len(old), 'new_bytes': len(new)})
        offset = end
    parts.append(source[offset:])
    complement.append(source[offset:])
    candidate = b''.join(parts)
    return candidate, {'family': family, 'baseline_bytes': len(source), 'baseline_sha256': sha(source),
        'candidate_bytes': len(candidate), 'candidate_sha256': sha(candidate), 'source_delta': len(candidate)-len(source),
        'exact_edits': rows, 'protected_complement_bytes': sum(map(len, complement)),
        'protected_complement_sha256': sha(b''.join(complement)), 'private_policy_changes': [],
        'clamps_unchanged': True, 'model_and_AVX2_unchanged': True,
        'contract_scope': 'production call graph only: TT writes always carry bound1..3 in bits41..42',
        'runtime_equivalence_not_yet_claimed': True}
