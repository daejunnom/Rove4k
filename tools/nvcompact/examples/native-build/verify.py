"""Finite external oracle for the native-build example's documented domain."""
import argparse
import json
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("binary")
parser.add_argument("--quick", action="store_true")
args = parser.parse_args()
values = list(range(32 if args.quick else 256))
payload = "".join(f"{value}\n" for value in values).encode()
expected = "".join(f"{value ** 2}\n" for value in values).encode()
result = subprocess.run([args.binary], input=payload, capture_output=True, timeout=5)
if (result.returncode, result.stdout, result.stderr) != (0, expected, b""):
    raise SystemExit("native example violated its finite input/output contract")
for payload in (b"256\n", b"x\n"):
    result = subprocess.run([args.binary], input=payload, capture_output=True, timeout=5)
    if (result.returncode, result.stdout, result.stderr) != (64, b"", b""):
        raise SystemExit("native example failed its invalid-input contract")
print(json.dumps({"status": "passed", "integer_inputs": len(values), "invalid_inputs": 2}))
