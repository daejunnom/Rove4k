#include "rove.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <inttypes.h>

static void stop_search(Session *s,pthread_t thread,int *running){(void)thread;if(*running){atomic_store_explicit(&s->stop,1,memory_order_relaxed);pthread_mutex_lock(&s->control);while(s->pending||s->active)pthread_cond_wait(&s->finished,&s->control);pthread_mutex_unlock(&s->control);*running=0;}}
static void *coordinator(void *arg){Session *s=arg;pthread_mutex_lock(&s->control);for(;;){while(!s->pending&&!s->quitting)pthread_cond_wait(&s->command,&s->control);if(s->quitting)break;s->pending=0;s->active=1;pthread_mutex_unlock(&s->control);session_run(s);pthread_mutex_lock(&s->control);s->active=0;pthread_cond_broadcast(&s->finished);}pthread_mutex_unlock(&s->control);return NULL;}
static int coordinator_init(Session *s,pthread_t *thread){int error=pthread_mutex_init(&s->control,NULL);if(error)goto failed_mutex;error=pthread_cond_init(&s->command,NULL);if(error)goto failed_command;error=pthread_cond_init(&s->finished,NULL);if(error)goto failed_finished;error=pthread_create(thread,NULL,coordinator,s);if(!error)return 1;pthread_cond_destroy(&s->finished);failed_finished:pthread_cond_destroy(&s->command);failed_command:pthread_mutex_destroy(&s->control);failed_mutex:fprintf(stderr,"Rove4k: coordinator startup failed (%d)\n",error);return 0;}
static void coordinator_shutdown(Session *s,pthread_t thread){pthread_mutex_lock(&s->control);s->quitting=1;pthread_cond_signal(&s->command);pthread_mutex_unlock(&s->control);int error=pthread_join(thread,NULL);if(error){fprintf(stderr,"Rove4k: coordinator join failed (%d)\n",error);abort();}pthread_cond_destroy(&s->finished);pthread_cond_destroy(&s->command);pthread_mutex_destroy(&s->control);}
static unsigned first_legal(const Board *p){Move moves[MAXMOVES];int n=generate(p,moves,0);for(int i=0;i<n;i++){Board t;if(make_move(p,moves[i].m,&t))return moves[i].m;}return 0;}
static void reply(Session *s,const char *line){pthread_mutex_lock(&s->mutex);puts(line);fflush(stdout);pthread_mutex_unlock(&s->mutex);}
static void position(Board *p,uint64_t *history,int *len,char *args){
    Board t;char *moves=strstr(args," moves ");if(moves){*moves=0;moves+=7;}
    if(!strcmp(args,"startpos"))board_start(&t);
#if ROVE_DEV
    else if(!strncmp(args,"fen ",4)){if(!board_fen(&t,args+4))return;}
#endif
    else return;
    uint64_t temp[MAXHISTORY];int n=1;temp[0]=t.key;
    if(moves){char *save=NULL;for(char *s=strtok_r(moves," \t\r\n",&save);s;s=strtok_r(NULL," \t\r\n",&save)){unsigned m=parse_move(&t,s);Board next;if(!m||!make_move(&t,m,&next)||n>=MAXHISTORY)return;t=next;temp[n++]=t.key;}}
    *p=t;*len=n;memcpy(history,temp,(size_t)n*sizeof(uint64_t));
}
static uint64_t number(const char *s){if(!s||*s=='-')return 0;return strtoull(s,NULL,10);}
int main(void){
    board_init();evaluate_init();
    rove_tt=calloc((size_t)1<<ROVE_TT_BITS,sizeof(TTEntry));if(!rove_tt)return 2;tt_clear();
    Board board;board_start(&board);uint64_t history[MAXHISTORY];int history_len=1;history[0]=board.key;
    Session session={0};pthread_mutex_init(&session.mutex,NULL);atomic_init(&session.stop,0);atomic_init(&session.nodes,0);
    session.workers=calloc(ROVE_WORKERS,sizeof(Worker));if(!session.workers){free(rove_tt);pthread_mutex_destroy(&session.mutex);return 2;}
    if(!parallel_init()){free(session.workers);free(rove_tt);pthread_mutex_destroy(&session.mutex);return 2;}
    pthread_t thread={0};if(!coordinator_init(&session,&thread)){parallel_shutdown();free(session.workers);free(rove_tt);pthread_mutex_destroy(&session.mutex);return 2;}int running=0;char line[32768];
    while(fgets(line,sizeof line,stdin)){size_t length=strlen(line);if(length&&line[length-1]!='\n'&&!feof(stdin)){int ch;while((ch=getchar())!='\n'&&ch!=EOF){}continue;}while(length&&(line[length-1]=='\r'||line[length-1]=='\n'||line[length-1]==' '))line[--length]=0;
        if(!strcmp(line,"uci")){char b[128];snprintf(b,sizeof b,"id name Rove4k C-%c\nid author Rove4k\nuciok",'A'+ROVE_VARIANT-1);reply(&session,b);}
        else if(!strcmp(line,"isready"))reply(&session,"readyok");
        else if(!strcmp(line,"quit")){stop_search(&session,thread,&running);break;}
        else if(!strcmp(line,"stop"))stop_search(&session,thread,&running);
        else if(!strcmp(line,"ucinewgame")){stop_search(&session,thread,&running);tt_clear();}
        else if(!strncmp(line,"position ",9)){stop_search(&session,thread,&running);position(&board,history,&history_len,line+9);}
        else if(!strcmp(line,"go")||!strncmp(line,"go ",3)){
            stop_search(&session,thread,&running);session.board=board;session.history_len=history_len;memcpy(session.history,history,(size_t)history_len*sizeof(uint64_t));session.depth=MAXPLY-2;session.node_limit=0;session.deadline=0;session.completed_depth=0;session.score=0;session.best=first_legal(&board);session.start=now_ms();session.generation++;session.assigned=session.reassigned=session.reused=session.shared_bounds=session.clauses=session.repairs=0;session.parallel_mode=ROVE_PARALLEL;session.groups=1;uint64_t clock=0,increment=0,movetime=0;int infinite=0,clock_present=0;
            char *save=NULL;for(char *token=strtok_r(line+2," \t",&save);token;token=strtok_r(NULL," \t",&save)){
                if(!strcmp(token,"wtime")||!strcmp(token,"btime")){int side=*token=='w'?1:-1;char *value=strtok_r(NULL," \t",&save);if(side==board.side){clock=number(value);clock_present=1;}}
                else if(!strcmp(token,"winc")||!strcmp(token,"binc")){int side=*token=='w'?1:-1;char *value=strtok_r(NULL," \t",&save);if(side==board.side)increment=number(value);}
#if ROVE_DEV
                else if(!strcmp(token,"depth")){uint64_t d=number(strtok_r(NULL," \t",&save));if(d>0&&d<MAXPLY-1)session.depth=(int)d;}
                else if(!strcmp(token,"nodes"))session.node_limit=number(strtok_r(NULL," \t",&save));
                else if(!strcmp(token,"movetime"))movetime=number(strtok_r(NULL," \t",&save));
                else if(!strcmp(token,"infinite"))infinite=1;
#endif
            }
            if(!infinite){uint64_t budget=movetime;if(!budget&&clock_present){budget=clock/30+(increment>UINT64_C(86400000)?UINT64_C(86400000):increment)*3/4;if(budget>clock/5)budget=clock/5;if(!budget)budget=1;}if(budget>UINT64_C(86400000))budget=UINT64_C(86400000);if(budget)session.deadline=session.start+budget;}
            atomic_store_explicit(&session.stop,0,memory_order_relaxed);atomic_store_explicit(&session.nodes,0,memory_order_relaxed);
            pthread_mutex_lock(&session.control);session.pending=1;pthread_cond_signal(&session.command);pthread_mutex_unlock(&session.control);running=1;
        }
#if ROVE_DEV
        else if(!strncmp(line,"perft ",6)){stop_search(&session,thread,&running);uint64_t depth=number(line+6);if(depth<=8)printf("perft %d %" PRIu64 "\n",(int)depth,perft(&board,(int)depth));fflush(stdout);}
        else if(!strcmp(line,"legal")){stop_search(&session,thread,&running);Move moves[MAXMOVES];int n=generate(&board,moves,0);printf("legal");for(int i=0;i<n;i++){Board t;if(make_move(&board,moves[i].m,&t)){char b[8];move_string(moves[i].m,b);printf(" %s",b);}}puts("");fflush(stdout);}
        else if(!strcmp(line,"fen")){stop_search(&session,thread,&running);char b[128];board_format(&board,b,sizeof b);printf("fen %s\n",b);fflush(stdout);}
        else if(!strcmp(line,"eval")){stop_search(&session,thread,&running);printf("eval %d\n",evaluate(&board));fflush(stdout);}
        else if(!strcmp(line,"state")){stop_search(&session,thread,&running);printf("{\"hash\":\"%016" PRIx64 "\",\"pawn_hash\":\"%016" PRIx64 "\",\"halfmove\":%d,\"fullmove\":%d,\"side\":%d,\"eval\":%d,\"draw\":%s,\"invariant\":%s}\n",board.key,board.pawnkey,board.half,board.full,board.side,evaluate(&board),drawn(&board,history,history_len)?"true":"false",board_invariant(&board)?"true":"false");fflush(stdout);}
        else if(!strncmp(line,"see ",4)){stop_search(&session,thread,&running);unsigned m=parse_move(&board,line+4);if(m){int value=see(&board,m);if(value==SEE_INCOMPLETE)puts("see incomplete");else printf("see %s %d\n",line+4,value);}else puts("see illegal");fflush(stdout);}
        else if(!strcmp(line,"verify")){stop_search(&session,thread,&running);int tested=0,good=board_invariant(&board);Move moves[MAXMOVES];int n=generate(&board,moves,0);for(int i=0;i<n;i++){Board t;if(make_move(&board,moves[i].m,&t)){tested++;good&=board_invariant(&t);
                    good&=evaluate_reference(&t)==evaluate(&t);
                }}printf("verify %s positions %d\n",good?"pass":"fail",tested+1);fflush(stdout);}
        else if(!strcmp(line,"stats")){stop_search(&session,thread,&running);printf("{\"variant\":%d,\"workers\":%d,\"total_threads\":%d,\"tt_bytes\":%zu,\"see\":%" PRIu64 ",\"singular\":%" PRIu64 ",\"simd\":%" PRIu64 ",\"model\":%" PRIu64 ",\"mtd_probes\":%" PRIu64 ",\"mtd_conflicts\":%" PRIu64 ",\"mtd_converged\":%" PRIu64 ",\"nodes\":%" PRIu64 ",\"completed_depth\":%d,",ROVE_VARIANT,ROVE_WORKERS,ROVE_WORKERS+1,sizeof(TTEntry)*((size_t)1<<ROVE_TT_BITS),atomic_load(&rove_see_calls),atomic_load(&rove_singular_calls),atomic_load(&rove_simd_calls),atomic_load(&rove_model_calls),atomic_load(&rove_mtd_probes),atomic_load(&rove_mtd_conflicts),atomic_load(&rove_mtd_converged),atomic_load(&session.nodes),session.completed_depth);printf("\"parallel\":%d,\"groups\":%d,\"assigned\":%" PRIu64 ",\"reassigned\":%" PRIu64 ",\"reused\":%" PRIu64 ",\"shared_bounds\":%" PRIu64 ",\"clauses\":%" PRIu64 ",\"repairs\":%" PRIu64 ",\"worker_bytes\":%zu}\n",session.parallel_mode,session.groups,session.assigned,session.reassigned,session.reused,session.shared_bounds,session.clauses,session.repairs,sizeof(Worker)*(size_t)ROVE_WORKERS);fflush(stdout);}
#endif
    }
    stop_search(&session,thread,&running);coordinator_shutdown(&session,thread);parallel_shutdown();free(session.workers);free(rove_tt);pthread_mutex_destroy(&session.mutex);return 0;
}
