"""Reuse A's existing successful-child piece index at a quiet cutoff.

The positive-depth cutoff excludes captures and every promotion. Successful
nonpromotion make puts the same parent piece at the destination, including
castling, so existing R and the old parent expression identify the same
continuation cell. Canonical C and DEV bypass this fixed shipping-only stage.
This helper consumes no experiment, report, AST or external artifact.
"""
import hashlib

INPUT_BYTES=9265
INPUT_SHA256='06ca0bc2871c2b1a8ce1eeccc24d65680bbc874066498db6e0c295af89003a46'
OUTPUT_BYTES=9256
OUTPUT_SHA256='c5e2d2994ea12df6df8b3152c2c89a00f787ee03ae09b1d546c9082145b5c56d'
OLD=b'w->an[f][s(p->b[o])]'
NEW=b'w->an[f][R]'
COMPLEMENT_SHA256='5d518118caaab27f085c1597afffc5894cc8226cb1056424fa342f9441362e47'


def sha(raw):return hashlib.sha256(raw).hexdigest()


def transform_source(source):
    if type(source) is not bytes or len(source)!=INPUT_BYTES or sha(source)!=INPUT_SHA256:
        raise ValueError('exact post-globalnames A shipping source required')
    context=b'if(C>0&&!Q){int S=C*C;O(&w->zC[o][P],S);O(&'+OLD+b',S);}'
    if source.count(OLD)!=1 or source.count(context)!=1 or source.count(b'int o=FROM(m),P=TO(m),Q=(m&8)||PROMO(m),R=s(q.b[P]);')!=1:
        raise ValueError('actual child-index and quiet-cutoff context changed')
    at=source.index(OLD);result=source[:at]+NEW+source[at+len(OLD):]
    complement=source[:at]+source[at+len(OLD):]
    if result[:at]+OLD+result[at+len(NEW):]!=source or sha(complement)!=COMPLEMENT_SHA256:
        raise ValueError('exact inverse or protected complement changed')
    if len(result)!=OUTPUT_BYTES or sha(result)!=OUTPUT_SHA256:
        raise ValueError('fixed continuation-slot output changed')
    return result,{'stage':'shipping-after-globalnames','regions':1,'old_bytes':len(OLD),'new_bytes':len(NEW),'raw_source_delta':-9,
                   'exact_inverse':True,'protected_complement_bytes':len(complement),'protected_complement_sha256':sha(complement),
                   'same_continuation_slot_source_identity':True,'quiet_promotions_excluded_by_PROMO':True,'castling_keeps_king_identity':True,
                   'canonical_readable_unchanged':True,'DEV_bypasses_stage':True,'new_state_signature_helper_or_learning_policy':False}
