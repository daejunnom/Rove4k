"""Fixed full-F formatter sharing after the reviewed frequency spelling stage.

Only j's body changes. Its actual consumers own local char[6] buffers. Four
coordinate writes share shifts 0/4/7/11 and mask7; private Move bit3 is ignored.
Promotion suffix and NUL writes are unchanged. For m==0 the final bytes remain
0000/NUL and byte5 remains untouched. The loop index is0..3 and Y is unsigned.
The temporary space at s[4] has no observer in either actual caller. Old/new
actual j, u and y were compared in a bounded UBSan unit before promotion.

This pure byte replay owns no compiler, codec, AST, report, or external input.
Canonical readable/DEV and the optional material policy outputs bypass it.
"""
import ast
import hashlib

INPUT=(8020,'c56a7ca964643537d0389827e59f2f82995fbd5b598058408bec944c16bbf42f')
OUTPUT=(7979,'03fc7a4d8c3d99b1cdd633b47ef1939cb80247e72e0ef1acfbc5bc477155dd27')
AT=5555
OLD=b'''static void j(Y m,char*s){if(!m){strcpy(s,"0000");H;}s[0]='a'+(FROM(m)&7);s[1]='1'+(FROM(m)>>4);s[2]='a'+(TO(m)&7);s[3]='1'+(TO(m)>>4);s[4]="  nbrq"[PROMO(m)];s[4+!!PROMO(m)]=0;}'''
NEW=b'''static void j(Y m,char*s){for(S i=0;i<4;i++)s[i]=m?(i&1?'1':'a')+((m>>(i/2*7+(i&1)*4))&7):'0';s[4]="  nbrq"[PROMO(m)];s[4+!!PROMO(m)]=0;}'''
COMPLEMENT=(7842,'41f6cdc2a5fc8fa10659642faa666f15a51a0dfb6ef59ea0bfc06fcc87375b30')

def pin(data):return len(data),hashlib.sha256(data).hexdigest()

def rewrite(source,inverse=False):
    if type(source)is not bytes or pin(source)!=(OUTPUT if inverse else INPUT):
        raise ValueError('fixed full-F formatter input differs')
    old,new=(NEW,OLD)if inverse else(OLD,NEW)
    if source.count(old)!=1 or source[AT:AT+len(old)]!=old:
        raise ValueError('fixed full-F formatter role differs')
    complement=source[:AT]+source[AT+len(old):]
    if pin(complement)!=COMPLEMENT:raise ValueError('formatter protected complement differs')
    result=source[:AT]+new+source[AT+len(old):]
    if pin(result)!=(INPUT if inverse else OUTPUT):raise ValueError('formatter output differs')
    return result

def restore_source(source):return rewrite(source,True)

def transform_source(source):
    result=rewrite(source)
    if restore_source(result)!=source:raise ValueError('formatter complete inverse differs')
    return result,{'family':'F','policy':'full-fixed2','stage':'format-loop-after-frequency',
        'input_bytes':INPUT[0],'input_sha256':INPUT[1],'output_bytes':OUTPUT[0],'output_sha256':OUTPUT[1],
        'raw_delta':-41,'roles':1,'protected_gaps':2,'full_inverse':True,
        'actual_callers':'qb (previous u) and y; local char[6]',
        'Move17_capture_bit3_coordinates_promotion_zero_NUL_preserved':True,
        'canonical_DEV_actual_optional_changed':False,'native_identity_claimed':False,'external_reads':0}

def source_literal(source,previous):
    restored=restore_source(source);expression,kind=previous(restored)
    if ast.literal_eval(expression)!=restored:raise ValueError('previous actual F literal differs')
    old=restored.decode('ascii');new=source.decode('ascii')
    if expression.count(old)!=1:raise ValueError('fixed formatter literal interior differs')
    result=expression.replace(old,new,1)
    if result.count(new)!=1 or result.replace(new,old,1)!=expression or ast.literal_eval(result)!=source:
        raise ValueError('formatter literal inverse/restoration differs')
    return result,kind
