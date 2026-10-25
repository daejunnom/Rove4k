/* Fixture ports only. engine.c is an exact old/new readable; DEV=0 is retained.
 * The generated fen-port.inc copies canonical DEV FEN admission verbatim,
 * changing its name to fixture_fen. The shipping protocol gains no command. */
#define main fixture_engine_main
#include "engine.c"
#undef main
#include <ctype.h>
#include <errno.h>
#include "fen-port.inc"

static void snapshot(const Board *p){
    printf("{\"b\":[");
    for(int i=0;i<128;i++)printf("%s%d",i?",":"",p->b[i]);
    printf("],\"s\":%d,\"c\":%d,\"e\":%d,\"k\":[%d,%d],\"half\":%d,\"v\":%d,\"h\":\"%016llx\",\"r\":\"%016llx\"}",
           p->s,p->c,p->e,p->k[0],p->k[1],p->half,p->v,
           (unsigned long long)p->h,(unsigned long long)p->r);
}

int main(void){
    char line[4096];int index=0;
    while(fgets(line,sizeof line,stdin)){
        size_t length=strlen(line);if(!length||line[length-1]!='\n')return 2;line[length-1]=0;
        char *save,*fen_s=strtok_r(line,"\t",&save),*moves=strtok_r(NULL,"\t",&save),*depth_s=strtok_r(NULL,"\t",&save);
        if(!fen_s||!moves||!depth_s||strtok_r(NULL,"\t",&save))return 3;
        Board b;if(!fixture_fen(&b,fen_s))return 4;
        printf("{\"index\":%d,\"initial\":",index++);snapshot(&b);printf(",\"replay\":[");
        int replayed=0;
        if(strcmp(moves,"-"))for(char *part=strtok_r(moves," ",&save);part;part=strtok_r(NULL," ",&save)){
            Board child;Move move=parse(&b,part,&child);if(!move)return 5;b=child;
            printf("%s{\"move\":\"%s\",\"state\":",replayed++?",":"",part);snapshot(&b);printf("}");
        }
        printf("],\"root\":");snapshot(&b);printf(",\"attacks\":[");
        for(int side=0;side<2;side++){
            printf("%s[",side?",":"");
            for(int q=0;q<64;q++)printf("%s%d",q?",":"",attacked(&b,(q&7)+(q>>3)*16,side?-1:1));
            printf("]");
        }
        Move list[MOVES];int n=gen(&b,list),legal=0;printf("],\"pseudo_count\":%d,\"children\":[",n);
        for(int i=0;i<n;i++){
            Board child;if(!make(&b,list[i],&child))continue;char name[6];text(list[i],name);
            printf("%s{\"move\":\"%s\",\"state\":",legal++?",":"",name);snapshot(&child);printf("}");
        }
        printf("]");
        int depth=atoi(depth_s);
        if(depth){
            if(depth!=2)return 6;
            table=calloc((size_t)1<<TT_BITS,sizeof *table);if(!table)return 7;clear();
            Worker *w=workers;memset(w,0,sizeof *w);w->length=1;w->keys[0]=b.h;
            deadline=now()+5000;atomic_store(&stopped,0);Move best=0;
            int score=search(w,&b,depth,-MATE,MATE,0,6,&best);char name[6];text(best,name);
            printf(",\"search\":{\"depth\":%d,\"score\":%d,\"best\":\"%s\",\"nodes\":%llu,\"stopped\":%d}",
                   depth,score,name,(unsigned long long)w->nodes,atomic_load(&stopped));
            free(table);table=NULL;
        }
        puts("}");fflush(stdout);
    }
    return ferror(stdin)?8:0;
}
