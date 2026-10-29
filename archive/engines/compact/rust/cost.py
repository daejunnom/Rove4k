"""Read-only source-cost inventory for the owned Rust engine.

This is an analysis tool, never a Rust rewriter.  The item scanner understands
literal/comment delimiters and inventories function bodies; it deliberately
does not claim name resolution, reachability or compiler equivalence.  Compressed
deletion deltas are diagnostic marginal costs, not compilable candidates.
"""
import argparse
import hashlib
import importlib.util
import json
import lzma
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def syntax_mask(text):
    """Mask comments and literals without moving source offsets or newlines."""
    out = list(text)
    i = 0
    while i < len(text):
        start = i
        if text.startswith("//", i):
            end = text.find("\n", i + 2)
            i = len(text) if end < 0 else end
        elif text.startswith("/*", i):
            depth, i = 1, i + 2
            while i < len(text) and depth:
                if text.startswith("/*", i):
                    depth, i = depth + 1, i + 2
                elif text.startswith("*/", i):
                    depth, i = depth - 1, i + 2
                else:
                    i += 1
            if depth:
                raise ValueError("unterminated Rust block comment")
        else:
            raw = re.match(r'(?:br|cr|r)(#{0,255})"', text[i:])
            literal = re.match(r'(?:b|c)?(["\'])', text[i:])
            lifetime = re.match(r"'[A-Za-z_][A-Za-z_0-9]*", text[i:])
            if raw:
                marker = '"' + raw.group(1)
                end = text.find(marker, i + raw.end())
                if end < 0:
                    raise ValueError("unterminated Rust raw literal")
                i = end + len(marker)
            elif lifetime and not text.startswith("'", i + lifetime.end()):
                i += lifetime.end()
                continue
            elif literal:
                quote = literal.group(1)
                i += literal.end()
                while i < len(text):
                    if text[i] == "\\":
                        i += 2
                    elif text[i] == quote:
                        i += 1
                        break
                    else:
                        i += 1
                else:
                    raise ValueError("unterminated Rust literal")
            else:
                i += 1
                continue
        for at in range(start, i):
            if out[at] not in "\r\n":
                out[at] = " "
    return "".join(out)


def functions(data):
    text = data.decode("utf-8")
    masked = syntax_mask(text)
    pattern = re.compile(r"\b(?:pub(?:\([^\n)]*\))?\s+)?(?:unsafe\s+)?(?:const\s+)?fn\s+(\w+)\b")
    found, counts = [], {}
    for match in pattern.finditer(masked):
        begin = match.start()
        line_begin = text.rfind("\n", 0, begin) + 1
        if not text[line_begin:begin].strip():
            begin = line_begin
        # A return type such as [i16; 32] contains a semicolon that does not
        # terminate the declaration.  Only a top-level semicolon is a trait
        # prototype.  These owned signatures contain no const-expression braces.
        stack, brace = [], -1
        for at in range(match.end(), len(masked)):
            token = masked[at]
            if token in "([":
                stack.append(token)
            elif token in ")]":
                if not stack:
                    raise ValueError("unbalanced Rust function signature")
                stack.pop()
            elif not stack and token == ";":
                break
            elif not stack and token == "{":
                brace = at
                break
        if brace < 0:
            continue  # Trait declaration, not a body.
        depth, end = 1, brace + 1
        while depth and end < len(masked):
            depth += (masked[end] == "{") - (masked[end] == "}")
            end += 1
        if depth:
            raise ValueError("unbalanced function body: " + match.group(1))
        name = match.group(1)
        counts[name] = counts.get(name, 0) + 1
        found.append({"name": name, "occurrence": counts[name], "start": begin,
                      "end": end, "line": text.count("\n", 0, begin) + 1,
                      "data": text[begin:end].encode()})
    for a, b in zip(found, found[1:]):
        if a["end"] > b["start"]:
            raise ValueError("nested functions require explicit audit")
    return found


def source_files(revision):
    if revision:
        names = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", revision,
                                         "engines/rust", "engines/model"], cwd=ROOT, text=True).splitlines()
        return {name.removeprefix("engines/"): subprocess.check_output(["git", "show", revision + ":" + name], cwd=ROOT)
                for name in names if name.endswith(".rs")}
    return {path.relative_to(ROOT / "engines").as_posix(): path.read_bytes()
            for directory in (ROOT / "engines/rust", ROOT / "engines/model")
            for path in sorted(directory.rglob("*.rs"))}


def audit(files):
    compact = load("rove_cost_minify", ROOT / "engines/scripts/minify.py").compact_source
    archive = load("rove_cost_pack", ROOT / "engines/scripts/pack.py").archive_files
    packed = {name: compact(data, "rust") for name, data in files.items()}
    compressed = lambda inputs: len(lzma.compress(archive(inputs), preset=9))
    baseline = compressed(packed)
    items, modules = [], []
    for name, data in sorted(files.items()):
        module = {"path": name, "raw_bytes": len(data), "compact_bytes": len(packed[name]),
                  "sha256": hashlib.sha256(data).hexdigest()}
        modules.append(module)
        for item in functions(data):
            part = compact(item["data"], "rust")
            changed = dict(packed)
            text = data.decode()
            without = text[:item["start"]] + text[item["end"]:]
            changed[name] = compact(without.encode(), "rust")
            items.append({key: value for key, value in item.items() if key not in ("data", "start", "end")}
                         | {"path": name, "raw_bytes": len(item["data"]), "compact_bytes": len(part),
                            "lzma_marginal_deletion_bytes": baseline - compressed(changed)})
    return {"scope": "read-only source inventory; deletion deltas are non-compilable diagnostic estimates",
            "compression": {"codec": "LZMA", "format": "XZ", "preset": 9,
                            "counted_launcher_bytes": False},
            "tool_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                            for name in ("engines/compact/rust/cost.py", "engines/scripts/minify.py",
                                         "engines/scripts/pack.py")},
            "raw_bytes": sum(len(data) for data in files.values()),
            "compact_bytes": sum(len(data) for data in packed.values()),
            "archive_bytes": len(archive(packed)), "lzma_archive_bytes": baseline,
            "modules": modules, "functions": items}


def main():
    raise SystemExit("Rust A is retired; this historical structural-cost CLI is disabled.")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", help="read immutable tracked Git blobs instead of the live source tree")
    parser.add_argument("--out", type=Path, help="optional external JSON evidence path")
    args = parser.parse_args()
    record = audit(source_files(args.revision))
    record["revision"] = args.revision
    encoded = json.dumps(record, indent=2) + "\n"
    if args.out:
        output = args.out.resolve()
        if output == ROOT or ROOT in output.parents:
            parser.error("evidence output must be outside the source checkout")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded, encoding="utf-8")
    else:
        sys.stdout.write(encoded)


if __name__ == "__main__":
    main()
