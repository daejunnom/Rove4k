"""One role-admitted type-token policy; no alias search or C AST."""
import hashlib

POLICIES={'B': {'uint64_t': 'D', 'Move': 'N'}, 'C': {'uint64_t': 'M', 'Move': 'T'}, 'E': {'uint64_t': 'I', 'Move': 'T'}}

LATE_INCLUDES={'B': [], 'C': [{'offset': 4060, 'line': '#include <immintrin.h>'}], 'E': []}

def sha(raw):return hashlib.sha256(raw).hexdigest()


def transform(source,full,config,lexer):
    POLICY=POLICIES[config['family']];PREFIX='typedef uint64_t '+POLICY['uint64_t']+';'
    if full['policies']!=POLICIES or config['map']!=POLICY or config['alias_prefix']!=PREFIX:raise ValueError('sole family type policy changed')
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
    macro=full['macro_old'];replacement=config['macro_new']
    if s.count(macro)!=1 or replacement!=macro.replace('Move',POLICY['Move']) or macro.count('Move')!=3:
        raise ValueError('sole MOVE cast directive differs')
    if '#' in macro[1:] or '##' in macro:raise ValueError('stringify/paste is not admitted')
    anchor='typedef unsigned Move;';insert=s.index(anchor)
    if s.count(anchor)!=1 or insert!=config['insert_offset']:raise ValueError('owned typedef insertion changed')
    late=[{'offset':s.index(line),'line':line} for line in s.splitlines() if line.startswith('#include ') and s.index(line)>=insert]
    if config['late_includes']!=LATE_INCLUDES[config['family']] or late!=config['late_includes']:
        raise ValueError('fixed family late-include domain differs')
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
    output_counts={t:sum(token==t for a,b,token in lexer._identifier_spans(output)) for t in ('int16_t','zb')}
    if output_counts!=config['protected_type_counts']:raise ValueError('protected type counts differ')
    return result,dict(exact_inverse=True,protected_complement_exact=True,
        protected_complement_bytes=sum(map(len,before)),protected_complement_sha256=sha(''.join(before).encode()),
        map=POLICY,ordinary_counts=counts,protected_type_counts=output_counts,admitted_late_includes=late,macro_Move_casts=3,alias_definition_cost=len(PREFIX),
        source_delta=len(result)-len(source),fresh_source_aliases=True,edits=edits,
        stage='shipping-only final type-token presentation',header_collision_gate='actual full-native equality',
        external_symbol_or_layout_change_intended=False,AST=0,PP=0)
