"""Guarded tiny-A search-state source co-design experiments.

This recipe owns no engine or packaging policy.  It rewrites the readable
``tiny.h``/``search.c`` source mapping before the parent's normal specialization,
stitching, lexical compaction and whole-wrapper measurement.  Each operation is
independent so a compressed-file regression can be left out.  Unexpected owned
source shapes are errors; the canonical sources are never modified in place.

The supported search has the existing positive-depth learning calls, mate scale,
full 64-bit TT keys and nonblocking acquire/release slot lock.  No operation
changes node visitation/order, learner values, repetition/path keys, publication,
or the stored bound/depth/move bits.  The optional hole-learners operation changes
only the private learner backing layout.
"""

import re


DEFAULT_OPERATIONS = ("probe-marker", "mate-helper", "clip-helper", "positive-bonus")
OPERATIONS = DEFAULT_OPERATIONS + ("hole-learners",)


def _once(source, old, new, description):
    if source.count(old) != 1:
        raise ValueError(f"tiny search state requires exactly one {description}")
    return source.replace(old, new, 1)


def transform(sources, *, operations=DEFAULT_OPERATIONS):
    """Return copied byte sources and one observation per selected operation.

    ``sources`` uses the readable tiny-A module names (``tiny.h``, ``search.c``,
    etc.).  Operations admit DEV and shipping alike: they preserve the observed
    counter increments, calls and mutable data.  The parent remains responsible
    for whole-file size selection and engine validation.
    """
    if isinstance(operations, str):
        raise ValueError("tiny search state operations must be a sequence")
    operations = tuple(operations)
    if len(set(operations)) != len(operations) or set(operations) - set(OPERATIONS):
        raise ValueError("unknown or duplicate tiny search state operation")
    # Apply in recipe order: positive-bonus audits the readable caller forms
    # before the optional representation change maps their array accesses.
    operations = tuple(operation for operation in OPERATIONS if operation in operations)
    result = dict(sources)
    try:
        header = result["tiny.h"].decode("utf-8")
        source = result["search.c"].decode("utf-8")
    except (KeyError, AttributeError, UnicodeError) as error:
        raise ValueError("tiny search state requires readable byte tiny.h/search.c") from error
    if "\r" in header or "\r" in source:
        raise ValueError("tiny search state requires caller-normalized LF sources")
    if "typedef struct { atomic_flag lock; uint64_t key,data; } Entry;" not in header:
        raise ValueError("tiny search state requires the full-key coherent Entry")
    if "#define MATE 30000" not in header:
        raise ValueError("tiny search state requires the declared mate scale")
    if "tiny_mate(" in source or "tiny_clip(" in source:
        raise ValueError("tiny search state helpers already exist")

    observations = []
    helpers = []
    for operation in operations:
        before = len(source.encode())
        if operation == "probe-marker":
            # Every write has bound 1, 2 or 3 at bit 41, so zero cannot be a
            # written payload.  The key, lock scope/order and returned value are
            # unchanged.  In particular a busy write still does not publish.
            for fragment in (
                "if(atomic_flag_test_and_set_explicit(&e->lock,memory_order_acquire))return 0;",
                "else data=e->key==key?e->data:0;",
                "atomic_flag_clear_explicit(&e->lock,memory_order_release);",
                "bound=best<=old?3:best>=beta?2:1;",
                "((uint64_t)bound<<41)",
            ):
                if source.count(fragment) != 1:
                    raise ValueError("tiny probe marker requires unchanged coherent TT and nonzero bounds")
            if len(re.findall(r"\bprobe\s*\(", source)) != 3:
                raise ValueError("tiny probe marker requires one definition and two owned callers")
            source = _once(source, "probe(uint64_t key,int write,uint64_t data)",
                           "probe(uint64_t key,uint64_t data)", "probe signature")
            source = _once(source, "if(write)e->key=key,e->data=data;",
                           "if(data)e->key=key,e->data=data;", "probe write marker")
            source = _once(source, "data=probe(key,0,0)", "data=probe(key,0)", "TT read")
            source = _once(source, "probe(key,1,data);", "probe(key,data);", "TT write")
            proof = "Reads pass zero; each write contains a nonzero 1..3 bound at bit 41; full key and acquire/release lock unchanged."
        elif operation == "mate-helper":
            # Preserve both sequential comparisons, rather than combining the
            # comparisons before the first adjustment.  Encoding uses +ply and
            # decoding -ply, with exactly the old comparison/update order.
            source = _once(source,
                "int score=(int16_t)(data>>17),bound=(data>>41)&3,ttdepth=(data>>33)&255;",
                "int score=tiny_mate((int16_t)(data>>17),-ply),bound=(data>>41)&3,ttdepth=(data>>33)&255;",
                "TT mate read")
            source = _once(source,
                "    if(score>MATE-PLY)score-=ply;\n    if(score< -MATE+PLY)score+=ply;\n",
                "", "TT read mate adjustments")
            source = _once(source,
                "    score=best;\n    if(score>MATE-PLY)score+=ply;\n    if(score< -MATE+PLY)score-=ply;\n",
                "", "TT write mate adjustments")
            source = _once(source, "((uint64_t)(uint16_t)score<<17)",
                           "((uint64_t)(uint16_t)tiny_mate(best,ply)<<17)", "TT score packing")
            helpers.append("static int tiny_mate(int score,int ply){\n"
                           "    if(score>MATE-PLY)score+=ply;\n"
                           "    if(score< -MATE+PLY)score-=ply;\n"
                           "    return score;\n}\n")
            proof = "One ordered helper performs the same two comparisons and signed ply adjustments; move/depth/bound packing unchanged."
        elif operation == "clip-helper":
            # Keep sequential clamping even though both actual limits are
            # positive.  This is not a ternary rewrite with different priority.
            source = _once(source,
                "    int evaluation=p->s*p->v;\n"
                "    if(evaluation>MATE-PLY-1)evaluation=MATE-PLY-1;\n"
                "    if(evaluation< -MATE+PLY+1)evaluation=-MATE+PLY+1;\n",
                "    int evaluation=tiny_clip(p->s*p->v,MATE-PLY-1);\n",
                "evaluation clipping")
            source = _once(source,
                "int error=best-p->s*p->v;if(error>256)error=256;if(error< -256)error=-256;",
                "int error=tiny_clip(best-p->s*p->v,256);", "correction error clipping")
            helpers.append("static int tiny_clip(int score,int limit){\n"
                           "    if(score>limit)score=limit;\n"
                           "    return score< -limit?-limit:score;\n}\n")
            proof = "Both existing two-step saturations use one ordered helper; evaluation scale and correction update values unchanged."
        elif operation == "positive-bonus":
            if len(re.findall(r"\blearn\s*\(", source)) != 3:
                raise ValueError("tiny positive bonus requires one learner and two owned callers")
            calls = ("                int bonus=depth*depth;\n"
                     "                learn(&w->history[from][to],bonus);\n"
                     "                learn(&w->continuation[prior][piece_index(p->b[from])],bonus);")
            if source.count(calls) != 1 or "if(depth>0&&!tactical){\n" + calls not in source:
                raise ValueError("tiny positive bonus requires the unchanged positive-depth squared bonus")
            source = _once(source, "*cell+=(bonus-*cell*abs(bonus)/16384);",
                           "*cell+=(bonus-*cell*bonus/16384);", "positive learner bonus")
            proof = "Both and only callers pass depth*depth inside depth>0; abs(bonus) equals bonus for every defined execution."
        else:
            # Generated moves always have legal 0x88 from/to coordinates.
            # Original history cells therefore never occupy rows 8..15 or
            # 24..31.  Flatten the original backing before placing the two
            # other tables in those holes; no cross-row C pointer arithmetic.
            if "#define FROM(m) ((m)&127)" not in header or "#define TO(m) (((m)>>7)&127)" not in header:
                raise ValueError("tiny learner holes require the owned mailbox move representation")
            if "board.c" not in result:
                raise ValueError("tiny learner holes require the readable board generator")
            board = result["board.c"].decode("utf-8")
            if ("for(int from=0;from<128;from++){\n        if(from&0x88){from+=7;continue;}" not in board
                    or "if(!(to&0x88)" not in board):
                raise ValueError("tiny learner holes require the owned 0x88 move generator")
            for name, content in result.items():
                if name != "search.c" and name.endswith((".c", ".h")):
                    if re.search(r"(?:->|\.)\s*(?:history|continuation|correction)\s*\[", content.decode("utf-8")):
                        raise ValueError(f"tiny learner holes found an external learner access: {name}")
            expected = {"history": 2, "continuation": 2, "correction": 3}
            for field, count in expected.items():
                if len(re.findall(r"\bw\s*->\s*" + field + r"\s*\[", source)) != count:
                    raise ValueError(f"tiny learner holes require {count} owned {field} accesses")
            if source.count("w->history[from][to]") != 2 or source.count("w->correction[p->h&1023]") != 3:
                raise ValueError("tiny learner holes require the owned history/correction index forms")
            header = _once(header,
                "int16_t history[128][128],continuation[13][13],correction[1024];",
                "int16_t history[16384];", "owned learner declarations")
            source = source.replace("w->history[from][to]", "w->history[from*128+to]")
            source = _once(source, "w->continuation[prior][pi]",
                           "w->history[1024+prior*13+pi]", "continuation score read")
            source = _once(source, "w->continuation[prior][piece_index(p->b[from])]",
                           "w->history[1024+prior*13+piece_index(p->b[from])]", "continuation update")
            source = source.replace("w->correction[p->h&1023]", "w->history[p->h&1023|3072]")
            if len(re.findall(r"\bw\s*->\s*history\s*\[", source)) != 7:
                raise ValueError("tiny learner holes did not map all seven owned accesses")
            if re.search(r"\bw\s*->\s*(?:continuation|correction)\s*\[", source):
                raise ValueError("tiny learner holes retained an unmapped learner access")
            proof = "Legal history rows exclude 8..15 and 24..31; continuation maps injectively to 1024..1192 and correction to 3072..4095; all seven accesses and zero initialization preserved."
        observations.append({"operation": operation, "proof": proof,
                             "body_bytes_delta": len(source.encode()) - before})

    if helpers:
        source = _once(source, "static int piece_index(int p){return p+6;}\n",
                       "".join(helpers) + "static int piece_index(int p){return p+6;}\n",
                       "owned helper insertion point")
    result["tiny.h"] = header.encode()
    result["search.c"] = source.encode()
    return result, {"operations": observations,
                    "helper_bytes": len("".join(helpers).encode()),
                    "search_bytes_before": len(sources["search.c"]),
                    "search_bytes_after": len(result["search.c"]),
                    "header_bytes_before": len(sources["tiny.h"]),
                    "header_bytes_after": len(result["tiny.h"]),
                    "learner_payload_bytes_saved_per_worker": 2386 if "hole-learners" in operations else 0,
                    "engine_runtime_tested": False,
                    "canonical_sources_modified": False}
