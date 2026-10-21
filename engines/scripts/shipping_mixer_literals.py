"""Fixed LP64 large mixer hex spellings; no hash-policy change.

Only the three >2**63 unsigned-long64 literals lose UINT64_C wrappers. B is
excluded after its complete-file loss; its UINT64_C(1) shift stays intact.
All headers and constants/operations stay. DEV bypass belongs to the caller.
"""
import hashlib

CASES = {('A', 'full'): ((9082, '038ec565e9ad3ae339fe2830165ab0f621455024ab8aea5b2da861a925a78945'),
                 (9052, 'd1d490074754c3468785b1cd7f8f3c841f3ed1115933003fcc06edc5314e452c'),
                 ((884,
                   884,
                   b'W e(W x){x+=UINT64_C(0x9e3779b97f4a7c15);x=(x^(x>>30))*UINT64_C(0xbf58476d1ce4e5b9);x=(x'
                   b'^(x>>27))*UINT64_C(0x94d049bb133111eb);return x^(x>>31);}',
                   b'W e(W x){x+=0x9e3779b97f4a7c15;x=(x^(x>>30))*0xbf58476d1ce4e5b9;x=(x^(x>>27))*0x94d049bb'
                   b'133111eb;return x^(x>>31);}'),)),
 ('C', 'full'): ((10114, 'fde89cdc49ef55d075343cd2480a5e65a02d18e94884271890b579ae60e93304'),
                 (10084, 'ed5b5fba543a7ab3a208af466e14744d0339447b0b812448a5092a068cd9715b'),
                 ((947,
                   947,
                   b'M c(M x){x+=UINT64_C(0x9e3779b97f4a7c15);x=(x^(x>>30))*UINT64_C(0xbf58476d1ce4e5b9);x=(x'
                   b'^(x>>27))*UINT64_C(0x94d049bb133111eb);return x^(x>>31);}',
                   b'M c(M x){x+=0x9e3779b97f4a7c15;x=(x^(x>>30))*0xbf58476d1ce4e5b9;x=(x^(x>>27))*0x94d049bb'
                   b'133111eb;return x^(x>>31);}'),)),
 ('E', 'full'): ((10470, '5a3352258412593216641c095762a3171a40a0f3e4d02fa434f67824281b1012'),
                 (10440, 'c65f0d610acbba9ad2dbfad230a18fb8c0a15d1eab995675a58ea71c5b5352e8'),
                 ((919,
                   919,
                   b'I c(I x){x+=UINT64_C(0x9e3779b97f4a7c15);x=(x^(x>>30))*UINT64_C(0xbf58476d1ce4e5b9);x=(x'
                   b'^(x>>27))*UINT64_C(0x94d049bb133111eb);return x^(x>>31);}',
                   b'I c(I x){x+=0x9e3779b97f4a7c15;x=(x^(x>>30))*0xbf58476d1ce4e5b9;x=(x^(x>>27))*0x94d049bb'
                   b'133111eb;return x^(x>>31);}'),)),
 ('F', 'full'): ((8959, '601ea9b983a6b86fa74ff09555d2c9349433b9b0d7c664c636fb87aa19316acf'),
                 (8939, '53f3326c9062601fa037212f853c91c34cd1b36a076a571d8e1f52624514e08c'),
                 ((853,
                   853,
                   b'W r(W x){x=(x^(x>>30))*UINT64_C(0xbf58476d1ce4e5b9);x=(x^(x>>27))*UINT64_C(0x94d049bb133'
                   b'111eb);return x^(x>>31);}',
                   b'W r(W x){x=(x^(x>>30))*0xbf58476d1ce4e5b9;x=(x^(x>>27))*0x94d049bb133111eb;return x^(x>>'
                   b'31);}'),)),
 ('F', 'material-noise'): ((8538, '95b9c72aa25e10bdafdad338e3a8e067d545741086329d4348efeadca0c48fd1'),
                           (8508, 'a7b50f5d084b558c1fb07f3c4c572afa29291a4982ddd00fd783f187a3f74c93'),
                           ((821,
                             821,
                             b'W h(W x){x+=UINT64_C(0x9e3779b97f4a7c15);x=(x^(x>>30))*UINT64_C(0xbf58476d1c'
                             b'e4e5b9);x=(x^(x>>27))*UINT64_C(0x94d049bb133111eb);return x^(x>>31);}',
                             b'W h(W x){x+=0x9e3779b97f4a7c15;x=(x^(x>>30))*0xbf58476d1ce4e5b9;x=(x^(x>>27)'
                             b')*0x94d049bb133111eb;return x^(x>>31);}'),)),
 ('F', 'material-move-tt'): ((7771, 'e1f4e4069ed0fd69d27034cff49c09e890cd18db97905d881d69507141b55505'),
                             (7741, '6d3fa3e0099285dd9efe8934f7b419fdd204f80ed4eaf502ad64a9f5b2e12122'),
                             ((770,
                               770,
                               b'W h(W x){x+=UINT64_C(0x9e3779b97f4a7c15);x=(x^(x>>30))*UINT64_C(0xbf58476d1c'
                               b'e4e5b9);x=(x^(x>>27))*UINT64_C(0x94d049bb133111eb);return x^(x>>31);}',
                               b'W h(W x){x+=0x9e3779b97f4a7c15;x=(x^(x>>30))*0xbf58476d1ce4e5b9;x=(x^(x>>27)'
                               b')*0x94d049bb133111eb;return x^(x>>31);}'),))}
def transform_source(source, *, family, policy='full'):
    """Replay only frozen literal spans; preserve every other byte."""
    before, after, edits = CASES[(family, policy)]
    if type(source) is not bytes or (len(source), hashlib.sha256(source).hexdigest()) != before:
        raise ValueError('fixed late forms input differs from fixed late source')
    pieces=[];gaps=[];cursor=target_cursor=0
    for start,target,old,new in edits:
        if start<cursor or source[start:start+len(old)]!=old:
            raise ValueError('fixed late forms literal differs')
        gap=source[cursor:start]
        if target_cursor+len(gap)!=target:
            raise ValueError('fixed late forms target differs')
        pieces.extend((gap,new));gaps.append(gap)
        cursor=start+len(old);target_cursor=target+len(new)
    pieces.append(source[cursor:]);gaps.append(source[cursor:]);candidate=b''.join(pieces)
    if (len(candidate),hashlib.sha256(candidate).hexdigest())!=after:
        raise ValueError('fixed late forms output differs')
    inverse=candidate;new_gaps=[];cursor=0
    for start,target,old,new in edits:
        if candidate[target:target+len(new)]!=new:
            raise ValueError('fixed late forms candidate span differs')
        new_gaps.append(candidate[cursor:target]);cursor=target+len(new)
    new_gaps.append(candidate[cursor:])
    for start,target,old,new in reversed(edits):
        inverse=inverse[:target]+old+inverse[target+len(new):]
    if inverse!=source or gaps!=new_gaps:
        raise ValueError('fixed late forms inverse/complement differs')
    remainder=b''.join(gaps)
    return candidate,dict(stage='late-fixed-LP64-mixer-literals',family=family,policy=policy,
        input_bytes=before[0],input_sha256=before[1],output_bytes=after[0],output_sha256=after[1],
        literal_spans=len(edits),exact_inverse=True,complement_bytes=len(remainder),
        complement_sha256=hashlib.sha256(remainder).hexdigest(),
        external_reads=0,compiler_codec_engine_executed_by_transform=0)
