"""Bind a reviewed include cleanup to the actual production compiler.

Candidate discovery belongs to NVCompact. This finite production projection
only replays the reviewed limits.h candidate, after every source consumer has
been emitted. A spelling match is not proof that an include is unused: the
producer must additionally compare complete expanded input and native images.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path

SCHEMA = "rove4k.profile-dependencies.v1"
SELF = "engines/experiments/tcec-next/profile_dependencies.py"
DECLARATION = {"path": SELF, "variant": "unused-includes"}
DIRECTIVE = b"#include<limits.h>\n"


def pin(data):
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


def require(value, message):
    if not value:
        raise ValueError(message)


def transform_source(source):
    require(type(source) is bytes and source.count(DIRECTIVE) <= 1,
            "at most one reviewed literal limits include required")
    offset = source.find(DIRECTIVE)
    spans = [] if offset < 0 else [dict(offset=offset, before=DIRECTIVE.decode(), after="")]
    result = source if offset < 0 else source[:offset] + source[offset + len(DIRECTIVE):]
    proof = dict(schema=SCHEMA, input=pin(source), output=pin(result), spans=spans,
                 full_inverse=True, semantic_gate="identical-expanded-input-and-native",
                 cost_gate="whole-artifact-non-growth")
    require(restore_source(result, proof) == source, "dependency projection inverse differs")
    return result, proof


def restore_source(candidate, proof):
    require(proof.get("schema") == SCHEMA and pin(candidate) == proof.get("output"),
            "dependency output identity differs")
    result = candidate
    for span in reversed(proof["spans"]):
        at, before, after = span["offset"], span["before"].encode(), span["after"].encode()
        require(0 <= at <= len(result) and result[at:at + len(after)] == after,
                "dependency inverse span differs")
        result = result[:at] + before + result[at + len(after):]
    require(pin(result) == proof.get("input"), "dependency restored input differs")
    return result


def preprocess_command(compiler):
    """Preserve target/optimization/feature flags, replacing only output mode."""
    command = list(compiler)
    require(command.count("-") == 1 and command.count("-o") == 1,
            "one stdin input and one native output required")
    at = command.index("-o")
    require(at + 1 < len(command) and command[at + 1] == "x" and
            not any(flag in command for flag in ("-E", "-P", "-c", "-S")),
            "reviewed native compiler mode required")
    del command[at:at + 2]
    command = [flag for flag in command if flag != "-s"]
    return [*command, "-E", "-P"]


def compile_gate(before, after, *, compiler, directory, run, prefix):
    """Use the caller's bounded process owner; no separate subprocess runner."""
    require(before != after, "dependency compiler gate requires a real edit")
    directory = Path(directory)
    directory.mkdir()
    (directory / "before.c").write_bytes(before)
    (directory / "after.c").write_bytes(after)
    command = preprocess_command(compiler)
    expanded = []
    for label, source in (("before", before), ("after", after)):
        data = run(command, cwd=directory, kind=prefix + "-dependencies-" + label, data=source)
        (directory / (label + ".i")).write_bytes(data)
        expanded.append(data)
    require(expanded[0] == expanded[1], "include removal changed expanded compiler input")
    run(compiler, cwd=directory, kind=prefix + "-dependencies-native", data=before)
    return dict(input=pin(before), output=pin(after), expanded=pin(expanded[0]),
                native=pin((directory / "x").read_bytes()))


def validate_receipt(build, manifest, proof, source, *, checked, final_compact=False):
    """Validate owned compiler evidence, not a caller-supplied equality flag.

    When an explicitly admitted final compaction follows this stage, its
    separately owned control compile is the compile of this stage's output.
    The caller must separately validate the final stage and shipping compile.
    """
    require(manifest.get("source_dependencies") == DECLARATION,
            "explicit named dependency projection required")
    require(type(final_compact) is bool, "explicit final compaction mode required")
    declaration = manifest.get("post_compact")
    if final_compact:
        require(type(declaration) is dict and set(declaration) == {"path", "variant"}
                and all(type(declaration[key]) is str and declaration[key] for key in declaration),
                "explicit final compaction declaration required")
    else:
        require(declaration is None, "final compaction requires its explicit control compile")
    before = restore_source(source, proof)
    require(transform_source(before) == (source, proof), "dependency candidate does not replay")
    compiler = manifest.get("compile_executor", manifest["compiler"])
    for attempt in manifest["attempts"]:
        directory = attempt["directory"]
        native = {key: attempt["native_" + key] for key in ("bytes", "sha256")}
        compact_diagnostics = None
        if final_compact:
            control = attempt.get("final_compact_gate")
            require(type(control) is dict and set(control) == {"directory", "source", "native", "image_identical"}
                    and control["directory"] == "final-compact-control" and control["source"] == pin(source)
                    and control["native"] == native and control["image_identical"] is True,
                    "final compaction control gate differs")
            rows = [row for row in manifest["commands"] if row.get("kind") == directory + "-final-compact-control"]
            require(len(rows) == 1 and rows[0].get("command") == list(compiler) and
                    type(rows[0].get("returncode")) is int and rows[0]["returncode"] == 0 and
                    rows[0].get("terminal") is True and rows[0].get("reaped") is True and
                    rows[0].get("owned_group_absent") is True and rows[0].get("forced_cleanup") is False,
                    "final compaction control compiler command differs")
            row = rows[0]
            stdin_name = Path(row["stdout"]["path"]).with_suffix(".stdin").name
            require(checked(build, stdin_name, pin(source)) == source,
                    "final compaction control stdin differs")
            require(checked(build, directory + "/final-compact-control/x", native) ==
                    checked(build, directory + "/native/x", native),
                    "final compaction control native differs")
            record = row["stderr"]
            compact_diagnostics = checked(build, Path(record["path"]).name,
                                          {k: record[k] for k in ("bytes", "sha256")})
            compact_cost = attempt.get("final_compact_cost")
            require(type(compact_cost) is dict and set(compact_cost) == {"before", "after"}
                    and type(compact_cost["before"]) is int and type(compact_cost["after"]) is int
                    and compact_cost["before"] >= compact_cost["after"] >= 0
                    and type(attempt["whole_bytes"]) is int and compact_cost["after"] == attempt["whole_bytes"],
                    "final compaction whole cost differs")
        gate = attempt.get("dependency_gate")
        if before == source:
            require(gate is None, "identity projection must not declare a compiler gate")
            continue
        require(isinstance(gate, dict) and gate.get("input") == pin(before)
                and gate.get("output") == pin(source), "dependency source gate differs")
        require(gate.get("native") == native, "dependency native image differs")
        root = directory + "/dependency-gate/"
        require(checked(build, root + "before.c", pin(before)) == before
                and checked(build, root + "after.c", pin(source)) == source,
                "dependency gate source differs")
        expanded = [checked(build, root + label + ".i", gate["expanded"])
                    for label in ("before", "after")]
        require(expanded[0] == expanded[1], "dependency expanded input differs")
        require(checked(build, root + "x", native) ==
                checked(build, directory + "/native/x", native), "dependency native bytes differ")
        kinds = [("before", preprocess_command(compiler)), ("after", preprocess_command(compiler)),
                 ("native", list(compiler))]
        diagnostics = []
        for label, command in kinds:
            rows = [row for row in manifest["commands"]
                    if row.get("kind") == directory + "-dependencies-" + label]
            require(len(rows) == 1 and rows[0].get("command") == command and
                    rows[0].get("returncode") == 0 and rows[0].get("terminal") is True and
                    rows[0].get("reaped") is True and rows[0].get("owned_group_absent") is True and
                    rows[0].get("forced_cleanup") is False, "dependency compiler command differs")
            row = rows[0]
            stdin_name = Path(row["stdout"]["path"]).with_suffix(".stdin").name
            stdin = source if label == "after" else before
            require(checked(build, stdin_name, pin(stdin)) == stdin,
                    "dependency compiler stdin differs")
            for pipe in ("stdout", "stderr"):
                record = row[pipe]
                # Frozen build directories can be moved; accept only their
                # owned log basename, never dereference an external receipt path.
                name = Path(record["path"]).name
                require(name.startswith("tool-") and name.endswith("." + pipe),
                        "dependency compiler log is not owned")
                data = checked(build, name, {k: record[k] for k in ("bytes", "sha256")})
                if pipe == "stdout" and label != "native":
                    require(data == expanded[0], "dependency expansion command output differs")
                if pipe == "stderr":
                    diagnostics.append((label, data))
        require(dict(diagnostics)["before"] == dict(diagnostics)["after"],
                "dependency preprocessing diagnostics differ")
        # Native diagnostics have to match the compile of the dependency
        # output: the actual shipping compile on the legacy path, or the
        # separately verified pre-compaction control on the new path.
        if final_compact:
            shipping_diagnostics = compact_diagnostics
        else:
            rows = [row for row in manifest["commands"] if row.get("kind") == directory + "-compile"]
            require(len(rows) == 1 and rows[0].get("command") == list(compiler) and
                    rows[0].get("returncode") == 0 and rows[0].get("terminal") is True and
                    rows[0].get("reaped") is True and rows[0].get("owned_group_absent") is True and
                    rows[0].get("forced_cleanup") is False, "shipping dependency compiler command differs")
            stdin_name = Path(rows[0]["stdout"]["path"]).with_suffix(".stdin").name
            require(checked(build, stdin_name, pin(source)) == source, "shipping dependency stdin differs")
            record = rows[0]["stderr"]
            shipping_diagnostics = checked(build, Path(record["path"]).name,
                                           {k: record[k] for k in ("bytes", "sha256")})
        require(dict(diagnostics)["native"] == shipping_diagnostics,
                "dependency native diagnostics differ")
        cost = gate.get("whole_cost", {})
        if final_compact:
            require(type(cost.get("before")) is int and type(cost.get("after")) is int,
                    "dependency whole cost differs")
            dependency_after = compact_cost["before"]
        else:
            dependency_after = attempt["whole_bytes"]
        require(cost.get("before", -1) >= cost.get("after", -1) >= 0
                and cost.get("after") == dependency_after, "dependency whole cost grew")
    return before
