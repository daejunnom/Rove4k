"""Full F2: directly select the deeper result from exactly two workers.

The sole product caller holds qj after the last --qk reaches zero. All worker
results are then stable. Strict greater-than retains worker0 on a tie and
the following bestmove/fallback logic is unchanged. This fixed2 stage follows
shipping_names; F8 retains the pre-name source and its own resource loop.
No files, compiler, codec, report or engine are read or executed here.
"""
import hashlib

INPUT=(8538,'400ad454b0e3108814636bab4060f224ae4b2d28cdc7929c8c98590adb46c59d')
OUTPUT=(8513,'9f2804e0bc9467ee5f831cf7e2f90bb27f54117a50228ffb3ad1681d4873a272')
START=6296
OLD=b'zc*w=qr;for(S i=1;i<2;i++)if(qr[i].b>w->b)w=qr+i;'
NEW=b'zc*w=qr+(qr[1].b>qr->b);'
GAPS=((6296,'a3af680a8c67b427efe30f184c5f41de81f8ac897d868745d27ac18b8e999b0d'),
      (2193,'121c73407c81829eb4179e0326f086f126928ba521e32d5490d982f07bf57ed2'))


def _pin(data):return len(data),hashlib.sha256(data).hexdigest()


def transform_source(source,family='F'):
    """Replay one exact fixed2 selector edit after full-F names only."""
    if family!='F' or type(source) is not bytes or _pin(source)!=INPUT:
        raise ValueError('fixed full-F2 selector input differs')
    end=START+len(OLD)
    if source[START:end]!=OLD:
        raise ValueError('fixed full-F2 selector literal/offset differs')
    gaps=(source[:START],source[end:])
    candidate=gaps[0]+NEW+gaps[1]
    newgaps=(candidate[:START],candidate[START+len(NEW):])
    inverse=candidate[:START]+OLD+candidate[START+len(NEW):]
    if (_pin(candidate)!=OUTPUT or candidate[START:START+len(NEW)]!=NEW
            or inverse!=source or newgaps!=gaps or tuple(map(_pin,gaps))!=GAPS):
        raise ValueError('fixed full-F2 selector output/inverse/two gaps differ')
    return candidate,{
        'family':'F','stage':'fixed-two-worker-completion-selector-after-names',
        'input_bytes':INPUT[0],'input_sha256':INPUT[1],
        'output_bytes':OUTPUT[0],'output_sha256':OUTPUT[1],
        'raw_delta':-25,'edits':1,'full_inverse':True,'all_gaps_equal':True,
        'gap_count':2,'protected_gaps':GAPS,'fixed_workers':2,
        'strict_greater_depth_and_first_worker_tie_preserved':True,
        'completion_mutex_and_lazy_fallback_bytes_protected':True,
        'pre_names_F8_input_and_own_resource_specialization_preserved':True,
        'external_reads':0,'compiler_codec_engine_executed_by_transform':0}
