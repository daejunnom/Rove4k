"""One literal qA expression stage after unchanged ordinary shipping policies."""
import hashlib
import re

def sha(data):return hashlib.sha256(data).hexdigest()
def need(value,message):
    if not value:raise ValueError(message)
def logical(data):return data.replace(b'\\\r\n',b'').replace(b'\\\n',b'')

def transform(source,*,family,recipe,lexer,readable):
    need(isinstance(source,bytes)and isinstance(readable,bytes),'immutable source bytes required')
    expected=recipe['families'][family]['macro_input'];name=b'qA'
    expression=b'atomic_load_explicit(&qp,memory_order_relaxed)'
    definition=b'#define qA '+expression+b'\n'
    need(recipe['macro_name']=='qA'and recipe['expression'].encode()==expression and
         recipe['definition'].encode()==definition and len(definition)==58,'fixed macro drift')
    need(len(source)==expected['shipping_bytes']and sha(source)==expected['shipping_sha256'],'unknown final shipping input')
    for raw in(source,readable):
        need(not re.search(rb'\bqA\b',raw+logical(raw)),'qA not fresh in owned source')
    spans=list(lexer._identifier_spans(source.decode()))
    positions=[m.start()for m in re.finditer(re.escape(expression),source)]
    need(positions==recipe['families'][family]['offsets']and len(positions)==expected['all_replacements'],
         'literal expression positions/count differ')
    starts={a:t for a,b,t in spans}
    need(all(starts.get(p)=='atomic_load_explicit'for p in positions),'non-code replacement attempted')
    includes=list(re.finditer(rb'(?m)^\s*#\s*include[^\n]*\n',source))
    need(includes and includes[-1].end()==211==recipe['insert_after_include_offset'],'last include boundary drift')
    need(all(p>=211 for p in positions),'expression before include boundary')
    replaced=source.replace(expression,name)
    candidate=replaced[:211]+definition+replaced[211:]
    need(candidate.count(definition)==1,'new definition count differs')
    need(candidate.replace(definition,b'',1).replace(name,expression)==source,'non-macro source bytes changed')
    need(len(candidate)==expected['proposed_source_bytes']and sha(candidate)==expected['proposed_source_sha256'],
         'literal macro candidate identity differs')
    need(len(source)-len(candidate)==expected['net_source_saved_bytes'],'define-inclusive arithmetic differs')
    return candidate,{'family':family,'macro':'qA','expression':expression.decode(),
        'definition_bytes':58,'last_include_end_offset':211,'replacement_offsets':positions,
        'source_bytes':len(source),'source_sha256':sha(source),'candidate_bytes':len(candidate),
        'candidate_sha256':sha(candidate),'net_source_saved_bytes':len(source)-len(candidate),
        'all_nonstage_bytes_restored_by_exact_inverse':True,'old_policies_broadened':False,
        'native_or_runtime_acceptance':False}
