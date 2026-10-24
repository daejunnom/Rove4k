"""Pure E19 shipping source composition and exact source inverse.

The previous E chain remains the entry guard and the model authority. Actual
physical21 weights, Q, phase setter, S and R are bound from its passed bytes.
The selected Board/PVS/runtime definitions below are readable E-owned canonical
regions of the reviewed mailbox composition. The old E regions also remain as
canonical regeneration data for restore_source; neither direction opens files,
imports A or reads an experiment/native. This is a selected common implementation,
not a claim that the entire old E search has an identical execution trace.

The caller injects the repository's already pinned compact_source. Only ordinary
canonical regions are compacted; original model bodies are never reformatted.
Directives and line boundaries have separate literal ownership. Fixed region
pins and final whole-source pins make an unexpected minifier result fail closed.
"""
import hashlib

INPUT_PIN = (9866, '51e1db47b52d2ec12f0573911a923e9fe400c809ac225270a7821137e72122b7')
OUTPUT_PIN = (9074, 'e818bf407f95d0d028da939d2e57fbda81195dd64ee58d539e72ce768cf2e73f')
LOGICAL_MODEL_ID = 'e-hand-quadratic-19-1'
LOGICAL19_S16LE_SHA256 = 'a5bb11099b62489aca43a011619e15076b0637b2f2e460d89772162965cd5424'

_INPUT_MODELS = {'weights': (947, 97, '2970794446c70c1f2bb5b611a57ce68f04853124a06c9469da688fa6ff3c28bc'), 'center': (1044, 58, '7eb515dccd0be17035ae1090c3cc4c581095b1cab3273661dd719ecff878919e'), 'setter': (1193, 279, '482eb0310b1834927d930423577dfe6614214295622064d325a93f01bcaa9d46'), 'evaluate': (3686, 140, 'bde59e4cab8600f24b0c88618fcefb4f6ed89e4edefba30cdc5a6d93de18bfcf'), 'order': (3826, 344, '2cb4d3b55f6447b430c9040fc80201c0f1b70a87a0a7a657519d7147c6d4a9f8')}
_OUTPUT_MODELS = {'weights': (914, 81, 'eb95b2c446b4542dfebb1674cf1414e77bbb09f3befcf52d18fcf1357e466404'), 'center': (995, 58, '7eb515dccd0be17035ae1090c3cc4c581095b1cab3273661dd719ecff878919e'), 'evaluate': (1053, 119, 'c31795f50df445550c71bb28f21e01566002f233a829c7071e602eb839d0bab8'), 'order': (1172, 253, 'a5b6b8c04fc764837a905d17fb225948d0332cde4f3f636d1f3cb121c7154b56'), 'setter': (1515, 248, '3fd89f32e1ab0db06c381d435e81f24cf5620043f1d3abdf99ba40981bffb567')}
_BINDINGS = {'weights': [(13, 13, 'int16_t', 'X'), (21, 15, 'tiny_weights', 'qi')], 'center': [], 'setter': [(12, 12, 'H', 'b'), (14, 14, 'za', 'E'), (103, 102, 'tiny_weights', 'qi'), (128, 117, 'tiny_weights', 'qi'), (157, 136, 'tiny_weights', 'qi'), (208, 177, 'c', 'e'), (211, 180, 'I', 'W')], 'evaluate': [(19, 19, 'za', 'E'), (41, 40, 'tiny_weights', 'qi'), (82, 71, 'tiny_weights', 'qi')], 'order': [(11, 11, 'R', 'r'), (19, 19, 'za', 'E'), (24, 23, 'T', 'Y'), (123, 122, 'tiny_weights', 'qi'), (160, 149, 'tiny_weights', 'qi'), (177, 156, 'tiny_weights', 'qi'), (193, 162, 'tiny_weights', 'qi'), (210, 169, 'tiny_weights', 'qi'), (234, 183, 'tiny_weights', 'qi'), (252, 191, 'tiny_weights', 'qi'), (268, 197, 'tiny_weights', 'qi'), (296, 215, 'tiny_weights', 'qi')]}
_INPUT_GAPS = [(0, 645, '15599274f1c07ef5f39ba28b37cb6eb36d201eeea8445511c792e482b175ba66'), (749, 83, '5b8da6ef5410ef3e02e66d482952d75c06705a82010ddf6dc856cb33c431479c'), (947, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (1044, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (1102, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (1193, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (1472, 35, 'da5b2d8f28f3c3eee06f8e0b942cfb3e17a443951ac782d62599b4eca0a41073'), (1556, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (1770, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (1986, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (2065, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (2540, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (2693, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (3446, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (3490, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (3686, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (3826, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (4170, 1, '01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b'), (4405, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (4573, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (4624, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (4656, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (6528, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (6788, 162, '9fe290ee4b5560b5e93324abb2bfcc3886a4b34d9067f1eb9de0054c499da2ca'), (7133, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (7306, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (7469, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (7809, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (7960, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (8042, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (8094, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (8363, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (8475, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (8927, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (9865, 1, '01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b')]
_OUTPUT_GAPS = [(0, 615, 'abbd0dc8f46d9a8b6df2963aa11bc59f9b555193919e89c1ce726199e2a6f214'), (719, 80, 'c7c57103aa39a5db6562f4a263903bf9e09b7285fb544f9bdbddd492a110703d'), (914, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (995, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (1053, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (1172, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (1425, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (1515, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (1763, 34, '4c167455beee30974fafe04a5f515f16b640f99c118ec95158b8cd58b5b22509'), (1845, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (2059, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (2273, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (2352, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (2821, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (2953, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (3698, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (3741, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (3929, 1, '01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b'), (4158, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (4311, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (4356, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (4388, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (6125, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (6356, 140, '3ac6ec1392561e7067c82c132f3c07ab6c5d5e3488da3e695322d3b5fc0f4300'), (6679, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (6850, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (6985, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (7271, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (7398, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (7477, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (7529, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (7775, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (7887, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (8303, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (9073, 1, '01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b')]

# Canonical region name -> (presentation, readable C, compact size, SHA-256).
_CANONICAL = {
    'old-state-0-line-0': ('literal', r"""
""", 1, '01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b'),
    'old-state-0-line-1': ('literal', r"""#define _POSIX_C_SOURCE 200809L
""", 32, '11ea95c064d1e73e0d5455f1d458da179992d79a98c47145a42a7b23143ea0d9'),
    'old-state-0-line-2': ('literal', r"""#include<stdint.h>
""", 19, '584b1c0f6bfcab3462f5b9844577878d32d3294984b8acf8fa8c2f2abda5384a'),
    'old-state-0-line-3': ('literal', r"""#include<stdatomic.h>
""", 22, 'a740a5395dbfde8ac09071c7abf7d888a5fbf5e0aba601e90bc30b1462366d03'),
    'old-state-0-line-4': ('literal', r"""#include<pthread.h>
""", 20, 'b690be08ad0c8b9c01829574562cb7f1d2946aaec2de5f2582a853b2380a22fb'),
    'old-state-0-line-5': ('literal', r"""#include<stdlib.h>
""", 19, 'deea8bab8a65384fd9135e9551d500cb53697e9ed87d6a4b3299a0c3fe44c7aa'),
    'old-state-0-line-6': ('literal', r"""#include<stdio.h>
""", 18, '61003fe92a2bd78aae61845c10ca5e83ed1fbdb24e8a6a34f34b05ee93074794'),
    'old-state-0-line-7': ('literal', r"""#include<string.h>
""", 19, 'cbca550dcde6d7c9b3019139dc9d8e34ac0bfd76b99008441c2ef60264f5f1e9'),
    'old-state-0-line-8': ('literal', r"""#include<time.h>
""", 17, '6fb69b34661e4f3144eadd1b53bef029c8d6d2e1438e324eb8683b2400a30591'),
    'old-state-0-declarations-12': ('code', r"""typedef uint64_t I;
typedef unsigned T;
typedef struct{
    int8_t b[128];
    int s,c,e,k[2],zL,v,a;
    I h,r;
}
za;""", 99, 'a95f892badc015ca015401c0753b7fe0369e5fafe9550c340197c3a6c8403804'),
    'old-state-0-line-13': ('literal', r"""#define FROM(m) ((m)&119)
""", 26, '7004b6439eb6090f452e54dc659edca24d46eafc8c8990475be3b122dbaf281a'),
    'old-state-0-line-14': ('literal', r"""#define TO(m) (((m)>>7)&127)
""", 29, '25cc7985aee055405a1a857a91b9a49d3a343740fac739183da61d7d7bddea1b'),
    'old-state-0-line-15': ('literal', r"""#define PROMO(m) (((m)>>14)&7)
""", 31, '01cdc98c1d5367674370e727c58d60bf4ef270bd71dfc236ffba81a5490e091e'),
    'old-state-0-line-16': ('literal', r"""#define MOVE(f,t,p) ((T)(f)|((T)(t)<<7)|((T)(p)<<14))
""", 54, '19b5f02ab2bf106f7dcee2d40141f8354112cbfdae1eec40dbc79307bf4020b9'),
    'old-state-0-declarations-17': ('code', r"""typedef struct{
    atomic_flag zY;
    I zP,zA;
}
zb;
typedef struct{
    int id,zB,yl;
    T zi;
    I z4,zQ[4096+128];
    int16_t zM[128][128],zw[13][13],zx[1024];
}
zd;
zb*table;
zd workers[2];
atomic_int stopped;
I deadline,game_keys[4096];
int game_length;
za position;""", 235, '89cd8c3d947e43c15edb2c02a6d97869d0c0099ad267d75f5a0c84ed111fb9f4'),
    'old-monotonic-clock': ('code', r"""I k(void){
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC,&t);
    return(I)t.tv_sec*1000+t.tv_nsec/1000000;
}""", 104, '161e2c4f9ef21be25c256e82fdd4054c37ee455e1363f7abc1af83730a655ecb'),
    'old-state-1-declarations-0': ('code', r"""static const int steps[16]={
    33,31,18,14,-14,-18,-31,-33,1,-1,16,-16,17,15,-15,-17
}
;""", 83, '5b8da6ef5410ef3e02e66d482952d75c06705a82010ddf6dc856cb33c431479c'),
    'old-piece-key-mix': ('code', r"""I c(I x){
    x+=0x9e3779b97f4a7c15;
    x=(x^(x>>30))*0xbf58476d1ce4e5b9;
    x=(x^(x>>27))*0x94d049bb133111eb;
    return x^(x>>31);
}""", 115, 'b654087ce1d58e10dfe70943eb36cb0f29e79d6e55bde902772d1cb7f5e97206'),
    'old-metadata-key': ('code', r"""static I O(const za*p){
    return c(2048+p->c)^(p->s<0?c(2064):0)^(p->e<0?0:c(2065+(p->e&7)));
}""", 91, '410156029530a751c1b600938a6871bfeea00519500565af2e3df63a1a4dc583'),
    'old-state-6-declarations-0': ('code', r"""static int V(const za*,T*,int,int);""", 35, 'da5b2d8f28f3c3eee06f8e0b942cfb3e17a443951ac782d62599b4eca0a41073'),
    'old-attacked-square': ('code', r"""int b(const za*p,int a,int d){
    return V(p,0,a,d);
}""", 49, 'cd40071d8a779cf8a8ccdcebeb3a2c25e9f73f48d9cdfe6c8abc547d2b1209ba'),
    'old-dead-material': ('code', r"""int r(const za*p){
    int d=0;
    for(int q=0;q<128;q++)if(!(q&0x88)){
        int a=abs(p->b[q]);
        if(a==2){
            if(d)return 0;
            d=-1;
        }
        else if(a==3){
            if(d<0)return 0;
            d|=1<<((q+(q>>4))&1);
            if(d==3)return 0;
        }
        else if(a&&a<6)return 0;
    }
    return 1;
}""", 214, 'c96ac6dc497209509e0d99cb6e7e041c9c0187be858092d5adcc917f0652e115'),
    'old-legal-EP-normalizer': ('code', r"""static void A(za*p){
    if(p->e<0)return;
    for(int d=-1;d<=1;d+=2){
        int q=p->e-p->s*16+d;
        if(!(q&0x88)&&p->b[q]==p->s){
            za t=*p;
            t.b[q]=t.b[p->e-p->s*16]=0;
            t.b[p->e]=(int8_t)p->s;
            if(!b(&t,p->k[p->s<0],-p->s))return;
        }
    }
    p->e=-1;
}""", 216, 'aad36ded270443d3646575b630d6a2c1727185fdd83226c9010aff55402ffefe'),
    'old-castling-rights-mask': ('code', r"""static int K(int q){
    return q==4?3:q==116?12:q==0?2:q==7?1:q==112?8:q==119?4:0;
}""", 79, '72eb0da4392f03edbc649f97178310cbba96c49a1faf1835cf83caf3996ae2b2'),
    'old-board-make': ('code', r"""int e(const za*p,T m,za*t){
    int a=FROM(m),d=TO(m),f=PROMO(m),s=p->s;
    int v=p->b[a],i=p->b[d];
    if(abs(i)==6)return 0;
    *t=*p;
    t->h^=O(p);
    t->zL++;
    t->e=-1;
    if(abs(v)==1){
        t->zL=0;
        if(d==p->e&&!i)H(t,d-s*16,0);
        if(abs(d-a)==32)t->e=a+s*16;
        if(f)v=s*f;
    }
    if(i)t->zL=0;
    if(abs(v)==6&&abs(d-a)==2){
        int j=d>a?a+3:a-4,n=d>a?a+1:a-1;
        H(t,j,0);
        H(t,n,s*4);
    }
    H(t,a,0);
    H(t,d,v);
    t->c&=~(K(a)|K(d));
    t->s=-s;
    if(b(t,t->k[s<0],-s))return 0;
    A(t);
    t->h^=O(t);
    t->r=t->zL?((p->r<<1)|(p->r>>63))^t->h:t->h;
    return 1;
}""", 475, 'a4cfa2a1b5447539d050b5af6924bd155467f875d46e4e623f9c1de0507e7b53'),
    'old-move-emitter': ('code', r"""static void g(T*a,int*n,int zJ,int to,int d){
    int f=d>1&&!(to+16&96);
    for(int z=f?2:0;z<=(f?5:0);z++){
        if(*n>=512)abort();
        a[(*n)++]=MOVE(zJ,to,z)|(d&1)*8;
    }
}""", 153, '724841343eb29fefc68b3e712655abc901cdc1a921957c4655884cda680125ee'),
    'old-move-and-attack-walker': ('code', r"""static int V(const za*p,T*f,int j,int s){
    int n=0;
    for(int m=0;m<128;m++){
        if(m&0x88){
            m+=7;
            continue;
        }
        int a=abs(p->b[m]);
        if(p->b[m]*s<=0)continue;
        if(f&&a==1){
            int q=m+s*16;
            if(!(q&0x88)&&!p->b[q]){
                g(f,&n,m,q,2);
                if((m>>4)==(s>0?1:6)&&!p->b[q+s*16])g(f,&n,m,q+s*16,0);
            }
        }
        int t=a==1?(s>0?12:14):a==2?0:a==3?12:8;
        int u=a==1?t+2:a==2?8:a==4?12:16;
        for(int i=t;i<u;i++){
            int d=steps[i];
            for(int v=m+d;!(v&0x88);v+=d){
                int w=p->b[v];
                if(!f&&v==j)return 1;
                if(w*s>0||(f&&a==1&&!w&&v!=p->e))break;
                if(f)g(f,&n,m,v,a==1?3:!!w);
                if(w||a<3||a==6)break;
            }
        }
        if(f&&a==6){
            int x=s>0?4:116,z=s>0?0:2;
            if(m==x&&!b(p,x,-s)){
                if((p->c&(1<<z))&&!p->b[x+1]&&!p->b[x+2]&&!b(p,x+1,-s))g(f,&n,m,x+2,0);
                if((p->c&(2<<z))&&!p->b[x-1]&&!p->b[x-2]&&!p->b[x-3]&&!b(p,x-1,-s))g(f,&n,m,x-2,0);
            }
        }
    }
    return n;
}""", 753, '782000fbf6e5b50eeadb2609b5c97090a318a1b05a71f623fefcefb6ca9d48d0'),
    'old-pseudo-generation': ('code', r"""int h(const za*p,T*a){
    return V(p,a,0,p->s);
}""", 44, 'bc51ca6ae11c235b309697795e95adeaaf3ec7964066afc241cddb77be9a5835'),
    'old-initial-position': ('code', r"""void q(za*p){
    static const int back[8]={
        4,2,3,5,6,3,2,4
    }
    ;
    za t={
        0
    }
    ;
    t.s=1;
    t.c=15;
    t.e=-1;
    for(int f=0;f<8;f++){
        H(&t,f,back[f]);
        H(&t,16+f,1);
        H(&t,96+f,-1);
        H(&t,112+f,-back[f]);
    }
    t.h^=O(&t);
    t.r=t.h;
    *p=t;
}""", 196, '34b2012991455cacbe51572aba619cd03434d916a10781fa76c2788d9d545a12'),
    'old-locked-full-TT': ('code', r"""static I G(I a,I f){
    zb*e=table+(a&((1u<<18)-1));
    if(atomic_flag_test_and_set_explicit(&e->zY,memory_order_acquire))return 0;
    if(f)e->zP=a,e->zA=f;
    else f=e->zP==a?e->zA:0;
    atomic_flag_clear_explicit(&e->zY,memory_order_release);
    return f;
}""", 234, 'cac35a2a728fa689dae19a477e67a9ccd519c30d391aed479f233eae909b2639'),
    'old-search-poll': ('code', r"""static int o(zd*w){
    if(atomic_load_explicit(&stopped,memory_order_relaxed))return 0;
    if(!(w->z4&255)&&k()>=deadline){
        atomic_store(&stopped,1);
        return 0;
    }
    ++w->z4;
    return 1;
}""", 168, 'fb29840537b9273b75a9a029dbee408c0fd2a2a098e3d5d8827e178744f2b38a'),
    'old-bounded-history-update': ('code', r"""static void C(int16_t*a,int d){
    *a+=(d-*a*d/16384);
}""", 51, '34e153af9f1b5be724aa3aeaa52df09e3d2db9d18001785154933de9407c0f21'),
    'old-continuation-piece-index': ('code', r"""static int F(int p){
    return p+6;
}""", 32, '835c66317e101780a387333b6ca1eb11c23851a38bc8e4adbd1a43c55d0ae728'),
    'old-PVS-QS-search': ('code', r"""static int M(zd*w,const za*p,int a,int d,int f,int n,int yb,T*u){
    if(!o(w))return 0;
    int v=b(p,p->k[p->s<0],-p->s),x=p->zL>=100;
    int z=0,L=game_length+n;
    for(int i=L-3;i>=0&&i>=L-1-p->zL;i-=2)z+=w->zQ[i]==p->h;
    x|=z>=2||r(p);
    T W[512],zj=0;
    int X[512],Y=h(p,W),Z=0,z6=d,zi=-30000;
    int zF=p->s*S(p);
    x|=2*(n==128-1);
    I zP=p->h^c(p->r+(unsigned)p->zL),zA=x?0:G(zP,0);
    T tt=zA&131071;
    int yl=(int16_t)(zA>>17),zo=(zA>>41)&3,yz=(zA>>33)&255;
    if(yl>30000-128)yl-=n;
    if(yl< -30000+128)yl+=n;
    if(n&&zo&&yz>=(a>0?a:0)&&(zo==1||(zo==2&&yl>=f)||(zo==3&&yl<=d)))return yl;
    int ye=!x&&a<=0&&!v;
    if(ye){
        zi=zF;
        if(zi>d)d=zi;
    }
    for(int i=0;i<Y;i++){
        T m=W[i];
        int zJ=FROM(m),to=TO(m),pi=F(p->b[zJ]);
        X[i]=m==tt?1000000:m&8?500000:w->zM[zJ][to]+w->zw[yb][pi]+(int)((m*37u+w->id*19u)%17);
        if(PROMO(m))X[i]+=400000+PROMO(m)*1000;
        X[i]+=R(p,m);
    }
    for(int i=0;i<Y;i++){
        int j=i;
        for(int k=i+1;k<Y;k++)if(X[k]>X[j])j=k;
        T m=W[j];
        W[j]=W[i];
        X[j]=X[i];
        za q;
        if(!e(p,m,&q))continue;
        if(x){
            if(x==2)atomic_store(&stopped,1);
            return 0;
        }
        ++Z;
        int zJ=FROM(m),to=TO(m),yu=(m&8)||PROMO(m),pi=F(q.b[to]);
        if(ye&&(!yu||d>=f))continue;
        w->zQ[L]=q.h;
        if(Z==1||a<=0)yl=-M(w,&q,a-1,-f,-d,n+1,pi,0);
        else{
            int yg=a>=4&&Z>=4&&!yu&&!v&&!b(&q,q.k[q.s<0],-q.s);
            if(yg){
                yg=zF+w->zx[p->h&1023]/64<d+100;
            }
            yl=-M(w,&q,a-1-yg,-d-1,-d,n+1,pi,0);
            if(yg&&yl>d)yl=-M(w,&q,a-1,-d-1,-d,n+1,pi,0);
            if(yl>d&&yl<f)yl=-M(w,&q,a-1,-f,-d,n+1,pi,0);
        }
        if(atomic_load_explicit(&stopped,memory_order_relaxed))return 0;
        if(yl>zi){
            zi=yl;
            zj=m;
            if(u)*u=m;
        }
        if(yl>d)d=yl;
        if(d>=f){
            if(a>0&&!yu){
                int zn=a*a;
                C(&w->zM[zJ][to],zn);
                C(&w->zw[yb][pi],zn);
            }
            break;
        }
    }
    if(!Z)return v?-30000+n:0;
    zo=zi<=z6?3:zi>=f?2:1;
    if(a>0&&zo==1&&!v&&zj&&!(zj&8)&&!PROMO(zj)&&abs(zi)<30000-128){
        int zE=zi-zF;
        if(zE>256)zE=256;
        if(zE< -256)zE=-256;
        w->zx[p->h&1023]+=zE-w->zx[p->h&1023]/64;
    }
    yl=zi;
    if(yl>30000-128)yl+=n;
    if(yl< -30000+128)yl-=n;
    zA=zj|((I)(uint16_t)yl<<17)|((I)(a>0?a:0)<<33)|((I)zo<<41);
    G(zP,zA);
    return zi;
}""", 1872, '4e8a882fc6f34fda628f6a4785b0d2e59b40d2891c0b3935db92aeb1ca67c6ba'),
    'old-iterative-search': ('code', r"""void i(zd*w,const za*p){
    w->z4=0;
    w->zB=0;
    w->yl=0;
    w->zi=0;
    memcpy(w->zQ,game_keys,game_length*sizeof(I));
    for(int a=1;a<=128-2;a++){
        T d=w->zi;
        int f=M(w,p,a,-30000,30000,0,6,&d);
        if(atomic_load_explicit(&stopped,memory_order_relaxed))break;
        w->zi=d;
        w->yl=f;
        w->zB=a;
    }
}""", 260, '14900dd9282bcbc87b79f797de3042c790fea24c7273fbee60bd41e72eff26ba'),
    'old-state-23-declarations-0': ('code', r"""static pthread_mutex_t mutex=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t command=PTHREAD_COND_INITIALIZER;
static unsigned epoch;
static int pending=2,quitting;""", 162, '9fe290ee4b5560b5e93324abb2bfcc3886a4b34d9067f1eb9de0054c499da2ca'),
    'old-move-format': ('code', r"""static void P(T m,char*s){
    if(!m){
        strcpy(s,"0000");
        return;
    }
    s[0]='a'+(FROM(m)&7);
    s[1]='1'+(FROM(m)>>4);
    s[2]='a'+(TO(m)&7);
    s[3]='1'+(TO(m)>>4);
    s[4]="  nbrq"[PROMO(m)];
    s[4+!!PROMO(m)]=0;
}""", 183, '416f70e261fdc0a6ef3ca8b37efe1cae195e14d46aae9759c5a5a25c0e31c280'),
    'old-legal-move-parser': ('code', r"""static T E(const za*b,const char*s,za*c){
    T a[512];
    char d[6];
    int n=h(b,a);
    for(int i=0;i<n;i++){
        if(s){
            P(a[i],d);
            if(strcmp(s,d))continue;
        }
        if(e(b,a[i],c))return a[i];
    }
    return 0;
}""", 173, 'ac6d797e1762f8af7d6921620f62b71ec000db5b7f355b9a32c2d780464ecf6f'),
    'old-worker-result': ('code', r"""static void J(void){
    zd*w=workers+(workers[1].zB>workers[0].zB);
    za fb;
    T a=w->zi?w->zi:E(&position,0,&fb);
    char d[6];
    P(a,d);
    printf("bestmove %s\n",d);
    fflush(stdout);
}""", 163, '39aaf2b3ed7bd94babbbecddd2e3ab3b14bbeeb0a15937053db925ba72b5a287'),
    'old-persistent-worker': ('code', r"""static void*s(void*p){
    zd*w=0;
    unsigned a=0;
    pthread_mutex_lock(&mutex);
    for(;;){
        if(!--pending){
            if(w)J();
            pthread_cond_broadcast(&command);
        }
        while(a==epoch&&!quitting)pthread_cond_wait(&command,&mutex);
        if(quitting)break;
        w=p;
        a=epoch;
        pthread_mutex_unlock(&mutex);
        i(w,&position);
        pthread_mutex_lock(&mutex);
    }
    pthread_mutex_unlock(&mutex);
    return NULL;
}""", 340, 'c91a6dcfa90e1b3f99de16f5f5bedf9248cc471219050aee62ee44f83a8c7800'),
    'old-stop-and-drain': ('code', r"""static void U(void){
    atomic_store(&stopped,1);
    pthread_mutex_lock(&mutex);
    while(pending)pthread_cond_wait(&command,&mutex);
    pthread_mutex_unlock(&mutex);
}""", 151, 'f1a6415da208bdc378f25e5728ad35cf103179fe99d1dc719fa9627da61cd67f'),
    'old-clear-TT-flags': ('code', r"""static void y(void){
    for(size_t i=0;i<(1<<18);i++)atomic_flag_clear(&table[i].zY);
}""", 82, '6b78f48c89b1b782316b22e1d03892161c469d966b2391050338c20bdce7e5e1'),
    'old-command-token': ('code', r"""static char*nt(void){
    return strtok(NULL," \t\r\n");
}""", 52, '1549bfb96edd1bbfb9665b41166697bf5fd9f020ee49be26d5ad081bea2cd34c'),
    'old-position-command': ('code', r"""static void N(void){
    za b,c;
    I a[4096];
    int n=1;
    char*d=nt();
    if(!d||strcmp(d,"startpos"))return;
    q(&b);
    a[0]=b.h;
    d=nt();
    if(d){
        if(strcmp(d,"moves"))return;
        while((d=nt())){
            if(n==4096||!E(&b,d,&c))return;
            b=c;
            a[n++]=b.h;
        }
    }
    position=b;
    game_length=n;
    memcpy(game_keys,a,n*sizeof*a);
}""", 269, 'd68b713615657e4c039bb16a73aa7be6a745f77f55ca36fe1e164a42bd9bb4f9'),
    'old-time-number': ('code', r"""static I D(const char*s){
    char*e;
    if(!s||(unsigned)(*s-'0')>9)return 0;
    I n=strtoull(s,&e,10);
    return*e||n>>63?0:n;
}""", 112, '62b81b4d1b0a1bdd147c1bf7f247a586c3f16506bd022337300c06016d4028e7'),
    'old-go-command': ('code', r"""static void B(void){
    U();
    I a=-1,d=0,f=0;
    for(char*t=nt();t;t=nt()){
        if((*t=='w'||*t=='b')&&(!strcmp(t+1,"time")||!strcmp(t+1,"inc"))){
            I n=D(nt());
            if((*t=='w')==(position.s>0)){
                if(t[1]=='t')a=n;
                else d=n;
            }
        }
    }
    if(~a){
        f=a/30+(d>86400000?86400000:d)*3/4;
        if(f>a/5)f=a/5;
        if(!f)f=1;
    }
    else f=1000;
    deadline=k()+(f>86400000?86400000:f);
    atomic_store(&stopped,0);
    pthread_mutex_lock(&mutex);
    pending=2;
    epoch++;
    pthread_cond_broadcast(&command);
    pthread_mutex_unlock(&mutex);
}""", 452, 'ca477f66a34631db96477c73f1afca9e6346fbaca612520b5547775fc042864e'),
    'old-protocol-main': ('code', r"""int main(void){
    pthread_t a[2];
    int d=0,f=0;
    char j[32768];
    table=calloc(1<<18,sizeof*table);
    if(!table)return 2;
    y();
    q(&position);
    game_keys[0]=position.h;
    game_length=1;
    for(;d<2;d++){
        workers[d].id=d;
        if(pthread_create(a+d,NULL,s,workers+d)){
            f=2;
            goto shutdown;
        }
    }
    pthread_mutex_lock(&mutex);
    while(pending)pthread_cond_wait(&command,&mutex);
    pthread_mutex_unlock(&mutex);
    while(fgets(j,sizeof j,stdin)){
        if(!strchr(j,'\n')){
            int n=getchar();
            if(n!=EOF&&n!='\n'){
                do{
                    n=getchar();
                }
                while(n!=EOF&&n!='\n');
                continue;
            }
        }
        char*p=strtok(j," \t\r\n");
        if(!p)continue;
        if(!strcmp(p,"uci")){
            puts("uciok");
            fflush(stdout);
        }
        else if(!strcmp(p,"isready")){
            puts("readyok");
            fflush(stdout);
        }
        else if(!strcmp(p,"quit"))break;
        else if(!strcmp(p,"position")){
            U();
            N();
        }
        else if(!strcmp(p,"go"))B();
    }
    U();
    shutdown:pthread_mutex_lock(&mutex);
    quitting=1;
    pthread_cond_broadcast(&command);
    pthread_mutex_unlock(&mutex);
    for(int i=0;i<d;i++)if(pthread_join(a[i],NULL))f=2;
    free(table);
    return f;
}""", 938, '35da9619743aace61cceeeaaff220a99ed778a47caa58c0efb1dddecd3672270'),
    'selected-state-0-line-2': ('literal', r"""#include <stdint.h>
""", 20, 'dd1e65241020275e480c9f023566ad3d27cad42dfac5d4d1b9c176732d1eede5'),
    'selected-state-0-line-3': ('literal', r"""#include <stdatomic.h>
""", 23, 'c3eccdb5117e4d76c50ac3ced5b73fe8dda3c3583e47e85e5f898d60b3532e10'),
    'selected-state-0-line-4': ('literal', r"""#include <pthread.h>
""", 21, 'e6c0a1187a7165fe16302207e55480caf91c82e13efa73a49e920b520d7d8e49'),
    'selected-state-0-line-5': ('literal', r"""#include <stdlib.h>
""", 20, '0255684c4d6c1527072949458c753df8cd146612251d4ba3fe3b22a7e063cec1'),
    'selected-state-0-line-6': ('literal', r"""#include <stdio.h>
""", 19, 'd3139b187138b0a2b1fd9b889746cb293f2dfc1ec526153bb345b1617eca9ef4'),
    'selected-state-0-line-7': ('literal', r"""#include <string.h>
""", 20, '7c7dfb862fbd4063378bb2086e49db0857322c3de8cb9d570f175da1d253a682'),
    'selected-state-0-line-8': ('literal', r"""#include <time.h>
""", 18, 'b0435d5a79b71fa5959ff0c96fa0ff267156768e8d969da1e22f3c7c1a27e6f7'),
    'selected-state-0-declarations-12': ('code', r"""typedef uint64_t W;
typedef int16_t X;
typedef unsigned Y;
typedef struct{
    int8_t b[128];
    int s,c,e,k[2],aI,v,a;
    W h,r;
}
E;""", 116, 'b9f788a42be6d30538e6d6005d3c4f90cb205d1af430c71ac672713499e838a2'),
    'selected-state-0-line-16': ('literal', r"""#define MOVE(f,t,p) ((Y)(f)|((Y)(t)<<7)|((Y)(p)<<14))
""", 54, '1d3b6274e74c471732e79536b09eaaac5160a4305b7d5d39c2a235af4cf1e8e1'),
    'selected-state-0-declarations-17': ('code', r"""typedef struct{
    atomic_flag zN;
    W aT,U;
}
Z;
typedef struct{
    int id,C,l;
    Y H;
    W a5,aA[4096+128];
    X zC[128][128],an[13][13],ah[1024];
}
ai;
Z*qq;
ai qr[2];
atomic_int qp;
W qc,qg[4096];
int qh;
E ql;""", 181, 'a827192e7e468caa71d44fc6b3634bf73297bcde5f2588ab8911f4072e613d3b'),
    'selected-monotonic-clock': ('code', r"""W u(void){
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC,&t);
    return(W)t.tv_sec*1000+t.tv_nsec/1000000;
}""", 104, 'b91a993ad0e2e1bbe9dbfd32257bb6709a7f2139253070fa8551f99840ba3bef'),
    'selected-state-1-declarations-0': ('code', r"""static const int qo[16]={
    33,31,18,14,-14,-18,-31,-33,1,-1,16,-16,17,15,-15,-17
}
;""", 80, 'c7c57103aa39a5db6562f4a263903bf9e09b7285fb544f9bdbddd492a110703d'),
    'selected-piece-key-mix': ('code', r"""W e(W x){
    x+=0x9e3779b97f4a7c15;
    x=(x^(x>>30))*0xbf58476d1ce4e5b9;
    x=(x^(x>>27))*0x94d049bb133111eb;
    return x^(x>>31);
}""", 115, '38a406226094526d05f2c5c14ecc0e5536171a9bae30e19a64e0264c82798d06'),
    'selected-metadata-key': ('code', r"""static W l(const E*p){
    return e(2048+p->c)^(p->s<0?e(2064):0)^(p->e<0?0:e(2065+(p->e&7)));
}""", 90, 'd1053d460bb33779602d3e6b8a930d3992ca3119f729b7b0bdd5d05e275a4f50'),
    'selected-state-8-declarations-0': ('code', r"""static int g(const E*,Y*,int,int);""", 34, '4c167455beee30974fafe04a5f515f16b640f99c118ec95158b8cd58b5b22509'),
    'selected-attacked-square': ('code', r"""int c(const E*p,int a,int d){
    return g(p,0,a,d);
}""", 48, '991c5094d45aea7dffcc1af7a594a9f9a297cf6cac6cb19b0cc80b4987498cb9'),
    'selected-dead-material': ('code', r"""int ap(const E*p){
    int d=0;
    for(int q=0;q<128;q++)if(!(q&0x88)){
        int a=abs(p->b[q]);
        if(a==2){
            if(d)return 0;
            d=-1;
        }
        else if(a==3){
            if(d<0)return 0;
            d|=1<<((q+(q>>4))&1);
            if(d==3)return 0;
        }
        else if(a&&a<6)return 0;
    }
    return 1;
}""", 214, '34a9c0c4e3ce8a49c4a5ec503fd087036f85a313c69a163dfbd752aec8c13c34'),
    'selected-legal-EP-normalizer': ('code', r"""static void D(E*p){
    if(p->e<0)return;
    for(int d=-1;d<=1;d+=2){
        int q=p->e-p->s*16+d;
        if(!(q&0x88)&&p->b[q]==p->s){
            E t=*p;
            t.b[q]=t.b[p->e-p->s*16]=0;
            t.b[p->e]=(int8_t)p->s;
            if(!c(&t,p->k[p->s<0],-p->s))return;
        }
    }
    p->e=-1;
}""", 214, '6cbec02f2c32f55be56a759d018dbcdad5b919920dbb773c363b30af653829ad'),
    'selected-castling-rights-mask': ('code', r"""static int n(int q){
    return q==4?3:q==116?12:q==0?2:q==7?1:q==112?8:q==119?4:0;
}""", 79, '11328d2ad5aac33f0927d9979de09a7edc3d9c6c983086691ccf26b0b0b7a97e'),
    'selected-board-make': ('code', r"""int v(const E*p,Y m,E*w){
    int o=FROM(m),a=TO(m),d=PROMO(m),s=p->s,v=p->b[o],f=p->b[a];
    if(abs(f)==6)return 0;
    *w=*p;
    w->h^=l(p);
    w->aI++;
    w->e=-1;
    if(abs(v)==1){
        w->aI=0;
        if(a==p->e&&!f)b(w,a-s*16,0);
        if(abs(a-o)==32)w->e=o+s*16;
        if(d)v=s*d;
    }
    if(f)w->aI=0;
    if(abs(v)==6&&abs(a-o)==2){
        int g=a>o?o+3:o-4,i=a>o?o+1:o-1;
        b(w,g,0);
        b(w,i,s*4);
    }
    b(w,o,0);
    b(w,a,v);
    w->c&=~(n(o)|n(a));
    w->s=-s;
    if(c(w,w->k[s<0],-s))return 0;
    D(w);
    w->h^=l(w);
    w->r=w->aI?((p->r<<1)|(p->r>>63))^w->h:w->h;
    return 1;
}""", 469, '5826376ea116bbd734b01689ba1b83a56684295bc7cb71ad46272fd1cc2b88ce'),
    'selected-move-emitter': ('code', r"""static void k(Y*B,int*n,int o,int to,int a){
    int d=a>1&&!(to+16&96);
    for(int z=d?2:0;z<=(d?5:0);z++){
        B[(*n)++]=MOVE(o,to,z)|(a&1)*8;
    }
}""", 132, 'e1b75a5f3fbb3d399ecabd26d042776d17705e88fc81b62acf43716a0b2a9585'),
    'selected-move-and-attack-walker': ('code', r"""static int g(const E*p,Y*B,int f,int s){
    int n=0;
    for(int o=0;o<128;o++){
        if(o&0x88){
            o+=7;
            continue;
        }
        int a=abs(p->b[o]);
        if(p->b[o]*s<=0)continue;
        if(B&&a==1){
            int g=o+s*16;
            if(!(g&0x88)&&!p->b[g]){
                k(B,&n,o,g,2);
                if((o>>4)==(s>0?1:6)&&!p->b[g+s*16])k(B,&n,o,g+s*16,0);
            }
        }
        int j=a==1?(s>0?12:14):a==2?0:a==3?12:8,m=a==1?j+2:a==2?8:a==4?12:16;
        for(int i=j;i<m;i++){
            int d=qo[i];
            for(int q=o+d;!(q&0x88);q+=d){
                int t=p->b[q];
                if(!B&&q==f)return 1;
                if(t*s>0||(B&&a==1&&!t&&q!=p->e))break;
                if(B)k(B,&n,o,q,a==1?3:!!t);
                if(t||a<3||a==6)break;
            }
        }
        if(B&&a==6){
            int u=s>0?4:116,w=s>0?0:2;
            if(o==u&&!c(p,u,-s)){
                if((p->c&(1<<w))&&!p->b[u+1]&&!p->b[u+2]&&!c(p,u+1,-s))k(B,&n,o,u+2,0);
                if((p->c&(2<<w))&&!p->b[u-1]&&!p->b[u-2]&&!p->b[u-3]&&!c(p,u-1,-s))k(B,&n,o,u-2,0);
            }
        }
    }
    return n;
}""", 745, '21238772ba295266a149a2e3c699b3bf274a95a33cc4d9dafa945239a4488a5f'),
    'selected-pseudo-generation': ('code', r"""int T(const E*p,Y*B){
    return g(p,B,0,p->s);
}""", 43, 'fc3258e00c43d288f74272e31565526f94035b0d9f2235656f0eee37704837c1'),
    'selected-initial-position': ('code', r"""void q(E*p){
    static const int qa[8]={
        4,2,3,5,6,3,2,4
    }
    ;
    E t={
        0
    }
    ;
    t.s=1;
    t.c=15;
    t.e=-1;
    for(int f=0;f<8;f++){
        b(&t,f,qa[f]);
        b(&t,16+f,1);
        b(&t,96+f,-1);
        b(&t,112+f,-qa[f]);
    }
    t.h^=l(&t);
    t.r=t.h;
    *p=t;
}""", 188, '8f2c0eb1609009537ebc66f53580d023d48f31d5dfd88343b45527a465372cb6'),
    'selected-locked-full-TT': ('code', r"""static W V(W a,W U){
    Z*e=qq+(a&((1u<<18)-1));
    if(atomic_flag_test_and_set_explicit(&e->zN,memory_order_acquire))return 0;
    if(U)e->aT=a,e->U=U;
    else U=e->aT==a?e->U:0;
    atomic_flag_clear_explicit(&e->zN,memory_order_release);
    return U;
}""", 228, 'ec1813ddf3af5accdf362871eb8562fcb1d41e8b8395ca031a8647d8a4cca5b4'),
    'selected-search-poll': ('code', r"""static int ay(ai*w){
    if(atomic_load_explicit(&qp,memory_order_relaxed))return 0;
    if(!(w->a5&255)&&u()>=qc){
        atomic_store(&qp,1);
        return 0;
    }
    ++w->a5;
    return 1;
}""", 153, 'cc11078f970fd90962ad7f2e57bbcefcb125027cf96da5bb246413b900a7e9bf'),
    'selected-bounded-history-update': ('code', r"""static void O(X*a,int d){
    *a+=(d-*a*d/16384);
}""", 45, '83639d4e53833872a384653a92ea1790c8901338c142afe76b4ec3f4baca9767'),
    'selected-continuation-piece-index': ('code', r"""static int s(int p){
    return p+6;
}""", 32, '8e777c4c208f3c3530d5728665f295ea2c08ec008497d97e3f03f9eacb054de6'),
    'selected-PVS-QS-search': ('code', r"""static int h(ai*w,const E*p,int C,int G,int a,int d,int f,Y*g){
    if(!ay(w))return 0;
    int n=c(p,p->k[p->s<0],-p->s),t=p->aI>=100,u=0,x=qh+d-1-p->aI;
    if(x<0)x=0;
    for(int i=qh+d-3;i>=x;i-=2)u+=w->aA[i]==p->h;
    t|=u>=2||ap(p);
    t|=(d==128-1)*2;
    Y B[512],N=0;
    int y[512],z=T(p,B),A=0,D=G,H=-30000,F=p->s*S(p);
    W I=p->h^e(p->r+(unsigned)p->aI),U=t?0:V(I,0);
    Y J=U&131071;
    int l=(X)(U>>17),K=(U>>41)&3,L=(U>>33)&255;
    if(l>30000-128)l-=d;
    if(l< -30000+128)l+=d;
    if(d&&K&&L>=(C>0?C:0)&&(K==1||(K==2&&l>=a)||(K==3&&l<=G)))return l;
    int M=!t&&C<=0&&!n;
    if(M){
        H=F;
        if(H>G)G=H;
    }
    for(int i=0;i<z;i++){
        Y m=B[i];
        int o=FROM(m),P=TO(m),R=s(p->b[o]);
        y[i]=m==J?1000000:m&8?500000:w->zC[o][P]+w->an[f][R]+(int)((m*37u+w->id*19u)%17);
        if(PROMO(m))y[i]+=400000+PROMO(m)*1000;
        y[i]+=r(p,m);
    }
    for(int i=0;i<z;i++){
        int j=i;
        for(int k=i+1;k<z;k++)if(y[k]>y[j])j=k;
        Y m=B[j];
        B[j]=B[i];
        y[j]=y[i];
        E q;
        if(!v(p,m,&q))continue;
        if(t){
            if(t==2)atomic_store(&qp,1);
            return 0;
        }
        ++A;
        int o=FROM(m),P=TO(m),Q=(m&8)||PROMO(m),R=s(q.b[P]);
        if(M&&(!Q||G>=a))continue;
        w->aA[qh+d]=q.h;
        if(A==1||C<=0)l=-h(w,&q,C-1,-a,-G,d+1,R,0);
        else{
            int S=C>=4&&A>=4&&!Q&&!n&&!c(&q,q.k[q.s<0],-q.s);
            if(S){
                S=F+w->ah[p->h&1023]/64<G+100;
            }
            l=-h(w,&q,C-1-S,-G-1,-G,d+1,R,0);
            if(S&&l>G)l=-h(w,&q,C-1,-G-1,-G,d+1,R,0);
            if(l>G&&l<a)l=-h(w,&q,C-1,-a,-G,d+1,R,0);
        }
        if(atomic_load_explicit(&qp,memory_order_relaxed))return 0;
        if(l>H){
            H=l;
            N=m;
            if(g)*g=m;
        }
        if(l>G)G=l;
        if(G>=a){
            if(C>0&&!Q){
                int S=C*C;
                O(&w->zC[o][P],S);
                O(&w->an[f][R],S);
            }
            break;
        }
    }
    if(!A)return n?-30000+d:0;
    K=H<=D?3:H>=a?2:1;
    if(C>0&&K==1&&!n&&N&&!(N&8)&&!PROMO(N)&&abs(H)<30000-128){
        int S=H-F;
        if(S>256)S=256;
        if(S< -256)S=-256;
        w->ah[p->h&1023]+=S-w->ah[p->h&1023]/64;
    }
    l=H;
    if(l>30000-128)l+=d;
    if(l< -30000+128)l-=d;
    U=N|((W)(uint16_t)l<<17)|((W)(C>0?C:0)<<33)|((W)K<<41);
    V(I,U);
    return H;
}""", 1737, '3004a98711f335c3a25fb5c517e7259986f70b4ef2a2dffa48483b9d395c9a41'),
    'selected-iterative-search': ('code', r"""void C(ai*w,const E*p){
    w->a5=0;
    w->C=0;
    w->l=0;
    w->H=0;
    memcpy(w->aA,qg,qh*sizeof(W));
    for(int C=1;C<=128-2;C++){
        Y H=w->H;
        int l=h(w,p,C,-30000,30000,0,6,&H);
        if(atomic_load_explicit(&qp,memory_order_relaxed))break;
        w->H=H;
        w->l=l;
        w->C=C;
    }
}""", 231, 'f35caa3919bac6c929c5247dc82aff3081ecbbdee5d54de43d61ba8161fbd426'),
    'selected-state-23-declarations-0': ('code', r"""static pthread_mutex_t qj=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t qb=PTHREAD_COND_INITIALIZER;
static unsigned qd;
static int qk=2,qm;""", 140, '3ac6ec1392561e7067c82c132f3c07ab6c5d5e3488da3e695322d3b5fc0f4300'),
    'selected-move-format': ('code', r"""static void o(Y m,char*s){
    if(!m){
        strcpy(s,"0000");
        return;
    }
    s[0]='a'+(FROM(m)&7);
    s[1]='1'+(FROM(m)>>4);
    s[2]='a'+(TO(m)&7);
    s[3]='1'+(TO(m)>>4);
    s[4]="  nbrq"[PROMO(m)];
    s[4+!!PROMO(m)]=0;
}""", 183, '03e618f536f3f7bef7488923c84b2d5fbe9b743bd6723122b33668cfc3cd768d'),
    'selected-legal-move-parser': ('code', r"""static Y i(const E*b,const char*s,E*c){
    Y a[512];
    char d[6];
    int n=T(b,a);
    for(int i=0;i<n;i++){
        if(s){
            o(a[i],d);
            if(strcmp(s,d))continue;
        }
        if(v(b,a[i],c))return a[i];
    }
    return 0;
}""", 171, '776e4a316e26cda4965982800afb7f4676e14706b8d6e45d5c73bed4da1ef649'),
    'selected-worker-result': ('code', r"""static void x(void){
    ai*w=qr+(qr[1].C>qr->C);
    E fb;
    Y H=w->H?w->H:i(&ql,0,&fb);
    char a[6];
    o(H,a);
    printf("bestmove %s\n",a);
    fflush(stdout);
}""", 135, '79e9519f3f647789e5e347a5a5e9a892a48e6bfceb3dcf49a51975e74629680b'),
    'selected-persistent-worker': ('code', r"""static void*A(void*p){
    ai*w=0;
    unsigned a=0;
    pthread_mutex_lock(&qj);
    for(;;){
        if(!--qk){
            if(w)x();
            pthread_cond_broadcast(&qb);
        }
        while(a==qd&&!qm)pthread_cond_wait(&qb,&qj);
        if(qm)break;
        w=p;
        a=qd;
        pthread_mutex_unlock(&qj);
        C(w,&ql);
        pthread_mutex_lock(&qj);
    }
    pthread_mutex_unlock(&qj);
    return NULL;
}""", 286, '8eb09c01749929b631c6d5a21de4e35c7112a6aae43f6d81a48edee48b3d2cc2'),
    'selected-stop-and-drain': ('code', r"""static void j(void){
    atomic_store(&qp,1);
    pthread_mutex_lock(&qj);
    while(qk)pthread_cond_wait(&qb,&qj);
    pthread_mutex_unlock(&qj);
}""", 127, 'f1d9fccd25f4024a1aa0778b2d9f178fcf7119e7c94edddb2cc8e0b335793df2'),
    'selected-clear-TT-flags': ('code', r"""static void B(void){
    for(size_t i=0;i<(1<<18);i++)atomic_flag_clear(&qq[i].zN);
}""", 79, 'ba74c04b7c6832fe77ed955c0815193d6a90f3f625548c3dbd4d345e694f53b9'),
    'selected-position-command': ('code', r"""static void z(void){
    E b,c;
    W a[4096];
    int n=1;
    char*B=nt();
    if(!B||strcmp(B,"startpos"))return;
    q(&b);
    a[0]=b.h;
    B=nt();
    if(B){
        if(strcmp(B,"moves"))return;
        while((B=nt())){
            if(n==4096||!i(&b,B,&c))return;
            b=c;
            a[n++]=b.h;
        }
    }
    ql=b;
    qh=n;
    memcpy(qg,a,n*sizeof*a);
}""", 246, '86c0d928087af3d93ee131674874477f56baa47d94badc673dd8421d77f9b886'),
    'selected-time-number': ('code', r"""static W y(const char*s){
    char*e;
    if(!s||(unsigned)(*s-'0')>9)return 0;
    W n=strtoull(s,&e,10);
    return*e||n>>63?0:n;
}""", 112, '84162918393a6dda6a5b5628f0739bed485aedf2658c0fa662f92cea91006813'),
    'selected-go-command': ('code', r"""static void w(void){
    j();
    W a=-1,d=0,S=0;
    for(char*t=nt();t;t=nt()){
        if((*t=='w'||*t=='b')&&(!strcmp(t+1,"time")||!strcmp(t+1,"inc"))){
            W n=y(nt());
            if((*t=='w')==(ql.s>0)){
                if(t[1]=='t')a=n;
                else d=n;
            }
        }
    }
    if(~a){
        S=a/30+(d>86400000?86400000:d)*3/4;
        if(S>a/5)S=a/5;
        if(!S)S=1;
    }
    else S=1000;
    qc=u()+(S>86400000?86400000:S);
    atomic_store(&qp,0);
    pthread_mutex_lock(&qj);
    qk=2;
    qd++;
    pthread_cond_broadcast(&qb);
    pthread_mutex_unlock(&qj);
}""", 416, '5ae9865ae53c4821ff26e1c0e79ede8645ac18e2dfad4507dc44acdc23d02098'),
    'selected-protocol-main': ('code', r"""int main(void){
    pthread_t a[2];
    int V=0,d=0;
    char R[32768];
    qq=calloc(1<<18,sizeof*qq);
    if(!qq)return 2;
    B();
    q(&ql);
    qg[0]=ql.h;
    qh=1;
    for(;V<2;V++){
        qr[V].id=V;
        if(pthread_create(a+V,NULL,A,qr+V)){
            d=2;
            goto shutdown;
        }
    }
    j();
    while(fgets(R,sizeof R,stdin)){
        if(!strchr(R,'\n')){
            int n=getchar();
            if(n!=EOF&&n!='\n'){
                do{
                    n=getchar();
                }
                while(n!=EOF&&n!='\n');
                continue;
            }
        }
        char*g=strtok(R," \t\r\n");
        if(!g)continue;
        if(!strcmp(g,"uci")){
            puts("uciok");
            fflush(stdout);
        }
        else if(!strcmp(g,"isready")){
            puts("readyok");
            fflush(stdout);
        }
        else if(!strcmp(g,"quit"))break;
        else if(!strcmp(g,"position")){
            j();
            z();
        }
        else if(!strcmp(g,"go"))w();
    }
    j();
    shutdown:pthread_mutex_lock(&qj);
    qm=1;
    pthread_cond_broadcast(&qb);
    pthread_mutex_unlock(&qj);
    for(int i=0;i<V;i++)if(pthread_join(a[i],NULL))d=2;
    free(qq);
    return d;
}""", 770, '10d74db6c8e80beebba434a3a9bc7af2cc0d32aa5b8707b42024d28b8293be88'),
}

_OLD_LAYOUT = [('canonical', 'old-state-0-line-0'), ('canonical', 'old-state-0-line-1'), ('canonical', 'old-state-0-line-2'), ('canonical', 'old-state-0-line-3'), ('canonical', 'old-state-0-line-4'), ('canonical', 'old-state-0-line-5'), ('canonical', 'old-state-0-line-6'), ('canonical', 'old-state-0-line-7'), ('canonical', 'old-state-0-line-8'), ('canonical', 'old-state-0-line-0'), ('canonical', 'old-state-0-line-0'), ('canonical', 'old-state-0-line-0'), ('canonical', 'old-state-0-declarations-12'), ('canonical', 'old-state-0-line-0'), ('canonical', 'old-state-0-line-13'), ('canonical', 'old-state-0-line-14'), ('canonical', 'old-state-0-line-15'), ('canonical', 'old-state-0-line-16'), ('canonical', 'old-state-0-declarations-17'), ('canonical', 'old-monotonic-clock'), ('canonical', 'old-state-1-declarations-0'), ('canonical', 'old-piece-key-mix'), ('model', 'weights'), ('model', 'center'), ('canonical', 'old-metadata-key'), ('model', 'setter'), ('canonical', 'old-state-6-declarations-0'), ('canonical', 'old-attacked-square'), ('canonical', 'old-dead-material'), ('canonical', 'old-legal-EP-normalizer'), ('canonical', 'old-castling-rights-mask'), ('canonical', 'old-board-make'), ('canonical', 'old-move-emitter'), ('canonical', 'old-move-and-attack-walker'), ('canonical', 'old-pseudo-generation'), ('canonical', 'old-initial-position'), ('model', 'evaluate'), ('model', 'order'), ('canonical', 'old-state-0-line-0'), ('canonical', 'old-locked-full-TT'), ('canonical', 'old-search-poll'), ('canonical', 'old-bounded-history-update'), ('canonical', 'old-continuation-piece-index'), ('canonical', 'old-PVS-QS-search'), ('canonical', 'old-iterative-search'), ('canonical', 'old-state-23-declarations-0'), ('canonical', 'old-move-format'), ('canonical', 'old-legal-move-parser'), ('canonical', 'old-worker-result'), ('canonical', 'old-persistent-worker'), ('canonical', 'old-stop-and-drain'), ('canonical', 'old-clear-TT-flags'), ('canonical', 'old-command-token'), ('canonical', 'old-position-command'), ('canonical', 'old-time-number'), ('canonical', 'old-go-command'), ('canonical', 'old-protocol-main'), ('canonical', 'old-state-0-line-0')]
_NEW_LAYOUT = [('canonical', 'old-state-0-line-0'), ('canonical', 'old-state-0-line-1'), ('canonical', 'selected-state-0-line-2'), ('canonical', 'selected-state-0-line-3'), ('canonical', 'selected-state-0-line-4'), ('canonical', 'selected-state-0-line-5'), ('canonical', 'selected-state-0-line-6'), ('canonical', 'selected-state-0-line-7'), ('canonical', 'selected-state-0-line-8'), ('canonical', 'old-state-0-line-0'), ('canonical', 'old-state-0-line-0'), ('canonical', 'old-state-0-line-0'), ('canonical', 'selected-state-0-declarations-12'), ('canonical', 'old-state-0-line-0'), ('canonical', 'old-state-0-line-13'), ('canonical', 'old-state-0-line-14'), ('canonical', 'old-state-0-line-15'), ('canonical', 'selected-state-0-line-16'), ('canonical', 'selected-state-0-declarations-17'), ('canonical', 'selected-monotonic-clock'), ('canonical', 'selected-state-1-declarations-0'), ('canonical', 'selected-piece-key-mix'), ('model', 'weights'), ('model', 'center'), ('model', 'evaluate'), ('model', 'order'), ('canonical', 'selected-metadata-key'), ('model', 'setter'), ('canonical', 'selected-state-8-declarations-0'), ('canonical', 'selected-attacked-square'), ('canonical', 'selected-dead-material'), ('canonical', 'selected-legal-EP-normalizer'), ('canonical', 'selected-castling-rights-mask'), ('canonical', 'selected-board-make'), ('canonical', 'selected-move-emitter'), ('canonical', 'selected-move-and-attack-walker'), ('canonical', 'selected-pseudo-generation'), ('canonical', 'selected-initial-position'), ('canonical', 'old-state-0-line-0'), ('canonical', 'selected-locked-full-TT'), ('canonical', 'selected-search-poll'), ('canonical', 'selected-bounded-history-update'), ('canonical', 'selected-continuation-piece-index'), ('canonical', 'selected-PVS-QS-search'), ('canonical', 'selected-iterative-search'), ('canonical', 'selected-state-23-declarations-0'), ('canonical', 'selected-move-format'), ('canonical', 'selected-legal-move-parser'), ('canonical', 'selected-worker-result'), ('canonical', 'selected-persistent-worker'), ('canonical', 'selected-stop-and-drain'), ('canonical', 'selected-clear-TT-flags'), ('canonical', 'old-command-token'), ('canonical', 'selected-position-command'), ('canonical', 'selected-time-number'), ('canonical', 'selected-go-command'), ('canonical', 'selected-protocol-main'), ('canonical', 'old-state-0-line-0')]

METADATA = {
    'family': 'E', 'stage': 'e19-mailbox-common-PVS-runtime',
    'input_bytes': INPUT_PIN[0], 'input_sha256': INPUT_PIN[1],
    'output_bytes': OUTPUT_PIN[0], 'output_sha256': OUTPUT_PIN[1],
    'raw_delta': OUTPUT_PIN[0]-INPUT_PIN[0],
    'model_id': LOGICAL_MODEL_ID, 'logical_coefficients': 19, 'physical_slots': 21,
    'logical19_s16le_sha256': LOGICAL19_S16LE_SHA256,
    'actual_input_model_regions': 5, 'model_body_roundtrip': True,
    'full_inverse': True, 'canonical_DEV_unchanged': True,
    'canonical_regions': len(_CANONICAL),
    'input_partition_gaps': len(_INPUT_GAPS), 'output_partition_gaps': len(_OUTPUT_GAPS),
    'scope': 'selected E19 Board/PVS/runtime composition; complete model bodies are rebound from the actual previous E output',
    'policy_note': 'E19 model and move ordering retained; selected common search/runtime presentation, not old-E whole search-trace equivalence',
    'external_reads_compiler_codec_engine': 0,
}

def _pin(raw):
    return len(raw), hashlib.sha256(raw).hexdigest()

def _need(good, message):
    if not good:
        raise ValueError(message)

def _guard(source, expected, label):
    _need(type(source) is bytes and _pin(source)==expected, label+' fixed source identity')

def _extract(source, specs):
    result={}
    for role,(start,size,digest) in specs.items():
        body=source[start:start+size]
        _need(_pin(body)==(size,digest), role+' fixed model region')
        result[role]=body
    return result

def _partition(source, gaps):
    for start,size,digest in gaps:
        _need(_pin(source[start:start+size])==(size,digest), 'fixed canonical partition gap')

def _splice(body, role, reverse=False):
    parts=[];cursor=0
    for old_at,new_at,old,new in _BINDINGS[role]:
        at,before,after=(new_at,new.encode(),old.encode()) if reverse else (old_at,old.encode(),new.encode())
        _need(at>=cursor and body[at:at+len(before)]==before, role+' binder token span')
        parts.extend((body[cursor:at],after));cursor=at+len(before)
    parts.append(body[cursor:])
    return b''.join(parts)

def _bind_models(models, reverse=False):
    target_specs=_INPUT_MODELS if reverse else _OUTPUT_MODELS
    result={}
    for role,body in models.items():
        bound=_splice(body,role,reverse)
        _need(_pin(bound)==target_specs[role][1:], role+' bound model identity')
        _need(_splice(bound,role,not reverse)==body, role+' positional model full inverse')
        result[role]=bound
    return result

def _assemble(layout, models, compact):
    _need(callable(compact), 'existing pinned compact_source callback required')
    parts=[]
    for kind,name in layout:
        if kind=='model':
            parts.append(models[name]);continue
        presentation,readable,size,digest=_CANONICAL[name]
        if presentation=='literal':
            body=readable.encode('ascii')
        else:
            packed=compact(readable.encode('ascii'),'c')
            _need(type(packed) is bytes and packed.endswith(b'\n'), name+' existing C compactor result')
            body=packed[:-1]
        _need(_pin(body)==(size,digest), name+' canonical C token identity')
        parts.append(body)
    return b''.join(parts)

def _forward(source, compact):
    _guard(source,INPUT_PIN,'previous E chain')
    _partition(source,_INPUT_GAPS)
    models=_bind_models(_extract(source,_INPUT_MODELS))
    result=_assemble(_NEW_LAYOUT,models,compact)
    _guard(result,OUTPUT_PIN,'selected E19')
    _partition(result,_OUTPUT_GAPS)
    return result

def restore_source(source, *, compact):
    """Regenerate exact previous E bytes, using the actual selected model bodies.

    This inverse is for the existing source-literal/guard chain. Canonical old
    runtime regions reconstruct replaced code; positional unbinding reconstructs
    model tokens without renaming pre-existing mailbox b members or EP e fields.
    """
    _guard(source,OUTPUT_PIN,'selected E19 inverse input')
    _partition(source,_OUTPUT_GAPS)
    models=_bind_models(_extract(source,_OUTPUT_MODELS),reverse=True)
    restored=_assemble(_OLD_LAYOUT,models,compact)
    _guard(restored,INPUT_PIN,'previous E inverse result')
    _partition(restored,_INPUT_GAPS)
    _need(_forward(restored,compact)==source,'selected source inverse roundtrip')
    return restored

def transform_source(source, *, compact):
    result=_forward(source,compact)
    _need(restore_source(result,compact=compact)==source,'previous E full source inverse')
    return result,dict(METADATA)


# Packaging is a one-way adapter after the actual previous literal consumer:
# new source -> restore old source -> old common.source_literal/template ->
# this guarded two-region replacement. No second compression is performed.
import ast

_BOOT_INPUT_PIN = (10868, '3aba86632592b6644495515cfe281b5ebe47bd236d13641408707178877cd9a7')
_BOOT_OUTPUT_PIN = (10028, '8ee9afdc733bc350fbf58100a0e65b669ddc6d3abed09a890d771ad2bdf11a26')
_BOOT_COMPILER_BEFORE = b"'cc -std=c11 -Os -pthread -DWORKERS=2 -DTT_BITS=18 -DDEV=0 -x c - -o x'.split()"
_BOOT_COMPILER_AFTER = b"'cc -Os -x c - -o x -s'.split()"

BOOTSTRAP_METADATA = {
    'input_bytes': _BOOT_INPUT_PIN[0], 'input_sha256': _BOOT_INPUT_PIN[1],
    'output_bytes': _BOOT_OUTPUT_PIN[0], 'output_sha256': _BOOT_OUTPUT_PIN[1],
    'actual_previous_literal_and_template_consumed': True,
    'selected_literal': 'triple-double raw bytes after actual common literal validation',
    'owned_regions': 2, 'protected_gaps': 3, 'full_inverse': True,
    'compiler_policy': 'selected A flags; old E preprocessor and DEV compiler unchanged',
    'external_reads_compiler_codec_engine': 0,
}
METADATA.update(
    core_origin_source_sha256='c8efc687c503e9872e004431af9fd07c07867ebb19a996fb9c4c0f4d6508f529',
    model_origin_source_sha256=INPUT_PIN[1],
    search_policy='selected full A-PVS common implementation with exact current E19 model; separate search variant',
)

def transform_bootstrap(previous, *, before, source, old_expression, expression, compact):
    """Consume the actual old E package script, then replace compiler/literal."""
    _guard(previous, _BOOT_INPUT_PIN, 'actual previous E bootstrap')
    _guard(before, INPUT_PIN, 'actual restored E source')
    _guard(source, OUTPUT_PIN, 'selected E source')
    _need(restore_source(source,compact=compact)==before, 'literal source inverse consumed')
    _need(type(old_expression) is str and type(expression) is str, 'actual literal expressions required')
    _need(ast.literal_eval(old_expression)==before and ast.literal_eval(expression)==source,
          'actual old/new literals restore complete source')
    # The selected A envelope uses triple-double raw bytes. The previous
    # common literal is still actually consumed and validated above.
    quote=chr(34)*3
    _need(source.isascii() and quote.encode() not in source and b'\r' not in source,
          'selected raw triple-double source domain')
    selected_expression='br'+quote+source.decode('ascii')+quote
    _need(ast.literal_eval(selected_expression)==source, 'selected raw bytes literal inverse')
    rows = [
        (_BOOT_COMPILER_BEFORE, _BOOT_COMPILER_AFTER),
        (old_expression.encode('ascii'), selected_expression.encode('ascii')),
    ]
    edits=[]
    for old,new in rows:
        _need(previous.count(old)==1, 'fixed previous bootstrap region')
        edits.append((previous.index(old),old,new))
    edits.sort()
    parts=[];inverse=[];gaps=[];cursor=output_cursor=0
    for at,old,new in edits:
        _need(at>=cursor, 'nonoverlapping bootstrap regions')
        gap=previous[cursor:at];parts.extend((gap,new))
        gaps.append((cursor,at,output_cursor,output_cursor+len(gap)))
        output_cursor+=len(gap);inverse.append((output_cursor,old,new))
        output_cursor+=len(new);cursor=at+len(old)
    parts.append(previous[cursor:]);result=b''.join(parts)
    gaps.append((cursor,len(previous),output_cursor,len(result)))
    for lo,hi,out_lo,out_hi in gaps:
        _need(previous[lo:hi]==result[out_lo:out_hi], 'protected bootstrap gap')
    restored=result
    for at,old,new in reversed(inverse):
        _need(restored[at:at+len(new)]==new, 'bootstrap inverse fixed region')
        restored=restored[:at]+old+restored[at+len(new):]
    _need(restored==previous, 'actual previous bootstrap full inverse')
    _guard(result,_BOOT_OUTPUT_PIN,'selected bootstrap')
    calls=[node for node in ast.walk(ast.parse(result))
           if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute)
           and node.func.attr=='communicate']
    _need(len(calls)==1 and len(calls[0].args)==1
          and ast.literal_eval(calls[0].args[0])==source, 'selected literal C stdin')
    return result,dict(BOOTSTRAP_METADATA)
