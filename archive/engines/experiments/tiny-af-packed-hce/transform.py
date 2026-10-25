"""One literal packed-coefficient function replacement per current A/F input."""
import hashlib

FIXED = {
    'A': (9687, '6946861173a6b1dee660e83d72db40cde36a066be04e3c4457d4b67a6ab7ae4e',
          9675, 'c7734b9a325fad922e07fa93eb0c0b3b8e5b9260a4403a507a9a9a3ffc4f4b30', 'al', 'l'),
    'F': (9702, '60a74d16a6b3fbd7c1fc2d05207cfe4b860a52746caca137f7d34418762eab99',
          9690, 'e0aa8dd94f6dbfa1a3da172cde28492083d259b780344f49e7f5eb906523f9f6', 'ad', 'j'),
}
OLD = 'int {function}(int v,int q){{static const int qi[7]={{0,100,320,330,500,900,0}};int a=abs(v),d=q>>4,f=q&7,g=v>0?d:7-d,i=7-abs(2*f-7)-abs(2*d-7),{score}=qi[a]+g*(a==1?7:a==4?2:0)+i*(a==2?9:a==3?5:a==6?-3:(a==1||a==5)*2);return v>0?{score}:-{score};}}'
NEW = 'int {function}(int v,int q){{static const int qi[7]={{24576,48228,98624,65866,27124,41860,0}};int a=qi[abs(v)],d=q>>4,f=q&7,g=v>0?d:7-d,i=7-abs(2*f-7)-abs(2*d-7),{score}=(a&1023)+g*((a>>10)&7)+i*((a>>13)-3);return v>0?{score}:-{score};}}'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def transform(source, family):
    size, pin, new_size, new_pin, function, score = FIXED[family]
    if len(source) != size or sha(source) != pin:
        raise ValueError('exact uncombined current family shipping input required')
    old = OLD.format(function=function, score=score).encode()
    new = NEW.format(function=function, score=score).encode()
    if source.count(old) != 1 or len(old) != 219 or len(new) != 207:
        raise ValueError('fixed function domain differs')
    candidate = source.replace(old, new, 1)
    if candidate.count(new) != 1 or candidate.replace(new, old, 1) != source:
        raise ValueError('exact inverse differs')
    if candidate.replace(new, b'$FUNCTION', 1) != source.replace(old, b'$FUNCTION', 1):
        raise ValueError('protected complement differs')
    if len(candidate) != new_size or sha(candidate) != new_pin:
        raise ValueError('exact candidate identity differs')
    return candidate, {'old_function_bytes': 219, 'new_function_bytes': 207,
                       'source_delta': -12, 'inverse_equal': True,
                       'protected_complement_equal': True, 'new_names': 0,
                       'model_or_material_summary_composition': False}
