"""One fixed default A depth-jobflag pool form; no IO/processes.
Staticzero worker depth is idle; -1 published underqj is an unclaimed job.
The typed pointer a=p lets the unchanged w=0 startup/completion epilogue wait
on its own depth without dereferencing null w. w=a and depth0 claim happen
underqj before unchanged think C. Direct C users would need depth0 seeded;
shipping caller is only A->C(w,&ql). Existing default source only; rootpolicy
and DEV consumers are outside this transform. Jreturn/Lint/TT j/k protected.
"""
import hashlib
INPUT=(8461, 'a745a1e971034cd068ffeec4527b941b4607105cb229626753344cdc5187295c')
OUTPUT=(8443, '7e03415f6fd01167cb2bc50d02f7ee2fafbdd74a8862c4839c2cf8f87b7c5b3f')
EDITS=((5609, 5609, b'w->a5=0;w->C=0;w->l=0;', b'w->a5=0;w->l=0;'), (5913, 5906, b'static unsigned qd;', b''), (6443, 6417, b'ai*w=0;unsigned a=0;', b'ai*w=0,*a=p;'), (6543, 6509, b'while(a==qd&&!qm)', b'while(a->C>=0&&!qm)'), (6599, 6567, b'w=p;a=qd;', b'w=a;w->C=0;'), (7643, 7613, b'qk=2;qd++;', b'qk=2;qr->C=qr[1].C=-1;'))
GAPS=((0, 0, 5609, '50bdb119d311dbbdbb3f8dafbad27e4f90f5a5d2a80442fc3ee0ea9cc3daa753'), (5631, 5624, 282, '0640a16e3d5945fe33773f86cdf1f5d0bfe2fa0eaba85952e6041139609c8458'), (5932, 5906, 511, '3d3b119929a1987a7d016c29e69f5d1ae4e2c63ff0ee2ac220f7bc8f731dacc2'), (6463, 6429, 80, '9a3c8abac19f9e84b752bc16e75b56e763b8c273223c5e25b28de2fede40419e'), (6560, 6528, 39, '2db75265c2eb7155de557c4303b1197fc74ab4768a44e348bc6a26c01633116a'), (6608, 6578, 1035, '5dd2913f9b38704934d6044e14374b54b79b2eedae67c6e9c94868d4deed481d'), (7653, 7635, 808, '8b5fcc203356921c7a79e36066521723417f03bdc599ae2d5b9a669f5f73a228'))

def transform(source):
    if type(source)is not bytes or(len(source),hashlib.sha256(source).hexdigest())!=INPUT:raise ValueError('fixed A input')
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
    if type(source)is not bytes or(len(source),hashlib.sha256(source).hexdigest())!=OUTPUT:raise ValueError('fixed A pool output')
    result=source
    for a,b,old,new in reversed(EDITS):
        if source[b:b+len(new)]!=new:raise ValueError('A inverse pool role')
        result=result[:b]+old+result[b+len(new):]
    if (len(result),hashlib.sha256(result).hexdigest())!=INPUT or transform(result)!=source:raise ValueError('A pool inverse')
    return result

METADATA={'stage':'default-Loose-depth-jobflag-after-keyword-scope','family':'A',
    'input_bytes':INPUT[0],'input_sha256':INPUT[1],'output_bytes':OUTPUT[0],'output_sha256':OUTPUT[1],
    'roles':6,'protected_gaps':7,'raw_delta':-18,'full_inverse':True,
    'job_token':'C=-1 unclaimed; own worker claims0 under qj; 0..126 completed depth',
    'shipping_C_caller':'A->C(w,&ql) only; direct C consumers must seed depth0',
    'w_null_startup_sentinel_and_shared_epilogue_preserved':True,
    'qk_result_after_flush_partial_create_join_preserved':True,
    'canonical_DEV_root_policy_changes':False,'native_identity_claimed':False,
    'runtime_claimed_by_transform':False,'external_reads':0}

def transform_source(source):
    result=transform(source)
    if restore_source(result)!=source:raise ValueError('A pool complete inverse')
    return result,dict(METADATA)

def transform_literal(expression,previous):
    quote=chr(39)*3;oldquote=chr(34)*3
    if type(expression)is not str or not expression.startswith('br'+quote)or not expression.endswith(quote):raise ValueError('A pool raw-single literal required')
    old=restore_source(expression[5:-3].encode('ascii'));original=expression[:5]+old.decode('ascii')+expression[-3:]
    guarded=previous(original)
    if type(guarded)is not str or not guarded.startswith('br'+oldquote)or not guarded.endswith(oldquote)or guarded[5:-3].encode('ascii')!=old:raise ValueError('A actual keyword/output/condition/names literal guards differ')
    return guarded[:5]+transform(guarded[5:-3].encode('ascii')).decode('ascii')+guarded[-3:]
