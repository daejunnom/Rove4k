"""One exact B6219 source architecture experiment; no tuning or shared edits."""
import hashlib
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
READABLE_SHA256 = '1f879828346dfbc6023f6abfbbf1e1d2062e8e2dc0e9919aade254ba7a0a97f6'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def region(text, signature):
    if text.count(signature) != 1:
        raise ValueError('exact function signature changed: ' + signature)
    start = text.index(signature)
    i = text.index('{', start) + 1
    depth = 1
    while depth:
        if text.startswith('//', i):
            end = text.find('\n', i)
            i = len(text) if end < 0 else end + 1
            continue
        if text.startswith('/*', i):
            i = text.index('*/', i) + 2
            continue
        if text[i] in ('"', "'"):
            quote = text[i]
            i += 1
            while text[i] != quote:
                i += 2 if text[i] == '\\' else 1
            i += 1
            continue
        depth += (text[i] == '{') - (text[i] == '}')
        i += 1
    return start, i


def transform(source):
    if sha(source) != READABLE_SHA256:
        raise ValueError('exact qualified B6219 readable source required')
    text = source.decode()
    if '\r' in text:
        raise ValueError('exact LF source required')
    first, last = region(text, 'int gen(const Board *p,Move *moves){')
    begin, end = region(text, 'static int exchange(Exchange *e,const Board *p,int target){')
    exchange = text[begin:end]
    body = exchange.index('    int best=0;uint64_t candidates=attackers(p,target,p->s);')
    tail = exchange.index('    return best;')
    templates = {name: (HERE / name).read_bytes() for name in ('generate.c.in', 'exchange-loop.c.in')}
    if any(b'\r' in value for value in templates.values()):
        raise ValueError('LF templates required')
    patches = [(first, last, templates['generate.c.in'].decode().rstrip('\n')),
               (begin + body, begin + tail, templates['exchange-loop.c.in'].decode())]
    patches.sort()
    output, retained, retained_positions = [], [], []
    at = 0
    offset = 0
    for a, b, replacement in patches:
        if a < at:
            raise ValueError('overlapping source patches')
        unchanged = text[at:a]
        output.append(unchanged)
        retained.append(unchanged)
        retained_positions.append((offset, offset + len(unchanged)))
        offset += len(unchanged)
        output.append(replacement)
        offset += len(replacement)
        at = b
    output.append(text[at:])
    retained.append(text[at:])
    retained_positions.append((offset, offset + len(text[at:])))
    result = ''.join(output)
    before = ''.join(retained)
    after = ''.join(result[a:b] for a, b in retained_positions)
    if before != after:
        raise ValueError('source outside exact two replacement regions changed')
    return result.encode(), {
        'scope': 'one target-centered B generator shared by ordinary generation and exact SEE',
        'baseline_readable_sha256': sha(source), 'candidate_readable_sha256': sha(result.encode()),
        'protected_complement_sha256': sha(before.encode()), 'protected_complement_bytes': len(before.encode()),
        'protected_complement_identical': True,
        'retained': ['mailbox/bitboard put/make', 'hash/ordered path/halfmove', 'attackers king safety',
                     'coherent full-key TT', 'PVS/QS/learning', 'qualified singular/excluded fences',
                     'SEE original deadline/stop/visit guard/incomplete propagation', 'startup pool/minimal UCI'],
        'policy_change': 'target-square order replaces source/direction order; SEE follows same target emitter',
        'generation_attack_queries_upper_bound': 64,
        'SEE_target_mode': 'one occupied enemy target only; negative sentinel is ordinary all-target mode',
        'performance': 'unmeasured; up to64 reverse attack queries per ordinary generation can be substantially slower',
        'SEE_stack_array': {'moves': 512, 'bytes': 2048, 'simultaneous_exchange_frames_upper_bound': 31,
                            'array_bytes_upper_bound': 63488, 'whole_frame_bytes': 'not yet measured',
                            'new_stack_proof_required': True},
        'template_sha256': {name: sha(data) for name, data in templates.items()},
    }
