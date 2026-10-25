#ifndef TINY_H
#define TINY_H
#include <stdint.h>
#include <stddef.h>
#include <stdatomic.h>
#include <limits.h>

/* This candidate supplies these operations itself: no libc or TLS ABI. */
void *memcpy(void *,const void *,size_t);
void *memset(void *,int,size_t);
int memcmp(const void *,const void *,size_t);
size_t strlen(const char *);
int strcmp(const char *,const char *);
int strncmp(const char *,const char *,size_t);
char *strchr(const char *,int);
char *strstr(const char *,const char *);
char *strtok_r(char *,const char *,char **);
long strtol(const char *,char **,int);
_Noreturn void abort(void);
static inline int abs(int n){return n<0?-n:n;}
#if DEV
extern int tiny_errno;
#define errno tiny_errno
#define toupper(c) ((c)>='a'&&(c)<='z'?(c)-32:(c))
#define isupper(c) ((c)>='A'&&(c)<='Z')
#endif

#ifndef WORKERS
#define WORKERS 2
#endif
#ifndef TT_BITS
#define TT_BITS 18
#endif
#ifndef DEV
#define DEV 0
#endif
#ifndef PLY
#define PLY 128
#endif
/* Admission preserves <=16 pieces/side; each piece has <=27 pseudo moves,
 * including all promotions/castles, so the conservative bound is 432. */
#define MOVES 512
#define HISTORY 4096
#define MATE 30000
typedef unsigned Move;
/* Absolute a1=0 .. h8=63; color 0 white / 1 black, piece kinds P..K=0..5.
 * The eight bitboards are the sole piece-placement authority. No cached king
 * square, signed-piece mailbox or secondary occupancy needs synchronization.
 * h is the legal-EP repetition key, r the ordered reversible TT context. */
typedef struct { uint64_t color[2],pieces[6]; int s,c,e,half,v; uint64_t h,r; } Board;
#define OCC(p) ((p)->color[0]|(p)->color[1])
#define KING(p,c) (__builtin_ctzll((p)->pieces[5]&(p)->color[c]))
static inline int piece_at(const Board *p,int sq){
    uint64_t bit=UINT64_C(1)<<sq;
    for(int kind=0;kind<6;kind++)if(p->pieces[kind]&bit)return kind+1;
    return 0;
}
int attacked(const Board *,int,int);
int gen(const Board *,Move *);
int make(const Board *,Move,Board *);
int dead(const Board *);
void start(Board *);
#if DEV
int fen(Board *,const char *);
int verify_board(const Board *);
#endif
uint64_t mix(uint64_t);
int value(int,int,int);
#define FROM(m) ((m)&63)
#define TO(m) (((m)>>6)&63)
#define PROMO(m) (((m)>>12)&7)
#define KIND(m) (((m)>>15)&7)
#define CAP(m) (((m)>>18)&7)
#define MOVE(f,t,p,k,c) ((Move)(f)|((Move)(t)<<6)|((Move)(p)<<12)|((Move)(k)<<15)|((Move)(c)<<18))

typedef struct { atomic_flag lock; uint64_t key,data; } Entry;
typedef struct {
    int id,depth,score; Move best;
    uint64_t nodes,keys[HISTORY+PLY]; int length;
    int16_t history[64][64],continuation[13][13],correction[1024];
#if DEV
    uint64_t pvs,qs,hits,hist_updates,cont_updates,corr_updates,corr_uses,ply_aborts;
#endif
} Worker;
_Static_assert(ATOMIC_INT_LOCK_FREE==2,"syscall pool requires lock-free int atomics");
extern Entry *table;
extern Worker workers[WORKERS];
extern atomic_int stopped;
extern uint64_t deadline;
#if DEV
extern uint64_t limit;
extern int max_depth;
extern atomic_uint_fast64_t searched;
#endif
extern Board position;
extern uint64_t game_keys[HISTORY];
extern int game_length;
uint64_t now(void);
void think(Worker *,const Board *);
#endif
