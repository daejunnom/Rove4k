"""One exact A castle emission region; explicit private order/query policy change."""
import hashlib
from pathlib import Path

BASELINE = '71f9ff6ce1b7f555ad85c3bf49766381c0627315da94acf0c49eeee7bee4a734'
OLD = b'''                if(moves)add(moves,&n,from,to,a==1);
                if(target||a<3||a==6)break;
            }
        }
        if(moves&&a==6){
            int home=s>0?4:116,shift=s>0?0:2;
            if(from==home&&!attacked(p,home,-s)){
                if((p->c&(1<<shift))&&!p->b[home+1]&&!p->b[home+2]&&!attacked(p,home+1,-s))add(moves,&n,from,home+2,0);
                if((p->c&(2<<shift))&&!p->b[home-1]&&!p->b[home-2]&&!p->b[home-3]&&!attacked(p,home-1,-s))add(moves,&n,from,home-2,0);
                }
        }
'''


def sha(data):
    return hashlib.sha256(data).hexdigest()


def transform(source):
    if sha(source) != BASELINE or source.count(OLD) != 1 or b'\r' in source:
        raise ValueError('exact LF A readable baseline/region required')
    replacement = Path(__file__).with_name('castle.c.in').read_bytes()
    if b'\r' in replacement or len(OLD) != 525 or len(replacement) != 427:
        raise ValueError('sole fixed castle fragment length/LF changed')
    before, after = source.split(OLD)
    candidate = before + replacement + after
    if candidate[:len(before)] != before or candidate[len(before)+len(replacement):] != after:
        raise ValueError('protected complement changed')
    return candidate, {'baseline_readable_sha256': BASELINE, 'candidate_readable_sha256': sha(candidate),
        'old_region_bytes': len(OLD), 'new_region_bytes': len(replacement),
        'protected_complement_bytes': len(before)+len(after), 'protected_complement_sha256': sha(before+after),
        'protected_complement_identical': True, 'scope': 'share castle emission with ordinary king horizontal geometry',
        'private_policy_changes': ['king generated move order, hence possible tied search order',
                                   'origin attack queries may repeat for the two eligible castle paths'],
        'full_behavior_preservation_claim': False, 'exact_legal_child_and_rule_preservation_pending_runtime': True,
        'native_identity_expected_to_change': True, 'candidate_runtime_qualified': False}
