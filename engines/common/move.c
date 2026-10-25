/* Shared move application and mailbox walk. The canonical template owns
 * the preconditions, Board layout and selected attack adapter. Promotion and
 * legality policy are unchanged by source composition. */

/* rove:begin walk */
static int walk(const Board *p,Move *moves,int sq,int s){
    int n=0;
    for(int from=0;from<128;from++){
        if(from&0x88){from+=7;continue;}
        int a=abs(p->b[from]);if(p->b[from]*s<=0)continue;
        if(moves&&a==1){
            int to=from+s*16;
            if(!(to&0x88)&&!p->b[to]){
                add(moves,&n,from,to,1);
                if((from>>4)==(s>0?1:6)&&!p->b[to+s*16])add(moves,&n,from,to+s*16,0);
            }
        }
        int first=a==1?(s>0?12:14):a==2?0:a==3?12:8;
        int last=a==1?first+2:a==2?8:a==4?12:16;
        for(int i=first;i<last;i++){
            int d=steps[i];
            for(int to=from+d;!(to&0x88);to+=d){
                int target=p->b[to];
                if(!moves&&to==sq)return 1;
                if(target*s>0||(moves&&a==1&&!target&&to!=p->e))break;
                if(moves)add(moves,&n,from,to,a==1);
                if(target||a<3||a==6)break;
            }
        }
        if(moves&&a==6){
            int home=s>0?4:116,shift=s>0?0:2;
            if(from==home&&!attacked(p,home,-s)){
                if((p->c&(1<<shift))&&!p->b[home+1]&&!p->b[home+2]&&!attacked(p,home+1,-s))add(moves,&n,from,home+2,0);
                if((p->c&(2<<shift))&&!p->b[home-1]&&!p->b[home-2]&&!p->b[home-3]&&!attacked(p,home-1,-s))add(moves,&n,from,home-2,0);
                }
        }
    }
    return n;
}
/* rove:end walk */

/* rove:begin make */
int make(const Board *p,Move m,Board *t){
    int from=FROM(m),to=TO(m),prom=PROMO(m),s=p->s;
    int v=p->b[from],target=p->b[to];
    if(abs(target)==6)return 0;
    *t=*p;t->h^=state(p);t->half++;t->e=-1;
    if(abs(v)==1){
        t->half=0;
        if(to==p->e&&!target)put(t,to-s*16,0);
        if(abs(to-from)==32)t->e=from+s*16;
        if(prom)v=s*prom;
    }
    if(target)t->half=0;
    if(abs(v)==6&&abs(to-from)==2){
        int rook=to>from?from+3:from-4,transit=to>from?from+1:from-1;
        put(t,rook,0);put(t,transit,s*4);
    }
    put(t,from,0);put(t,to,v);t->c&=~(rights(from)|rights(to));t->s=-s;
    if(attacked(t,t->k[s<0],-s))return 0;
    ep(t);t->h^=state(t);
    /* TT context retains the ordered reversible path. A pawn move or capture
     * resets it; repeated boards reached along distinct paths stay distinct. */
    t->r=t->half?((p->r<<1)|(p->r>>63))^t->h:t->h;
    return 1;
}
/* rove:end make */

/* rove:begin attacked */
int attacked(const Board *p,int sq,int side){return walk(p,0,sq,side);}
/* rove:end attacked */

/* rove:begin gen */
int gen(const Board *p,Move *moves){return walk(p,moves,0,p->s);}
/* rove:end gen */

/* rove:begin add */
static void add(Move *moves,int *n,int from,int to,int pawn){
    int promotion=pawn&&((to>>4)==0||(to>>4)==7);
    for(int z=promotion?2:0;z<=(promotion?5:0);z++){
        if(*n>=MOVES)abort();
        moves[(*n)++]=MOVE(from,to,z);
    }
}
/* rove:end add */

/* rove:begin capture */
static int capture(const Board *p,Move m){return p->b[TO(m)]||
    (abs(p->b[FROM(m)])==1&&TO(m)==p->e);}
/* rove:end capture */
