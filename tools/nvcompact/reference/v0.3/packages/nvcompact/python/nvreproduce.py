#!/usr/bin/env python3
"""Fresh-process replay of one nvenvelope recipe, including source derivation.

Run this separately from the search. Reports name immutable original bytes,
source transformation policy, exact codec recipe and all Python module hashes.
No new search, fallback recipe, or automatic repair is allowed on replay failure.
"""
import argparse
import json
from pathlib import Path
import sys

import nvenvelope as env


def reproduce(summary_path: Path, output: Path, selection="smallest", *, uci=False,
              oracle_path=None, uci_config=None):
    summary_path = summary_path.resolve(strict=True)
    old = json.loads(summary_path.read_text())
    manifest = old["manifest"]
    for name, expected in old["module_sha256"].items():
        if env.sha((Path(__file__).parent/name).read_bytes()) != expected:
            raise ValueError("replay module differs from recorded tool: " + name)
    record = old["winner"] if selection == "smallest" else old.get("accepted")
    if not record:
        raise ValueError("search has no accepted candidate")
    original = (summary_path.parent/"original").read_bytes()
    if env.sha(original) != old["original_sha256"]:
        raise ValueError("original artifact changed")
    output.mkdir(parents=True, exist_ok=False)
    report = {"format": "nvcompact.envelope-replay.v1", "selection": selection,
              "expected_sha256": record["sha256"], "source_derived_again": False,
              "semantic_scope": record["equivalence"]}
    payload = None
    header = None
    variants = [{"id": "raw", "data": original}]
    if manifest.get("envelope"):
        header, payload = env.extract(original, manifest["envelope"])
        variants = [{"id": "raw", "data": payload}]
        if record["variant"] != "raw":
            from nvnotation import generate_variants
            options = manifest.get("notation", {})
            variants = generate_variants(payload, language=manifest["language"], target=options.get("target"),
                                         token_contract=options.get("token_contract", "opaque"),
                                         compact=options.get("compact", True), max_variants=13)
            changed = next(item["data"] for item in variants if item["id"] == record["variant"])
            report["source_derived_again"] = True
            if manifest.get("compile_argv"):
                work = output/"native-equivalence"
                work.mkdir()
                baseline = env.native_fingerprint(payload, manifest["compile_argv"], work)
                candidate = env.native_fingerprint(changed, manifest["compile_argv"], work)
                if not baseline.get("sha256") or baseline.get("sha256") != candidate.get("sha256"):
                    raise ValueError("source replay no longer compiles to byte-identical native output")
                report["native_equivalence"] = {"baseline": baseline, "candidate": candidate}
    if record["id"] == "identity":
        data = original
    elif record["id"] == "submitted-payload":
        data = env.best_header(header, manifest["envelope"]["decoder"], record["recipe"]["decoder"])+original[len(header):]
    elif record["recipe"]["format"] == "native_pack":
        from nvpack import pack_by_id
        data = pack_by_id(original, target="x86_64-unknown-linux-gnu", pack_id=record["recipe"]["pack_id"])["data"]
    else:
        payload = next(item["data"] for item in variants if item["id"] == record["variant"])
        if record.get("payload_sha256") and env.sha(payload) != record["payload_sha256"]:
            raise ValueError("derived payload changed")
        data = env.best_header(header, manifest["envelope"]["decoder"], env.decoder_for(record["recipe"]))+env.compress(payload, record["recipe"])
    if len(data) != record["bytes"] or env.sha(data) != record["sha256"]:
        raise ValueError("exact final-file replay failed; fix the cause, do not whitelist this result")
    binary = output/"reproduced"
    binary.write_bytes(data)
    binary.chmod(0o755)
    report.update(bytes=len(data), sha256=env.sha(data), byte_replay="pass")
    if record["id"] != "identity":
        report["payload_check"] = env.check_deployed_payload(binary, record, manifest, original, variants)
    if uci:
        from nvuci import verify_engine
        if manifest.get("runtime_blocked"):
            report["uci"] = {"verdict": "blocked", "reason": manifest["runtime_blocked"]}
        else:
            report["uci"] = verify_engine([str(binary.resolve())], {"oracle_path": oracle_path, **(uci_config or {}), "artifact_path": str(binary.resolve())})
    env.write_json(output/"replay.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--selection", choices=("smallest", "accepted"), default="smallest")
    parser.add_argument("--uci", action="store_true")
    parser.add_argument("--oracle-path")
    parser.add_argument("--uci-config", type=Path)
    args = parser.parse_args()
    try:
        report = reproduce(args.summary, args.output.resolve(), args.selection, uci=args.uci,
                           oracle_path=args.oracle_path,
                           uci_config=json.loads(args.uci_config.read_text()) if args.uci_config else None)
        print(json.dumps({k:v for k,v in report.items() if k not in ("native_equivalence", "uci")}, indent=2))
        if args.uci and report["uci"]["verdict"] != "pass":
            return 2
        return 0
    except (ValueError, OSError, StopIteration) as exc:
        print("nvreproduce: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
