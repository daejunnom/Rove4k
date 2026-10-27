"""Explicit full-D search representation experiments after the BSS cost baseline.

These selectors are source candidates, not selected production changes. They
retain all search features, full TT keys and atomic16 publication. The caller
owns actual cost, native behavior, many-worker and strength observations.
Only the bounded source transformations and observer rendering run here.
"""
from __future__ import annotations

from pathlib import Path
import re

FILES = frozenset(("tiny.h", "board.c", "search.c", "runtime.c", "start.S", "image.ld"))
OPTIONS = ("tt_bytes", "pvs_stages", "repetition_prefix", "board_path")


def _once(data: bytes, before: bytes | str, after: bytes | str) -> bytes:
    if isinstance(before, str):
        before = before.encode()
    if isinstance(after, str):
        after = after.encode()
    if data.count(before) != 1:
        raise ValueError("unique D search size boundary required: " + repr(before[:100]))
    return data.replace(before, after)


def _names(names):
    if isinstance(names, str):
        raise ValueError("explicit search selector sequence required")
    names = tuple(names)
    if len(set(names)) != len(names) or any(name not in OPTIONS for name in names):
        raise ValueError("unique known search size selectors required")
    return names


def _board_references(data: bytes) -> bytes:
    """The finite local-Board to owned-slot address change, never a C parser."""
    return (data.replace(b"search(w,&q,", b"search(w,")
            .replace(b"attacked(&q,q.k[q.s<0],-q.s)", b"attacked(q,q->k[q->s<0],-q->s)")
            .replace(b"piece_index(q.b[to])", b"piece_index(q->b[to])"))


def apply(files: dict[str, bytes], names: tuple[str, ...]) -> dict[str, bytes]:
    """Return fresh sources; no mutation, build, implicit selector or fallback.

    The input is the current full fast-capacity cohort with root_current. Source
    bounds require normal D depth/mate/worker profiles and legal 0x88 moves.
    Both DEV modes retain their original observation and cancellation code.
    """
    names = _names(names)
    if set(files) != FILES or any(type(data) is not bytes or b"\r" in data for data in files.values()):
        raise ValueError("complete normalized six-file D cohort required")
    result = dict(files)
    for name in names:
        source, header = result["search.c"], result["tiny.h"]
        if name == "tt_bytes":
            # All stored moves fit 17 bits; the zeroed gaps are implicit. The
            # coherent 128-bit key/data object and its CAS accesses do not move.
            source = _once(source, "Move tt=data&131071;", "Move tt=(Move)data;")
            source = _once(source,
                "int score=(int16_t)(data>>17),bound=(data>>41)&3,ttdepth=(data>>33)&255;",
                "int score=(int16_t)(data>>32),bound=data>>56,ttdepth=(data>>48)&255;")
            source = _once(source,
                "data=bestmove|((uint64_t)(uint16_t)score<<17)|((uint64_t)(depth>0?depth:0)<<33)|((uint64_t)bound<<41);",
                "data=bestmove|((uint64_t)(uint16_t)score<<32)|((uint64_t)(depth>0?depth:0)<<48)|((uint64_t)bound<<56);")
        elif name == "pvs_stages":
            before = b'''        int narrow=legal>1&&depth>0,reduce=0;
        if(narrow){
            COUNT(w,pvs);
            reduce=depth>=4&&legal>=4&&!tactical&&!check&&!attacked(&q,q.k[q.s<0],-q.s);
            if(reduce){COUNT(w,corr_uses);reduce=evaluation+w->correction[p->h&1023]/64<alpha+100;}
        }
        for(;;){
            score=-search(w,&q,depth-1-reduce,-(narrow?alpha+1:beta),-alpha,ply+1,piece_index(q.b[to]));
            if(!narrow||score<=alpha||(!reduce&&score>=beta))break;
            if(reduce)reduce=0;else narrow=0;
        }
'''
            after = b'''        /* 2: reduced null, 1: normal null, 0: full window. */
        int stage=legal>1&&depth>0;
        if(stage){
            COUNT(w,pvs);
            if(depth>=4&&legal>=4&&!tactical&&!check&&!attacked(&q,q.k[q.s<0],-q.s)){
                COUNT(w,corr_uses);stage+=evaluation+w->correction[p->h&1023]/64<alpha+100;
            }
        }
        for(;;){
            score=-search(w,&q,depth-1-(stage==2),-(stage?alpha+1:beta),-alpha,ply+1,piece_index(q.b[to]));
            if(!stage||score<=alpha||(stage==1&&score>=beta))break;
            --stage;
        }
'''
            if b"const Board *p=w->boards+ply;" in source:
                before, after = _board_references(before), _board_references(after)
            source = _once(source, before, after)
        elif name == "repetition_prefix":
            # The last 100 root positions contain every possible root-prefix
            # read for half<100. For half>=100 the existing draw flag already
            # decides the result; terminal/checkmate precedence is unchanged.
            # Search suffix slots are never a ring: siblings cannot overwrite
            # an ancestor's root prefix or an ancestor's current path key.
            header = _once(header, "uint64_t nodes,keys[PLY];",
                           "int root_keys;\n    uint64_t nodes,keys[100+PLY];")
            helper = b'''static void prepare_path(Worker *w){
    w->root_keys=game_length<100?game_length:100;
    memcpy(w->keys,game_keys+game_length-w->root_keys,(size_t)w->root_keys*sizeof *game_keys);
}
'''
            source = _once(source, "static Move first(const Board *);", helper + b"static Move first(const Board *);")
            source = _once(source, "int length=game_length+ply;", "int length=w->root_keys+ply;")
            source = _once(source,
                "repetitions+=(i<game_length?game_keys[i]:w->keys[i-game_length])==p->h;",
                "repetitions+=w->keys[i]==p->h;")
            source = _once(source, "w->keys[ply]=", "w->keys[w->root_keys+ply]=")
            source = _once(source, "void think(Worker *w,const Board *p){\n",
                           "void think(Worker *w,const Board *p){\n    prepare_path(w);\n")
        elif name == "board_path":
            # Only the owning worker writes these slots. Each make writes the
            # next ply; recursive descendants use strictly later slots. Parent
            # Boards therefore stay immutable until that frame returns. This
            # removes the seventh SysV argument and the automatic child Board.
            header = _once(header, "    uint16_t history[128][128],",
                           "    Board boards[PLY];\n    uint16_t history[128][128],")
            helper = b"static void prepare_board(Worker *w,const Board *p){w->boards[0]=*p;}\n"
            source = _once(source, "static Move first(const Board *);", helper + b"static Move first(const Board *);")
            source = _once(source,
                "static int search(Worker *w,const Board *p,int depth,int alpha,int beta,int ply,int prior){\n",
                "static int search(Worker *w,int depth,int alpha,int beta,int ply,int prior){\n    const Board *p=w->boards+ply;\n")
            source = _once(source, "        Board q;if(!make(p,m,&q))continue;",
                           "        Board *q=w->boards+ply+1;if(!make(p,m,q))continue;")
            source = _once(source, "q.h;", "q->h;")
            source = _once(source, "attacked(&q,q.k[q.s<0],-q.s)", "attacked(q,q->k[q->s<0],-q->s)")
            source = _once(source, "piece_index(q.b[to])", "piece_index(q->b[to])")
            source = _once(source, "search(w,&q,", "search(w,")
            source = _once(source, "search(w,p,depth,-MATE,MATE,0,6);", "search(w,depth,-MATE,MATE,0,6);")
            source = _once(source, "void think(Worker *w,const Board *p){\n",
                           "void think(Worker *w,const Board *p){\n    prepare_board(w,p);\n")
        result["search.c"], result["tiny.h"] = source, header
    return result


def render_probe(files, source_tool, storage_fixture, probe, *, reference_board, names=()):
    """Instrument actual variants with the existing independent D search oracle.

    This explicitly adapts observation to representation changes. It neither
    restores old search code nor drops changed fields from comparison. The TT
    allocator/width belongs to this bounded fixture, not the shipping runtime.
    Full packaged execution and resource qualification remain separate checks.
    """
    names = _names(names)
    probe.require(set(files) == FILES and all(type(data) is bytes for data in files.values()),
                  "complete actual D candidate required")
    authority = Path(storage_fixture.__file__).read_bytes().replace(b"\r\n", b"\n")
    probe.require(probe.pin(authority)["sha256"] == probe.STORAGE_FIXTURE_SHA,
                  "frozen independent D storage fixture required")
    board_path, stages, prefix = (name in names for name in ("board_path", "pvs_stages", "repetition_prefix"))
    source = files["search.c"]
    probe.require((b"const Board *p=w->boards+ply;" in source) == board_path and
                  (b"int stage=legal>1&&depth>0;" in source) == stages and
                  (b"static void prepare_path(Worker *w){" in source) == prefix and
                  (b"bound=data>>56" in source) == ("tt_bytes" in names),
                  "observer selector contract differs from actual source")
    narrow = b"        int stage=legal>1&&depth>0;" if stages else b"        int narrow=legal>1&&depth>0,reduce=0;"
    research = b"            --stage;" if stages else b"            if(reduce)reduce=0;else narrow=0;"
    make = (b"        Board *q=w->boards+ply+1;if(!make(p,m,q))continue;" if board_path else
            b"        Board q;if(!make(p,m,&q))continue;")
    edits = [
        ("claim-checkpoint", b"static int claim(Worker *w){\n",
         b"static int claim(Worker *w){\n    if(++test_claims==test_cancel_at){atomic_store(&stopped,1);return 0;}\n"),
        ("actual-search-entry-and-prior", b"    if(!claim(w))return 0;\n",
         b"    if(!claim(w))return 0;\n    observe_entry(w,p,depth,ply);observe_prior(p,ply,prior);\n"),
        ("actual-PVS-narrow", narrow, narrow + (b"test_narrow+=stage;" if stages else b"test_narrow+=narrow;")),
        ("actual-PVS-research", research, b"            ++test_research;" + research.lstrip()),
        ("observe-every-selected-pseudo-move", make, b"        observe_candidate(m,ply);" + make.lstrip()),
        ("independent-post-make-child-prior", b"        ++legal;",
         b"        ++legal;observe_child(" + (b"q" if board_path else b"&q") + b",m,ply);"),
    ]
    generated = dict(files)
    generated["search.c"], instrumentation = source_tool.project(source, edits)
    # A small fixture TT is explicitly allocated by the existing driver. It
    # observes the actual CAS/search code; it is not the BSS ELF allocation test.
    header_edits = []
    if b'extern Entry table[] __asm__("D_kernel_tt");' in generated["tiny.h"]:
        before = b'extern Entry table[] __asm__("D_kernel_tt");'
        generated["tiny.h"] = _once(generated["tiny.h"], before, b"extern Entry *table;")
        header_edits.append({"role": "fixture-owned-TT-pointer", "before": probe.pin(before),
                             "after": probe.pin(b"extern Entry *table;")})
        matches = re.findall(rb'^_Static_assert\(TT_BITS==[0-9]+,"kernel TT profile binding"\);\n', generated["tiny.h"], re.M)
        probe.require(len(matches) == 1, "one shipping BSS TT width binding required")
        generated["tiny.h"] = _once(generated["tiny.h"], matches[0], b"")
        header_edits.append({"role": "fixture-TT12-not-shipping-layout", "before": probe.pin(matches[0]),
                             "after": probe.pin(b"")})
    driver = storage_fixture.DRIVER.encode()
    driver_edits = []

    def edit(before, after, role):
        nonlocal driver
        if isinstance(before, str): before = before.encode()
        if isinstance(after, str): after = after.encode()
        driver, record = probe._once(driver, before, after, role)
        driver_edits.append(record)

    edit(b"static void observe_entry(const Worker *,const Board *,int,int);",
         b"static void observe_entry(const Worker *,const Board *,int,int);\n"
         b"static void observe_candidate(Move,int);static void observe_child(const Board *,Move,int);"
         b"static void observe_prior(const Board *,int,int);", "observation-prototypes")
    expected = probe.independent_start()
    constant = ("static const Board fixture_expected_start={.s=1,.c=15,.e=-1,.k={4,116},.half=0,.v=0,.h=UINT64_C(" +
                str(expected["h"]) + "),.r=UINT64_C(" + str(expected["r"]) + "),.b={" +
                ",".join(map(str, expected["b"])) + "}};\n").encode()
    edit(b"static uint64_t learners",
         probe._reference_start(reference_board) + b"\n" + constant + probe.EXTRA.encode() + b"\nstatic uint64_t learners",
         "actual-observer-and-independent-domains")
    root = b"expected_prior[0]=6;"
    if prefix:
        root += b"prepare_path(&fixture_worker);"
    if board_path:
        root += b"prepare_board(&fixture_worker,p);"
    root += (b"fixture_worker.current=0;int score=search(&fixture_worker," +
             (b"" if board_path else b"p,") + b"depth,-MATE,MATE,0,6);Move best=fixture_worker.current;")
    edit(b"Move best=0;int score=search(&fixture_worker,p,depth,-MATE,MATE,0,0,&best);", root,
         "root-owner-initialization-and-actual-signature")
    if prefix:
        # The full logical history hash keeps the same index/key information.
        # Read every retained prefix and search key from the actual owned array;
        # older game records are observed only to retain the historical oracle.
        edit(b"uint64_t key=i<game_length?game_keys[i]:w->keys[i-game_length];",
             b"uint64_t key=i<game_length-w->root_keys?game_keys[i]:w->keys[i-game_length+w->root_keys];",
             "canonical-logical-prefix-and-actual-path-storage")
    if "tt_bytes" in names:
        # This is a bijection on the admitted move/score/depth/bound payload.
        # Reject nonzero gap bits instead of silently discarding an error.
        edit(b"h=add_hash(h,table[i].key);h=add_hash(h,table[i].data);",
             b"uint64_t data=table[i].data;\n"
             b"        if(((uint32_t)data&~131071u)||(data>>56)>3){puts(\"BROKEN_TT_REPRESENTATION\");abort();}\n"
             b"        uint64_t canonical=(uint32_t)data|(((data>>32)&65535)<<17)|(((data>>48)&255)<<33)|((data>>56)<<41);\n"
             b"        h=add_hash(h,table[i].key);h=add_hash(h,canonical);", "canonical-full-TT-payload")
    abi = b'    printf("ABI worker=%zu board=%zu entry=%zu\\n",sizeof(Worker),sizeof(Board),sizeof(Entry));\n'
    edit(abi, abi + b"    check_start();check_learners();\n", "independent-start-and-learning")
    promotion_runs = b'''    for(int side=-1;side<=1;side+=2){
        promotion_root(&p,side);snprintf(name,sizeof name,"promotion-%d",side);
        if(run(name,&p,2,0,1,0)==UINT64_MAX)return 7;
    }
    for(int side=0;side<2;side++)for(int piece=0;piece<4;piece++)for(int capture=0;capture<2;capture++)
        if(!promotion_seen[side][piece][capture]){puts("MISSING_PROMOTION_PRIOR");return 8;}
    printf("ORDER candidates=%" PRIu64 " prior_checks=%" PRIu64 " promotions=16\\n",order_count,prior_checks);
'''
    edit(b'    printf("TOTAL runs=%', promotion_runs + b'    printf("TOTAL runs=%', "full-promotion-and-order-coverage")
    proof = {"kind": "D-actual-search-size-next-observer", "selectors": list(names),
             "source": probe.inventory(files), "output": probe.inventory(generated),
             "observer": probe.pin(Path(__file__).read_bytes()), "actual_storage_fixture": probe.pin(authority),
             "original_search_oracle": probe.pin(Path(probe.__file__).read_bytes()),
             "source_instrumentation": instrumentation, "header_adaptations": header_edits,
             "driver_edits": driver_edits, "driver": probe.pin(driver),
             "TT_bits": 12, "TT_allocated_by_fixture": True, "actual_runtime": False,
             "reference_board": probe.pin(reference_board), "independent_start": expected,
             "comparison": "actual node order, cancellation calls, rules, priors, learners and canonical full key/payload/path"}
    return generated, driver, proof
