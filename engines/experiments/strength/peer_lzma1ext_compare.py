"""Compare two temporary exact c4ke builds with LZMA1EXT, emitting JSON only.

No external source or compressed engine is copied into the receipt. The
caller owns the temporary producer tree and the separately built helpers.
This comparison grants no runtime or league qualification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import lzma
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from . import peer_lzma1ext_trial as trial, registry
except ImportError:
    import peer_lzma1ext_trial as trial
    import registry

EXPECTED_REVISION = "22e318f59b3a9eed1d2b8161da832222d4a51033"
TT_BYTES = 192 << 30
PINNED_DEB_VERSION = "5.6.1+really5.4.5-1ubuntu0.4"


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _read(path, maximum):
    with Path(path).open("rb") as stream:
        data = stream.read(maximum + 1)
    if len(data) > maximum:
        raise ValueError("trial input exceeds its size bound")
    return data


def compare(root, helper1, helper2, xz):
    root = Path(root).resolve(strict=True)
    receipt_data = _read(root / "peer-exact.json", 1 << 20)
    receipt = json.loads(receipt_data)
    observation = registry.inspect_exact_peer_proposal(root / "peer-exact.json", _sha(receipt_data))
    if (not observation["source_snapshot_inverse_verified"]
            or not observation["retained_source_whole_consistent"]
            or observation["eligible_for_diagnostic"]
            or observation["eligible_for_scored_league"]):
        raise ValueError("baseline proposal scope differs")
    if (receipt.get("complete") is not True or receipt.get("reproducible") is not True
            or receipt.get("peer") != "c4ke" or receipt.get("revision") != EXPECTED_REVISION
            or receipt.get("source_variant") != "edit-castle-phalanx-v1"
            or receipt.get("launcher_variant") != "gnu-tail-v1"
            or receipt.get("codec_search", {}).get("name") != "extended"
            or receipt.get("resources", {}).get("workers") != 192
            or receipt.get("resources", {}).get("tt_bytes") != TT_BYTES
            or len(receipt.get("attempts", [])) != 2):
        raise ValueError("baseline is not the exact pinned P192 phalanx experiment")

    output = []
    for index, (attempt, helper) in enumerate(zip(receipt["attempts"], (helper1, helper2)), 1):
        attempt_root = (root / ("attempt-" + str(index))).resolve(strict=True)
        source = _read(attempt_root / "main.cpp", trial.INPUT_LIMIT)
        whole_path = (attempt_root / "c4ke-tcec").resolve(strict=True)
        if Path(attempt["whole"]["path"]).resolve(strict=True) != whole_path:
            raise ValueError("baseline whole path does not name the retained attempt")
        whole = _read(whole_path, 2 * trial.INPUT_LIMIT + 8192)
        header_bytes = attempt["header"]["bytes"]
        if type(header_bytes) is not int or not 0 < header_bytes < len(whole):
            raise ValueError("invalid baseline header size")
        header, baseline_payload = whole[:header_bytes], whole[header_bytes:]
        if ({"bytes": len(source), "sha256": _sha(source)} != attempt["source"]
                or _sha(whole) != attempt["whole"]["sha256"]
                or len(whole) != attempt["whole"]["bytes"]
                or _sha(header) != attempt["header"]["sha256"]):
            raise ValueError("baseline source, whole or launcher pin differs")
        try:
            dec = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE, memlimit=trial.DECODER_LIMIT)
            restored = dec.decompress(baseline_payload, max_length=len(source) + 1)
        except lzma.LZMAError as error:
            raise ValueError("baseline LZMA stream rejected") from error
        if restored != source or not dec.eof or dec.unused_data or len(baseline_payload) < 13:
            raise ValueError("baseline payload differs from emitted source")
        prop = baseline_payload[0]
        lc, rest = prop % 9, prop // 9
        lp, pb = rest % 5, rest // 5
        if (lc, lp, pb) != (2, 0, 0):
            raise ValueError("baseline is not the extended search position profile")
        selected = attempt["selected_codec"]
        dict_size = int.from_bytes(baseline_payload[1:5], "little")
        payload, evidence = trial.encode_verified(
            source, helper=helper, xz=xz, lc=lc, lp=lp, pb=pb,
            mf=selected["mf"], nice=selected["nice_len"], dict_size=dict_size, depth=0)
        if (evidence["liblzma_header"] != "5.4.5" or evidence["liblzma_runtime"] != "5.4.5"
                or not evidence["xz_version"].startswith("xz (XZ Utils) 5.4.5")):
            raise ValueError("liblzma header, runtime or xz does not match the pinned version")
        candidate = header + payload
        output.append({"source": source, "header": header, "baseline": whole,
                       "payload": payload, "candidate": candidate, "evidence": evidence})

    first, second = output
    if any(first[key] != second[key] for key in ("source", "header", "baseline", "payload", "candidate")):
        raise ValueError("independent retained attempts or trial payloads differ")
    return {
        "format": "peer-lzma1ext-comparison-v1",
        "scope": "build-only size comparison; no engine execution or league admission",
        "peer": "c4ke", "revision": EXPECTED_REVISION,
        "source_variant": "edit-castle-phalanx-v1", "launcher_variant": "gnu-tail-v1",
        "baseline_receipt_sha256": _sha(receipt_data),
        "source": {"bytes": len(first["source"]), "sha256": _sha(first["source"])},
        "launcher": {"bytes": len(first["header"]), "sha256": _sha(first["header"])},
        "baseline_whole": {"bytes": len(first["baseline"]), "sha256": _sha(first["baseline"])},
        "trial_whole": {"bytes": len(first["candidate"]), "sha256": _sha(first["candidate"])},
        "delta_bytes": len(first["candidate"]) - len(first["baseline"]),
        "size_within_4096": len(first["candidate"]) <= 4096,
        "same_source_header_and_whole_verified": True,
        "two_retained_attempts_trial_bytes_equal": True,
        "trial_invocations": [item["evidence"] for item in output],
        "emitted_tt_semantics_verified": False,
        "runtime_qualified": False,
        "league_qualified": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--producer-root", required=True)
    parser.add_argument("--helper-1", required=True)
    parser.add_argument("--helper-2", required=True)
    parser.add_argument("--xz", required=True)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--toolchain-json", required=True)
    args = parser.parse_args()
    result = compare(args.producer_root, args.helper_1, args.helper_2, args.xz)
    toolchain = json.loads(_read(args.toolchain_json, 65536))
    expected_packages = {name: PINNED_DEB_VERSION for name in ("liblzma5", "liblzma-dev", "xz-utils")}
    if (toolchain.get("packages") != expected_packages
            or not all(isinstance(toolchain.get(name), str) and toolchain[name]
                       for name in ("cc_version", "cxx_version", "python_version", "helper_source_sha256"))
            or any(item["helper_source_sha256"] != toolchain["helper_source_sha256"]
                   for item in result["trial_invocations"])):
        raise ValueError("toolchain evidence does not match the pinned trial")
    result["toolchain"] = toolchain
    payload = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode()
    with Path(args.receipt).open("xb") as output:
        output.write(payload)
    print(json.dumps({"trial_bytes": result["trial_whole"]["bytes"],
                      "baseline_bytes": result["baseline_whole"]["bytes"],
                      "within_4096": result["size_within_4096"],
                      "league_qualified": False}, sort_keys=True))
    return 0 if result["size_within_4096"] else 1


if __name__ == "__main__":
    sys.exit(main())
