"""Exact one-map replay only; declaration and expansion proof is source-pinned."""
import hashlib
FIXED=((169,4533,'ab','N'),(188,4993,'N','P'),(189,5001,'O','R'),(200,5796,'T','S'),(201,5968,'V','S'))
def sha(b):return hashlib.sha256(b).hexdigest()
def need(x,m):
 if not x:raise ValueError(m)
def transform(source,full,config,lexer):
 need((len(source),sha(source))==(9476,'71ae2a35736743103e72b2bb4738b8e71d2da9a78af44ad24b61c4157548ca27'),'current A source')
 rows=full['map'];need(tuple((r['ordinal'],r['declaration_offset'],r['old'],r['new']) for r in rows)==FIXED,'one literal declaration map')
 s=source.decode('ascii');tokens={a:(b,t) for a,b,t in lexer._identifier_spans(s)}
 observed=[(a,t) for a,(b,t) in tokens.items() if t in {'N','P','R','S'}];need(observed==[tuple(x) for x in full['alias_existing_token_inventory']],'exact alias namespace inventory')
 need(source.splitlines().count(b'#define PROMO(m) (((m)>>14)&7)')==1 and source.count(b'PROMO(ab)')==1 and source[5936:5945]==b'PROMO(ab)' and source[5942:5944]==b'ab','fixed untouched macro and sole physical argument')
 bridge=full['macro_argument_bridge'];need(bridge['expanded_reference_decl_ordinal']==169 and bridge['expanded_reference_decl_key']==['VAR_DECL','scope-input.c',4533] and bridge['physical_argument_start']==5942 and not bridge['tokenpaste_or_stringification'],'fixed expanded-to-spelling bridge')
 edits=full['edits'];expected=sorted((p,r['old'],r['new'],r['ordinal']) for r in rows for p in r['positions']);need([(e['start'],e['old'],e['new'],e['declaration_ordinal']) for e in edits]==expected,'declaration-bound occurrence ledger')
 result=source;delta=0;before=[];after=[];oldcursor=newcursor=0
 for e in edits:
  a,b=e['start'],e['end'];need(tokens.get(a)==(b,e['old']) and source[a:b]==e['old'].encode(),'physical token span');need(e['candidate_start']==a+delta and e['candidate_end']==a+delta+len(e['new']),'candidate offsets');delta+=len(e['new'])-len(e['old'])
 for e in reversed(edits):result=result[:e['start']]+e['new'].encode()+result[e['end']:]
 for e in edits:
  before.append(source[oldcursor:e['start']]);after.append(result[newcursor:e['candidate_start']]);oldcursor=e['end'];newcursor=e['candidate_end']
 before.append(source[oldcursor:]);after.append(result[newcursor:]);need(before==after,'protected complement')
 inverse=result
 for e in reversed(edits):
  a,b=e['candidate_start'],e['candidate_end'];need(inverse[a:b]==e['new'].encode(),'inverse span');inverse=inverse[:a]+e['old'].encode()+inverse[b:]
 need(inverse==source,'full inverse');need({'bytes':len(result),'sha256':sha(result)}==config['candidate_source'],'sole candidate identity')
 need([x for x in source.splitlines() if x.lstrip().startswith(b'#')]==[x for x in result.splitlines() if x.lstrip().startswith(b'#')],'all directives byte exact')
 return result,{'fixed_declarations':rows,'edits':edits,'exact_inverse':True,'protected_complement_exact':True,'protected_complement_bytes':sum(map(len,before)),'protected_complement_sha256':sha(b''.join(before)),'namespace_inventory_exact':True,'macro_definition_and_other_directives_exact':True,'single_macro_argument_bridge':bridge,'source_delta':len(result)-len(source),'AST_at_cost':0,'PP_at_cost':0}
