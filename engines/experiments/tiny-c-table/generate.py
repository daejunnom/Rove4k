"""Two bounded exact PSQT representations for the real AVX2 C search leaf."""
import hashlib
import struct

REPRESENTATIONS = ("startup", "readonly")


def value(piece, square):
    kind = abs(piece)
    rank, file = square >> 4, square & 7
    advance = rank if piece > 0 else 7 - rank
    center = 7 - abs(2 * file - 7) - abs(2 * rank - 7)
    score = (0, 100, 320, 330, 500, 900, 0)[kind]
    score += advance * (7 if kind == 1 else 2 if kind == 4 else 0)
    score += center * (9 if kind == 2 else 5 if kind == 3 else -3 if kind == 6 else 2 if kind in (1, 5) else 0)
    return score if piece > 0 else -score


def table_values():
    return [value(piece, (q // 8) * 16 + q % 8) for piece in range(-6, 7) for q in range(64)]


def produce(template, representation):
    if representation not in REPRESENTATIONS:
        raise ValueError("only startup or readonly exact tables are admitted")
    text = template.decode().replace("\r\n", "\n")
    if text.count("@TABLE_DECL@") != 1 or text.count("@TABLE_INIT@") != 1:
        raise ValueError("fixed PSQT template shape changed")
    values = table_values()
    if representation == "startup":
        declaration = "static int32_t tiny_table[13*64];"
        initialization = "for(int v=-6;v<=6;v++)for(int q=0;q<64;q++)tiny_table[(v+6)*64+q]=value(v,(q/8)*16+q%8);"
    else:
        declaration = "static const int32_t tiny_table[13*64]={" + ",".join(map(str, values)) + "};"
        initialization = ""
    text = text.replace("@TABLE_DECL@", declaration).replace("@TABLE_INIT@", initialization)
    if representation == "readonly":
        start = "static void __attribute__((constructor)) tiny_eval_init(void){"
        end = "}\nstatic int tiny_raw(const Board *p){"
        if text.count(start) != 1 or text.count(end) != 1:
            raise ValueError("fixed readonly constructor shape changed")
        text = text.replace(start, "#if DEV\n" + start).replace(end, "}\n#endif\nstatic int tiny_raw(const Board *p){")
    return text.encode(), {"representation": representation, "rows": 13, "squares": 64,
                           "elements": len(values), "element_type": "signed-32", "table_bytes": len(values) * 4,
                           "table_i32le_sha256": hashlib.sha256(struct.pack("<832i", *values)).hexdigest(),
                           "declaration_source_bytes": len(declaration.encode()),
                           "initialization_source_bytes": len(initialization.encode()),
                           "initialization": "832 calls to the exact original value() before main" if representation == "startup" else "source initializer, no shipping runtime arithmetic",
                           "shipping_constructor": representation == "startup",
                           "actual_leaf": "8 AVX2 gathers cover all 64 visible squares; SIMD sum returned to search",
                           "cached_hce_used": False, "runtime_isa_selection": False}
