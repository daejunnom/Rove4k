"""One exact A retry region; protected source complement is byte-identical."""
import hashlib
from pathlib import Path

BASELINE = '71f9ff6ce1b7f555ad85c3bf49766381c0627315da94acf0c49eeee7bee4a734'
OLD = b'''        if(legal==1||depth<=0)score=-search(w,&q,depth-1,-beta,-alpha,ply+1,next,0);
        else{
            COUNT(w,pvs);
            int reduce=depth>=4&&legal>=4&&!tactical&&!check&&!attacked(&q,q.k[q.s<0],-q.s);
            if(reduce){COUNT(w,corr_uses);reduce=evaluation+w->correction[p->h&1023]/64<alpha+100;}
            score=-search(w,&q,depth-1-reduce,-alpha-1,-alpha,ply+1,next,0);
            if(reduce&&score>alpha)score=-search(w,&q,depth-1,-alpha-1,-alpha,ply+1,next,0);
            if(score>alpha&&score<beta)score=-search(w,&q,depth-1,-beta,-alpha,ply+1,next,0);
        }
'''


def sha(data):
    return hashlib.sha256(data).hexdigest()


def transform(source):
    if sha(source) != BASELINE or source.count(OLD) != 1 or b'\r' in source:
        raise ValueError('exact LF A readable baseline/region required')
    replacement = Path(__file__).with_name('retry.c.in').read_bytes()
    if b'\r' in replacement or not replacement.endswith(b'\n'):
        raise ValueError('retry template must be LF')
    before, after = source.split(OLD)
    candidate = before + replacement + after
    if candidate[:len(before)] != before or candidate[len(before)+len(replacement):] != after:
        raise ValueError('protected complement changed')
    return candidate, {'baseline_readable_sha256': BASELINE, 'candidate_readable_sha256': sha(candidate),
        'old_region_bytes': len(OLD), 'new_region_bytes': len(replacement),
        'protected_complement_bytes': len(before)+len(after), 'protected_complement_sha256': sha(before+after),
        'protected_complement_identical': True, 'scope': 'four recursive child call sites to one retry-state loop',
        'native_identity_expected_to_change': True, 'candidate_runtime_qualified': False}
