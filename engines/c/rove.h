#ifndef ROVE_H
#define ROVE_H
#define _POSIX_C_SOURCE 200809L
#include <stdint.h>
#include <stdatomic.h>
#include <pthread.h>
#include <stddef.h>
#ifndef ROVE_VARIANT
#define ROVE_VARIANT 1
#endif
#ifndef ROVE_WORKERS
#define ROVE_WORKERS 2
#endif
#ifndef ROVE_TT_BITS
#define ROVE_TT_BITS 16
#endif
#ifndef ROVE_DEV
#define ROVE_DEV 0
#endif
#ifndef ROVE_PARALLEL
#define ROVE_PARALLEL 0
#endif
#ifndef ROVE_MODEL
#define ROVE_MODEL 0
#endif
#if ROVE_WORKERS < 1 || ROVE_WORKERS > 512
#error ROVE_WORKERS must be between 1 and 512
#endif
#if ROVE_TT_BITS < 8 || ROVE_TT_BITS > 28
#error ROVE_TT_BITS must be between 8 and 28
#endif
#define MAXPLY 96
#define MAXMOVES 256
#define MAXHISTORY 4096
#define INF 32000
#define MATE 30000
#define FROM(m) ((int)((m)&127))
#define TO(m) ((int)(((m)>>7)&127))
#define PROM(m) ((int)(((m)>>14)&7))
#define MOVE(f,t,p) ((unsigned)((f)|((t)<<7)|((p)<<14)))
typedef struct {
    int b[128], side, castle, ep, half, full, king[2], material, hce;
    uint64_t key, pawnkey, bb[2][7], occ[2];
} Board;
typedef struct { unsigned m; int score; } Move;
typedef struct { _Atomic uint64_t key, data; } TTEntry;
typedef struct Worker Worker;
typedef struct {
    Board board;
    uint64_t history[MAXHISTORY];
    int history_len, depth;
    uint64_t node_limit, deadline, start;
    _Atomic int stop;
    _Atomic uint64_t nodes;
    pthread_mutex_t mutex;
    unsigned best;
    int score, completed_depth;
    uint64_t generation, assigned, reassigned, reused, shared_bounds, clauses, repairs;
    int parallel_mode, groups;
    Worker *workers;
} Session;
struct Worker {
    Session *session;
    int id, seldepth, aborted;
    uint64_t nodes, path[MAXHISTORY+MAXPLY];
    int path_len;
    int history[2][128][128], continuation[13][13];
    int correction[2][1024];
    unsigned killers[MAXPLY][2], previous[MAXPLY], pv[MAXPLY][MAXPLY];
    int pvlen[MAXPLY];
    TTEntry *table;
    size_t table_mask;
    unsigned hint;
    int hint_ply;
};
extern TTEntry *rove_tt;
extern const int rove_value[7];
extern _Atomic uint64_t rove_see_calls, rove_singular_calls, rove_simd_calls, rove_model_calls, rove_mtd_probes;
void board_init(void);
int board_fen(Board *,const char *);
void board_start(Board *);
void board_format(const Board *,char *,int);
uint64_t board_key(const Board *);
int board_invariant(const Board *);
int attacked(const Board *,int,int);
uint64_t attackers(const Board *,int,int);
int in_check(const Board *);
int make_move(const Board *,unsigned,Board *);
int generate(const Board *,Move *,int);
uint64_t perft(const Board *,int);
unsigned parse_move(const Board *,const char *);
void move_string(unsigned,char *);
int evaluate_scalar(const Board *);
int evaluate_reference(const Board *);
int hce_piece(int,int);
void evaluate_init(void);
int evaluate(const Board *);
int see(const Board *,unsigned);
int drawn(const Board *,const uint64_t *,int);
uint64_t now_ms(void);
int search(Worker *,const Board *,int,int,int,int,unsigned,int);
void *worker_run(void *);
void *session_run(void *);
void tt_clear(void);
int parallel_init(void);
void parallel_shutdown(void);
#endif
