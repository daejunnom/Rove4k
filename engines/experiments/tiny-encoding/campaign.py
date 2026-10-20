#!/usr/bin/env python3
"""Bounded literal/command/profile encoding study; canonical Tiny A stays intact.

Every complete wrapper includes the unchanged signal/wait/cleanup/fd-exec
bootstrap. Source restoration is checked byte-for-byte. Compiler flag/profile
changes require full compiler-stdin native identity in their declared class.
"""
import argparse
import ast
from collections import Counter
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def sha(data):
    return hashlib.sha256(data).hexdigest()


def argument(script, owner, method):
    tree = ast.parse(script)
    matches = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and node.args
               and isinstance(node.func, ast.Attribute) and node.func.attr == method
               and isinstance(node.func.value, ast.Name) and node.func.value.id == owner]
    if len(matches) != 1:
        raise ValueError("expected one bootstrap call: " + owner + "." + method)
    return matches[0].args[0]


def replace_argument(script, owner, method, expression):
    node = argument(script, owner, method)
    starts = [0] + [match.end() for match in re.finditer(rb"\r\n|\r|\n", script)]
    begin = starts[node.lineno - 1] + node.col_offset
    end = starts[node.end_lineno - 1] + node.end_col_offset
    result = script[:begin] + expression.encode() + script[end:]
    ast.parse(result)
    return result


def value(node):
    # Only immutable literal methods are admitted. C input remains literal data.
    for part in ast.walk(node):
        if isinstance(part, ast.Call):
            if not isinstance(part.func, ast.Attribute) or part.func.attr not in ("encode", "replace", "split") or part.keywords:
                raise ValueError("unapproved expression call")
        if isinstance(part, (ast.Name, ast.Lambda, ast.Subscript, ast.comprehension)):
            raise ValueError("nonliteral expression")
    return eval(compile(ast.Expression(node), "<encoding-expression>", "eval"), {"__builtins__": {}})


def word_expression(source, count):
    if not source.isascii():
        raise ValueError("word codec is restricted to ASCII C input")
    text = source.decode()
    words = Counter(re.findall(r"[A-Za-z_][A-Za-z_0-9]*", text))
    selected = sorted((word for word in words if len(word) > 1),
                      key=lambda word: (-(len(word) - 1) * words[word], word))[:count]
    mapping = {word: chr(256 + index) for index, word in enumerate(selected)}
    encoded = re.sub(r"[A-Za-z_][A-Za-z_0-9]*", lambda match: mapping.get(match[0], match[0]), text)
    quote = "'''" if "'''" not in encoded else '"""'
    if quote in encoded or encoded.endswith(quote[0]) or encoded.endswith("\\"):
        raise ValueError("word codec raw literal delimiter unavailable")
    expression = "r" + quote + encoded + quote
    for word, marker in mapping.items():
        expression += ".replace(" + repr(marker) + "," + repr(word) + ")"
    return expression + ".encode()", selected


def profile_literals(source, lexer):
    replacements = {"WORKERS": "2", "TT_BITS": "18"}
    text, chunks, previous, counts = source.decode(), [], 0, Counter()
    for begin, end, token in lexer._identifier_spans(text):
        if token in replacements:
            chunks.extend((text[previous:begin], replacements[token]))
            previous = end
            counts[token] += 1
    chunks.append(text[previous:])
    if not all(counts[name] for name in replacements):
        raise ValueError("expected declared fixed resource identifiers")
    return "".join(chunks).encode(), dict(counts)


def manual_functions(source, lexer, private):
    names = ["attacked", "make", "think", "value", "start", "dead", "mix", "gen", "now"]
    if private:
        names += ["search", "probe", "capture", "claim", "learn", "piece_index", "first", "parse", "go",
                  "result", "read_line", "set_position", "number", "work", "wait", "clear", "text", "rights",
                  "piece", "state", "ep", "put", "walk", "add"]
    used = set(re.findall(r"[A-Za-z_$][A-Za-z_0-9$]*", source.decode()))
    fresh = (a + b for a, b in itertools.product("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ", repeat=2))
    result, mapping = {"main.c": source}, {}
    for name in names:
        if name not in used:
            continue
        alias = next(item for item in fresh if item not in used)
        used.add(alias)
        result = lexer._replace(result, name, alias)
        mapping[name] = alias
    return result["main.c"], mapping


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--baseline-wrapper", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cases", help="comma-separated fixed cases; no new candidate search")
    args = parser.parse_args()
    if not args.out.is_absolute() or args.out.exists() or ROOT in args.out.parents:
        parser.error("new absolute external output required")
    args.out.mkdir(parents=True)
    frozen = args.out / "frozen"
    frozen.mkdir()
    helpers = {"pack_stream.py": ROOT / "engines/compact/tiny-a/pack_stream.py",
               "rename_c.py": ROOT / "engines/scripts/rename_c.py", "literal.py": HERE / "literal.py",
               "campaign.py": Path(__file__)}
    for name, path in helpers.items():
        (frozen / name).write_bytes(path.read_bytes())
    producer = module("encoding_frozen_stream", frozen / "pack_stream.py")
    literal = module("encoding_frozen_literal", frozen / "literal.py")
    lexer = module("encoding_frozen_lexer", frozen / "rename_c.py")
    source = args.source.read_bytes()
    (frozen / "main.c").write_bytes(source)
    (frozen / "reference-wrapper").write_bytes(args.baseline_wrapper.read_bytes())
    command = ["cc", "-std=c11", "-Os", "-pthread", "-DWORKERS=2", "-DTT_BITS=18", "-DDEV=0", "-x", "c", "-", "-o", "x"]
    baseline_data, baseline_record = producer.make_stream(source, command, "xz")
    if baseline_data != args.baseline_wrapper.read_bytes():
        raise ValueError("source/producer/command does not reproduce the declared baseline wrapper")
    compile_dir = args.out / "gate"
    compile_dir.mkdir()
    compile_cache, classes, gates = {}, {}, []
    def compile_native(data, argv):
        key = (sha(data), tuple(argv))
        if key in compile_cache:
            return compile_cache[key]
        process = subprocess.run(argv, input=data, cwd=compile_dir, capture_output=True, timeout=30)
        gate = {"source_sha256": key[0], "command": argv, "returncode": process.returncode,
                "stderr": process.stderr.decode(errors="replace")}
        if not process.returncode:
            binary = (compile_dir / "x").read_bytes()
            gate.update(native_sha256=sha(binary), native_bytes=len(binary))
        gates.append(gate)
        compile_cache[key] = gate
        return gate
    classes["unstripped"] = compile_native(source, command)
    stripped_command = command + ["-s"]
    classes["stripped"] = compile_native(source, stripped_command)
    if any(record["returncode"] for record in classes.values()):
        raise ValueError("mandatory compiler-stdin baseline failed")
    cases = []
    for name, expression in literal.variants(source).items():
        cases.append(("literal-" + name, source, command, expression, "list", "unstripped", {}))
    cases += [("command-split", source, command, None, "split", "unstripped", {}),
              ("command-tuple", source, command, None, "tuple", "unstripped", {})]
    for name, removed in (("no-dev", ("-DDEV=0",)), ("no-standard", ("-std=c11",)),
                          ("no-pthread", ("-pthread",)), ("reduced-flags", ("-DDEV=0", "-std=c11", "-pthread"))):
        cases.append((name, source, [part for part in command if part not in removed], None, "split", "unstripped", {}))
    fixed, fixed_record = profile_literals(source, lexer)
    cases.append(("fixed-resource-literals", fixed, [part for part in command if not part.startswith(("-DWORKERS=", "-DTT_BITS=", "-DDEV="))],
                  None, "split", "unstripped", {"resource_literals": fixed_record}))
    reduced_fixed = [part for part in command if part not in ("-std=c11", "-pthread")
                     and not part.startswith(("-DWORKERS=", "-DTT_BITS=", "-DDEV="))]
    cases.append(("combined-fixed-reduced", fixed, reduced_fixed, None, "split", "unstripped",
                  {"resource_literals": fixed_record}))
    for count in (8, 16, 32):
        expression, dictionary = word_expression(source, count)
        cases.append(("word-codec-" + str(count), source, command, expression, "list", "unstripped", {"dictionary": dictionary}))
    cases.append(("stripped-baseline", source, stripped_command, None, "list", "stripped", {}))
    for private in (False, True):
        changed, mapping = manual_functions(source, lexer, private)
        cases.append(("stripped-functions-" + ("all" if private else "public"), changed, stripped_command,
                      None, "list", "stripped", {"manual_function_spellings": mapping}))
    renamed_fixed, mapping = manual_functions(fixed, lexer, True)
    cases.append(("combined-fixed-stripped", renamed_fixed, reduced_fixed + ["-s"], None, "split", "stripped",
                  {"resource_literals": fixed_record, "manual_function_spellings": mapping}))
    cases.append(("combined-fixed-stripped-pthread", renamed_fixed, reduced_fixed + ["-pthread", "-s"], None,
                  "split", "stripped", {"resource_literals": fixed_record, "manual_function_spellings": mapping}))
    conservative = ["cc", "-std=c11", "-Os", "-pthread", "-x", "c", "-", "-o", "x", "-s"]
    cases.append(("combined-fixed-stripped-c11-pthread", renamed_fixed, conservative, None, "split", "stripped",
                  {"resource_literals": fixed_record, "manual_function_spellings": mapping}))
    if args.cases:
        wanted = set(args.cases.split(","))
        unknown = wanted - {case[0] for case in cases}
        if unknown:
            raise ValueError("unknown fixed cases: " + repr(sorted(unknown)))
        cases = [case for case in cases if case[0] in wanted]
    records, canonical_bootstrap = [], producer.bootstrap
    for index, (name, data, argv, expression, rendering, identity, details) in enumerate(cases):
        directory = args.out / ("%02d-" % index + name)
        directory.mkdir()
        (directory / "main.c").write_bytes(data)
        record = {"case": name, "identity_class": identity, "source_sha256": sha(data), "source_bytes": len(data),
                  "command": argv, "command_rendering": rendering, **details}
        gate = compile_native(data, argv)
        record["native_gate"] = gate
        expected = classes[identity]["native_sha256"]
        if gate.get("native_sha256") != expected:
            record.update(accepted=False, reason="native_identity_gate_failed")
            records.append(record)
            continue
        script, kind = canonical_bootstrap(data, argv)
        if expression is not None:
            script = replace_argument(script, "p", "communicate", expression)
        if rendering != "list":
            cmd_expression = repr(" ".join(argv)) + ".split()" if rendering == "split" else repr(tuple(argv))
            script = replace_argument(script, "subprocess", "Popen", cmd_expression)
        if value(argument(script, "p", "communicate")) != data:
            raise ValueError("restored C bytes changed: " + name)
        if list(value(argument(script, "subprocess", "Popen"))) != list(argv):
            raise ValueError("actual compiler arguments changed: " + name)
        (directory / "bootstrap.py").write_bytes(script)
        producer.bootstrap = lambda _source, _command, chosen=script, label=name: (chosen, "experiment-" + label)
        artifacts = producer.write_stream(data, directory / "packed", argv)
        repeated = producer.write_stream(data, directory / "repeated", argv)
        for first, second in zip(artifacts, repeated):
            if Path(first["path"]).read_bytes() != Path(second["path"]).read_bytes():
                raise ValueError("complete wrapper repetition differed")
        minimum = min(artifacts, key=lambda artifact: artifact["bytes"])
        record.update(accepted=minimum["bytes"] <= baseline_record["bytes"],
                      reason="whole_file_improved" if minimum["bytes"] < baseline_record["bytes"] else
                             "whole_file_equal" if minimum["bytes"] == baseline_record["bytes"] else "whole_file_increased",
                      bootstrap_sha256=sha(script), source_restored_exactly=True, artifacts=artifacts, minimum=minimum)
        records.append(record)
        print(json.dumps({"case": name, "class": identity, "bytes": minimum["bytes"], "accepted": record["accepted"]}), flush=True)
    producer.bootstrap = canonical_bootstrap
    eligible = [record for record in records if record.get("accepted")]
    best = min(eligible, key=lambda record: record["minimum"]["bytes"])
    report = {"scope": "representation experiment; no canonical promotion or 4K eligibility claim",
              "input_source": str(args.source), "input_wrapper": str(args.baseline_wrapper),
              "experiment_recipe_sha256": sha(Path(__file__).read_bytes()),
              "baseline": baseline_record, "baseline_source_sha256": sha(source), "compiler_stdin_classes": classes,
              "helper_sha256": {name: sha((frozen / name).read_bytes()) for name in helpers},
              "compiler": subprocess.check_output(["cc", "--version"], text=True).splitlines()[0],
              "gates": gates, "records": records, "selected": best, "runtime_qualified": False}
    (args.out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"selected": best["case"], "bytes": best["minimum"]["bytes"], "identity_class": best["identity_class"]}), flush=True)


if __name__ == "__main__":
    main()
