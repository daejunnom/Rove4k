#ifndef TINY_H
#define TINY_H
#define _POSIX_C_SOURCE 200809L
#include <stdint.h>
#include <stdatomic.h>
#include <pthread.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <limits.h>

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
#ifndef CONTROLLED
#define CONTROLLED 1
#endif
#define WHITE 8
#define BLACK 16
#define EDGE 24
#define TYPE(v) ((v)&7)
#define SIDE(s) ((s)>>4)
#define OTHER(s) ((s)^24)
#define DIR(s) ((s)==WHITE?10:-10)
#define FILE_OF(q) ((q)%10-1)
#define RANK_OF(q) ((q)/10-2)
#define OLD_SQUARE(q) (RANK_OF(q)*16+FILE_OF(q))
#if CONTROLLED
#define ORDER_MOVE(m) MOVE(OLD_SQUARE(FROM(m)),OLD_SQUARE(TO(m)),PROMO(m))
#else
#define ORDER_MOVE(m) (m)
#endif
/* Admission preserves <=16 pieces/side; each piece has <=27 pseudo moves,
 * including all promotions/castles, so the conservative bound is 432. */
#define MOVES 512
#define HISTORY 4096
#define MATE 30000
typedef unsigned Move;
/* 10x12 sentinel mailbox: a1=21, h8=98; low three bits P/N/B/R/Q/K=1..6.
 * WHITE=8, BLACK=16, empty=0; all offboard cells contain both colours=24.
 * A target's own-colour bit therefore tests friendly and boundary together.
 * h is the FIDE repetition key, v incremental white HCE, r the reversible
 * path digest used only for TT context. e=-1 means no LEGAL en passant.
 */
typedef struct { uint8_t b[120]; int s,c,e,k[2],half,v; uint64_t h,r; } Board;
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
    int16_t history[120][120],continuation[13][13],correction[1024];
#if DEV
    uint64_t pvs,qs,hits,hist_updates,cont_updates,corr_updates,corr_uses,ply_aborts;
#endif
} Worker;
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
