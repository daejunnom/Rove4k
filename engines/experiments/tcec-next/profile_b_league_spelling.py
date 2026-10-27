"""Finite B league atomic spelling for two actual source-JIT projections.

The two named inputs are the actual CI-produced B ``tcec-final-lf`` sources.
This helper owns no engine selection, runtime eligibility or native-image pin.
"""
from hashlib import sha256
import json
import re


SCHEMA = 'rove4k.league-b-atomic.v1'
VARIANT = 'atomic-assignment'
INPUTS = {
    'test-p16': (8010, 'e8f8a5f63ea74b25398dd381b1850a2f72285821fb9a50144760989b574fdd6e'),
    'test-p192': (8038, '665e7a02f9f1c15543ecec4b5bb7b757dc9150af5dd4a366f16e5a8d7d494e06'),
}
SCOPE = ('C11 atomic_int standalone assignment retains sequentially consistent stores; '
         'explicit relaxed/acquire/release operations unchanged')


def pin(data):
    return dict(bytes=len(data), sha256=sha256(data).hexdigest())


def require(value, message):
    if not value:
        raise ValueError(message)


def _rewrite(source):
    """Rewrite exactly five standalone seq-cst stores, preserving all gaps."""
    require(type(source) is bytes, 'atomic input must be bytes')
    text = source.decode('ascii')
    require('atomic_int qp;' in text, 'pinned stop object must remain atomic_int')
    matches = list(re.finditer(r'atomic_store\(&qp,([01])\);', text))
    require(len(matches) == 5, 'pinned standalone atomic stores differ')
    old_at = new_at = 0
    pieces, rows, gaps = [], [], []
    for match in matches:
        before, after = match.group(), 'qp=' + match.group(1) + ';'
        gap = text[old_at:match.start()].encode('ascii')
        pieces.append(gap)
        gaps.append(dict(input_begin=old_at, output_begin=new_at, **pin(gap)))
        new_at += len(gap)
        rows.append(dict(input_begin=match.start(), output_begin=new_at, before=before,
                         after=after, role='implicit-seq-cst-atomic-assignment'))
        pieces.append(after.encode('ascii'))
        new_at += len(after)
        old_at = match.end()
    gap = text[old_at:].encode('ascii')
    pieces.append(gap)
    gaps.append(dict(input_begin=old_at, output_begin=new_at, **pin(gap)))
    return b''.join(pieces), rows, gaps


def transform_source(source, *, family, profile_id, variant):
    require(family == 'B' and profile_id in INPUTS and variant == VARIANT,
            'named B P16/P192 atomic variant required')
    require(type(source) is bytes and (len(source), sha256(source).hexdigest()) == INPUTS[profile_id],
            'exact CI-observed B projection source required')
    candidate, edits, gaps = _rewrite(source)
    require(candidate != source, 'atomic spelling must change source')
    proof = dict(schema=SCHEMA, family=family, profile_id=profile_id, variant=variant,
                 input=pin(source), output=pin(candidate), edits=edits, protected_gaps=gaps,
                 full_inverse=True, scope=SCOPE, resources_changed=False,
                 features_removed=False, production_selected=False)
    return candidate, proof


def restore_source(candidate, proof):
    require(type(candidate) is bytes and type(proof) is dict and proof.get('schema') == SCHEMA
            and pin(candidate) == proof.get('output'), 'exact candidate and B atomic proof required')
    old = candidate
    for row in reversed(proof['edits']):
        at, before, after = row['output_begin'], row['before'].encode('ascii'), row['after'].encode('ascii')
        require(type(at) is int and at >= 0 and old[at:at + len(after)] == after,
                'atomic inverse span differs')
        old = old[:at] + before + old[at + len(after):]
    repeated, expected = transform_source(old, family=proof['family'],
                                          profile_id=proof['profile_id'], variant=proof['variant'])
    require(repeated == candidate and json.dumps(proof, sort_keys=True, allow_nan=False) ==
            json.dumps(expected, sort_keys=True, allow_nan=False),
            'full atomic inverse or typed protected gaps differ')
    return old
