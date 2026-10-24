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
/* 0x88: a1=0, h8=119. Signed P/N/B/R/Q/K = 1..6, white positive.
 * h is the FIDE repetition key, v incremental white HCE, r the reversible
 * path digest used only for TT context. e=-1 means no LEGAL en passant.
 */
typedef struct { int s,c,e,k[2],half,v; uint64_t h,r; int8_t b[128]; } Board;
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
int value(int,int);
#define FROM(m) ((m)&127)
#define TO(m) (((m)>>7)&127)
#define PROMO(m) (((m)>>14)&7)
#define MOVE(f,t,p) ((Move)(f)|((Move)(t)<<7)|((Move)(p)<<14))

typedef struct { atomic_flag lock; uint64_t key,data; } Entry;
typedef struct {
    int id,depth,score; Move best;
    uint64_t nodes,keys[HISTORY+PLY]; int length;
    int16_t history[128][128],continuation[13][13],correction[1024];
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
