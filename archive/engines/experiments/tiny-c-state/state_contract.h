#ifndef ROVE_STATE_CONTRACT_H
#define ROVE_STATE_CONTRACT_H
#include <stddef.h>
#include <stdint.h>

/* Fixture-only ABI. No Board layout is shared between the two production
 * translation units, and padding/cached fields are never normalized by copy. */
typedef struct {
    int8_t cells[128];
    int side,rights,ep,kings[2],halfmove;
    uint64_t hash,reversible;
} RoveStateSnapshot;

typedef struct {
    const char *label;
    size_t board_bytes;
    void (*initial)(void *);
    int (*fixture_fen)(void *,const char *);
    int (*generate)(const void *,unsigned *);
    int (*play)(const void *,unsigned,void *);
    void (*snapshot)(const void *,RoveStateSnapshot *);
    int (*raw)(const void *);
    int (*piece_value)(int,int);
    int (*table_term)(int,int);
    int (*dead_position)(const void *);
    uint64_t (*tt_key)(const void *);
    int (*cached_white)(const void *);
} RoveStateAPI;

extern const RoveStateAPI rove_state_baseline,rove_state_candidate;
#endif
