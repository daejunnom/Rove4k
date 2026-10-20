"""One shipping specialization for the closed legal-startpos-history API.

The exact control already requires generated move membership.  This change
adds the stronger shipping-only predecessor-legality precondition; DEV keeps
its FEN admission and both original checks byte for byte after preprocessing.
"""
import hashlib

CONTROL_SHA256 = '38d6c829a4d98a172b01c945a20e091bd529a5998174896dbf0ad2dbc01a0a7b'
OMITTED = {
    'king_capture': 'a legal predecessor leaves its own king unattacked by the next side; no generated next move can target that king',
    'list_capacity': 'at most 16 own pieces including exactly one king: 15*27+10=415 pseudo moves, below MOVES=512',
}


def transform(data):
    if hashlib.sha256(data).hexdigest() != CONTROL_SHA256:
        raise ValueError('unknown qualified minimal A readable control')
    source = data.decode('utf-8')
    for before in ('    if(abs(target)==6)return 0;\n',
                   '        if(*n>=MOVES)abort();\n'):
        if source.count(before) != 1:
            raise ValueError('unexpected guard multiplicity: ' + before.strip())
        source = source.replace(before, '#if DEV\n' + before + '#endif\n', 1)
    return source.encode(), dict(OMITTED)
