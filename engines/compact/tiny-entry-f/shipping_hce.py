"""Fixed ordinary shipping-only packed HCE coefficients after declarations."""
import hashlib

OLD_SOURCE_BYTES = 9702
OLD_SOURCE_SHA256 = '60a74d16a6b3fbd7c1fc2d05207cfe4b860a52746caca137f7d34418762eab99'
NEW_SOURCE_BYTES = 9690
NEW_SOURCE_SHA256 = 'e0aa8dd94f6dbfa1a3da172cde28492083d259b780344f49e7f5eb906523f9f6'
OLD = b'int ad(int v,int q){static const int qi[7]={0,100,320,330,500,900,0};int a=abs(v),d=q>>4,f=q&7,g=v>0?d:7-d,i=7-abs(2*f-7)-abs(2*d-7),j=qi[a]+g*(a==1?7:a==4?2:0)+i*(a==2?9:a==3?5:a==6?-3:(a==1||a==5)*2);return v>0?j:-j;}'
NEW = b'int ad(int v,int q){static const int qi[7]={24576,48228,98624,65866,27124,41860,0};int a=qi[abs(v)],d=q>>4,f=q&7,g=v>0?d:7-d,i=7-abs(2*f-7)-abs(2*d-7),j=(a&1023)+g*((a>>10)&7)+i*((a>>13)-3);return v>0?j:-j;}'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def transform_source(source):
    if len(source) != OLD_SOURCE_BYTES or sha(source) != OLD_SOURCE_SHA256:
        raise ValueError('exact post-declarations F source required')
    if source.count(OLD) != 1:
        raise ValueError('fixed HCE old function is not unique')
    result = source.replace(OLD, NEW, 1)
    if result.count(NEW) != 1 or result.replace(NEW, OLD, 1) != source:
        raise ValueError('fixed HCE inverse differs')
    if source.replace(OLD, b'$VALUE', 1) != result.replace(NEW, b'$VALUE', 1):
        raise ValueError('fixed HCE protected complement differs')
    if len(result) != NEW_SOURCE_BYTES or sha(result) != NEW_SOURCE_SHA256:
        raise ValueError('fixed HCE output differs')
    return result, {'stage': 'shipping-after-declarations', 'inverse_equal': True,
                    'protected_complement_equal': True, 'source_delta': -12,
                    'signed_int_coefficient_bits': [10, 3], 'center_bias': 3,
                    'new_names': 0, 'canonical_DEV_changed': False,
                    'old_function_bytes': 219, 'new_function_bytes': 207}
