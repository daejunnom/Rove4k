"""Carry the fixed B shipping continuation row through private search calls.

Root establishes neutral6; four successful-made-child calls supply the signed
destination slot. Same-position singular verification forwards the entry row,
including black-king slot0, with excluded TT and learning0 unchanged. The row
read moves to the caller's private initialized child; general read timing is
not an equivalence claim. Canonical/DEV and the existing positive learner keep
their bodies. No experiment, report or generated artifact is a runtime input.
"""
import hashlib
import re

INPUT_BYTES=10548
INPUT_SHA256='d91416e56e2b7716b9df2bec5db22c1f9d3f6ded5598d80741d68487ecc09bbb'
OUTPUT_BYTES=10507
OUTPUT_SHA256='8c7a110e5282e75128cf76c4b706a0c79ca5890be25a93e38f1734e9fb53089e'
READABLE_SHA256='1f879828346dfbc6023f6abfbbf1e1d2062e8e2dc0e9919aade254ba7a0a97f6'

REGIONS=(('entry-context-parameter', 4973, 4973, b'static int P(zd*w,const za*p,int a,int d,int f,int n,N previous,N*t,N u,int x)', b'static int P(zd*w,const za*p,int a,int d,int f,int n,int yb,N*t,N u,int x)'), ('same-position-singular-context-forward', 5722, 5718, b'int s=P(w,p,(a-1)/2,yx-1,yx,n,previous,0,tt,0);', b'int s=P(w,p,(a-1)/2,yx-1,yx,n,yb,0,tt,0);'), ('remove-late-previous-redecode', 5880, 5870, b'int yb=previous?J(p->b[TO(previous)]):6;', b''), ('successful-made-child-slot', 6420, 6370, b'int zJ=FROM(m),to=TO(m),yu=m&8;', b'int zJ=FROM(m),to=TO(m),yu=m&8,pi=J(q.b[to]);'), ('four-made-child-PVS-context-arguments', 6533, 6497, b'if(zU==1||a<=0)yl=-P(w,&q,z3,-f,-d,n+1,m,0,0,x);else{int yg=a>=4&&zU>=4&&!yu&&!z&&!e(&q,q.k[q.s<0],-q.s);if(yg){yg=zF+w->zx[p->h&1023]/64<d+100;}yl=-P(w,&q,z3-yg,-d-1,-d,n+1,m,0,0,x);if(yg&&yl>d)yl=-P(w,&q,z3,-d-1,-d,n+1,m,0,0,x);if(yl>d&&yl<f)yl=-P(w,&q,z3,-f,-d,n+1,m,0,0,x);}', b'if(zU==1||a<=0)yl=-P(w,&q,z3,-f,-d,n+1,pi,0,0,x);else{int yg=a>=4&&zU>=4&&!yu&&!z&&!e(&q,q.k[q.s<0],-q.s);if(yg){yg=zF+w->zx[p->h&1023]/64<d+100;}yl=-P(w,&q,z3-yg,-d-1,-d,n+1,pi,0,0,x);if(yg&&yl>d)yl=-P(w,&q,z3,-d-1,-d,n+1,pi,0,0,x);if(yl>d&&yl<f)yl=-P(w,&q,z3,-f,-d,n+1,pi,0,0,x);}'), ('quiet-learning-column-reuse', 6980, 6948, b'F(&w->zw[yb][J(p->b[zJ])],zn);', b'F(&w->zw[yb][pi],zn);'), ('root-neutral-six', 7494, 7453, b'int f=P(w,p,a,-MATE,MATE,0,0,&d,0,1);', b'int f=P(w,p,a,-MATE,MATE,0,6,&d,0,1);'))

PROTECTED_GAPS=((0, 0, 4973, '80b5839ee4f6d41357e61fa1b2b6ea05bc0b47e8111984cea190b44c958742e4'), (5051, 5047, 671, 'a5ca9c9d319683112f51dc23cf700dc4057351c014913726cfa05bf567351c96'), (5769, 5759, 111, '981a96611bee55f0aaa6265bf64dee57974d43fe231343664191f4a342cdc04e'), (5920, 5870, 500, '95fa435433575cff0a276e9fbb1d6837327f4cdcf89be0654908260f0e5af78e'), (6451, 6415, 82, 'e4e211b92c484aad74f0042f49def45242cf013989d3b32ed636e9d17f0ff647'), (6811, 6779, 169, '0a3da31b69e211549f22e0aae4f26a94d64fdf12e1c2c60a13588a885d00d4b0'), (7010, 6969, 484, '20501a36e8243d59f71d5f2be82c1923965518c063d8589447e5545966183186'), (7531, 7490, 3017, '0ad50f80ada1a2d14eb8040056735c58c3ab57f9ea9bbb8b71701ef1f951d014'))

def sha(data):return hashlib.sha256(data).hexdigest()


def transform_source(source,*,readable):
    if (type(source) is not bytes or len(source)!=INPUT_BYTES or sha(source)!=INPUT_SHA256
            or type(readable) is not bytes or sha(readable)!=READABLE_SHA256):
        raise ValueError('exact B post-clock/line-drain shipping and unchanged readable required')
    if len(re.findall(rb'\bP\s*\(',source))!=7 or len(re.findall(rb'\bF\s*\(',source))!=3 or source.count(b'previous')!=4:
        raise ValueError('fixed private B search/learner caller inventory differs')
    parts=[];last=0;complement=[]
    for role,old_at,new_at,old,new in REGIONS:
        if old_at<last or source[old_at:old_at+len(old)]!=old:
            raise ValueError('fixed B search role differs: '+role)
        gap=source[last:old_at];parts.extend((gap,new));complement.append(gap);last=old_at+len(old)
    parts.append(source[last:]);complement.append(source[last:]);result=b''.join(parts)
    for old_at,new_at,length,digest in PROTECTED_GAPS:
        if sha(source[old_at:old_at+length])!=digest or sha(result[new_at:new_at+length])!=digest:
            raise ValueError('protected B body/gap differs')
    inverse=result
    for role,old_at,new_at,old,new in reversed(REGIONS):
        if inverse[new_at:new_at+len(new)]!=new:raise ValueError('fixed B search inverse role differs')
        inverse=inverse[:new_at]+old+inverse[new_at+len(new):]
    if inverse!=source or len(result)!=OUTPUT_BYTES or sha(result)!=OUTPUT_SHA256:
        raise ValueError('fixed B search output or full inverse differs')
    return result,{'stage':'B-shipping-after-clock-and-line-drain','exact_regions':len(REGIONS),
        'source_bytes_delta':OUTPUT_BYTES-INPUT_BYTES,'full_source_inverse':True,
        'protected_gaps':len(PROTECTED_GAPS),'protected_complement_sha256':sha(b''.join(complement)),
        'P_definition_same_position_child_root_roles':[1,1,4,1],'root_neutral_slot':6,
        'black_king_slot_zero_valid':True,'same_position_entry_row_forwarded':True,
        'same_position_excluded_TT_learning0_other_arguments_unchanged':True,
        'child_slot':'signed already-made child piece at TO plus6, including promotion/EP/castle',
        'current_row_read_advanced_to_private_caller_child':True,
        'singular_forwarding_no_additional_Board_read':True,'general_read_timing_equivalence':False,
        'quiet_cutoff_parent_FROM_column_equal':True,'existing_positive_F_byte_identical':True,
        'SEE_cancel_singular_depth_windows_TT_learning_conditions_protected':True,
        'gen_make_repetition_model_input_pool_bytes_protected':True,
        'DEV_canonical_unchanged':True,'new_native_identity_required':True}
