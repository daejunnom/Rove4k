"""Strict, frozen TinyA-to-B source overlay. This is a real shipping engine.

The checked-in base is an unmodified TinyA snapshot. Every replacement is exact
and counted; a stale input fails instead of silently dropping B's algorithms.
"""
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = {
    "tiny.h": "e209d37be5c1a8b320c45de87944ed3dc55b8c006713834ad4fd1cfb5eeae19d",
    "board-generated.c.in": "d96f3981b46c13ae152da97ecf884c0a35d81081cd3b242c659ffe39b2d74235",
    "search.c": "87bec413c4dcbccafd1b9c48e2a4ae878caae11747caf942f36a1036e88c7fb8",
    "main.c": "46e31d2cd761cab09afe537af82cec1e6941eb96bdd72b9d4455ea47ca5c6b63",
    "stitch.py": "2b0d25b4855a3ed4ddd9e24b8e4b0e081439baa2ed8f744dba0215a700023f23",
    "pack_single.py": "0d7463f7b7ea4b6ff411ad81ea5efdc70828a24a6f9a305f5bf7be3c9d43b5ff",
    "pack_stream.py": "b4addefbb1233881e85707aa525ca4af7f8210d9d27f56fbb52e4440a966b99e",
}


def replace(text, old, new, count=1):
    if text.count(old) != count:
        raise ValueError("frozen overlay shape changed: " + repr(old))
    return text.replace(old, new)


def sources():
    result = {}
    for name, expected in BASE.items():
        raw = (HERE / "base" / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError("frozen base bytes changed: " + name)
        result[name] = raw.decode().replace("\r\n", "\n")
    header = result["tiny.h"]
    header = replace(header, "int8_t b[128]; int s", "int8_t b[128]; uint64_t bb[2][7]; int s")
    header = replace(header, "#define MOVES 512", "#if PLY > 879\n#error admitted HCE bound overlaps mate scale\n#endif\n#define MOVES 512")
    header = replace(header, "corr_uses,ply_aborts;", "corr_uses,ply_aborts,see_calls,see_incomplete,singular_calls,extensions;")
    board = result["board-generated.c.in"]
    board = replace(board, "/* A's mailbox is the only board representation. No bitboard or hash table\n * initialization is required. Piece and state key domains do not overlap. */",
                    "/* B maintains mailbox plus piece and occupied bitboards in put().\n * King safety and exact legal exchange share attackers(). */")
    board = replace(board, "if(old){p->h^=piece(old,q);p->v-=value(old,q);}",
                    "if(old){p->bb[old<0][abs(old)]^=bit(q);p->bb[old<0][0]^=bit(q);p->h^=piece(old,q);p->v-=value(old,q);}")
    board = replace(board, "if(v){p->h^=piece(v,q);", "if(v){p->bb[v<0][abs(v)]^=bit(q);p->bb[v<0][0]^=bit(q);p->h^=piece(v,q);")
    # bit() is defined before put(); attackers() before its first king-safety use.
    board = replace(board, "static uint64_t piece(int v,int q)", "static uint64_t bit(int q){return UINT64_C(1)<<((q>>4)*8+(q&7));}\nstatic uint64_t piece(int v,int q)")
    attacks = (HERE / "attackers.c.in").read_text().replace("\r\n", "\n")
    board = replace(board, "static int walk(const Board *,Move *,int,int);\nint attacked(const Board *p,int sq,int side){return walk(p,0,sq,side);}", attacks.rstrip())
    board = replace(board, "Board t=*p;t.b[q]=t.b[p->e-p->s*16]=0;t.b[p->e]=(int8_t)p->s;",
                    "Board t=*p;put(&t,q,0);put(&t,p->e-p->s*16,0);put(&t,p->e,p->s);")
    board = replace(board, "/* Both modes walk forward from pieces of side s. A null output list asks\n * whether any geometric attack reaches sq, even if sq holds a friendly piece.\n * Pawn pushes and castling belong only to move generation, never attacks. */\nstatic int walk(const Board *p,Move *moves,int sq,int s){",
                    "/* Forward pseudo generation. King safety and SEE both use shared attackers. */\nint gen(const Board *p,Move *moves){\n    int s=p->s;")
    board = replace(board, "if(moves&&a==1)", "if(a==1)")
    board = replace(board, "                if(!moves&&to==sq)return 1;\n", "")
    board = replace(board, "(moves&&a==1&&!target&&to!=p->e)", "(a==1&&!target&&to!=p->e)")
    board = replace(board, "if(moves)add(moves,&n,from,to,a==1);", "add(moves,&n,from,to,a==1);")
    board = replace(board, "if(moves&&a==6)", "if(a==6)")
    board = replace(board, "int gen(const Board *p,Move *moves){return walk(p,moves,0,p->s);}\n", "")
    board = replace(board, "ep(&t);return t.e==p->e&&p->h==(t.h^state(&t));",
                    "ep(&t);return !memcmp(t.bb,p->bb,sizeof t.bb)&&t.e==p->e&&p->h==(t.h^state(&t));")
    runtime = replace(result["main.c"], "id name Rove4k A", "id name Rove4k B")
    # B's focused contract reads its counters directly from the production core;
    # retain the unchanged public diagnostics for existing external verification.
    return {"tiny.h": header.encode(), "board-generated.c.in": board.encode(),
            "search.c": (HERE / "search.c").read_bytes(), "main.c": runtime.encode()}


def strip_counters(source):
    """Only remove declared no-op shipping counters; native identity is a gate."""
    text = source.decode()
    text = replace(text, "#define COUNT(w,f) ((void)0)\n", "")
    for statement in ("if(bound)COUNT(w,hits);", "if(depth<=0)COUNT(w,qs);"):
        text = replace(text, statement, "")
    calls = ("ply_aborts", "pvs", "corr_uses", "hist_updates", "cont_updates", "corr_updates",
             "see_calls", "see_incomplete", "singular_calls", "extensions")
    for field in calls:
        text = replace(text, "COUNT(w," + field + ");", "")
    if "COUNT(" in text:
        raise ValueError("unknown diagnostic left in shipping source")
    return text.encode(), {"removed_noop_counter_calls": len(calls) + 2,
                           "required_native_byte_identity": True}
