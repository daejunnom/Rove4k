"""Full-only depth and repetition representation after result-stream replay.

Production think starts depth1..126. Saturated QS depth obeys new=max(old,0):
its zero horizon, check evasions, learner gates and positive bonus stay exact.
Direct negative-depth calls to the new private U are outside this contract.
Repetition distance2,4,... <=half and <length reads the original same indices
in the same order; length1..4223 stays inside the4224-key worker array.
Full-key coherent bound TT, MTD windows, learners, witness, rules and resources
are retained. Canonical DEV and selected optional policies bypass this stage.
This exact pure replay reads no file, process, receipt or experimental input.
"""
import hashlib

INPUT=(8821,'00c48b5c6d74a45d68fe8280d45648e4405763c6c5742d8e11ed9736c71beb9c')
OUTPUT=(8793,'6d1f0c57ac56c4e4d25022b58716c94704a5ce4ed4a110e3ca7d281b1d3b21d4')
EDITS=((4285, 4285, b't=0,u=w->g-1-p->a;if(u<0)u=0;for(int i=w->g-3;i>=u;i-=2)t+=w->f[i]==p->h;', b't=0;for(int i=2;i<=p->a&&i<w->g;i+=2)t+=w->f[w->g-1-i]==p->h;'), (4594, 4582, b'(a>0?a:0)', b'a'), (4632, 4612, b'a<=0', b'!a'), (5091, 5069, b'H=-U(w,&q,a-1,1-d,f+1,Q,0);', b'H=-U(w,&q,a-!!a,1-d,f+1,Q,0);'), (5397, 5377, b'(a>0?a:0)', b'a'))
COMPLEMENT=(8699,'c9f6bba6db352194769efa820fd32a117bc1119f699d480f58738d366e683fcf')

def _pin(data):
    return len(data),hashlib.sha256(data).hexdigest()

def transform_source(source):
    if type(source) is not bytes or _pin(source)!=INPUT:
        raise ValueError('full-F depth/repetition input differs')
    parts=[];gaps=[];cursor=written=0
    for start,target,old,new in EDITS:
        gap=source[cursor:start]
        if start<cursor or source[start:start+len(old)]!=old or written+len(gap)!=target:
            raise ValueError('full-F depth/repetition literal or offset differs')
        parts.extend((gap,new));gaps.append(gap)
        cursor=start+len(old);written=target+len(new)
    parts.append(source[cursor:]);gaps.append(source[cursor:])
    result=b''.join(parts);inverse=[];new_gaps=[];cursor=0
    for start,target,old,new in EDITS:
        gap=result[cursor:target]
        if result[target:target+len(new)]!=new:
            raise ValueError('full-F depth/repetition inverse literal differs')
        inverse.extend((gap,old));new_gaps.append(gap);cursor=target+len(new)
    inverse.append(result[cursor:]);new_gaps.append(result[cursor:])
    if (_pin(result)!=OUTPUT or b''.join(inverse)!=source or gaps!=new_gaps
            or _pin(b''.join(gaps))!=COMPLEMENT):
        raise ValueError('full-F depth/repetition output, inverse or complement differs')
    return result,{
        'family':'F','policy':'full','stage':'depth-saturation-and-repetition-distance',
        'input_bytes':INPUT[0],'input_sha256':INPUT[1],
        'output_bytes':OUTPUT[0],'output_sha256':OUTPUT[1],
        'raw_delta':-28,'fixed_edits':5,'exact_inverse':True,'every_gap_equal':True,
        'complement_bytes':COMPLEMENT[0],'complement_sha256':COMPLEMENT[1],
        'depth_relation':'new=max(old,0), production root1..126; private negative input not admitted',
        'repetition':'same key order by old_index=length-1-distance',
        'full_rules_TT_MTD_learners_witness_resources_retained':True,
        'external_reads':0,'compiler_codec_engine_executed_by_transform':0,
    }
