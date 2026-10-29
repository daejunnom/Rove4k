"""Exact E19 shipping material slots after the final clock-presence stage.

Pure bytes-to-bytes transform. The caller keeps DEV on its existing path and
runs the existing readable E19 model admission first. Only the admitted final
shipping source is accepted; no artifact, recipe or generated file is read.
"""
from hashlib import sha256
from struct import pack

INPUT_BYTES=10428
INPUT_SHA='072a0757878a53be119c9184f84ff8b2abe99d95ed702af2eaa15c53bc0350c9'
OUTPUT_BYTES=10400
OUTPUT_SHA='431bdde48fd1f2d450bb92dd6c03e3309017158353de06bfe4fffd0bc96c839e'
MODEL_ID='e-hand-quadratic-19-1'
PARAMETERS=(100, 320, 330, 500, 900, 3, 8, 5, 2, 1, -3, 6, 10, 1, 16, -1, 12, 2, 4)
PARAMETERS_I16LE_SHA='a5bb11099b62489aca43a011619e15076b0637b2f2e460d89772162965cd5424'
EDITS=((1034, 1034, b'static const int16_t tiny_weights[19]={100,320,330,500,900,3,8,5,2,1,-3,6,10,1,16,-1,12,2,4};', b'static const int16_t tiny_weights[21]={0,100,320,330,500,900,0,3,8,5,2,1,-3,6,10,1,16,-1,12,2,4};', '23a9db506c181cf5b31c7480d538707ce8ae194a0b0521bb54728ddc1ca97fb9', '2970794446c70c1f2bb5b611a57ce68f04853124a06c9469da688fa6ff3c28bc'), (1195, 1199, b'static I d(za*p,int v,int q,int d){int a=abs(v),s=v>0?d:-d;p->v+=s*(a<6?tiny_weights[a-1]:0);p->a+=s*(tiny_weights[a+4]*Q(q)+(a==1?tiny_weights[11]*((v<0?7-(q>>4):q>>4)-1):0));return c((I)(q+(v+6)*128));}', b'static I d(za*p,int v,int q,int d){int a=abs(v),s=v>0?d:-d;p->v+=s*tiny_weights[a];p->a+=s*(tiny_weights[a+6]*Q(q)+(a==1?tiny_weights[13]*((v<0?7-(q>>4):q>>4)-1):0));return c((I)(q+(v+6)*128));}', 'b54ca003bfd4e7bcba3cbc75dcacdf18d3f9f8aabdb32aadad7e8b1e6364f55f', '605420f951ef08c3a9113d84293c47053469477628ed8f27c9cebfe7be8dc5c4'), (3829, 3823, b'static int S(const za*p){int s=p->v+p->a+tiny_weights[13]*p->a*abs(p->a)/128+p->s*tiny_weights[12];return s>20000?20000:s< -20000?-20000:s;}', b'static int S(const za*p){int s=p->v+p->a+tiny_weights[15]*p->a*abs(p->a)/128+p->s*tiny_weights[14];return s>20000?20000:s< -20000?-20000:s;}', '562cf997f09a85ea865702e13a98da76576cca1b7b1b7d7d5301138d01486adf', 'bde59e4cab8600f24b0c88618fcefb4f6ed89e4edefba30cdc5a6d93de18bfcf'), (3969, 3963, b'static int R(const za*p,T m){int d=FROM(m),f=TO(m),i=p->b[d],a=abs(i),v=abs(p->b[f]),j=PROMO(m);if(a==1&&f==p->e&&!v)v=1;int s=tiny_weights[17]*(Q(f)-Q(d));if(v)s+=tiny_weights[14]*(v<6?tiny_weights[v-1]:0)+tiny_weights[15]*(a<6?tiny_weights[a-1]:0);if(j)s+=tiny_weights[16]*(tiny_weights[j-1]-tiny_weights[0]);if(a==1)s+=tiny_weights[18]*((f>>4)-(d>>4))*(i<0?-1:1);return s;}', b'static int R(const za*p,T m){int d=FROM(m),f=TO(m),i=p->b[d],a=abs(i),v=abs(p->b[f]),j=PROMO(m);if(a==1&&f==p->e&&!v)v=1;int s=tiny_weights[19]*(Q(f)-Q(d));if(v)s+=tiny_weights[16]*tiny_weights[v]+tiny_weights[17]*tiny_weights[a];if(j)s+=tiny_weights[18]*(tiny_weights[j]-tiny_weights[1]);if(a==1)s+=tiny_weights[20]*((f>>4)-(d>>4))*(i<0?-1:1);return s;}', '2eaf701c6748db97edb92b25cfd8918bf1419422731a7bcf7795c60248a27fea', '1b6950fe9e8973675fe2baeb338c6990b1145c2c3875fb46704fc511822934a4'))
GAPS=((0, 1034, 0, 1034, 1034, 'd78613b029e07f0c421fcee77e86182a710c74a9282ab9ed16502985cdff5102'), (1127, 1195, 1131, 1199, 68, '16b06dee3d6bc0585f65d557e6599ee522d83e0389ce826a6713f56ae79df91a'), (1399, 3829, 1393, 3823, 2430, '25dac402dfc97d540b8490a48dd8f0ccfd90ce10354cfc7da7d8c1ce863768ca'), (3969, 3969, 3963, 3963, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (4345, 10428, 4317, 10400, 6083, '374c4488b0c209edac0972dab60e418a4a9729e6966be1c9c005127b2b7bd166'))
COMPLEMENT_BYTES=9615
COMPLEMENT_SHA='b86f4b07647890b2d5b9a8c663d6d7173094b950c98d7bb8a1f8df74eccd8f65'

def _sha(data):
    return sha256(data).hexdigest()


def _typed_values(fragment,count):
    prefix=('static const int16_t tiny_weights['+str(count)+']={').encode()
    if not fragment.startswith(prefix) or not fragment.endswith(b'};'):
        raise ValueError('fixed int16 table declaration differs')
    values=tuple(int(value) for value in fragment[len(prefix):-2].split(b','))
    if len(values)!=count or any(value< -32768 or value>32767 for value in values):
        raise ValueError('fixed int16 table extent/value differs')
    return values


def transform_source(source):
    """Apply four literal regions to exact clock10428 source; caller bypasses DEV."""
    if type(source) is not bytes or len(source)!=INPUT_BYTES or _sha(source)!=INPUT_SHA:
        raise ValueError('exact final E clock-presence shipping source required')
    parts=[];old_cursor=new_cursor=0
    for index,(old_at,new_at,old,new,old_sha,new_sha) in enumerate(EDITS):
        gap=GAPS[index]
        if (gap[0],gap[1],gap[2],gap[3])!=(old_cursor,old_at,new_cursor,new_at):
            raise ValueError('fixed source region/gap offsets differ')
        untouched=source[old_cursor:old_at]
        if len(untouched)!=gap[4] or _sha(untouched)!=gap[5]:
            raise ValueError('fixed complementary gap differs')
        if source.count(old)!=1 or source[old_at:old_at+len(old)]!=old:
            raise ValueError('fixed unique old model region differs')
        if _sha(old)!=old_sha or _sha(new)!=new_sha:
            raise ValueError('literal model fragment differs')
        parts.extend((untouched,new))
        old_cursor=old_at+len(old);new_cursor=new_at+len(new)
    gap=GAPS[-1];tail=source[old_cursor:]
    if (gap[0],gap[1],gap[2],gap[3])!=(old_cursor,INPUT_BYTES,new_cursor,OUTPUT_BYTES):
        raise ValueError('fixed final complementary gap offsets differ')
    if len(tail)!=gap[4] or _sha(tail)!=gap[5]:
        raise ValueError('fixed final complementary gap differs')
    parts.append(tail);result=b''.join(parts)
    if len(result)!=OUTPUT_BYTES or _sha(result)!=OUTPUT_SHA:
        raise ValueError('fixed zero-slot source identity differs')

    inverse=[];old_cursor=new_cursor=0;complement=[]
    for index,(old_at,new_at,old,new,old_sha,new_sha) in enumerate(EDITS):
        old_gap=source[old_cursor:old_at];new_gap=result[new_cursor:new_at]
        if old_gap!=new_gap or result[new_at:new_at+len(new)]!=new:
            raise ValueError('inverse region or byte complement differs')
        complement.append(old_gap);inverse.extend((new_gap,old))
        old_cursor=old_at+len(old);new_cursor=new_at+len(new)
    if source[old_cursor:]!=result[new_cursor:]:
        raise ValueError('inverse final complement differs')
    complement.append(source[old_cursor:]);inverse.append(result[new_cursor:])
    rest=b''.join(complement)
    if b''.join(inverse)!=source or len(rest)!=COMPLEMENT_BYTES or _sha(rest)!=COMPLEMENT_SHA:
        raise ValueError('full inverse/complement identity differs')
    if source.count(b'tiny_weights')!=15 or b'tiny_weights' in rest:
        raise ValueError('model consumer closure differs')

    old_values=_typed_values(EDITS[0][2],19)
    physical=_typed_values(EDITS[0][3],21)
    logical=physical[1:6]+physical[7:21]
    if physical[0]!=0 or physical[6]!=0 or logical!=old_values or logical!=PARAMETERS:
        raise ValueError('logical E19 coefficients or fixed zero slots differ')
    coefficient_sha=_sha(pack('<19h',*logical))
    if coefficient_sha!=PARAMETERS_I16LE_SHA:
        raise ValueError('logical signed16-le coefficient identity differs')
    return result,{
        'input_bytes':INPUT_BYTES,'input_sha256':INPUT_SHA,
        'output_bytes':OUTPUT_BYTES,'output_sha256':OUTPUT_SHA,'raw_delta':-28,
        'fixed_model_regions':4,'fixed_gaps':5,'full_inverse':True,
        'byte_complement_exact':True,'complement_bytes':COMPLEMENT_BYTES,
        'complement_sha256':COMPLEMENT_SHA,'all_table_consumers_in_regions':True,
        'model_id':MODEL_ID,'logical_coefficient_count':19,
        'signed16_le_sha256':coefficient_sha,'physical_int16_elements':21,
        'fixed_nonparameter_zero_slots':[0,6],
        'logical_extraction':'physical[1:6]+physical[7:21]',
        'caller_domain':'d reached by H only for nonzero signed1..6; R moving1..6/victim0..6, EP and promotion2..5',
        'domain_limit':'d(v=0) and invalid pieces remain outside the old caller contract',
        'qualification_scope':'exact shipping representation; no new model, DEV, runtime or strength qualification',
    }
