"""One exact project-owned PVS retry template; no alternate representation."""
import hashlib

SEARCH_SHA = '87bec413c4dcbccafd1b9c48e2a4ae878caae11747caf942f36a1036e88c7fb8'
PHASE_SHA = '0228587d1c602162ec8472c6d8f26431d4c721fee8654c9f39c51bcb6f6fd569'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def apply(search, phase):
    if sha(search) != SEARCH_SHA or sha(phase) != PHASE_SHA:
        raise ValueError('unknown fixed search/template input')
    begin_marker = b'        if(legal==1||depth<=0)score=-search('
    end_marker = b'        --w->length;'
    if search.count(begin_marker) != 1 or search.count(end_marker) != 1:
        raise ValueError('search replacement boundary differs')
    begin, end = search.index(begin_marker), search.index(end_marker)
    before = search[begin:end]
    if before.count(b'score=-search(w,&q,') != 4 or phase.count(b'score=-search(w,&q,') != 1:
        raise ValueError('expected exactly four old/one new child call sites')
    candidate = search[:begin] + phase + search[end:]
    if candidate[:begin] != search[:begin] or candidate[begin + len(phase):] != search[end:]:
        raise AssertionError('non-phase search body changed')
    return candidate, {
        'control_search_sha256': sha(search), 'candidate_search_sha256': sha(candidate),
        'phase_sha256': sha(phase), 'control_fragment_sha256': sha(before),
        'unchanged_prefix_suffix_sha256': sha(search[:begin] + search[end:]),
        'control_search_bytes': len(search), 'candidate_search_bytes': len(candidate),
        'control_fragment_bytes': len(before), 'candidate_fragment_bytes': len(phase),
        'child_call_sites': [4, 1], 'search_arity': 8,
        'key_push_pop_and_stopped_boundary_unchanged': True,
    }
