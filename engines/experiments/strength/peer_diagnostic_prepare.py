"""Prepare one upstream peer for the owned P16/P192 functional probe.

The producer and reference are built on this host from the seed's upstream
blob-pinned source.  The resulting candidate set is an input to the existing
diagnostic path, not an engine run, scored admission, host authentication or
proof that the seed was obtained from a trusted producer.  The upstream tiny
policy can generate queen promotions only; this is not the Rove full policy.
No upstream source is written into the repository.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from . import cloud_runtime, diagnostic_candidates, peer_runtime, peers, registry
except ImportError:
    import cloud_runtime
    import diagnostic_candidates
    import peer_runtime
    import peers
    import registry


def _pin(path):
    data = cloud_runtime.ordinary(Path(path), limit=256 << 20)
    return {"path": str(path), **cloud_runtime.pin(data)}


def prepare(*, seed_root, seed_sha256, family, profile, cpu, out):
    """Generate and re-admit a peer candidate without executing its engine."""
    if sys.platform != "linux":
        raise RuntimeError("peer producer and reference require Linux")
    if family not in ("ice4", "c4ke") or profile not in ("test-p16", "test-p192"):
        raise ValueError("an ice4/c4ke P16/P192 peer is required")
    if not isinstance(seed_sha256, str) or not cloud_runtime.SHA.fullmatch(seed_sha256):
        raise ValueError("an externally pinned seed manifest SHA-256 is required")
    if type(cpu) is not int or cpu not in os.sched_getaffinity(0):
        raise ValueError("producer CPU must belong to the current affinity")
    root = diagnostic_candidates._safe_input_path(seed_root)
    if not root.is_dir():
        raise ValueError("materialized seed directory required")
    manifest_path = root / "seed.json"
    diagnostic_candidates._safe_input_path(manifest_path)
    seed = cloud_runtime.load_seed_manifest(manifest_path, seed_sha256)
    # Check every listed path before revalidate_seed opens any member. The
    # general seed transport permits a broader set of names than this task's
    # explicit protected/generated-input policy.
    for name in seed["members"]:
        diagnostic_candidates._check_path_components(root / cloud_runtime.member(name))
    cloud_runtime.revalidate_seed(seed, root)
    cloud_runtime.validate_host_source(seed)
    rows = [row for row in seed["peers"] if row.get("family") == family and row.get("profile") == profile]
    if len(rows) != 1:
        raise ValueError("exactly one matching peer source seed is required")
    row = rows[0]
    spec = peers.peer_spec(family)
    prefix = cloud_runtime.member(row["source"])
    if (row.get("repository") != spec.repository or row.get("revision") != spec.revision or
            row.get("license") != prefix + "/LICENSE"):
        raise ValueError("seed peer repository, upstream revision or license differs")
    actual = {name[len(prefix) + 1:] for name in seed["members"] if name.startswith(prefix + "/")}
    if actual != set(peers.SOURCE_BLOBS[family]):
        raise ValueError("seed peer source closure differs from the pinned upstream files")
    source_root = diagnostic_candidates._safe_input_path(root / prefix)
    # This verifies the exact pinned upstream Git blobs, including LICENSE,
    # before the producer copies and patches only resource declarations.
    peers.verify_source(family, source_root)
    output = diagnostic_candidates._safe_output_path(out)
    if not output.parent.is_dir():
        raise ValueError("peer output parent must already exist")
    output.mkdir()
    built = peers.build_resource_tiny(family, source_root, output / "peer-build", profile,
        run=lambda argv, cwd, **kw: peers.bounded_run(argv, cwd, cpu=cpu, **kw))
    build_path = Path(built["path"])
    admitted = peer_runtime.validate_build(build_path, built["sha256"])
    ref = peer_runtime.prepare_reference(build_path, output / "peer-reference",
                                         manifest_sha=built["sha256"], cpu=cpu)
    reference_path = Path(ref["path"])
    ref_record = ref["record"]
    layout = admitted["layout"]
    whole = Path(admitted["record"]["whole"]["path"])
    source = reference_path.parent / "main.cpp"
    native = Path(ref_record["native"]["path"])
    artifact = registry.Artifact(
        id=f'{family}-{profile}-{admitted["record"]["whole"]["sha256"][:8]}-{ref_record["native"]["sha256"][:8]}',
        family=family, path=whole, purpose="test", profile=profile,
        workers=layout["workers"], tt_bytes=layout["tt_bytes"], entry_bytes=layout["entry_bytes"],
        representation="source-jit", full=True, sha256=admitted["record"]["whole"]["sha256"],
        whole_bytes=admitted["record"]["whole"]["bytes"], native_sha256=ref_record["native"]["sha256"])
    candidate = {"artifact": {**artifact.identity(), "path": str(whole)}, "source": _pin(source),
                 "native": _pin(native), "evidence": {"kind": "peer-reference-v1",
                 "build": _pin(build_path), "reference": _pin(reference_path)}}
    value = {"format": "rove4k-diagnostic-candidate-set-v1", "profile": profile, "candidates": [candidate]}
    target = output / "candidate.json"
    pin = cloud_runtime.json_new(target, value)
    # Replay the existing peer build/reference and candidate checks on the
    # exact file which the functional probe will later consume.
    checked, digest = diagnostic_candidates.read_candidates(target, pin["sha256"], profile, allow_single=True)
    if len(checked) != 1 or checked[0]["artifact"].id != artifact.id or digest != pin["sha256"]:
        raise ValueError("prepared peer candidate did not replay")
    return {"format": "rove4k-peer-diagnostic-preparation-v1", "seed_sha256": seed_sha256,
            "family": family, "profile": profile, "artifact_id": artifact.id,
            "candidate": {"path": str(target), **pin}, "build": candidate["evidence"]["build"],
            "reference": candidate["evidence"]["reference"],
            "scope": "host source/whole/native preparation only; no engine execution or admission"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-root", required=True)
    parser.add_argument("--seed-sha256", required=True)
    parser.add_argument("--family", choices=("ice4", "c4ke"), required=True)
    parser.add_argument("--profile", choices=("test-p16", "test-p192"), required=True)
    parser.add_argument("--cpu", type=int, required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    result = prepare(seed_root=args.seed_root, seed_sha256=args.seed_sha256, family=args.family,
                     profile=args.profile, cpu=args.cpu, out=args.out)
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
