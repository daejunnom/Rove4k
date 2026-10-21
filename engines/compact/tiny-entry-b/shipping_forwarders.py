"""Pure B shipping direct ports to the existing shared walker.

Apply after HCE declarations. Preserve full-mask/Boolean/count domains and
rename only H's private output parameter to unshadow c. Canonical and DEV
bypass this stage. No file, compiler, codec or research artifact is read.
"""
import hashlib

_BEFORE=(10394,'61f6dabc7b171c864c3d3511906799e13b638023d96a537c1fa15a05a0648c63')
_AFTER=(10270,'c64dd2000d88396d41165e3a288ed5464c07d791cb27e3562c8934459c625278')
_REGIONS=((2493, 2493, b'static D l(const za*p,int sq,int s){return c(p,0,sq,s);}int e(const za*p,int a,int d){return l(p,a,d)!=0;}', b''), (2982, 2876, b'!e(&t,p->k[p->s<0],-p->s)', b'!c(&t,0,p->k[p->s<0],-p->s)'), (3486, 3382, b'if(e(t,t->k[s<0],-s))', b'if(c(t,0,t->k[s<0],-s))'), (3772, 3670, b'int v(const za*p,N*f){return c(p,f,0,p->s);}', b''), (4666, 4520, b'D d=l(&t,yv,t.s);', b'D d=c(&t,0,yv,t.s);'), (5019, 4875, b'int z=e(p,p->k[p->s<0],-p->s),', b'int z=!!c(p,0,p->k[p->s<0],-p->s),'), (5176, 5036, b'Z=v(p,X),', b'Z=c(p,X,0,p->s),'), (6507, 6374, b'!e(&q,q.k[q.s<0],-q.s)', b'!c(&q,0,q.k[q.s<0],-q.s)'), (7827, 7696, b'static N H(const za*b,const char*s,za*c){N a[MOVES];char d[6];int n=v(b,a);for(int i=0;i<n;i++){if(s){T(a[i],d);if(strcmp(s,d))continue;}if(h(b,a[i],c))return a[i];}return 0;}', b'static N H(const za*b,const char*s,za*j){N a[MOVES];char d[6];int n=c(b,a,0,b->s);for(int i=0;i<n;i++){if(s){T(a[i],d);if(strcmp(s,d))continue;}if(h(b,a[i],j))return a[i];}return 0;}'))
_GAPS=((0, 0, 2493, '9cd4f1821aabd25a23166245f37d59db2e8f57ed054d57e398a64d4e9e7e8f50'), (2599, 2493, 383, '2ae66282e8aa45d3d3007cec8057ec546deeb81893c1bace137cedd4368d0c95'), (3007, 2903, 479, '3564047bcb8f2c7c4e16db8b8f1eccbc7c71f65f55f8ef801a2715da25b36db7'), (3507, 3405, 265, '45fc647df5bc8e6ed183e8adc5776dea253f72ccd5235751e0ec655adc438558'), (3816, 3670, 850, '0ae59e7c727501ffa4b06c5c9cb1b8757525dda9334f696e445d25f8e8ea2bb9'), (4683, 4539, 336, '718c4d1a1ed5a645a91a4ac02476c27abc2f877e115e3b2c206f1ee7c6ba63f4'), (5049, 4909, 127, 'd919591d3bef3a38ad07e2b0c2d55ca2507b564a16d41e649b419e226f44add7'), (5185, 5052, 1322, '4ec1e4603d7399b2a0f40f5675749f4786d57f3f0eb6245b3d7495e2cc1bd241'), (6529, 6398, 1298, 'c10f19087058964bcad424c6fc21f454437f1776b10d2f96ce7b892ac5a23451'), (8002, 7878, 2392, '0d49871e88de714bd311ef72d9ae581d29d9a406b5c9980d821225e701c5d1ff'))
_COMPLEMENT=(9945, 'ddf866383081f2b841c53dccaaea13b07761cffa7fd1d70382ba98c13d2295ab')

def _pin(data):return len(data),hashlib.sha256(data).hexdigest()

def transform_source(source):
    if type(source) is not bytes or _pin(source)!=_BEFORE:
        raise ValueError('fixed B after-declarations shipping source required')
    parts=[];previous=0
    for old_at,new_at,old,new in _REGIONS:
        if old_at<previous or source[old_at:old_at+len(old)]!=old:
            raise ValueError('fixed B walker-forwarder role differs')
        parts.extend((source[previous:old_at],new));previous=old_at+len(old)
    parts.append(source[previous:]);result=b''.join(parts)
    if _pin(result)!=_AFTER:raise ValueError('fixed B direct-walker source differs')
    complement=[]
    for old_at,new_at,length,digest in _GAPS:
        old=source[old_at:old_at+length];new=result[new_at:new_at+length]
        if old!=new or hashlib.sha256(old).hexdigest()!=digest:
            raise ValueError('protected B direct-walker gap differs')
        complement.append(old)
    if _pin(b''.join(complement))!=_COMPLEMENT:
        raise ValueError('protected B direct-walker complement differs')
    inverse=result
    for old_at,new_at,old,new in reversed(_REGIONS):
        if inverse[new_at:new_at+len(new)]!=new:
            raise ValueError('B direct-walker inverse role differs')
        inverse=inverse[:new_at]+old+inverse[new_at+len(new):]
    if inverse!=source:raise ValueError('full B direct-walker inverse differs')
    return result,{'family':'B','stage':'late-shipping-shared-walker-direct-ports',
        'input_bytes':_BEFORE[0],'input_sha256':_BEFORE[1],
        'output_bytes':_AFTER[0],'output_sha256':_AFTER[1],'raw_delta':-124,
        'owned_regions':9,'protected_gaps':10,'all_gaps_equal':True,'full_inverse':True,
        'protected_complement_bytes':_COMPLEMENT[0],
        'protected_complement_sha256':_COMPLEMENT[1],
        'forwarder_definitions_removed':3,'consumer_ports':7,
        'P_int_check_explicit_bool':True,'Q_entire_attack_mask':True,
        'generated_count_domain':[0,432],'H_private_output_unshadow':'c to j',
        'same_walker_body_arguments_move_order_and_truth':True,
        'search_TT_learners_worker_result_lifetimes_protected':True,
        'canonical_DEV':'caller bypass; earlier readable and helper guards unchanged',
        'general_external_C_ABI_symbol_frame_timing_equivalence_claimed':False,
        'new_native_requires_separate_actual_qualification':True,
        'external_reads':0,'compiler_codec_engine_executed_by_transform':0}
