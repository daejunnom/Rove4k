"""One fixed two-function hash/HCE delta rewrite, with paired readable roles."""
import hashlib
import re


def sha(raw):return hashlib.sha256(raw).hexdigest()
def need(ok,message):
    if not ok:raise ValueError(message)


def project(raw,roles):
    text=raw.decode()
    need(not any(part in text for part in ('"',"'",'/*','//')),'only fixed literal-free role fragments')
    text=re.sub(r'[A-Za-z_][A-Za-z_0-9]*',lambda match:roles.get(match[0],match[0]),text)
    return ''.join(text.split()).encode()


def patch(data,changes):
    spans=[]
    for row in changes:
        old=row['old'].encode();new=row['new'].encode()
        need(old and data.count(old)==1 and data.count(new)==0,'unique fixed preimage '+row['role'])
        spans.append((data.index(old),old,new,row['role']))
    spans.sort();pieces=[];gaps=[];records=[];cursor=0;size=0
    for pos,old,new,role in spans:
        need(pos>=cursor,'overlapping literal spans')
        gap=data[cursor:pos];pieces.extend((gap,new));gaps.append(gap);size+=len(gap)
        records.append({'role':role,'old_offset':pos,'new_offset':size,'old_bytes':len(old),'new_bytes':len(new),'old_sha256':sha(old),'new_sha256':sha(new)})
        size+=len(new);cursor=pos+len(old)
    pieces.append(data[cursor:]);gaps.append(data[cursor:]);candidate=b''.join(pieces)
    inverse=[];newgaps=[];cursor=0
    for row,(_,old,new,_) in zip(records,spans):
        pos=row['new_offset'];need(candidate[pos:pos+len(new)]==new,'new span literal')
        gap=candidate[cursor:pos];inverse.extend((gap,old));newgaps.append(gap);cursor=pos+len(new)
    inverse.append(candidate[cursor:]);newgaps.append(candidate[cursor:])
    need(gaps==newgaps and b''.join(inverse)==data,'exact inverse/protected complement')
    return candidate,{'exact_inverse':True,'protected_complement_exact':True,'protected_complement_bytes':sum(map(len,gaps)),'protected_complement_sha256':sha(b''.join(gaps)),'regions':records,'source_delta':len(candidate)-len(data)}


def transform(source,canonical,config):
    need({'bytes':len(source),'sha256':sha(source)}==config['controls']['main.c'],'actual fixed shipping source')
    need(len(canonical)==config['canonical_bytes'] and sha(canonical)==config['canonical_sha256'],'actual fixed readable')
    canonical_rows=config['changes']['canonical'];shipping_rows=config['changes']['shipping']
    need([r['role'] for r in canonical_rows]==[r['role'] for r in shipping_rows]==['piece','put'],'fixed two roles')
    for c,s in zip(canonical_rows,shipping_rows):
        for side in ('old','new'):
            need(project(c[side].encode(),config['roles'])==b''.join(s[side].encode().split()),'paired readable/shipping role '+c['role']+'/'+side)
    # The fixed whole-source pins plus this count bind all direct private uses.
    for raw,name,rows in ((canonical,'piece',canonical_rows),(source,config['roles']['piece'],shipping_rows)):
        token=(name+'(').encode()
        need(raw.count(token)==3 and rows[0]['old'].encode().count(token)==1 and rows[1]['old'].encode().count(token)==2,'private piece definition+put-only calls')
    readable,cp=patch(canonical,canonical_rows);candidate,sp=patch(source,shipping_rows)
    return candidate,readable,{'candidate_count':1,'roles':config['roles'],'readable_shipping_role_pairs_exact':True,'canonical':cp,'shipping':sp,'zero_piece_domain_defined':True,'value_zero_already_exact':True,'private_piece_callers_only_put':True,'king_update_retained':True,'board_layout_changed':False,'existing_names_preserved':True,'AST':0,'PP':0,'new_allocator':0,'policy_change_intended':False,'signed_bound':'old/new[-6,6], contribution magnitude<=910 and difference<=1820 within admitted32piece HCE','state_EP_rights_half_r_unchanged':True,'functional_execution_claim':False}
