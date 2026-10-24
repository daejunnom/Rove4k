"""Full-F valid-square successor after the existing integer-expression guard.

af and the shared T walker visit the same ordered 64 valid 0x88 squares.
For file0..6, (index+9)&~8 advances one; file7 advances nine, ending128.
The removed hole visits only performed loop-control checks. Actual af/T
early returns, continue paths, emitters and castling recursion retain their
ordered valid-square inputs. Fixed GNU17/Linux int indices stay in0..128.
No body, search, TT, learner, worker or protocol changes. Native identity,
timing and runtime equivalence are not established by this source proof.
Canonical/DEV/actual optional selected/F8 pre-name bypass this stage;
optional separate full_reference applies it explicitly. No external reads.
"""
import ast
import hashlib

INPUT=(8385,'acae5c84a77a22d52335aa905ac1b72117d7c74c3ac06e0fc86300c368a540c5')
OUTPUT=(8360,'b4e8f79615eb08c4d5dcb8db9e1cac76cecbef172f2096c64cafcebbc54cabf8')
EDITS=((1410,1410,b'for(S q=0;q<128;q++)if(!(q&0x88)){',b'for(S q=0;q<128;q=(q+9)&~8){'),
       (2491,2485,b'for(S j=0;j<128;j++){if(j&0x88){j+=7;continue;}',b'for(S j=0;j<128;j=(j+9)&~8){'))
GAPS=((0,0,1410,'3a9de5b5f28e28f457632785e0c0c556cca39288b2e8385c8728d2ae1a41bbe6'),
      (1444,1438,1047,'bef6b7f390c07b58353799ce7cc3f269480f7614158b3f596013df10a202626f'),
      (2538,2513,5847,'0dc9e88965c743a1d3065da3ff8f8fdb054695f7da7e19010687a8dd4a49c2cf'))


def _pin(raw):return len(raw),hashlib.sha256(raw).hexdigest()


def _need(ok,message):
    if not ok:raise ValueError(message)


def restore_source(result):
    _need(type(result)is bytes and _pin(result)==OUTPUT,'fixed F successor output differs')
    source=result
    for old_at,new_at,old,new in reversed(EDITS):
        _need(result[new_at:new_at+len(new)]==new,'fixed F successor output span differs')
        source=source[:new_at]+old+source[new_at+len(new):]
    _need(_pin(source)==INPUT,'fixed F successor restored integer output differs')
    for old_at,new_at,length,digest in GAPS:
        before=source[old_at:old_at+length];after=result[new_at:new_at+length]
        _need(before==after and hashlib.sha256(before).hexdigest()==digest,'F successor protected gap differs')
    return source


def transform_source(source):
    _need(type(source)is bytes and _pin(source)==INPUT,'fixed full-F post-integer successor input differs')
    result=source
    for old_at,new_at,old,new in reversed(EDITS):
        _need(source[old_at:old_at+len(old)]==old,'fixed F successor input span differs')
        result=result[:old_at]+new+result[old_at+len(old):]
    _need(restore_source(result)==source,'F successor full inverse differs')
    return result,{'family':'F','policy':'full-fixed2','stage':'valid-square-successor-after-integer-expressions',
        'input_bytes':INPUT[0],'input_sha256':INPUT[1],
        'output_bytes':OUTPUT[0],'output_sha256':OUTPUT[1],
        'source_regions':2,'protected_gaps':3,'protected_bytes':8304,'full_inverse':True,'raw_source_delta':-25,
        'ordered_valid_squares':64,'exit_index':128,'maximum_addition_result':128,
        'same_af_T_caller_domain_and_body_bytes':True,'native_identity_claimed':False,
        'canonical_DEV_actual_optional_F8_pre_name_changed':False,'external_reads':0}


def source_literal(source,previous):
    """Consume the previous literal path with its exact8385 input, then forward."""
    restored=restore_source(source)
    expression,kind=previous(restored)
    _need(ast.literal_eval(expression)==restored,'previous F literal did not restore exact integer source')
    old=restored.decode('ascii');new=source.decode('ascii')
    _need(expression.count(old)==1,'previous F raw source literal interior differs')
    result=expression.replace(old,new,1)
    _need(result.count(new)==1 and result.replace(new,old,1)==expression and ast.literal_eval(result)==source,
          'F successor literal inverse/restoration differs')
    return result,kind
