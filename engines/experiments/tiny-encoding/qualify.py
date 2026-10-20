#!/usr/bin/env python3
"""Pin an actual restored native image and the unchanged bootstrap skeleton."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location("encoding_campaign", HERE / "campaign.py")
campaign = importlib.util.module_from_spec(spec)
spec.loader.exec_module(campaign)
sys.path.insert(0, str(ROOT / "engines/tests"))
from verify import Engine


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--wrapper", type=Path,
                        help="qualify a recompressed XZ wrapper with exactly the selected bootstrap bytes")
    parser.add_argument("--expected-wrapper-sha256")
    args = parser.parse_args()
    if bool(args.wrapper) != bool(args.expected_wrapper_sha256):
        parser.error("--wrapper and --expected-wrapper-sha256 are required together")
    if not args.out.is_absolute() or args.out.exists() or ROOT in args.out.parents:
        parser.error("new absolute external output required")
    args.out.mkdir(parents=True)
    report = json.loads(args.report.read_text())
    chosen = report["selected"]
    artifact = chosen["minimum"]
    path = Path(artifact["path"])
    assert campaign.sha(path.read_bytes()) == artifact["sha256"]
    directory = path.parents[2]
    source = (directory / "main.c").read_bytes()
    script = (directory / "bootstrap.py").read_bytes()
    assert campaign.sha(source) == chosen["source_sha256"]
    assert campaign.value(campaign.argument(script, "p", "communicate")) == source
    assert list(campaign.value(campaign.argument(script, "subprocess", "Popen"))) == chosen["command"]
    if args.wrapper:
        recompress = campaign.module("qualified_xz_recipe", HERE / "recompress.py")
        wrapped = args.wrapper.read_bytes()
        assert campaign.sha(wrapped) == args.expected_wrapper_sha256
        original_prefix, _, _ = recompress.split_wrapper(path.read_bytes())
        new_prefix, _, decoded = recompress.split_wrapper(wrapped)
        assert new_prefix == original_prefix and decoded == script
        path = args.wrapper
        artifact = {"sha256": args.expected_wrapper_sha256}
    producer = campaign.module("qualified_frozen_stream", args.report.parent / "frozen/pack_stream.py")
    original = (args.report.parent / "frozen/main.c").read_bytes()
    baseline_command = report["compiler_stdin_classes"]["unstripped"]["command"]
    baseline, _ = producer.bootstrap(original, baseline_command)
    def skeleton(body):
        body = campaign.replace_argument(body, "p", "communicate", "b'SOURCE'")
        return campaign.replace_argument(body, "subprocess", "Popen", "['COMMAND']")
    assert skeleton(script) == skeleton(baseline)
    engine_spec = {"id": "encoded-actual", "command": [str(path)], "profile": "shipping", "workers": 2,
                   "startup_threads": 3, "startup_timeout": 60}
    engine = Engine(engine_spec, args.out, "actual", 10)
    try:
        engine.initialize()
        engine.assert_threads_stable()
        proc = Path("/proc") / str(engine.process.pid)
        image = (proc / "exe").read_bytes()
        expected = report["compiler_stdin_classes"][chosen["identity_class"]]["native_sha256"]
        assert campaign.sha(image) == expected
        executable = os.readlink(proc / "exe")
        assert executable.endswith(" (deleted)")
        assert not Path(executable.removesuffix(" (deleted)")).parent.exists()
        assert not (proc / "task" / str(engine.process.pid) / "children").read_text().strip()
        (args.out / "actual-native").write_bytes(image)
        needed = subprocess.check_output(["readelf", "-d", str(args.out / "actual-native")], text=True)
        symbols = subprocess.check_output(["readelf", "--dyn-syms", "--wide", str(args.out / "actual-native")], text=True)
        result = {"passed": True, "case": chosen["case"], "artifact_sha256": artifact["sha256"],
                  "actual_restored_native_sha256": campaign.sha(image), "native_identity_class": chosen["identity_class"],
                  "native_bytes": len(image), "startup_threads": len(list((proc / "task").iterdir())),
                  "bootstrap_skeleton_unchanged": True, "exact_C_bytes_and_compiler_argv": True,
                  "recompressed_wrapper": bool(args.wrapper),
                  "native_replaced_wrapper": True, "temp_removed_before_engine_input": True,
                  "glibc": subprocess.check_output(["getconf", "GNU_LIBC_VERSION"], text=True).strip(),
                  "needed": [line.strip() for line in needed.splitlines() if "NEEDED" in line],
                  "pthread_symbols": [line.strip() for line in symbols.splitlines() if "pthread_create" in line or "pthread_join" in line]}
        engine.close()
        (args.out / "identity.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result))
    finally:
        if engine.process.poll() is None:
            engine.terminate()


if __name__ == "__main__":
    main()
