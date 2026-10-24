"""Pure final A shipping replay: history length is job length plus caller ply.

The fixed production pool keeps qh immutable through each think. Root ply0
starts at qh and every recursive call advances one ply. Exact source pins
admit only the reviewed after-clock domain; canonical/DEV bypass is owned by
the builder. Worker layout/native identity change; raw Worker bytes are not
an equality claim. No file, process, codec, AST, artifact or network is read.
"""
import hashlib

BEFORE=(9040,'624ad8a28a9d555fda37efa82b468fce09f98d4c5b86b20739ee2e6f589ff5a8')
AFTER=(9011,'4c9e83760ad39668239be2b6f8bcd8dd76f24d64bf8660ec2a95f7a4139c55ea')
COMPLEMENT=(8964,'ce18065a5fbdd381241d7c4752dab8edf0f5589bbb7e223244dc4f99b094f572')
EDITS=(
    (597,b'int at;',b''),
    (4246,b'x=w->at-1-p->aI',b'x=qh+d-1-p->aI'),
    (4273,b'for(int i=w->at-3;',b'for(int i=qh+d-3;'),
    (5187,b'w->aA[w->at++]=q.h;',b'w->aA[qh+d]=q.h;'),
    (5456,b'--w->at;',b''),
    (5997,b'w->at=qh;',b''),
)

def _pin(raw):
    return len(raw),hashlib.sha256(raw).hexdigest()

def _need(condition,message):
    if not condition:raise ValueError(message)

def transform_source(source):
    _need(type(source) is bytes and _pin(source)==BEFORE,'fixed after-clock A shipping source required')
    parts=[];gaps=[];rows=[];cursor=target=0
    for offset,old,new in EDITS:
        _need(offset>=cursor and source[offset:offset+len(old)]==old and source.count(old)==1,
              'history-depth sole fixed literal or span differs')
        gap=source[cursor:offset];gaps.append(gap);parts.extend((gap,new));target+=len(gap)
        rows.append({'offset':offset,'target':target,'old_bytes':len(old),'new_bytes':len(new)})
        target+=len(new);cursor=offset+len(old)
    gaps.append(source[cursor:]);parts.append(source[cursor:]);candidate=b''.join(parts)
    _need(_pin(candidate)==AFTER,'fixed derived-history-length candidate differs')
    inverse=[];candidate_gaps=[];cursor=0
    for (offset,old,new),row in zip(EDITS,rows):
        start=row['target'];gap=candidate[cursor:start]
        _need(candidate[start:start+len(new)]==new,'history-depth candidate literal differs')
        candidate_gaps.append(gap);inverse.extend((gap,old));cursor=start+len(new)
    candidate_gaps.append(candidate[cursor:]);inverse.append(candidate[cursor:])
    _need(b''.join(inverse)==source and candidate_gaps==gaps,'history-depth inverse or protected gap differs')
    complement=b''.join(gaps)
    _need(_pin(complement)==COMPLEMENT,'history-depth protected complement differs')
    return candidate,{'stage':'A-only fixed shipping after clock presence','input_bytes':BEFORE[0],
        'input_sha256':BEFORE[1],'output_bytes':AFTER[0],'output_sha256':AFTER[1],
        'edits':rows,'raw_source_delta':-29,'exact_inverse':True,'each_protected_gap_exact':True,
        'complement_bytes':COMPLEMENT[0],'complement_sha256':COMPLEMENT[1],
        'entry_relation':'old cursor == immutable job length qh + caller ply d',
        'same_history_indices_and_child_key_write':True,'new_recursive_arguments':0,
        'removed_private_cursor_field':True,'Worker_layout_changed':True,'old_native_equality_claimed':False,
        'canonical_readable_unchanged':True,'DEV_bypasses_stage':True,
        'runtime_retry_branch_coverage':'unmeasured; source four-call induction is separate'}
