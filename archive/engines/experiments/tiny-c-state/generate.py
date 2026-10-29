"""One shipping-only removal of the unused C HCE cache; no other changes."""
import hashlib

CONTROL_SHA256='f0bc01d4ebde79578248e1d210723bff6be0639e829c166d6204de02466c3e82'


def sha(data):return hashlib.sha256(data).hexdigest()


def transform(source):
    if sha(source)!=CONTROL_SHA256:raise ValueError('unknown fixed C5955 readable control')
    text=source.decode()
    replacements=(
        ('int s,c,e,k[2],half,v;', 'int s,c,e,k[2],half\n#if DEV\n,v\n#endif\n;'),
        ('if(old){p->h^=piece(old,q);p->v-=value(old,q);}',
         'if(old){p->h^=piece(old,q);\n#if DEV\np->v-=value(old,q);\n#endif\n}'),
        ('if(v){p->h^=piece(v,q);p->v+=value(v,q);if(abs(v)==6)p->k[v<0]=q;}',
         'if(v){p->h^=piece(v,q);\n#if DEV\np->v+=value(v,q);\n#endif\nif(abs(v)==6)p->k[v<0]=q;}'),
    )
    for before,after in replacements:
        if text.count(before)!=1:raise ValueError('fixed cache-removal shape changed')
        text=text.replace(before,after)
    if text.count('int error=best-evaluation;')!=1 or 'best-p->s*p->v' in text:
        raise ValueError('unchanged correction residual contract differs')
    result=text.encode()
    restored=text
    for before,after in reversed(replacements):restored=restored.replace(after,before)
    if restored.encode()!=source:raise ValueError('unexpected edits outside the three declared guard sites')
    return result,{'control_sha256':sha(source),'candidate_sha256':sha(result),
                   'changes':['DEV-only Board.v declarator','DEV-only old-piece HCE subtraction','DEV-only new-piece HCE addition'],
                   'other_bytes_unchanged':True,'braces_unchanged':True,'residual_unchanged':True,
                   'expected_shipping_lexical_bytes_removed':38,'expected_LP64_Board_bytes':[176,168],
                   'DEV_cache_and_oracle_retained':True,'fixed_candidate_count':1}
