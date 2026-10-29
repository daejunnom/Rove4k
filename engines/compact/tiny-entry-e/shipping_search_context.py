"""Close fixed E shipping continuation slots and positive cutoff bonuses.

M has one definition, four successful-made-child calls and one neutral root.
The two learner callers pass positive depth squared. E19 nonlinear model,
ordering and all other source bytes are protected; canonical/DEV bypass this
stage. No experiment, receipt, AST or generated artifact is a runtime input.
"""
import hashlib
import re

INPUT_BYTES=10400
INPUT_SHA256='431bdde48fd1f2d450bb92dd6c03e3309017158353de06bfe4fffd0bc96c839e'
OUTPUT_BYTES=10360
OUTPUT_SHA256='6e9e7eb6a439934aba2d48f9387f710a95a0032a89233ff2b676b5d6451d47fb'
READABLE_SHA256='0a7fe69022051e1893ffbd52ade7a2fbb3f342fe20b581bb786d6997b46fb712'

REGIONS=(('positive-only-cutoff-bonus', 4720, 4720, b'static void C(int16_t*a,int d){*a+=(d-*a*abs(d)/16384);}', b'static void C(int16_t*a,int d){*a+=(d-*a*d/16384);}'), ('search-context-argument', 4895, 4890, b'static int M(zd*w,const za*p,int a,int d,int f,int n,T previous,T*u)', b'static int M(zd*w,const za*p,int a,int d,int f,int n,int yb,T*u)'), ('remove-child-redecode', 5591, 5582, b'int yb=previous?F(p->b[TO(previous)]):6;', b''), ('selected-made-child-slot', 5971, 5922, b'int zJ=FROM(m),to=TO(m),yu=l(p,m)||PROMO(m);', b'int zJ=FROM(m),to=TO(m),yu=l(p,m)||PROMO(m),pi=F(q.b[to]);'), ('all-four-PVS-context-ports', 6062, 6027, b'if(Z==1||a<=0)yl=-M(w,&q,a-1,-f,-d,n+1,m,0);else{int yg=a>=4&&Z>=4&&!yu&&!v&&!b(&q,q.k[q.s<0],-q.s);if(yg){yg=zF+w->zx[p->h&1023]/64<d+100;}yl=-M(w,&q,a-1-yg,-d-1,-d,n+1,m,0);if(yg&&yl>d)yl=-M(w,&q,a-1,-d-1,-d,n+1,m,0);if(yl>d&&yl<f)yl=-M(w,&q,a-1,-f,-d,n+1,m,0);}', b'if(Z==1||a<=0)yl=-M(w,&q,a-1,-f,-d,n+1,pi,0);else{int yg=a>=4&&Z>=4&&!yu&&!v&&!b(&q,q.k[q.s<0],-q.s);if(yg){yg=zF+w->zx[p->h&1023]/64<d+100;}yl=-M(w,&q,a-1-yg,-d-1,-d,n+1,pi,0);if(yg&&yl>d)yl=-M(w,&q,a-1,-d-1,-d,n+1,pi,0);if(yl>d&&yl<f)yl=-M(w,&q,a-1,-f,-d,n+1,pi,0);}'), ('quiet-cutoff-column-reuse', 6497, 6466, b'C(&w->zw[yb][F(p->b[zJ])],zn);', b'C(&w->zw[yb][pi],zn);'), ('root-neutral-context', 7023, 6983, b'int f=M(w,p,a,-MATE,MATE,0,0,&d);', b'int f=M(w,p,a,-MATE,MATE,0,6,&d);'))

PROTECTED_GAPS=((0, 0, 4720, '0f9adc0b8fa676f4fed155151539655ef1df58fd6187e12733292510c6f361c6'), (4776, 4771, 119, 'e6f6fdca1f73b0856217933501f59b0a21f0a33479d9e8808662d6b293067072'), (4963, 4954, 628, '0827497c5ff5ef2e4dbea4dbcf13c1b52c864c5164e01a2ec7f5dbf63a3f95d0'), (5631, 5582, 340, '793b92d35cf93710ee919a10846248d0ad667718659f0f55d44ffed90e247df1'), (6015, 5980, 47, '68cb201b24b30f28fac076037ca62c3d8c601ccd78c3198195b2f205592ac9b0'), (6326, 6295, 171, '43ef450579c456d36225110b310afc2ac2d5eb03143fc162775417e276db29dc'), (6527, 6487, 496, '95d6bc34b23439459cf0812b4afc12a836cbef2b3f68e5a9f0cd46cfd7af431e'), (7056, 7016, 3344, '4909ce33e5cd11f7fead88c41d9d9deafd1a8e064dd8aaa4ac153e8a8d891256'))

def sha(data):return hashlib.sha256(data).hexdigest()


def transform_source(source,*,readable):
    if (type(source) is not bytes or len(source)!=INPUT_BYTES or sha(source)!=INPUT_SHA256
            or type(readable) is not bytes or sha(readable)!=READABLE_SHA256):
        raise ValueError('exact E post-clock/model-zero shipping and unchanged readable required')
    if len(re.findall(rb'\bM\s*\(',source))!=6 or len(re.findall(rb'\bC\s*\(',source))!=3 or source.count(b'previous')!=3:
        raise ValueError('fixed private E search/cutoff caller inventory differs')
    parts=[];last=0;complement=[]
    for role,old_at,new_at,old,new in REGIONS:
        if old_at<last or source[old_at:old_at+len(old)]!=old:
            raise ValueError('fixed E search role differs: '+role)
        gap=source[last:old_at];parts.extend((gap,new));complement.append(gap);last=old_at+len(old)
    parts.append(source[last:]);complement.append(source[last:]);result=b''.join(parts)
    for old_at,new_at,length,digest in PROTECTED_GAPS:
        if sha(source[old_at:old_at+length])!=digest or sha(result[new_at:new_at+length])!=digest:
            raise ValueError('protected E body/gap differs')
    inverse=result
    for role,old_at,new_at,old,new in reversed(REGIONS):
        if inverse[new_at:new_at+len(new)]!=new:raise ValueError('fixed E search inverse role differs')
        inverse=inverse[:new_at]+old+inverse[new_at+len(new):]
    if inverse!=source or len(result)!=OUTPUT_BYTES or sha(result)!=OUTPUT_SHA256:
        raise ValueError('fixed E search output or full inverse differs')
    return result,{'stage':'E-shipping-after-clock-and-model-zero-slots','exact_regions':len(REGIONS),
        'source_bytes_delta':OUTPUT_BYTES-INPUT_BYTES,'full_source_inverse':True,
        'protected_gaps':len(PROTECTED_GAPS),'protected_complement_sha256':sha(b''.join(complement)),
        'M_definition_recursive_root_roles':[1,4,1],'root_neutral_slot':6,
        'child_slot':'signed already-made child piece at TO plus6, including promotion/EP/castle',
        'quiet_cutoff_parent_FROM_column_equal':True,'C_positive_callers':2,
        'depth_bonus_domain':[1,126],'bonus_domain':[1,15876],
        'all_int16_cell_product_abs_max':520224768,'E19_model_and_ordering_bytes_protected':True,
        'board_gen_make_repetition_TT_correction_input_pool_bytes_protected':True,
        'DEV_canonical_unchanged':True,'new_native_identity_required':True}
