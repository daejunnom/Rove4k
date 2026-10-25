"""Compose reviewed projections on one exact selected source, never fuzzy input.

Each producer first admits the original full source independently. Edits use
that original coordinate system and must be disjoint. Entry unlink is checked
against the composed body before its edit is added. A full inverse protects
the entire untouched body; individual proofs retain their own semantic scope.
"""
import hashlib
import importlib.util
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
PINS = {
    'self_unlink': '9daf5a0e942b475608ec52146725c66a7935c6771c641af22466ae747c4b72a4',
    'per_go': '9fca19ea6eac67a5037251c1bf8d6ffcbad507223db02890ac320a537c76bd96',
    'history_layout': 'ecbbec6299e4a2bcdf28afd1f56863faf9774b687f93f9cf47b1b8f58ce1b856',
    'search_queries': '9dd9b7f9cf89ccfa35b0080fe08512ead290fe707720fb15db2b59b040b0dd04',
    'b_state': '1698694f4f8ebffd4fa6b7512475c690771f595a59c7ef5d8c3f9aa64ff9c46e',
}


def pin(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def require(value, message):
    if not value:
        raise ValueError(message)


def module(name):
    path = HERE/(name+'.py')
    data = path.read_bytes().replace(b'\r\n', b'\n')
    require(b'\r' not in data and pin(data)['sha256'] == PINS[name], 'projection source drift: '+name)
    spec = importlib.util.spec_from_file_location('next_composed_'+name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = result
    spec.loader.exec_module(result)
    return result


def transform_source(source, *, family, per_go=True, prefix=True, dense=False,
                     tt='control', qs=False, occupancy=False, unlink_variant='return-short',entry_names=None):
    unlink = module('self_unlink')
    # Admission precedes all extraction, including combinations with no edits.
    unlink.transform_source(source, family=family,variant=unlink_variant)
    require(all(type(v) is bool for v in (per_go,prefix,dense,qs,occupancy)), 'explicit boolean projections required')
    require(not occupancy or family == 'B', 'occupancy-only projection is B-specific')
    rows, stages = [], []

    def spans(name, proof, values):
        stages.append({'stage': name, 'proof': proof})
        for value in values:
            rows.append(dict(stage=name, role=value['role'], begin=value['begin'],
                             before=value['before'], after=value['after']))

    if per_go and family in ('A','B','C','E'):
        helper=module('per_go'); candidate, proof=helper.transform_source(source,family=family)
        require(helper.restore_source(candidate,proof)==source, 'per-GO inverse differs')
        spans('per-GO',proof,[dict(begin=r['old_start'],before=r['old'].encode(),after=r['new'].encode(),role=r['role']) for r in proof['spans']])
    if (prefix and family not in ('F','F8')) or dense:
        helper=module('history_layout')
        candidate,proof=helper.transform_source(source,family=family,prefix=prefix,dense=dense)
        require(helper.restore_source(candidate,proof)==source, 'history inverse differs')
        spans('history',proof,helper.source_edits(source,family=family,prefix=prefix,dense=dense))
    if tt!='control' or qs:
        helper=module('search_queries')
        candidate,proof=helper.transform_source(source,family=family,tt=tt,qs=qs)
        require(helper.restore_source(candidate,proof)==source, 'query inverse differs')
        spans('queries',proof,helper.source_edits(source,family=family,tt=tt,qs=qs))
    if occupancy:
        helper=module('b_state');candidate,proof=helper.transform_source(source)
        require(helper.restore_source(candidate,proof)==source, 'occupancy inverse differs')
        spans('occupancy',proof,[dict(begin=r['old_start'],before=r['old'].encode(),after=r['new'].encode(),role=r['role']) for r in proof['spans']])

    def apply(edits):
        result, at = [], 0
        for row in sorted(edits,key=lambda r:r['begin']):
            start, before=row['begin'],row['before']
            require(start>=at and source[start:start+len(before)]==before, 'overlapping or mismatched projection: '+row['role'])
            result.extend((source[at:start],row['after']));at=start+len(before)
        result.append(source[at:]);return b''.join(result)

    body=apply(rows)
    unlink.check_entry_context(body,family=family,variant=unlink_variant)
    _, proof=unlink.transform_source(source,family=family,variant=unlink_variant)
    entry=list(unlink.source_edits(source,family=family,variant=unlink_variant))
    if entry_names is not None:
        require(unlink_variant=='return-short' and tuple(entry_names) in
                (('a','b'),('b','a'),('a','c'),('c','a'),('v','w'),('x','y'),('y','z'),('u','v')),
                'entry aliases require one explicit finite short-return pair')
        main=body[body.index(b'main(void){'):]
        occupied=set(re.findall(rb'[A-Za-z_][A-Za-z_0-9]*',main))
        occupied.update(re.findall(rb'#define\s+([A-Za-z_][A-Za-z_0-9]*)',body))
        require(not any(name.encode() in occupied for name in entry_names), 'entry alias shadows a consumed name or macro')
        entry[0]={**entry[0],'after':entry[0]['after'].replace(b'z0',entry_names[0].encode()).replace(b'z1',entry_names[1].encode())}
    spans('entry-unlink',proof,entry)
    rows.sort(key=lambda r:r['begin'])
    candidate=apply(rows)
    at=target=0; gaps=[]; edits=[]
    for row in rows:
        start,before,after=row['begin'],row['before'],row['after']
        gap=source[at:start]
        gaps.append(pin(gap));target+=len(gap)
        edits.append(dict(stage=row['stage'],role=row['role'],begin=start,target=target,
                          before=before.decode(),after=after.decode()))
        at=start+len(before);target+=len(after)
    gaps.append(pin(source[at:]))
    proof=dict(schema='rove4k-next-composed-v1',family=family,input=pin(source),output=pin(candidate),
               policy=dict(per_go=per_go,prefix=prefix,dense=dense,tt=tt,qs=qs,occupancy=occupancy,unlink_variant=unlink_variant,entry_names=entry_names),
               stages=stages,edits=edits,protected_gaps=gaps,full_inverse=True)
    require(restore_source(candidate,proof)==source, 'composed inverse differs')
    return candidate,proof


def restore_source(candidate,proof):
    require(proof.get('schema')=='rove4k-next-composed-v1' and pin(candidate)==proof['output'], 'composed output differs')
    result=[];cursor=0;gaps=[]
    for row in proof['edits']:
        at,after=row['target'],row['after'].encode()
        require(at>=cursor and candidate[at:at+len(after)]==after, 'composed inverse span differs')
        gap=candidate[cursor:at];gaps.append(pin(gap));result.extend((gap,row['before'].encode()));cursor=at+len(after)
    gaps.append(pin(candidate[cursor:]));result.append(candidate[cursor:]);source=b''.join(result)
    require(pin(source)==proof['input'] and gaps==proof['protected_gaps'], 'composed inverse gaps differ')
    module('self_unlink').transform_source(source,family=proof['family'])
    return source
