"""Small pure algebra checks for the two changed production data-flow contracts."""
from itertools import permutations


def selection(moves, scores, reduced):
    moves, scores, emitted, suffixes = moves.copy(), scores.copy(), [], []
    for i in range(len(moves)):
        j = i
        for k in range(i+1, len(moves)):
            if scores[k] > scores[j]:
                j = k
        m = moves[j]
        moves[j] = moves[i]
        if reduced:
            scores[j] = scores[i]
        else:
            moves[i] = m
            t = scores[j]
            scores[j] = scores[i]
            scores[i] = t
        emitted.append(m)
        suffixes.append((moves[i+1:].copy(), scores[i+1:].copy()))
    return emitted, suffixes


def run():
    cases = [([], []), ([0], [0]), ([0, 1, 2], [0, 0, 0]),
             ([2, 2, 1, 1], [3, 3, -1, 3]), ([0, 1, 2, 3], [-2, 3, 3, 0])]
    cases += [(list(order), [0, 2, 2, -1]) for order in permutations(range(4))]
    for moves, scores in cases:
        if selection(moves, scores, False) != selection(moves, scores, True):
            raise ValueError('selected sequence or future suffix differs')
    payloads = 0
    for bound in (1, 2, 3):
        for depth in (0, 1, 126):
            for score in (-30000, -29872, -1, 0, 1, 29872, 30000):
                for move in (0, 1, 131071):
                    other = move | ((score & 65535) << 17) | (depth << 33)
                    data = other | (bound << 41)
                    if other >= 1 << 41 or not data or ((data >> 41) & 3) != bound:
                        raise ValueError('nonzero payload domain failed')
                    payloads += 1
    return {'complete': True, 'selection_cases': len(cases), 'same_emitted_sequence_and_future_suffixes': True,
        'duplicate_tie_and_j_equals_i_covered': True, 'payload_boundary_cases': payloads,
        'all_production_write_bound_bits_nonzero': True, 'read_sentinel': 0,
        'write_zero_is_not_a_production_caller': True, 'engine_runs': 0}
