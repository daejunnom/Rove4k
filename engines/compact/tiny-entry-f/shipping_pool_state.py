"""One fixed full-F pool representation: per-worker completed-depth negative job token.
No IO or processes. Depth0..126 is published result; -1 is unclaimed currentjob.
Only worker B calls think i in the admitted standalone shipping TU. Main marks
-1 only underqj after k() proves pending0 and outputflush done. Worker claims0
underqj before unlocking/think; spurious wakes cannot repeat a consumed token.
Think loses only redundant depth0 reset; standalone direct-i consumers would
need to seed0, a private-consumer domain difference. qk/startup/result/qm/joins
and all search/TT/learning/protocol bodies otherwise remain protected.
"""
import ast
import hashlib
INPUT=(8117, '47d50421842f00b4a4f78ed20d71a06b714b20924b6e8b227f16ae03c7ecf1f9')
OUTPUT=(8094, '543b6469c4f5ec616cde0e5113fa15c1419651a414717b9e25c498044369a79e')
EDITS=((4972, 4972, b'w->e=0;w->b=0;w->c=0;', b'w->e=0;w->c=0;'), (5570, 5563, b'static unsigned qd;', b''), (6095, 6069, b'zc*w=p;unsigned a=0;pthread_mutex_lock', b'zc*w=p;pthread_mutex_lock'), (6180, 6141, b'while(a==qd&&!qm)', b'while(w->b>=0&&!qm)'), (6224, 6187, b'if(qm)break;a=qd;', b'if(qm)break;w->b=0;'), (7300, 7265, b'qk=2;qd++;', b'qk=2;qr->b=qr[1].b=-1;'))
GAPS=((0, 0, 4972, 'bfd59f4883b1b593364028e3fc626eec275cf3073e1ddb40fafd21dd893f8eb1'), (4993, 4986, 577, '1915c08c8794e0f4cd10c74fe009670392c97145cf26d13f30b98bff1a5906ef'), (5589, 5563, 506, 'fbdd2ac5d960741ff80d8b8cfff7f49af9bf5c862175860d58eacb114cb3207d'), (6133, 6094, 47, 'c344bd1613bcafba9b7e5dc4ae7614bd9232b051dbcceb908f80ef72a482602b'), (6197, 6160, 27, 'd56ba43a13f97f370b215106d2630e1e04735d67b5e1946446188537c7799f97'), (6241, 6206, 1059, '91e988f62dec1b888ef7d260b30372bd1642936061bf5362600608308d88c724'), (7310, 7287, 807, '46ca106f14b810ab1dec5ac5c1d684d0a7ae6acf38138acf5dba1566824f9c25'))

def transform(source):
    if type(source)is not bytes or(len(source),hashlib.sha256(source).hexdigest())!=INPUT:raise ValueError('fixed F input')
    out=source
    for a,b,old,new in reversed(EDITS):
        if source[a:a+len(old)]!=old:raise ValueError('fixed pool role')
        out=out[:a]+new+out[a+len(old):]
    inverse=out
    for a,b,old,new in reversed(EDITS):
        if out[b:b+len(new)]!=new:raise ValueError('pool output role')
        inverse=inverse[:b]+old+inverse[b+len(new):]
    if inverse!=source or(len(out),hashlib.sha256(out).hexdigest())!=OUTPUT:raise ValueError('pool full inverse')
    for a,b,n,h in GAPS:
        if source[a:a+n]!=out[b:b+n]or hashlib.sha256(source[a:a+n]).hexdigest()!=h:raise ValueError('pool protected gap')
    return out

def restore_source(source):
    if type(source)is not bytes or(len(source),hashlib.sha256(source).hexdigest())!=OUTPUT:raise ValueError('fixed pool output required')
    result=source
    for a,b,old,new in reversed(EDITS):
        if result[b:b+len(new)]!=new:raise ValueError('fixed inverse pool role')
        result=result[:b]+old+result[b+len(new):]
    if (len(result),hashlib.sha256(result).hexdigest())!=INPUT or transform(result)!=source:raise ValueError('pool complete inverse differs')
    return result

def transform_source(source):
    result=transform(source)
    if restore_source(result)!=source:raise ValueError('pool full inverse differs')
    return result,{'family':'F','policy':'full-fixed2','stage':'worker-depth-token-after-TT-metadata',
        'input_bytes':INPUT[0],'input_sha256':INPUT[1],'output_bytes':OUTPUT[0],'output_sha256':OUTPUT[1],
        'roles':6,'protected_gaps':7,'full_inverse':True,'raw_delta':-23,
        'actual_i_caller_domain':'unique shipping B; claim0 underqj before i; direct-i fixture must seed0',
        'job_token':'worker.b -1 unclaimed,0 claimed,1..126 completed; job marks all underqj afterwait',
        'qk_startup_flush_join_quit_guards_retained':True,'native_identity_claimed':False,
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
