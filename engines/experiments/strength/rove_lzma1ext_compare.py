"""Compare Rove source-JIT candidates with LZMA1EXT; build evidence only.

The original engine and the replacement stream remain in the caller's
temporary directory or process memory. This produces a numeric/hash receipt,
not a selected artifact, runtime approval, or tournament qualification.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import lzma
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
import peer_lzma1ext_trial as trial

ROOT = Path(__file__).resolve().parents[3]
VARIANTS = {"A": "square-atomic", "B": "league-atomic", "C": "square-ep-atomic",
            "E": "ep-atomic", "F": "atomic-assignment"}
PROFILES = ("test-p16", "test-p192")
FINDERS = {"BT2": lzma.MF_BT2, "BT4": lzma.MF_BT4, "HC4": lzma.MF_HC4}


def pin(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def read_bounded(path, limit):
    with Path(path).open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError("comparison input exceeds limit")
    return data


def admit(manifest, build):
    path = ROOT / "engines/experiments/tcec-next/profile_verify.py"
    spec = importlib.util.spec_from_file_location("rove_lzma1ext_profile_verify", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.admit_c_build(manifest, build)


def compare(build, family, profile, variant, helper1, helper2, xz):
    if VARIANTS.get(family) != variant or profile not in PROFILES:
        raise ValueError("unsupported Rove comparison identity")
    build = Path(build).resolve(strict=True)
    raw = read_bounded(build / "build.json", 8 << 20)
    manifest = json.loads(raw)
    admitted = admit(manifest, build)
    if (manifest.get("complete") is not True or manifest.get("reproducible") is not True
            or manifest.get("family") != family or manifest.get("resources", {}).get("id") != profile
            or (admitted.family, admitted.profile_id, admitted.representation) != (family, profile, "source-jit")):
        raise ValueError("baseline does not match admitted family and profile")
    if family == "B":
        if (manifest.get("post_spelling", {}).get("selection") != "league-atomic"
                or manifest.get("post_profile", {}).get("variant") != "tcec-final-lf"):
            raise ValueError("baseline is not the B league-atomic candidate")
    elif manifest.get("post_league", {}).get("variant") != variant:
        raise ValueError("baseline does not match requested league variant")
    compression = manifest.get("compression", {})
    if (compression.get("format"), compression.get("filter"), compression.get("check")) != ("lzma-alone", "LZMA1", "NONE"):
        raise ValueError("baseline codec is not LZMA1 ALONE")
    if compression.get("mf") not in FINDERS:
        raise ValueError("baseline match finder is unsupported")
    names = ("main.c", "header.sh", "payload.lzma", "x")
    rows = []
    for attempt in ("first", "repeat"):
        data = {name: read_bounded(build / attempt / name, 2 * trial.INPUT_LIMIT + 8192) for name in names}
        for name in names:
            if data[name] != read_bounded(build / name, 2 * trial.INPUT_LIMIT + 8192):
                raise ValueError("baseline attempt and public artifact differ")
        if len(data["main.c"]) > trial.INPUT_LIMIT or data["x"] != data["header.sh"] + data["payload.lzma"]:
            raise ValueError("baseline source or package composition differs")
        dec = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE, memlimit=trial.DECODER_LIMIT)
        if (dec.decompress(data["payload.lzma"], max_length=len(data["main.c"]) + 1) != data["main.c"]
                or not dec.eof or dec.unused_data):
            raise ValueError("baseline payload does not exactly restore source")
        rows.append(data)
    if rows[0] != rows[1]:
        raise ValueError("independent baseline attempts differ")
    source, header, baseline = rows[0]["main.c"], rows[0]["header.sh"], rows[0]["x"]
    kwargs = {"lc": compression["lc"], "lp": compression["lp"], "pb": compression["pb"],
              "mf": FINDERS[compression["mf"]], "nice": compression["nice_len"],
              "dict_size": compression["dictionary_bytes"], "depth": 0}
    encoded = [trial.encode_verified(source, helper=helper, xz=xz, **kwargs)
               for helper in (helper1, helper2)]
    if encoded[0][0] != encoded[1][0]:
        raise ValueError("independent helper outputs differ")
    for _, receipt in encoded:
        if (receipt["liblzma_header"] != "5.4.5" or receipt["liblzma_runtime"] != "5.4.5"
                or not receipt["xz_version"].startswith("xz (XZ Utils) 5.4.5")):
            raise ValueError("trial tools differ from pinned liblzma/xz version")
    candidate = header + encoded[0][0]
    return {"format": "rove-lzma1ext-comparison-v1", "family": family, "profile": profile,
            "variant": variant, "baseline_manifest": pin(raw), "source": pin(source),
            "launcher": pin(header), "baseline_whole": pin(baseline), "trial_whole": pin(candidate),
            "delta_bytes": len(candidate) - len(baseline), "size_within_4096": len(candidate) <= 4096,
            "baseline_codec": compression, "trial_invocations": [row[1] for row in encoded],
            "trial_preset": "9-extreme with manifest lc/lp/pb/mf/dictionary/nice and depth 0",
            "baseline_codec_internals_identical": False,
            "same_source_and_launcher_verified": True, "two_attempts_equal": True,
            "engine_executed": False, "runtime_qualified": False,
            "tcec_qualified": False, "league_qualified": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("build", "family", "profile", "variant", "helper-1", "helper-2", "xz", "receipt"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    result = compare(args.build, args.family, args.profile, args.variant, args.helper_1, args.helper_2, args.xz)
    with Path(args.receipt).open("xb") as output:
        output.write((json.dumps(result, sort_keys=True, indent=2) + "\n").encode())
    print(json.dumps({"family": args.family, "profile": args.profile, "variant": args.variant,
                      "baseline_bytes": result["baseline_whole"]["bytes"],
                      "trial_bytes": result["trial_whole"]["bytes"],
                      "within_4096": result["size_within_4096"], "league_qualified": False}, sort_keys=True))


if __name__ == "__main__":
    main()
