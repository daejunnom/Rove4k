"""Pure fixed shipping integer forms, applied after material-state replay.

Fixed Linux x86-64 unsigned64 decimal admission; six sole final limits
includes removed, C late intrinsic include premise preserved. Only full F
and material F also remove their two fixed positive TT18 size_t casts.
DEV bypass is the caller's responsibility. No external file is read.
"""
import hashlib


# Actual numeric cost: 4b7cec0d6e7019a4a094a67925ea77bb5943acd4fb5cf0d40ec02fa0b9b9b26c
# Actual F numeric+cast cost: bc988d78c19ef8b458c93d6873aa023ec826bcc23bce19a634ece73a889ab086
_CASES = {
    ('A', 'full'): (
        (9125, 'e427db6e5697679c4765d4b0842dbfebe9637cffd1c2d1e48c3787f8fc43964b'),
        (9082, '038ec565e9ad3ae339fe2830165ab0f621455024ab8aea5b2da861a925a78945'),
        ('unsigned64-number-local', 'high-bit-signed64-admission', 'sole-final-limits-header-removed'),
        (
            (175, 175, b'#include <limits.h>\n', b''),
            (7772, 7752, b"static W y(const char*s){char*e;if(!s||(unsigned)(*s-'0')>9)return 0;unsigned long long n=strtoull(s,&e,10);return*e||n>LLONG_MAX?0:n;}", b"static W y(const char*s){char*e;if(!s||(unsigned)(*s-'0')>9)return 0;W n=strtoull(s,&e,10);return*e||n>>63?0:n;}"),
        ),
    ),
    ('B', 'full'): (
        (10745, '1aa26d8fcff91a0e38403211a72a0f52f464711a0462c7b611f4d112668ea5c1'),
        (10702, 'e15c61670e2addc01fa66432c3066fabb7b01f509bd84d9baa1f2d45095d4790'),
        ('unsigned64-number-local', 'high-bit-signed64-admission', 'sole-final-limits-header-removed'),
        (
            (175, 175, b'#include <limits.h>\n', b''),
            (9235, 9215, b"static D G(const char*s){char*e;if(!s||(unsigned)(*s-'0')>9)return 0;unsigned long long n=strtoull(s,&e,10);return*e||n>LLONG_MAX?0:n;}", b"static D G(const char*s){char*e;if(!s||(unsigned)(*s-'0')>9)return 0;D n=strtoull(s,&e,10);return*e||n>>63?0:n;}"),
        ),
    ),
    ('C', 'full'): (
        (10174, 'e3af22b2404d37187076ee676c51446aa561ac8cd14583b37d3da2529d9190a7'),
        (10151, 'd9f1faf12264af8b16699ed7e2aeb2bea37363019d17586be1d62d638aa6692f'),
        ('unsigned64-number-local', 'high-bit-signed64-admission'),
        (
            (8705, 8705, b"static M F(const char*s){char*e;if(!s||(unsigned)(*s-'0')>9)return 0;unsigned long long n=strtoull(s,&e,10);return*e||n>LLONG_MAX?0:n;}", b"static M F(const char*s){char*e;if(!s||(unsigned)(*s-'0')>9)return 0;M n=strtoull(s,&e,10);return*e||n>>63?0:n;}"),
        ),
    ),
    ('E', 'full'): (
        (10624, '75a6e0211afb6c6200327bf4d27dd3ed1a8cc4c7ded480e5bc25805a447ccfb7'),
        (10581, 'ddefebddc717011f8652165925dde4a6e0518bb321eacce932ef9b1afa721929'),
        ('unsigned64-number-local', 'high-bit-signed64-admission', 'sole-final-limits-header-removed'),
        (
            (175, 175, b'#include <limits.h>\n', b''),
            (8969, 8949, b"static I D(const char*s){char*e;if(!s||(unsigned)(*s-'0')>9)return 0;unsigned long long n=strtoull(s,&e,10);return*e||n>LLONG_MAX?0:n;}", b"static I D(const char*s){char*e;if(!s||(unsigned)(*s-'0')>9)return 0;I n=strtoull(s,&e,10);return*e||n>>63?0:n;}"),
        ),
    ),
    ('F', 'full'): (
        (9109, '2542ab10fd598d5496a4f34a6f22f3e048c64c2cbf1a5396f1c33a8a7da5b6e6'),
        (9050, 'fe854d32f8fe7c78f08512f40dbc4e99a74666d164528e9d9cb54f72e0dfee49'),
        ('unsigned64-number-local', 'high-bit-signed64-admission', 'sole-final-limits-header-removed', 'fixed-positive-TT18-casts'),
        (
            (175, 175, b'#include <limits.h>\n', b''),
            (7376, 7356, b'for(size_t i=0;i<((size_t)1<<18);i++)atomic_flag_clear(&qq[i].zN);', b'for(size_t i=0;i<(1<<18);i++)atomic_flag_clear(&qq[i].zN);'),
            (7748, 7720, b"static W A(const char*s){char*e;if(!s||(unsigned)(*s-'0')>9)return 0;unsigned long long n=strtoull(s,&e,10);return*e||n>LLONG_MAX?0:n;}", b"static W A(const char*s){char*e;if(!s||(unsigned)(*s-'0')>9)return 0;W n=strtoull(s,&e,10);return*e||n>>63?0:n;}"),
            (8387, 8336, b'qq=calloc((size_t)1<<18,sizeof*qq);', b'qq=calloc(1<<18,sizeof*qq);'),
        ),
    ),
    ('F', 'material-noise'): (
        (8604, '4867a0fdc8376359464e3eeb64c2dc6d441b9d57eadc8d0c4b9b4257f179db1f'),
        (8545, '918a6837918d83d692c816062063c4085e847efb897c74eea68ce850c77f6fd2'),
        ('unsigned64-number-local', 'high-bit-signed64-admission', 'sole-final-limits-header-removed', 'fixed-positive-TT18-casts'),
        (
            (175, 175, b'#include <limits.h>\n', b''),
            (6767, 6747, b'for(size_t i=0;i<((size_t)1<<18);i++)atomic_flag_clear(&qq[i].zN);', b'for(size_t i=0;i<(1<<18);i++)atomic_flag_clear(&qq[i].zN);'),
            (7158, 7130, b"static W B(const char*s){char*e;if(!s||(unsigned)(*s-'0')>9)return 0;unsigned long long n=strtoull(s,&e,10);return*e||n>LLONG_MAX?0:n;}", b"static W B(const char*s){char*e;if(!s||(unsigned)(*s-'0')>9)return 0;W n=strtoull(s,&e,10);return*e||n>>63?0:n;}"),
            (7872, 7821, b'qq=calloc((size_t)1<<18,sizeof*qq);', b'qq=calloc(1<<18,sizeof*qq);'),
        ),
    ),
    ('F', 'material-move-tt'): (
        (7821, '8352665bca27f8c17c8ba1eeede04ddf0abaf70d88bebb5d70c6104c0c3481ec'),
        (7778, 'e94399e7bec9ab24d6bc144986e38033bf0db92e89427bbea955a0839155517b'),
        ('unsigned64-number-local', 'high-bit-signed64-admission', 'sole-final-limits-header-removed'),
        (
            (175, 175, b'#include <limits.h>\n', b''),
            (6493, 6473, b"static W B(const char*s){char*e;if(!s||(unsigned)(*s-'0')>9)return 0;unsigned long long n=strtoull(s,&e,10);return*e||n>LLONG_MAX?0:n;}", b"static W B(const char*s){char*e;if(!s||(unsigned)(*s-'0')>9)return 0;W n=strtoull(s,&e,10);return*e||n>>63?0:n;}"),
        ),
    ),
}


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def transform_source(source, *, family, policy='full'):
    """Replay only the admitted literal spans and preserve every other byte."""
    if type(source) is not bytes or b'\r' in source:
        raise ValueError('integer forms require immutable LF source bytes')
    case = _CASES.get((family, policy))
    if case is None:
        raise ValueError('unsupported integer-forms family/policy')
    before, after, features, edits = case
    if (len(source), _sha(source)) != before:
        raise ValueError('integer-forms input differs from fixed material-state output')
    parts, remainder = [], []
    cursor = output_cursor = 0
    for start, target, old, new in edits:
        end = start + len(old)
        if start < cursor or source[start:end] != old:
            raise ValueError('integer-forms literal preimage differs or overlaps')
        untouched = source[cursor:start]
        if output_cursor + len(untouched) != target:
            raise ValueError('integer-forms target offset differs')
        parts.extend((untouched, new)); remainder.append(untouched)
        cursor = end; output_cursor = target + len(new)
    parts.append(source[cursor:]); remainder.append(source[cursor:])
    candidate = b''.join(parts)
    if (len(candidate), _sha(candidate)) != after:
        raise ValueError('integer-forms selected source differs')
    inverse = candidate
    for start, target, old, new in reversed(edits):
        if inverse[target:target + len(new)] != new:
            raise ValueError('integer-forms inverse literal differs')
        inverse = inverse[:target] + old + inverse[target + len(new):]
    if inverse != source:
        raise ValueError('integer-forms exact inverse failed')
    actual_remainder = []; cursor = 0
    for start, target, old, new in edits:
        if target < cursor or candidate[target:target + len(new)] != new:
            raise ValueError('integer-forms candidate literal differs')
        actual_remainder.append(candidate[cursor:target]); cursor = target + len(new)
    actual_remainder.append(candidate[cursor:])
    if actual_remainder != remainder:
        raise ValueError('integer-forms unchanged complement differs')
    unchanged = b''.join(remainder)
    return candidate, {
        'stage': 'fixed-shipping-integer-forms', 'family': family, 'policy': policy,
        'input_bytes': before[0], 'input_sha256': before[1],
        'output_bytes': after[0], 'output_sha256': after[1],
        'features': list(features), 'literal_edits': len(edits), 'exact_inverse': True,
        'unchanged_complement_bytes': len(unchanged),
        'unchanged_complement_sha256': _sha(unchanged),
    }
