"""Fixed full-F TT metadata byte: depth0..126 plus LOWER/UPPER only.

Move17/score16 and full-key coherent entry/lock remain intact. All production
writes have meta=2*(depth+1)+upper in2..255; empty0 cannot match. The probe
compares the complete high part after unchanged mate normalization. No mixed
old-format data is admitted: fresh startup calloc and private TT only. This
helper changes shipping full/reference, never canonical DEV or actual optional
policies. No AST/report/experiment/file is an input to its functions.
"""
import ast
import hashlib
INPUT=(8153, '62784180e34291403f2ad32a314bd83fb9de9167d820960ffe0099402879a8dc')
OUTPUT=(8117, '47d50421842f00b4a4f78ed20d71a06b714b20924b6e8b227f16ae03c7ecf1f9')
COMPLEMENT=(8045, '0b6a2a668afd108cfed932a29dca37e4c749cfc64862afbf73fe016f508b1d19')
EDITS=((4119, 4119, b'S u=(X)(F>>17),I=(F>>41)&3,J=(F>>33)&255;', b'S u=(X)(F>>17);'), (4188, 4162, b'if(f&&I&&J==a&&I!=2+(u>=d))H u;', b'if(f&&(F>>33)==a*2+2+(u<d))H u;'), (4882, 4856, b'I=C>=d?2:3;u=C;', b'u=C;'), (4950, 4913, b'((W)a<<33)|((W)I<<41)', b'((W)(a*2+2+(C<d))<<33)'))
def pin(b):return len(b),hashlib.sha256(b).hexdigest()
def rewrite(source,inverse=False):
 if type(source)is not bytes or pin(source)!=(OUTPUT if inverse else INPUT):raise ValueError('fixed TT source differs')
 parts=[];gaps=[];cursor=0
 for a,b,old,new in EDITS:
  at,expected,replacement=(b,new,old)if inverse else(a,old,new)
  if at<cursor or source[at:at+len(expected)]!=expected:raise ValueError('fixed TT role differs')
  gap=source[cursor:at];parts.extend((gap,replacement));gaps.append(gap);cursor=at+len(expected)
 parts.append(source[cursor:]);gaps.append(source[cursor:]);result=b''.join(parts)
 if pin(result)!=(INPUT if inverse else OUTPUT)or pin(b''.join(gaps))!=COMPLEMENT:raise ValueError('fixed TT output/complement differs')
 return result
def inverse(source):return rewrite(source,True)
def _forward(source):
 result=rewrite(source)
 if inverse(result)!=source:raise ValueError('complete TT inverse differs')
 return result

def restore_source(source):return inverse(source)
def transform_source(source):
    result=_forward(source)
    return result,{'family':'F','policy':'full-fixed2','stage':'TT-depth-bound-after-four-locals',
        'input_bytes':INPUT[0],'input_sha256':INPUT[1],'output_bytes':OUTPUT[0],'output_sha256':OUTPUT[1],
        'roles':4,'gaps':5,'full_inverse':True,'raw_delta':-36,'depth_range':[0,126],
        'writer_bounds':[2,3],'metadata_range':[2,255],'empty0_excluded':True,
        'Move17_score16_fullkey_lock_mate_witness_unchanged':True,
        'new_private_TT_encoding':True,'native_identity_claimed':False,
        'canonical_DEV_actual_optional_changed':False,'external_reads':0}

def source_literal(source,previous):
    restored=restore_source(source);expression,kind=previous(restored)
    if ast.literal_eval(expression)!=restored:raise ValueError('previous actual F literal differs')
    old=restored.decode('ascii');new=source.decode('ascii')
    if expression.count(old)!=1:raise ValueError('fixed raw literal interior differs')
    result=expression.replace(old,new,1)
    if result.count(new)!=1 or result.replace(new,old,1)!=expression or ast.literal_eval(result)!=source:
        raise ValueError('fixed F literal inverse/restoration differs')
    return result,kind
