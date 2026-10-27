"""Decode one UCI move once instead of spelling every generated move.

The generated legal move remains the authority, including its capture marker.
This representation candidate preserves exact NUL-token acceptance, full NBRQ
promotion, first-legal fallback and failed-position rollback in the caller.
"""

RESOLVER = r'''static Move resolve_move(const Board *b,Span token,Board *child){
    Move wanted=0;
    if(token&&*token){
        unsigned square[2]={0,0},promotion=0;
        for(unsigned i=0;i<4;i++){
            unsigned digit=(unsigned)(token[i]-(i&1?'1':'a'));
            if(digit>7)return 0;
            square[i/2]|=digit<<((i&1)*4);
        }
        if(token[4]){
            for(promotion=2;promotion<6&&"  nbrq"[promotion]!=token[4];promotion++);
            if(promotion==6||token[5])return 0;
        }
        wanted=MOVE(square[0],square[1],promotion);
    }
    Move list[MOVES];int count=gen(b,list);
    for(int index=0;index<count;index++){
        if(token&&*token&&(list[index]&~8u)!=wanted)continue;
        if(make(b,list[index],child))return list[index];
        if(token&&*token)return 0;
    }
    return 0;
}
'''


def apply(files):
    result = dict(files)
    text = files["runtime.c"].decode()
    begin, end = "static Move resolve_move(", "static int parse_apply("
    if text.count(begin) != 1 or text.count(end) != 1:
        raise ValueError("unique move resolver and consumer required")
    first, last = text.index(begin), text.index(end)
    old = text[first:last]
    if last <= first or "text(list[index],name);if(!word(token,name))continue;" not in old:
        raise ValueError("exact generated-move spelling resolver required")
    if b"#define FROM(m) ((m)&119)" not in files["tiny.h"]:
        raise ValueError("0x88 move with low capture-marker bit required")
    result["runtime.c"] = (text[:first] + RESOLVER + text[last:]).encode()
    return result
