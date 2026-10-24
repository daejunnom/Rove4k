"""Fixed scalar TT-in-BSS placement; no HQ/DEV specialization."""
import hashlib
POLICY = 'scalar-loader-owned-static-TT-v1'
PREIMAGES={'native/tiny.h': '55a0a29dc2a5c378937443c4cc6c2067520a280793d7ecdd14a733941351e4ba', 'native/runtime.c': '2febf5acec5a3c74ab3a6dcb2fd2a1eb2ba44fab4d6892d9c354fcdcebfe4342'}
EDITS={
    'native/tiny.h':(
        ('TT_array_declaration',b'extern Entry *table;',b'extern Entry table[1u<<TT_BITS];'),
    ),
    'native/runtime.c':(
        ('TT_array_storage',b'Entry *table;',b'Entry table[1u<<TT_BITS];'),
        ('remove_TT_runtime_mmap',b'table=allocate(((size_t)1<<TT_BITS)*sizeof *table);if(!table)return 2;',b''),
    ),
}
def transform_sources(original,*,hq=0,dev=0):
    if hq not in (0,1) or dev not in (0,1):raise ValueError('fixed Boolean profile required')
    if hq or dev:return dict(original),{'applied':False,'identity':True}
    if set(original)!=set(PREIMAGES):raise ValueError('exact two source inputs required')
    digest=lambda b:hashlib.sha256(b).hexdigest()
    output={};proof={}
    for name,b in original.items():
        if digest(b)!=PREIMAGES[name]:raise ValueError('unknown TT source preimage: '+name)
        result=b;rows=[];gaps=[];cursor=0
        for role,old,new in EDITS[name]:
            if b.count(old)!=1 or result.count(old)!=1:raise ValueError('TT source role differs: '+role)
            at=b.index(old)
            if at<cursor:raise ValueError('TT source role order')
            gaps.append(b[cursor:at]);cursor=at+len(old)
            target=result.index(old);result=result[:target]+new+result[target+len(old):]
            rows.append({'role':role,'source_offset':at,'target_offset':target,'old_bytes':len(old),'new_bytes':len(new),'old_sha256':digest(old),'new_sha256':digest(new)})
        gaps.append(b[cursor:]);actual=[];cursor=0
        for row,(_,old,new) in zip(rows,EDITS[name]):
            at=row['target_offset'];actual.append(result[cursor:at]);cursor=at+len(new)
        actual.append(result[cursor:]);restored=result
        for row,(_,old,new) in reversed(list(zip(rows,EDITS[name]))):
            at=row['target_offset']
            if restored[at:at+len(new)]!=new:raise ValueError('TT source inverse span')
            restored=restored[:at]+old+restored[at+len(new):]
        if restored!=b or actual!=gaps:raise ValueError('TT source inverse/complement differs')
        output[name]=result;proof[name]={'old_bytes':len(b),'new_bytes':len(result),'old_sha256':digest(b),'new_sha256':digest(result),'full_inverse':True,'all_gaps_byteexact':True,'edits':rows,'gaps':[{'bytes':len(g),'sha256':digest(g)}for g in gaps]}
    return output,{'applied':True,'sources':proof}
