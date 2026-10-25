"""ONE declared untrained E19 quadratic model + incremental inputs; no normal edits."""
import hashlib
BASE_SHA='761e301cdad7b1dcf15da6458959612606e93be8b863ba2072e2ba509cb857f9'
CANDIDATE_SHA='b043eae2df9190c07beaad8c6528aa1a76db1173990eefc2f047875118991052'
PAIRS=[(b'int s,c,e,k[2],zL;', b'int s,c,e,k[2],zL,v,a;'), (b'static uint64_t piece(int v,int q){return mix((uint64_t)(q+(v+6)*128));}', b'static const int16_t tiny_weights[19]={100,320,330,500,900,3,8,5,2,1,-3,6,10,1,16,-1,12,2,4};static int Q(int q){int f=q&7,r=q>>4;return(f<4?f:7-f)+(r<4?r:7-r);}static uint64_t piece(za*p,int v,int q,int d){int a=abs(v),s=v>0?d:-d;p->v+=s*(a<6?tiny_weights[a-1]:0);p->a+=s*(tiny_weights[a+4]*Q(q)+(a==1?tiny_weights[11]*((v<0?7-(q>>4):q>>4)-1):0));return mix((uint64_t)(q+(v+6)*128));}'), (b'p->h^=piece(a,q);', b'p->h^=piece(p,a,q,-1);'), (b'p->h^=piece(v,q);', b'p->h^=piece(p,v,q,1);'), (b'static const int16_t tiny_weights[21]={100,320,330,500,900,3,8,5,2,1,-3,6,-12,-8,24,10,16,-1,12,2,4};static int Q(int q){int f=q&7,r=q>>4;return(f<4?f:7-f)+(r<4?r:7-r);}static int T(const za*p){int d[2][10]={{0}},i[2]={0},j=p->s*tiny_weights[15];for(int q=0;q<128;q++)if(!(q&0x88)&&p->b[q]){int v=p->b[q],m=v<0,a=abs(v),t=m?-1:1;j+=t*((a<6?tiny_weights[a-1]:0)+tiny_weights[a+4]*Q(q));if(a==1){d[m][(q&7)+1]++;j+=t*tiny_weights[11]*((m?7-(q>>4):q>>4)-1);}if(a==3)i[m]++;}for(int u=0;u<2;u++){int s=i[u]>1?tiny_weights[14]:0;for(int f=1;f<9;f++){int n=d[u][f];if(n){s+=tiny_weights[12]*(n-1);if(!d[u][f-1]&&!d[u][f+1])s+=tiny_weights[13]*n;}}j+=u?-s:s;}return j;}static int S(const za*p){int s=T(p);return s>20000?20000:s< -20000?-20000:s;}static int R(const za*p,Move m){int d=FROM(m),f=TO(m),i=p->b[d],a=abs(i),v=abs(p->b[f]),j=PROMO(m);if(a==1&&f==p->e&&!v)v=1;int s=tiny_weights[19]*(Q(f)-Q(d));if(v)s+=tiny_weights[16]*(v<6?tiny_weights[v-1]:0)+tiny_weights[17]*(a<6?tiny_weights[a-1]:0);if(j)s+=tiny_weights[18]*(tiny_weights[j-1]-tiny_weights[0]);if(a==1)s+=tiny_weights[20]*((f>>4)-(d>>4))*(i<0?-1:1);return s;}', b'static int S(const za*p){int s=p->v+p->a+tiny_weights[13]*p->a*abs(p->a)/128+p->s*tiny_weights[12];return s>20000?20000:s< -20000?-20000:s;}static int R(const za*p,Move m){int d=FROM(m),f=TO(m),i=p->b[d],a=abs(i),v=abs(p->b[f]),j=PROMO(m);if(a==1&&f==p->e&&!v)v=1;int s=tiny_weights[17]*(Q(f)-Q(d));if(v)s+=tiny_weights[14]*(v<6?tiny_weights[v-1]:0)+tiny_weights[15]*(a<6?tiny_weights[a-1]:0);if(j)s+=tiny_weights[16]*(tiny_weights[j-1]-tiny_weights[0]);if(a==1)s+=tiny_weights[18]*((f>>4)-(d>>4))*(i<0?-1:1);return s;}')]

def transform(source):
    if len(source)!=11378 or hashlib.sha256(source).hexdigest()!=BASE_SHA:
        raise ValueError('exact current E shipping source required')
    result=source;old_rest=source
    for old,new in PAIRS:
        if result.count(old)!=1:raise ValueError('fixed old span is not unique')
        result=result.replace(old,new,1)
    inverse=result;new_rest=result
    for index,(old,new)in enumerate(PAIRS):
        if inverse.count(new)!=1:raise ValueError('fixed new span is not unique')
        inverse=inverse.replace(new,old,1)
        marker=('$SPAN'+str(index)).encode()
        old_rest=old_rest.replace(old,marker,1);new_rest=new_rest.replace(new,marker,1)
    if inverse!=source or old_rest!=new_rest:raise ValueError('inverse/complement changed')
    if len(result)!=11105 or hashlib.sha256(result).hexdigest()!=CANDIDATE_SHA:
        raise ValueError('fixed candidate differs')
    return result,{'fixed_regions':len(PAIRS),'inverse':True,'untouched_complement':True}
