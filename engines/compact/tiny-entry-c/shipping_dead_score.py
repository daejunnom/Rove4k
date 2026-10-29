"""Remove the unconsumed published score from the fixed full C shipping pool.

In this exact closure, think C writes worker l at reset and after a completed
search, but result x and the pool consume only completed depth C and best H.
The score returned by h is unused here; h itself, its arguments and search
locals remain exact. Four spans and five gaps retain the remaining source.
The two live workers keep their completed-depth publication and drain order.
Canonical/DEV bypass this shipping stage. This is not a general Worker API
equivalence: H moves within ai, so native identity is explicitly not claimed.
The module reads no files, reports, environment, compiler or runtime state.
"""
import ast
import hashlib

INPUT=(8992,'a82b3d17f132fba5e3949c9d2750ad2eeb5e2034db36d27daca2d8d3cdcd1329')
OUTPUT=(8970,'391944ca8e3fbe1c0064793232ad0664b8e282b812455c47d3047fcee9baec62')
EDITS=((517,517,b'int id,C,l;',b'int id,C;'),
       (6092,6090,b'w->l=0;',b''),
       (6171,6162,b'int l=h(w,p,C,-30000,30000,0,6,&H);',b'h(w,p,C,-30000,30000,0,6,&H);'),
       (6269,6254,b'w->l=l;',b''))
GAPS=((0,0,517,'c64cf98381f051c9874ac5d4a39304333fecb4cc65aba9310b48c74d422724f7'),
      (528,526,5564,'b3e68770e63b35dedefc8a12076f5117c68ae65a177554f8b14097825a047b34'),
      (6099,6090,72,'dd4fda2d1d599536fc39a148a29ba9362186357042d1ef55be9635b345678f1b'),
      (6206,6191,63,'89da0d039b0a3553c4eff04ba85fdd08348eb3b0c201e78211a407dd259e0a93'),
      (6276,6254,2716,'8ab822fd4755d91912635cb211623246ab30ae67697a0eb792020edd2509e7fa'))
BOOT_INPUT=(10969,'7614e2609b15ecac010f3dfbf3bc99807139d8fc3ff4c9e4dd9a138d856132e5')
BOOT_OUTPUT=(10947,'2f1dd8b4e6a12f0aa7f25705f63fea55c1775cc49c18b544ed5e0e211b2dc1b8')

def pin(data):return len(data),hashlib.sha256(data).hexdigest()

def restore_source(source):
    if type(source)is not bytes or pin(source)!=OUTPUT:raise ValueError('fixed C dead-score inverse input')
    out=source
    for a,b,old,new in reversed(EDITS):
        if source[b:b+len(new)]!=new:raise ValueError('C dead-score inverse role')
        out=out[:b]+old+out[b+len(new):]
    if pin(out)!=INPUT:raise ValueError('C dead-score restored source')
    return out

def transform_source(source):
    if type(source)is not bytes or pin(source)!=INPUT:raise ValueError('fixed C dead-score input')
    if source.count(b'->l')!=2:raise ValueError('C published-score closure differs')
    out=source
    for a,b,old,new in reversed(EDITS):
        if source[a:a+len(old)]!=old:raise ValueError('C dead-score role')
        out=out[:a]+new+out[a+len(old):]
    if pin(out)!=OUTPUT or b'->l' in out:raise ValueError('C dead-score output')
    for a,b,n,h in GAPS:
        if source[a:a+n]!=out[b:b+n] or pin(source[a:a+n])!=(n,h):raise ValueError('C dead-score protected gap')
    if restore_source(out)!=source:raise ValueError('C dead-score complete inverse')
    return out,{'family':'C','stage':'dead-published-score-after-four-constants',
                'input_bytes':INPUT[0],'input_sha256':INPUT[1],
                'output_bytes':OUTPUT[0],'output_sha256':OUTPUT[1],
                'raw_delta':-22,'roles':4,'protected_gaps':5,'full_inverse':True,
                'closure':'only reset/commit write worker l; result/pool read completed depth C and best H',
                'search_h_body_arguments_SIMD_TT_learners_unchanged':True,
                'completed_depth_best_stop_and_drain_order_unchanged':True,
                'canonical_DEV_changed':False,'native_identity_claimed':False,'external_reads':0}

def transform_bootstrap(previous,*,source):
    baseline=restore_source(source)
    if type(previous)is not bytes or pin(previous)!=BOOT_INPUT:raise ValueError('actual repaired C bootstrap differs')
    quote=b'"'*3;old=b'br'+quote+baseline+quote;new=b'br'+quote+source+quote
    if previous.count(old)!=1 or ast.literal_eval(old.decode())!=baseline or ast.literal_eval(new.decode())!=source:
        raise ValueError('C dead-score actual raw source literal differs')
    result=previous.replace(old,new,1)
    if result.count(new)!=1 or result.replace(new,old,1)!=previous or pin(result)!=BOOT_OUTPUT:
        raise ValueError('C dead-score bootstrap inverse/output differs')
    def calls(script,name):
        return [node for node in ast.walk(ast.parse(script)) if isinstance(node,ast.Call) and
                ((isinstance(node.func,ast.Name) and node.func.id==name) or
                 (isinstance(node.func,ast.Attribute) and node.func.attr==name))]
    views=calls(result,'memoryview')
    if len(views)!=1 or ast.literal_eval(views[0].args[0])!=source:raise ValueError('C repaired compiler stdin differs')
    before,after=calls(previous,'Popen'),calls(result,'Popen')
    if len(before)!=1 or len(after)!=1 or ast.dump(before[0])!=ast.dump(after[0]):
        raise ValueError('C compiler owner/argv changed')
    return result,{'stage':'dead-score-source-literal-after-actual-compiler-owner',
                   'input_bytes':BOOT_INPUT[0],'input_sha256':BOOT_INPUT[1],
                   'output_bytes':BOOT_OUTPUT[0],'output_sha256':BOOT_OUTPUT[1],
                   'previous_common_cross_pool_constants_and_compiler_owner_guards_consumed':True,
                   'outside_source_literal_unchanged':True,'full_inverse':True,
                   'compiler_resources_codec_changed':False,'external_reads':0}
