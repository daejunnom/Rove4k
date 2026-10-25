"""Reproduce the one frozen A4739 capture-only bit3 source proposal."""
import hashlib
import json
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def transform(source):
    fixed = json.loads(Path(__file__).with_name('fixed.json').read_bytes())
    old = fixed['control']
    new = fixed['candidate']
    if type(source) is not bytes or len(source) != old['bytes'] or sha(source) != old['sha256']:
        raise ValueError('exact current A4739 shipping source required')
    parts = []
    gaps = []
    last = offset = 0
    for row in fixed['regions']:
        a, b = row['old_start'], row['old_end']
        before, after = row['old'].encode(), row['new'].encode()
        if a < last or source[a:b] != before or source.count(before) != 1:
            raise ValueError('exact source span/order differs: ' + row['role'])
        gap = source[last:a]
        parts.extend((gap, after))
        gaps.append(gap)
        offset += len(gap)
        if row['new_start'] != offset or row['new_end'] != offset + len(after):
            raise ValueError('fixed output region offset differs')
        offset += len(after)
        last = b
    parts.append(source[last:])
    gaps.append(source[last:])
    candidate = b''.join(parts)
    inverse = candidate
    for row in reversed(fixed['regions']):
        a, b = row['new_start'], row['new_end']
        if inverse[a:b] != row['new'].encode():
            raise ValueError('inverse preimage differs')
        inverse = inverse[:a] + row['old'].encode() + inverse[b:]
    if inverse != source or len(candidate) != new['bytes'] or sha(candidate) != new['sha256']:
        raise ValueError('fixed candidate or raw inverse differs')
    if sum(map(len, gaps)) != fixed['untouched_complement_bytes'] or sha(b''.join(gaps)) != fixed['untouched_complement_sha256']:
        raise ValueError('protected source complement differs')
    return candidate, {
        'regions': fixed['regions'], 'exact_inverse': True,
        'protected_complement_bytes': sum(map(len, gaps)),
        'protected_complement_sha256': sha(b''.join(gaps)),
        'FROM_mask': 119, 'capture_bit': 3, 'TT_move_bits': 17,
        'tag0_quiet_castle_doublepush': 0, 'tag1_nonpawn_capture': 1,
        'tag2_single_pawn_push': 2, 'tag3_pawn_capture_or_EP': 3,
        'quiet_promotion_capture_bit': 0,
        'B_promotion_inclusive_tactical_policy_imported': False,
        'private_Move_ABI_changed': True,
        'runtime_or_compiler_equivalence_proved': False,
        'F_autoapplication': False,
    }
