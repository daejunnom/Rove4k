"""Exact late full-F terminal legal-loop sharing; DEV bypass belongs to the caller.

Only the frozen integer9050 input is admitted. Terminal TT score lookup is
suppressed before the shared ordered legal loop. This changes terminal work
order and timing; it preserves terminal result/stop/publication semantics.
No external source, receipt, parser or experimental producer is read here.
"""
import hashlib

INPUT=(9050, 'fe854d32f8fe7c78f08512f40dbc4e99a74666d164528e9d9cb54f72e0dfee49')
OUTPUT=(8998, '94593b739c14afc27bbec0db7d9027cef65e4c7ee1b358f105b1b08f1072ebd2')
EDITS=(('encode-draw-ply-state', 4475, 4475, b'o|=t>=2||af(p);', b'o|=t>=2||af(p);o|=(f==128-1)*2;'),
 ('remove-separate-terminal-legal-scan',
  4551,
  4567,
  b'if(o||f==128-1){za q;for(int i=0;i<A;i++)if(h(p,x[i],&q)){if(!o){atomic_store(&qp,1);}return 0;}return n'
  b'?-MATE+f:0;}',
  b''),
 ('skip-terminal-TT-read-and-bound', 4699, 4599, b'F=V(E,0);', b'F=o?0:V(E,0);'),
 ('terminal-return-at-shared-legal-make',
  5137,
  5041,
  b'if(!h(p,m,&q))continue;++B;',
  b'if(!h(p,m,&q))continue;if(o){if(o==2)atomic_store(&qp,1);return 0;}++B;'))
GAPS=((4475, '041994f3d0faec1190bf966461aba19da2e2a2156ff48f7c04546f3c11b43633'), (61, 'd3126120b2c56bd096e755cf6539fd98fac22c5f6485df82730968446c8b2874'), (32, '99760d128e61cba21cb3c4771c7092949141c66f726e0dcb69dd2245d9016b9c'), (429, '46978bdca6d5d0ac461f3da0f8ccc307b754ed41cbdf6f6e7e63f04565cbc794'), (3886, '86a9f841428829564de6fccf5b94a80ae115f138107c98dc3d09e4c044f5b0b7'))
COMPLEMENT=(8883, '82a34de491f8fc31cb3afde9722b2e0a9b5b4fd8ae5d6541e4c66b92f498d64e')
OLD_U=(4283, 5607, 'b43f0faee173d4b4e8eda039d700f4e1edb3189fd245dd83e724fe27059587f8')
NEW_U=(4283, 5555, '7808d241cd2f039d4f286aec6eec7769d82f842aaa05e790f84dc6034520ee26')
QUALIFIED_COMPONENT_RECEIPT_SHA256="3d3815c6dd155871b8ae2142b4aa5c6828f9073e795e4cb8b9c619dfb3320bf8"

def _pin(data):
    return len(data), hashlib.sha256(data).hexdigest()


def transform_source(source):
    """Project exactly one fixed full-F shipping source and return audit metadata."""
    if type(source) is not bytes or _pin(source) != INPUT:
        raise ValueError('full-F terminal input differs from fixed integer9050 source')
    pieces=[]; old_gaps=[]; cursor=0; output_cursor=0
    for index,(role,start,new_start,old,new) in enumerate(EDITS):
        gap=source[cursor:start]
        if (_pin(gap) != GAPS[index] or source[start:start+len(old)] != old
                or source.count(old) != 1 or output_cursor+len(gap) != new_start):
            raise ValueError('full-F terminal literal/gap boundary differs: '+role)
        pieces.extend((gap,new));old_gaps.append(gap)
        cursor=start+len(old);output_cursor=new_start+len(new)
    gap=source[cursor:]
    if _pin(gap) != GAPS[-1]:
        raise ValueError('full-F terminal final complement differs')
    pieces.append(gap);old_gaps.append(gap);candidate=b''.join(pieces)
    if _pin(candidate) != OUTPUT:
        raise ValueError('full-F terminal output differs from actual composed candidate')
    inverse=[];new_gaps=[];cursor=0
    for role,start,new_start,old,new in EDITS:
        gap=candidate[cursor:new_start]
        if candidate[new_start:new_start+len(new)] != new:
            raise ValueError('full-F terminal positional inverse differs: '+role)
        inverse.extend((gap,old));new_gaps.append(gap);cursor=new_start+len(new)
    inverse.append(candidate[cursor:]);new_gaps.append(candidate[cursor:])
    old_remainder=b''.join(old_gaps);new_remainder=b''.join(new_gaps)
    if (b''.join(inverse) != source or old_remainder != new_remainder
            or _pin(old_remainder) != COMPLEMENT):
        raise ValueError('full-F terminal inverse or complement mismatch')
    if (hashlib.sha256(source[OLD_U[0]:OLD_U[1]]).hexdigest() != OLD_U[2]
            or hashlib.sha256(candidate[NEW_U[0]:NEW_U[1]]).hexdigest() != NEW_U[2]):
        raise ValueError('full-F old/new actual search body differs')
    metadata={
        'family':'F','policy':'full','stage':'late-terminal-shared-legal-loop',
        'input_bytes':INPUT[0],'input_sha256':INPUT[1],
        'output_bytes':OUTPUT[0],'output_sha256':OUTPUT[1],
        'raw_delta':OUTPUT[0]-INPUT[0],'literal_spans':len(EDITS),
        'exact_inverse':True,'complement_bytes':COMPLEMENT[0],
        'complement_sha256':COMPLEMENT[1],
        'actual_old_U_sha256':OLD_U[2],'actual_new_U_sha256':NEW_U[2],
        'actual_component_function_proof_receipt_sha256':QUALIFIED_COMPONENT_RECEIPT_SHA256,
        'terminal_TT_score_lookup_suppressed':True,
        'terminal_work_order_and_timing_changed':True,
        'external_reads':0,'compiler_codec_engine_executed_by_transform':0,
    }
    return candidate,metadata
