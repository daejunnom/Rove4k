"""One fixed F unit-window bound predicate; no TT policy or horizon changes."""
import hashlib

INPUT_BYTES = 9464
INPUT_SHA256 = 'd942731c54f82da8dfa1aa5fedcc6328b56b32fe0ab527b5396847ceea541f26'
OLD = b'if(f&&I&&J==(a>0?a:0)&&(I==1||(I==2&&H>=d)||(I==3&&H<d)))return H;'
NEW = b'if(f&&I&&J==(a>0?a:0)&&I!=2+(H>=d))return H;'
READABLE_OLD = 'if(ply&&bound&&ttdepth==(depth>0?depth:0)&&(bound==1||(bound==2&&score>=beta)||(bound==3&&score<beta)))return score;'
READABLE_NEW = 'if(ply&&bound&&ttdepth==(depth>0?depth:0)&&bound!=2+(score>=beta))return score;'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def transform(source):
    if type(source) is not bytes or len(source) != INPUT_BYTES or sha(source) != INPUT_SHA256:
        raise ValueError('exact maintained F9464 source required')
    if source.count(OLD) != 1 or NEW in source:
        raise ValueError('one original guarded predicate and no replacement required')
    role = {'ply': 'f', 'bound': 'I', 'ttdepth': 'J', 'depth': 'a', 'score': 'H', 'beta': 'd'}
    import re
    project = lambda text: re.sub(r'[A-Za-z_][A-Za-z_0-9]*', lambda m: role.get(m[0], m[0]), text).encode()
    if project(READABLE_OLD) != OLD or project(READABLE_NEW) != NEW:
        raise ValueError('readable/physical role projection differs')
    rows = []
    for high, expected in [(False, (False, True, False, True)), (True, (False, True, True, False))]:
        for bound in range(4):
            old = bool(bound) and (bound == 1 or bound == 2 and high or bound == 3 and not high)
            new = bool(bound) and bound != 2 + high
            if old != expected[bound] or new != expected[bound]:
                raise ValueError('fixed bound truth table differs')
            rows.append({'bound': bound, 'score_ge_beta': high, 'old': old, 'new': new})
    before, after = source.split(OLD)
    candidate = before + NEW + after
    if candidate.count(NEW) != 1 or candidate.replace(NEW, OLD) != source:
        raise ValueError('exact inverse failed')
    return candidate, {
        'old_fragment': OLD.decode(), 'new_fragment': NEW.decode(),
        'readable_old': READABLE_OLD, 'readable_new': READABLE_NEW,
        'role_projection': role, 'bound_codes': {'0': 'empty gate', '1': 'exact', '2': 'lower', '3': 'upper'},
        'truth_table': rows, 'exact_inverse': True,
        'protected_complement_bytes': len(before) + len(after),
        'protected_complement_sha256': sha(before + after),
        'source_bytes_before': len(source), 'source_bytes_after': len(candidate),
        'source_sha256_after': sha(candidate),
        'unchanged': ['full-key coherent TT', 'exact requested horizon including QS0', 'root cutoff disabled',
                      'mate adjustment', 'MTD lower/upper/witness', 'TT payload/flags', 'model', 'pool', 'input'],
    }
