"""One source-only 32-bit move-effect projection of audited scalar D.

The generated list owns special-move geometry. make consumes its extra-square
descriptor; search and the atomic128 TT keep the original low17 identity.
Callers supply source.project/restore. This module never compiles, packages,
executes an engine, imports a target helper, or writes generated files.
"""
from __future__ import annotations

import hashlib


SCHEMA = 'rove4k.d.move-effects-source.v1'
INPUT = {
    'tiny.h': (3052, 'd24ccd0ea44a0fa8c984bf3085a9495e54bc76c75b4c7bcd8b217d938e07417b'),
    'board.c': (10346, '4f00f4c88eefe89fb6a61445a566c034095d074b14db37a07919fc3c45b48070'),
    'search.c': (6001, 'c25fe0cc2faf50397e9cf24af92eab5de4133341a893a05a740672f939282099'),
    'runtime.c': (15784, 'eea671466ff74b3f619d99f90278f30b491c163e40335d61dbe585090deea4e4'),
    'start.S': (697, '701f24836cffd49614235cfe11e6b961ee1b2c2b7d2466965b0916217cf43586'),
    'image.ld': (446, '38756c865914b52432572864446fcc58b791dfb508af8a33156d5c190c01044b'),
}
CHANGED = ('tiny.h', 'board.c', 'search.c')

MOVE_MACROS = b'''#define MOVE(f,t,p) ((Move)(f)|((Move)(t)<<7)|((Move)(p)<<14))
/* Identity belongs to ordering/TT; the generated descriptor belongs to make.
 * Zero extras mean ordinary, equal nonzero extras EP, unequal extras castle.
 * A castle from a1 still has a nonzero destination descriptor. */
#define IDENTITY(m) ((m)&131071u)
#define EFFECT(a,b) (((Move)(a)<<17)|((Move)(b)<<24))
#define EXTRA_FROM(m) (((m)>>17)&127)
#define EXTRA_TO(m) (((m)>>24)&127)
_Static_assert(sizeof(Move)==4 && UINT_MAX==UINT32_MAX,"32-bit move effects");
#if D_HQ || DEV
#error D move effects projection requires D_HQ=0 and DEV=0
#endif
'''

APPLY_EFFECT = b'''    if(m>>17){
        int a=EXTRA_FROM(m),b=EXTRA_TO(m);
        put(t,a,0);if(a!=b)put(t,b,s*4);
    }
'''


def pin(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def pins(files):
    return {name: pin(data) for name, data in sorted(files.items())}


def contract():
    """Return the supported source/representation boundary, not acceptance."""
    return dict(schema=SCHEMA, hq=0, dev=0, move_bits=32,
                identity_mask=131071, extra_from_shift=17, extra_to_shift=24,
                extra_square_mask=127, ordinary='A=B=0',
                en_passant='A=B!=0: remove A',
                castle='A!=B: remove A, insert side*4 at B',
                tt='unchanged aligned atomic128; stores low17 identity only',
                frames='unchanged Move and Board arrays and worker storage',
                source_only=True, compiled=False, cost_measured=False,
                runtime_qualified=False, selected=False)


def _configuration(hq, dev):
    if type(hq) is not int or type(dev) is not int or hq != 0 or dev != 0:
        raise ValueError('move effects supports only explicit HQ=0/DEV=0')
    return dict(hq=hq, dev=dev)


def _admit(files):
    if type(files) is not dict or set(files) != set(INPUT):
        raise ValueError('exact audited six-file input required')
    if any(type(data) is not bytes for data in files.values()):
        raise ValueError('audited source bytes required')
    expected = {name: dict(bytes=size, sha256=sha) for name, (size, sha) in INPUT.items()}
    if pins(files) != expected or any(b'\r' in data for data in files.values()):
        raise ValueError('audited fast-capacity LF source pin differs')


def _replace(data, before, after, count):
    if data.count(before) != count:
        raise ValueError('move-effect generation source count differs')
    return data.replace(before, after)


def _walk(board):
    begin, end = b'#if D_HQ || DEV\n', b'int gen(const Board *p,Move *moves)'
    if board.count(begin) != 1 or board.count(end) != 1:
        raise ValueError('unique move-generation boundary required')
    old = board[board.index(begin):board.index(end)]
    new = old
    # Update both readable backends, while the projection/compiler contract
    # deliberately admits only the current scalar shipping configuration.
    for before, after, count in (
        (b'add(moves,&n,from,to,!!p->b[to]);',
         b'add(moves,&n,from,to,!!p->b[to],0);', 1),
        (b'add(moves,&n,from,to,2);',
         b'add(moves,&n,from,to,2,0);', 2),
        (b'add(moves,&n,from,to+s*16,0);',
         b'add(moves,&n,from,to+s*16,0,0);', 2),
        (b'add(moves,&n,from,to,a==1?3:!!target);',
         b'add(moves,&n,from,to,a==1?3:!!target,a==1&&!target?EFFECT(to-s*16,to-s*16):0);', 2),
        (b'add(moves,&n,from,home+2*d,0);',
         b'add(moves,&n,from,home+2*d,0,EFFECT(home+(d>0?3:-4),home+d));', 2),
    ):
        new = _replace(new, before, after, count)
    return old, new


def transform(files, source, *, hq=0, dev=0):
    """Project exact six LF inputs; reject other modes before source generation."""
    configuration = _configuration(hq, dev)
    _admit(files)
    walk_before, walk_after = _walk(files['board.c'])
    castle = b'''    if(abs(v)==6&&abs(to-from)==2){
        int rook=to>from?from+3:from-4,transit=to>from?from+1:from-1;
        put(t,rook,0);put(t,transit,s*4);
    }
'''
    edits = {
        'tiny.h': [('identity-and-generated-effect-layout',
                    b'#define MOVE(f,t,p) ((Move)(f)|((Move)(t)<<7)|((Move)(p)<<14))\n',
                    MOVE_MACROS)],
        'board.c': [
            ('synthetic-EP-effect-descriptor',
             b'MOVE(q,p->e,0),&t)',
             b'(MOVE(q,p->e,0)|EFFECT(p->e-p->s*16,p->e-p->s*16)),&t)'),
            ('generated-EP-replaces-application-geometry',
             b'        if(to==p->e&&!target)put(t,to-s*16,0);\n', b''),
            ('one-generated-extra-action-owner', castle, APPLY_EFFECT),
            ('emitter-accepts-effect-descriptor',
             b'static void add(Move *moves,int *n,int from,int to,int kind){',
             b'static void add(Move *moves,int *n,int from,int to,int kind,Move extra){'),
            ('emitter-retains-identity-and-effect',
             b'MOVE(from,to,z)|((kind&1)<<3);',
             b'MOVE(from,to,z)|((kind&1)<<3)|extra;'),
            ('generator-owns-special-geometry', walk_before, walk_after),
        ],
        'search.c': [
            ('TT-order-compares-identity', b'scores[i]=m==tt?',
             b'scores[i]=IDENTITY(m)==tt?'),
            ('worker-jitter-retains-identity', b'(m*37u+w->id*19u)%17',
             b'(IDENTITY(m)*37u+w->id*19u)%17'),
            ('atomic128-payload-retains-identity', b'data=bestmove|',
             b'data=IDENTITY(bestmove)|'),
        ],
    }
    output = dict(files)
    proof = dict(schema=SCHEMA, configuration=configuration, contract=contract(),
                 input=pins(files), source_edits={})
    for name, roles in edits.items():
        output[name], proof['source_edits'][name] = source.project(files[name], roles)
    proof['output'] = pins(output)
    if restore(output, proof, source) != files:
        raise ValueError('move-effect full six-file inverse differs')
    return output, proof


def restore(files, proof, source):
    """Restore every exact admitted byte through the existing inverse owner."""
    if type(proof) is not dict or proof.get('schema') != SCHEMA:
        raise ValueError('move-effect proof schema differs')
    configuration = proof.get('configuration')
    if type(configuration) is not dict or set(configuration) != {'hq', 'dev'}:
        raise ValueError('move-effect configuration differs')
    _configuration(configuration['hq'], configuration['dev'])
    if proof.get('contract') != contract():
        raise ValueError('move-effect projection contract differs')
    if type(files) is not dict or set(files) != set(INPUT) or pins(files) != proof['output']:
        raise ValueError('move-effect output differs')
    if set(proof['source_edits']) != set(CHANGED):
        raise ValueError('move-effect source roles differ')
    restored = dict(files)
    for name in CHANGED:
        restored[name] = source.restore(files[name], proof['source_edits'][name])
    _admit(restored)
    if pins(restored) != proof['input']:
        raise ValueError('move-effect inverse input differs')
    return restored
