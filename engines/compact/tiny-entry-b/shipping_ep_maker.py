"""Pure fixed B EP normalization through the actual legal maker.

The preceding B stages and int alias remain the exact entry guard. Only the
owned EP normalizer and its maker prototype change. B mailbox/bitboard/king
coherence is required: this is not the mailbox-only scratch used elsewhere.
The inner maker's private hash/context/half/rights are discarded; only nonzero
legality is consumed. Legal EP returns 101. Actual production C input has half0
after a double push; the inner EP sets e=-1, so its nested C returns immediately.
No time/atomic/TT/learner callback is introduced. Extra work/stack/timing can
differ; native equality and timed node/result equivalence are not claimed.
"""
import hashlib

INPUT_PIN = (9797, '6a29540d10a0b1e50650e197d485165851dd6d6b882faa31be3ecdc690f7ec14')
OUTPUT_PIN = (9759, '1bc4d0f68300913c8bdf4edbe55b8d79082f9ac198b53619ab5d42169e094e87')
_OFFSET = 2483
_BEFORE = b'static void C(za*p){if(p->e<0)return;for(I d=-1;d<=1;d+=2){I q=p->e-p->s*16+d;if(!(q&0x88)&&p->b[q]==p->s){za t=*p;M(&t,q,0);M(&t,p->e-p->s*16,0);M(&t,p->e,p->s);if(!c(&t,0,p->k[p->s<0],-p->s))return;}}p->e=-1;}'
_AFTER = b'I h(const za*,N,za*);static void C(za*p){if(p->e<0)return;for(I d=-1;d<=1;d+=2){I q=p->e-p->s*16+d;za t;if(!(q&0x88)&&p->b[q]==p->s&&h(p,MOVE(q,p->e,0),&t))return;}p->e=-1;}'
_GAPS = [(0, 0, 2483, 'f168eb9904bd6c0315de5d34ee901556bdf3b3a1eae22f307bf5f1d46a96a3bb'), (2694, 2656, 7103, '7f29800e1264cba93d7449815677c7c99b28b69a95905890865b941ad7eb41d0')]
METADATA = {'family': 'B', 'stage': 'late-shipping-EP-normalizer-reuses-legal-maker', 'input_bytes': 9797, 'input_sha256': '6a29540d10a0b1e50650e197d485165851dd6d6b882faa31be3ecdc690f7ec14', 'output_bytes': 9759, 'output_sha256': '1bc4d0f68300913c8bdf4edbe55b8d79082f9ac198b53619ab5d42169e094e87', 'raw_delta': -38, 'owned_regions': 1, 'protected_gaps': 2, 'full_inverse': True, 'actual_C_solecaller': 'h after completed piece updates and king safety, before state-hash/context finalization', 'domain': 'e>=0 follows a valid generated/legal double pawn push; empty EP target/victim pawn/half0; ownpawn filter', 'legal_EP_return': 101, 'nonzero_only': True, 'nested_termination': 'inner EP h sets e=-1; nested C returns immediately', 'private_observation': 'victim/own-pawn removal order changes; completed b/bb/k legality preserved; inner h/r/half/rights discarded', 'source_other_bytes_unchanged': True, 'canonical_DEV_guards_model_flags_unchanged': True, 'native_entire_equal': False, 'extra_time_atomic_TT_learner_callbacks': False, 'timed_trace_performance_stack_size_equivalence_claimed': False, 'literal_inverse_adapter_required': False}

def _pin(data):
    return len(data),hashlib.sha256(data).hexdigest()

def _guard(data,pin,label):
    if type(data) is not bytes or _pin(data)!=pin:
        raise ValueError('B EP maker '+label+' differs from fixed source')

def _gaps(before,after):
    for old_at,new_at,size,digest in _GAPS:
        if (before[old_at:old_at+size]!=after[new_at:new_at+size] or
                _pin(before[old_at:old_at+size])!=(size,digest)):
            raise ValueError('B EP maker protected gap differs')

def restore_source(source):
    _guard(source,OUTPUT_PIN,'inverse input')
    if source[_OFFSET:_OFFSET+len(_AFTER)]!=_AFTER:
        raise ValueError('B EP maker inverse region differs')
    restored=source[:_OFFSET]+_BEFORE+source[_OFFSET+len(_AFTER):]
    _guard(restored,INPUT_PIN,'inverse output')
    _gaps(restored,source)
    return restored

def transform_source(source):
    _guard(source,INPUT_PIN,'input')
    if source.count(_BEFORE)!=1 or source[_OFFSET:_OFFSET+len(_BEFORE)]!=_BEFORE:
        raise ValueError('B EP maker owned region differs')
    result=source[:_OFFSET]+_AFTER+source[_OFFSET+len(_BEFORE):]
    _guard(result,OUTPUT_PIN,'output')
    _gaps(source,result)
    if restore_source(result)!=source:
        raise ValueError('B EP maker whole inverse differs')
    return result,dict(METADATA)
