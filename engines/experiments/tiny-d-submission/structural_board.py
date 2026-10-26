"""Closed D board alternatives for the structural size experiment.

These pure projections consume the composed, readable D source mapping. The
caller owns the complete input cohort and its observation contract; matching a
function name is not a proof for arbitrary C. Each projection fails when a
required source role is absent. This module performs no I/O, compilation,
selection, publication, or runtime qualification. BEST is the board selection
to compare, not a claim that it is smallest in every compiler/codec context.

The retained alternatives include size losses so they can be remeasured under
a new complete-artifact context. apply() preserves the caller's option order;
incompatible compositions fail instead of silently selecting a fallback.

Required board invariants
-------------------------
* s is +1 or -1; b holds signed P/N/B/R/Q/K=1..6; each side has one king and
  at most 16 pieces. Generated endpoints are valid 0x88 squares, 0..119.
* make() consumes gen() members, plus the documented provisional EP trial.
  Promotion remains N/B/R/Q in the original order. Capacity and king-safety
  checks remain active.
* Castling rights can only be cleared by moves. start() establishes the home
  king/rook relation and FEN admission clears incompatible rights. Thus a
  surviving side-specific right proves its unique king is on the home square.
* put() owns mailbox, piece hash, evaluation and king-square maintenance. The
  optional material signature joins that same owner; no caller updates it
  independently.

The material signature uses four five-bit counts: dark-square bishops in bits
0..4, light-square bishops in bits 5..9, knights in bits 10..14, and pawns/rooks/queens in
bits 15..19. Two kings and at most 32 pieces bound every count by 30. Removing a
present piece cannot borrow into another count, and adding one cannot carry.
The unsigned subtraction in the shared put loop is defined modulo 2^32; its
final value equals the bounded count sum. The new unsigned field occupies the
existing four-byte padding before h on the admitted x86-64 ABI: Board remains
176 bytes, material is at 28, h at 32, and the mailbox at 48. DEV verification
rebuilds the signature from put() and checks it along with evaluation.

No variant below is a chess feature reduction or a generic minifier rule.
"""


def function(data, prefix):
    if data.count(prefix) != 1:
        raise ValueError("one exact D function role required: " + repr(prefix))
    start = data.index(prefix)
    opening = data.index(b"{", start)
    depth = 0
    for end in range(opening, len(data)):
        if data[end] == 123:
            depth += 1
        elif data[end] == 125:
            depth -= 1
            if not depth:
                return data[start:end + 1]
    raise ValueError("unclosed known C function")


def replace_function(files, prefix, after):
    result = dict(files)
    data = result["board.c"]
    before = function(data, prefix)
    if data.count(before) != 1:
        raise ValueError("one exact function body required")
    result["board.c"] = data.replace(before, after)
    return result


# This is test-only C. It includes the actual emitted board, rebuilds the
# incremental observations after every legal transition, and emits one stable
# fingerprint for comparison with the original board under the same compiler.
# No code is compiled or run while importing this pure projection module.
_LIFECYCLE_PROBE = rb'''#include <stdio.h>
#include <string.h>
#include "board.c"
#ifdef CHECK_MATERIAL
_Static_assert(sizeof(Board)==176 && offsetof(Board,material)==28 &&
               offsetof(Board,h)==32 && offsetof(Board,b)==48,
               "material signature must reuse Board padding");
#endif
REFERENCE_DEAD
static uint64_t checksum=1469598103934665603ULL,positions;
static uint32_t random_state=0x5ad6e321;
static void hashword(uint64_t value){for(int i=0;i<8;i++){checksum^=value&255;checksum*=1099511628211ULL;value>>=8;}}
static int verify(const Board *p){
    int eval=0,kings[2]={-1,-1};uint64_t key=0;unsigned material=0;
    for(int q=0;q<128;q++){
        int v=p->b[q],a=abs(v);
        if(q&0x88){if(v)return 0;continue;}
        if(a>6)return 0;
        if(v){
            key^=piece(v,q);eval+=value(v,q);
            if(a==6)kings[v<0]=q;
            else if(a==2)material+=1024;
            else if(a==3)material+=1u<<(5*((q+(q>>4))&1));
            else material+=32768;
        }
        hashword((uint64_t)v);
    }
    if(eval!=p->v||key!=(p->h^state(p))||kings[0]!=p->k[0]||kings[1]!=p->k[1]||dead(p)!=reference_dead(p))return 0;
#ifdef CHECK_MATERIAL
    if(material!=p->material)return 0;
#endif
    hashword(p->s);hashword(p->c);hashword(p->e);hashword(p->half);hashword(p->v);
    hashword(p->h);hashword(p->r);hashword(dead(p));positions++;
    return 1;
}
static int inspect(const Board *p,Board *legal){
    Move moves[MOVES];int n=gen(p,moves),count=0;
    if(!verify(p))return -1;
    hashword(n);
    for(int i=0;i<n;i++){
        Board child;int good=make(p,moves[i],&child);
        hashword(moves[i]);hashword(good);
        if(good){
            if(!verify(&child))return -1;
            uint64_t expected=child.half?((p->r<<1)|(p->r>>63))^child.h:child.h;
            if(child.r!=expected)return -1;
            legal[count++]=child;
        }
    }
    return count;
}
static int replay(Board *p,const char *sequence){
    static const char promotion_letters[]="  nbrq";
    start(p);
    while(*sequence){
        int f=(sequence[0]-'a')+16*(sequence[1]-'1'),t=(sequence[2]-'a')+16*(sequence[3]-'1');
        sequence+=4;int promotion=0;
        if(*sequence&&*sequence!=' '){const char *letter=strchr(promotion_letters,*sequence++);if(!letter)return 0;promotion=(int)(letter-promotion_letters);}
        Move wanted=MOVE(f,t,promotion),moves[MOVES];int n=gen(p,moves),found=0;
        for(int i=0;i<n;i++)if((moves[i]&~8u)==wanted){Board child;if(!make(p,moves[i],&child))return 0;*p=child;found++;}
        if(found!=1||!verify(p))return 0;
        if(*sequence==' ')sequence++;
    }
    return 1;
}
static const char *fixtures[]={FIXTURES};
int main(void){
    static Board legal[MOVES];Board current;
    for(unsigned i=0;i<sizeof fixtures/sizeof *fixtures;i++){
        if(!replay(&current,fixtures[i])||inspect(&current,legal)<0)return 1;
    }
    for(int game=0;game<64;game++){
        start(&current);
        for(int ply=0;ply<256;ply++){
            int n=inspect(&current,legal);if(n<0)return 2;
            if(!n||current.half>=100||dead(&current))break;
            random_state=1664525*random_state+1013904223;
            current=legal[random_state%(unsigned)n];
        }
    }
    printf("positions=%llu checksum=%016llx\n",(unsigned long long)positions,(unsigned long long)checksum);
    return 0;
}
'''


def render_lifecycle_probe(reference_board, paths):
    """Render a bounded board-state differential probe, without executing it.

    paths contains legal UCI move sequences from start, each as one string;
    the empty string denotes the initial position. The caller compiles against
    the actual candidate board.c, defines CHECK_MATERIAL for a cached-signature
    candidate, and compares the complete stdout with the reference execution.
    The probe also explores 64 deterministic games of at most 256 plies, checking
    all generated legal children, not only the move chosen for the next ply.
    """
    if type(reference_board) is not bytes or type(paths) not in (list, tuple) or not paths:
        raise ValueError("reference board bytes and explicit UCI paths required")
    encoded = []
    for path in paths:
        if type(path) is not str:
            raise ValueError("UCI path must be a string")
        for move in path.split(" ") if path else ():
            if (len(move) not in (4, 5) or move[0] not in "abcdefgh"
                    or move[1] not in "12345678" or move[2] not in "abcdefgh"
                    or move[3] not in "12345678"
                    or (len(move) == 5 and move[4] not in "nbrq")):
                raise ValueError("UCI path contains an invalid move token")
        encoded.append(b'"' + path.encode("ascii") + b'"')
    reference = function(reference_board, b"int dead(").replace(
        b"int dead(", b"static int reference_dead(", 1)
    return _LIFECYCLE_PROBE.replace(b"FIXTURES", b",".join(encoded)).replace(
        b"REFERENCE_DEAD", reference)



def ep_mailbox(files):
    return replace_function(files, b"static void ep(", b'''static void ep(Board *p){
    if(p->e<0)return;
    for(int d=-1;d<=1;d+=2){
        int q=p->e-p->s*16+d;
        if(!(q&0x88)&&p->b[q]==p->s){
            Board t=*p;t.b[q]=t.b[p->e-p->s*16]=0;t.b[p->e]=(int8_t)p->s;
            if(!attacked(&t,p->k[p->s<0],-p->s))return;
        }
    }
    p->e=-1;
}''')


def ep_restore(files):
    # The owner already has a private Board while normalizing EP. Temporarily
    # edit its mailbox and restore all three cells before returning. Avoiding a
    # second Board copy preserves every observer (attacked reads b and k only).
    return replace_function(files, b"static void ep(", b'''static void ep(Board *p){
    if(p->e<0)return;
    int side=p->s,victim=p->e-side*16;
    for(int d=-1;d<=1;d+=2){
        int q=victim+d;
        if(!(q&0x88)&&p->b[q]==side){
            p->b[q]=p->b[victim]=0;p->b[p->e]=(int8_t)side;
            int legal=!attacked(p,p->k[side<0],-side);
            p->b[q]=(int8_t)side;p->b[victim]=(int8_t)-side;p->b[p->e]=0;
            if(legal)return;
        }
    }
    p->e=-1;
}''')


def put_loop(files):
    return replace_function(files, b"static void put(", b'''static void put(Board *p,int q,int v){
    int old=p->b[q];p->b[q]=(int8_t)v;
    for(int sign=-1;sign<=1;sign+=2){
        if(old){p->h^=piece(old,q);p->v+=sign*value(old,q);}old=v;
    }
    if(abs(v)==6)p->k[v<0]=q;
}''')


def put_zero_value(files):
    return replace_function(files, b"static void put(", b'''static void put(Board *p,int q,int v){
    int old=p->b[q];
    if(old)p->h^=piece(old,q);
    if(v)p->h^=piece(v,q);
    p->v+=value(v,q)-value(old,q);
    p->b[q]=(int8_t)v;
    if(abs(v)==6)p->k[v<0]=q;
}''')


def put_shared_adjust(files):
    return replace_function(files, b"static void put(", b'''__attribute__((noinline)) static void adjust(Board *p,int q,int v,int sign){
    if(v){p->h^=piece(v,q);p->v+=sign*value(v,q);}
}
static void put(Board *p,int q,int v){
    adjust(p,q,p->b[q],-1);p->b[q]=(int8_t)v;adjust(p,q,v,1);
    if(abs(v)==6)p->k[v<0]=q;
}''')


def rights_packed(files):
    # Only admitted on-board endpoints: rank 0/7 and files a/e/h carry rights.
    # 0x4302 packs the white two-bit file masks; black shifts them by two.
    return replace_function(files, b"static int rights(", b'''static int rights(int q){
    return !(q+16&96)?(0x4302>>(2*(q&7))&3)<<(q>>5&2):0;
}''')


def rights_table(files):
    return replace_function(files, b"static int rights(", b'''static int rights(int q){
    static const unsigned char bits[128]={[0]=2,[4]=3,[7]=1,[112]=8,[116]=12,[119]=4};
    return bits[q];
}''')


def rights_file_table(files):
    return replace_function(files, b"static int rights(", b'''static int rights(int q){
    static const unsigned char bits[8]={2,0,0,0,3,0,0,1};
    return !(q+16&96)?bits[q&7]<<(q>>5&2):0;
}''')


def value_fold(files):
    # Rank reflection maps black advance to q>>4 while preserving center.
    return replace_function(files, b"int value(", b'''int value(int v,int q){
    static const int material[7]={24576,48228,98624,65866,27124,41860,0};
    int a=material[abs(v)];q^=v<0?112:0;
    int rank=q>>4,file=q&7;
    int center=7-abs(2*file-7)-abs(2*rank-7);
    int score=(a&1023)+rank*((a>>10)&7)+center*((a>>13)-3);
    return v>0?score:-score;
}''')


def make_half(files):
    # Decide the reset once from the original pawn/capture state, before promo.
    result = dict(files)
    data = result["board.c"]
    pairs = (
        (b"*t=*p;t->h^=state(p);t->half++;t->e=-1;", b"*t=*p;t->h^=state(p);t->half=abs(v)==1||target?0:p->half+1;t->e=-1;"),
        (b"    if(abs(v)==1){\n        t->half=0;", b"    if(abs(v)==1){"),
        (b"    if(target)t->half=0;\n", b""),
    )
    for before, after in pairs:
        if data.count(before) != 1:
            raise ValueError("exact make halfmove role required")
        data = data.replace(before, after)
    result["board.c"] = data
    return result


def board_small_fields(files):
    result=dict(files)
    before=b"typedef struct { int s,c,e,k[2],half,v; uint64_t h,r; int8_t b[128]; } Board;"
    after=b"typedef struct { int8_t s,c,e,k[2]; int half,v; uint64_t h,r; int8_t b[128]; } Board;"
    if result['tiny.h'].count(before)!=1: raise ValueError('one Board type required')
    result['tiny.h']=result['tiny.h'].replace(before,after)
    return result


def board_mailbox_front(files):
    result=dict(files)
    before=b"typedef struct { int s,c,e,k[2],half,v; uint64_t h,r; int8_t b[128]; } Board;"
    after=b"typedef struct { int8_t b[128]; int s,c,e,k[2],half,v; uint64_t h,r; } Board;"
    if result['tiny.h'].count(before)!=1: raise ValueError('one Board type required')
    result['tiny.h']=result['tiny.h'].replace(before,after)
    return result


def value_fold_center(files):
    # First orient advance. Then fold both coordinates into 0..3: each center
    # distance is 7-2*folded_coordinate. All shifts/additions stay in int range.
    return replace_function(files,b'int value(',b'''int value(int v,int q){
    static const int material[7]={24576,48228,98624,65866,27124,41860,0};
    int a=material[abs(v)];q^=v<0?112:0;
    int rank=q>>4;q^=(q>>2&17)*7;
    int center=2*(q&7)+(q>>3)-7;
    int score=(a&1023)+rank*((a>>10)&7)+center*((a>>13)-3);
    return v>0?score:-score;
}''')


def value_center_table(files):
    return replace_function(files,b'int value(',b'''int value(int v,int q){
    static const int material[7]={24576,48228,98624,65866,27124,41860,0};
    static const unsigned char distance[8]={7,5,3,1,1,3,5,7};
    int a=material[abs(v)];q^=v<0?112:0;
    int rank=q>>4;
    int center=7-distance[q&7]-distance[rank];
    int score=(a&1023)+rank*((a>>10)&7)+center*((a>>13)-3);
    return v>0?score:-score;
}''')


def value_center_packed(files):
    return replace_function(files,b'int value(',b'''int value(int v,int q){
    static const int material[7]={24576,48228,98624,65866,27124,41860,0};
    int a=material[abs(v)];q^=v<0?112:0;
    int rank=q>>4;
    int center=7-(0x75311357>>(4*(q&7))&7)-(0x75311357>>(4*rank)&7);
    int score=(a&1023)+rank*((a>>10)&7)+center*((a>>13)-3);
    return v>0?score:-score;
}''')


def make_hash_transition(files, *, conditional_castle=False):
    result=dict(files);data=result['board.c']
    before=b'*t=*p;t->h^=state(p);t->half++;t->e=-1;'
    after=b'*t=*p;t->half++;t->e=-1;'
    if data.count(before)!=1: raise ValueError('one state removal required')
    data=data.replace(before,after)
    before=b'ep(t);t->h^=state(t);'
    after=b'''ep(t);t->h^=mix(2064);
    if(p->e>=0)t->h^=mix(2065+(p->e&7));
    if(t->e>=0)t->h^=mix(2065+(t->e&7));
    '''+(b'if(t->c!=p->c)' if conditional_castle else b'')+b't->h^=mix(2048+p->c)^mix(2048+t->c);'
    if data.count(before)!=1: raise ValueError('one state addition required')
    result['board.c']=data.replace(before,after)
    return result


def make_hash_castle(files):
    return make_hash_transition(files,conditional_castle=True)


def put_two_while(files):
    return replace_function(files,b'static void put(',b'''static void put(Board *p,int q,int v){
    int old=p->b[q],sign=-1;p->b[q]=(int8_t)v;
    do{
        if(old){p->h^=piece(old,q);p->v+=sign*value(old,q);}old=v;
    }while((sign=-sign)>0);
    if(abs(v)==6)p->k[v<0]=q;
}''')


def walk_ranges(files):
    # Encode the same ascending direction interval, in units of two; shifting
    # the pawn interval by two preserves its black orientation and move order.
    result=dict(files);data=result['board.c']
    before=b'''        int first=a==1?(s>0?12:14):a==2?0:a==3?12:8;
        int last=a==1?first+2:a==2?8:a==4?12:16;'''
    after=b'''        static const unsigned char ranges[7]={0,62,32,70,52,68,68};
        int range=ranges[a],offset=a==1&&s<0?2:0;
        int first=2*(range&7)+offset,last=2*(range>>3)+offset;'''
    if data.count(before)!=1: raise ValueError('one scalar walker range required')
    result['board.c']=data.replace(before,after)
    return result


def walk_direction_bits(files):
    # Alternative to walk-ranges. ctz sees only nonzero unsigned masks; removing
    # the least bit enumerates the identical original ascending direction order.
    result=dict(files);data=result['board.c']
    before=b'''        int first=a==1?(s>0?12:14):a==2?0:a==3?12:8;
        int last=a==1?first+2:a==2?8:a==4?12:16;
        for(int i=first;i<last;i++){'''
    after=b'''        static const uint16_t ranges[7]={0,0x3000,0xff,0xf000,0xf00,0xff00,0xff00};
        unsigned directions=ranges[a];if(a==1&&s<0)directions<<=2;
        while(directions){
            int i=__builtin_ctz(directions);directions&=directions-1;'''
    if data.count(before)!=1: raise ValueError('one scalar walker range/loop required')
    result['board.c']=data.replace(before,after)
    return result


def walk_castle_rights(files):
    # A surviving right proves king home; test the relevant rights before the
    # expensive attack query. Origin/transit/destination safety is preserved.
    result=dict(files);data=result['board.c']
    before=b'''            int home=s>0?4:116,shift=s>0?0:2;
            if(from==home&&!attacked(p,home,-s)){
                for(int d=1;d>=-1;d-=2)
                    if((p->c&((d>0?1:2)<<shift))&&!p->b[home+d]&&!p->b[home+2*d]&&(d>0||!p->b[home-3])&&!attacked(p,home+d,-s))add(moves,&n,from,home+2*d,0);'''
    after=b'''            int home=from,rights=p->c>>(s<0?2:0)&3;
            if(rights&&!attacked(p,home,-s)){
                for(int d=1;d>=-1;d-=2)
                    if((rights&(d>0?1:2))&&!p->b[home+d]&&!p->b[home+2*d]&&(d>0||!p->b[home-3])&&!attacked(p,home+d,-s))add(moves,&n,from,home+2*d,0);'''
    if data.count(before)!=2: raise ValueError('two selected walker castle roles required')
    result['board.c']=data.replace(before,after)
    return result


def walk_signed_piece(files):
    # At the existing own-side filter, b[from]*s equals abs(b[from]) exactly.
    result=dict(files);data=result['board.c']
    before=b'int a=abs(p->b[from]);if(p->b[from]*s<=0)continue;'
    after=b'int a=p->b[from]*s;if(a<=0)continue;'
    if data.count(before)!=2: raise ValueError('two selected walker piece roles required')
    result['board.c']=data.replace(before,after)
    return result


def make_castle_midpoint(files):
    result=dict(files);data=result['board.c']
    before=b'int rook=to>from?from+3:from-4,transit=to>from?from+1:from-1;'
    after=b'int rook=(from&112)+(to>from?7:0),transit=(from+to)/2;'
    if data.count(before)!=1: raise ValueError('one rook transfer role required')
    result['board.c']=data.replace(before,after)
    return result


def add_do(files):
    # Emit 0 once, or 2/3/4/5 in order. Preserve each append's capacity guard.
    return replace_function(files,b'static void add(',b'''static void add(Move *moves,int *n,int from,int to,int kind){
    int z=kind>1&&!(to+16&96)?2:0;
    do{
        if(*n>=MOVES)abort();
        moves[(*n)++]=MOVE(from,to,z)|((kind&1)<<3);
    }while(z&&++z<6);
}''')


def add_hoisted_bound(files):
    return replace_function(files,b'static void add(',b'''static void add(Move *moves,int *n,int from,int to,int kind){
    int promotion=kind>1&&!(to+16&96);
    if(*n>MOVES-(promotion?4:1))abort();
    for(int z=promotion?2:0;z<=(promotion?5:0);z++)
        moves[(*n)++]=MOVE(from,to,z)|((kind&1)<<3);
}''')


def material_signature(files, *, shared_loop=False):
    # Five-bit counts replace the repeated whole-board dead-material scan.
    # material_piece is called only for nonzero pieces, inside the put guards.
    result=dict(files)
    before=b'typedef struct { int s,c,e,k[2],half,v; uint64_t h,r; int8_t b[128]; } Board;'
    after=b'typedef struct { int s,c,e,k[2],half,v; unsigned material; uint64_t h,r; int8_t b[128]; } Board;'
    if result['tiny.h'].count(before)!=1: raise ValueError('one padded Board required')
    result['tiny.h']=result['tiny.h'].replace(before,after)
    result=replace_function(result,b'int dead(',b'''int dead(const Board *p){
    unsigned material=p->material;
    return material<32||(!(material&31)&&material<=1024);
}''')
    increment=b'''static unsigned material_piece(int v,int q){
    int a=abs(v);
    return a==6?0:1u<<(a==2?10:a==3?5*((q+(q>>4))&1):15);
}
'''
    if shared_loop:
        body=b'''static void put(Board *p,int q,int v){
    int old=p->b[q];p->b[q]=(int8_t)v;
    for(int sign=-1;sign<=1;sign+=2){
        if(old){p->h^=piece(old,q);p->v+=sign*value(old,q);p->material+=sign*material_piece(old,q);}old=v;
    }
    if(abs(v)==6)p->k[v<0]=q;
}'''
    else:
        body=b'''static void put(Board *p,int q,int v){
    int old=p->b[q];
    if(old){p->h^=piece(old,q);p->v-=value(old,q);p->material-=material_piece(old,q);}
    p->b[q]=(int8_t)v;
    if(v){p->h^=piece(v,q);p->v+=value(v,q);p->material+=material_piece(v,q);if(abs(v)==6)p->k[v<0]=q;}
}'''
    result=replace_function(result,b'static void put(',increment+body)
    before=b'p->v!=t.v)return 0;'
    after=b'p->v!=t.v||p->material!=t.material)return 0;'
    if result['board.c'].count(before)!=1: raise ValueError('one Board verifier role required')
    result['board.c']=result['board.c'].replace(before,after)
    return result


def material_signature_loop(files):
    return material_signature(files,shared_loop=True)


def reverse_attacks(files):
    # Retained speed/size alternative: attack rays start at the queried square.
    # Generator order stays fixed; geometric attacks include pinned pieces.
    result=replace_function(files,b'int attacked(',b'''int attacked(const Board *p,int sq,int side){
    for(int i=0;i<16;i++){
        int step=steps[i],first=1;
        for(int to=sq+step;!(to&0x88);to+=step){
            int a=p->b[to]*side;
            if(a){
                if(i<8?a==2:a==5||a==(i<12?4:3)||
                   (first&&(a==6||(a==1&&i>=12&&step*side<0))))return 1;
                break;
            }
            if(i<8)break;
            first=0;
        }
    }
    return 0;
}''')
    data=result['board.c']
    before=b'''            if(!moves&&to==sq)return 1;'''
    if data.count(before)!=3: raise ValueError('three old attack walker roles required')
    data=data.replace(before,b'')
    for before,after in (
        (b'if(moves&&a==1)',b'if(a==1)'),
        (b'(moves&&a==1&&!target&&to!=p->e)',b'(a==1&&!target&&to!=p->e)'),
        (b'if(moves&&p->b[to]*s<=0)',b'if(p->b[to]*s<=0)'),
        (b'if(moves)add(',b'add('),
        (b'if(moves&&a==6)',b'if(a==6)'),
    ):
        if not data.count(before): raise ValueError('old move walker branch absent')
        data=data.replace(before,after)
    result['board.c']=data
    return result


def reverse_attacks_mask(files):
    result=reverse_attacks(files)
    return replace_function(result,b'int attacked(',b'''int attacked(const Board *p,int sq,int side){
    for(int i=0;i<16;i++){
        int step=steps[i],mask=i<8?4:i<12?48:40;
        if(i>=8)mask|=64|(i>=12&&step*side<0?2:0);
        for(int to=sq+step;!(to&0x88);to+=step){
            int a=p->b[to]*side;
            if(a){if(a>0&&(mask>>a&1))return 1;break;}
            if(i<8)break;
            mask&=~66;
        }
    }
    return 0;
}''')


VARIANTS = {
    "ep-mailbox": ep_mailbox,
    "ep-restore": ep_restore,
    "put-loop": put_loop,
    "put-zero-value": put_zero_value,
    "put-shared-adjust": put_shared_adjust,
    "rights-packed": rights_packed,
    "rights-table": rights_table,
    "rights-file-table": rights_file_table,
    "value-fold": value_fold,
    "make-half": make_half,
    "board-small-fields": board_small_fields,
    "board-mailbox-front": board_mailbox_front,
    "value-fold-center": value_fold_center,
    "value-center-table": value_center_table,
    "value-center-packed": value_center_packed,
    "make-hash-transition": make_hash_transition,
    "make-hash-castle": make_hash_castle,
    "put-two-while": put_two_while,
    "walk-ranges": walk_ranges,
    "walk-direction-bits": walk_direction_bits,
    "walk-castle-rights": walk_castle_rights,
    "walk-signed-piece": walk_signed_piece,
    "make-castle-midpoint": make_castle_midpoint,
    "add-do": add_do,
    "add-hoisted-bound": add_hoisted_bound,
    "material-signature": material_signature,
    "material-signature-loop": material_signature_loop,
    "reverse-attacks": reverse_attacks,
    "reverse-attacks-mask": reverse_attacks_mask,
}


BEST = (
    "value-fold-center",
    "make-half",
    "rights-packed",
    "walk-ranges",
    "walk-castle-rights",
    "walk-signed-piece",
    "add-do",
    "material-signature-loop",
)

# These options replace the same responsibility; allowing both would silently
# overwrite the first source alternative instead of comparing a composition.
_EXCLUSIVE = (
    frozenset(("ep-mailbox", "ep-restore")),
    frozenset(("put-loop", "put-zero-value", "put-shared-adjust", "put-two-while",
               "material-signature", "material-signature-loop")),
    frozenset(("rights-packed", "rights-table", "rights-file-table")),
    frozenset(("value-fold", "value-fold-center", "value-center-table", "value-center-packed")),
    frozenset(("board-small-fields", "board-mailbox-front",
               "material-signature", "material-signature-loop")),
    frozenset(("make-hash-transition", "make-hash-castle")),
    frozenset(("walk-ranges", "walk-direction-bits")),
    frozenset(("add-do", "add-hoisted-bound")),
    frozenset(("reverse-attacks", "reverse-attacks-mask")),
)


def apply(files, options):
    """Return a new immutable-source mapping for explicit D board alternatives."""
    if (type(files) is not dict or not {"board.c", "tiny.h"} <= files.keys()
            or not all(type(name) is str and type(data) is bytes
                       for name, data in files.items())):
        raise ValueError("named immutable D sources required")
    if type(options) not in (tuple, list) or not all(type(name) is str for name in options):
        raise ValueError("explicit ordered board-option names required")
    selected = set(options)
    if len(selected) != len(options) or not selected <= VARIANTS.keys():
        raise ValueError("unknown or repeated D board alternative")
    if any(len(selected & group) > 1 for group in _EXCLUSIVE):
        raise ValueError("mutually exclusive D board alternatives")
    result = dict(files)
    for name in options:
        result = VARIANTS[name](result)
    return result
