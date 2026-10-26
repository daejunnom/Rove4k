#!/usr/bin/env python3
"""Finite source-level comparisons of D ideas in the full A/B/C/E/F profiles.

The selected producers and their native-identity gates are never modified.
This experiment admits freshly generated source by the existing complete source
pins and compares control/candidates with one current compiler. A historical
native gate failure remains a failure, not a qualification of this experiment.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import lzma
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCOPE = HERE.parent / 'tcec-scope'


def pin(data):
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def load(name, path):
    spec = importlib.util.spec_from_file_location('reuse_' + name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def require(value, message):
    if not value:
        raise ValueError(message)


def project(base, family, profile_id='test-p4'):
    """Replay every existing pure source stage without an old native admission."""
    owner = load('owner', SCOPE / 'build.py')
    require((len(base), pin(base)['sha256']) == owner.CONTROL[family][:2],
            'fresh maintained complete source differs')
    stages = []
    source = base

    def stage(name, directory, **args):
        nonlocal source
        module = load(name, directory / (name + '.py'))
        before = source
        source, proof = module.transform_source(source, **args)
        restore_args = {'spelling': args['spelling']} if 'spelling' in args else {}
        require(module.restore_source(source, proof, **restore_args) == before,
                'source stage inverse differs: ' + name)
        stages.append(dict(stage=name, source=pin(source), proof=proof,
                           tool=pin((directory / (name + '.py')).read_bytes())))

    first_recipe = json.loads((SCOPE / 'recipe.json').read_bytes())['selected'][family]
    policy = first_recipe['policy']
    input_family = 'F2' if family == 'F' else family
    input_module = load('c_input', SCOPE / 'c_input.py')
    compiler_recipe = json.loads((ROOT / f'engines/compact/tiny-entry-{family.lower()}/recipe.json').read_bytes())
    compiler, compiler_proof = input_module.compiler_for(base, family=input_family,
                                                       original=compiler_recipe['compiler'])
    if policy['runtime'] == 'per-go':
        stage('c_per_go', SCOPE, family=input_family, variant=policy['variant'])
    elif policy['runtime'] != 'control':
        stage('c_final', SCOPE, family=family, workers=2, final=policy['final'])
    if policy['input_profile'] != 'control':
        stage('c_input', SCOPE, family=input_family, mode=policy['input_profile'])
    if policy.get('operators'):
        stage('c_per_go_operators', SCOPE, family=input_family)
    if policy.get('line_profile', 'control') != 'control':
        stage('c_line', SCOPE, family=input_family, variant=policy['line_profile'])
    if policy.get('b_compact'):
        stage('b_compact', SCOPE,
              forms=('score', 'see', 'constants', 'promotion', 'bitindex', 'hash', 'return', 'static'))
    if policy.get('b_fields'):
        stage('b_fields', SCOPE)
    require(pin(source) == dict(bytes=first_recipe['expected']['source_bytes'],
                               sha256=first_recipe['expected']['source_sha256']),
            'selected scope source differs')
    next_recipe = json.loads((HERE / 'recipe.json').read_bytes())['selected'][family]
    stage('compose', HERE, family=family, **next_recipe['policy'])
    production = load('production', ROOT / 'engines/scripts/production.py')
    stage('profile_source', HERE, family=family, profile=production.resource_profile(profile_id))
    if family == 'B':
        stage('profile_b', HERE, profile_id=profile_id, variant='tcec-final-lf')
    else:
        stage('profile_phase', HERE, family=family, profile_id=profile_id, variant='phase-init')
    if family == 'E':
        model_module = load('e19', ROOT / 'engines/model/e19.py')
        model = model_module.Model.load(ROOT / 'engines/model/e19.json')
        old_model = model_module.Model.from_physical_source(source, model_id='reuse-control')
        source, proof = model.bind_physical_table(source, source_model=old_model)
        stages.append(dict(stage='e19', source=pin(source), proof=proof))
    spelling = load('profile_spelling', HERE / 'profile_spelling.py')
    if family == 'B':
        stage('profile_spelling', HERE, family=family, profile_id=profile_id,
              variant='atomic-assignment')
    else:
        stage('spelling_compound', HERE, family=family, profile_id=profile_id, spelling=spelling)
    if family in ('A', 'C'):
        stage('profile_scan', HERE, family=family, profile_id=profile_id)
    stage('profile_dependencies', HERE)
    return source, dict(stages=stages, compiler=list(compiler), compiler_proof=compiler_proof,
                        compression=next_recipe['compression'])


# Finite, source-bound expressions are added here after inspecting the freshly
# replayed shipping inputs. They are comparisons, never selected defaults.
OPTIONS = {
    'A': {
        'put-loop': dict(speed='small-overhead-possible', edits=[(
            'static void b(E*p,L q,L v){L a=p->b[q];if(a){p->h^=d(a,q);p->v-=r(a,q);}p->b[q]=(int8_t)v;if(v){p->h^=d(v,q);p->v+=r(v,q);if(abs(v)==6)p->k[v<0]=q;}}',
            'static void b(E*p,L q,L v){L a=p->b[q];p->b[q]=(int8_t)v;for(L s=-1;s<=1;s+=2){if(a){p->h^=d(a,q);p->v+=s*r(a,q);}a=v;}if(abs(v)==6)p->k[v<0]=q;}')]),
        'rights-packed': dict(speed='neutral-or-faster-expected', edits=[(
            'static L n(L q){J q==4?3:q==116?12:q==0?2:q==7?1:q==112?8:q==119?4:0;}',
            'static L n(L q){J !(q+16&96)?(0x4302>>(2*(q&7))&3)<<(q>>5&2):0;}')]),
        'center-fold': dict(speed='neutral-or-faster-expected', edits=[(
            'L a=abs(v),d=q>>4,f=q&7,g=v>0?d:7-d,i=7-abs(2*f-7)-abs(2*d-7),l=qi[a]',
            'L a=abs(v),g=v>0?q>>4:7-(q>>4);q^=(q>>2&17)*7;L i=2*(q&7)+(q>>3)-7,l=qi[a]')]),
        'walk-signed': dict(speed='neutral-or-faster-expected', edits=[(
            'L a=abs(p->b[o]);if(p->b[o]*s<=0)continue;',
            'L a=p->b[o]*s;if(a<=0)continue;')]),
        'walk-ranges': dict(speed='neutral-or-faster-expected', edits=[(
            'L j=a==1?(s>0?12:14):a==2?0:a==3?12:8,m=a==1?j+2:a==2?8:a==4?12:16;',
            'static const unsigned char u[7]={0,44,128,76,72,136,136};L j=u[a]&15,m=j+(u[a]>>4);if(a==1&&s<0)j+=2,m+=2;')]),
        'halfmove': dict(speed='neutral-or-faster-expected', edits=[(
            '*w=*p;w->h^=l(p);w->aI++;w->e=-1;if(abs(v)==1){w->aI=0;',
            '*w=*p;w->h^=l(p);w->aI=abs(v)==1||f?0:p->aI+1;w->e=-1;if(abs(v)==1){'),
            ('if(f)w->aI=0;', '')]),
        'castle-rights': dict(speed='neutral-or-faster-expected', edits=[(
            'if(o==u&&!c(p,u,-s)){', 'if((p->c>>w&3)&&!c(p,u,-s)){')]),
        'promotion-do': dict(speed='neutral-or-faster-expected', edits=[(
            'L d=a>1&&!(to+16&96);for(L z=d?2:0;z<=(d?5:0);z++){B[(*n)++]=MOVE(o,to,z)|(a&1)*8;}',
            'L z=a>1&&!(to+16&96)?2:0;do{B[(*n)++]=MOVE(o,to,z)|(a&1)*8;}while(z&&++z<6);')]),
    },
    'B': {
        'dead-occupied': dict(speed='sparse-scan-benefit-versus-dense-early-exit-overhead', edits=[(
            'I y(const za*p){I d=0,n=0;X(I q=0;q<128;q++)W(!(q&136)){I a=abs(p->b[q]);W(a==2)n++;else W(a==3)d|=1<<((q+(q>>4))&1);else W(a&&a<6)l 0;}l n?n==1&&!d:d!=3;}',
            'I y(const za*p){I d=0,n=0;D b=p->a[0]|p->a[1];while(b){I q=__builtin_ctzll(b);q+=q&56;b&=b-1;I a=abs(p->b[q]);W(a==2)n++;else W(a==3)d|=1<<((q+(q>>4))&1);else W(a<6)l 0;}l n?n==1&&!d:d!=3;}')]),
        'rights-packed': dict(speed='neutral-or-faster-expected', edits=[(
            'J I O(I q){I f=q%112;l (f==4?3:f==0?2:f==7)<<(q/112*2);}',
            'J I O(I q){l !(q+16&96)?(0x4302>>(2*(q&7))&3)<<(q>>5&2):0;}')]),
        'center-fold': dict(speed='neutral-or-faster-expected', edits=[(
            'I a=abs(v),d=q>>4,f=q&7,i=v>0?d:7-d,j=7-abs(2*f-7)-abs(2*d-7),m=qi[a]',
            'I a=abs(v),i=v>0?q>>4:7-(q>>4);q^=(q>>2&17)*7;I j=2*(q&7)+(q>>3)-7,m=qi[a]')]),
        'walk-ranges': dict(speed='neutral-or-faster-expected', edits=[(
            'I q=a==1?(s>0?12:14):a==2?0:a==3?12:8;I t=a==1?q+2:a==2?8:a==4?12:16;',
            'J const unsigned char u[7]={0,44,128,76,72,136,136};I q=u[a]&15,t=q+(u[a]>>4);W(a==1&&s<0)q+=2,t+=2;')]),
        'halfmove': dict(speed='neutral-or-faster-expected', edits=[(
            '*t=*p;t->h^=S(p);t->n++;t->e=-1;W(abs(v)==1){t->n=0;',
            '*t=*p;t->h^=S(p);t->n=abs(v)==1||i?0:p->n+1;t->e=-1;W(abs(v)==1){'),
            ('W(i)t->n=0;', '')]),
        'castle-rights': dict(speed='neutral-or-faster-expected', edits=[(
            'W(j==x&&!c(p,0,x,-s)){', 'W((p->c>>z&3)&&!c(p,0,x,-s)){')]),
        'promotion-do': dict(speed='neutral-or-faster-expected', edits=[(
            'X(I z=f*2;z<=f*5;z++){W(*n>=512)abort();a[(*n)++]=MOVE(zJ,to,z)|((f|d)&1)*8;}',
            'I z=f*2;do{W(*n>=512)abort();a[(*n)++]=MOVE(zJ,to,z)|((f|d)&1)*8;}while(z&&++z<6);')]),
    },
    'F': {
        'put-loop': dict(speed='small-overhead-possible', edits=[(
            'aa void b(I*p,S q,S v){S a=p->b[q];if(a){p->h^=d(a,q);p->v-=s(a,q);}p->b[q]=(int8_t)v;if(v){p->h^=d(v,q);p->v+=s(v,q);if(abs(v)==6)p->k[v<0]=q;}}',
            'aa void b(I*p,S q,S v){S a=p->b[q];p->b[q]=(int8_t)v;for(S t=-1;t<=1;t+=2){if(a){p->h^=d(a,q);p->v+=t*s(a,q);}a=v;}if(abs(v)==6)p->k[v<0]=q;}')]),
        'rights-packed': dict(speed='neutral-or-faster-expected', edits=[(
            'aa S n(S q){H q==4?3:q==116?12:q==0?2:q==7?1:q==112?8:q==119?4:0;}',
            'aa S n(S q){H !(q+16&96)?(0x4302>>(2*(q&7))&3)<<(q>>5&2):0;}')]),
        'center-fold': dict(speed='neutral-or-faster-expected', edits=[(
            'S a=qi[abs(v)],d=q>>4^7*(v<0),f=q&7,i=7-abs(2*f-7)-abs(2*d-7),j=(a&1023)',
            'S a=qi[abs(v)],d=q>>4^7*(v<0);q^=(q>>2&17)*7;S i=2*(q&7)+(q>>3)-7,j=(a&1023)')]),
        'walk-signed': dict(speed='neutral-or-faster-expected', edits=[(
            'S a=abs(p->b[j]);if(p->b[j]*s<=0)continue;',
            'S a=p->b[j]*s;if(a<=0)continue;')]),
        'walk-ranges': dict(speed='neutral-or-faster-expected', edits=[(
            'S m=a==1?(s>0?12:14):a==2?0:a==3?12:8,o=a==1?m+2:a==2?8:a==4?12:16;',
            'aa const unsigned char u[7]={0,44,128,76,72,136,136};S m=u[a]&15,o=m+(u[a]>>4);if(a==1&&s<0)m+=2,o+=2;')]),
        'halfmove': dict(speed='neutral-or-faster-expected', edits=[(
            '*t=*p;t->h^=l(p);t->a++;t->e=-1;if(abs(v)==1){t->a=0;',
            '*t=*p;t->h^=l(p);t->a=abs(v)==1||g?0:p->a+1;t->e=-1;if(abs(v)==1){'),
            ('if(g)t->a=0;', '')]),
        'castle-rights': dict(speed='neutral-or-faster-expected', edits=[(
            'if(j==u&&!T(p,0,u,-s)){', 'if((p->c>>w&3)&&!T(p,0,u,-s)){')]),
        'promotion-do': dict(speed='neutral-or-faster-expected', edits=[(
            'for(S z=f?2:0;z<=(f?5:0);z++){if(*n>=512)abort();a[(*n)++]=MOVE(c,g,z)|(d&1)*8;}',
            'S z=f?2:0;do{if(*n>=512)abort();a[(*n)++]=MOVE(c,g,z)|(d&1)*8;}while(z&&++z<6);')]),
    },
}

# A/F have the same four padding bytes before their two 64-bit keys. The new
# field is maintained by their existing put owner, including start and EP.
# This removes dead() scans, but adds work to every put; speed needs measurement.
for _family, _integer, _returned, _board, _half, _dead, _value, _static in (
        ('A', 'L', 'J', 'E', 'aI', 'ap', 'r', 'static'),
        ('F', 'S', 'H', 'I', 'a', 'af', 's', 'aa')):
    _put = OPTIONS[_family]['put-loop']['edits'][0][0]
    _signature = (f'{_static} void b({_board}*p,{_integer} q,{_integer} v){{'
        f'{_integer} a=p->b[q];p->b[q]=(int8_t)v;'
        f'for({_integer} t=-1;t<=1;t+=2){{if(a){{p->h^=d(a,q);p->v+=t*{_value}(a,q);'
        'p->z+=t*(abs(a)==6?0:1u<<(abs(a)==2?10:abs(a)==3?5*((q+(q>>4))&1):15));}a=v;}'
        'if(abs(v)==6)p->k[v<0]=q;}')
    _old_dead = (f'{_integer} {_dead}(const {_board}*p){{{_integer} d=0;'
        f'for({_integer} q=0;q<128;q=' + ('q+9&~8' if _family == 'A' else '(q+9)&~8') + ')'
        f'{{{_integer} a=abs(p->b[q]);if(a==2){{if(d){_returned} 0;d=-1;}}'
        f'else if(a==3){{if(d<0){_returned} 0;d|=1<<((q+(q>>4))&1);if(d==3){_returned} 0;}}'
        f'else if(a&&a<6){_returned} 0;}}{_returned} 1;}}')
    OPTIONS[_family]['material-loop'] = dict(speed='put-overhead-versus-dead-scan-tradeoff', edits=[
        (f'{_integer} s,c,e,k[2],{_half},v;W h,r;}}{_board};',
         f'{_integer} s,c,e,k[2],{_half},v;Y z;W h,r;}}{_board};'),
        (_put, _signature),
        (_old_dead, f'{_integer} {_dead}(const {_board}*p){{Y d=p->z;{_returned} d<32||(!(d&31)&&d<=1024);}}')])

# C's put already shares both phases and owns eight incremental SIMD lanes.
# Only the unchanged scalar geometry and mailbox consumers are projected.
OPTIONS['C'] = {}
for _name in ('rights-packed', 'walk-signed', 'walk-ranges', 'halfmove', 'castle-rights'):
    _spec = OPTIONS['A'][_name]
    OPTIONS['C'][_name] = dict(speed=_spec['speed'], edits=[
        tuple(re.sub(r'\bJ\b', 'return', re.sub(r'\bL\b', 'int', part)) for part in pair)
        for pair in _spec['edits']])
OPTIONS['C']['center-fold'] = dict(speed='neutral-or-faster-expected', edits=[(
    'int a=abs(v),d=q>>4,f=q&7,i=v>0?d:7-d;int j=7-abs(2*f-7)-abs(2*d-7);',
    'int a=abs(v),i=v>0?q>>4:7-(q>>4);q^=(q>>2&17)*7;int j=2*(q&7)+(q>>3)-7;')])
OPTIONS['C']['promotion-do'] = dict(speed='neutral-or-faster-expected', edits=[(
    'int d=a>1&&!(to+16&96);for(int z=d?2:0;z<=(d?5:0);z++){if(*n>=512)abort();B[(*n)++]=MOVE(o,to,z)|(a&1)*8;}',
    'int z=a>1&&!(to+16&96)?2:0;do{if(*n>=512)abort();B[(*n)++]=MOVE(o,to,z)|(a&1)*8;}while(z&&++z<6);')])
OPTIONS['E'] = {name: OPTIONS['A'][name] for name in
                ('rights-packed', 'walk-signed', 'walk-ranges', 'halfmove', 'castle-rights', 'promotion-do')}
# E's activity feature is half the sum-of-distance expression used by HCE.
# Valid 0x88 endpoints make both distances odd, so their sum is even.
OPTIONS['E']['center-fold'] = dict(speed='neutral-or-faster-expected', edits=[(
    'static L Q(L q){J 7-(abs(q%8*2-7)+abs(q/8-7))/2;}',
    'static L Q(L q){q^=(q>>2&17)*7;J (q&7)+(q>>4);}')])


# These whole-function alternatives were measured only on the exact replayed
# full P4 A/F sources. Other families and changed source closures need their
# own caller/hash/evaluation analysis; matching a fragment is not admission.
BOARD_INPUTS = {
    'A': dict(bytes=7595, sha256='02faeb563c435c02321fc6d497f54a31de01d9093be33bff5e44206a93dfbdc6'),
    'F': dict(bytes=7034, sha256='c89769c80c70722f2a610dbe9371edce9f4063abc15ed2fff6cdc637fec4bc6e'),
}


def source_function(source, prefix):
    require(source.count(prefix) == 1, 'one admitted function required: ' + prefix.decode())
    start = source.index(prefix)
    opening = source.index(b'{', start)
    depth = 0
    for end in range(opening, len(source)):
        depth += (source[end] == 123) - (source[end] == 125)
        if not depth:
            return source[start:end + 1]
    raise ValueError('unclosed admitted function')


def admit_board_source(source, family):
    require(family in BOARD_INPUTS and pin(source) == BOARD_INPUTS[family],
            'only the exact replayed current full P4 A/F board sources are admitted')


def sentinel_edits(source, family):
    """Use a negative generation target; every attack target remains 0x88-valid."""
    admit_board_source(source, family)
    if family == 'A':
        prefix = b'static L g(const E*p'
        replacements = [
            (b'if(B&&a==1)', b'if(f<0&&a==1)'),
            (b'if(!B&&q==f)', b'if(q==f)'),
            (b'(B&&a==1&&!t&&q!=p->e)', b'(f<0&&a==1&&!t&&q!=p->e)'),
            (b'if(B)k(', b'if(f<0)k('),
            (b'if(B&&a==6)', b'if(f<0&&a==6)'),
        ]
        calls = [(b'J g(p,B,0,p->s);', b'J g(p,B,-1,p->s);')]
    else:
        prefix = b'aa S T(const I*p'
        replacements = [
            (b'if(f&&a==1)', b'if(g<0&&a==1)'),
            (b'if(!f&&q==g)', b'if(q==g)'),
            (b'(f&&a==1&&!t&&q!=p->e)', b'(g<0&&a==1&&!t&&q!=p->e)'),
            (b'if(f)e(', b'if(g<0)e('),
            (b'if(f&&a==6)', b'if(g<0&&a==6)'),
        ]
        calls = [(b'T(p,x,0,p->s)', b'T(p,x,-1,p->s)'),
                 (b'T(b,a,0,b->s)', b'T(b,a,-1,b->s)')]
    old = source_function(source, prefix)
    new = old
    for before, after in replacements:
        require(new.count(before) == 1, 'sentinel function consumer differs')
        new = new.replace(before, after, 1)
    return [(old, new), *calls], dict(
        whole_input=BOARD_INPUTS[family],
        mode='generation target -1; ordinary attacks retain valid 0x88 square',
        generation_callers=len(calls), output_pointer_tests_replaced=5,
        legal_order_and_nbrq_preserved=True)


def start_precomputed_edits(source, family):
    """Derive start state from the exact admitted family's hash and evaluation."""
    admit_board_source(source, family)
    mask = (1 << 64) - 1

    def mix(x):
        # F's shipping mix omits the Weyl increment present in A and D.
        # The whole-source pin owns this distinction; D's key is not reused.
        if family == 'A':
            x = (x + 0x9e3779b97f4a7c15) & mask
        x = ((x ^ (x >> 30)) * 0xbf58476d1ce4e5b9) & mask
        x = ((x ^ (x >> 27)) * 0x94d049bb133111eb) & mask
        return x ^ (x >> 31)

    def value(v, q):
        kind = abs(v)
        rank, file = q >> 4, q & 7
        center = 7 - abs(2 * file - 7) - abs(2 * rank - 7)
        reflected = rank if v > 0 else 7 - rank
        if family == 'A':
            score = (0, 100, 320, 330, 500, 900, 0)[kind]
            score += reflected * (7 if kind == 1 else 2 if kind == 4 else 0)
            score += center * (9 if kind == 2 else 5 if kind == 3 else
                               -3 if kind == 6 else 2 * (kind in (1, 5)))
        else:
            packed = (24576, 48228, 98624, 65866, 27124, 41860, 0)[kind]
            score = ((packed & 1023) + reflected * ((packed >> 10) & 7) +
                     center * ((packed >> 13) - 3))
        return score if v > 0 else -score

    board = [0] * 128
    for f, v in enumerate((4, 2, 3, 5, 6, 3, 2, 4)):
        board[f], board[16 + f], board[96 + f], board[112 + f] = v, 1, -1, -v
    key, evaluation, kings = mix(2063), 0, [-1, -1]
    for q, v in enumerate(board):
        if not v:
            continue
        key ^= mix(q + (v + 6) * 128)
        evaluation += value(v, q)
        if abs(v) == 6:
            kings[v < 0] = q
    require(evaluation == 0 and kings == [4, 116], 'admitted start derivation differs')
    typ, integer, storage, start = ('E', 'L', 'static', 'q') if family == 'A' else ('I', 'S', 'aa', 'o')
    old = source_function(source, f'void {start}({typ}*p)'.encode())
    after = (f'void {start}({typ}*p){{{storage} const {integer} qa[8]={{4,2,3,5,6,3,2,4}};'
             f'*p=({typ}){{0}};p->s=1;p->c=15;p->e=-1;p->k[0]=4;p->k[1]=116;'
             f'p->h=p->r=0x{key:016x};for({integer} f=0;f<8;f++){{p->b[f]=qa[f];'
             'p->b[16+f]=1;p->b[96+f]=-1;p->b[112+f]=-qa[f];}}').encode()
    return [(old, after)], dict(whole_input=BOARD_INPUTS[family], key=hex(key),
        evaluation=evaluation, kings=kings, initialization_calls_removed=32,
        board_layout_unchanged=True)


for _family in ('A', 'F'):
    OPTIONS[_family]['walk-sentinel'] = dict(speed='neutral-or-faster-expected',
                                            derived_edits=sentinel_edits)
    OPTIONS[_family]['start-precomputed'] = dict(speed='startup-only-work-reduction',
                                                derived_edits=start_precomputed_edits)


def transform(source, family, options):
    require(type(source) is bytes and family in OPTIONS, 'supported immutable full source required')
    require(len(options) == len(set(options)), 'repeated reuse option')
    require(not {'start-precomputed', 'material-loop'} <= set(options),
            'precomputed start does not initialize the separate material-cache layout')
    edits, derivations = [], {}
    for option in options:
        require(option in OPTIONS[family], 'unknown family reuse option: ' + option)
        spec = OPTIONS[family][option]
        if 'derived_edits' in spec:
            pairs, derivations[option] = spec['derived_edits'](source, family)
        else:
            pairs = [(before.encode(), after.encode()) for before, after in spec['edits']]
        for before, after in pairs:
            require(source.count(before) == 1, 'one exact source consumer required: ' + option)
            edits.append((source.index(before), before, after, option))
    edits.sort()
    cursor = 0
    for at, before, _, option in edits:
        require(at >= cursor, 'overlapping reuse options: ' + option)
        cursor = at + len(before)
    candidate = source
    for at, before, after, _ in reversed(edits):
        candidate = candidate[:at] + after + candidate[at + len(before):]
    return candidate, dict(options=list(options), input=pin(source), output=pin(candidate),
                           derivations=derivations,
                           edits=[dict(at=a, old=b.decode(), new=c.decode(), option=d)
                                  for a, b, c, d in edits])


def render_board_fixture(rules, source, control, family, options, cases):
    """Keep the measured A/F start-state and generation-caller observations."""
    admit_board_source(control, family)
    binding = dict(rules.BINDINGS[family])
    typ, start, half = ('E', 'q', 'aI') if family == 'A' else ('I', 'o', 'a')
    old = source_function(control, f'void {start}({typ}*p)'.encode())
    ref = old.replace(f'void {start}('.encode(), b'static void rv_ref_start(', 1)
    extra = b'\n' + ref
    if family == 'F':
        mode = -1 if 'walk-sentinel' in options else 0
        extra += (f'\nstatic int rv_gen(const I*p,unsigned*out){{return T(p,out,{mode},p->s);}}').encode()
        binding.update(generate='rv_gen', four_args=False)
    extra += (f'\nstatic void rv_start_equal(const {typ}*p){{{typ} ref;rv_ref_start(&ref);'
              f'if(memcmp(p->b,ref.b,sizeof p->b)||p->s!=ref.s||p->c!=ref.c||p->e!=ref.e||'
              f'p->k[0]!=ref.k[0]||p->k[1]!=ref.k[1]||p->{half}!=ref.{half}||p->v!=ref.v||'
              f'p->h!=ref.h||p->r!=ref.r)abort();}}\n').encode()
    result = rules.render_bound_fixture(source, binding, cases, extra)
    before = f'{typ} board;{start}(&board);char line[4096];'.encode()
    require(result.count(before) == 1, 'start comparison fixture boundary differs')
    return result.replace(before, before.replace(b'char line', b'rv_start_equal(&board);char line'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--entry', choices=tuple('ABCEF'), required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--case', action='append', default=[])
    parser.add_argument('--rules', action='store_true')
    args = parser.parse_args()
    out = args.out
    require(out.is_absolute() and not out.exists() and
            not any((p / '.git').exists() for p in (out, *out.parents)),
            'new absolute output outside every checkout required')
    out.mkdir(parents=True)
    report = dict(family=args.entry, profile='test-p4', complete=False, commands=[], cases=[],
                  selected=False, runtime_qualified=False, historical_native_admitted=False,
                  tool=pin(Path(__file__).read_bytes()))
    def save():
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    owner = load('build_owner', SCOPE / 'build.py')
    owner.LIMITS.update(aggregate_wall=1200, per_command_wall=180, parent_AS=4 << 30,
                        child_AS=2 << 30, child_CPU=150, parent_CPU=600, parent_CPU_hard=660,
                        tool_output_bytes=8 << 20)
    host = owner.Host(out, report, save)
    try:
        maintained = out / 'maintained'
        builder = ROOT / f'engines/compact/tiny-entry-{args.entry.lower()}/build.py'
        try:
            host.run([sys.executable, '-I', '-B', str(builder), '--wrapper', 'shell', '--out',
                      str(maintained)], cwd=out, kind='maintained-generation')
        except ValueError:
            # A complete source can be observed before a later native admission
            # rejects this toolchain. The failed run remains failed in this report.
            record = json.loads((maintained / 'build.json').read_bytes())
            require(record.get('error') == "ValueError('native ELF identity mismatch')",
                    'maintained generation failed outside the historical native gate')
            terminal = report['commands'][-1]
            require(terminal['terminal'] and terminal['reaped'] and terminal['owned_group_absent']
                    and not terminal['forced_cleanup'], 'failed generator did not settle cleanly')
            report['maintained_native_failure'] = record['error']
        else:
            report['historical_native_admitted'] = True
        locations = [maintained / 'main.c', maintained / 'attempt-1/main.c', maintained / 'first/main.c']
        available = [p for p in locations if p.is_file()]
        require(available, 'no freshly generated complete source')
        base = available[0].read_bytes()
        source, chain = project(base, args.entry)
        (out / 'control.c').write_bytes(source)
        report.update(chain=chain, base=pin(base), source=pin(source))
        package = load('source_package', ROOT / 'engines/scripts/source_package.py')
        wrapper = load('wrapper', HERE / 'wrapper.py')
        unlink = load('self_unlink', HERE / 'self_unlink.py')
        compiler = chain['compiler']
        report['compiler_version'] = host.run([compiler[0], '--version'], cwd=out,
                                               kind='compiler-version').decode().splitlines()[0]
        rules = load('rules', HERE / 'profile_rules.py')
        cases, coverage = rules.fixture_cases() if args.rules else (None, None)
        compare_values = args.rules and any('center-fold' in case.split('+') for case in args.case)
        compare_board = args.rules and args.entry in BOARD_INPUTS and any(
            {'walk-sentinel', 'start-precomputed'} & set(case.split('+')) for case in args.case)
        value_control = None
        for name in ['control', *args.case]:
            options = () if name == 'control' else tuple(name.split('+'))
            candidate, proof = transform(source, args.entry, options) if options else (source, None)
            directory = out / name
            directory.mkdir()
            (directory / 'main.c').write_bytes(candidate)
            host.run(compiler, cwd=directory, kind=name + '-compile', data=candidate)
            native = (directory / 'x').read_bytes()
            (directory / 'native').write_bytes(native)
            whole = wrapper.package(package, unlink, candidate, chain['compression'], compiler)
            header = wrapper.header(package, unlink, compiler)
            require(lzma.decompress(whole[len(header):], format=lzma.FORMAT_ALONE) == candidate,
                    'complete source inverse differs')
            (directory / 'x').write_bytes(whole)
            row = dict(name=name, source=pin(candidate), native=pin(native), whole=pin(whole),
                       header=pin(header), proof=proof, rules=None)
            report['cases'].append(row)
            if args.rules:
                fixture = (render_board_fixture(rules, candidate, source, args.entry, options, cases)
                           if compare_board else rules.render_fixture(candidate, args.entry, cases))
                (directory / 'rules.c').write_bytes(fixture)
                observations = []
                for mode, flags in [('plain', []), ('ubsan', ['-fsanitize=undefined', '-fno-sanitize-recover=all'])]:
                    program = directory / ('rules-' + mode)
                    host.run(['cc', '-O1', '-pthread', *(['-mavx2'] if args.entry == 'C' else []),
                              *flags, str(directory / 'rules.c'), '-o', str(program)],
                             cwd=directory, kind=name + '-rules-build-' + mode)
                    data = host.run([str(program)], cwd=directory, kind=name + '-rules-run-' + mode)
                    observations.append(dict(mode=mode, **rules._compare_output(data, cases)))
                row['rules'] = dict(observations=observations, coverage=coverage,
                                    fixture=pin(fixture), verifier=pin((HERE / 'profile_rules.py').read_bytes()))
                if compare_board:
                    row['rules']['all_start_fields_equal_original'] = True
                if name != 'control':
                    expected = report['cases'][0]['rules']['observations']
                    require([r['stdout'] for r in observations] == [r['stdout'] for r in expected],
                            'actual generated legal move order differs from control')
                    row['rules']['order_equal_to_control'] = True
                if compare_values and (name == 'control' or 'center-fold' in options):
                    expression = 'Q(q)' if args.entry == 'E' else ('s' if args.entry == 'F' else 'r') + '(p,q)'
                    lower, upper = (0, 0) if args.entry == 'E' else (-6, 6)
                    value_fixture = (b'#define main rv_reuse_original_main\n' + candidate +
                        ('\n#undef main\nint main(void){for(int p=' + str(lower) + ';p<=' + str(upper) +
                         ';p++)for(int q=0;q<128;q=(q+9)&~8)printf("%d\\n",' + expression +
                         ');return 0;}\n').encode())
                    (directory / 'values.c').write_bytes(value_fixture)
                    program = directory / 'values'
                    host.run(['cc', '-O1', '-pthread', *(['-mavx2'] if args.entry == 'C' else []),
                              '-fsanitize=undefined', '-fno-sanitize-recover=all',
                              str(directory / 'values.c'), '-o', str(program)],
                             cwd=directory, kind=name + '-value-build')
                    data = host.run([str(program)], cwd=directory, kind=name + '-value-run')
                    if name == 'control':
                        value_control = data
                    else:
                        require(data == value_control, 'finite actual evaluation domain differs')
                    row['values'] = dict(cases=(upper-lower+1)*64, stdout=pin(data),
                                         equal_to_control=name != 'control', fixture=pin(value_fixture))
            save()
            print(json.dumps({k: row[k] for k in ('name', 'source', 'native', 'whole')}), flush=True)
        report['complete'] = True
    except BaseException as error:
        report['failure'] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        host.close()
        save()


if __name__ == '__main__':
    main()
