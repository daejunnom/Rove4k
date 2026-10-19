"""Independent finite oracle for program.c; accepts one native/wrapped path."""
import subprocess
import sys

expected = "".join(
    f"{n + (3 if n % 2 else -3)} {n * (n + 1) // 2} {n + n % 2} {int(n != 0)}\n"
    for n in range(16)
).encode()
result = subprocess.run([sys.argv[1]], input=b"", capture_output=True, timeout=5)
if (result.returncode, result.stdout, result.stderr) != (0, expected, b""):
    raise SystemExit("C rewrite example violated its 16-row output/exit contract")
print("passed: 16 independently computed rows, zero exit, empty stderr")
