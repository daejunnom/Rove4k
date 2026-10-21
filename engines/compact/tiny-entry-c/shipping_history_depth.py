"""Pure final C shipping replay: history length is job length plus caller ply.

The fixed production pool keeps game_length immutable through each think. Root ply0
starts at game_length and every recursive call advances one ply. Exact source pins
admit only the reviewed after-search-context domain; canonical/DEV bypass is owned by
the builder. Worker layout/native identity change; raw Worker bytes are not
an equality claim. No file, process, codec, AST, artifact or network is read.
"""
import hashlib

BEFORE=(10032,'7612b83cb6a274c9b67c5217aa9c983c6271378df234b6d853e8985d97e46b12')
AFTER=(9992,'c7b8eeb2488e4ec0b9ebbdd721db311397dc5b29abc91dcb1f153046ceb2bebd')
COMPLEMENT=(9917,'1df565aa43acce0b59e5d947ec85b37c01fa0470a875a05b073f0b15bdba472c')
EDITS=((608, b'int zV;', b''), (4764, b'int z=0,A=w->zV-1-p->zL;if(A<0)A=0;for(int i=w->zV-3;i>=A;i-=2)', b'int z=0,A=game_length+n;for(int i=A-3;i>=0&&i>=A-1-p->zL;i-=2)'), (5785, b'w->zQ[w->zV++]=q.h;', b'w->zQ[A]=q.h;'), (6072, b'--w->zV;', b''), (6659, b'w->zV=game_length;', b''))
def _pin(raw):
    return len(raw),hashlib.sha256(raw).hexdigest()

def _need(condition,message):
    if not condition:raise ValueError(message)

def transform_source(source):
    _need(type(source) is bytes and _pin(source)==BEFORE,'fixed after-search-context C shipping source required')
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
    return candidate,{'stage':'C-only fixed shipping after search context','input_bytes':BEFORE[0],
        'input_sha256':BEFORE[1],'output_bytes':AFTER[0],'output_sha256':AFTER[1],
        'edits':rows,'raw_source_delta':-40,'exact_inverse':True,'each_protected_gap_exact':True,
        'complement_bytes':COMPLEMENT[0],'complement_sha256':COMPLEMENT[1],
        'entry_relation':'old cursor == immutable game_length + caller ply n',
        'same_history_indices_and_child_key_write':True,'new_recursive_arguments':0,
        'removed_private_cursor_field':True,'Worker_layout_changed':True,'old_native_equality_claimed':False,
        'canonical_readable_unchanged':True,'DEV_bypasses_stage':True,
        'runtime_retry_branch_coverage':'unmeasured; source four-call induction is separate'}
