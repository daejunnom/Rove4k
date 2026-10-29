#!/usr/bin/env python3
"""Seven bounded XZ settings; preserve the complete launcher and decoded bytes.

This experiment does not import or edit the shared packer. It requires the
baseline to be the exact default-XZ output, repeats every compression, and uses
the external xz decoder as well as Python to prove restoration byte identity.
The selected artifact is a complete executable file, not an isolated stream.
"""
import argparse
import hashlib
import json
import lzma
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[3]
PRESET = 9 | lzma.PRESET_EXTREME
SETTINGS = [(3, 2)] + [(lc, 0) for lc in range(5)] + [(3, 1)]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def split_wrapper(data):
    offset = data.find(b"\xfd7zXZ\0")
    if offset < 0:
        raise ValueError("no XZ stream in wrapper")
    prefix, payload = data[:offset], data[offset:]
    command = re.fullmatch(
        rb'#!/bin/sh\np=\$\(tail -c\+([0-9]+) "\$0"\|xz -dc\)\|\|exit\n'
        rb'exec python3 -c "\$p" "\$0" "\$@"\n', prefix)
    if command is None or int(command[1]) != offset + 1:
        raise ValueError("unexpected complete launcher or payload offset")
    decoder = lzma.LZMADecompressor(format=lzma.FORMAT_XZ)
    decoded = decoder.decompress(payload)
    if not decoder.eof or decoder.unused_data:
        raise ValueError("one complete XZ stream required")
    if decoder.check != lzma.CHECK_CRC64:
        raise ValueError("baseline must use the original CRC64 check")
    return prefix, payload, decoded


def compressed(decoded, lc, pb):
    return lzma.compress(decoded, format=lzma.FORMAT_XZ,
                         check=lzma.CHECK_CRC64,
                         filters=[{"id": lzma.FILTER_LZMA2, "preset": PRESET,
                                   "lc": lc, "lp": 0, "pb": pb}])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-wrapper", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--expected-native-sha256", required=True,
                        help="previous actual restored image; unchanged decoded bytes permit evidence reuse")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if not args.out.is_absolute() or args.out.exists() or ROOT in args.out.parents:
        parser.error("new absolute output outside checkout required")
    data = args.baseline_wrapper.read_bytes()
    if sha(data) != args.expected_sha256:
        parser.error("baseline wrapper SHA-256 mismatch")
    if re.fullmatch(r"[a-f0-9]{64}", args.expected_native_sha256) is None:
        parser.error("expected native SHA-256 must be an exact digest")
    prefix, payload, decoded = split_wrapper(data)
    # Pin liblzma's default baseline before interpreting parameter-only changes.
    default = lzma.compress(decoded, format=lzma.FORMAT_XZ, preset=PRESET)
    if default != payload or compressed(decoded, 3, 2) != payload:
        parser.error("input does not reproduce the declared default XZ recipe")
    args.out.mkdir(parents=True)
    frozen = args.out / "frozen"
    frozen.mkdir()
    (frozen / "recompress.py").write_bytes(Path(__file__).read_bytes())
    (frozen / "baseline-wrapper").write_bytes(data)
    (frozen / "decoded-bootstrap.py").write_bytes(decoded)
    records = []
    for index, (lc, pb) in enumerate(SETTINGS):
        encoded = compressed(decoded, lc, pb)
        actual = prefix + encoded
        assert actual == prefix + compressed(decoded, lc, pb)
        restored_prefix, _, restored = split_wrapper(actual)
        assert restored_prefix == prefix and restored == decoded
        external = subprocess.run(["xz", "-dc"], input=encoded,
                                  capture_output=True, check=True)
        assert external.stdout == decoded
        path = args.out / f"{index:02d}-lc{lc}-pb{pb}" / "x"
        path.parent.mkdir()
        path.write_bytes(actual)
        path.chmod(0o755)
        record = {"case": f"lc{lc}-lp0-pb{pb}", "lc": lc, "lp": 0, "pb": pb,
                  "format": "XZ", "check": "CRC64", "preset": "9e",
                  "bytes": len(actual), "payload_bytes": len(encoded),
                  "launcher_bytes": len(prefix), "sha256": sha(actual),
                  "path": str(path), "delta_from_baseline": len(actual) - len(data),
                  "decoded_sha256": sha(decoded), "launcher_sha256": sha(prefix),
                  "decoded_exact": True, "launcher_exact": True,
                  "independent_recompression_exact": True, "external_xz_decoded_exact": True}
        records.append(record)
        print(json.dumps(record), flush=True)
    chosen = min(records, key=lambda item: (item["bytes"], item["case"]))
    manifest = {"engines": [{"id": "tiny-encoding-xz-selected", "profile": "shipping",
                             "command": [chosen["path"]], "cwd": str(Path(chosen["path"]).parent),
                             "workers": 2, "startup_threads": 3, "startup_timeout": 60,
                             "expected_program_sha256": chosen["sha256"]}]}
    (args.out / "validation-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    result = {"schema": 1, "scope": "bounded lossless XZ parameter experiment; no source or bootstrap changes",
              "producer_sha256": sha(Path(__file__).read_bytes()), "trial_limit": 7,
              "baseline": {"path": str(args.baseline_wrapper), "bytes": len(data), "sha256": sha(data),
                           "default_reproduced_exactly": True},
              "decoded_bytes": len(decoded), "decoded_sha256": sha(decoded),
              "launcher_bytes": len(prefix), "launcher_sha256": sha(prefix),
              "expected_actual_native_sha256": args.expected_native_sha256,
              "native_evidence_reuse": "same exact decoded Python+C+compiler argv; actual selected execution pending",
              "runtime_qualified": False, "trials": records, "selected": chosen,
              "over_4096_bytes": max(0, chosen["bytes"] - 4096)}
    (args.out / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"selected": chosen, "over_4096_bytes": result["over_4096_bytes"]}), flush=True)


if __name__ == "__main__":
    main()
