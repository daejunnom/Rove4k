"""Opt-in final shipping transformations; historical pack_stream stays unchanged.

Only the seven fixed current two-worker/TT18 shipping sources admit guard
removal; A/C/E also omit two redundant fixed-bound casts. Literal selection
reuses the caller's previous API and all fallbacks.
"""
import hashlib
import re


# (input bytes, input SHA-256, output SHA-256), before/after the sole empty guard.
_DOMAINS = {
    ('A', 'full'): (9256, 'c5e2d2994ea12df6df8b3152c2c89a00f787ee03ae09b1d546c9082145b5c56d', '2a0059c489b54dfd0cb73dc8968656a8f725d2bb7e647803820843a9d691be2e'),
    ('B', 'full'): (10957, 'c3a86dd9d442356dde5150588c396caf86deb53401c09d15572db4fd5973bec5', 'c3b68e0957d7068abce346083785de8f8cabb8104eefead83a18fb15efa45488'),
    ('C', 'full'): (10305, '597b74bd71a843b58be58944c6763d09a31159caaf571c9dc80d39253beadbab', 'd85bfe7ff4d24c7d78f37273aa6355fd607c7b445e1c28c2e78efb3d2a7b0706'),
    ('E', 'full'): (10755, '7577ff9c4e23393534cf396e12a88e64cf44a0c73014f78154d8d9fa791b97b1', 'd984e9db86824655e1badc5a0e12cc113585b912397f918585777a4e4e839a6b'),
    ('F', 'full'): (9242, '61e0f5c7f79b6c45efd225624def06bb1ac3c1b1edfe1cd0443c0f3498a4a447', '19d0f155724d3455e36f3e424bb55618d9e83417a42b75e7c0ada846cd0f44ce'),
    ('F', 'material-noise'): (8602, '3752a0c745efb63a2c1ba08974789c10dc56b815428d11903fbc8f2b5461ea3b', '8080a7fb2f76d5abaebbc8697b6b12a46e242365ebed1f2f43f7980824c18378'),
    ('F', 'material-move-tt'): (8130, 'c63cf3d6216c9b9376c08a1f8ca753170b3b322536b31b39b45cf188ea3e2a47', 'cbe891f12a682b9cb702734bc88f0183a5bfb9bafa62a5d55d471864228b7572'),
}
_GUARD = b'#define TINY_H \n'
# Fixed Linux x86-64 int32/size_t64, TT18: 1<<18 is positive int262144.
# calloc converts that value to size_t; the size_t loop comparison does likewise.
# These exact owned roles exclude sizeof/_Generic/typeof and generic TT sizes.
_A_CASTS = (
    ('TT-clear-size_t-loop', b'for(size_t i=0;i<((size_t)1<<18);i++)atomic_flag_clear(&qq[i].zN);'),
    ('TT-calloc-size_t-parameter', b'qq=calloc((size_t)1<<18,sizeof*qq);'),
)
_CE_CASTS = (
    ('TT-clear-size_t-loop', b'for(size_t i=0;i<((size_t)1<<18);i++){table[i].zP=table[i].zA=0;atomic_flag_clear(&table[i].zY);}'),
    ('TT-calloc-size_t-parameter', b'table=calloc((size_t)1<<18,sizeof*table);'),
)
_CAST_OUTPUTS = {
    'A': ('fcb758088195b0e545573fe32f081a27bdf0370bf4adbb15528e531288742f09', _A_CASTS),
    'C': ('30e6ed94b9cd1a63cf07235b90742af35c21854b6e760290ee23e6907561c9dd', _CE_CASTS),
    'E': ('2d15040aa4f916f9f07c4f81eee1e56c59bc15944b55bd48952be02128804e72', _CE_CASTS),
}


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def transform_source(source, *, family, policy='full'):
    """Remove the unused guard and eligible casts in fixed shipping sources."""
    domain = _DOMAINS.get((family, policy))
    if domain is None:
        raise ValueError('unsupported shipping family/policy')
    size, before, after = domain
    if type(source) is not bytes or len(source) != size or _sha(source) != before:
        raise ValueError('shipping common input differs from the fixed source')
    offset = 1
    names = list(re.finditer(rb'\bTINY_H\b', source))
    if (b'\r' in source or source[:offset] != b'\n' or source.count(_GUARD) != 1
            or source[offset:offset + len(_GUARD)] != _GUARD
            or len(names) != 1 or names[0].start() != offset + len(b'#define ')):
        raise ValueError('guard is not the sole exact empty owned definition')
    candidate = source[:offset] + source[offset + len(_GUARD):]
    if candidate[:offset] + _GUARD + candidate[offset:] != source:
        raise ValueError('shipping common positional inverse failed')
    if _sha(candidate) != after:
        raise ValueError('shipping common output/remainder differs')
    metadata = {
        'stage': 'late-shipping-unused-owned-guard', 'family': family, 'policy': policy,
        'input_bytes': len(source), 'input_sha256': before,
        'output_bytes': len(candidate), 'output_sha256': after,
        'guard_offset': offset, 'removed_bytes': len(_GUARD),
        'sole_identifier_and_empty_directive': True, 'exact_inverse': True,
        'unchanged_remainder_bytes': len(candidate), 'unchanged_remainder_sha256': after,
    }
    if family in _CAST_OUTPUTS and policy == 'full':
        final_sha, roles = _CAST_OUTPUTS[family]
        guarded = candidate
        if guarded.count(b'(size_t)1<<18') != 2:
            raise ValueError('fixed TT18 cast count changed')
        edits = []
        for role, old in roles:
            if old.count(b'(size_t)') != 1 or candidate.count(old) != 1:
                raise ValueError('fixed TT18 cast role changed: ' + role)
            new = old.replace(b'(size_t)', b'', 1)
            edits.append((role, old, new))
            candidate = candidate.replace(old, new, 1)
        inverse = candidate
        old_remainder, new_remainder = guarded, candidate
        for role, old, new in reversed(edits):
            if inverse.count(new) != 1:
                raise ValueError('fixed TT18 inverse context changed: ' + role)
            inverse = inverse.replace(new, old, 1)
            old_remainder = old_remainder.replace(old, b'', 1)
            new_remainder = new_remainder.replace(new, b'', 1)
        if inverse != guarded or old_remainder != new_remainder:
            raise ValueError('fixed TT18 inverse or unchanged complement differs')
        if len(candidate) != len(guarded) - 16 or _sha(candidate) != final_sha:
            raise ValueError('fixed TT18 final output differs')
        metadata.update(
            stage='late-shipping-owned-guard-and-fixed-TT18-casts',
            guard_output_bytes=len(guarded), guard_output_sha256=after,
            unchanged_remainder_scope='guard deletion, before the fixed cast stage',
            output_bytes=len(candidate), output_sha256=final_sha,
            fixed_TT18_casts=[{'role': role, 'guarded_offset': guarded.index(old),
                              'final_offset': candidate.index(new), 'removed_bytes': 8}
                             for role, old, new in edits],
            cast_exact_inverse=True, cast_complement_sha256=_sha(old_remainder),
        )
    return candidate, metadata


def source_literal(source, previous):
    expression, kind = previous(source)
    if source.isascii() and kind in ('raw-single', 'raw-double'):
        quote = "'''" if kind == 'raw-single' else '"""'
        if not expression.startswith('r' + quote) or not expression.endswith(quote + '.encode()'):
            raise ValueError('the pinned current raw-string envelope changed')
        return 'b' + expression[:-len('.encode()')], 'raw-bytes-' + kind[4:]
    return expression, kind
