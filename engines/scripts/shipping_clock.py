"""Fixed full-profile clock-presence sentinel stage for A/B/C/E/F.

Pure bytes in/out. No file, recipe, artifact, process, compiler, codec, AST or
preprocessor dependency. Only exact admitted final shipping source domains pass.
DEV and F optional selection are caller decisions; this API accepts full only.

The actual numeric helpers return only 0..INT64_MAX (invalid/missing also 0).
Unsigned -1 is UINT64_MAX and uniquely denotes missing own-side time; assignment
carries presence, and ~time is nonzero exactly for every admitted present value.
This preserves token consumption and budget arithmetic outside three fixed spans.
No runtime or worker/lifecycle qualification claim is made by this helper.
"""
import hashlib

CASES = {'A': {'input': (9052, 'd1d490074754c3468785b1cd7f8f3c841f3ed1115933003fcc06edc5314e452c'),
       'output': (9040, '624ad8a28a9d555fda37efa82b468fce09f98d4c5b86b20739ee2e6f589ff5a8'),
       'complement': (8992, '6123b9e5a91ab3771495c9104e12d787c5ca5c8e9b73a801ea67bdf75bc66fe9'),
       'gaps': ((7858, 'c5d7e22e0be11c162620490f9ce154e069bfcfcddb9cabd79d646398001db62e'),
                (128, '5db9e2633ed04696e9c7102a11381d247ca7910617d0ad6ed541b4572cdda3b7'),
                (3, '04d46e43eb1d0b10521332a70aea52facaccf26b8288417d246e60496c111d1b'),
                (1003, '36e25a3d4e1fec05d55bea9b7acb167b756f88cecd045e7589f0619749a4b846')),
       'edits': ((7858, b'W a=0,d=0,S=0;int f=0;', b'W a=-1,d=0,S=0;'),
                 (8008, b"if(t[1]=='t'){a=n;f=1;}else d=n;", b"if(t[1]=='t')a=n;else d=n;"),
                 (8043, b'if(f){', b'if(~a){'))},
 'B': {'input': (10577, 'd360c9ca23b30fe7f295d3f1e0012da9618a1a25a6b8b9cec19240fdac6396ae'),
       'output': (10565, '6124424eff02466a28e900ca7abf0f8ff36f74d39de020e4c83b6909b95387cf'),
       'complement': (10517, 'e600a4e6aec7755618161cb276fe29a02c06a07ec978254b1fd1a31b99970f16'),
       'gaps': ((9298, '2d9e96cac36d11045d7df06d375b603b0d70d06b6c2c97ba89d71ab7eda05f55'),
                (128, '9785ed9122f716a4ce20972e7b14d348ce9e6f5894eb7d3dece64b0f74502bd5'),
                (3, '04d46e43eb1d0b10521332a70aea52facaccf26b8288417d246e60496c111d1b'),
                (1088, '5052101bb5de24b40527f2609c890eabfd294829e21dd1f57ce2c7a91925b4d9')),
       'edits': ((9298, b'D a=0,d=0,f=0;int j=0;', b'D a=-1,d=0,f=0;'),
                 (9448, b"if(t[1]=='t'){a=n;j=1;}else d=n;", b"if(t[1]=='t')a=n;else d=n;"),
                 (9483, b'if(j){', b'if(~a){'))},
 'C': {'input': (10084, 'ed5b5fba543a7ab3a208af466e14744d0339447b0b812448a5092a068cd9715b'),
       'output': (10072, 'fc2209ce96c714d3828790cae882051f8cbf8980f4e874381954280f0c9d17a3'),
       'complement': (10024, 'b07be6e1cceedfa98c4602abe60c1d5eaaee4b888dcb7420824a83fa290644b9'),
       'gaps': ((8774, 'ac3588029762349d58c989bedc486ef5062ae5f9a23973facae86832ce1e2eaa'),
                (134, '1577c1d37b2e26d65a1db13a63039d766fd72736e5de5b2bb7eb3418e21f5167'),
                (3, '04d46e43eb1d0b10521332a70aea52facaccf26b8288417d246e60496c111d1b'),
                (1113, 'a6241d24bba6ee784104c70582ef1bc1e4ab05191a214aab1a53f5969abf0903')),
       'edits': ((8774, b'M a=0,d=0,f=0;int i=0;', b'M a=-1,d=0,f=0;'),
                 (8930, b"if(t[1]=='t'){a=n;i=1;}else d=n;", b"if(t[1]=='t')a=n;else d=n;"),
                 (8965, b'if(i){', b'if(~a){'))},
 'E': {'input': (10440, 'c65f0d610acbba9ad2dbfad230a18fb8c0a15d1eab995675a58ea71c5b5352e8'),
       'output': (10428, '072a0757878a53be119c9184f84ff8b2abe99d95ed702af2eaa15c53bc0350c9'),
       'complement': (10380, '8ea28f3e6a7fae86da8be6ac09429d4ec9eb69f6390e755fa123d09a4fb31017'),
       'gaps': ((9028, '28315f9b124f5bf33818c6a4ce3a86cd3f6fb641c10a9f055df42e8392412d26'),
                (134, '2b20af11a66b73219b7db51408640ea07ff90c4b8949fc71b3cc760ba643237b'),
                (3, '04d46e43eb1d0b10521332a70aea52facaccf26b8288417d246e60496c111d1b'),
                (1215, '902402664bf7d8ce33d88f9205cb3e98baef50885706fad090ba4624306d1cfb')),
       'edits': ((9028, b'I a=0,d=0,f=0;int j=0;', b'I a=-1,d=0,f=0;'),
                 (9184, b"if(t[1]=='t'){a=n;j=1;}else d=n;", b"if(t[1]=='t')a=n;else d=n;"),
                 (9219, b'if(j){', b'if(~a){'))},
 'F': {'input': (8871, '14c87dab541b9ccad59a44ea0d2e5a916fe2c7a7e6211ee10789dbc2489246c3'),
       'output': (8859, 'e868953700cc0a319b8293cde473d9c0fd44a29e5105f25e1cc114e601740f59'),
       'complement': (8811, '129a75c11b92f512b94016ed020a50312ef2def52bc9a21b52c2368cac02faf4'),
       'gaps': ((7677, '73497fdd35d386a00725d94cfb65c0bdbf29816c032873769a19071d3f6ba238'),
                (128, 'e4575a8e9956a182a368c93cd6f54931d00b33e0e512dde6140e811085edc04d'),
                (3, '04d46e43eb1d0b10521332a70aea52facaccf26b8288417d246e60496c111d1b'),
                (1003, 'ce5c9b28c05e643204a971ee3708ca5255756256e8f84a1e01bf4c807ce89e9f')),
       'edits': ((7677, b'W a=0,d=0,f=0;int g=0;', b'W a=-1,d=0,f=0;'),
                 (7827, b"if(t[1]=='t'){a=n;g=1;}else d=n;", b"if(t[1]=='t')a=n;else d=n;"),
                 (7862, b'if(g){', b'if(~a){'))}}

def _pin(data):
    return len(data), hashlib.sha256(data).hexdigest()


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def transform_source(source, *, family, policy='full'):
    """Return the exact fixed full-profile source and its mechanical metadata."""
    _require(type(source) is bytes, 'clock source must be bytes')
    _require(type(family) is str and family in CASES, 'unadmitted clock family')
    _require(policy == 'full', 'clock stage admits full shipping profile only')
    case = CASES[family]
    _require(_pin(source) == case['input'], 'clock input bytes/SHA-256 differs')
    parts, old_gaps, targets = [], [], []
    cursor = length = 0
    for index, (offset, before, after) in enumerate(case['edits']):
        _require(offset >= cursor and source[offset:offset+len(before)] == before,
                 'clock fixed old span differs')
        gap = source[cursor:offset]
        _require(_pin(gap) == case['gaps'][index], 'clock old gap differs')
        old_gaps.append(gap)
        parts.extend((gap, after))
        length += len(gap)
        targets.append(length)
        length += len(after)
        cursor = offset + len(before)
    tail = source[cursor:]
    _require(_pin(tail) == case['gaps'][-1], 'clock old tail differs')
    old_gaps.append(tail)
    parts.append(tail)
    candidate = b''.join(parts)
    _require(_pin(candidate) == case['output'], 'clock output bytes/SHA-256 differs')
    inverse, new_gaps = [], []
    cursor = 0
    for index, ((offset, before, after), target) in enumerate(zip(case['edits'], targets)):
        gap = candidate[cursor:target]
        _require(gap == old_gaps[index] and _pin(gap) == case['gaps'][index],
                 'clock candidate gap differs')
        _require(candidate[target:target+len(after)] == after,
                 'clock fixed new span differs')
        new_gaps.append(gap)
        inverse.extend((gap, before))
        cursor = target + len(after)
    tail = candidate[cursor:]
    _require(tail == old_gaps[-1] and _pin(tail) == case['gaps'][-1],
             'clock candidate tail differs')
    new_gaps.append(tail)
    inverse.append(tail)
    _require(b''.join(inverse) == source, 'clock exact inverse differs')
    complement = b''.join(new_gaps)
    _require(_pin(complement) == case['complement'], 'clock complement differs')
    return candidate, {
        'stage': 'fixed full-profile clock-presence sentinel',
        'family': family,
        'policy': policy,
        'input_bytes': len(source),
        'input_sha256': case['input'][1],
        'output_bytes': len(candidate),
        'output_sha256': case['output'][1],
        'edits': [{'offset': offset, 'target': target,
                   'old_bytes': len(before), 'new_bytes': len(after)}
                  for (offset, before, after), target in zip(case['edits'], targets)],
        'each_gap_exact': True,
        'exact_inverse': True,
        'complement_bytes': len(complement),
        'complement_sha256': case['complement'][1],
        'declared_selected_time_state':
            'UINT64_MAX is absent; numeric results 0..INT64_MAX include invalid/missing0; '
            'own time assignment is present including0; ~time tests presence',
    }
