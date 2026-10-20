"""Try global C identifier substitutions behind a compiled-byte identity gate.

This is a lexical candidate generator, not a C parser or an AST equivalence
proof. Callers must supply ``compile_digest(files, trial_number)`` which builds
the *complete native executable* with the actual recipe and returns its SHA-256.
Use the same output path, inputs and flags for every invocation. The baseline
build is trial 0; failed baseline compilation is an error. Subsequent compile
errors or different executable bytes reject that substitution and retain the
last accepted source. Callback time/resource bounds belong to the caller.

Directive lines, quoted literals and comments retain their exact bytes. The
optional, recipe-dependent conversion of C trigraphs is not guessed: files
containing trigraph spellings are retained unchanged and recorded as excluded.
same spelling is replaced across all translation units, including struct fields
and names in different scopes. Header declarations, macros, stringification,
ABI names and compiler name-dependent behavior can make a lexical substitution
invalid; the native-byte comparison, rather than a lexical heuristic, decides
whether to retain it for the selected recipe. Final archive size must still be
measured separately.
"""

from collections import Counter
import hashlib
import itertools
import re


_KEYWORDS = frozenset("""
auto break case char const continue default do double else enum extern float
for goto if inline int long register restrict return short signed sizeof static
struct switch typedef union unsigned void volatile while _Alignas _Alignof
_Atomic _BitInt _Bool _Complex _Decimal32 _Decimal64 _Decimal128 _Generic
_Imaginary _Noreturn _Static_assert _Thread_local alignas alignof bool constexpr
false nullptr static_assert thread_local true typeof typeof_unqual asm
and and_eq bitand bitor compl not not_eq or or_eq xor xor_eq
""".split())
_ASCII_IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z_0-9]*\Z")
_ANY_WORD = re.compile(r"[A-Za-z_$][A-Za-z_0-9$]*")
_SHA256 = re.compile(r"[0-9a-fA-F]{64}\Z")
_LITERAL = re.compile(r'(?:u8|[LuU])?(["\'])')
_TRIGRAPH = re.compile(r"\?\?[=/'()!<>-]")
_TRIGRAPH_CHARS = dict(zip("=/'()!<>-", "#\\^[]|{}~"))
_FIRST = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
_REST = _FIRST + "0123456789"


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


def _short_names():
    length = 1
    while True:
        for first in _FIRST:
            for rest in itertools.product(_REST, repeat=length - 1):
                yield first + "".join(rest)
        length += 1


def _inventory(files):
    return {name: {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            for name, data in sorted(files.items())}


def _digest(value):
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError("compile_digest must return the full native executable SHA-256")
    return value.lower()


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


def compact_identifiers(files, compile_digest, *, max_trials=64):
    """Return accepted files and auditable candidate/gate metadata.

    ``max_trials`` bounds candidate builds, in addition to the mandatory baseline
    build. Zero requests baseline validation only. Callback exceptions reject a
    candidate; exceptions from the mandatory baseline propagate to the caller.
    Inputs are never mutated and each callback receives an independent mapping.
    """
    if not isinstance(max_trials, int) or isinstance(max_trials, bool) or max_trials < 0:
        raise ValueError("max_trials must be a nonnegative integer")
    if not files or any(not isinstance(name, str) or not name or not isinstance(data, bytes)
                        for name, data in files.items()):
        raise ValueError("files must map nonempty source names to bytes")
    accepted = dict(sorted(files.items()))
    baseline = _digest(compile_digest(dict(accepted), 0))
    counts, used, excluded = Counter(), set(_KEYWORDS) | {"main"}, {}
    for name, data in accepted.items():
        text = data.decode("utf-8")
        if _TRIGRAPH.search(text):
            excluded[name] = "trigraph spelling has recipe-dependent lexical meaning"
        counts.update(token for _, _, token in _identifier_spans(text))
        # This deliberately also reserves words in directives, literals and
        # comments. A fresh spelling must not collide with any existing token.
        used.update(_ANY_WORD.findall(text))
        used.update(_ANY_WORD.findall(_phase_two(text)[0]))
        if _TRIGRAPH.search(text):
            # Reserve spellings under both possible trigraph compiler modes,
            # although this source file itself is retained unchanged.
            converted = _TRIGRAPH.sub(lambda match: _TRIGRAPH_CHARS[match.group()[-1]], text)
            used.update(_ANY_WORD.findall(_phase_two(converted)[0]))
    candidates = sorted((name for name in counts if len(name) > 1 and
                         name not in _KEYWORDS and name != "main" and
                         _ASCII_IDENTIFIER.fullmatch(name)),
                        key=lambda name: (-(len(name) - 1) * counts[name],
                                          -counts[name], -len(name), name))
    names, trials, renames, rejected, unattempted = _short_names(), [], {}, {}, {}
    for old in candidates:
        if len(trials) >= max_trials:
            break
        new = next(name for name in names if name not in used)
        used.add(new)
        if len(new) >= len(old):
            unattempted[old] = "no_shorter_unused_identifier"
            continue
        candidate = _replace(accepted, old, new)
        trial = {"trial": len(trials) + 1, "identifier": old, "replacement": new,
                 "occurrences": counts[old],
                 "before_bytes": sum(map(len, accepted.values())),
                 "after_bytes": sum(map(len, candidate.values()))}
        try:
            digest = _digest(compile_digest(dict(candidate), trial["trial"]))
        except Exception as error:
            trial.update(status="rejected", reason="compile_error",
                         error_type=type(error).__name__, error=str(error)[:2000])
            stderr = getattr(error, "stderr", None)
            if stderr:
                trial["stderr"] = (stderr.decode(errors="replace") if isinstance(stderr, bytes)
                                   else str(stderr))[:4000]
        else:
            trial["native_sha256"] = digest
            if digest == baseline:
                accepted = candidate
                renames[old] = new
                trial.update(status="accepted", reason="native_bytes_equal")
            else:
                trial.update(status="rejected", reason="native_digest_mismatch")
        if trial["status"] == "rejected":
            rejected[old] = {key: value for key, value in trial.items()
                             if key not in ("identifier", "occurrences", "before_bytes", "after_bytes")}
        trials.append(trial)
    for old in candidates:
        if old not in renames and old not in rejected and old not in unattempted:
            unattempted[old] = "trial_limit"
    metadata = {"method": "lexical_candidates_with_full_native_sha256_gate",
                "baseline_native_sha256": baseline, "final_native_sha256": baseline,
                "max_trials": max_trials, "candidate_count": len(candidates),
                "lexically_excluded_files": excluded,
                "trials_completed": len(trials), "accepted_renames": renames,
                "rejected_renames": rejected, "unattempted_identifiers": unattempted,
                "trials": trials,
                "before": _inventory(files), "after": _inventory(accepted),
                "before_bytes": sum(map(len, files.values())),
                "after_bytes": sum(map(len, accepted.values()))}
    return accepted, metadata
