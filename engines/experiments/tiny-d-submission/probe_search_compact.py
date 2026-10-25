"""Actual D search-order, previous-piece, start and learner differential probe.

This pure renderer never runs a tool, starts an engine, or accepts a native
identity. The caller owns genuine frozen inputs, compiler processes and the
comparison between all outputs. The shipping board/search bodies are included
directly; only named observation/cancellation hooks are added. The libc driver
and synthetic valid positions are fixture-only and never shipping inputs.
"""
from hashlib import sha256
from pathlib import Path
import re

STORAGE_FIXTURE_SHA = "22cc308b30b46f67c41362bb2f5324c5432cdd8e5e2c81d422ec170ae0fe038f"
FILES = {"tiny.h", "board.c", "search.c", "runtime.c", "start.S", "image.ld"}
OPTION_NAMES = ("union-order", "previous-piece", "constant-start", "unsigned-history")
MASK64 = (1 << 64) - 1


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(data):
    return dict(bytes=len(data), sha256=sha256(data).hexdigest())


def inventory(files):
    return {name: pin(data) for name, data in sorted(files.items())}


def _once(data, before, after, role):
    require(data.count(before) == 1, "unique search fixture role required: " + role)
    return data.replace(before, after), dict(role=role, before=pin(before), after=pin(after))


def independent_start():
    """Derive original logical Board fields independently of its C start()."""
    def mix(value):
        value = (value + 0x9e3779b97f4a7c15) & MASK64
        value = ((value ^ (value >> 30)) * 0xbf58476d1ce4e5b9) & MASK64
        value = ((value ^ (value >> 27)) * 0x94d049bb133111eb) & MASK64
        return value ^ (value >> 31)
    board = [0] * 128
    order = (4, 2, 3, 5, 6, 3, 2, 4)
    for file, piece in enumerate(order):
        board[file], board[16 + file] = piece, 1
        board[96 + file], board[112 + file] = -1, -piece
    key = mix(2048 + 15)
    for square, piece in enumerate(board):
        if piece:
            key ^= mix(square + (piece + 6) * 128)
    # Mirrored material/advance/centre values cancel for this exact layout.
    return dict(s=1, c=15, e=-1, kings=[4, 116], half=0, v=0, h=key, r=key, b=board)


def _reference_start(board):
    start = b"void start(Board *p){"
    require(board.count(start) == 1, "original start function required for fixture reference")
    begin = board.index(start)
    depth, end = 0, None
    for index in range(begin + len(start) - 1, len(board)):
        if board[index] == ord("{"):
            depth += 1
        elif board[index] == ord("}"):
            depth -= 1
            if not depth:
                end = index + 1
                break
    require(end is not None, "complete original start body required")
    function = board[begin:end]
    require(b'"' not in function and b"/*" not in function and b"//" not in function,
            "reference start lexical domain changed")
    return function.replace(start, b"static void fixture_original_start(Board *p){", 1)


EXTRA = r'''
static int expected_prior[PLY];
static unsigned promotion_seen[2][4][2];
static uint64_t order_count,prior_checks,learner_checks,learner_digest;
static void observe_candidate(Move m,int ply){
    path_digest=add_hash(path_digest,UINT64_C(0xc4dec4de));
    path_digest=add_hash(path_digest,(unsigned)ply);
    path_digest=add_hash(path_digest,m);order_count++;
}
static void observe_child(const Board *q,Move m,int ply){
    int piece=q->b[TO(m)],prior=piece+6;
    if(prior<0||prior>12){puts("BROKEN_PRIOR_RANGE");abort();}
    if(ply+1<PLY)expected_prior[ply+1]=prior;
    if(ply==0&&PROMO(m)){
        int promotion=(int)PROMO(m),side=piece<0;
        if(promotion<2||promotion>5||abs(piece)!=promotion){puts("BROKEN_POST_PROMOTION");abort();}
        promotion_seen[side][promotion-2][!!(m&8)]++;
    }
}
static void observe_prior(const Board *p,int ply,int received){
    if(ply<0||ply>=PLY||received!=expected_prior[ply]){
        printf("BROKEN_PREVIOUS_PIECE ply=%d received=%d expected=%d\n",ply,received,expected_prior[ply]);abort();
    }
    path_digest=add_hash(path_digest,(unsigned)received);prior_checks++;
    (void)p;
}
static int equal_board_fields(const Board *a,const Board *b){
    return a->s==b->s&&a->c==b->c&&a->e==b->e&&a->k[0]==b->k[0]&&a->k[1]==b->k[1]&&
        a->half==b->half&&a->v==b->v&&a->h==b->h&&a->r==b->r&&!memcmp(a->b,b->b,128);
}
static void check_start(void){
    Board actual,reference;
    memset(&actual,165,sizeof actual);memset(&reference,90,sizeof reference);
    start(&actual);fixture_original_start(&reference);
    if(!equal_board_fields(&actual,&reference)||!equal_board_fields(&actual,&fixture_expected_start)){
        puts("BROKEN_START_FIELDS");abort();
    }
    printf("START h=%016" PRIx64 " r=%016" PRIx64 " v=%d\n",actual.h,actual.r,actual.v);
}
#if CASE_UNSIGNED_HISTORY
typedef uint16_t FixtureLearner;
_Static_assert(_Generic(&fixture_worker.history[0][0],uint16_t *:1,default:0),"history must be unsigned16");
_Static_assert(_Generic(&fixture_worker.continuation[0][0],uint16_t *:1,default:0),"continuation must be unsigned16");
#else
typedef int16_t FixtureLearner;
_Static_assert(_Generic(&fixture_worker.history[0][0],int16_t *:1,default:0),"history must be signed16 control");
_Static_assert(_Generic(&fixture_worker.continuation[0][0],int16_t *:1,default:0),"continuation must be signed16 control");
#endif
_Static_assert(_Generic(&fixture_worker.correction[0],int16_t *:1,default:0),"correction remains signed16");
static unsigned learn_reference(unsigned old,unsigned bonus){
    return old+bonus-(unsigned)((uint64_t)old*bonus/16384);
}
static void check_one_learner(unsigned old,unsigned bonus){
    FixtureLearner cell=(FixtureLearner)old;
    unsigned expected=learn_reference(old,bonus);
    learn(&cell,(int)bonus);
    if(expected>16384||(unsigned)cell!=expected){puts("BROKEN_POSITIVE_LEARNER");abort();}
    learner_digest=add_hash(learner_digest,(unsigned)cell);learner_checks++;
}
static void check_learners(void){
    learner_digest=UINT64_C(1469598103934665603);
    for(unsigned depth=1;depth<=126;depth++)for(unsigned old=0;old<=16384;old++)
        check_one_learner(old,depth*depth);
    FixtureLearner cell=0;unsigned expected=0;
    for(unsigned round=0;round<100000;round++){
        unsigned depth=(round*37)%126+1,bonus=depth*depth;
        expected=learn_reference(expected,bonus);learn(&cell,(int)bonus);
        if(expected>16384||(unsigned)cell!=expected){puts("BROKEN_PERSISTENT_LEARNER");abort();}
        learner_digest=add_hash(learner_digest,(unsigned)cell);learner_checks++;
    }
    printf("LEARN checks=%" PRIu64 " digest=%016" PRIx64 "\n",learner_checks,learner_digest);
}
static void promotion_root(Board *p,int side){
    Board q={0};q.s=side;q.e=-1;
    put(&q,4,6);put(&q,116,-6);
    if(side>0){put(&q,96,1);put(&q,113,-4);}
    else{put(&q,23,-1);put(&q,6,4);}
    q.h^=state(&q);q.r=q.h;*p=q;
    game_length=1;game_keys[0]=q.h;
}
'''


def render(files, source_tool, storage_fixture, *, reference_board, variant_proof=None,
           prefix=True, dense=False, union_order=False, previous_index=False,
           constant_start=False, unsigned_history=False):
    """Return observed files, actual-C driver bytes, and explicit fixture proof.

    reference_board must be the fresh untransformed readable board.c. It is
    checked against the candidate except for start() by the caller's complete
    source transform proof; the probe also independently derives logical start
    fields and executes both original and candidate start functions.
    """
    fixture_path=Path(storage_fixture.__file__)
    authority=fixture_path.read_bytes().replace(b"\r\n",b"\n")
    require(pin(authority)["sha256"]==STORAGE_FIXTURE_SHA,
            "genuine frozen actual-D storage fixture required")
    require(set(files)==FILES and all(isinstance(data,bytes) and b"\r" not in data for data in files.values()),
            "complete normalized six-file actual D source required")
    flags=(union_order,previous_index,constant_start,unsigned_history,prefix,dense)
    require(all(type(value) is bool for value in flags),"explicit boolean search fixture options required")
    options=dict(zip(OPTION_NAMES,flags[:4]))
    if variant_proof is None:
        require(not any(flags[:4]),"transformed search fixture needs explicit source proof")
    else:
        require(variant_proof.get("output")==inventory(files) and
                variant_proof.get("options")==[name for name in OPTION_NAMES if options[name]],
                "actual search source/options differ from candidate proof")
    generated,instrumentation=storage_fixture.instrument(source_tool,files)
    prior=b"prior" if previous_index else b"previous?piece_index(p->b[TO(previous)]):6"
    generated["search.c"],extra=source_tool.project(generated["search.c"],[
        ("observe-every-selected-pseudo-move",b"        Board q;if(!make(p,m,&q))continue;",
         b"        observe_candidate(m,ply);Board q;if(!make(p,m,&q))continue;"),
        ("independent-post-make-child-prior",b"        ++legal;",b"        ++legal;observe_child(&q,m,ply);"),
        ("check-actual-previous-consumer",b"    observe_entry(w,p,depth,ply);",
         b"    observe_entry(w,p,depth,ply);observe_prior(p,ply,"+prior+b");")])
    driver=storage_fixture.DRIVER.encode()
    edits=[]
    driver,record=_once(driver,b"static void observe_entry(const Worker *,const Board *,int,int);",
        b"static void observe_entry(const Worker *,const Board *,int,int);\n"
        b"static void observe_candidate(Move,int);static void observe_child(const Board *,Move,int);"
        b"static void observe_prior(const Board *,int,int);", "observation-prototypes");edits.append(record)
    expected=independent_start()
    constant=("static const Board fixture_expected_start={.s=1,.c=15,.e=-1,.k={4,116},.half=0,.v=0,.h=UINT64_C("+
        str(expected["h"])+"),.r=UINT64_C("+str(expected["r"])+"),.b={"+",".join(map(str,expected["b"]))+"}};\n").encode()
    definitions=_reference_start(reference_board)+b"\n"+constant+EXTRA.encode()+b"\nstatic uint64_t learners"
    driver,record=_once(driver,b"static uint64_t learners",definitions,"actual-observer-and-independent-domains");edits.append(record)
    root=b"Move best=0;int score=search(&fixture_worker,p,depth,-MATE,MATE,0,0,&best);"
    replacement=(b"expected_prior[0]=6;Move best=0;int score=search(&fixture_worker,p,depth,-MATE,MATE,0,"+
                 (b"6" if previous_index else b"0")+b",&best);")
    driver,record=_once(driver,root,replacement,"root-prior-binding");edits.append(record)
    # Preserve the ABI row as the first row excluded from semantic comparison.
    abi=b'    printf("ABI worker=%zu board=%zu entry=%zu\\n",sizeof(Worker),sizeof(Board),sizeof(Entry));\n'
    driver,record=_once(driver,abi,abi+b"    check_start();check_learners();\n", "run-independent-checks-after-abi");edits.append(record)
    promotion_runs=b'''    for(int side=-1;side<=1;side+=2){
        promotion_root(&p,side);snprintf(name,sizeof name,"promotion-%d",side);
        if(run(name,&p,2,0,1,0)==UINT64_MAX)return 7;
    }
    for(int side=0;side<2;side++)for(int piece=0;piece<4;piece++)for(int capture=0;capture<2;capture++)
        if(!promotion_seen[side][piece][capture]){puts("MISSING_PROMOTION_PRIOR");return 8;}
    printf("ORDER candidates=%" PRIu64 " prior_checks=%" PRIu64 " promotions=16\\n",order_count,prior_checks);
'''
    driver,record=_once(driver,b'    printf("TOTAL runs=%',promotion_runs+b'    printf("TOTAL runs=%', "both-colour-promotion-and-order-coverage");edits.append(record)
    require(driver.count(b"#include \"board.c\"")==1 and driver.count(b"#include \"search.c\"")==1,
            "actual board/search fixture inclusion differs")
    proof=dict(kind="D-actual-search-structural-fixture-v1",source=inventory(files),
        output=inventory(generated),candidate=variant_proof,options=options,prefix=prefix,dense=dense,
        actual_storage_fixture=pin(authority),reference_board=pin(reference_board),
        original_start=pin(_reference_start(reference_board)),independent_start=expected,
        source_instrumentation=instrumentation,extra_instrumentation=extra,driver_edits=edits,
        driver=pin(driver),actual_runtime=False,TT_bits=12,TT_allocated_by_fixture=True,
        promotion_cases="both colours, NBRQ, quiet and capture; observed post-make prior at actual recursive entry",
        learners="actual learn; all126squarebonusesxall0..16384cells,100000persistent updates",
        selected_order="every selected pseudo move hashed before make, strict-score ties exposed",
        target_qualification=False,strength_claim=False)
    return generated,driver,proof


def compiler_flags(*, prefix=True,dense=False,previous_index=False,unsigned_history=False,mode="plain"):
    require(mode in ("plain","ubsan"),"finite plain/UBSan fixture mode required")
    flags=["-std=c11","-O2","-g0","-fno-builtin","-msse4.2","-mcx16","-DDEV=0","-DD_HQ=0",
        "-DWORKERS=256","-DTT_BITS=12","-DPLY=128",f"-DCASE_PREFIX={int(prefix)}",
        f"-DCASE_DENSE={int(dense)}",f"-DCASE_PREVIOUS_INDEX={int(previous_index)}",
        f"-DCASE_UNSIGNED_HISTORY={int(unsigned_history)}"]
    if mode=="ubsan":flags += ["-fsanitize=undefined","-fno-sanitize-recover=undefined"]
    return flags


def verify_output(output):
    """Compare returned normalized bytes across every baseline/candidate/mode."""
    require(isinstance(output,bytes),"actual stdout bytes required")
    lines=output.splitlines()
    require(lines and lines[0].startswith(b"ABI ") and lines[-1].startswith(b"TOTAL "),
            "actual search probe output incomplete")
    require(sum(line.startswith(b"START ") for line in lines)==1 and
            sum(line.startswith(b"LEARN ") for line in lines)==1 and
            sum(line.startswith(b"ORDER ") for line in lines)==1,
            "start/learner/order observations incomplete")
    total=re.fullmatch(rb"TOTAL runs=(\d+) cancellation_runs=(\d+) research=(\d+)",lines[-1])
    require(total is not None and int(total[1])>=1486 and int(total[2])>=1344 and int(total[3])>0,
            "actual PVS/cancellation/research coverage missing")
    require(any(line.startswith(b"promotion--1 ") for line in lines) and
            any(line.startswith(b"promotion-1 ") for line in lines),"both promotion sides missing")
    normalized=b"\n".join(lines[1:])+b"\n"
    return normalized,dict(kind="D-actual-search-structural-observations-v1",ABI=lines[0].decode(),
        output=pin(output),normalized=pin(normalized),totals=lines[-1].decode(),
        runs=int(total[1]),cancellation_runs=int(total[2]),research=int(total[3]),
        start=next(line.decode() for line in lines if line.startswith(b"START ")),
        learners=next(line.decode() for line in lines if line.startswith(b"LEARN ")),
        order=next(line.decode() for line in lines if line.startswith(b"ORDER ")),
        equal_to_control_not_yet_checked=True,actual_runtime=False,target_qualification=False)
