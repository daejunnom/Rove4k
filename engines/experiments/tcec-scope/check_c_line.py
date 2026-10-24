"""Opt-in Linux qualification of an exact c_line input and explicit variant.

The real public main reads the test lines.  Diagnostic-only ready observers expose
complete Board/history bytes; normal shipping compiles contain no observer/shim.
The libc getline failure shim returns ENOMEM/EIO with NULL or poisoned contents
to establish that negative returns leave the loop without examining that buffer.
It is API failure injection, not host memory exhaustion.  Generated data belongs
in a fresh explicitly named directory outside Git.  No winner is adopted here.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

import c_input
import c_line
import check_c_input as input_check


_MAIN = {"A": ("L", "F"), "B": ("I", "ql"), "C": ("int", "ql"),
         "E": ("L", "ql"), "F2": ("S", "Z"), "F8": ("S", "Z")}


def _instrument(source, family, assertion):
    integer, root = _MAIN[family]
    main = f"{integer} main(void)".encode("ascii")
    if source.count(main) != 1 or source.count(b'puts("readyok");') != 1:
        raise ValueError("public-main observer admission differs")
    source = source.replace(main, b"static void rv_line_emit(void);" + main)
    source = source.replace(b'puts("readyok");', b'rv_line_emit();puts("readyok");')
    observer = rf'''
{assertion or ""}
static void rv_line_emit(void){{
 const unsigned char*rv_bytes=(const unsigned char*)&{root};
 printf("P %d ",(int)qh);
 for(size_t rv_i=0;rv_i<sizeof {root};rv_i++)printf("%02x",rv_bytes[rv_i]);
 for(int rv_i=0;rv_i<qh;rv_i++)printf(" %016llx",(unsigned long long)qg[rv_i]);
 putchar('\n');
}}
#include <errno.h>
ssize_t __real_getline(char**,size_t*,FILE*);
ssize_t __wrap_getline(char**rv_line,size_t*rv_capacity,FILE*rv_stream){{
 static unsigned rv_calls;
 if(!rv_calls&&(*rv_line||*rv_capacity))abort();
 const char*rv_mode=getenv("RV_LINE_FAIL");
 int rv_fail=rv_mode&&(*rv_mode!='A'||rv_calls);
 ++rv_calls;
 if(rv_fail){{
   *rv_line=*rv_mode=='N'?NULL:(char*)1;*rv_capacity=0;
   errno=*rv_mode=='E'?EIO:ENOMEM;return -1;
 }}
 return __real_getline(rv_line,rv_capacity,rv_stream);
}}
'''
    return source + observer.encode("ascii")


def _campaign(extended):
    lines, history = ["uci"], []
    for record in input_check._records():
        lines.extend((record, "isready"))
        tokens = record.split()
        history.append(1 + max(0, len(tokens) - 3))
    record = "position startpos moves e2e4 e7e5"
    for length in (32768, 131073):
        lines.extend((record + " " * (length - len(record)) if extended else record, "isready"))
        history.append(3)
    lines.extend(("unrecognized " + "x" * 1048576 if extended else "unrecognized", "isready"))
    history.append(3)
    lines.extend(("position startpos moves e2e4 e7e5 g1f3", "isready"))
    history.append(4)
    # No final LF: both public input paths must process the last isready at EOF.
    return "\n".join(lines).encode("ascii"), history


def _compiler(compiler, output):
    command = list(compiler)
    command[command.index("-o") + 1] = output
    return command


def check(source, *, family, variant, compiler, output):
    if not sys.platform.startswith("linux"):
        raise ValueError("this qualification is Linux-only")
    output.mkdir(parents=False, exist_ok=False)
    candidate, proof = c_line.transform_source(source, family=family, variant=variant)
    if c_line.restore_source(candidate, proof) != source:
        raise AssertionError("line input full inverse differs")
    (output / "source.c").write_bytes(candidate)
    (output / "source-proof.json").write_text(json.dumps(proof, indent=2) + "\n")
    report = {"schema": "rove4k.tcec-c-line-native.v1", "family": family, "variant": variant,
              "input": c_line.pin(source), "candidate": c_line.pin(candidate), "source_proof": proof,
              "compiler": compiler, "affinity": sorted(os.sched_getaffinity(0)), "commands": {},
              "tools": {"c_line": c_line.pin(Path(c_line.__file__).read_bytes()),
                        "check_c_line": c_line.pin(Path(__file__).read_bytes()),
                        "check_c_input": c_line.pin(Path(input_check.__file__).read_bytes())},
              "scope": "public parser and libc error/EOF contract; no GO, strength, or all-core claim"}
    compiler, _ = c_input.compiler_for(candidate, family=family, original=compiler)
    native_pins = []
    for index in (1, 2):
        name = f"native{index}"
        _, report["commands"][name] = input_check._run(_compiler(compiler, name),
            directory=output, stdin=candidate, label=name + ".compile")
        native_pins.append(c_line.pin((output / name).read_bytes()))
    if native_pins[0] != native_pins[1]:
        raise AssertionError("raw shipping source native2 differs")
    assertion = proof["required_target_type_assertion"]
    if assertion:
        qualified = candidate + assertion.encode("ascii")
        name = "type-qualified"
        argv = _compiler(compiler, name) + ["-Werror=incompatible-pointer-types", "-Werror=implicit-function-declaration"]
        _, report["commands"][name] = input_check._run(argv, directory=output,
            stdin=qualified, label=name + ".compile")
        if c_line.pin((output / name).read_bytes()) != native_pins[0]:
            raise AssertionError("type-qualified native differs from raw shipping source")
    report["native2"] = native_pins[0]
    report["target_pointer_type_qualified"] = True
    smoke, report["commands"]["native_smoke"] = input_check._run(["./native1"], directory=output,
        stdin=b"uci\nisready\nquit\n", label="native.smoke")
    if smoke != b"uciok\nreadyok\n":
        raise AssertionError("normal native UCI smoke differs")
    results = []
    environment = dict(os.environ, ASAN_OPTIONS="detect_leaks=0:halt_on_error=1", UBSAN_OPTIONS="halt_on_error=1")
    environment.pop("RV_LINE_FAIL", None)
    for label, data, extended in (("control", source, False), ("candidate", candidate, True)):
        probe = _instrument(data, family, assertion if label == "candidate" else None)
        (output / f"{label}.probe.c").write_bytes(probe)
        argv = _compiler(compiler, label + ".probe") + ["-O1", "-g0", "-fsanitize=address,undefined",
            "-fno-omit-frame-pointer", "-Wl,--wrap=getline", "-Werror=incompatible-pointer-types",
            "-Werror=implicit-function-declaration"]
        _, report["commands"][label + "_probe_compile"] = input_check._run(argv, directory=output,
            stdin=probe, label=label + ".probe.compile")
        campaign, expected_history = _campaign(extended)
        (output / f"{label}.input").write_bytes(campaign)
        stdout, report["commands"][label + "_probe_run"] = input_check._run(["./" + label + ".probe"],
            directory=output, stdin=campaign, label=label + ".probe.run", env=environment)
        states = [line for line in stdout.splitlines() if line.startswith(b"P ")]
        if len(states) != len(expected_history) or [int(s.split(b" ", 2)[1]) for s in states] != expected_history:
            raise AssertionError("public main did not consume every legal replay/long line")
        results.append(stdout)
    if results[0] != results[1]:
        raise AssertionError("full public-parser Board/history projection differs")
    report["public_projection"] = c_line.pin(results[0])
    report["ready_states"] = len(expected_history)
    report["valid_equal"] = True
    report["largest_candidate_line"] = 1048589
    report["sanitizer_leak_detection"] = "disabled: selected policy intentionally owns allocations until process exit"
    report["failure_injections"] = {}
    for mode in ("N", "P", "E", "A"):
        output_bytes, record = input_check._run(["./candidate.probe"], directory=output,
            stdin=b"uci\nisready\n", label="failure." + mode,
            env=dict(environment, RV_LINE_FAIL=mode))
        expected = b"uciok\n" if mode == "A" else b""
        if output_bytes != expected:
            raise AssertionError("failed getline contents were consumed")
        report["failure_injections"][mode] = record
    report["failure_scope"] = "injected getline ENOMEM/EIO return -1 with NULL/poisoned contents, not host exhaustion"
    report["owned_processes_after_return"] = 0
    (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--family", choices=tuple(c_line.PROFILES), required=True)
    parser.add_argument("--variant", choices=c_line.VARIANTS, required=True)
    parser.add_argument("--compiler-json", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = check(args.source.read_bytes(), family=args.family, variant=args.variant,
                   compiler=json.loads(args.compiler_json), output=args.output)
    print(json.dumps({key: report[key] for key in ("family", "variant", "native2", "valid_equal", "ready_states")}))


if __name__ == "__main__":
    main()
