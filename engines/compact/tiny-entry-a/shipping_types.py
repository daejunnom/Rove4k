"""Fixed shipping-only uniform type tokens for the admitted A source.

Family-owned ordinary literals; no experiment, report, old artifact, AST, type
allocator or upstream input. The existing pinned lexer is passed by the builder.
DEV bypasses this final source-presentation stage.
"""
import hashlib


def sha(raw):return hashlib.sha256(raw).hexdigest()


POLICY={'uint64_t': 'W', 'int16_t': 'X', 'Move': 'Y', 'zb': 'Z'}
PREFIX='typedef uint64_t W;typedef int16_t X;'
READABLE='71f9ff6ce1b7f555ad85c3bf49766381c0627315da94acf0c49eeee7bee4a734'
FIXED={'map': {'uint64_t': 'W', 'int16_t': 'X', 'Move': 'Y', 'zb': 'Z'},
 'alias_prefix': 'typedef uint64_t W;typedef int16_t X;',
 'macro_old': '#define MOVE(f,t,p) ((Move)(f)|((Move)(t)<<7)|((Move)(p)<<14))\n',
 'macro_new': '#define MOVE(f,t,p) ((Y)(f)|((Y)(t)<<7)|((Y)(p)<<14))\n'}
CONTROL={'counts': {'Move': 19, 'uint64_t': 23, 'zb': 3, 'int16_t': 3},
 'ordinary_roles': [{'start': 304, 'end': 308, 'old': 'Move', 'new': 'Y', 'role': 'typedef-declarator'},
                    {'start': 358, 'end': 366, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 554, 'end': 562, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 569, 'end': 571, 'old': 'zb', 'new': 'Z', 'role': 'typedef-declarator'},
                    {'start': 598, 'end': 602, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 605, 'end': 613, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 640, 'end': 647, 'old': 'int16_t', 'new': 'X', 'role': 'type-name'},
                    {'start': 685, 'end': 687, 'old': 'zb', 'new': 'Z', 'role': 'type-name'},
                    {'start': 714, 'end': 722, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 750, 'end': 758, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 827, 'end': 835, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 949, 'end': 957, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 961, 'end': 969, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 1335, 'end': 1343, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 1371, 'end': 1379, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 1403, 'end': 1411, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 1680, 'end': 1684, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 2254, 'end': 2258, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 2714, 'end': 2718, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 2862, 'end': 2866, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 3606, 'end': 3610, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 3839, 'end': 3847, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 3851, 'end': 3859, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 3862, 'end': 3870, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 3874, 'end': 3876, 'old': 'zb', 'new': 'Z', 'role': 'type-name'},
                    {'start': 4252, 'end': 4259, 'old': 'int16_t', 'new': 'X', 'role': 'type-name'},
                    {'start': 4346, 'end': 4350, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 4471, 'end': 4475, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 4634, 'end': 4638, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 4820, 'end': 4828, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 4871, 'end': 4875, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 4894, 'end': 4901, 'old': 'int16_t', 'new': 'X', 'role': 'type-name'},
                    {'start': 5101, 'end': 5105, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 5383, 'end': 5387, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 6244, 'end': 6252, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 6272, 'end': 6280, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 6298, 'end': 6306, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 6420, 'end': 6428, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 6457, 'end': 6461, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 6757, 'end': 6761, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 6780, 'end': 6784, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 6959, 'end': 6963, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 6995, 'end': 6999, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 7225, 'end': 7229, 'old': 'Move', 'new': 'Y', 'role': 'type-name'},
                    {'start': 7902, 'end': 7910, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 8213, 'end': 8221, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 8377, 'end': 8385, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'},
                    {'start': 8548, 'end': 8556, 'old': 'uint64_t', 'new': 'W', 'role': 'type-name'}],
 'candidate_source': {'bytes': 9476,
                      'sha256': '71ae2a35736743103e72b2bb4738b8e71d2da9a78af44ad24b61c4157548ca27'},
 'insert_offset': 287,
 'controls': {'main.c': {'bytes': 9687,
                         'sha256': '6946861173a6b1dee660e83d72db40cde36a066be04e3c4457d4b67a6ab7ae4e'}}}


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
