"""Remove an unconsumed published score in the fixed default A Loose pool.

This exact shipping closure only writes worker l at reset and completed
publication. Result x and the pool consume completed depth C and best H.
The h call and its arguments, all inner search locals and side effects remain
exact. Four spans and five gaps retain the remaining source and lifetime.
Canonical/DEV and root-hint/NORMAL/PALS have separate source/score contracts
and bypass this stage. H moves inside M; no native identity is claimed.
The module reads no files, reports, environment, compiler or runtime state.
"""
import ast
import hashlib

INPUT=(8355,'74235dccfe91308f60559595bc15cde36dc5eaba9f9a3ff314827b2e460b73bd')
OUTPUT=(8335,'2d077291e5615790206a43399d809b23aca5a2deec17623cd4c32f40fcb1ebf4')
EDITS=((591,591,b'L id,C,l;',b'L id,C;'),
       (5565,5563,b'w->l=0;',b''),
       (5642,5633,b'L l=h(w,p,C,-MATE,MATE,0,6,&H);',b'h(w,p,C,-MATE,MATE,0,6,&H);'),
       (5735,5722,b'w->l=l;',b''))
GAPS=((0,0,591,'6ee2bb5eceb0e6c356f4eafc645f69e6b461fabc46a94120503e1f951b01a7c5'),
      (600,598,4965,'70e9ac6c4ec64cc116f5e04cdddffcbc43a1094f65a1d2d800acde51170859b3'),
      (5572,5563,70,'bdd7c0e92864fa764567ba6cf06abdba6338951021f60a9c3af4b5f9cce86a63'),
      (5673,5660,62,'07ff756904cc41ae5a92bb286d54ada5b2fb479a88f77f4551d7676bea6fda36'),
      (5742,5722,2613,'b16f4b030ee037e8b725bd24d302062c861cc5174d838811ca20724eef02d548'))
BOOT_INPUT=(10325,'bf5166b17fd6ab727c17565ac1070d8058888df9062a566638a8deae64c1d36d')
BOOT_OUTPUT=(10305,'fb0e7c10dce6d4ce957e4c92e5bebbcf85b13bdcaf1cb034ed5d3d24771320f0')

def pin(data):return len(data),hashlib.sha256(data).hexdigest()

def restore_source(source):
    if type(source)is not bytes or pin(source)!=OUTPUT:raise ValueError('fixed default A dead-score inverse input')
    out=source
    for a,b,old,new in reversed(EDITS):
        if source[b:b+len(new)]!=new:raise ValueError('A dead-score inverse role')
        out=out[:b]+old+out[b+len(new):]
    if pin(out)!=INPUT:raise ValueError('A dead-score restored source')
    return out

def transform_source(source):
    if type(source)is not bytes or pin(source)!=INPUT:raise ValueError('fixed default A dead-score input')
    if source.count(b'->l')!=2:raise ValueError('A published-score closure differs')
    out=source
    for a,b,old,new in reversed(EDITS):
        if source[a:a+len(old)]!=old:raise ValueError('A dead-score role')
        out=out[:a]+new+out[a+len(old):]
    if pin(out)!=OUTPUT or b'->l' in out:raise ValueError('A dead-score output')
    for a,b,n,h in GAPS:
        if source[a:a+n]!=out[b:b+n] or pin(source[a:a+n])!=(n,h):raise ValueError('A dead-score protected gap')
    if restore_source(out)!=source:raise ValueError('A dead-score complete inverse')
    return out,{'family':'A','policy':'loose','stage':'dead-published-score-after-default-EP',
                'input_bytes':INPUT[0],'input_sha256':INPUT[1],
                'output_bytes':OUTPUT[0],'output_sha256':OUTPUT[1],
                'raw_delta':-20,'roles':4,'protected_gaps':5,'full_inverse':True,
                'closure':'only reset/commit write worker l; result/pool read completed depth C and best H',
                'search_h_body_arguments_TT_learners_unchanged':True,
                'completed_depth_best_stop_and_drain_order_unchanged':True,
                'canonical_DEV_root3_changed':False,'native_identity_claimed':False,'external_reads':0}

def transform_bootstrap(previous,*,source):
    baseline=restore_source(source)
    if type(previous)is not bytes or pin(previous)!=BOOT_INPUT:raise ValueError('actual repaired default A bootstrap differs')
    quote=b'"'*3;old=b'br'+quote+baseline+quote;new=b'br'+quote+source+quote
    if previous.count(old)!=1 or ast.literal_eval(old.decode())!=baseline or ast.literal_eval(new.decode())!=source:
        raise ValueError('A dead-score actual raw source literal differs')
    result=previous.replace(old,new,1)
    if result.count(new)!=1 or result.replace(new,old,1)!=previous or pin(result)!=BOOT_OUTPUT:
        raise ValueError('A dead-score bootstrap inverse/output differs')
    def calls(script,name):
        return [node for node in ast.walk(ast.parse(script)) if isinstance(node,ast.Call) and
                ((isinstance(node.func,ast.Name) and node.func.id==name) or
                 (isinstance(node.func,ast.Attribute) and node.func.attr==name))]
    views=calls(result,'memoryview')
    if len(views)!=1 or ast.literal_eval(views[0].args[0])!=source:raise ValueError('A repaired compiler stdin differs')
    before,after=calls(previous,'Popen'),calls(result,'Popen')
    if len(before)!=1 or len(after)!=1 or ast.dump(before[0])!=ast.dump(after[0]):
        raise ValueError('A compiler owner/argv changed')
    return result,{'stage':'default-dead-score-source-literal-after-actual-compiler-owner',
                   'input_bytes':BOOT_INPUT[0],'input_sha256':BOOT_INPUT[1],
                   'output_bytes':BOOT_OUTPUT[0],'output_sha256':BOOT_OUTPUT[1],
                   'previous_EP_frequency_pool_keyword_output_condition_names_readonly_and_compiler_owner_guards_consumed':True,
                   'outside_source_literal_unchanged':True,'full_inverse':True,
                   'compiler_resources_codec_changed':False,'external_reads':0}
