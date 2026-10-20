"""Pure final B shipping recapture-promotion composition. Ordinary fixed literals only; no experiment/report/artifact/Clang input."""
import hashlib
import re

INPUT = {'bytes':11009,'sha256':'ce6a8b884009a4735ad5c9dbc948b444fe1af185ee7b40dd6335946625b92587'}
OUTPUT = {'bytes':10957,'sha256':'c3a86dd9d442356dde5150588c396caf86deb53401c09d15572db4fd5973bec5'}
OLD_Q = {'bytes':605,'sha256':'4eaab90935384a9157c15b324c8b8816c3e08d1500b23674df3bda87b62eb10e'}

# Only the internal fixed-target recapture promotion maximum is composed.
# Real h/make and all four initial generated promotions stay unchanged.
# Completed values are equal by target-recapture state convergence; checkpoint
# visit count/schedule changes, so old deadline/cancel timing is not inherited.
READABLE_RECAP = b'''int promoted=kind==1&&((target>>4)==0||(target>>4)==7)?5:0;
int score=see(worker,&child,MOVE(from,target,promoted));
if(score==SEE_INCOMPLETE)return SEE_INCOMPLETE;
'''
ROLES = {'promoted':'z','kind':'k','target':'yv','score':'a','see':'Q',
         'worker':'w','child':'t','from':'zJ'}
OLD = b'int f=k==1&&((yv>>4)==0||(yv>>4)==7);int a=-MATE;for(int z=f?2:0;z<=(f?5:0);z++){int j=Q(w,&t,MOVE(zJ,yv,z));if(j==SEE_INCOMPLETE)return SEE_INCOMPLETE;if(j>a)a=j;}'
NEW = b'int z=k==1&&((yv>>4)==0||(yv>>4)==7)?5:0;int a=Q(w,&t,MOVE(zJ,yv,z));if(a==SEE_INCOMPLETE)return SEE_INCOMPLETE;'
ORDERING = b'if(m&8){int s=Q(w,p,m);if(s!=SEE_INCOMPLETE)Y[i]+=s*32;}'


def info(data):
    return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}


def transform_source(source):
    if info(source)!=INPUT:
        raise ValueError('exact qualified B5279 input required')
    start=source.index(b'static int Q(')
    end=source.index(b'static int P(',start)
    if info(source[start:end])!=OLD_Q or source.count(OLD)!=1 or source.count(ORDERING)!=1:
        raise ValueError('actual Q/domain or unchanged ordering differs')
    projected=re.sub(rb'[A-Za-z_][A-Za-z_0-9]*',lambda m:ROLES.get(m.group().decode(),m.group().decode()).encode(),READABLE_RECAP)
    word=b'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_0123456789'
    projected=re.sub(rb'\s+',lambda m:b' ' if m.start() and m.end()<len(projected) and projected[m.start()-1] in word and projected[m.end()] in word else b'',projected).strip()
    if projected!=NEW:
        raise ValueError('readable recapture role projection differs')
    at=source.index(OLD)
    if not start<=at<at+len(OLD)<=end:
        raise ValueError('recapture span escaped actual Q')
    result=source[:at]+NEW+source[at+len(OLD):]
    if result[:at]+OLD+result[at+len(NEW):]!=source or info(result)!=OUTPUT:
        raise ValueError('fixed complete inverse/output differs')
    return result,{'old_start':at,'old_end':at+len(OLD),'new_end':at+len(NEW),
        'old_fragment':info(OLD),'new_fragment':info(NEW),
        'protected_complement':info(source[:at]+source[at+len(OLD):]),
        'full_inverse':True,'readable_role_binding':True,'one_fixed_span_only':True,
        'completed_legal_LVA_value_preserved':True,'full_minimax_equivalence':False,
        'internal_promotion_max':'queen weakly dominates all four only within fixed-target legal exchange',
        'all_four_initial_generated_promotions_unchanged':True,
        'real_make_pin_king_EP_coherent_board_unchanged':True,
        'numeric_ordering_unknown_guard_unchanged':True,'QS_SEE_pruning_disabled':True,
        'checkpoint_schedule_changed':True,'same_cancellation_visit_schedule':False,
        'no_cache_or_ABI_adapter':True,
        'fullkey_TT_singular_excludedlearning_protocol_pool_complement_exact':True,
        'old_runtime_strength_stack_evidence_inherited':False}
