"""Fixed default A EP trial through actual make; no IO in generation.
The sole shipping caller has an initialized legal Board. Nonempty EP follows
pawn doublepush, half0, valid king cache and abs(HCE)<=29120. Trial15/17 with
PROMO0 keeps child.e=-1: nested D returns, maximum v/D nesting2. All child
fields initialize through the unchanged maker; provisional unsigned h/r are
discarded and only own-king legality escapes. Arbitrary poisoned HCE/high-half
Boards are not this private API. Canonical DEV and all root3 forms bypass.
"""
import hashlib
INPUT=(8397, '669a976fffd47c1643f9f371eb995bd78dd97691b39927d6ff9b7e90c7eaec61')
OUTPUT=(8355, '74235dccfe91308f60559595bc15cde36dc5eaba9f9a3ff314827b2e460b73bd')
OLD=b'static void D(E*p){if(p->e<0)J;for(L d=-1;d<=1;d+=2){L q=p->e-p->s*16+d;if(!(q&0x88)&&p->b[q]==p->s){E t=*p;t.b[q]=t.b[p->e-p->s*16]=0;t.b[p->e]=(int8_t)p->s;if(!c(&t,p->k[p->s<0],-p->s))J;}}p->e=-1;}'
DECL=b'static void D(E*);'
NEW=b'static void D(E*p){if(p->e<0)J;for(L d=-1;d<=1;d+=2){L q=p->e-p->s*16+d;E t;if(!(q&0x88)&&p->b[q]==p->s&&v(p,MOVE(q,p->e,0),&t))J;}p->e=-1;}'
A=1727
C=2428
GAPS=((0, 0, 1727, '25c794d0d39d55d5ce34e151af2071a084c2b899457b2a4adf89a62dbcce510e'), (1927, 1745, 501, 'ff5a7dc41258bb62187429208dd785720c831ba5ec3fba126a7f93615ed4a1a8'), (2428, 2386, 5969, '0029d31fd69cd58c427e0031c672a2fc856313df10b0f5e30637f99231d4c841'))
METADATA={'stage': 'default-Loose-EP-make-sharing-after-frequency', 'family': 'A', 'input_bytes': 8397, 'input_sha256': '669a976fffd47c1643f9f371eb995bd78dd97691b39927d6ff9b7e90c7eaec61', 'output_bytes': 8355, 'output_sha256': '74235dccfe91308f60559595bc15cde36dc5eaba9f9a3ff314827b2e460b73bd', 'roles': 2, 'protected_gaps': 3, 'raw_delta': -42, 'full_inverse': True, 'private_domain': 'initialized legal shipping Board; nonempty EP only after doublepush with half0 and valid bounded HCE/kings', 'scratch': 'new maker child fully initialized; provisional uint64 h/r discarded; boolean legality only', 'bounded_call_cycle': 'EP pawn displacement15/17 PROMO0 keeps child.e=-1; nested D returns; v/D nesting at most2', 'arbitrary_poisoned_or_highhalf_Board_equivalence': False, 'canonical_DEV_root3_changes': False, 'native_identity_claimed': False, 'runtime_claimed_by_transform': False, 'external_reads': 0}

def _pin(data):return len(data),hashlib.sha256(data).hexdigest()
def _need(ok,message):
    if not ok:raise ValueError(message)
def restore_source(candidate):
    _need(type(candidate)is bytes and _pin(candidate)==OUTPUT,'fixed A EP output')
    at=C-len(OLD)+len(DECL)
    _need(candidate[A:A+len(DECL)]==DECL and candidate[at:at+len(NEW)]==NEW,'fixed EP output roles')
    old=candidate[:A]+OLD+candidate[A+len(DECL):at]+candidate[at+len(NEW):]
    _need(_pin(old)==INPUT,'complete A EP inverse')
    return old
def transform_source(source):
    _need(type(source)is bytes and _pin(source)==INPUT,'fixed post-frequency A source')
    _need(source[A:A+len(OLD)]==OLD,'fixed old EP role')
    out=source[:A]+DECL+source[A+len(OLD):C]+NEW+source[C:]
    _need(_pin(out)==OUTPUT and restore_source(out)==source,'A EP forward/inverse')
    for old_at,new_at,size,digest in GAPS:
        left=source[old_at:old_at+size];right=out[new_at:new_at+size]
        _need(left==right and _pin(left)==(size,digest),'A EP protected gap')
    return out,dict(METADATA)
def transform_literal(expression,previous):
    single=chr(39)*3;double=chr(34)*3
    _need(type(expression)is str and expression[:5]=='br'+single and expression[-3:]==single,'fixed A EP raw-single literal')
    old=restore_source(expression[5:-3].encode('ascii'))
    guarded=previous(expression[:5]+old.decode('ascii')+expression[-3:])
    _need(type(guarded)is str and guarded[:5]=='br'+double and guarded[-3:]==double and guarded[5:-3].encode('ascii')==old,'actual A frequency/pool/keyword/output/condition/names guards differ')
    return guarded[:5]+transform_source(old)[0].decode('ascii')+guarded[-3:]
