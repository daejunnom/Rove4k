"""Exact A/C/E/full-F league projections for C11 atomic assignment.

Inputs are the P16/P192 control resource projections observed in CI run
40530103670. This is an opt-in source experiment, not a selected producer,
runtime qualification, or evidence of a smaller complete submission.
"""
from hashlib import sha256
import json
import re


SCHEMA = 'rove4k.league-acef-atomic.v1'
VARIANT = 'atomic-assignment'
INPUTS = {
    ('A', 'test-p16'): (7868, 'dfea3d86ab55b725ebc09e37b00a4053be1039b5bcd50b0c73d82aaaaf5c4ead'),
    ('A', 'test-p192'): (7869, 'c02da48b86de955f13f7d0442d5a1804e3eb91253d15160186a72dd116c0d910'),
    ('C', 'test-p16'): (8502, 'd85638b93ceefd6ad937d2f157d9d6e0af3f03d5cfab7fec42a5c150bd6ea4d8'),
    ('C', 'test-p192'): (8503, '9a41fa67f547f0074bfb7a2fdd0ca124b6da68027455741b558d06461d6e5e2d'),
    ('E', 'test-p16'): (8061, '996ae7e3ea1becb7c8d6a37a89385ab1297fc219ccf8c387978747941aa27006'),
    ('E', 'test-p192'): (8062, 'ddc4412e5b033cda3372e070676f8686180231ff85adfc0200518bde59a8af2f'),
    ('F', 'test-p16'): (7296, '9cf612e94b59dc5519a18ae59dc34772b04821707b843ba31ce7eb271f5c7b76'),
    ('F', 'test-p192'): (7297, '2aabca27a041aa31ee819ae4381df4b63192b5fcc5dde26123763f8709c5414f'),
}
TARGETS = {'A': ('X', 4), 'C': ('qp', 4), 'E': ('qp', 4), 'F': ('V', 5)}
SCOPE = ('C11 atomic_int standalone assignment retains sequentially consistent stores; '
         'explicit relaxed/acquire/release operations unchanged')


def pin(data):
    return {'bytes': len(data), 'sha256': sha256(data).hexdigest()}


def require(value, message):
    if not value:
        raise ValueError(message)


def _rewrite(source, *, family):
    """Rewrite only the reviewed target object's complete standalone stores."""
    require(type(source) is bytes and family in TARGETS, 'reviewed atomic source and family required')
    text = source.decode('ascii')
    name, count = TARGETS[family]
    declaration = 'atomic_int ' + name + ';'
    require(text.count(declaration) == 1, 'pinned target must be a unique atomic_int')
    matches = list(re.finditer(r'atomic_store\(&' + re.escape(name) + r',([01])\);', text))
    require(len(matches) == count and text.count('atomic_store(') == count,
            'pinned standalone atomic stores differ')
    old_at = new_at = 0
    pieces, rows, gaps = [], [], []
    for match in matches:
        before, after = match.group(), name + '=' + match.group(1) + ';'
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
    require((family, profile_id) in INPUTS and variant == VARIANT,
            'named A/C/E/F P16/P192 atomic variant required')
    require(type(source) is bytes and (len(source), sha256(source).hexdigest()) == INPUTS[(family, profile_id)],
            'exact CI-observed resource projection required')
    candidate, edits, gaps = _rewrite(source, family=family)
    require(candidate != source, 'atomic spelling must change source')
    proof = dict(schema=SCHEMA, family=family, profile_id=profile_id, variant=variant,
                 input=pin(source), output=pin(candidate), edits=edits, protected_gaps=gaps,
                 full_inverse=True, scope=SCOPE, resources_changed=False,
                 features_removed=False, production_selected=False)
    return candidate, proof


def restore_source(candidate, proof):
    require(type(candidate) is bytes and type(proof) is dict and proof.get('schema') == SCHEMA
            and pin(candidate) == proof.get('output'), 'exact candidate and atomic proof required')
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
