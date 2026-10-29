"""Opt-in F-MTD-MaterialNoise-v1 fixed shipping policy.

This is a declared evaluation and move-ordering policy, not lossless source
compression. Full F/DEV keep their learning and HCE. The sole input follows
startup and precedes full-F aliases/capture. No external artifact is read.
"""
import hashlib

INPUT_BYTES=9422
INPUT_SHA256='109cb9df07a6d2a44b2930abcdadaba2246d953e1276a70a66ecb182fd77544a'
OUTPUT_BYTES=8779
OUTPUT_SHA256='a4f3dafc7a99ac180d582350a34ec41a78e6f51f6ec202bc1e88dcda8fd24323'
EDITS=(('learner arrays', 618, 618, b'X h[128][128],i[13][13],j[1024];', b''), ('material evaluation', 1043, 1011, b'int ad(int v,int q){static const int qi[7]={24576,48228,98624,65866,27124,41860,0};int a=qi[abs(v)],d=q>>4,f=q&7,g=v>0?d:7-d,i=7-abs(2*f-7)-abs(2*d-7),j=(a&1023)+g*((a>>10)&7)+i*((a>>13)-3);return v>0?j:-j;}', b'int ad(int v){static const int qi[7]={0,100,320,330,500,900,0};int a=qi[abs(v)];return v>0?a:-a;}'), ('material square argument', 1472, 1330, b'ad(a,q)', b'ad(a)'), ('material square argument', 1525, 1381, b'ad(v,q)', b'ad(v)'), ('learn helper', 4119, 3973, b'static void an(X*a,int d){*a+=d-*a*d/16384;}', b''), ('piece index helper', 4163, 3973, b'static int ao(int p){return p+6;}', b''), ('quiet learner helper', 4284, 4061, b'static int ap(zc*w,const za*p,Y m,int a){int d=FROM(m),f=TO(m),g=w->j[(p->h^m)&1023]/64;return w->h[d][f]+w->i[a][ao(p->b[d])]+g+(int)((m*37u+w->a*19u)%17);}', b''), ('search prior formal', 4441, 4061, b'static int aj(zc*w,const za*p,int a,int d,int f,int g,Y*l){', b'static int aj(zc*w,const za*p,int a,int d,int f,Y*l){'), ('material square argument', 5125, 4739, b'ad(p->b[M],M)', b'ad(p->b[M])'), ('material square argument', 5147, 4759, b'ad(p->b[L],L)', b'ad(p->b[L])'), ('stateless quiet ordering', 5162, 4772, b'ap(w,p,m,g)', b'(int)((m*37u+w->a*19u)%17)'), ('unused from/to locals', 5348, 4973, b'N=FROM(m),O=TO(m),', b''), ('next piece', 5385, 4992, b',Q=ao(q.b[O])', b''), ('recursive prior actual', 5445, 5039, b'aj(w,&q,a-1,1-d,f+1,Q,0)', b'aj(w,&q,a-1,1-d,f+1,0)'), ('cutoff learning', 5572, 5164, b'if(a>0&&!P){int R=a*a;an(&w->h[N][O],R);an(&w->i[g][ao(p->b[N])],R);}', b''), ('root prior actual', 5990, 5513, b'aj(w,p,a,i,0,6,&j)', b'aj(w,p,a,i,0,&j)'), ('completed-iteration correction', 6223, 5744, b'if(yk&&!aa(p,p->k[p->s<0],-p->s)&&!al(p,yk)&&!PROMO(yk)&&abs(g)<MATE-128){int l=g-p->s*p->v;if(l>256)l=256;if(l< -256)l=-256;X*m=&w->j[(p->h^yk)&1023];*m+=l-*m/64;}', b''))
GAPS=((0, 0, 618, '2a903a443947c461ee50a7a29a386062d32ecbe767c47951bfd610160ce753ae'), (650, 618, 393, 'b4426ee90d5592d5e92160f10e9f8537e833666ce331c3b7f41fcdca63aef453'), (1250, 1108, 222, '5d1d9e83686ec39a6495bb91939090b2428ad5d396e5eeb207a1fd6598114d66'), (1479, 1335, 46, '03ec9b09f31075950a6f8b04700329292876c3ccef7207e799b873fac3ee151a'), (1532, 1386, 2587, '899424b0e53dbde6d37baffbcd18535c5bb6d2e93f6a9b8be4982b52f473c6ab'), (4163, 3973, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (4196, 3973, 88, 'fbcc7d89ed855b49adae11a47d36d83ef1a5d4b390799b2778168905259c6084'), (4441, 4061, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (4500, 4114, 625, '96258b63347f00abf9b01590a176b3a6098b459d188570ca629cf2174b24be99'), (5138, 4750, 9, 'aaeb76e23e05101245c52124299459bba5f621d3f4166d99b05c25aef324adce'), (5160, 4770, 2, 'f4bbd8dc0a3fd7f22beb6c7a462f6fbf6e92608166f7a495fd87bb43be9bd034'), (5173, 4798, 175, 'd7e09ec5ba39ca930a1a9a1e5f6552617a102e40eb5d55321f15cb2ee87fed0c'), (5366, 4973, 19, 'd7ac9c9271ebccbb9d5db0cc1d6d39959fed258a1e2b19fd4b617a861cc6b9bd'), (5398, 4992, 47, '9b7a37825f1ed5b11bb93c2190a0a053ff381f5cb3b651ca52c0fab3a426509c'), (5469, 5061, 103, '24906e23ce7188993a800e22bea6a6fefc1d585daf419df01398af3c5ae117d4'), (5641, 5164, 349, '2bd0737e963c60be24dc250b4554f19d58aef27f5bf04d86e187d4203120bbb9'), (6008, 5529, 215, '9277edeb91379875fc173b4a5755245eea786e1ad0ec0b57ca77145b297ebb33'), (6387, 5744, 3035, 'e4306f2d06fe764f2d795567beedbecb77b48e8bb8a3b61e4c92fdee6153198b'))

def sha(data):return hashlib.sha256(data).hexdigest()

def transform_source(source):
    if type(source) is not bytes or len(source)!=INPUT_BYTES or sha(source)!=INPUT_SHA256:
        raise ValueError('exact post-startup full F source required for MaterialNoise-v1')
    parts=[];oldat=0;newat=0;inverse=[]
    for role,oa,na,old,new in EDITS:
        if oa<oldat or source[oa:oa+len(old)]!=old or source.count(old)!=1:
            raise ValueError('fixed material policy role differs: '+role)
        parts.extend((source[oldat:oa],new));oldat=oa+len(old)
    parts.append(source[oldat:]);result=b''.join(parts)
    for role,oa,na,old,new in EDITS:
        if result[na:na+len(new)]!=new:raise ValueError('material policy output role differs: '+role)
        inverse.extend((result[newat:na],old));newat=na+len(new)
    inverse.append(result[newat:])
    if b''.join(inverse)!=source:raise ValueError('material policy literal inverse differs')
    for oa,na,size,pin in GAPS:
        a=source[oa:oa+size];b=result[na:na+size]
        if a!=b or sha(a)!=pin:raise ValueError('material policy protected complement differs')
    if len(result)!=OUTPUT_BYTES or sha(result)!=OUTPUT_SHA256:
        raise ValueError('fixed MaterialNoise-v1 source identity differs')
    return result,{'policy':'F-MTD-MaterialNoise-v1','stage':'shipping-after-startup-before-full-aliases-capture',
                   'role_edits':17,'protected_gaps':18,'exact_inverse':True,
                   'source_bytes':len(result),'source_sha256':sha(result),'DEV_bypasses_stage':True,
                   'policy_change_not_equivalence':True,'material_values':[0,100,320,330,500,900,0],
                   'ordering':'TT then captures/promotions; original stateless worker noise quiets',
                   'optional_history_continuation_correction':False,
                   'full_MTD_rules_fullkey_context_pool_resources_preserved':True}
