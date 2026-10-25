"""One fixed common terminal-witness rewrite; no C lexer, AST or new names."""
import hashlib


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def need(ok,message):
    if not ok:raise ValueError(message)


def transform(source,config):
    roles=config['roles'];pair=config['pair_text'].encode()
    marker=('static int '+roles['search']+'(').encode()
    old=(config['declarations']+config['evaluation']+config['terminal_old']).encode()
    new=(config['evaluation']+config['terminal_new']+config['declarations']).encode()
    need(source.count(pair)==1 and sha(pair)==config['pair_sha256'] and len(pair)==config['pair_bytes'],'fixed text/query definition pair')
    need(source.count(marker)==1 and source.count(old)==1 and sha(old)==config['old_region_sha256'] and sha(new)==config['new_region_sha256'],'fixed terminal/declaration role pair')
    search=source.index(marker);terminal=source.index(old);tail=source.index(pair)
    need(search<terminal<tail,'fixed function/terminal order')
    need(pair.startswith(('static void '+roles['text']+'(').encode()) and pair.count(('static Move '+roles['query']+'(').encode())==1,'definition role binding')
    need(source[tail+len(pair):].startswith(('static void '+roles['result']+'(').encode()),'query/result boundary')
    # Insert unchanged definitions, replace one terminal region, remove old pair.
    changes=((search,b'',pair),(terminal,old,new),(tail,pair,b''))
    pieces=[];gaps=[];records=[];cursor=0;size=0
    for pos,before,after in changes:
        need(pos>=cursor and source[pos:pos+len(before)]==before,'fixed span changed')
        gap=source[cursor:pos];pieces.extend((gap,after));gaps.append(gap);size+=len(gap)
        records.append({'old_offset':pos,'new_offset':size,'old_bytes':len(before),'new_bytes':len(after),'old_sha256':sha(before),'new_sha256':sha(after)})
        size+=len(after);cursor=pos+len(before)
    pieces.append(source[cursor:]);gaps.append(source[cursor:]);candidate=b''.join(pieces)
    inverse=[];newgaps=[];cursor=0
    for record,(_,before,after) in zip(records,changes):
        pos=record['new_offset'];need(candidate[pos:pos+len(after)]==after,'new span mismatch')
        gap=candidate[cursor:pos];inverse.extend((gap,before));newgaps.append(gap);cursor=pos+len(after)
    inverse.append(candidate[cursor:]);newgaps.append(candidate[cursor:])
    need(gaps==newgaps and b''.join(inverse)==source,'exact inverse/protected complement')
    for name,kind in ((roles['text'],'void'),(roles['query'],'Move'),(roles['search'],'int')):
        definition=('static '+kind+' '+name+'(').encode()
        need(candidate.count(definition)==source.count(definition)==1,'unique unchanged function definition '+name)
    need(candidate.index(pair)<candidate.index(marker) and candidate.count(new)==1,'new query/search terminal order')
    return candidate,{'source_saved_bytes':len(source)-len(candidate),'candidate_count':1,'roles':roles,'definitions_pair_sha256':sha(pair),'definitions_pair_bytes':len(pair),'definitions_relocated_unchanged':True,'exact_inverse':True,'protected_complement_bytes':sum(map(len,gaps)),'protected_complement_sha256':sha(b''.join(gaps)),'regions':records,'evaluation_literal_unchanged':True,'normal_declarations_relocated_unchanged':True,'new_prototypes':0,'AST':0,'PP':0,'new_names':0,'policy_change_intended':False,'Move0_basis':'generated legal from/to differ, so FROM|TO<<7|PROMO<<14 is nonzero; null parse returns0 only without a legal witness','F_null_query_formatting_retained':True}
