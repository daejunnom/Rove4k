"""Pure final B shipping stage: generated-Move tactical metadata in unused FROM bit3.

Private ABI/quiet-promotion ordering change. Old canonical/DEV bypass unchanged.
Only embedded source/literal/role pins are read; no experiment/artifact input."""
import hashlib
import re

INPUT = {'bytes':11532,'sha256':'3fca96ff1a913ed74edaed69d74794a433a9013e4a6cd88dc0e3dfe5e35d0b6f'}
OUTPUT = {'bytes': 11430, 'sha256': '54759113c9949f0f3d619d5eefe5e8ac4d6b562baf4c09da7e7743907d3f8a2a'}

READABLE_ADD = b'''static void add(Move *moves,int *count,int from,int to,int tag){
    int promotion=tag>1&&((to>>4)==0||(to>>4)==7);
    for(int z=promotion?2:0;z<=(promotion?5:0);z++){
        if(*count>=MOVES)abort();
        moves[(*count)++]=MOVE(from,to,z)|((promotion|tag)&1)*8;
    }
}
'''
ROLES = {'add':'g','moves':'a','count':'n','from':'zJ','tag':'d','promotion':'f'}
OLD_ADD = b'static void g(Move*a,int*n,int zJ,int to,int d){int f=d&&((to>>4)==0||(to>>4)==7);for(int z=f?2:0;z<=(f?5:0);z++){if(*n>=MOVES)abort();a[(*n)++]=MOVE(zJ,to,z);}}'
NEW_ADD = b'static void g(Move*a,int*n,int zJ,int to,int d){int f=d>1&&((to>>4)==0||(to>>4)==7);for(int z=f?2:0;z<=(f?5:0);z++){if(*n>=MOVES)abort();a[(*n)++]=MOVE(zJ,to,z)|((f|d)&1)*8;}}'
PAIRS = [
    ('FROM decode',b'#define FROM(m) ((m)&127)',b'#define FROM(m) ((m)&119)'),
    ('quiet pawn push',b'g(f,&n,j,m,1);',b'g(f,&n,j,m,2);'),
    ('geometric emission classification',b'g(f,&n,j,m,a==1);',b'g(f,&n,j,m,a==1?3:!!w);'),
    ('shared promotion/tactical emitter',OLD_ADD,NEW_ADD),
    ('remove repeated board classifier',b'static int y(const za*p,Move m){return p->b[TO(m)]||(abs(p->b[FROM(m)])==1&&TO(m)==p->e);}',b''),
    ('SEE initial EP gain only',b'if(!p->b[yv]&&y(p,m))j=100;',b'if(!p->b[yv]&&!PROMO(m)&&(m&8))j=100;'),
    ('ordering tactical tier',b'm==tt?1000000:y(p,m)?',b'm==tt?1000000:m&8?'),
    ('ordering SEE eligibility',b'if(y(p,m)||PROMO(m))',b'if(m&8)'),
    ('QS and reduction tactical flag',b'yu=y(p,m)||PROMO(m)',b'yu=m&8'),
    ('correction quiet guard',b'!y(p,zj)&&!PROMO(zj)',b'!(zj&8)'),
]


def info(data):
    return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}


def transform_source(source):
    if info(source)!=INPUT:
        raise ValueError('exact qualified B5371 shipping source required')
    projected=re.sub(rb'[A-Za-z_][A-Za-z_0-9]*',lambda m:ROLES.get(m.group().decode(),m.group().decode()).encode(),READABLE_ADD)
    word=b'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_0123456789'
    projected=re.sub(rb'\s+',lambda m:b' ' if m.start() and m.end()<len(projected) and projected[m.start()-1] in word and projected[m.end()] in word else b'',projected).strip()
    if projected!=NEW_ADD:
        raise ValueError('readable emitter and physical role projection differ')
    patches=[]
    for label,old,new in PAIRS:
        if source.count(old)!=1:
            raise ValueError('one exact old span required: '+label)
        a=source.index(old)
        patches.append((a,a+len(old),label,old,new))
    patches.sort()
    parts=[];gaps=[];rows=[];at=offset=0
    for a,b,label,old,new in patches:
        if a<at:raise ValueError('fixed source spans overlap')
        same=source[at:a];parts.extend((same,new));gaps.append(same);offset+=len(same)
        rows.append({'label':label,'old_start':a,'old_end':b,'new_start':offset,'new_end':offset+len(new),'old':info(old),'new':info(new)})
        offset+=len(new);at=b
    parts.append(source[at:]);gaps.append(source[at:]);result=b''.join(parts)
    inverse=result
    for row,patch in reversed(list(zip(rows,patches))):
        old,new=patch[3:];a,b=row['new_start'],row['new_end']
        if inverse[a:b]!=new:raise ValueError('fixed inverse span differs')
        inverse=inverse[:a]+old+inverse[b:]
    if inverse!=source or re.search(rb'\by\b',result):
        raise ValueError('inverse or removed classifier consumers differ')
    if OUTPUT is None or info(result)!=OUTPUT:
        raise ValueError('one source-prepared output required')
    return result,{'regions':rows,'full_inverse':True,'protected_complement':info(b''.join(gaps)),
        'readable_emitter_role_binding':True,'private_Move_ABI_changed':True,
        'tag_bit':3,'FROM_mask':119,'TO_PROMO_and_TT17bit_layout_unchanged':True,
        'ordering_policy_changed':'quiet promotions now receive the tactical capture base tier',
        'declared_legal_LVA_gain_unchanged_for_actual_tagged_gen_callers':True,
        'Q_recursive_untagged_moves_have_occupied_target':True,
        'inexact_negative_used_for_QS_pruning':False,
        'fullkey_TT_singular_exclusion_learning_pool_input_source_complement_unchanged':True,
        'old_raw_Move_identity_and_old_DEV_or_stack_evidence_inherited':False}
