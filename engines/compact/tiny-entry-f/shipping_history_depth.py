"""Derive the full-F private history cursor from published base plus ply.

Each production U entry/return has old length=immutable qh+recursion ply f.
The sole child push precedes f+1; its old pop precedes stop/result/learning.
All root MTD probes re-enter with ply0. QS depth saturation does not stop ply.
qh1..4096, entry ply0..127 and the unchanged4224-key array retain capacity.
Old Worker g is removed; learner offsets/native identity can change. DEV and
actual optional policies bypass this fixed stage; separate full references
use it. The function reads no files and starts no compiler/codec/engine.
"""
import hashlib

INPUT=(8587,'a1ebe0f07ddf1889a9caa17f6903a5f2ecbc62ac3249d7006176a8aa5ce736cd')
OUTPUT=(8566,'c7da40086c5f6d0616b21a990e1296c405d6486808eb34b5d2de3c486f5e4c5e')
COMPLEMENT=(8548,'cd2e31eb3d2c95ecdc59973fd44d9c6c703627cba14091ce58ffccea5257a5cf')
EDITS=((518, 518, b'S g;', b''), (4149, 4145, b'i<w->g', b'i<qh+f'), (4169, 4165, b'w->g-1-i', b'qh+f-1-i'), (4876, 4872, b'w->g++', b'qh+f'), (4917, 4911, b'--w->g;', b''), (5283, 5270, b'w->g=qh;', b''))

def _pin(data):return len(data),hashlib.sha256(data).hexdigest()

def transform_source(source,family='F'):
    if family!='F' or type(source) is not bytes or _pin(source)!=INPUT:
        raise ValueError('fixed full-F history-depth input differs')
    parts=[];gaps=[];cursor=written=0
    for start,target,old,new in EDITS:
        gap=source[cursor:start]
        if start<cursor or source[start:start+len(old)]!=old or written+len(gap)!=target:
            raise ValueError('fixed history-depth edit literal/offset differs')
        parts.extend((gap,new));gaps.append(gap);cursor=start+len(old);written=target+len(new)
    parts.append(source[cursor:]);gaps.append(source[cursor:]);candidate=b''.join(parts)
    inverse=[];newgaps=[];cursor=previous_old=0
    for start,target,old,new in EDITS:
        gap=candidate[cursor:target]
        if gap!=source[previous_old:start] or candidate[target:target+len(new)]!=new:
            raise ValueError('fixed history-depth inverse literal/gap differs')
        inverse.extend((gap,old));newgaps.append(gap);cursor=target+len(new);previous_old=start+len(old)
    inverse.append(candidate[cursor:]);newgaps.append(candidate[cursor:])
    if _pin(candidate)!=OUTPUT or b''.join(inverse)!=source or gaps!=newgaps or _pin(b''.join(gaps))!=COMPLEMENT:
        raise ValueError('fixed history-depth output/inverse/complement differs')
    return candidate,{'family':'F','stage':'published-history-base-plus-recursion-ply','input_bytes':INPUT[0],'input_sha256':INPUT[1],
        'output_bytes':OUTPUT[0],'output_sha256':OUTPUT[1],'raw_delta':-21,'edits':6,'full_inverse':True,'all_gaps_equal':True,
        'gap_count':7,'complement_bytes':COMPLEMENT[0],'complement_sha256':COMPLEMENT[1],
        'production_relation':'old cursor=immutable qh+recursion ply at every U entry/return; each MTD root ply0',
        'public_qh_range':[1,4096],'entry_ply_range':[0,127],'key_capacity':4224,'Worker_layout_and_native_identity_unchanged':False,
        'external_reads':0,'compiler_codec_engine_executed_by_transform':0}
