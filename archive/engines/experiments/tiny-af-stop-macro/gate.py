"""Literal preprocessing gate for the single qA stop-load macro candidate.

Inputs are bytes.  The supplied run(command, directory, input_data, timeout)
callback owns subprocess registration, deadlines and cleanup and returns a
CompletedProcess with byte stdout/stderr.  This module starts no subprocesses.
"""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re


COMPILER_A = ("cc", "-Os", "-x", "c", "-", "-o", "x", "-s")
COMPILER_F = ("cc", "-Os", "-pthread", "-x", "c", "-", "-o", "x", "-s")
EXPRESSION = b"atomic_load_explicit(&qp,memory_order_relaxed)"
DEFINITION = b"#define qA " + EXPRESSION + b"\n"
IDENTIFIER = re.compile(rb"(?<![A-Za-z0-9_])qA(?![A-Za-z0-9_])")
TIMEOUT = 60


def _identity(data):
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


def _freshness(data):
    # Conservative freshness only: recognize ordinary splices, GCC's optional
    # whitespace before the newline, and a possible trigraph backslash.  These
    # derived bytes are never used for either output-equality admission.
    logical = re.sub(
        rb"\\[ \t\v\f]*(?:\r\n|\n|\r)", b"", data.replace(b"??/", b"\\")
    )
    raw = IDENTIFIER.search(data)
    joined = IDENTIFIER.search(logical)
    return {
        "raw_fresh": raw is None,
        "logical_fresh": joined is None,
        "raw_first_offset": None if raw is None else raw.start(),
        "logical_first_offset": None if joined is None else joined.start(),
    }


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _first_difference(original, candidate):
    limit = min(len(original), len(candidate))
    offset = next(
        (i for i in range(limit) if original[i] != candidate[i]), limit
    )
    start = max(0, offset - 24)
    end = offset + 25
    return {
        "offset": offset,
        "original_bytes": len(original),
        "candidate_bytes": len(candidate),
        "original_byte": original[offset] if offset < len(original) else None,
        "candidate_byte": candidate[offset] if offset < len(candidate) else None,
        "context_start": start,
        "original_context_hex": original[start:end].hex(),
        "candidate_context_hex": candidate[start:end].hex(),
    }


def _counter_difference(lines):
    # Preserve each distinct raw line and its multiplicity in diagnostics.
    return [{"line_hex": line.hex(), "count": count} for line, count in lines.items()]


def check(source, candidate, compiler, readable, directory, run):
    """Return a passed receipt or save a failed receipt and raise.

    No whitespace/token normalization or inverse transform is used to compare
    expanded output.  Macro admission compares Counters of raw splitlines with
    their original line endings, including duplicate definition counts.
    """
    directory = Path(directory)
    report = {
        "complete": False,
        "passed": False,
        "scope": "one qA macro; literal full expanded bytes and raw macro lines",
        "candidate_native_compiles": 0,
        "codec_calls": 0,
        "engine_runs": 0,
        "commands": [],
        "freshness": {},
        "expanded_equal": False,
        "macro_counter_equal": False,
    }

    def save_report():
        directory.mkdir(parents=True, exist_ok=True)
        temporary = directory / "gate.json.tmp"
        temporary.write_text(
            json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8"
        )
        temporary.replace(directory / "gate.json")

    def save_bytes(name, data):
        _require(isinstance(data, bytes), name + " must be raw bytes")
        (directory / name).write_bytes(data)
        return {"file": name, **_identity(data)}

    def fresh(name, data):
        result = _freshness(data)
        report["freshness"][name] = result
        _require(result["raw_fresh"] and result["logical_fresh"], name + " contains qA")

    def preprocess(label, options, data):
        command = list(base) + list(options)
        row = {
            "label": label,
            "command": command,
            "timeout": TIMEOUT,
            "returncode": None,
            "passed": False,
        }
        report["commands"].append(row)
        save_report()
        try:
            result = run(command, directory, data, TIMEOUT)
            # Do not encode strings or turn missing output into empty bytes.
            # A callback contract violation must fail rather than normalize it.
            # Save the two streams independently before rejecting either one.
            stream_errors = []
            for field in ("stdout", "stderr"):
                output = getattr(result, field, None)
                if isinstance(output, bytes):
                    row[field] = save_bytes(label + "." + field, output)
                else:
                    row[field + "_type"] = type(output).__name__
                    stream_errors.append(field)
            returncode = getattr(result, "returncode", None)
            if isinstance(returncode, int):
                row["returncode"] = returncode
            else:
                row["returncode_type"] = type(returncode).__name__
            _require(not stream_errors, label + " outputs must be raw bytes: " + ", ".join(stream_errors))
            _require(isinstance(returncode, int), label + " returncode must be an integer")
            _require(result.returncode == 0, label + " preprocessor failed")
            row["passed"] = True
            return result.stdout
        except BaseException as error:
            row["error"] = {"type": type(error).__name__, "message": str(error)}
            # CalledProcessError/TimeoutExpired can carry raw partial output.
            # Preserve it without replacing outputs already saved above.
            for field in ("stdout", "stderr"):
                partial = getattr(error, field, None)
                if field not in row and isinstance(partial, bytes):
                    row[field] = save_bytes(label + "." + field, partial)
            raise
        finally:
            save_report()

    try:
        directory.mkdir(parents=True, exist_ok=True)
        for name, data in (("source", source), ("candidate", candidate), ("readable", readable)):
            _require(isinstance(data, bytes), name + " must be raw bytes")
            report[name] = save_bytes(name + ".c", data)
        argv = tuple(compiler)
        _require(all(isinstance(part, str) for part in argv), "compiler argv must contain strings")
        report["compiler"] = list(argv)
        _require(argv in (COMPILER_A, COMPILER_F), "compiler argv is not the fixed A/F profile")
        # The exact allowlist above binds both the position and value removed.
        output_index = argv.index("-o")
        base = argv[:output_index] + argv[output_index + 2:]
        report["preprocessor_base"] = list(base)
        fresh("source", source)
        fresh("readable", readable)

        original_expanded = preprocess("baseline-expanded", ("-E", "-P"), source)
        original_macros = preprocess("baseline-macros", ("-E", "-dM"), source)
        fresh("baseline-expanded", original_expanded)
        fresh("baseline-macros", original_macros)
        candidate_expanded = preprocess("candidate-expanded", ("-E", "-P"), candidate)
        report["expanded_equal"] = original_expanded == candidate_expanded
        if not report["expanded_equal"]:
            report["expanded_first_difference"] = _first_difference(
                original_expanded, candidate_expanded
            )
        # Preserve the observed mismatch and stop before any further PP command.
        save_report()
        _require(report["expanded_equal"], "full expanded output differs; raw outputs and first difference saved")
        candidate_macros = preprocess("candidate-macros", ("-E", "-dM"), candidate)

        original_lines = Counter(original_macros.splitlines(keepends=True))
        candidate_lines = Counter(candidate_macros.splitlines(keepends=True))
        expected_lines = original_lines + Counter({DEFINITION: 1})
        report["macro_counter_equal"] = candidate_lines == expected_lines
        report["macro_lines"] = {
            "comparison": "Counter(raw bytes splitlines(keepends=True))",
            "expected_added_line_hex": DEFINITION.hex(),
            "exact_added_definition_count": candidate_lines[DEFINITION],
            "original_total_lines": sum(original_lines.values()),
            "candidate_total_lines": sum(candidate_lines.values()),
            "missing": _counter_difference(expected_lines - candidate_lines),
            "extra": _counter_difference(candidate_lines - expected_lines),
        }
        _require(candidate_lines[DEFINITION] == 1, "exact qA definition must occur once")
        _require(report["macro_counter_equal"], "macro dump differs beyond the one exact qA definition")
        report["complete"] = True
        report["passed"] = True
        return report
    except BaseException as error:
        report["complete"] = False
        report["passed"] = False
        report["error"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        save_report()
