"""Fixed full-F QS standpat cutoff after lazy fallback; caller bypasses DEV.

The first successful legal make establishes B!=0 before the new break.
Terminal handling precedes it; final key/score/depth0/lower2/y0 TT publication
is unchanged. For Kfalse or C<beta the recursive/learner paths are unchanged.
Pure later make/sort queries are omitted, so timing and SMP interleavings may
differ. This helper performs no external reads or compiler/codec/engine work.
"""
import hashlib

INPUT=(8550,'a5ee66aac85b5681e255e880553b9602228946f36d0b0a8ad950fb5b1cea4f2f')
OUTPUT=(8559,'65ca88c60d29f87249aac7e43905af1420e868065701e93fb7bdacbbc560f4c7')
OFFSET=4841
OLD=b'if(K&&(!P||C>=d))continue;'
NEW=b'if(K&&C>=d)break;if(K&&!P)continue;'
GAPS=((4841,'2e788f94f0ce0d040bb6050b9494217c66c7af79c820c1eb32b6c37bde26229b'),
      (3683,'42166f524c71ebd7fca5bd43af8cf731f5415a0362b7be257f9d48c4bbd24ca1'))
COMPLEMENT=(8524,'f779cfbf0024e99b6039840f02fde2627b6d3a9bcceae15036384a0c3cc689fd')
OLD_U=(1203,'61337dd2b9060c6b61ed44c1ec82daa52c8f48138436bcd94aaef3cd060b506b')
NEW_U=(1212,'19517466683504a84254948fd339ec60175e7c4408e32192fc27dd660624a48e')
COMBINED_COST_INDEX_SHA256='e7ed0bcf358e527ff08a652d30648abcd8c84efdfcdd55e10219ab6fcddf3b77'
COMPONENT_FOCUSED_INDEX_SHA256='91fe05c91368c9fdfe63b423cdfbc539f58d43f1c123b04f5532bb83e40e6fc6'
COMPONENT_FOCUSED_RESULT_SHA256='6bdd9b7911e9a6b247bdbfd2a5b41b7904ac3684968ef156dd9ed5ac63697483'

def _pin(data):return len(data),hashlib.sha256(data).hexdigest()

def transform_source(source,family='F'):
    """Replay only the pinned lazy-full-F input; return C and audit metadata."""
    if family!='F' or type(source) is not bytes or _pin(source)!=INPUT:
        raise ValueError('fixed lazy-full-F QS cutoff input differs')
    prefix=source[:OFFSET];suffix=source[OFFSET+len(OLD):]
    if (source[OFFSET:OFFSET+len(OLD)]!=OLD or source.count(OLD)!=1
            or (_pin(prefix),_pin(suffix))!=GAPS):
        raise ValueError('fixed QS cutoff literal or protected gaps differ')
    result=prefix+NEW+suffix
    newgaps=(result[:OFFSET],result[OFFSET+len(NEW):])
    inverse=result[:OFFSET]+OLD+result[OFFSET+len(NEW):]
    if (_pin(result)!=OUTPUT or result.count(NEW)!=1
            or inverse!=source or newgaps!=(prefix,suffix)
            or _pin(prefix+suffix)!=COMPLEMENT):
        raise ValueError('fixed QS cutoff output/inverse/complement differs')
    def body(data):
        start=data.index(b'static S U(')
        return data[start:data.index(b'void i(',start)]
    if _pin(body(source))!=OLD_U or _pin(body(result))!=NEW_U:
        raise ValueError('fixed actual QS search body differs')
    return result,{
        'family':'F','stage':'quiet-QS-first-legal-standpat-cutoff-after-lazy-fallback',
        'input_bytes':INPUT[0],'input_sha256':INPUT[1],
        'output_bytes':OUTPUT[0],'output_sha256':OUTPUT[1],
        'raw_delta':9,'edits':1,'full_inverse':True,'all_gaps_equal':True,
        'protected_gaps':GAPS,'protected_complement':COMPLEMENT,
        'old_actual_U':OLD_U,'new_actual_U':NEW_U,
        'terminal_before_break_and_nonzero_legal_preserved':True,
        'final_full_key_depth_score_bound_witness_TT_store_unchanged':True,
        'claim_deadline_cancel_and_learning_sites_unchanged':True,
        'lazy_global_result_GO_regions_disjoint_after_QS':True,
        'combined_cost_index_sha256':COMBINED_COST_INDEX_SHA256,
        'component_focused_index_sha256':COMPONENT_FOCUSED_INDEX_SHA256,
        'component_focused_result_sha256':COMPONENT_FOCUSED_RESULT_SHA256,
        'measured_combined_whole_bytes':4479,
        'measured_whole_delta_to_lazy_only':1,
        'measured_whole_delta_to_maintained':-4,
        'component8_search_make_calls':(59087,18119),
        'component8_search_attack_calls':(65023,24055),
        'component8_raw_oracles_excluded':True,
        'combined_normal_or_manycore_proof_claimed_by_helper':False,
        'pure_query_work_order_and_timing_changed':True,
        'external_reads':0,'compiler_codec_engine_executed_by_transform':0,
    }