"""Pure fixed-source shipping replay; no external receipt or artifact is read.

Accept only current base sources produced after shipping_common. This byte
replay is not a claim of runtime qualification for any feature or policy.
Input offsets use LF bytes; CR is rejected rather than silently normalized.
"""
import hashlib


# Historical literal provenance: composition receipt SHA-256
# 54637beda72cedd68301a25c56adacbeb917f301c2a93f22f99343c8a3b3e39c
# Per case: input pin, output pin, features, sorted (old offset, new offset,
# old bytes, new bytes) edits. No runtime selection beyond the fixed case key.
# C/E full tokenizer component cost: 4882c7fdde9e1f07792aff9a57eb1bad4d50757d206f4a7630c6545e493c968f
# F full tokenizer+mate component cost: fba8a5b4fa3211393225664e6fb67a761cdd964d0775d366c489bdf5396617b9
_CASES = {
    ("A", "full"): (
        (9224, "fcb758088195b0e545573fe32f081a27bdf0370bf4adbb15528e531288742f09"),
        (9107, "dc6d43dee4eec5f0f5a785cab6f6ece822b7083f50a841b53d6978f5c34ebfdd"),
        ("promotion-rank", "main-owned-tokenizer",),
        (
            (2637, 2637, b"(", b"!"),
            (2641, 2641, b">>4)==0||(to>>4)==7", b"+16&96"),
            (7470, 7457, b"", b"char*nt(void){return strtok(NULL,\" \\t\\r\\n\");}static "),
            (7477, 7516, b"char*s", b"void"),
            (7517, 7554, b"d,*", b""),
            (7522, 7556, b"s", b"n"),
            (7524, 7558, b"rtok_r", b""),
            (7531, 7559, b"s,\" \\t\\r\\n\",&d", b""),
            (7599, 7613, b"s", b"n"),
            (7601, 7615, b"rtok_r", b""),
            (7608, 7616, b"NULL,\" \\t\\r\\n\",&d", b""),
            (7670, 7661, b"s", b"n"),
            (7672, 7663, b"rtok_r", b""),
            (7679, 7664, b"NULL,\" \\t\\r\\n\",&d", b""),
            (7935, 7903, b"char*s", b"void"),
            (7969, 7935, b"char*g;", b""),
            (7987, 7946, b"s", b"n"),
            (7989, 7948, b"rtok_r", b""),
            (7996, 7949, b"s,\" \\t\\r\\n\",&g", b""),
            (8016, 7955, b"s", b"n"),
            (8018, 7957, b"rtok_r", b""),
            (8025, 7958, b"NULL,\" \\t\\r\\n\",&g", b""),
            (8117, 8033, b"s", b"n"),
            (8119, 8035, b"rtok_r", b""),
            (8126, 8036, b"NULL,\" \\t\\r\\n\",&g", b""),
            (8796, 8689, b"f,*", b""),
            (8807, 8697, b"_r", b""),
            (8821, 8709, b",&f", b""),
            (9023, 8908, b"f", b""),
            (9053, 8937, b"f", b""),
        ),
    ),
    ("B", "full"): (
        (10941, "c3b68e0957d7068abce346083785de8f8cabb8104eefead83a18fb15efa45488"),
        (10727, "9715f9df054922568346484d1ac15458910f22650466f34f2ebfa7823ab056b4"),
        ("promotion-rank", "main-owned-tokenizer", "make-material-gain",),
        (
            (1056, 1056, b"int r(int v,int q){", b""),
            (1124, 1105, b"", b"int r(int v,int q){"),
            (3312, 3312, b"", b"{"),
            (3326, 3327, b"", b"i=s;}"),
            (3602, 3608, b"", b"+qi[abs(i)]+(f?qi[f]-100:0)"),
            (3660, 3693, b"(", b"!"),
            (3664, 3697, b">>4)==0||(to>>4)==7", b"+16&96"),
            (4477, 4497, b"static const int qi[7]={0,100,320,330,500,900,20000};", b""),
            (4603, 4570, b"f(!", b"nt j="),
            (4615, 4584, b"", b"-1;if(j<0"),
            (4640, 4618, b",j=qi[abs(p->b[yv])];if(!p->b[yv]&&!PROMO(m)&&(m&8))j=100;j+=PROMO(m)?qi[PROMO(m)]-100:0", b""),
            (9029, 8919, b"", b"char*nt(void){return strtok(NULL,\" \\t\\r\\n\");}static "),
            (9036, 8978, b"char*s", b"void"),
            (9077, 9017, b"f,*", b""),
            (9082, 9019, b"s", b"n"),
            (9084, 9021, b"rtok_r", b""),
            (9091, 9022, b"s,\" \\t\\r\\n\",&f", b""),
            (9159, 9076, b"s", b"n"),
            (9161, 9078, b"rtok_r", b""),
            (9168, 9079, b"NULL,\" \\t\\r\\n\",&f", b""),
            (9230, 9124, b"s", b"n"),
            (9232, 9126, b"rtok_r", b""),
            (9239, 9127, b"NULL,\" \\t\\r\\n\",&f", b""),
            (9495, 9366, b"char*s", b"void"),
            (9529, 9398, b"char*m;", b""),
            (9547, 9409, b"s", b"n"),
            (9549, 9411, b"rtok_r", b""),
            (9556, 9412, b"s,\" \\t\\r\\n\",&m", b""),
            (9576, 9418, b"s", b"n"),
            (9578, 9420, b"rtok_r", b""),
            (9585, 9421, b"NULL,\" \\t\\r\\n\",&m", b""),
            (9677, 9496, b"s", b"n"),
            (9679, 9498, b"rtok_r", b""),
            (9686, 9499, b"NULL,\" \\t\\r\\n\",&m", b""),
            (10513, 10309, b"m,*", b""),
            (10524, 10317, b"_r", b""),
            (10538, 10329, b",&m", b""),
            (10740, 10528, b"m", b""),
            (10770, 10557, b"m", b""),
        ),
    ),
    ("C", "full"): (
        (10273, '30e6ed94b9cd1a63cf07235b90742af35c21854b6e760290ee23e6907561c9dd'),
        (10156, '316a2704f2f7b5746fccfdb98f8f9b76a8004af68481eb32e7024b1d2b7b9bab'),
        ('promotion-rank', 'main-owned-tokenizer'),
        (
            (2790, 2790, b'(', b'!'),
            (2794, 2794, b'>>4)==0||(to>>4)==7', b'+16&96'),
            (8380, 8367, b'', b'char*nt(void){return strtok(NULL," \\t\\r\\n");}static '),
            (8387, 8426, b'char*s', b'void'),
            (8428, 8465, b'f,*', b''),
            (8433, 8467, b's', b'n'),
            (8435, 8469, b'rtok_r', b''),
            (8442, 8470, b's," \\t\\r\\n",&f', b''),
            (8510, 8524, b's', b'n'),
            (8512, 8526, b'rtok_r', b''),
            (8519, 8527, b'NULL," \\t\\r\\n",&f', b''),
            (8581, 8572, b's', b'n'),
            (8583, 8574, b'rtok_r', b''),
            (8590, 8575, b'NULL," \\t\\r\\n",&f', b''),
            (8868, 8836, b'char*s', b'void'),
            (8902, 8868, b'char*j;', b''),
            (8920, 8879, b's', b'n'),
            (8922, 8881, b'rtok_r', b''),
            (8929, 8882, b's," \\t\\r\\n",&j', b''),
            (8949, 8888, b's', b'n'),
            (8951, 8890, b'rtok_r', b''),
            (8958, 8891, b'NULL," \\t\\r\\n",&j', b''),
            (9050, 8966, b's', b'n'),
            (9052, 8968, b'rtok_r', b''),
            (9059, 8969, b'NULL," \\t\\r\\n",&j', b''),
            (9825, 9718, b'm,*', b''),
            (9836, 9726, b'_r', b''),
            (9850, 9738, b',&m', b''),
            (10052, 9937, b'm', b''),
            (10082, 9966, b'm', b''),
        ),
    ),
    ("E", "full"): (
        (10723, '2d15040aa4f916f9f07c4f81eee1e56c59bc15944b55bd48952be02128804e72'),
        (10606, '684f3d0aec72718d18eb72bff1d03efa84b97b8d1abbdb5847dd4c47362aee9e'),
        ('promotion-rank', 'main-owned-tokenizer'),
        (
            (2790, 2790, b'(', b'!'),
            (2794, 2794, b'>>4)==0||(to>>4)==7', b'+16&96'),
            (8644, 8631, b'', b'char*nt(void){return strtok(NULL," \\t\\r\\n");}static '),
            (8651, 8690, b'char*s', b'void'),
            (8692, 8729, b'f,*', b''),
            (8697, 8731, b's', b'n'),
            (8699, 8733, b'rtok_r', b''),
            (8706, 8734, b's," \\t\\r\\n",&f', b''),
            (8774, 8788, b's', b'n'),
            (8776, 8790, b'rtok_r', b''),
            (8783, 8791, b'NULL," \\t\\r\\n",&f', b''),
            (8845, 8836, b's', b'n'),
            (8847, 8838, b'rtok_r', b''),
            (8854, 8839, b'NULL," \\t\\r\\n",&f', b''),
            (9132, 9100, b'char*s', b'void'),
            (9166, 9132, b'char*m;', b''),
            (9184, 9143, b's', b'n'),
            (9186, 9145, b'rtok_r', b''),
            (9193, 9146, b's," \\t\\r\\n",&m', b''),
            (9213, 9152, b's', b'n'),
            (9215, 9154, b'rtok_r', b''),
            (9222, 9155, b'NULL," \\t\\r\\n",&m', b''),
            (9314, 9230, b's', b'n'),
            (9316, 9232, b'rtok_r', b''),
            (9323, 9233, b'NULL," \\t\\r\\n",&m', b''),
            (10275, 10168, b'm,*', b''),
            (10286, 10176, b'_r', b''),
            (10300, 10188, b',&m', b''),
            (10502, 10387, b'm', b''),
            (10532, 10416, b'm', b''),
        ),
    ),
    ("F", "full"): (
        (9226, '19d0f155724d3455e36f3e424bb55618d9e83417a42b75e7c0ada846cd0f44ce'),
        (9091, '7cc8d24d3080d4c0af177413e5441f7fb4141e3fb28175e9e0489b78291dfd68'),
        ('promotion-rank', 'main-owned-tokenizer', 'mate-adjust-expression'),
        (
            (2596, 2596, b'(', b'!'),
            (2600, 2600, b'>>4)==0||(to>>4)==7', b'+16&96'),
            (4782, 4769, b'', b'abs('),
            (4783, 4774, b'', b')'),
            (4794, 4786, b'-=f;if(H< -MATE+128)H', b''),
            (4817, 4788, b'', b'H>0?-f:'),
            (5531, 5509, b'', b'abs('),
            (5532, 5514, b'', b')'),
            (5545, 5528, b'', b'H>0?'),
            (5546, 5533, b';if(H< ', b':'),
            (5554, 5535, b'MATE+128)H-=', b''),
            (7463, 7432, b'', b'char*nt(void){return strtok(NULL," \\t\\r\\n");}static '),
            (7470, 7491, b'char*s', b'void'),
            (7511, 7530, b'f,*', b''),
            (7516, 7532, b's', b'n'),
            (7518, 7534, b'rtok_r', b''),
            (7525, 7535, b's," \\t\\r\\n",&f', b''),
            (7593, 7589, b's', b'n'),
            (7595, 7591, b'rtok_r', b''),
            (7602, 7592, b'NULL," \\t\\r\\n",&f', b''),
            (7664, 7637, b's', b'n'),
            (7666, 7639, b'rtok_r', b''),
            (7673, 7640, b'NULL," \\t\\r\\n",&f', b''),
            (7929, 7879, b'char*s', b'void'),
            (7963, 7911, b'char*i;', b''),
            (7981, 7922, b's', b'n'),
            (7983, 7924, b'rtok_r', b''),
            (7990, 7925, b's," \\t\\r\\n",&i', b''),
            (8010, 7931, b's', b'n'),
            (8012, 7933, b'rtok_r', b''),
            (8019, 7934, b'NULL," \\t\\r\\n",&i', b''),
            (8111, 8009, b's', b'n'),
            (8113, 8011, b'rtok_r', b''),
            (8120, 8012, b'NULL," \\t\\r\\n",&i', b''),
            (8798, 8673, b'j,*', b''),
            (8809, 8681, b'_r', b''),
            (8823, 8693, b',&j', b''),
            (9025, 8892, b'j', b''),
            (9055, 8921, b'j', b''),
        ),
    ),
    ("F", "material-noise"): (
        (8586, "8080a7fb2f76d5abaebbc8697b6b12a46e242365ebed1f2f43f7980824c18378"),
        (8586, "8080a7fb2f76d5abaebbc8697b6b12a46e242365ebed1f2f43f7980824c18378"),
        (),
        (
        ),
    ),
    ("F", "material-move-tt"): (
        # Superseding F row: 564f52fbfc60e0d9757254d1d4a7abf62c6dc927493d2590646cd34b35744457
        (8114, "cbe891f12a682b9cb702734bc88f0183a5bfb9bafa62a5d55d471864228b7572"),
        (7803, "aef86ac5c2541b53a81316f26e35de3af3c869d8aaa1ff4c72da68c9de1aeab9"),
        ("promotion-rank", "main-owned-tokenizer", "terminal-loop-sharing", "atomic64-full-index-key-move-TT", "fixed-positive-TT18-casts",),
        (
            (496, 496, b"struct{W a;Y b;a", b"_A"),
            (517, 503, b"_flag", b""),
            (523, 504, b"c;}", b"W "),
            (2364, 2344, b"(", b"!"),
            (2368, 2348, b">>4)==0||(to>>4)==7", b"+16&96"),
            (3490, 3457, b"", b"d){"),
            (3497, 3467, b"flag_te", b""),
            (3506, 3469, b"_and_set_explicit(&e->c,mem", b""),
            (3535, 3471, b"y_or", b"e(e,(a>>18<<18)|"),
            (3540, 3488, b"er_acquire))return 0;if(d)e->a=a,e->b=d;else d=e->a==a?e->b:0;atomic_flag_clear_explicit(&e->c,memory_order_release", b""),
            (3665, 3498, b"", b";}W f=atomic_load(e);return(f^a)>>18?0:f&131071"),
            (4071, 3951, b"if(o||f==127){E q;for(int i=0;i<A;i++)if(g(p,x[i],&q)){if(!o){atomic_store(&F,1);}return 0;}return n?-MATE+f:0;}", b""),
            (4525, 4293, b"", b"if(o||f==127){if(!o)atomic_store(&F,1);return 0;}"),
            (6326, 6143, b"(size_t)", b""),
            (6352, 6161, b"flag_clear", b"init"),
            (6363, 6166, b"&", b""),
            (6365, 6167, b"[", b"+"),
            (6367, 6169, b"].c", b",0"),
            (6380, 6181, b"", b"char*nt(void){return strtok(NULL,\" \\t\\r\\n\");}static "),
            (6387, 6240, b"char*s", b"void"),
            (6427, 6278, b"f,*", b""),
            (6432, 6280, b"s", b"n"),
            (6434, 6282, b"rtok_r", b""),
            (6441, 6283, b"s,\" \\t\\r\\n\",&f", b""),
            (6509, 6337, b"s", b"n"),
            (6511, 6339, b"rtok_r", b""),
            (6518, 6340, b"NULL,\" \\t\\r\\n\",&f", b""),
            (6580, 6385, b"s", b"n"),
            (6582, 6387, b"rtok_r", b""),
            (6589, 6388, b"NULL,\" \\t\\r\\n\",&f", b""),
            (6842, 6624, b"char*s", b"void"),
            (6876, 6656, b"char*i;", b""),
            (6894, 6667, b"s", b"n"),
            (6896, 6669, b"rtok_r", b""),
            (6903, 6670, b"s,\" \\t\\r\\n\",&i", b""),
            (6923, 6676, b"s", b"n"),
            (6925, 6678, b"rtok_r", b""),
            (6932, 6679, b"NULL,\" \\t\\r\\n\",&i", b""),
            (7024, 6754, b"s", b"n"),
            (7026, 6756, b"rtok_r", b""),
            (7033, 6757, b"NULL,\" \\t\\r\\n\",&i", b""),
            (7405, 7112, b"(size_t)", b""),
            (7691, 7390, b"j,*", b""),
            (7702, 7398, b"_r", b""),
            (7716, 7410, b",&j", b""),
            (7918, 7609, b"j", b""),
            (7948, 7638, b"j", b""),
        ),
    ),
}


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def transform_source(source, *, family, policy='full'):
    """Replay one exact base-source case without changing unrelated bytes."""
    if type(source) is not bytes:
        raise ValueError('shipping refinements require immutable source bytes')
    if b'\r' in source:
        raise ValueError('CR in shipping source; fixed offsets require LF bytes')
    case = _CASES.get((family, policy))
    if case is None:
        raise ValueError('unsupported shipping refinement family/policy')
    before, after, features, edits = case
    if (len(source), _sha(source)) != before:
        raise ValueError('shipping refinements input differs from the fixed base')
    pieces, remainder = [], []
    cursor = output_cursor = 0
    for start, target, old, new in edits:
        end = start + len(old)
        if start < cursor or end > len(source) or source[start:end] != old:
            raise ValueError('fixed literal edit differs or overlaps')
        untouched = source[cursor:start]
        if output_cursor + len(untouched) != target:
            raise ValueError('fixed candidate edit offset differs')
        pieces.extend((untouched, new))
        remainder.append(untouched)
        cursor = end
        output_cursor = target + len(new)
    pieces.append(source[cursor:])
    remainder.append(source[cursor:])
    candidate = b''.join(pieces)
    if (len(candidate), _sha(candidate)) != after:
        raise ValueError('shipping refinements final output differs')
    inverse = candidate
    for start, target, old, new in reversed(edits):
        if inverse[target:target + len(new)] != new:
            raise ValueError('fixed candidate inverse literal differs')
        inverse = inverse[:target] + old + inverse[target + len(new):]
    if inverse != source:
        raise ValueError('shipping refinements exact inverse failed')
    actual_remainder = []
    cursor = 0
    for start, target, old, new in edits:
        if target < cursor or candidate[target:target + len(new)] != new:
            raise ValueError('candidate complement edit span differs')
        actual_remainder.append(candidate[cursor:target])
        cursor = target + len(new)
    actual_remainder.append(candidate[cursor:])
    unchanged = b''.join(remainder)
    if b''.join(actual_remainder) != unchanged:
        raise ValueError('shipping refinements unchanged complement differs')
    metadata = {
        'stage': 'fixed-shipping-refinements', 'family': family, 'policy': policy,
        'input_bytes': before[0], 'input_sha256': before[1],
        'output_bytes': after[0], 'output_sha256': after[1],
        'features': list(features), 'literal_edits': len(edits),
        'exact_inverse': True, 'unchanged_complement_bytes': len(unchanged),
        'unchanged_complement_sha256': _sha(unchanged),
    }
    if family == 'F' and policy == 'material-move-tt':
        metadata['move_TT'] = {
            'identity_bits': 64, 'index_bits': 18, 'stored_identity_bits': 46,
            'atomic_record_bytes': 8, 'table_bytes': 2097152,
            'memory_order': 'C11 sequentially consistent atomic64 load/store',
            'publication_difference': 'coherent snapshot; busy-read misses and busy-write drops removed',
            'replacement': 'unconditional atomic store may replace a concurrent store',
            'move_bits': 17, 'zero_is_query': True,
        }
    return candidate, metadata
