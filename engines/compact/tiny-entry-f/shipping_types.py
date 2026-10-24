"""Fixed shipping-only uniform type tokens for the admitted full-key F source.

Family-owned ordinary literals; no experiment, report, old artifact, AST, type
allocator or upstream input. The existing pinned lexer is passed by the builder.
DEV bypasses this final source-presentation stage; no atomic-TT composition.
"""
import hashlib


def sha(raw):return hashlib.sha256(raw).hexdigest()


POLICY={'uint64_t': 'W', 'int16_t': 'X', 'Move': 'Y', 'zb': 'Z'}
PREFIX='typedef uint64_t W;typedef int16_t X;'
READABLE='ec39b5641ac9fc5ab19a0c919c05e0d68169b461cc1d32afeee83274926becbd'
FIXED={'map': {'uint64_t': 'W', 'int16_t': 'X', 'Move': 'Y', 'zb': 'Z'},
 'alias_prefix': 'typedef uint64_t W;typedef int16_t X;',
 'macro_old': '#define MOVE(f,t,p) ((Move)(f)|((Move)(t)<<7)|((Move)(p)<<14))\n',
 'macro_new': '#define MOVE(f,t,p) ((Y)(f)|((Y)(t)<<7)|((Y)(p)<<14))\n'}
CONTROL={'counts': {'Move': 22, 'uint64_t': 23, 'zb': 3, 'int16_t': 4},
 'ordinary_roles': [{'start': 287, 'end': 291, 'old': 'Move', 'new': 'Y', 'role': 'typedef-declarator'},
                    {'start': 340, 'end': 348, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 537, 'end': 545, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 551, 'end': 553, 'old': 'zb', 'new': 'Z', 'role': 'typedef-declarator'},
                    {'start': 579, 'end': 583, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 586, 'end': 594, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 618, 'end': 625, 'old': 'int16_t', 'new': 'X', 'role': 'type-name'},
                    {'start': 660, 'end': 662, 'old': 'zb', 'new': 'Z', 'role': 'type-name'},
                    {'start': 689, 'end': 697, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 726, 'end': 734, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 803, 'end': 811, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 925, 'end': 933, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 937, 'end': 945, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 1299, 'end': 1307, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 1335, 'end': 1343, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 1367, 'end': 1375, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 1647, 'end': 1651, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 1927, 'end': 1931, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 2197, 'end': 2201, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 2676, 'end': 2680, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 2848, 'end': 2852, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 3593, 'end': 3597, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 3828, 'end': 3836, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 3840, 'end': 3848, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 3851, 'end': 3859, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 3863, 'end': 3865, 'old': 'zb', 'new': 'Z', 'role': 'type-name'},
                    {'start': 4237, 'end': 4244, 'old': 'int16_t', 'new': 'X', 'role': 'type-name'},
                    {'start': 4330, 'end': 4334, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 4426, 'end': 4430, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 4610, 'end': 4614, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 4768, 'end': 4772, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 4950, 'end': 4958, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 5000, 'end': 5004, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 5023, 'end': 5030, 'old': 'int16_t', 'new': 'X', 'role': 'type-name'},
                    {'start': 5216, 'end': 5220, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 5444, 'end': 5448, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 5900, 'end': 5908, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 5928, 'end': 5936, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 5954, 'end': 5962, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 6074, 'end': 6082, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 6137, 'end': 6141, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 6178, 'end': 6182, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 6547, 'end': 6554, 'old': 'int16_t', 'new': 'X', 'role': 'type-name'},
                    {'start': 6769, 'end': 6773, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 6792, 'end': 6796, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 6971, 'end': 6975, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 7009, 'end': 7013, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 7228, 'end': 7232, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 7905, 'end': 7913, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 8216, 'end': 8224, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 8380, 'end': 8388, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 8551, 'end': 8559, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'}],
 'candidate_source': {'bytes': 9464,
                      'sha256': 'd942731c54f82da8dfa1aa5fedcc6328b56b32fe0ab527b5396847ceea541f26'},
 'insert_offset': 270,
 'controls': {'main.c': {'bytes': 9690,
                         'sha256': 'e0aa8dd94f6dbfa1a3da172cde28492083d259b780344f49e7f5eb906523f9f6'}}}


def transform_source(source, *, readable, lexer):
    if sha(readable)!=READABLE:raise ValueError('fixed type readable differs')
    full=FIXED;config=CONTROL
    if full['map']!=POLICY or full['alias_prefix']!=PREFIX:raise ValueError('sole literal type policy changed')
    control=config['controls']['main.c']
    if (len(source),sha(source))!=(control['bytes'],control['sha256']):raise ValueError('fixed shipping source differs')
    s=source.decode('ascii')
    if chr(92)+chr(10) in s or chr(92)+chr(13)+chr(10) in s:raise ValueError('unadmitted physical splice')
    spans=list(lexer._identifier_spans(s));all_names={t for a,b,t in spans};directive_names=set()
    for line in s.splitlines():
        if line.lstrip().startswith('#'):
            directive_names.update(t for a,b,t in lexer._identifier_spans(line.lstrip()[1:]))
    if not set(POLICY.values()).isdisjoint(all_names|directive_names):raise ValueError('fresh alias already has source binding/use')
    selected=[(a,b,t) for a,b,t in spans if t in POLICY]
    expected=[(r['start'],r['end'],r['old']) for r in config['ordinary_roles']]
    if selected!=expected:raise ValueError('role-admitted type positions differ')
    counts={t:sum(old==t for a,b,old in selected) for t in POLICY}
    if counts!=config['counts']:raise ValueError('fixed type counts differ')
    macro=full['macro_old'];replacement=full['macro_new']
    if s.count(macro)!=1 or replacement!=macro.replace('Move','Y') or macro.count('Move')!=3:
        raise ValueError('sole MOVE cast directive differs')
    if '#' in macro[1:] or '##' in macro:raise ValueError('stringify/paste is not admitted')
    anchor='typedef unsigned Move;';insert=s.index(anchor)
    if s.count(anchor)!=1 or insert!=config['insert_offset']:raise ValueError('owned typedef insertion changed')
    if any(s.index(line)>=insert for line in s.splitlines() if line.startswith('#include ')):
        raise ValueError('aliases must follow every include')
    edits=[dict(start=a,end=b,old=s[a:b],new=POLICY[t],role='ordinary-type-token') for a,b,t in selected]
    a=s.index(macro);edits.append(dict(start=a,end=a+len(macro),old=macro,new=replacement,role='exact-MOVE-casts'))
    edits.append(dict(start=insert,end=insert,old='',new=PREFIX,role='after-includes-type-aliases'))
    edits.sort(key=lambda x:x['start'])
    if any(a['end']>b['start'] for a,b in zip(edits,edits[1:])):raise ValueError('type edit overlap')
    output=s
    for row in reversed(edits):output=output[:row['start']]+row['new']+output[row['end']:]
    result=output.encode('ascii')
    if (len(result),sha(result))!=(config['candidate_source']['bytes'],config['candidate_source']['sha256']):raise ValueError('sole type candidate identity differs')
    delta=0;before=[];after=[];oc=nc=0
    for row in edits:
        row['new_start']=row['start']+delta;row['new_end']=row['new_start']+len(row['new'])
        before.append(s[oc:row['start']]);after.append(output[nc:row['new_start']])
        oc=row['end'];nc=row['new_end'];delta+=len(row['new'])-len(row['old'])
    before.append(s[oc:]);after.append(output[nc:])
    if before!=after:raise ValueError('non-type protected complement differs')
    inverse=output
    for row in reversed(edits):
        if inverse[row['new_start']:row['new_end']]!=row['new']:raise ValueError('type inverse span differs')
        inverse=inverse[:row['new_start']]+row['old']+inverse[row['new_end']:]
    if inverse!=s:raise ValueError('full inverse differs')
    return result,dict(exact_inverse=True,protected_complement_exact=True,
        protected_complement_bytes=sum(map(len,before)),protected_complement_sha256=sha(''.join(before).encode()),
        map=POLICY,ordinary_counts=counts,macro_Move_casts=3,alias_definition_cost=len(PREFIX),
        source_delta=len(result)-len(source),fresh_source_aliases=True,edits=edits,
        stage='shipping-only final type-token presentation',header_collision_gate='actual full-native equality',
        external_symbol_or_layout_change_intended=False,AST=0,PP=0)
