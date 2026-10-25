"""One fixed same-TU A/F storage18 shipping spelling policy.

The exact policy is embedded as immutable literal bytes. This ordinary helper
accepts only the qualified post-A31/F73 shipping C and its own canonical readable
source. Its scanners are source copies of the qualified lexical/opaque checks;
there are no source paths, side files, imports of other project modules, alias
discovery, preprocessing, compilation, packaging, or engine execution.

The readable reservation union is embedded from both exact audited canonical
inputs. A caller supplies only its own family readable bytes; no other engine is
read at runtime. Declaration roles and native/whole/runtime qualification remain
the qualified recipe's separate contracts, not a general lexical AST proof.
"""

from collections import Counter
import hashlib
import json
import re


_POLICY_SHA256 = "e89afbf078f902a4cfc3c0ee8c1fba525966be76e4df14b18f50746c2d40cff3"
_POLICY_BYTES = b'''{
  "format": 1,
  "policy": "one-fixed-private-storage18-AF-20261020",
  "scope": "final shipping-only18 private global/static object aliases after unchanged baseline A31/F73; no alternativealias/order search",
  "mapping": {
    "back": "qa",
    "command": "qb",
    "deadline": "qc",
    "epoch": "qd",
    "fallback": "qe",
    "finished": "qf",
    "game_keys": "qg",
    "game_length": "qh",
    "material": "qi",
    "mutex": "qj",
    "pending": "qk",
    "position": "ql",
    "quitting": "qm",
    "ready": "qn",
    "steps": "qo",
    "stopped": "qp",
    "table": "qq",
    "workers": "qr"
  },
  "allowed_shipping_names": [
    "back",
    "command",
    "deadline",
    "epoch",
    "fallback",
    "finished",
    "game_keys",
    "game_length",
    "material",
    "mutex",
    "pending",
    "position",
    "quitting",
    "ready",
    "steps",
    "stopped",
    "table",
    "workers"
  ],
  "protected_shipping_names": [
    "B",
    "C",
    "CLOCK_MONOTONIC",
    "E",
    "EOF",
    "FROM",
    "G",
    "H",
    "HISTORY",
    "LLONG_MAX",
    "MATE",
    "MOVE",
    "MOVES",
    "Move",
    "NULL",
    "PLY",
    "PROMO",
    "PTHREAD_COND_INITIALIZER",
    "PTHREAD_MUTEX_INITIALIZER",
    "R",
    "S",
    "TO",
    "U",
    "UINT64_C",
    "V",
    "a",
    "a1",
    "a2",
    "a4",
    "a5",
    "a7",
    "aA",
    "aB",
    "aC",
    "aD",
    "aE",
    "aF",
    "aG",
    "aH",
    "aI",
    "aJ",
    "aK",
    "aL",
    "aM",
    "aN",
    "aO",
    "aP",
    "aQ",
    "aR",
    "aS",
    "aT",
    "aU",
    "aV",
    "aW",
    "aX",
    "aZ",
    "aa",
    "ab",
    "abort",
    "abs",
    "ac",
    "ad",
    "ae",
    "af",
    "ag",
    "ah",
    "ai",
    "aj",
    "ak",
    "al",
    "am",
    "an",
    "ao",
    "ap",
    "aq",
    "ar",
    "as",
    "at",
    "atomic_flag",
    "atomic_flag_clear",
    "atomic_flag_clear_explicit",
    "atomic_flag_test_and_set_explicit",
    "atomic_int",
    "atomic_load_explicit",
    "atomic_store",
    "au",
    "av",
    "aw",
    "ax",
    "ay",
    "az",
    "b",
    "ba",
    "bb",
    "bc",
    "bd",
    "be",
    "bf",
    "bg",
    "bh",
    "break",
    "c",
    "calloc",
    "char",
    "clock",
    "clock_gettime",
    "const",
    "continue",
    "d",
    "e",
    "else",
    "f",
    "fflush",
    "flockfile",
    "for",
    "free",
    "funlockfile",
    "getchar",
    "goto",
    "h",
    "i",
    "id",
    "if",
    "int",
    "int16_t",
    "int8_t",
    "j",
    "k",
    "l",
    "m",
    "main",
    "memcpy",
    "memory_order_acquire",
    "memory_order_relaxed",
    "memory_order_release",
    "n",
    "o",
    "p",
    "pi",
    "printf",
    "pthread_cond_broadcast",
    "pthread_cond_t",
    "pthread_cond_wait",
    "pthread_create",
    "pthread_join",
    "pthread_mutex_lock",
    "pthread_mutex_t",
    "pthread_mutex_unlock",
    "pthread_t",
    "puts",
    "q",
    "r",
    "return",
    "s",
    "shutdown",
    "size_t",
    "sizeof",
    "sq",
    "static",
    "stdout",
    "strcmp",
    "strcpy",
    "strlen",
    "strncmp",
    "strstr",
    "strtok_r",
    "struct",
    "t",
    "timespec",
    "to",
    "tt",
    "tv_nsec",
    "tv_sec",
    "typedef",
    "uint16_t",
    "uint64_t",
    "unsigned",
    "v",
    "void",
    "w",
    "while",
    "x",
    "ya",
    "yb",
    "yc",
    "yd",
    "ye",
    "yf",
    "yg",
    "yh",
    "yi",
    "yj",
    "yk",
    "z",
    "z0",
    "z1",
    "z2",
    "z3",
    "z4",
    "z5",
    "z6",
    "z7",
    "z8",
    "z9",
    "zA",
    "zB",
    "zC",
    "zD",
    "zE",
    "zF",
    "zG",
    "zH",
    "zI",
    "zJ",
    "zK",
    "zL",
    "zM",
    "zN",
    "zO",
    "zP",
    "zQ",
    "zR",
    "zS",
    "zT",
    "zU",
    "zV",
    "zW",
    "zX",
    "zY",
    "zZ",
    "za",
    "zb",
    "zc",
    "zd",
    "ze",
    "zf",
    "zg",
    "zh",
    "zi",
    "zj",
    "zk",
    "zl",
    "zm",
    "zn",
    "zo",
    "zp",
    "zq",
    "zr",
    "zs",
    "zt",
    "zu",
    "zv",
    "zw",
    "zx",
    "zy",
    "zz"
  ],
  "resource_literals": {},
  "readable_inputs": {
    "engines/compact/tiny-entry-a/engine.c": {
      "bytes": 24820,
      "sha256": "71f9ff6ce1b7f555ad85c3bf49766381c0627315da94acf0c49eeee7bee4a734"
    },
    "engines/compact/tiny-entry-f/engine.c": {
      "bytes": 26100,
      "sha256": "dc065b98d99a147f862bd2d4cb0a1349ff79a2da7c1be873d906dff71cc9cd89"
    }
  },
  "families": {
    "A": {
      "source": {
        "bytes": 10606,
        "sha256": "252d87ed58df8c86b2d7898fafcedc0bed1c3bab447846b484e5afbdd5b27ac3"
      },
      "candidate": {
        "bytes": 10184,
        "sha256": "9e764bbbea91f198a4cb5aff62aae9f3007df5f715d4d8b8142e4795b5109d5a"
      },
      "alpha_counts": {
        "back": 3,
        "command": 4,
        "deadline": 3,
        "epoch": 4,
        "fallback": 3,
        "finished": 4,
        "game_keys": 4,
        "game_length": 5,
        "material": 2,
        "mutex": 13,
        "pending": 5,
        "position": 8,
        "quitting": 4,
        "ready": 0,
        "steps": 2,
        "stopped": 8,
        "table": 9,
        "workers": 6
      },
      "source_saved_bytes": 422,
      "alpha_saved_bytes": 422,
      "mapping_used": 17,
      "source_edits_count": 87,
      "retained_directive_bytes": 432,
      "opaque_regions_preserved": 53,
      "preserved_PLY_code_uses": 8
    },
    "F": {
      "source": {
        "bytes": 11216,
        "sha256": "5c4008afe4a0708558eb829c815a7a095c436df92a3a7685e8553e24efedb991"
      },
      "candidate": {
        "bytes": 10745,
        "sha256": "fa03bfe65508b5fd72097940cea869c79744a8d3d2fa3bd09f8cd60b90173dc2"
      },
      "alpha_counts": {
        "back": 3,
        "command": 4,
        "deadline": 3,
        "epoch": 4,
        "fallback": 3,
        "finished": 5,
        "game_keys": 4,
        "game_length": 5,
        "material": 2,
        "mutex": 16,
        "pending": 4,
        "position": 8,
        "quitting": 4,
        "ready": 3,
        "steps": 2,
        "stopped": 10,
        "table": 9,
        "workers": 10
      },
      "source_saved_bytes": 471,
      "alpha_saved_bytes": 471,
      "mapping_used": 18,
      "source_edits_count": 99,
      "retained_directive_bytes": 416,
      "opaque_regions_preserved": 52,
      "preserved_PLY_code_uses": 0
    }
  },
  "provenance": {
    "one_literal_proposal_sha256": "a0e047f1e11ea22956962a13107db2a28c457009137b5d04d671e55e63b9d488",
    "proposal_or_old_reports_are_normal_build_dependencies": false
  },
  "protected_contract": "all original functions/main/externalAPI/types, directives/macro bodies, strings/comments, DEV and oldmappingliteraldecisions remain unchanged",
  "numeric_inverse_replacements": 0
}
'''
if hashlib.sha256(_POLICY_BYTES).hexdigest() != _POLICY_SHA256:
    raise ValueError("embedded fixed storage policy SHA-256 mismatch")

# Exact union of raw and phase-two words from the two policy-pinned readables.
_READABLE_RESERVED = frozenset("""
A Admission B Board Both Bounds CLOCK_MONOTONIC COUNT Canonicalize Contention Correction Current
DEV EOF EP Each Entry Every F FEN FIDE FROM Full HCE HISTORY Horizon Internal K KQkq Keep L
LEGAL LLONG_MAX MATE MOVE MOVES MTD Move N NULL Neither No Only P PLY PNBRQK PROMO
PTHREAD_COND_INITIALIZER PTHREAD_MUTEX_INITIALIZER PVS Pawn Piece Q QS R Retain Root Rove4k
Search Signed TINY_H TO TT TT_BITS This Thus Two UINT64_C UINT64_MAX WORKERS Worker
_POSIX_C_SOURCE a a1 abort aborts abs acquired across add admissible admitted advance affect
after all along alpha already an and any apply applying are asks
atomic_compare_exchange_weak_explicit atomic_fetch_add_explicit atomic_flag atomic_flag_clear
atomic_flag_clear_explicit atomic_flag_test_and_set_explicit atomic_int atomic_load
atomic_load_explicit atomic_store atomic_uint_fast64_t attack attacked attacks b back bad before
belong belongs best bestmove beta binc bit bitboard board boards bonus bound bounds break btime
budget busy c calloc came capture captured castle castles castling cell center ch changes char
check claim clear clock clock_gettime colors combines command completed completed_depth
conservative const cont cont_updates context continuation continuation_updates continue contract
corr corr_updates corr_uses correction correction_updates correction_uses count counts covers cp
created ctype cutoffs d data dead deadline deeper define depth destination different digest
disabled discoveries distinct distinguish do domains draw drawn e each earlier eligibility else
en end endif endpoints ends ep epoch errno error eval evaluation even exactly exceeds exists
explores exposes f f_conflicts f_converged f_lower f_probes f_upper f_upper_other fail fallback
false fen fflush file filtered finished first fixed flockfile for forward free friendly from
full funlockfile game_keys game_length gen generation geometric geometry getchar go good goto h
h8 half halfmove has hash have heuristics high hist hist_updates history history_updates hits
holds home horizons i id if ifndef implementation in inc include includes including incremental
infinite info initialization int int16_t int8_t integer intentionally invariant irreversible is
isready isupper it iteration its j k key keys king kings knights last later leaf learn legal
length letters limit limits line list llu llx lock long lower m mailbox main make mate material
max_depth may meaning means members memcmp memcpy memory_order_acquire memory_order_relaxed
memory_order_release minors miss mix modes move moves movetime must mutable mutex n name nbrq
never next no nodes nonfirst nor normal normalized not now nuciok null number observation
occupancy occurrences of old one only or order ordered ordering ordinary origin output overlap
own p parse pass passant path paths pawn payload payloads pending perft pi piece piece_index
pieces pins plus ply ply_aborts position positions positive present preserves previous printf
prior probe prohibition prom promotion promotions prove proves pseudo pthread
pthread_cond_broadcast pthread_cond_t pthread_cond_wait pthread_create pthread_join
pthread_mutex_lock pthread_mutex_t pthread_mutex_unlock pthread_t publication publishes pushes
put puts pv pvs q qs quiescence quiet quiet_score quit quitting r rank raw reached reaches read
read_line ready readyok reduce reduction refers remain repeat repeated repetition repetitions
representation requested required resets result resulting retains return returns reversible
rights rook root runtimes s safety save scale score scores search searched seen selective
set_position share shared shift shutdown side since single size_t sizeof slot slots so sq
squares start startpos state static stats status stay stdatomic stdint stdio stdlib stdout steps
still stop stopped storing strchr strcmp strcpy string strlen strncmp strstr strtok_r strtol
struct successful t table tactical target test tested text the their think third this threads
through tie time timespec to torn total total_threads toupper transit true try tt tt_hits
ttdepth tv_nsec tv_sec typedef u uci ucinewgame uciok uint16_t uint64_t uncapturable under
unsigned upper used uses v valid value verify verify_board visit void w wait waiting walk
whether while white whose winc with without witness work worker workers written wtime x x88
x94d049bb133111eb x9e3779b97f4a7c15 xbf58476d1ce4e5b9 z
""".split())
_READABLE_RESERVED_SHA256 = '9e5385d1267627cedde157e22cd8cb51a85da1ac3c3c558def2cfa34b489e585'




_KEYWORDS = frozenset("""
auto break case char const continue default do double else enum extern float
for goto if inline int long register restrict return short signed sizeof static
struct switch typedef union unsigned void volatile while _Alignas _Alignof
_Atomic _BitInt _Bool _Complex _Decimal32 _Decimal64 _Decimal128 _Generic
_Imaginary _Noreturn _Static_assert _Thread_local alignas alignof bool constexpr
false nullptr static_assert thread_local true typeof typeof_unqual asm
and and_eq bitand bitor compl not not_eq or or_eq xor xor_eq
""".split())


_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z_0-9]*\Z")


_WORD = re.compile(r"[A-Za-z_$][A-Za-z_0-9$]*")


_TRIGRAPH = re.compile(r"\?\?[=/'()!<>-]")


_LITERAL = re.compile(r"(?:u8|[LuU])?([\"'])")


def _word_start(char):
    # Keep an entire non-ASCII spelling opaque, including combining marks;
    # do not accidentally offer just its ASCII prefix as a candidate.
    return char in "_$" or char.isalpha() or ord(char) >= 128 and not char.isspace()


def _word_part(char):
    return _word_start(char) or char.isdigit()


def _logical_end(text, start):
    """End of a directive or // comment in already phase-2 logical text."""
    end = text.find("\n", start)
    return len(text) if end < 0 else end + 1


def _quoted_end(text, start):
    quote, pos = text[start], start + 1
    while pos < len(text):
        if text[pos] == "\\":
            pos += 2
        elif text[pos] == quote:
            return pos + 1
        elif text[pos] in "\r\n":
            raise ValueError("unescaped newline in C quoted literal")
        else:
            pos += 1
    raise ValueError("unterminated C quoted literal")


def _unspliced_identifier_spans(text):
    """Scan C after phase-2 line splicing, returning logical offsets."""
    pos, prefix = 0, True
    while pos < len(text):
        char = text[pos]
        if char.isspace():
            if char in "\r\n":
                prefix = True
            pos += 1
            continue
        if text.startswith("//", pos):
            pos = _logical_end(text, pos)
            prefix = True
            continue
        if text.startswith("/*", pos):
            end = text.find("*/", pos + 2)
            if end < 0:
                raise ValueError("unterminated C block comment")
            if "\n" in text[pos:end + 2] or "\r" in text[pos:end + 2]:
                prefix = True
            pos = end + 2
            continue
        if prefix and (char == "#" or text.startswith(("%:", "??="), pos)):
            pos = _logical_end(text, pos)
            prefix = True
            continue
        prefix = False
        literal = _LITERAL.match(text, pos)
        if literal:
            pos = _quoted_end(text, literal.end() - 1)
            continue
        # C preprocessing numbers include exponent signs and identifier-like
        # suffixes. Do not treat 0xabcdef, 1e+6 or 12UL as editable names.
        if char.isdigit() or char == "." and pos + 1 < len(text) and text[pos + 1].isdigit():
            end = pos + 1
            while end < len(text):
                item = text[end]
                if _word_part(item) or item in ".'":
                    end += 1
                elif item in "+-" and text[end - 1] in "eEpP":
                    end += 1
                else:
                    break
            pos = end
            continue
        if _word_start(char) or text.startswith(("\\u", "\\U"), pos):
            end = pos
            while end < len(text):
                if _word_part(text[end]):
                    end += 1
                elif text.startswith(("\\u", "\\U"), end):
                    digits = 4 if text[end + 1] == "u" else 8
                    end += 2 + digits
                else:
                    break
            yield pos, end, text[pos:end]
            pos = end
            continue
        pos += 1


def _phase_two(text):
    """Apply line splicing once, retaining every surviving original offset."""
    logical, offsets, pos = [], [], 0
    while pos < len(text):
        if text.startswith("\\\r\n", pos):
            pos += 3
        elif text.startswith("\\\n", pos):
            pos += 2
        else:
            logical.append(text[pos])
            offsets.append(pos)
            pos += 1
    return "".join(logical), offsets


def _identifier_spans(text):
    """Yield original offsets, preserving comments formed by line splicing.

    Spliced identifiers themselves are excluded: changing only a physical
    fragment would not be an identifier-token substitution. The supplied
    specialized/minified input normally contains no such continuations.
    """
    if _TRIGRAPH.search(text):
        return
    if "\\\n" not in text and "\\\r\n" not in text:
        yield from _unspliced_identifier_spans(text)
        return
    logical, offsets = _phase_two(text)
    for start, end, token in _unspliced_identifier_spans(logical):
        original_start, original_end = offsets[start], offsets[end - 1] + 1
        if text[original_start:original_end] == token:
            yield original_start, original_end, token


def _replace(files, old, new):
    result = {}
    for name, data in files.items():
        text, output, previous = data.decode("utf-8"), [], 0
        for start, end, token in _identifier_spans(text):
            if token == old:
                output.extend((text[previous:start], new))
                previous = end
        output.append(text[previous:])
        result[name] = "".join(output).encode("utf-8")
    return result


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _binding(data, expected, label):
    if len(data) != expected["bytes"] or _sha(data) != expected["sha256"]:
        raise ValueError(label + " bytes/SHA-256 mismatch")


def _logical(text):
    """Independent physical-offset map for opaque-region preservation checks."""
    chars, offsets, pos = [], [], 0
    while pos < len(text):
        if text.startswith("\\\r\n", pos):
            pos += 3
        elif text.startswith("\\\n", pos):
            pos += 2
        else:
            chars.append(text[pos])
            offsets.append(pos)
            pos += 1
    return "".join(chars), offsets


def _opaque_parts(text):
    """Inventory exact directive, comment, and quoted-literal physical bytes.

    This deliberately uses a scanner separate from the supplied identifier
    lexer. It checks preservation, not header expansion or C name resolution.
    Phase-two splicing is considered before recognizing opaque regions.
    """
    if _TRIGRAPH.search(text):
        raise ValueError("trigraph spellings are outside the fixed policy")
    logical, offsets = _logical(text)
    parts, pos, prefix = [], 0, True
    while pos < len(logical):
        char, start = logical[pos], pos
        if char.isspace():
            if char in "\r\n":
                prefix = True
            pos += 1
            continue
        kind = None
        if prefix and (char == "#" or logical.startswith("%:", pos)):
            kind = "directive"
            end = logical.find("\n", pos)
            pos = len(logical) if end < 0 else end + 1
            prefix = True
        elif logical.startswith("//", pos):
            kind = "comment"
            end = logical.find("\n", pos)
            pos = len(logical) if end < 0 else end + 1
            prefix = True
        elif logical.startswith("/*", pos):
            kind = "comment"
            end = logical.find("*/", pos + 2)
            if end < 0:
                raise ValueError("unterminated C block comment")
            pos = end + 2
            if "\n" in logical[start:pos] or "\r" in logical[start:pos]:
                prefix = True
        else:
            prefix = False
            literal = _LITERAL.match(logical, pos)
            if literal:
                kind = "literal"
                quote, pos = literal.group(1), literal.end()
                while pos < len(logical):
                    if logical[pos] == "\\":
                        pos += 2
                    elif logical[pos] == quote:
                        pos += 1
                        break
                    elif logical[pos] in "\r\n":
                        raise ValueError("unescaped newline in C quoted literal")
                    else:
                        pos += 1
                else:
                    raise ValueError("unterminated C quoted literal")
            else:
                pos += 1
        if kind:
            parts.append((kind, text[offsets[start]:offsets[pos - 1] + 1]))
    return tuple(parts)


def _rewrite(data, substitutions):
    """Apply a supplied fixed mapping; exposed privately for pure fixtures."""
    if not isinstance(data, bytes):
        raise ValueError("source must be immutable bytes")
    text = data.decode("utf-8")
    if not all(_IDENTIFIER.fullmatch(old) and isinstance(new, str)
               and (_IDENTIFIER.fullmatch(new) or new.isdecimal())
               for old, new in substitutions.items()):
        raise ValueError("invalid fixed substitution")
    aliases = [new for new in substitutions.values() if not new.isdecimal()]
    if len(aliases) != len(set(aliases)):
        raise ValueError("fixed aliases must be injective")
    reserved = set(_WORD.findall(text)) | set(_WORD.findall(_logical(text)[0]))
    reserved |= set(_KEYWORDS) | set(substitutions) | {"main"}
    if reserved.intersection(aliases):
        raise ValueError("fixed alias is not fresh")
    opaque = _opaque_parts(text)
    output, previous, span_end, counts = [], 0, 0, Counter()
    for start, end, token in _identifier_spans(text):
        if not (isinstance(start, int) and isinstance(end, int)
                and span_end <= start < end <= len(text)
                and text[start:end] == token and _IDENTIFIER.fullmatch(token)):
            raise ValueError("invalid or overlapping lexer span")
        span_end = end
        if token in substitutions:
            output.extend((text[previous:start], substitutions[token]))
            previous = end
            counts[token] += 1
    output.append(text[previous:])
    candidate = "".join(output).encode("utf-8")
    repeated = {"source.c": data}
    for old, new in substitutions.items():
        repeated = _replace(repeated, old, new)
    if repeated != {"source.c": candidate}:
        raise ValueError("single-pass and repeated _replace disagree")
    if _opaque_parts(candidate.decode("utf-8")) != opaque:
        raise ValueError("directive/literal/comment bytes changed")
    return candidate, counts, opaque


def transform_source(source: bytes, *, family: str, readable: bytes):
    """Apply the sole fixed18 policy to one exact shipping/readable pair.

    The input stage follows the unchanged local A31/F73 aliases. DEV source,
    other families, modified bytes and already-transformed source fail closed.
    Only source reproduction is checked here; no native/package gate is run.
    """
    if not isinstance(source, bytes) or not isinstance(readable, bytes):
        raise ValueError("immutable shipping and canonical readable bytes required")
    if not isinstance(family, str) or family not in ("A", "F"):
        raise ValueError("unknown fixed AF storage family")
    if _sha(_POLICY_BYTES) != _POLICY_SHA256:
        raise ValueError("embedded fixed storage policy SHA-256 mismatch")
    fixed = json.loads(_POLICY_BYTES)
    row = fixed["families"][family]
    _binding(source, row["source"], family + " post-local-alpha shipping input")
    relative = "engines/compact/tiny-entry-" + family.lower() + "/engine.c"
    _binding(readable, fixed["readable_inputs"][relative], family + " canonical readable")
    mapping, resources = fixed["mapping"], fixed["resource_literals"]
    if resources or len(mapping) != 18 or fixed["numeric_inverse_replacements"] != 0:
        raise ValueError("fixed18 object-only policy changed")
    if (sorted(mapping) != fixed["allowed_shipping_names"]
            or set(mapping).intersection(fixed["protected_shipping_names"])):
        raise ValueError("protected or unaudited old spelling admitted")
    if any(len(old) <= 2 or not re.fullmatch(r"q[a-r]", new)
           for old, new in mapping.items()):
        raise ValueError("unexpected fixed storage alias rule")
    aliases = set(mapping.values())
    if len(aliases) != 18:
        raise ValueError("noninjective fixed storage aliases")
    reserved_bytes = ("\n".join(sorted(_READABLE_RESERVED)) + "\n").encode("utf-8")
    if _sha(reserved_bytes) != _READABLE_RESERVED_SHA256:
        raise ValueError("embedded readable reservation union changed")
    own_text = readable.decode("utf-8")
    own_words = set(_WORD.findall(own_text)) | set(_WORD.findall(_logical(own_text)[0]))
    if not own_words.issubset(_READABLE_RESERVED):
        raise ValueError("canonical readable reservation union differs")
    if aliases.intersection(_READABLE_RESERVED | own_words):
        raise ValueError("alias occurs in a qualified readable source")
    before = _sha(source)
    candidate, counts, opaque = _rewrite(source, mapping)
    alpha_counts = {old: counts[old] for old in mapping}
    if alpha_counts != row["alpha_counts"]:
        raise ValueError("literal storage token occurrence counts changed")
    alpha_saved = sum((len(old) - len(new)) * counts[old] for old, new in mapping.items())
    directive_bytes = sum(len(raw.encode("utf-8")) for kind, raw in opaque if kind == "directive")
    used = sum(counts[old] > 0 for old in mapping)
    if (alpha_saved != row["alpha_saved_bytes"]
            or len(source) - len(candidate) != row["source_saved_bytes"]
            or used != row["mapping_used"] or sum(counts.values()) != row["source_edits_count"]
            or directive_bytes != row["retained_directive_bytes"]
            or len(opaque) != row["opaque_regions_preserved"]):
        raise ValueError("literal storage arithmetic or opaque count changed")
    ply_before = sum(token == "PLY" for _, _, token in _identifier_spans(source.decode("utf-8")))
    ply_after = sum(token == "PLY" for _, _, token in _identifier_spans(candidate.decode("utf-8")))
    if ply_before != row["preserved_PLY_code_uses"] or ply_after != ply_before:
        raise ValueError("PLY code uses changed")
    _binding(candidate, row["candidate"], family + " sole storage candidate")
    if _sha(source) != before:
        raise ValueError("source mutated")
    return candidate, {
        "family": family, "policy": fixed["policy"], "policy_sha256": _POLICY_SHA256,
        "before": dict(row["source"]), "after": dict(row["candidate"]),
        "readable": dict(fixed["readable_inputs"][relative]),
        "readable_reservation_inputs": fixed["readable_inputs"],
        "readable_reservation_sha256": _READABLE_RESERVED_SHA256,
        "readable_reservation_scope": "embedded exact audited union; own family readable bytes checked",
        "mapping": mapping, "mapping_used": used, "alpha_counts": alpha_counts,
        "resource_literals": resources, "resource_counts": {},
        "alpha_saved_bytes": alpha_saved, "resource_saved_bytes": 0,
        "source_saved_bytes": len(source) - len(candidate),
        "source_edits_count": sum(counts.values()), "retained_directive_bytes": directive_bytes,
        "opaque_regions_preserved": len(opaque), "preserved_PLY_code_uses": ply_after,
        "prior_A31_F73_decisions_unchanged": True,
        "independent_opaque_and_rewrite_checks": True,
        "input_immutable": True, "source_only_proof": True,
        "native_or_package_gate_executed": False,
    }
