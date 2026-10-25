"""One fixed B shared forward geometry stage; pure ordinary byte inputs."""
import hashlib
import re

NEW_READABLE = b'''static void add(Move*,int*,int,int,int);
static uint64_t walk(const Board *p,Move *moves,int target,int side){
    int n=0;uint64_t result=0,sources=p->bb[side<0][0];
    while(sources){
        int i=__builtin_ctzll(sources),from=(i&7)+(i&56)*2;sources&=sources-1;
        int kind=abs(p->b[from]);
        if(moves&&kind==1){
            int to=from+side*16;
            if(!(to&0x88)&&!p->b[to]){
                add(moves,&n,from,to,1);
                if((from>>4)==(side>0?1:6)&&!p->b[to+side*16])add(moves,&n,from,to+side*16,0);
            }
        }
        int first=kind==1?(side>0?12:14):kind==2?0:kind==3?12:8;
        int last=kind==1?first+2:kind==2?8:kind==4?12:16;
        for(int i=first;i<last;i++){
            int step=steps[i];
            for(int to=from+step;!(to&0x88);to+=step){
                int piece=p->b[to];
                if(!moves&&to==target){result|=bit(from);break;}
                if(piece*side>0||(moves&&kind==1&&!piece&&to!=p->e))break;
                if(moves)add(moves,&n,from,to,kind==1);
                if(piece||kind<3||kind==6)break;
            }
        }
        if(moves&&kind==6){
            int home=side>0?4:116,shift=side>0?0:2;
            if(from==home&&!walk(p,0,home,-side)){
                if((p->c&(1<<shift))&&!p->b[home+1]&&!p->b[home+2]&&!walk(p,0,home+1,-side))add(moves,&n,from,home+2,0);
                if((p->c&(2<<shift))&&!p->b[home-1]&&!p->b[home-2]&&!p->b[home-3]&&!walk(p,0,home-1,-side))add(moves,&n,from,home-2,0);
            }
        }
    }
    return moves?n:result;
}
static uint64_t attackers(const Board *p,int target,int side){return walk(p,0,target,side);}
'''
ROLES = {'Board': 'za', 'add': 'g', 'steps': 'qo', 'bit': 'o', 'attackers': 'l', 'moves': 'f', 'target': 'sq', 'side': 's', 'result': 'r', 'sources': 'b', 'from': 'j', 'kind': 'a', 'to': 'm', 'first': 'q', 'last': 't', 'step': 'd', 'piece': 'w', 'home': 'x', 'shift': 'z'}
INPUT_PIN = {'bytes': 11702, 'sha256': 'd0b914e337f56623f7d1028381ccc4b012da02c4bc0681737a7a6a6e571274c7'}
OUTPUT_PIN = {'bytes': 11532, 'sha256': '3fca96ff1a913ed74edaed69d74794a433a9013e4a6cd88dc0e3dfe5e35d0b6f'}
COMPLEMENT_PIN = {'bytes': 10580, 'sha256': '12c3b6c7fa65012bf167d45ca65bebe0b76d5c546c4d7406a2cfe27e62b57313'}
REGIONS = [{'name': 'attackers→sharedwalk+l', 'old_start': 1854, 'old_end': 2249, 'new_start': 1854, 'new_end': 2754, 'old_literal': 'static uint64_t l(const za*p,int a,int f){int c=f<0;uint64_t j=0,m=p->bb[0][0]|p->bb[1][0];for(int d=-1;d<=1;d+=2){int q=a-f*16+d;if(!(q&0x88))j|=p->bb[c][1]&o(q);}for(int i=0;i<8;i++){int q=a+qo[i];if(!(q&0x88))j|=p->bb[c][2]&o(q);q=a+qo[i+8];if(!(q&0x88))j|=p->bb[c][6]&o(q);for(q=a+qo[i+8];!(q&0x88);q+=qo[i+8]){uint64_t b=o(q);if(m&b){j|=b&(p->bb[c][5]|p->bb[c][i<4?4:3]);break;}}}return j;}', 'new_literal': 'static void g(Move*,int*,int,int,int);static uint64_t walk(const za*p,Move*f,int sq,int s){int n=0;uint64_t r=0,b=p->bb[s<0][0];while(b){int i=__builtin_ctzll(b),j=(i&7)+(i&56)*2;b&=b-1;int a=abs(p->b[j]);if(f&&a==1){int m=j+s*16;if(!(m&0x88)&&!p->b[m]){g(f,&n,j,m,1);if((j>>4)==(s>0?1:6)&&!p->b[m+s*16])g(f,&n,j,m+s*16,0);}}int q=a==1?(s>0?12:14):a==2?0:a==3?12:8;int t=a==1?q+2:a==2?8:a==4?12:16;for(int i=q;i<t;i++){int d=qo[i];for(int m=j+d;!(m&0x88);m+=d){int w=p->b[m];if(!f&&m==sq){r|=o(j);break;}if(w*s>0||(f&&a==1&&!w&&m!=p->e))break;if(f)g(f,&n,j,m,a==1);if(w||a<3||a==6)break;}}if(f&&a==6){int x=s>0?4:116,z=s>0?0:2;if(j==x&&!walk(p,0,x,-s)){if((p->c&(1<<z))&&!p->b[x+1]&&!p->b[x+2]&&!walk(p,0,x+1,-s))g(f,&n,j,x+2,0);if((p->c&(2<<z))&&!p->b[x-1]&&!p->b[x-2]&&!p->b[x-3]&&!walk(p,0,x-1,-s))g(f,&n,j,x-2,0);}}}return f?n:r;}static uint64_t l(const za*p,int sq,int s){return walk(p,0,sq,s);}', 'old': {'bytes': 395, 'sha256': '85f87aef74ec067a46f890c2a38851189c11c00b254dc6e5a52fea6b94baedc4'}, 'new': {'bytes': 900, 'sha256': 'c1a6bb551df7cb35ec354bfacba84360a6b3636dcbe2c7814affd06827f17a1c'}}, {'name': 'gen→walkwrapper', 'old_start': 3453, 'old_end': 4180, 'new_start': 3958, 'new_end': 4010, 'old_literal': 'int gen(const za*p,Move*f){int s=p->s;int n=0;for(int j=0;j<128;j++){if(j&0x88){j+=7;continue;}int a=abs(p->b[j]);if(p->b[j]*s<=0)continue;if(a==1){int m=j+s*16;if(!(m&0x88)&&!p->b[m]){g(f,&n,j,m,1);if((j>>4)==(s>0?1:6)&&!p->b[m+s*16])g(f,&n,j,m+s*16,0);}}int q=a==1?(s>0?12:14):a==2?0:a==3?12:8;int t=a==1?q+2:a==2?8:a==4?12:16;for(int i=q;i<t;i++){int d=qo[i];for(int u=j+d;!(u&0x88);u+=d){int w=p->b[u];if(w*s>0||(a==1&&!w&&u!=p->e))break;g(f,&n,j,u,a==1);if(w||a<3||a==6)break;}}if(a==6){int x=s>0?4:116,z=s>0?0:2;if(j==x&&!attacked(p,x,-s)){if((p->c&(1<<z))&&!p->b[x+1]&&!p->b[x+2]&&!attacked(p,x+1,-s))g(f,&n,j,x+2,0);if((p->c&(2<<z))&&!p->b[x-1]&&!p->b[x-2]&&!p->b[x-3]&&!attacked(p,x-1,-s))g(f,&n,j,x-2,0);}}}return n;}', 'new_literal': 'int gen(const za*p,Move*f){return walk(p,f,0,p->s);}', 'old': {'bytes': 727, 'sha256': '969d01faed3ad3ec8031edb38ceddeb7ffa6153e16a8fb5875eab355f70bb965'}, 'new': {'bytes': 52, 'sha256': 'b0a27c409bddcc6674cfd83fb9086afc4ae681d1d7b9f6811de46a648c703117'}}]


def info(data):return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def need(value,message):
    if not value:raise ValueError(message)


def transform(source):
    need(type(source) is bytes and info(source)==INPUT_PIN,'one exact current B source required')
    need(info(NEW_READABLE)==READABLE_PIN,'fixed readable walker changed')
    need(b'"' not in NEW_READABLE and b"'" not in NEW_READABLE,'fixed walker has no opaque literals')
    projected=re.sub(rb'[A-Za-z_][A-Za-z_0-9]*',lambda m:ROLES.get(m.group().decode(),m.group().decode()).encode(),NEW_READABLE)
    word=b'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_0123456789'
    projected=re.sub(rb'\s+',lambda m:b' ' if m.start() and m.end()<len(projected) and projected[m.start()-1] in word and projected[m.end()] in word else b'',projected).strip()
    need(projected==REGIONS[0]['new_literal'].encode(),'fixed readable/physical role projection differs')
    need(b'walk' not in re.findall(rb'[A-Za-z_][A-Za-z_0-9]*',source),'new helper identifier is not fresh')
    output=[];retained=[];at=0;offset=0
    for region in REGIONS:
        a,b=region['old_start'],region['old_end'];old=region['old_literal'].encode();new=region['new_literal'].encode()
        need(a>=at and source[a:b]==old and source.count(old)==1 and info(old)==region['old'] and info(new)==region['new'],'fixed preimage/domain/disjointness differs')
        gap=source[at:a];retained.append(gap);output.extend((gap,new));offset+=len(gap)
        need((region['new_start'],region['new_end'])==(offset,offset+len(new)),'fixed new location differs')
        offset+=len(new);at=b
    output.append(source[at:]);retained.append(source[at:]);output=b''.join(output)
    need(info(b''.join(retained))==COMPLEMENT_PIN and info(output)==OUTPUT_PIN,'full candidate/all-gap complement differs')
    inverse=output
    for region in reversed(REGIONS):
        a,b=region['new_start'],region['new_end'];old=region['old_literal'].encode();new=region['new_literal'].encode()
        need(inverse[a:b]==new,'inverse preimage differs');inverse=inverse[:a]+old+inverse[b:]
    need(inverse==source,'full inverse differs')
    return output,{'two_regions_disjoint':True,'full_inverse':True,'readable_role_projection':True,
        'all_gap_complement':COMPLEMENT_PIN,'new_helper_identifier_fresh':True,
        'LVA_input_TT_singular_excludedlearning_protocol_source_complement_exact':True,
        'intended_full_geometric_mask_and_pseudo_list_order_equal':True,'query_work_policy_changed':True,
        'runtime_equivalence_or_strength_stack_qualified':False,'helper_executes_engine_or_compiler':False}

READABLE_PIN = {'bytes': 1651, 'sha256': '4b7a4d3c8d4966ff5fabea55e1c7aeda7a81bfa8f7e41590bb989ca58c3536e5'}
