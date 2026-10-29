"""Inline one private piece-index helper and the fixed history constant.

Each cell is int8_t: promotion to int and one +6 match the pure helper exactly.
Four HISTORY expansions remain the identical int token4096, preserving all
array extents and capacity rejection. Macro-dump/line identities change;
canonical/DEV and earlier shipping stages retain their original inputs.
This pure measured full-F stage reads no external source or receipt.
"""
import hashlib

INPUT=(8933,'cc8ef7dab0e35e2a62fee66d427eab09698e6eeebfa6eed3abb0e20d20b1a0a1')
OUTPUT=(8871,'14c87dab541b9ccad59a44ea0d2e5a916fe2c7a7e6211ee10789dbc2489246c3')
EDITS=(
    (187,187,b'#define HISTORY 4096\n',b''),
    (556,535,b'HISTORY',b'4096'),
    (647,623,b'HISTORY',b'4096'),
    (4036,4009,b'static int S(int p){return p+6;}',b''),
    (4182,4123,b'S(p->b[d])',b'(p->b[d]+6)'),
    (5095,5037,b'S(q.b[O])',b'(q.b[O]+6)'),
    (5329,5272,b'S(p->b[N])',b'(p->b[N]+6)'),
    (7381,7325,b'HISTORY',b'4096'),
    (7523,7464,b'HISTORY',b'4096'),
)
COMPLEMENT=(8823,'05e0d560e1c83adb171b9ad5a79a282ab3c9514ce09d3c31cd17da3f9879cf52')


def _pin(data):
    return len(data),hashlib.sha256(data).hexdigest()


def transform_source(source):
    """Produce the admitted composition; all other source bytes remain exact."""
    if type(source) is not bytes or _pin(source)!=INPUT:
        raise ValueError('full-F source forms input differs')
    pieces=[];gaps=[];cursor=0;written=0
    for start,target,old,new in EDITS:
        gap=source[cursor:start]
        if source[start:start+len(old)]!=old or written+len(gap)!=target:
            raise ValueError('full-F source forms literal/offset differs')
        pieces.extend((gap,new));gaps.append(gap)
        cursor=start+len(old);written=target+len(new)
    pieces.append(source[cursor:]);gaps.append(source[cursor:])
    candidate=b''.join(pieces)
    inverse=[];new_gaps=[];cursor=0
    for start,target,old,new in EDITS:
        gap=candidate[cursor:target]
        if candidate[target:target+len(new)]!=new:
            raise ValueError('full-F source forms inverse literal differs')
        inverse.extend((gap,old));new_gaps.append(gap);cursor=target+len(new)
    inverse.append(candidate[cursor:]);new_gaps.append(candidate[cursor:])
    if (_pin(candidate)!=OUTPUT or b''.join(inverse)!=source or gaps!=new_gaps
            or _pin(b''.join(gaps))!=COMPLEMENT):
        raise ValueError('full-F source forms output/inverse/complement differs')
    return candidate,{
        'family':'F','policy':'full','stage':'piece-index-and-history-literal',
        'input_bytes':INPUT[0],'input_sha256':INPUT[1],
        'output_bytes':OUTPUT[0],'output_sha256':OUTPUT[1],
        'raw_delta':-62,'exact_inverse':True,'each_gap_exact':True,
        'complement_bytes':COMPLEMENT[0],'complement_sha256':COMPLEMENT[1],
        'piece_index_domain':'three int8_t cells, each evaluated once, same int addition',
        'history_capacity_and_types_unchanged':True,'HISTORY_macro_removed':True,
        'native_entire_bytes_equal_at_first_cost':True,'external_reads':0,
        'compiler_codec_engine_executed_by_transform':0,
    }
