"""Exact late A terminal legal-loop sharing; canonical/DEV bypass it.

Terminal scoring/sorting may select a different private legal child and do
additional work. Terminal TT cutoff remains suppressed before the shared
make epilogue. Source contracts and actual-source qualification are separate
from runtime timing/strength claims. No external artifact is read here.
"""
import hashlib
INPUT=(8965,'6230471043c6259016908792bc4b8ad58cf089503e7195ce8a4b6cc6d9886533')
OUTPUT=(8914,'597d01d9cece4762880cc4a4c8c3a5329125ca76cb4b92eba6c31da3231c683a')
EDITS=((4310, 4310, b't|=u>=2||ap(p);', b't|=u>=2||ap(p);t|=(d==PLY-1)*2;', 'draw-plus-cap-state'), (4390, 4406, b'if(t||d==PLY-1){E q;for(int i=0;i<z;i++)if(v(p,B[i],&q)){if(!t){atomic_store(&qp,1);}return 0;}return n?-MATE+d:0;}', b'', 'remove-terminal-only-legal-scan'), (4538, 4439, b'U=V(I,0);', b'U=t?0:V(I,0);', 'skip-terminal-TT-probe'), (5073, 4978, b'if(!v(p,m,&q))continue;++A;', b'if(!v(p,m,&q))continue;if(t){if(t==2)atomic_store(&qp,1);return 0;}++A;', 'shared-terminal-legal-epilogue'))
GAPS=((0, 0, 4310, '5240760fef94adebf50bd0a02c6bb6b21c1742cfa70d129643198f2f7f0006b2'), (4325, 4341, 65, '011a714a8c1b3826d6b8dabb929d1b860fc85172c2d9eef82f1d1263a24cdc6d'), (4505, 4406, 33, '88c6eac6bf9db60e1dc016eb72ecfcf3152b81f35482d4b676defd745b7a67f4'), (4547, 4452, 526, '19473b712cf018f4981357f2a808690c7111b8536e76c1d7e010bf9f8cf6aa5b'), (5100, 5049, 3865, 'df298cc49a48b91f6872ea563b5fd9eeaaac5549e26a12197e6764bfe8bc6faa'))
def _sha(raw):return hashlib.sha256(raw).hexdigest()
def transform_source(source):
    if type(source) is not bytes or (len(source),_sha(source))!=INPUT:
        raise ValueError('exact A shared-worker shipping source required')
    pieces=[];cursor=written=0
    for start,target,old,new,role in EDITS:
        if start<cursor or source[start:start+len(old)]!=old or source.count(old)!=1:
            raise ValueError('A terminal source role differs: '+role)
        gap=source[cursor:start]
        if written+len(gap)!=target:raise ValueError('A terminal target differs')
        pieces.extend((gap,new));cursor=start+len(old);written=target+len(new)
    pieces.append(source[cursor:]);result=b''.join(pieces)
    if (len(result),_sha(result))!=OUTPUT:raise ValueError('A terminal output differs')
    for old_at,new_at,length,digest in GAPS:
        old=source[old_at:old_at+length];new=result[new_at:new_at+length]
        if old!=new or _sha(old)!=digest:raise ValueError('A terminal complement differs')
    restored=result
    for start,target,old,new,role in reversed(EDITS):
        if restored[target:target+len(new)]!=new:raise ValueError('A terminal inverse span differs')
        restored=restored[:target]+old+restored[target+len(new):]
    if restored!=source:raise ValueError('A terminal full inverse differs')
    return result,{'stage':'A-late-terminal-shared-legal-loop','input_bytes':INPUT[0],
        'input_sha256':INPUT[1],'output_bytes':OUTPUT[0],'output_sha256':OUTPUT[1],
        'literal_regions':4,'protected_gaps':5,'full_inverse':True,
        'terminal_TT_probe_suppressed':True,'terminal_early_return_before_state_writes':True,
        'terminal_work_order_and_timing_changed':True,'native_identity_changed':True,
        'canonical_DEV_unchanged':True,'external_reads':0}
