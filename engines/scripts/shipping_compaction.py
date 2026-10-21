"""Late shipping forms for B/C/E; DEV bypass belongs to the caller.

Startup clear is only admitted immediately after checked calloc before any
thread/input/TT access. Every atomic flag is still explicitly cleared. B/E
job fields reset unconditionally in worker think; direct preseeded-think
semantics change. B SEE rank predicate is equivalent for TO in 0..127.
"""
import hashlib

STAGE='fixed-shipping-job-startup-SEE-forms'
CASES = {'B': ((10702, 'e15c61670e2addc01fa66432c3066fabb7b01f509bd84d9baa1f2d45095d4790'), (10595, '036d9c1aaec37b68508ec76ea335e77775d486bf4141dd7d4e94698a6313e33b'), ('startup-plain-TT-zero-covered-by-checked-calloc', 'per-entry-atomic-flag-clear-retained', 'worker-owned-unconditional-job-reset', 'fixed-positive-TT18-casts', 'SEE-TO127-promotion-rank-equivalence'), ((4861, 4861, b'((yv>>4)==0||(yv>>4)==7)', b'!(yv+16&96)'), (7394, 7381, b'void i(zd*w,const za*p){w->z4=0;w->zB=0;w->yl=0;', b'void i(zd*w,const za*p){w->z4=0;w->zB=0;w->yl=0;w->zi=0;'), (8801, 8796, b'static void B(void){for(size_t i=0;i<((size_t)1<<18);i++){qq[i].zP=qq[i].zA=0;atomic_flag_clear(&qq[i].zY);}}', b'static void B(void){for(size_t i=0;i<(1<<18);i++)atomic_flag_clear(&qq[i].zY);}'), (9686, 9651, b'for(int i=0;i<2;i++){qr[i].zB=qr[i].yl=0;qr[i].zi=0;qr[i].z4=0;}', b''), (9895, 9796, b'qq=calloc((size_t)1<<18,sizeof*qq);', b'qq=calloc(1<<18,sizeof*qq);'))), 'C': ((10151, 'd9f1faf12264af8b16699ed7e2aeb2bea37363019d17586be1d62d638aa6692f'), (10123, '0eeee8fd2c976cd5a0221365e1765ad01714c68609183381ea19eb8f4b3118ff'), ('startup-plain-TT-zero-covered-by-checked-calloc', 'per-entry-atomic-flag-clear-retained'), ((8268, 8268, b'static void y(void){for(size_t i=0;i<(1<<18);i++){table[i].zP=table[i].zA=0;atomic_flag_clear(&table[i].zY);}}', b'static void y(void){for(size_t i=0;i<(1<<18);i++)atomic_flag_clear(&table[i].zY);}'),)), 'E': ((10581, 'ddefebddc717011f8652165925dde4a6e0518bb321eacce932ef9b1afa721929'), (10477, '1bf5ca54da0a0ae5ae7c96deabf3830bace04db821c56fd9759c35e317da7436'), ('startup-plain-TT-zero-covered-by-checked-calloc', 'per-entry-atomic-flag-clear-retained', 'worker-owned-unconditional-job-reset'), ((6932, 6932, b'void i(zd*w,const za*p){w->z4=0;w->zB=0;w->yl=0;', b'void i(zd*w,const za*p){w->z4=0;w->zB=0;w->yl=0;w->zi=0;'), (8512, 8520, b'static void y(void){for(size_t i=0;i<(1<<18);i++){table[i].zP=table[i].zA=0;atomic_flag_clear(&table[i].zY);}}', b'static void y(void){for(size_t i=0;i<(1<<18);i++)atomic_flag_clear(&table[i].zY);}'), (9449, 9429, b'for(int i=0;i<2;i++){workers[i].zB=workers[i].yl=0;workers[i].zi=0;workers[i].z4=0;}', b'')))}

def transform_source(source, *, family):
    """Replay fixed literal spans; never read cost artifacts or run build tools."""
    before, after, features, edits = CASES[family]
    if type(source) is not bytes or (len(source), hashlib.sha256(source).hexdigest()) != before:
        raise ValueError('late source replay input differs: ' + family)
    pieces=[]; gaps=[]; cursor=target_cursor=0
    for start,target,old,new in edits:
        if start<cursor or source[start:start+len(old)]!=old:
            raise ValueError('late source replay literal differs')
        gap=source[cursor:start]
        if target_cursor+len(gap)!=target:
            raise ValueError('late source replay target differs')
        pieces.extend((gap,new));gaps.append(gap)
        cursor=start+len(old);target_cursor=target+len(new)
    pieces.append(source[cursor:]);gaps.append(source[cursor:]);candidate=b''.join(pieces)
    if (len(candidate),hashlib.sha256(candidate).hexdigest())!=after:
        raise ValueError('late source replay output differs')
    inverse=candidate;new_gaps=[];cursor=0
    for start,target,old,new in edits:
        if candidate[target:target+len(new)]!=new:
            raise ValueError('late source replay candidate span differs')
        new_gaps.append(candidate[cursor:target]);cursor=target+len(new)
    new_gaps.append(candidate[cursor:])
    for start,target,old,new in reversed(edits):
        inverse=inverse[:target]+old+inverse[target+len(new):]
    if inverse!=source or gaps!=new_gaps:
        raise ValueError('late source replay inverse/complement differs')
    remainder=b''.join(gaps)
    return candidate,dict(family=family,stage=STAGE,input_bytes=before[0],input_sha256=before[1],
        output_bytes=after[0],output_sha256=after[1],features=list(features),literal_spans=len(edits),
        exact_inverse=True,complement_bytes=len(remainder),complement_sha256=hashlib.sha256(remainder).hexdigest(),
        external_reads=0,compiler_codec_engine_executed_by_transform=0)
