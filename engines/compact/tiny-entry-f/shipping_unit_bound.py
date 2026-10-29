"""Fixed F unit-window bound expression after the ordinary type-token stage.

No experiment, artifact, report or upstream code is a regeneration input.
For the C int bound extracted by &3, the retained bound0 gate rejects empty.
For score<beta, 2+(score>=beta) is 2: accept exact1/upper3, reject lower2.
For score>=beta it is 3: accept exact1/lower2, reject upper3. Comparisons
produce int0/1 and adding2 cannot overflow. The entire guarded condition is
the sole replaced span; exact requested depth/QS0 and root cutoff stay fixed.
"""
import hashlib

INPUT_BYTES = 9464
INPUT_SHA256 = 'd942731c54f82da8dfa1aa5fedcc6328b56b32fe0ab527b5396847ceea541f26'
OUTPUT_BYTES = 9442
OUTPUT_SHA256 = '245dae234e80c514d64da9109326dbf50077d703f6f353011f97aac682bdfd20'
OLD = b'if(f&&I&&J==(a>0?a:0)&&(I==1||(I==2&&H>=d)||(I==3&&H<d)))return H;'
NEW = b'if(f&&I&&J==(a>0?a:0)&&I!=2+(H>=d))return H;'
TRUTH_TABLE = (
    (0, False, False), (1, False, True), (2, False, False), (3, False, True),
    (0, True, False), (1, True, True), (2, True, True), (3, True, False),
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def transform_source(source):
    if type(source) is not bytes or len(source) != INPUT_BYTES or sha(source) != INPUT_SHA256:
        raise ValueError('exact post-type full-key F source required')
    if source.count(OLD) != 1 or NEW in source:
        raise ValueError('one original bound predicate required')
    before, after = source.split(OLD)
    result = before + NEW + after
    if result.count(NEW) != 1 or result.replace(NEW, OLD) != source:
        raise ValueError('unit-window expression inverse differs')
    if len(result) != OUTPUT_BYTES or sha(result) != OUTPUT_SHA256:
        raise ValueError('fixed unit-window output differs')
    return result, {
        'stage': 'shipping-after-types', 'exact_inverse': True,
        'protected_complement_bytes': len(before) + len(after),
        'protected_complement_sha256': sha(before + after),
        'old_guard': OLD.decode(), 'new_guard': NEW.decode(),
        'bound_high_accept_truth_table': TRUTH_TABLE,
        'C_int_comparison_result': [0, 1], 'added_constant': 2,
        'empty_bound_gate_preserved': True, 'exact_horizon_QS0_preserved': True,
        'root_cutoff_disabled_preserved': True,
        'TT_payload_key_flags_mate_MTD_witness_unchanged': True,
        'entire_native_identity_to_predecessor': False,
    }
