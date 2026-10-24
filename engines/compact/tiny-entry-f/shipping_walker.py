"""Fixed full-F direct walker calls, after its shared-condition stage.

Remove c/T forwarding functions and reuse T for the actual static walker.
This avoids h/walker/U local-g shadowing without changing any local binding.
Actual callers are attack6 and generation2; null-buffer result0/1 and the
ordered512-slot generation/count/abort stay. Additional arguments are pure
constants/local/immutable Board reads. No Board/TT/MTD/learner/pool mutation
is added. The closed single TU has no wrapper-address/external API consumer.
External C ABI/function-name/frame/stack/native/timing identity is not claimed.
Canonical/DEV, optional selected products and F8 pre-name source bypass this
late stage. No files, compiler, environment, codec or report are consulted.
"""
import hashlib

INPUT=(8469,'350fdabcac9809267bbb47a7f3a76e6029933e11455322e6306f705fb6554136')
OUTPUT=(8410,'0185b1140d96adc4c0e48ba08ee52e296f733046a9958c6810ecec2e39e4a884')
_EDITS=((1367, b'g', b'T'), (1387, b'S c(const za*p,S a,S d){return g(p,0,a,d);}', b''), (2254, b'c(t,t->k[s<0],-s)', b'T(t,0,t->k[s<0],-s)'), (2500, b'g', b'T'), (3033, b'c(p,u,-s)', b'T(p,0,u,-s)'), (3087, b'c(p,u+1,-s)', b'T(p,0,u+1,-s)'), (3170, b'c(p,u-1,-s)', b'T(p,0,u-1,-s)'), (3211, b'S T(const za*p,Y*a){return g(p,a,0,p->s);}', b''), (4077, b'c(p,p->k[p->s<0],-p->s)', b'T(p,0,p->k[p->s<0],-p->s)'), (4243, b'T(p,x)', b'T(p,x,0,p->s)'), (5617, b'c(p,p->k[p->s<0],-p->s)', b'T(p,0,p->k[p->s<0],-p->s)'), (6150, b'T(b,a)', b'T(b,a,0,b->s)'))
_GAPS=((1367, '957294553dee862123a7073cbee2678e9df3667bac7b47cec10482809916c302'), (19, 'c6f98ceea4d0aaa400c5de805f28e4478568b03a9d99d5646d9d73687c936a1a'), (824, 'bf717197483c01d64abe5f5eaa391d040912098f6a0151d412ca4ed4636203ff'), (229, 'f8f49833cbb44e4f55bc3b0809deda999874e52d8c0964af22a485d2daabe751'), (532, '7812ff8744ee7919576f7f06c98cba20a668cf8fde44748933e409e853f7f03b'), (45, '274f9a9be10453e51e525f5e47973c7249c8e0584bc609bdbfb6242106031071'), (72, '980cd538126cb0cb7d01435b30bca9704c3201c2d7424e42494c1de55b67d057'), (30, 'ed0ba3bebbe0479e0de548633d017c6542b66c90eb5560223fa5bd4732f4bf3f'), (824, '162f35f952f668a302061a87584eca74554ae01d2f07b314b75eb18d607195dc'), (143, '4570717b9e0317ecb0d4d3bb005eccd2748841d71e23694a24ae7bd320dae1a6'), (1368, '8f49c6f9a5a13b62e948220d9d3c65ce28e26843f96e0b9d49552d1d3a8d6f76'), (510, 'cbf099bf9f1a768291edc49467a45dacfdffab3da3576d69450871f2f75a9c35'), (2313, 'f507b0e33f9bca83f00dbbea58b1e83665edf332cef200fe3e998b4cae3f3ec1'))

def _pin(data):return len(data),hashlib.sha256(data).hexdigest()

def transform_source(source):
    if type(source) is not bytes or _pin(source)!=INPUT:
        raise ValueError('fixed full-F post-condition walker input differs')
    parts=[];gaps=[];new_spans=[];cursor=size=0
    for start,old,new in _EDITS:
        end=start+len(old)
        if start<cursor or source[start:end]!=old:
            raise ValueError('fixed walker span/order differs')
        gap=source[cursor:start];gaps.append(gap);parts.extend((gap,new))
        size+=len(gap);new_spans.append((size,old,new));size+=len(new);cursor=end
    gaps.append(source[cursor:]);parts.append(gaps[-1]);result=b''.join(parts)
    inverse=result
    for start,old,new in reversed(new_spans):
        if inverse[start:start+len(new)]!=new:
            raise ValueError('fixed walker replacement span differs')
        inverse=inverse[:start]+old+inverse[start+len(new):]
    new_gaps=[];cursor=0
    for start,old,new in new_spans:
        new_gaps.append(result[cursor:start]);cursor=start+len(new)
    new_gaps.append(result[cursor:])
    if (tuple(map(_pin,gaps))!=_GAPS or new_gaps!=gaps
            or _pin(result)!=OUTPUT or inverse!=source):
        raise ValueError('fixed walker output/gaps/full inverse differs')
    return result,{'family':'F','policy':'full-fixed2','stage':'direct-walker-after-shared-condition',
        'input_bytes':INPUT[0],'input_sha256':INPUT[1],
        'output_bytes':OUTPUT[0],'output_sha256':OUTPUT[1],
        'raw_delta':-59,'spans':12,'gaps':13,'full_inverse':True,'all_gaps_equal':True,
        'attack_calls':6,'generation_calls':2,'local_g_bindings_changed':0,
        'function_address_external_C_ABI_claimed':False,'native_identity_claimed':False,
        'external_reads':0}
