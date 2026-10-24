"""Pure A-only destination binding and fixed raw-literal spelling.

The make function's E* destination parameter t becomes w at24 exact tokens.
All other C bytes and the complete native image remain unchanged. The same
C bytes are embedded with triple-double rather than triple-single quotes.
No external artifact, compiler, AST, search or codec is a helper input.
"""
import hashlib

BEFORE=(8914,'597d01d9cece4762880cc4a4c8c3a5329125ca76cb4b92eba6c31da3231c683a')
AFTER=(8914,'5319dd376e8e7fe6c03c6b40f6fc81b571902d75a663148ffbae00b615059c18')
POSITIONS=(2118, 2182, 2187, 2198, 2206, 2228, 2253, 2281, 2310, 2379, 2388, 2400, 2409, 2416, 2435, 2448, 2450, 2475, 2478, 2486, 2489, 2494, 2523, 2528)
GAPS=((0, 2118, '87e40da3138ae807aa72dbbfa5a9ce7292ad04e6e471f13a20ba5e2bc61a4bcf'), (2119, 2182, 'c79d5047202319ea13291d1b3ed1eeb55562621c4c7000437cef78c1803cc6e3'), (2183, 2187, '269afa79018af40fc61bc9afcd5bd5462724747e81a87cec63a5336b6d5b7b22'), (2188, 2198, '3047310d0b57791abd3d6461bcb65e306c35798cad43c77f0fc9a553465eb160'), (2199, 2206, '3b7c24e658de12d44005ad8cffa08e5d9277ab6d2f49a354255c6b2c8df7d4bf'), (2207, 2228, '55aedbeb88ef0d907c45ce20b99703bfff6de64b14a0afc81eb0c43d2d448faa'), (2229, 2253, '0ca22bf67c7acd43e4fbc6a741f8f03c2ce9ca3f401624c0a350fdff1b78b347'), (2254, 2281, '527667b5c6c95ead9b6de284a10ee43dc57ba8a062ec437574bea85060286e8e'), (2282, 2310, 'ac1b3368ae4fc749c49557fa783260da4fa7401430569db70330b57863d5243a'), (2311, 2379, '9d3d6c2d3e68629830821c9f5f5edc71c8eed2183354412d65fefaefec3f89e1'), (2380, 2388, '03af6c8a54ae49d6debff2ab8d1e2f18bd7f3c8735265a3e6c0d9a7a14948c4e'), (2389, 2400, '9f523e83bdce1b234c729ea99af0444c3588278d16c6b01881282a1184b5154c'), (2401, 2409, 'f189961e31998189b37a5931f52bdb92e42a6bdad88025bf61477ba3984d3969'), (2410, 2416, 'eec1d6bcebd47cf4f0b773e830ebb95ac5ec91d2f91f49ee9138912328cb2ead'), (2417, 2435, '5ae2e3b57f0d866fd904c4c38b412d32730919ef402109e87789aa2ffd8a64c0'), (2436, 2448, 'bdb859e5681c0726cb08794bbc01b1f4d5c28e5537957cc52b1eb073355ef0e6'), (2449, 2450, 'd03502c43d74a30b936740a9517dc4ea2b2ad7168caa0a774cefe793ce0b33e7'), (2451, 2475, 'cbc39633cc0df62b65ba76bb2cbdb880f3169ab3eaaa43768946a055121db365'), (2476, 2478, '9d8b2b5670d18da8a99f6152f7ee75558019cd106d8032bf7c1117bd37273e37'), (2479, 2486, '8e1c50316e54ffd7f97d582b56ff38c3c2ef84fc40008e30efd4b5a8ecfca692'), (2487, 2489, '9d8b2b5670d18da8a99f6152f7ee75558019cd106d8032bf7c1117bd37273e37'), (2490, 2494, '05d26e2af845218f286782797f319c61a5fa533f0ad9b0340916d3af543e6924'), (2495, 2523, '3f519ea7fefb3d3048814af8e268a7daf2c355e1a2b21c146516e72daff40f41'), (2524, 2528, 'e949038208316635cdf38272b0e7ec033db2cc054e5f74324a6d5e761cd56faf'), (2529, 8914, '5a7f30087c19089cb6b291df9bc4a4f0e730a16485ab7718cce2daf8160c3c05'))
SINGLE_LITERAL=(8922, '6a302f1649be794a902cc58477e78782addf2315f2ca408f79de05fb6d978258')
DOUBLE_LITERAL=(8922, '86bf50499d1daccf38ffd8551594ac70f2abf0104379e4fa1995abfe295d0376')

def _pin(raw):return len(raw),hashlib.sha256(raw).hexdigest()
def _need(ok,message):
    if not ok:raise ValueError(message)

def transform_source(source):
    _need(type(source)is bytes and _pin(source)==BEFORE,'fixed A terminal-loop source required')
    candidate=bytearray(source)
    for at in POSITIONS:
        _need(source[at:at+1]==b't','A destination binding token differs')
        candidate[at]=ord('w')
    candidate=bytes(candidate)
    _need(_pin(candidate)==AFTER,'fixed A destination rename differs')
    inverse=bytearray(candidate)
    for at in POSITIONS:inverse[at]=ord('t')
    _need(bytes(inverse)==source,'A destination full inverse differs')
    for start,end,digest in GAPS:
        _need(source[start:end]==candidate[start:end] and hashlib.sha256(source[start:end]).hexdigest()==digest,'A destination protected gap differs')
    return candidate,{'input_bytes':BEFORE[0],'input_sha256':BEFORE[1],
        'output_bytes':AFTER[0],'output_sha256':AFTER[1],
        'function':'v/make','parameter':'E*t to E*w','declaration':2118,
        'identifier_token_regions':24,'protected_gaps':25,'protected_complement_bytes':8890,
        'full_inverse':True,'native_whole_image_unchanged':True,
        'canonical_DEV_rules_learners_TT_thread_policy_changed':False,'external_reads':0}

def transform_literal(expression):
    _need(type(expression)is str and _pin(expression.encode())==SINGLE_LITERAL,'fixed renamed-C triple-single literal required')
    _need(expression[:5]=="br"+"'"*3 and expression[-3:]=="'"*3,'A original raw literal delimiter differs')
    selected='br'+chr(34)*3+expression[5:-3]+chr(34)*3
    _need(_pin(selected.encode())==DOUBLE_LITERAL,'fixed A triple-double literal differs')
    _need(expression[:5]+selected[5:-3]+expression[-3:]==expression,'A literal inverse differs')
    return selected
