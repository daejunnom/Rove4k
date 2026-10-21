"""A evaluation reuse in canonical, profiled DEV and fixed shipping source.

Existing spelling stages retain their reviewed reference preimage. This pure
adapter proves its exact inverse, then returns the same cached expression
at the final shipping boundary. Runtime evidence is never a generation input.
"""
import hashlib

REFERENCE='71f9ff6ce1b7f555ad85c3bf49766381c0627315da94acf0c49eeee7bee4a734'
CANONICAL='a6aab57fffacc1900dbd9de133652d811d316b3823144ec2181c4f8dda581b6a'
BEFORE=(8995,'a52d492bcdfe623863153b9d5d651c6218fa1511e3253c3d6efe80b81c017101')
AFTER=(8987,'4fd5231ace3db9f7d8aca8c2e26871895905cd3e77cb38e4b41117bdca4f31d8')
OLD=b'int error=best-p->s*p->v;'
NEW=b'int error=best-evaluation;'

def _sha(raw):return hashlib.sha256(raw).hexdigest()
def _need(ok,message):
    if not ok:raise ValueError(message)
def _replace(source,old,new):
    _need(type(source) is bytes and source.count(old)==1,'sole evaluation expression required')
    result=source.replace(old,new)
    _need(result.count(new)==1 and result.replace(new,old)==source,'evaluation inverse differs')
    return result

def reference_readable(source):
    _need(type(source) is bytes and _sha(source)==CANONICAL,'current cached-evaluation canonical A required')
    reference=_replace(source,NEW,OLD)
    _need(_sha(reference)==REFERENCE,'reviewed spelling reference differs')
    return reference

def reuse_readable(source):
    result=_replace(source,OLD,NEW)
    return result,{'stage':'cached evaluation after readable DEV input profile',
        'input_sha256':_sha(source),'output_sha256':_sha(result),'exact_inverse':True,
        'correction_raw_evaluation_reused':True,'old_DEV_bytes_equal':False}

def transform_source(source):
    _need(type(source) is bytes and (len(source),_sha(source))==BEFORE,'fixed after-lazy-fallback A source required')
    old=b'int S=H-p->s*p->v;';new=b'int S=H-F;'
    result=_replace(source,old,new)
    _need((len(result),_sha(result))==AFTER,'fixed cached-evaluation shipping source differs')
    return result,{'stage':'A fixed shipping after lazy fallback','input_bytes':BEFORE[0],
        'input_sha256':BEFORE[1],'output_bytes':AFTER[0],'output_sha256':AFTER[1],
        'raw_source_delta':-8,'exact_inverse':True,'correction_raw_evaluation_reused':True,
        'canonical_uses_same_evaluation':True,'old_native_bytes_equal':False,
        'TT_LMR_learners_threads_profile_changed':False}
