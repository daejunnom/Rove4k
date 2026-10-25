"""Exact literal source relation for one incremental-material representation."""
import hashlib


def sha(raw):return hashlib.sha256(raw).hexdigest()


def rewrite(raw,pairs):
    old=raw.decode('ascii');new=old;rows=[];cursor=0
    for pair in pairs:
        a,b=pair['old'],pair['new']
        if old.count(a)!=1:raise ValueError('fixed material preimage '+pair['role'])
        start=old.index(a)
        if start<cursor:raise ValueError('fixed material source order')
        cursor=start+len(a);new=new.replace(a,b,1)
        rows.append(dict(pair,old_offset=start,old_bytes=len(a),new_bytes=len(b)))
    before=[];after=[];oc=nc=0
    for row in rows:
        row['new_offset']=new.index(row['new'])
        before.append(old[oc:row['old_offset']]);after.append(new[nc:row['new_offset']])
        oc=row['old_offset']+row['old_bytes'];nc=row['new_offset']+row['new_bytes']
    before.append(old[oc:]);after.append(new[nc:])
    if before!=after:raise ValueError('material protected complement')
    inverse=new
    for row in reversed(rows):
        i=row['new_offset']
        if inverse[i:i+row['new_bytes']]!=row['new']:raise ValueError('material inverse span')
        inverse=inverse[:i]+row['old']+inverse[i+row['new_bytes']:]
    if inverse!=old:raise ValueError('material exact inverse')
    return new.encode('ascii'),dict(exact_inverse=True,protected_complement_exact=True,
        protected_complement_bytes=sum(map(len,before)),
        protected_complement_sha256=sha(''.join(before).encode()),spans=rows)


def transform(source,canonical,config):
    if (len(source),sha(source))!=(config['controls']['main.c']['bytes'],config['controls']['main.c']['sha256']):
        raise ValueError('fixed current shipping source differs')
    if (len(canonical),sha(canonical))!=(config['canonical']['bytes'],config['canonical']['sha256']):
        raise ValueError('fixed current readable differs')
    result,shipping=rewrite(source,config['changes']['shipping'])
    readable,relation=rewrite(canonical,config['changes']['readable'])
    for raw,key in [(result,'candidate_source'),(readable,'candidate_readable')]:
        if (len(raw),sha(raw))!=(config[key]['bytes'],config[key]['sha256']):raise ValueError('sole material candidate differs: '+key)
    return result,readable,{'shipping':shipping,'readable':relation,'DEV_generation':False}
