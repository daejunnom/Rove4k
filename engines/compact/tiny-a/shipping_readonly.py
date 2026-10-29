"""Pure fixed Linux readonly flag spelling for four admitted legacy templates.

Call after the builder's original input/template/argv guards and before C
insertion. Standard Linux os.O_RDONLY is0. F and optional profiles opt out.
"""
import hashlib

_RULES={'A': ((979, 'c66d3a5a8942539af1fe5eba1ad595a19c2337a1c07f5141e37b49c1c20cecc0'), (969, '680d5cd1f6f5265e56d332417710d74c88fdd89e9174a129163ac1c535b0de68'), 845, 'b69e1b07fdca9e0fd1fb2d69e71256db130721620cf16038b91f6354a2fd4703', '5a34e8fa70dc719b428e62bfe1bc06c4162ac2bec40c264d671cab1a303f8419'), 'B': ((1054, 'e73c535e70911a6d2dd9ede8740ced65156ec40acdcffc10953f189d576e0d42'), (1044, 'f574f7550bd453f1f1e551bf2bb4fff93507c5299353ac911fb5f89f7a8e1ad1'), 920, '36b3e2b3a7db6290c01b6b4f18ee9a4bf27474d95f706929271708c91eb0d3d1', '5a34e8fa70dc719b428e62bfe1bc06c4162ac2bec40c264d671cab1a303f8419'), 'C': ((1064, '550de6230871e39a6d43be55b28832ee2958628268d2c328ff1bbfc01945bc56'), (1054, 'bd29b188e37443d74c97aac3da963ced8945614723e121315b9241fcd0705712'), 930, '429176c9a2b9f164fbd313078fd6f8671281e14d7771e2b804a5d79a36b336dc', '5a34e8fa70dc719b428e62bfe1bc06c4162ac2bec40c264d671cab1a303f8419'), 'E': ((1027, '9d1d26c9c6b793d7ca921f61f09facfd3f724508faca97a48b23f3e48318bd50'), (1017, '31a587f56a1943a3d789f27df4dfc8e3c01d90d7688d7849a7ae7cd9a567808e'), 893, '59e7216de62ffc76440e5753c4168f65c1f69c50a0bb2e637d2c39d7a7af6ebc', '5a34e8fa70dc719b428e62bfe1bc06c4162ac2bec40c264d671cab1a303f8419')}
_OLD=b"fd=os.open(d+'/x',os.O_RDONLY)"
_NEW=b"fd=os.open(d+'/x',0)"
_MARKER=b'__ROVE_SOURCE_LITERAL__'

def _pin(data):return len(data),hashlib.sha256(data).hexdigest()

def transform_template(template, family):
    if type(template) is not bytes or type(family) is not str or family not in _RULES:
        raise ValueError('fixed A/B/C/E legacy template and family required')
    before,after,at,prefix_sha,suffix_sha=_RULES[family]
    if (_pin(template)!=before or template.count(_OLD)!=1 or template.count(_MARKER)!=1
            or template[at:at+len(_OLD)]!=_OLD):
        raise ValueError('qualified legacy readonly template differs')
    prefix=template[:at];suffix=template[at+len(_OLD):]
    if hashlib.sha256(prefix).hexdigest()!=prefix_sha or hashlib.sha256(suffix).hexdigest()!=suffix_sha:
        raise ValueError('protected readonly template gaps differ')
    result=prefix+_NEW+suffix
    if (_pin(result)!=after or result.count(_MARKER)!=1 or
            result[:at]+_OLD+result[at+len(_NEW):]!=template):
        raise ValueError('fixed readonly template output or inverse differs')
    return result,{'family':family,'stage':'fixed-Linux-readonly-template',
        'input_bytes':before[0],'input_sha256':before[1],
        'output_bytes':after[0],'output_sha256':after[1],
        'raw_delta':-10,'span_offset':at,'protected_gaps':2,
        'all_gaps_equal':True,'full_inverse':True,'source_marker_count':1,
        'Linux_readonly_flag':0,'embedded_C_compiler_resources_unchanged':True,
        'attribute_monkeypatch_source_traceback_timing_equivalence_claimed':False,
        'external_reads':0}
