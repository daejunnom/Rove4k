"""One post-name full-F resource profile: workers8/TT18, no file IO."""
import hashlib
INPUT = (8538, '400ad454b0e3108814636bab4060f224ae4b2d28cdc7929c8c98590adb46c59d')
OUTPUT = (8538, 'ad02fbb83d8c1012ab09f52da68cb019f8b9669a0a1fa9fe1ccfc93b892158f1')
EDITS = ((560, 'worker_state_array', b'zc qr[2]', 554, b'zc qr[8]'), (5930, 'startup_ready_pending', b'static S qk=2,qm', 5918, b'static S qk=8,qm'), (6316, 'completed_result_depth_scan', b'for(S i=1;i<2;i++)if(qr[i].b', 6304, b'for(S i=1;i<8;i++)if(qr[i].b'), (7714, 'job_pending_publication', b'pthread_mutex_lock(&qj);qk=2;qd++', 7687, b'pthread_mutex_lock(&qj);qk=8;qd++'), (7801, 'thread_handle_array', b'pthread_t a[2]', 7789, b'pthread_t a[8]'), (7905, 'create_success_count_limit', b'for(;d<2;d++){qr[d].a=d;', 7898, b'for(;d<8;d++){qr[d].a=d;'))

def _pin(source):return len(source),hashlib.sha256(source).hexdigest()
def transform_source(source,workers=8,tt_bits=18,family='F'):
    if family!='F' or workers!=8 or tt_bits!=18 or type(source) is not bytes or _pin(source)!=INPUT:
        raise ValueError('only pinned full-F8538 path-only workers8/TT18 profile is admitted')
    result=bytearray(source);spans=[];gaps=[];cursor=0
    for at,role,anchor,start,replacement in EDITS:
        if source[start:start+len(anchor)]!=anchor or source.count(anchor)!=1 or source[at:at+1]!=b'2':
            raise ValueError('exact resource role/anchor changed: '+role)
        gap=source[cursor:at];gaps.append((cursor,len(gap),hashlib.sha256(gap).hexdigest()))
        result[at]=ord('8');spans.append({'offset':at,'role':role,'old':'2','new':'8','anchor':anchor.decode()});cursor=at+1
    gap=source[cursor:];gaps.append((cursor,len(gap),hashlib.sha256(gap).hexdigest()))
    result=bytes(result);inverse=bytearray(result)
    for at,*_ in EDITS:inverse[at]=ord('2')
    if _pin(result)!=OUTPUT or bytes(inverse)!=source or any(source[at:at+length]!=result[at:at+length] for at,length,_ in gaps):
        raise ValueError('profile output/inverse/protected complement changed')
    complement=b''.join(source[at:at+length] for at,length,_ in gaps)
    return result,{'input':INPUT,'output':OUTPUT,'workers':8,'TT_bits':18,'main_threads':1,'native_TIDs_if_all_creates_succeed':9,
        'edits':spans,'raw_delta':0,'full_inverse':True,'all_gaps_equal':True,'gaps':gaps,
        'complement':_pin(complement),'shutdown_uses_actual_created_count':True,'public_resource_options_added':0,
        'manycore_or_512_claim':False,'compiler_codec_PP_engine_runtime_calls':0}
