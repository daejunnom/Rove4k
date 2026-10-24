"""Opt-in native contract check of a pinned, real compact source.

Run in Linux with a CPU affinity assigned by the experiment coordinator.  This
compiles old/new sources as independent ASan/UBSan parser probes; their native
bytes are diagnostic probes, never submission artifacts.  No expected source
pin or acceptance result is refreshed automatically.  All outputs go to a new
explicit directory outside the repository.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

import c_input


# Kept independently of the transformation templates: these describe the real
# compact programs' already-existing startup and callable parser entry points.
_PROBES = {
    "A": ("N", "B", "q", "F", "z", "y"),
    "B": ("qq", "B", "k", "ql", "R", "G"),
    "C": ("qq", "B", "q", "ql", "z", "y"),
    "E": ("qq", "B", "q", "ql", "z", "y"),
    "F2": ("B", "qk", "o", "Z", "z", "qm"),
    "F8": ("B", "qk", "o", "Z", "z", "qm"),
}
_VALID_NUMBERS = ("0", "00", "1", "000123", "86400000", "9223372036854775807", "0" * 128 + "9223372036854775807")


def _identity(data: bytes) -> dict:
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


def _records() -> list[str]:
    records = [
        "position startpos",
        "position startpos moves",
        "\tposition\tstartpos\tmoves\te2e4  e7e5\tg1f3\r",
        "position startpos moves e2e4 a7a6 e4e5 d7d5 e5d6",  # white EP
        "position startpos moves a2a3 e7e5 a3a4 e5e4 d2d4 e4d3",  # black EP
        "position startpos moves g1f3 g8f6 e2e4 e7e5 f1e2 f8e7 e1g1 e8g8",
        "position startpos moves d2d4 d7d5 b1c3 b8c6 c1f4 c8f5 d1d2 d8d7 e1c1 e8c8",
    ]
    for white in "nbrq":
        for black in "nbrq":
            records.append("position startpos moves a2a4 h7h5 a4a5 h5h4 a5a6 h4h3 a6b7 h3g2 "
                           f"b7a8{white} g2h1{black}")
    # Legal reversible knight moves exercise the exact history boundary on a
    # >20KB line, independently of repeated-position/draw search adjudication.
    cycle = ["g1f3", "g8f6", "f3g1", "f6g8"]
    longest = "position startpos moves " + " ".join((cycle * 1024)[:4095])
    records.extend((longest, longest + " " * (32767 - len(longest))))
    return records


def _probe_source(source: bytes, family: str) -> bytes:
    table, initialize, start, root, position, number = _PROBES[family]
    numeric_literals = ",".join(json.dumps(n) for n in _VALID_NUMBERS)
    harness = rf'''
#undef main
static void rv_probe_emit(void){{
  const unsigned char *rv_bytes=(const unsigned char*)&{root};
  printf("P %d ",(int)qh);
  for(size_t rv_i=0;rv_i<sizeof {root};rv_i++)printf("%02x",rv_bytes[rv_i]);
  for(int rv_i=0;rv_i<qh;rv_i++)printf(" %016llx",(unsigned long long)qg[rv_i]);
  putchar('\n');
}}
int main(void){{
  {table}=calloc(1<<18,sizeof*{table});if(!{table})return 2;
  {initialize}();{start}(&{root});qg[0]={root}.h;qh=1;
  const char*rv_numbers[]={{{numeric_literals}}};
  printf("N %llu",(unsigned long long){number}(NULL));
  for(size_t rv_i=0;rv_i<sizeof rv_numbers/sizeof*rv_numbers;rv_i++)
    printf(" %llu",(unsigned long long){number}(rv_numbers[rv_i]));
  putchar('\n');
  char rv_line[32768];
  while(fgets(rv_line,sizeof rv_line,stdin)){{
    if(!strchr(rv_line,'\n')){{
      int rv_end=getchar();if(rv_end!=EOF&&rv_end!='\n')return 93;
    }}
    char*rv_first=strtok(rv_line," \t\r\n");
    if(!rv_first||strcmp(rv_first,"position"))return 90;
    {position}();if(qh<1||qh>4096)return 91;rv_probe_emit();
  }}
  puts("MALFORMED");
  const char*rv_badnumbers[]={{"-1","9223372036854775808","18446744073709551616","12x","","x"}};
  for(size_t rv_i=0;rv_i<sizeof rv_badnumbers/sizeof*rv_badnumbers;rv_i++)
    printf("%llu\n",(unsigned long long){number}(rv_badnumbers[rv_i]));
  char rv_badpositions[][96]={{"position","position fen malformed","position startpos bogus",
    "position startpos moves e2e5","position startpos moves e2e4 illegal"}};
  for(size_t rv_i=0;rv_i<sizeof rv_badpositions/sizeof*rv_badpositions;rv_i++){{
    strtok(rv_badpositions[rv_i]," \t\r\n");{position}();if(qh<1||qh>4096)return 92;
  }}
  char rv_excess[32768]="position startpos moves ";size_t rv_used=strlen(rv_excess);
  const char*rv_cycle[]={{"g1f3","g8f6","f3g1","f6g8"}};
  for(int rv_i=0;rv_i<4096;rv_i++){{
    memcpy(rv_excess+rv_used,rv_cycle[rv_i&3],4);rv_used+=4;rv_excess[rv_used++]=' ';
  }}
  rv_excess[rv_used]=0;strtok(rv_excess," \t\r\n");{position}();if(qh<1||qh>4096)return 94;
  free({table});return 0;
}}
'''
    return b"#define main rv_original_main\n" + source + harness.encode("ascii")


def _run(command: list[str], *, directory: Path, stdin: bytes, label: str, env=None) -> tuple[bytes, dict]:
    completed = subprocess.run(command, input=stdin, capture_output=True, cwd=directory, timeout=60, env=env)
    stdout = completed.stdout
    (directory / f"{label}.stdout").write_bytes(stdout)
    (directory / f"{label}.stderr").write_bytes(completed.stderr)
    record = {"argv": command, "exit_code": completed.returncode,
              "stdout": _identity(stdout), "stderr": _identity(completed.stderr)}
    if completed.returncode:
        raise RuntimeError(f"{label} exited {completed.returncode}; preserved diagnostic outputs in {directory}")
    return stdout, record


def check(source: bytes, *, family: str, output: Path) -> dict:
    if not sys.platform.startswith("linux"):
        raise ValueError("this native diagnostic is Linux-only")
    output.mkdir(parents=False, exist_ok=False)
    candidate, proof = c_input.transform_source(source, family=family)
    if c_input.restore_source(candidate, proof) != source:
        raise AssertionError("full inverse mismatch")
    # Reject tampering with any protected, untouched byte rather than accepting
    # a proof that happens to reconstruct only the two edited functions.
    try:
        c_input.restore_source(candidate + b"\n", proof)
    except ValueError:
        pass
    else:
        raise AssertionError("altered complete output was admitted")
    records = _records()
    stdin = ("\n".join(records) + "\n").encode("ascii")
    (output / "valid-input.txt").write_bytes(stdin)
    report = {"schema": "rove4k.tcec-c-input-native.v1", "family": family,
              "input": _identity(source), "candidate": _identity(candidate), "source_proof": proof,
              "tools": {"transform": _identity(Path(c_input.__file__).read_bytes()),
                        "checker": _identity(Path(__file__).read_bytes())},
              "affinity": sorted(os.sched_getaffinity(0)), "valid_records": len(records),
              "longest_record_bytes": max(len(r) for r in records), "commands": {},
              "scope": "parser state/history and numeric values; no GO/thread/native-size claim"}
    projections = []
    for label, data in (("control", source), ("candidate", candidate)):
        probe = _probe_source(data, family)
        (output / f"{label}.probe.c").write_bytes(probe)
        argv = ["cc", "-std=c11", "-O1", "-g0", "-pthread", "-fsanitize=address,undefined",
                "-fno-omit-frame-pointer", "-x", "c", "-", "-o", f"{label}.probe"]
        _, report["commands"][label + "_compile"] = _run(argv, directory=output, stdin=probe, label=label + ".compile")
        environment = dict(os.environ, ASAN_OPTIONS="detect_leaks=1:halt_on_error=1", UBSAN_OPTIONS="halt_on_error=1")
        stdout, report["commands"][label + "_run"] = _run([f"./{label}.probe"], directory=output,
            stdin=stdin, label=label + ".run", env=environment)
        valid, separator, _ = stdout.partition(b"MALFORMED\n")
        if not separator:
            raise AssertionError("probe did not finish valid-input domain")
        lines = valid.decode("ascii").splitlines()
        expected_numbers = "N " + " ".join(str(n) for n in (0, *(int(n) for n in _VALID_NUMBERS)))
        if len(lines) != len(records) + 1 or lines[0] != expected_numbers:
            raise AssertionError("numeric domain or output count mismatch")
        for text, state in zip(records, lines[1:]):
            tokens = text.split()
            expected_history = 1 + (len(tokens) - 3 if len(tokens) > 2 else 0)
            if int(state.split(" ", 2)[1]) != expected_history:
                raise AssertionError(f"legal replay did not consume every move: {text[:120]}")
        projections.append(valid)
    if projections[0] != projections[1]:
        raise AssertionError("full Board bytes or history differ on valid records")
    report["valid_projection"] = _identity(projections[0])
    report["valid_equal"] = True
    report["malformed_bounded_sanitizer_runs"] = 2
    report["owned_processes_after_return"] = 0
    (output / "result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", choices=tuple(_PROBES), required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.read_bytes()
    if sha256(source).hexdigest() != args.expected_sha256:
        raise SystemExit("source pin mismatch; no probe compiled")
    result = check(source, family=args.family, output=args.output)
    print(json.dumps({"family": args.family, "valid_equal": result["valid_equal"],
                      "records": result["valid_records"], "input": result["input"],
                      "candidate": result["candidate"], "output": str(args.output)}))


if __name__ == "__main__":
    main()
