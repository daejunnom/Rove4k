"""Close the fixed C continuation-slot and positive-cutoff-bonus source form.

The standalone shipping search has six P roles: one definition, four recursive
calls, and think's root call. Successful make supplies the signed child piece
slot; root supplies neutral6. Quiet-only cutoff learning uses the same column.
E's only two callers pass depth*depth with depth1..126. DEV/canonical keep their
old APIs and general learner formula. No experiment, report, AST or generated
artifact is an input to this ordinary fixed transformation.
"""
import hashlib
import re

INPUT_BYTES=10072
INPUT_SHA256='fc2209ce96c714d3828790cae882051f8cbf8980f4e874381954280f0c9d17a3'
OUTPUT_BYTES=10032
OUTPUT_SHA256='7612b83cb6a274c9b67c5217aa9c983c6271378df234b6d853e8985d97e46b12'
READABLE_SHA256='15999279c5bd4690db7129bda032c6b5962acbd814236719cda40755ae31794b'

REGIONS=(('C2-positive-only-bonus', 4468, 4468, b'static void E(int16_t*a,int d){*a+=(d-*a*abs(d)/16384);}', b'static void E(int16_t*a,int d){*a+=(d-*a*d/16384);}'), ('C1-search-context-argument', 4643, 4638, b'static int P(zd*w,const za*p,int a,int d,int f,int n,T previous,T*u)', b'static int P(zd*w,const za*p,int a,int d,int f,int n,int yb,T*u)'), ('C1-remove-child-redecode', 5338, 5329, b'int yb=previous?I(p->b[TO(previous)]):6;', b''), ('C1-selected-made-child-slot', 5748, 5699, b'int zJ=FROM(m),to=TO(m),yu=l(p,m)||PROMO(m);', b'int zJ=FROM(m),to=TO(m),yu=l(p,m)||PROMO(m),pi=I(q.b[to]);'), ('C1-all-four-identical-PVS-context-ports', 5839, 5804, b'if(Y==1||a<=0)yl=-P(w,&q,a-1,-f,-d,n+1,m,0);else{int yg=a>=4&&Y>=4&&!yu&&!v&&!b(&q,q.k[q.s<0],-q.s);if(yg){yg=zF+w->zx[p->h&1023]/64<d+100;}yl=-P(w,&q,a-1-yg,-d-1,-d,n+1,m,0);if(yg&&yl>d)yl=-P(w,&q,a-1,-d-1,-d,n+1,m,0);if(yl>d&&yl<f)yl=-P(w,&q,a-1,-f,-d,n+1,m,0);}', b'if(Y==1||a<=0)yl=-P(w,&q,a-1,-f,-d,n+1,pi,0);else{int yg=a>=4&&Y>=4&&!yu&&!v&&!b(&q,q.k[q.s<0],-q.s);if(yg){yg=zF+w->zx[p->h&1023]/64<d+100;}yl=-P(w,&q,a-1-yg,-d-1,-d,n+1,pi,0);if(yg&&yl>d)yl=-P(w,&q,a-1,-d-1,-d,n+1,pi,0);if(yl>d&&yl<f)yl=-P(w,&q,a-1,-f,-d,n+1,pi,0);}'), ('C1-quiet-cutoff-reuse', 6274, 6243, b'E(&w->zw[yb][I(p->b[zJ])],zn);', b'E(&w->zw[yb][pi],zn);'), ('C1-root-neutral-context', 6799, 6759, b'int f=P(w,p,a,-MATE,MATE,0,0,&d);', b'int f=P(w,p,a,-MATE,MATE,0,6,&d);'))

PROTECTED_GAPS=((0, 0, 4468, '3aac7269fd753f640671642c149e5200a10cf1307e389ecc40e5867a346d151c'), (4524, 4519, 119, 'c375308ed174b62c07201d2d74cb11e654ff81d4d4ee5e0b94f1abb5589d182c'), (4711, 4702, 627, '768220baba5907afa06b11dd9aa79cd94efc6d971b11bc4d9f74b7e9c18bca05'), (5378, 5329, 370, 'ab47bdbf5808cfe0f1e8076943a292a98c24f3229134d2a294d0e429808dece3'), (5792, 5757, 47, '68cb201b24b30f28fac076037ca62c3d8c601ccd78c3198195b2f205592ac9b0'), (6103, 6072, 171, '7db026164988c02904067c722f2a0f7b3b320c5a5cedbc0440c3f08ade9f79e0'), (6304, 6264, 495, '9b574e4478829da7f4a3b42f36786de2e2749d2e735529481586955afbaedf3d'), (6832, 6792, 3240, '3113a30b568fdeef740e471f616729471d6b154b3ae370081a9e28e647eebd5e'))

def sha(data):return hashlib.sha256(data).hexdigest()


def transform_source(source,*,readable):
    if (type(source) is not bytes or len(source)!=INPUT_BYTES or sha(source)!=INPUT_SHA256
            or type(readable) is not bytes or sha(readable)!=READABLE_SHA256):
        raise ValueError('exact post-clock C shipping and unchanged readable required')
    if len(re.findall(rb'\bP\s*\(',source))!=6 or len(re.findall(rb'\bE\s*\(',source))!=3 or source.count(b'previous')!=3:
        raise ValueError('fixed private search/cutoff caller inventory differs')
    parts=[];last=0;complement=[]
    for role,old_at,new_at,old,new in REGIONS:
        if old_at<last or source[old_at:old_at+len(old)]!=old:
            raise ValueError('fixed C search role differs: '+role)
        gap=source[last:old_at];parts.extend((gap,new));complement.append(gap);last=old_at+len(old)
    parts.append(source[last:]);complement.append(source[last:]);result=b''.join(parts)
    for old_at,new_at,length,digest in PROTECTED_GAPS:
        if sha(source[old_at:old_at+length])!=digest or sha(result[new_at:new_at+length])!=digest:
            raise ValueError('protected C body/gap differs')
    inverse=result
    for role,old_at,new_at,old,new in reversed(REGIONS):
        if inverse[new_at:new_at+len(new)]!=new:raise ValueError('fixed search inverse role differs')
        inverse=inverse[:new_at]+old+inverse[new_at+len(new):]
    if inverse!=source or len(result)!=OUTPUT_BYTES or sha(result)!=OUTPUT_SHA256:
        raise ValueError('fixed C search output or full inverse differs')
    return result,{'stage':'C-shipping-after-clock-presence','exact_regions':len(REGIONS),
        'source_bytes_delta':OUTPUT_BYTES-INPUT_BYTES,'full_source_inverse':True,
        'protected_gaps':len(PROTECTED_GAPS),'protected_complement_sha256':sha(b''.join(complement)),
        'P_definition_recursive_root_roles':[1,4,1],'root_neutral_slot':6,
        'child_slot':'signed already-made child piece at TO plus6, including promotion/EP/castle',
        'quiet_cutoff_parent_FROM_column_equal':True,'E_positive_callers':2,
        'depth_bonus_domain':[1,126],'bonus_domain':[1,15876],
        'all_int16_cell_product_abs_max':520224768,
        'board_gen_make_SIMD_context_TT_input_pool_bytes_protected':True,
        'DEV_canonical_unchanged':True,'new_native_identity_required':True}
