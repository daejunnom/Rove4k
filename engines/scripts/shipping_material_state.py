"""Pure late replay of seven fixed shipping material classifiers.

Apply after shipping_refinements. Preserve the existing limited classifier
policy: KNN stays live; same-square-color bishops may be recognized dead.
This is not a general insufficient-material or runtime qualification claim.
Only literal function bytes change; this module reads no external files.
"""
import hashlib


# Full four-case proposal: c0bc8a6e208dc54a0d5fadb1564ea53db0b46eee99c3ba20d5b28fa939cced92
# Cost receipts: 7f4e8e47ae66fa3304207ae3e0b9e8e5d65869ce09518f9919312f662f9f2f27
# and 9762dba0aebfa66c32b72470b03e3657f6bd65a51d2ba0ef74bfdba9c7b96f03.
# B full cost receipt: e560dabc21d1bc584fce7993c47c7c3a4512cbaeb82a2abe9a33e792a7985f20
# Tuple fields: before pin, after pin, byte offset, old/new full function.
_CASES = {
    ('A', 'full'): (
        (9107, 'dc6d43dee4eec5f0f5a785cab6f6ece822b7083f50a841b53d6978f5c34ebfdd'),
        (9125, 'e427db6e5697679c4765d4b0842dbfebe9637cffd1c2d1e48c3787f8fc43964b'),
        1646,
        b'int ap(const E*p){int d=0,f=0,g=0;for(int q=0;q<128;q++)if(!(q&0x88)){int a=abs(p->b[q]);if(a==2){d++;f++;}else if(a==3){d++;g|=1<<((q+(q>>4))&1);}else if(a&&a<6)return 0;}return d<2||(!f&&g!=3);}',
        b'int ap(const E*p){int d=0;for(int q=0;q<128;q++)if(!(q&0x88)){int a=abs(p->b[q]);if(a==2){if(d)return 0;d=-1;}else if(a==3){if(d<0)return 0;d|=1<<((q+(q>>4))&1);if(d==3)return 0;}else if(a&&a<6)return 0;}return 1;}',
    ),
    ('B', 'full'): (
        (10727, '9715f9df054922568346484d1ac15458910f22650466f34f2ebfa7823ab056b4'),
        (10745, '1aa26d8fcff91a0e38403211a72a0f52f464711a0462c7b611f4d112668ea5c1'),
        2641,
        b'int y(const za*p){int d=0,f=0,i=0;for(int q=0;q<128;q++)if(!(q&0x88)){int a=abs(p->b[q]);if(a==2){d++;f++;}else if(a==3){d++;i|=1<<((q+(q>>4))&1);}else if(a&&a<6)return 0;}return d<2||(!f&&i!=3);}',
        b'int y(const za*p){int d=0;for(int q=0;q<128;q++)if(!(q&0x88)){int a=abs(p->b[q]);if(a==2){if(d)return 0;d=-1;}else if(a==3){if(d<0)return 0;d|=1<<((q+(q>>4))&1);if(d==3)return 0;}else if(a&&a<6)return 0;}return 1;}',
    ),
    ('C', 'full'): (
        (10156, '316a2704f2f7b5746fccfdb98f8f9b76a8004af68481eb32e7024b1d2b7b9bab'),
        (10174, 'e3af22b2404d37187076ee676c51446aa561ac8cd14583b37d3da2529d9190a7'),
        1770,
        b'int s(const za*p){int d=0,f=0,i=0;for(int q=0;q<128;q++)if(!(q&0x88)){int a=abs(p->b[q]);if(a==2){d++;f++;}else if(a==3){d++;i|=1<<((q+(q>>4))&1);}else if(a&&a<6)return 0;}return d<2||(!f&&i!=3);}',
        b'int s(const za*p){int d=0;for(int q=0;q<128;q++)if(!(q&0x88)){int a=abs(p->b[q]);if(a==2){if(d)return 0;d=-1;}else if(a==3){if(d<0)return 0;d|=1<<((q+(q>>4))&1);if(d==3)return 0;}else if(a&&a<6)return 0;}return 1;}',
    ),
    ('E', 'full'): (
        (10606, '684f3d0aec72718d18eb72bff1d03efa84b97b8d1abbdb5847dd4c47362aee9e'),
        (10624, '75a6e0211afb6c6200327bf4d27dd3ed1a8cc4c7ded480e5bc25805a447ccfb7'),
        1770,
        b'int r(const za*p){int d=0,f=0,i=0;for(int q=0;q<128;q++)if(!(q&0x88)){int a=abs(p->b[q]);if(a==2){d++;f++;}else if(a==3){d++;i|=1<<((q+(q>>4))&1);}else if(a&&a<6)return 0;}return d<2||(!f&&i!=3);}',
        b'int r(const za*p){int d=0;for(int q=0;q<128;q++)if(!(q&0x88)){int a=abs(p->b[q]);if(a==2){if(d)return 0;d=-1;}else if(a==3){if(d<0)return 0;d|=1<<((q+(q>>4))&1);if(d==3)return 0;}else if(a&&a<6)return 0;}return 1;}',
    ),
    ('F', 'full'): (
        (9091, '7cc8d24d3080d4c0af177413e5441f7fb4141e3fb28175e9e0489b78291dfd68'),
        (9109, '2542ab10fd598d5496a4f34a6f22f3e048c64c2cbf1a5396f1c33a8a7da5b6e6'),
        1614,
        b'int af(const za*p){int d=0,f=0,g=0;for(int q=0;q<128;q++)if(!(q&0x88)){int a=abs(p->b[q]);if(a==2){d++;f++;}else if(a==3){d++;g|=1<<((q+(q>>4))&1);}else if(a&&a<6)return 0;}return d<2||(!f&&g!=3);}',
        b'int af(const za*p){int d=0;for(int q=0;q<128;q++)if(!(q&0x88)){int a=abs(p->b[q]);if(a==2){if(d)return 0;d=-1;}else if(a==3){if(d<0)return 0;d|=1<<((q+(q>>4))&1);if(d==3)return 0;}else if(a&&a<6)return 0;}return 1;}',
    ),
    ('F', 'material-noise'): (
        (8586, '8080a7fb2f76d5abaebbc8697b6b12a46e242365ebed1f2f43f7980824c18378'),
        (8604, '4867a0fdc8376359464e3eeb64c2dc6d441b9d57eadc8d0c4b9b4257f179db1f'),
        1468,
        b'int Q(const za*p){int d=0,f=0,g=0;for(int q=0;q<128;q++)if(!(q&0x88)){int a=abs(p->b[q]);if(a==2){d++;f++;}else if(a==3){d++;g|=1<<((q+(q>>4))&1);}else if(a&&a<6)return 0;}return d<2||(!f&&g!=3);}',
        b'int Q(const za*p){int d=0;for(int q=0;q<128;q++)if(!(q&0x88)){int a=abs(p->b[q]);if(a==2){if(d)return 0;d=-1;}else if(a==3){if(d<0)return 0;d|=1<<((q+(q>>4))&1);if(d==3)return 0;}else if(a&&a<6)return 0;}return 1;}',
    ),
    ('F', 'material-move-tt'): (
        (7803, 'aef86ac5c2541b53a81316f26e35de3af3c869d8aaa1ff4c72da68c9de1aeab9'),
        (7821, '8352665bca27f8c17c8ba1eeede04ddf0abaf70d88bebb5d70c6104c0c3481ec'),
        1413,
        b'int Q(const E*p){int d=0,f=0,g=0;for(int q=0;q<128;q++)if(!(q&0x88)){int a=abs(p->b[q]);if(a==2){d++;f++;}else if(a==3){d++;g|=1<<((q+(q>>4))&1);}else if(a&&a<6)return 0;}return d<2||(!f&&g!=3);}',
        b'int Q(const E*p){int d=0;for(int q=0;q<128;q++)if(!(q&0x88)){int a=abs(p->b[q]);if(a==2){if(d)return 0;d=-1;}else if(a==3){if(d<0)return 0;d|=1<<((q+(q>>4))&1);if(d==3)return 0;}else if(a&&a<6)return 0;}return 1;}',
    ),
}


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def transform_source(data, *, family, policy='full'):
    """Return exact fixed classifier replay and byte-preservation metadata."""
    if type(data) is not bytes or b'\r' in data:
        raise ValueError('material state requires immutable LF source bytes')
    case = _CASES.get((family, policy))
    if case is None:
        raise ValueError('unsupported material-state family/policy')
    before, after, start, old, new = case
    if (len(data), _sha(data)) != before:
        raise ValueError('material-state input differs from the fixed source')
    end = start + len(old)
    if data.count(old) != 1 or data[start:end] != old:
        raise ValueError('material-state full-function literal differs')
    candidate = data[:start] + new + data[end:]
    if (len(candidate), _sha(candidate)) != after or candidate.count(new) != 1:
        raise ValueError('material-state candidate identity differs')
    target_end = start + len(new)
    inverse = candidate[:start] + old + candidate[target_end:]
    complement = data[:start] + data[end:]
    if inverse != data:
        raise ValueError('material-state exact inverse failed')
    if candidate[:start] + candidate[target_end:] != complement:
        raise ValueError('material-state unchanged complement differs')
    return candidate, {
        'stage': 'fixed-shipping-material-state', 'family': family, 'policy': policy,
        'input_bytes': before[0], 'input_sha256': before[1],
        'output_bytes': after[0], 'output_sha256': after[1],
        'function_offset': start, 'old_function_sha256': _sha(old),
        'new_function_sha256': _sha(new), 'literal_edits': 1,
        'exact_inverse': True, 'unchanged_complement_bytes': len(complement),
        'unchanged_complement_sha256': _sha(complement),
    }
