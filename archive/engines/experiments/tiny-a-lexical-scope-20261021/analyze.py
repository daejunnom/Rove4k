"""One closed A search-function lexical-scope map; existing libclang only."""
import argparse,ctypes,hashlib,importlib.util,json
from pathlib import Path
SELECTED=((169,4533,'ab','N'),(188,4993,'N','P'),(189,5001,'O','R'),(200,5796,'T','S'),(201,5968,'V','S'))
SOURCE_SHA='71ae2a35736743103e72b2bb4738b8e71d2da9a78af44ad24b61c4157548ca27'
def sha(b):return hashlib.sha256(b).hexdigest()
def need(x,m):
 if not x:raise ValueError(m)
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main():
 c=argparse.ArgumentParser();c.add_argument('--source',type=Path,required=True);c.add_argument('--project-helper',type=Path,required=True);c.add_argument('--clang-site',type=Path,required=True);c.add_argument('--resource-dir',type=Path,required=True);c.add_argument('--out',type=Path,required=True);a=c.parse_args();need(a.out.is_absolute() and not a.out.exists(),'new absolute output required');a.out.mkdir()
 source=a.source.read_bytes();need(len(source)==9476 and sha(source)==SOURCE_SHA,'exact current A required');M=module('pinned_project_scope_analysis',a.project_helper);ci=M.clang_api(a.clang_site)
 lib=ctypes.CDLL(str(a.clang_site/'clang/native/libclang.so'))
 class CXString(ctypes.Structure):_fields_=[('data',ctypes.c_void_p),('flags',ctypes.c_uint)]
 lib.clang_getClangVersion.restype=CXString;lib.clang_getCString.argtypes=[CXString];lib.clang_getCString.restype=ctypes.c_char_p;lib.clang_disposeString.argtypes=[CXString];v=lib.clang_getClangVersion();version=lib.clang_getCString(v).decode();lib.clang_disposeString(v);need(version=='clang version 18.1.1','fixed existing tool version')
 tu,args,diagnostics=M.parse(ci,source,a.resource_dir,['-std=gnu17']);decls,ids,shapes,refs=M.snapshot(ci,tu);cursors=list(tu.cursor.walk_preorder());tokens=list(tu.get_tokens(extent=tu.cursor.extent));identifiers={t.extent.start.offset:t for t in tokens if M.main_location(t.location) and t.kind==ci.TokenKind.IDENTIFIER};macros={x.spelling for x in cursors if x.kind==ci.CursorKind.MACRO_DEFINITION};opaque=[(t.extent.start.offset,t.extent.end.offset) for t in tokens if M.main_location(t.location) and t.kind in (ci.TokenKind.COMMENT,ci.TokenKind.LITERAL)]+[(x.extent.start.offset,x.extent.end.offset) for x in cursors if x.kind==ci.CursorKind.MACRO_INSTANTIATION and M.main_location(x.location)]
 function=next(x for x in tu.cursor.get_children() if x.kind==ci.CursorKind.FUNCTION_DECL and x.spelling=='au' and x.is_definition());scope={}
 def walk(x,path):
  if x.kind in (ci.CursorKind.COMPOUND_STMT,ci.CursorKind.FOR_STMT):path=path+[(x.kind.name,x.extent.start.offset,x.extent.end.offset)]
  if x.kind in (ci.CursorKind.PARM_DECL,ci.CursorKind.VAR_DECL) and M.main_location(x.location):scope[M.key(x)]=path
  for ch in x.get_children():walk(ch,path)
 walk(function,[('FUNCTION_DECL',function.extent.start.offset,function.extent.end.offset)])
 protected={x.spelling for x in decls if x.kind not in (ci.CursorKind.VAR_DECL,ci.CursorKind.PARM_DECL) or x.semantic_parent.kind!=ci.CursorKind.FUNCTION_DECL or x.storage_class not in (ci.StorageClass.NONE,ci.StorageClass.AUTO,ci.StorageClass.REGISTER)}|macros|M.KEYWORDS
 macro_line=b'#define PROMO(m) (((m)>>14)&7)';invocation=b'PROMO(ab)';macro_start=5936;argument_start=5942
 need(source.splitlines().count(macro_line)==1 and source.count(invocation)==1 and source[macro_start:macro_start+len(invocation)]==invocation,'sole unchanged PROMO definition/invocation')
 defs=[x for x in cursors if x.kind==ci.CursorKind.MACRO_DEFINITION and M.main_location(x.location) and x.spelling=='PROMO'];uses=[x for x in cursors if x.kind==ci.CursorKind.MACRO_INSTANTIATION and M.main_location(x.location) and x.location.offset==macro_start and x.spelling=='PROMO']
 need(len(defs)==len(uses)==1 and M.key(uses[0].referenced)==M.key(defs[0]),'exact invocation references owned macro definition')
 macro_tokens=[t.spelling for t in defs[0].get_tokens()];need(macro_tokens==['PROMO','(','m',')','(','(','(','m',')','>>','14',')','&','7',')'] and not any(t in ('#','##') for t in macro_tokens),'pure fixed macro parameter expression')
 need(uses[0].extent.start.offset==macro_start and uses[0].extent.end.offset==macro_start+len(invocation),'fixed macro invocation extent')
 bridge=None;bridge_refs=0;rows=[];edits=[]
 for ordinal,offset,old,new in SELECTED:
  d=decls[ordinal];key=M.key(d);need(d.spelling==old and d.location.offset==offset and d.kind==ci.CursorKind.VAR_DECL and M.key(d.semantic_parent)==M.key(function),'exact closed declaration identity');need(d.linkage==ci.LinkageKind.NO_LINKAGE and d.storage_class in (ci.StorageClass.NONE,ci.StorageClass.AUTO,ci.StorageClass.REGISTER),'automatic storage');need(new not in protected,'global/type/member/macro namespace reserved');positions={offset}
  for x in function.walk_preorder():
   if not x.kind.is_declaration() and x.referenced is not None and M.key(x.referenced)==key:
    need(M.main_location(x.location),'nonphysical reference')
    if x.location.offset==macro_start:
     need(ordinal==169 and offset==4533 and old=='ab' and new=='N' and x.kind==ci.CursorKind.DECL_REF_EXPR and x.spelling=='ab','only sole fixed expanded bestmove reference admitted')
     need(scope[key][-1]==('COMPOUND_STMT',4366,6174) and 4533<argument_start<6174,'fixed argument lexical scope')
     bridge_refs+=1;positions.add(argument_start);bridge={'definition':macro_line.decode(),'macro_definition_key':M.key(defs[0]),'definition_tokens':macro_tokens,'invocation':invocation.decode(),'invocation_start':macro_start,'invocation_end':macro_start+len(invocation),'physical_argument_start':argument_start,'physical_argument_end':argument_start+2,'expanded_reference_location':x.location.offset,'expanded_reference_kind':x.kind.name,'expanded_reference_decl_key':M.key(x.referenced),'expanded_reference_decl_ordinal':ordinal,'source_scope':scope[key],'tokenpaste_or_stringification':False}
    else:positions.add(x.location.offset)
  for position in sorted(positions):
   t=identifiers.get(position);need(t is not None and t.spelling==old and source[position:t.extent.end.offset]==old.encode(),'exact physical identifier')
   if ordinal==169 and position==argument_start:
    need(bridge is not None and bridge_refs==1 and source[macro_start:position]==b'PROMO(' and source[position+2:macro_start+len(invocation)]==b')','only fixed physical argument exception')
    bridge['physical_token_kind']=t.kind.name;bridge['physical_token_cursor_kind']=t.cursor.kind.name;bridge['physical_token_annotation_key']=M.key(t.cursor.referenced or t.cursor)
   else:
    need(M.key(t.cursor.referenced or t.cursor)==key,'token owner');need(not M.intersect(position,position+len(old),opaque),'macro/opaque edit')
   edits.append({'start':position,'end':position+len(old),'old':old,'new':new,'declaration_ordinal':ordinal})
  rows.append({'ordinal':ordinal,'old':old,'new':new,'declaration_offset':offset,'type':d.type.spelling,'scopes':scope[key],'positions':sorted(positions)})
 need(bridge_refs==1 and bridge is not None,'exactly one fixed macro argument bridge')
 edits.sort(key=lambda x:x['start']);candidate=source;delta=0
 for e in edits:e['candidate_start']=e['start']+delta;e['candidate_end']=e['candidate_start']+len(e['new']);delta+=len(e['new'])-len(e['old'])
 for e in reversed(edits):candidate=candidate[:e['start']]+e['new'].encode()+candidate[e['end']:]
 need(M.inverse(candidate,edits)==source,'full inverse');before=[];after=[];o=n=0
 for e in edits:before.append(source[o:e['start']]);after.append(candidate[n:e['candidate_start']]);o=e['end'];n=e['candidate_end']
 before.append(source[o:]);after.append(candidate[n:]);need(before==after,'protected complement')
 tu2,args2,diagnostics2=M.parse(ci,candidate,a.resource_dir,['-std=gnu17']);_,_,shapes2,refs2=M.snapshot(ci,tu2);expected=list(shapes)
 for row in rows:
  old=expected[row['ordinal']];expected[row['ordinal']]=(old[0],row['new'],*old[2:])
 need(shapes2==expected and refs2==refs and args2==args,'entire reparse declaration/reference graph or parser config differs')
 # Explicit sibling-scope witnesses plus the freed outer N name.
 intervals={i:scope[M.key(decls[i])][-1][1:] for i in (188,189,196,198,199,200,201)}
 for p,q in ((188,196),(189,198),(199,200),(199,201),(200,201)):
  x,y=intervals[p],intervals[q];need(x[1]<=y[0] or y[1]<=x[0],'declared sharing scopes overlap')
 all_function_N=[x.location.offset for x in function.walk_preorder() if x.kind in (ci.CursorKind.VAR_DECL,ci.CursorKind.PARM_DECL) and x.spelling=='N'];need(all_function_N==[4993],'outer N freedom witness')
 proof={'complete':True,'stage':'one fixed closed lexical-scope map proof; no allocation/name search','source_bytes':len(source),'source_sha256':sha(source),'candidate_bytes':len(candidate),'candidate_sha256':sha(candidate),'source_delta':len(candidate)-len(source),'function':'au','fixed_map':rows,'edits':edits,'scope_independence_pairs':[(p,q,intervals[p],intervals[q]) for p,q in ((188,196),(189,198),(199,200),(199,201),(200,201))],'outer_N_original_declaration_offsets':all_function_N,'protected_namespace_names':sorted(protected),'alias_existing_token_inventory':[(p,t.spelling) for p,t in identifiers.items() if t.spelling in {'N','P','R','S'}],'ordinary_edit_token_owners_exact':True,'macro_argument_bridge':bridge,'macro_definition_literal_comment_edits':0,'other_macro_affected_tokens_admitted':0,'exact_inverse':True,'protected_complement_bytes':sum(map(len,before)),'protected_complement_sha256':sha(b''.join(before)),'protected_complement_exact':True,'all_declaration_shapes_except_fixed_names_equal':True,'entire_reference_graph_equal':True,'declarations_compared':len(shapes),'reference_edges_compared':len(refs),'parser_args':args,'diagnostics':diagnostics,'candidate_diagnostics':diagnostics2,'tool_version':version,'tool_paths':{'clang_site':str(a.clang_site),'resource_dir':str(a.resource_dir)},'project_helper':{'path':str(a.project_helper),'sha256':sha(a.project_helper.read_bytes())},'native_compiles':0,'codecs':0,'engine_runs':0}
 (a.out/'main.c').write_bytes(candidate);(a.out/'proof.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({k:proof[k] for k in ('complete','source_delta','candidate_bytes','candidate_sha256','entire_reference_graph_equal','all_declaration_shapes_except_fixed_names_equal','declarations_compared','reference_edges_compared','tool_version')}))
if __name__=='__main__':main()
