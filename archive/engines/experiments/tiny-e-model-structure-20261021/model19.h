/* e-hand-quadratic-19-1. Hand-authored, UNTRAINED; no data/quantization.
 * Readable model fragment for the exact shipping candidate. The ordinary
 * transform carries these same token bodies in fixed literal regions.
 * Requires the candidate's private za board and FROM/TO/PROMO/mix.
 *
 * 0..4: material PNBRQ. 5..10: center PNBRQK. 11: pawn advance.
 * 12: side-to-move tempo. 13: quadratic gain. 14..18: ordering
 * victim material, capture attacker material, promotion gain, center delta,
 * pawn rank delta. Static signed16 values are stored exactly.
 *
 * Compared with old E21, doubled/isolated pawn and bishop-pair features
 * are removed, and global signed activity interaction is added. This is a
 * declared model change, not an encoding or equality claim for frozen.json.
 * |M|<=14400, |A|<=1728, |A*abs(A)|<=2985984, |raw|<=39466;
 * these conservative bounds use at most16 pieces per color. C division
 * truncates toward zero, so the quadratic residual is exactly odd.
 * Equal white/black activity cancels before the nonlinearity by definition.
 */
static const int16_t tiny_weights[19]={
    100,320,330,500,900, 3,8,5,2,1,-3, 6,10,1, 16,-1,12,2,4
};
static int Q(int q){
    int f=q&7,r=q>>4;
    return(f<4?f:7-f)+(r<4?r:7-r);
}
/* Called only with a nonzero piece and delta -1/+1 by put. Hash output
 * stays exact; material/activity state belongs privately to this board. */
static uint64_t piece(za*p,int v,int q,int d){
    int a=abs(v),s=v>0?d:-d;
    p->v+=s*(a<6?tiny_weights[a-1]:0);
    p->a+=s*(tiny_weights[a+4]*Q(q)+
        (a==1?tiny_weights[11]*((v<0?7-(q>>4):q>>4)-1):0));
    return mix((uint64_t)(q+(v+6)*128));
}
/* Actual white-perspective inference. g(A)=A+A*abs(A)/128 is nonadditive:
 * g(32)=40 while g(16)+g(16)=36. Search applies side after the clamp. */
static int S(const za*p){
    int s=p->v+p->a+tiny_weights[13]*p->a*abs(p->a)/128+
        p->s*tiny_weights[12];
    return s>20000?20000:s< -20000?-20000:s;
}
/* The original five-feature ordering model, with its exact coefficients.
 * No ordering score is a normal TT bound. Called on pseudo moves before make. */
static int R(const za*p,Move m){
    int d=FROM(m),f=TO(m),i=p->b[d],a=abs(i),v=abs(p->b[f]),j=PROMO(m);
    if(a==1&&f==p->e&&!v)v=1;
    int s=tiny_weights[17]*(Q(f)-Q(d));
    if(v)s+=tiny_weights[14]*(v<6?tiny_weights[v-1]:0)+
        tiny_weights[15]*(a<6?tiny_weights[a-1]:0);
    if(j)s+=tiny_weights[16]*(tiny_weights[j-1]-tiny_weights[0]);
    if(a==1)s+=tiny_weights[18]*((f>>4)-(d>>4))*(i<0?-1:1);
    return s;
}
