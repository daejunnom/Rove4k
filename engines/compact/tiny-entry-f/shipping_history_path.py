"""Full F: share the immutable job prefix and store only private path keys.

The old key at qh+ply-1-distance is private iff distance<ply; equality
selects qg[qh-1]. Parents write path[ply] before child ply+1; cap127
prevents a child write after parent126. qg/qh are published before GO
and remain immutable through all workers' complete think/MTD/correction
and result return, until the main thread's drain permits position writes.
Every original repetition comparison, including half>=100, is retained.
Worker layout/native identity and memory-access timing may change. DEV
and actual reduced policies bypass this fixed stage; full references use it.
No file reads, compiler, codec or engine execution occurs in this helper.
"""
import hashlib

INPUT=(8559,'65ca88c60d29f87249aac7e43905af1420e868065701e93fb7bdacbbc560f4c7')
OUTPUT=(8538,'47353a15426e508cf2975d0bcba529052aac791b9461f952a88084b5e0e8d5a0')
COMPLEMENT=(8490,'7806bbec613a6c894976a254f58dea65e0f348fc5042f6ada2e1ad612678ca60')
EDITS=((506,506,b'f[4096+128]',b'f[128]'),
       (4160,4155,b'w->f[qh+f-1-i]',b'(i<f?w->f[f-1-i]:qg[qh+f-1-i])'),
       (4876,4887,b'w->f[qh+f]=q.h;',b'w->f[f]=q.h;'),
       (5279,5287,b'memcpy(w->f,qg,qh*sizeof(W));',b''))

def _pin(data):return len(data),hashlib.sha256(data).hexdigest()

def transform_source(source,family='F'):
    """Replay four exact edits on the qualified lazy+QS full F source only."""
    if family!='F' or type(source) is not bytes or _pin(source)!=INPUT:
        raise ValueError('fixed full-F history-path input differs')
    parts=[];gaps=[];cursor=written=0
    for start,target,old,new in EDITS:
        gap=source[cursor:start]
        if start<cursor or source[start:start+len(old)]!=old or written+len(gap)!=target:
            raise ValueError('fixed history-path edit literal/offset differs')
        parts.extend((gap,new));gaps.append(gap);cursor=start+len(old);written=target+len(new)
    parts.append(source[cursor:]);gaps.append(source[cursor:]);candidate=b''.join(parts)
    inverse=[];newgaps=[];cursor=previous_old=0
    for start,target,old,new in EDITS:
        gap=candidate[cursor:target]
        if gap!=source[previous_old:start] or candidate[target:target+len(new)]!=new:
            raise ValueError('fixed history-path inverse literal/gap differs')
        inverse.extend((gap,old));newgaps.append(gap);cursor=target+len(new);previous_old=start+len(old)
    inverse.append(candidate[cursor:]);newgaps.append(candidate[cursor:])
    if (_pin(candidate)!=OUTPUT or b''.join(inverse)!=source or gaps!=newgaps
            or len(gaps)!=5 or _pin(b''.join(gaps))!=COMPLEMENT):
        raise ValueError('fixed history-path output/inverse/five gaps/complement differs')
    return candidate,{
        'family':'F','stage':'private-path-with-immutable-global-job-prefix-after-lazy-QS',
        'input_bytes':INPUT[0],'input_sha256':INPUT[1],
        'output_bytes':OUTPUT[0],'output_sha256':OUTPUT[1],
        'raw_delta':-21,'edits':4,'full_inverse':True,'all_gaps_equal':True,
        'gap_count':5,'protected_gaps':[_pin(gap) for gap in gaps],
        'complement_bytes':COMPLEMENT[0],'complement_sha256':COMPLEMENT[1],
        'logical_mapping':'old.f[qh+j]=new.f[j]; root prefix read directly from immutable qg',
        'query_boundary':'distance<ply selects private path; distance==ply selects qg[qh-1]',
        'public_qh_range':[1,4096],'entry_ply_range':[0,127],
        'private_key_capacity':128,'maximum_parent_write':126,
        'all_half_ge100_comparisons_and_terminal_TT_learner_sites_preserved':True,
        'global_publication_and_whole_job_drain_preserved':True,
        'Worker_layout_and_native_identity_unchanged':False,
        'RAM_performance_manycore_claimed':False,
        'external_reads':0,'compiler_codec_engine_executed_by_transform':0}
