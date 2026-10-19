#!/usr/bin/env python3
"""NVCompact 0.2: repack explicitly described, already self-extracting files.

The shell header is an input contract, never inferred as an arbitrary shell AST.
Identity is always retained. Every compressed candidate round-trips to its
declared payload. Changed C/C++ source additionally needs byte-identical native
output with the submitted compile flags; Python needs the notation AST contract.
UCI acceptance is a separate, final-artifact gate, not an equivalence proof.
"""
from __future__ import annotations

import argparse
import bz2
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
import lzma
import os
from pathlib import Path
import platform
import re
import selectors
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time

VERSION = "0.2.0"
MAX_ARTIFACT = 4 << 20
MAX_PAYLOAD = 8 << 20
TAIL = re.compile(rb"tail -(c|n)\s*\+(\d+)")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def decode(blob: bytes, recipe: dict) -> bytes:
    kind = recipe["format"]
    if kind in ("alone", "xz", "raw"):
        fmt = {"alone": lzma.FORMAT_ALONE, "xz": lzma.FORMAT_XZ, "raw": lzma.FORMAT_RAW}[kind]
        filters = None
        if kind == "raw":
            filters = ([{"id": lzma.FILTER_X86}] if recipe.get("x86") else []) + [
                {"id": lzma.FILTER_LZMA2, "dict_size": 8 << 20}]
        dec = lzma.LZMADecompressor(format=fmt, filters=filters)
        data = dec.decompress(blob, max_length=MAX_PAYLOAD + 1)
        if len(data) > MAX_PAYLOAD or not dec.eof or dec.unused_data:
            raise ValueError("oversize, unfinished, or trailing LZMA payload")
        return data
    # These inputs are bounded, local build artifacts. Streaming caps still
    # prevent a dishonest manifest from expanding into unbounded output.
    if kind == "bzip2":
        dec = bz2.BZ2Decompressor()
        data = dec.decompress(blob, max_length=MAX_PAYLOAD + 1)
        if len(data) > MAX_PAYLOAD or not dec.eof or dec.unused_data:
            raise ValueError("invalid bzip2 payload")
        return data
    if kind == "gzip":
        import zlib
        dec = zlib.decompressobj(31)
        data = dec.decompress(blob, MAX_PAYLOAD + 1)
        if len(data) > MAX_PAYLOAD or not dec.eof or dec.unused_data:
            raise ValueError("invalid gzip payload")
        return data
    raise ValueError("unsupported payload format: " + kind)


def extract(artifact: bytes, spec: dict) -> tuple[bytes, bytes]:
    if len(artifact) > MAX_ARTIFACT:
        raise ValueError("artifact exceeds input bound")
    header = spec["header"].encode("utf-8")
    if not artifact.startswith(header) or not header.endswith(b"\n"):
        raise ValueError("exact inspected header does not match")
    matches = list(TAIL.finditer(header))
    if len(matches) != 1:
        raise ValueError("exactly one supported tail offset is required")
    match = matches[0]
    expected = len(header) + 1 if match[1] == b"c" else header.count(b"\n") + 1
    if int(match[2]) != expected:
        raise ValueError("tail offset does not match the submitted header")
    decoder = spec["decoder"].encode("ascii")
    if header.count(decoder) != 1:
        raise ValueError("decoder span is not unique")
    return header, decode(artifact[len(header):], spec["payload_codec"])


def make_header(header: bytes, old_decoder: str, new_decoder: str, style="original") -> bytes:
    """Replace only the inspected decoder span and repair the tail fixed point."""
    old, new = old_decoder.encode("ascii"), new_decoder.encode("ascii")
    if header.count(old) != 1:
        raise ValueError("ambiguous decoder")
    header = header.replace(old, new, 1)
    if style != "original":
        if style not in ("lines", "bytes"):
            raise ValueError("unknown tail spelling")
        header = TAIL.sub(b"tail -" + (b"n" if style == "lines" else b"c") + b"+0", header, count=1)
    for _ in range(12):
        match = TAIL.search(header)
        if not match:
            raise ValueError("tail offset missing")
        value = len(header) + 1 if match[1] == b"c" else header.count(b"\n") + 1
        changed = header[:match.start(2)] + str(value).encode() + header[match.end(2):]
        if changed == header:
            return header
        header = changed
    raise ValueError("tail offset did not converge")


def best_header(header: bytes, old_decoder: str, new_decoder: str) -> bytes:
    # Only this independent, uncompressed prefix is minimized greedily. Every
    # spelling extracts the identical suffix; whole payload recipes stay open.
    return min((make_header(header, old_decoder, new_decoder, style)
                for style in ("original", "lines", "bytes")), key=len)


def codec_recipes(payload_size: int, thorough: bool = False) -> list[dict]:
    """Finite deterministic context/model portfolio, including source-friendly lc=0.

    A dictionary covering the complete input is sufficient for this bounded
    in-memory LZ search. Decoder window is capped at 8 MiB for the raw launcher.
    Input size alone does not identify the best literal context or parse.
    """
    dictionary = min(8 << 20, max(4096, 1 << (max(1, payload_size) - 1).bit_length()))
    contexts = [(lc, lp, pb) for lp in range(5) for lc in range(5-lp) for pb in range(5)]
    if not thorough:
        contexts = [(lc, lp, pb) for lp in (0, 1) for lc in range(5-lp) for pb in (0, 1, 2)]
    recipes = []
    for fmt, x86 in (("alone", False), ("xz", False), ("raw", False), ("raw", True)):
        for preset in (6, 9 | lzma.PRESET_EXTREME):
            for lc, lp, pb in contexts:
                recipes.append(dict(format=fmt, x86=x86, preset=preset,
                                    dict_size=dictionary, lc=lc, lp=lp, pb=pb))
    recipes.extend({"format": fmt, "level": level} for fmt in ("gzip", "bzip2") for level in (1, 9))
    return recipes


def compress(data: bytes, recipe: dict) -> bytes:
    fmt = recipe["format"]
    if fmt == "gzip":
        return gzip.compress(data, compresslevel=recipe["level"], mtime=0)
    if fmt == "bzip2":
        return bz2.compress(data, compresslevel=recipe["level"])
    filter_id = lzma.FILTER_LZMA1 if fmt == "alone" else lzma.FILTER_LZMA2
    filters = ([{"id": lzma.FILTER_X86}] if recipe.get("x86") else []) + [
        {"id": filter_id, **{key: recipe[key] for key in ("preset", "dict_size", "lc", "lp", "pb", "mf", "nice_len", "depth") if key in recipe}}]
    kw = {"format": {"alone": lzma.FORMAT_ALONE, "xz": lzma.FORMAT_XZ, "raw": lzma.FORMAT_RAW}[fmt],
          "filters": filters}
    if fmt == "xz":
        kw["check"] = lzma.CHECK_NONE
    return lzma.compress(data, **kw)


def decoder_for(recipe: dict) -> str:
    fmt = recipe["format"]
    if fmt in ("alone", "xz"):
        return "xz -d"
    if fmt == "raw":
        return "xz -dcFraw " + ("--x86 " if recipe.get("x86") else "") + "--lzma2"
    return {"gzip": "gzip -d", "bzip2": "bzip2 -d"}[fmt]


def refinement_recipes(records: list[dict], thorough: bool) -> list[dict]:
    """Refine two promising codec families; the bound and seeds are auditable.

    This is intentionally a finite beam, not a claim that all parameter
    interactions have been explored. Original packed bytes remain available.
    """
    seeds = []
    seen = set()
    for item in sorted(records, key=lambda row: row["bytes"]):
        recipe = item["recipe"]
        if recipe["format"] not in ("alone", "xz", "raw"):
            continue
        family = (recipe["format"], recipe.get("x86", False))
        if family in seen:
            continue
        seen.add(family)
        seeds.append(recipe)
        if len(seeds) == 2:
            break
    nice = range(4, 274) if thorough else (4, 8, 16, 24, 32, 48, 64, 96, 128, 192, 273)
    match_finders = (lzma.MF_HC3, lzma.MF_HC4, lzma.MF_BT2, lzma.MF_BT3, lzma.MF_BT4)
    return [{**seed, "mf": mf, "nice_len": length} for seed in seeds for mf in match_finders for length in nice]


def bounded_command(command: list[str], data: bytes, directory: Path, timeout=60, limit=MAX_PAYLOAD+65536) -> dict:
    """Trusted commands, bounded I/O/time, cleanup of their original process group."""
    started = time.monotonic()
    proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            cwd=directory, start_new_session=True, close_fds=True, bufsize=0)
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    sent = 0
    with selectors.DefaultSelector() as selector:
        for stream, mode, name in ((proc.stdin, selectors.EVENT_WRITE, "stdin"),
                                   (proc.stdout, selectors.EVENT_READ, "stdout"),
                                   (proc.stderr, selectors.EVENT_READ, "stderr")):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, mode, name)
        try:
            while selector.get_map():
                remaining = timeout-(time.monotonic()-started)
                if remaining <= 0:
                    raise ValueError("command timeout: " + command[0])
                for key, _ in selector.select(min(remaining, .05)):
                    stream, name = key.fileobj, key.data
                    if name == "stdin":
                        try:
                            count = os.write(stream.fileno(), data[sent:sent+65536]) if sent < len(data) else 0
                            sent += count
                        except BrokenPipeError:
                            sent = len(data)
                        if sent == len(data):
                            selector.unregister(stream)
                            stream.close()
                    else:
                        chunk = os.read(stream.fileno(), 65536)
                        if not chunk:
                            selector.unregister(stream)
                            stream.close()
                        else:
                            buffers[name].extend(chunk)
                            if sum(map(len, buffers.values())) > limit:
                                raise ValueError("command output_limit: " + command[0])
            proc.wait(timeout=max(.01, timeout-(time.monotonic()-started)))
        finally:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait()
            for stream in (proc.stdin, proc.stdout, proc.stderr):
                if not stream.closed:
                    stream.close()
    return {"returncode": proc.returncode, **{k: bytes(v) for k, v in buffers.items()},
            "seconds": round(time.monotonic()-started, 6)}


def native_fingerprint(source: bytes, argv: list[str], directory: Path) -> dict:
    """Use the submitted compiler invocation, via stdin, at one stable path."""
    output = directory / "compiled-engine"
    if output.exists():
        output.unlink()
    command = [word.replace("{output}", str(output)) for word in argv]
    run = bounded_command(command, source, directory)
    compiler = Path(shutil.which(command[0]) or command[0]).resolve()
    detail = {"argv": command, "returncode": run["returncode"], "stderr": run["stderr"][-8192:].decode(errors="replace"),
              "compiler_sha256": sha(compiler.read_bytes()), "seconds": run["seconds"]}
    if run["returncode"] == 0 and output.is_file():
        detail["sha256"] = sha(output.read_bytes())
        detail["bytes"] = output.stat().st_size
    return detail


def payload_variants(payload: bytes, manifest: dict, out: Path, notation: bool) -> tuple[list[dict], list[dict]]:
    values = [{"id": "raw", "data": payload, "audit": [], "equivalence": "decoded payload byte identity"}]
    reports = []
    if not notation or not manifest.get("language"):
        return values, reports
    from nvnotation import generate_variants
    opts = manifest.get("notation", {})
    candidates = generate_variants(payload, language=manifest["language"], target=opts.get("target"),
                                   token_contract=opts.get("token_contract", "opaque"),
                                   compact=opts.get("compact", True), max_variants=13)
    compiler = manifest.get("compile_argv")
    baseline = None
    if compiler:
        builddir = out / "native-equivalence"
        builddir.mkdir(exist_ok=True)
        baseline = native_fingerprint(payload, compiler, builddir)
        reports.append({"id": "baseline", "native": baseline})
    seen_sources = {sha(payload): "raw"}
    for item in candidates:
        if item["data"] == payload:
            continue
        report = {key: val for key, val in item.items() if key != "data"}
        digest = sha(item["data"])
        if digest in seen_sources:
            reports.append({**report, "duplicate_source_of": seen_sources[digest], "compiled_again": False})
            continue
        seen_sources[digest] = item["id"]
        accepted = False
        if manifest["language"] == "python":
            accepted = True  # nvnotation enforces typed AST identity and opt-in source contract.
            report["equivalence"] = "typed Python AST identity; source non-observation contract"
        elif compiler and baseline.get("sha256"):
            native = native_fingerprint(item["data"], compiler, builddir)
            report["native"] = native
            accepted = native.get("sha256") == baseline["sha256"]
            report["equivalence"] = "complete native bytes identical under submitted compile recipe"
        report["accepted"] = accepted
        reports.append(report)
        if accepted:
            values.append({**item, "equivalence": report["equivalence"]})
    return values, reports


def _actual_decoder(blob: bytes, decoder: str, payload: bytes, *, failure_report=False) -> dict:
    command = shlex.split(decoder)
    run = bounded_command(command, blob, Path.cwd(), timeout=10)
    if run["returncode"] and failure_report:
        return {"argv": command, "status": "fail", "returncode": run["returncode"],
                "stderr": run["stderr"].decode(errors="replace"),
                "meaning": "original deployment command failed; payload identity is separately pinned"}
    if run["returncode"] or run["stdout"] != payload:
        raise ValueError("deployment decoder failed byte-identity check: " + decoder)
    binary = Path(shutil.which(command[0]) or command[0]).resolve()
    return {"argv": command, "executable": str(binary), "executable_sha256": sha(binary.read_bytes()),
            "payload_sha256": sha(payload), "status": "pass"}


def check_deployed_payload(path: Path, record: dict, manifest: dict, original: bytes, variants: list[dict]) -> dict:
    if not manifest.get("envelope"):
        return {"status": "native_payload_checked_by_packer"}
    if record["id"] == "identity":
        prefix = manifest["envelope"]["header"].encode()
        decoder = manifest["envelope"]["decoder"]
    else:
        recipe = record["recipe"]
        decoder = recipe.get("decoder") if recipe["format"] == "submitted" else decoder_for(recipe)
        prefix = best_header(manifest["envelope"]["header"].encode(), manifest["envelope"]["decoder"], decoder)
    match = TAIL.search(prefix)
    command = ["tail", "-"+match[1].decode()+"+"+match[2].decode(), str(path.resolve())]
    tail = bounded_command(command, b"", path.parent, timeout=10)
    expected = path.read_bytes()[len(prefix):]
    if tail["returncode"] or tail["stdout"] != expected:
        raise ValueError("deployed tail spelling does not restore the expected suffix")
    source_data = next(item["data"] for item in variants if item["id"] == record["variant"])
    return {"tail_argv": command, "tail_status": "pass", "decoder": _actual_decoder(expected, decoder, source_data)}


def run(manifest_path: Path, output: Path, *, thorough=False, notation=True, jobs=2,
        uci=False, oracle_path=None, uci_config=None, max_protocol_candidates=16) -> dict:
    manifest_path = manifest_path.resolve(strict=True)
    manifest = json.loads(manifest_path.read_text())
    source = (manifest_path.parent / manifest["artifact"]).resolve(strict=True)
    original = source.read_bytes()
    if len(original) > MAX_ARTIFACT or sha(original) != manifest["sha256"]:
        raise ValueError("submitted artifact size/hash does not match manifest")
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    original_path = output / "original"
    original_path.write_bytes(original)
    original_path.chmod(0o755)
    summary = {"format": "nvcompact.envelope.v1", "version": VERSION,
               "name": manifest["name"], "manifest": manifest, "original_bytes": len(original),
               "original_sha256": sha(original), "platform": platform.platform(),
               "python": sys.version, "python_sha256": sha(Path(sys.executable).read_bytes()),
               "tool_sha256": sha(Path(__file__).read_bytes()),
               "scope": "finite codec/spelling portfolio; no claim of global compression optimum",
               "notation": [], "candidates": 1}
    summary["module_sha256"] = {name: sha((Path(__file__).parent/name).read_bytes())
                                for name in ("nvenvelope.py", "nvreproduce.py", "nvnotation.py", "nvuci.py", "nvpack.py")}
    identity = {"id": "identity", "bytes": len(original), "sha256": sha(original),
                "variant": "raw", "equivalence": "complete submitted file byte identity"}
    records = [identity]
    best_data, best_record = original, identity
    per_variant = []
    header = payload = None
    variants = [{"id": "raw", "data": original}]
    if manifest.get("envelope"):
        if manifest.get("category") == "4k-elf":
            raise ValueError("ELF-only category cannot gain a shell envelope")
        header, payload = extract(original, manifest["envelope"])
        original_blob = original[len(header):]
        pinned_payload = manifest.get("payload_sha256")
        if pinned_payload and sha(payload) != pinned_payload:
            raise ValueError("decoded payload does not match independent payload hash")
        summary["original_decoder_check"] = _actual_decoder(original_blob, manifest["envelope"]["decoder"], payload,
                                                           failure_report=bool(pinned_payload))
        summary["original_deployment_equivalent"] = summary["original_decoder_check"]["status"] == "pass"
        (output / "original-payload").write_bytes(payload)
        summary["payload_sha256"] = sha(payload)
        summary["payload_bytes"] = len(payload)
        variants, summary["notation"] = payload_variants(payload, manifest, output, notation)
        # Preserve the upstream compressor's work too. Recompressing with a
        # finite portfolio need not rediscover its match-finder choices.
        submitted_decoder = decoder_for(manifest["envelope"]["payload_codec"])
        submitted_header = best_header(header, manifest["envelope"]["decoder"], submitted_decoder)
        submitted = submitted_header + original_blob
        submitted_record = {"id": "submitted-payload", "variant": "raw", "bytes": len(submitted),
                            "sha256": sha(submitted), "header": submitted_header.decode(),
                            "header_bytes": len(submitted_header), "packed_bytes": len(original_blob),
                            "equivalence": "original compressed payload; equivalent tail/decoder spelling",
                            "recipe": {"format": "submitted", "decoder": submitted_decoder}}
        records.append(submitted_record)
        if len(submitted) < best_record["bytes"]:
            best_data, best_record = submitted, submitted_record
        for variant in variants:
            data = variant["data"]
            recipes = codec_recipes(len(data), thorough)
            def evaluate(recipe):
                blob = compress(data, recipe)
                if decode(blob, recipe) != data:
                    raise ValueError("codec round-trip changed payload")
                new_header = best_header(header, manifest["envelope"]["decoder"], decoder_for(recipe))
                result = new_header + blob
                record = {"id": sha(json.dumps([variant["id"], recipe], sort_keys=True).encode())[:16],
                          "variant": variant["id"], "recipe": recipe, "bytes": len(result),
                          "header_bytes": len(new_header), "packed_bytes": len(blob), "source_bytes": len(data),
                          "sha256": sha(result), "equivalence": variant["equivalence"]}
                return record, result
            variant_best = None
            variant_records = []
            with ThreadPoolExecutor(max_workers=jobs) as executor:
                for record, result in executor.map(evaluate, recipes):
                    records.append(record)
                    variant_records.append(record)
                    # Stable ties prefer the original identity, then recipe order.
                    if variant_best is None or record["bytes"] < variant_best["bytes"]:
                        variant_best = record
                    if record["bytes"] < best_record["bytes"]:
                        best_data, best_record = result, record
                refinements = refinement_recipes(variant_records, thorough)
                for record, result in executor.map(evaluate, refinements):
                    record["phase"] = "match-finder-refinement"
                    records.append(record)
                    if record["bytes"] < variant_best["bytes"]:
                        variant_best = record
                    if record["bytes"] < best_record["bytes"]:
                        best_data, best_record = result, record
            per_variant.append(variant_best)
        summary["variants"] = per_variant
        if best_record["id"] not in ("identity", "submitted-payload"):
            selected = next(item for item in variants if item["id"] == best_record["variant"])
            selected_payload = selected["data"]
            recipe = best_record["recipe"]
            new_header = best_header(header, manifest["envelope"]["decoder"], decoder_for(recipe))
            blob = compress(selected_payload, recipe)
            if new_header + blob != best_data:
                raise ValueError("selected recipe is not reproducible")
            summary["decoder_check"] = _actual_decoder(blob, decoder_for(recipe), selected_payload)
            (output / "selected-payload").write_bytes(selected_payload)
            best_record["payload_sha256"] = sha(selected_payload)
            best_record["header"] = new_header.decode()
    elif original.startswith(b"\x7fELF") and manifest.get("category") == "4k":
        # No ELF metadata edits: golfed programs can execute bytes in headers.
        from nvpack import candidate_ids, pack_by_id
        for pack_id in candidate_ids("x86_64-unknown-linux-gnu"):
            if pack_id == "raw":
                continue
            result = pack_by_id(original, target="x86_64-unknown-linux-gnu", pack_id=pack_id)
            data = result["data"]
            record = {"id": "native-"+pack_id, "variant": "raw", "bytes": len(data), "sha256": sha(data),
                      "recipe": {"format": "native_pack", "pack_id": pack_id},
                      "equivalence": "complete original ELF restored byte-for-byte; native loader contract",
                      "header_bytes": result["loader_bytes"], "packed_bytes": result["payload_bytes"]}
            records.append(record)
            if len(data) < best_record["bytes"]:
                best_data, best_record = data, record

    def regenerate(record):
        if record["id"] == "identity":
            data = original
        elif record["id"] == "submitted-payload":
            data = submitted_header + original_blob
        elif record["recipe"]["format"] == "native_pack":
            from nvpack import pack_by_id
            data = pack_by_id(original, target="x86_64-unknown-linux-gnu", pack_id=record["recipe"]["pack_id"])["data"]
        else:
            source_data = next(item["data"] for item in variants if item["id"] == record["variant"])
            new_header = best_header(header, manifest["envelope"]["decoder"], decoder_for(record["recipe"]))
            data = new_header + compress(source_data, record["recipe"])
        if len(data) != record["bytes"] or sha(data) != record["sha256"]:
            raise ValueError("fresh selected recipe does not reproduce exactly")
        return data

    if regenerate(best_record) != best_data:
        raise ValueError("measurement winner does not reproduce")
    winner = output / "smallest"
    winner.write_bytes(best_data)
    winner.chmod(0o755)
    if best_record["id"] != "identity":
        summary["smallest_payload_check"] = check_deployed_payload(winner, best_record, manifest, original, variants)
    summary.update(candidates=len(records), winner=best_record, saved_bytes=len(original)-len(best_data),
                   no_size_regression=len(best_data) <= len(original), compression_seconds=round(time.monotonic()-started, 3))
    write_json(output / "candidates.json", records)
    summary["accepted"] = None
    if uci:
        from nvuci import verify_engine, compare_results
        if manifest.get("runtime_blocked"):
            summary["uci"] = {"status": "blocked", "reason": manifest["runtime_blocked"]}
        else:
            config = {"oracle_path": oracle_path, **(uci_config or {})}
            baseline = verify_engine([str(original_path.resolve())], {**config, "artifact_path": str(original_path.resolve())})
            write_json(output / "uci-original.json", baseline)
            screened = set()
            protocol_attempts = []
            ordered = sorted(enumerate(records), key=lambda pair: (pair[1]["bytes"], pair[0]))
            for _, record in ordered:
                if record["bytes"] > len(original) or record["sha256"] in screened:
                    continue
                if len(screened) >= max_protocol_candidates:
                    break
                screened.add(record["sha256"])
                path = winner if record["sha256"] == best_record["sha256"] else output / "protocol-candidate"
                data = regenerate(record)
                path.write_bytes(data)
                path.chmod(0o755)
                if record["id"] != "identity":
                    check_deployed_payload(path, record, manifest, original, variants)
                candidate = verify_engine([str(path.resolve())], {**config, "artifact_path": str(path.resolve())})
                write_json(output / ("uci-smallest.json" if path == winner else "uci-"+record["id"]+".json"), candidate)
                if path == winner:
                    summary["uci"] = compare_results(baseline, candidate)
                protocol_attempts.append({"id": record["id"], "sha256": record["sha256"], "bytes": record["bytes"], "verdict": candidate["verdict"]})
                if candidate["verdict"] == "pass":
                    accepted = output / "accepted"
                    accepted.write_bytes(regenerate(record))
                    accepted.chmod(0o755)
                    final = verify_engine([str(accepted.resolve())], {**config, "artifact_path": str(accepted.resolve())})
                    write_json(output / "uci-accepted.json", final)
                    if final["verdict"] != "pass":
                        accepted.rename(output / "rejected-final")
                        raise ValueError("accepted candidate failed independent final replay; investigate reproducibility")
                    summary["accepted"] = {**record, "protocol_verdict": "pass", "reproduced": True}
                    break
            # A bounded search must not lose its already known valid fallback.
            if summary["accepted"] is None and baseline["verdict"] == "pass":
                accepted = output / "accepted"
                accepted.write_bytes(regenerate(identity))
                accepted.chmod(0o755)
                final = verify_engine([str(accepted.resolve())], {**config, "artifact_path": str(accepted.resolve())})
                write_json(output / "uci-accepted.json", final)
                if final["verdict"] != "pass":
                    accepted.rename(output / "rejected-final")
                    raise ValueError("original fallback failed final replay; investigate reproducibility")
                summary["accepted"] = {**identity, "protocol_verdict": "pass", "reproduced": True, "reason": "verified original fallback after bounded candidate search"}
            summary["protocol_attempts"] = protocol_attempts
            eligible_shas = {item["sha256"] for item in records if item["bytes"] <= len(original)}
            summary["protocol_search_complete"] = bool(summary["accepted"] and summary["accepted"].get("reason") is None) or eligible_shas <= screened
    else:
        summary["uci"] = {"status": "not_run"}
    # A minimum can exist without being eligible for publication. Never turn
    # baseline protocol failure into a pass by retaining identity.
    summary["acceptance"] = "uci_verified; external-command/rule review still separate" if summary["accepted"] else "no_accepted_artifact; measurement_only"
    if source.read_bytes() != original or winner.read_bytes() != best_data:
        raise ValueError("input or final artifact mutated during campaign")
    write_json(output / "summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--thorough", action="store_true")
    parser.add_argument("--no-notation", action="store_true")
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--uci", action="store_true")
    parser.add_argument("--oracle-path")
    parser.add_argument("--uci-config", type=Path)
    parser.add_argument("--max-protocol-candidates", type=int, default=16)
    args = parser.parse_args()
    if not 1 <= args.jobs <= 16 or not 1 <= args.max_protocol_candidates <= 256:
        parser.error("--jobs must be 1..16 and --max-protocol-candidates 1..256")
    try:
        result = run(args.manifest, args.output.resolve(), thorough=args.thorough,
                     notation=not args.no_notation, jobs=args.jobs, uci=args.uci,
                     oracle_path=args.oracle_path,
                     uci_config=json.loads(args.uci_config.read_text()) if args.uci_config else None,
                     max_protocol_candidates=args.max_protocol_candidates)
        print(json.dumps({key: result[key] for key in ("name", "original_bytes", "winner", "saved_bytes", "candidates", "uci")}, indent=2))
        return 0 if not args.uci or result["accepted"] else 2
    except (ValueError, OSError, subprocess.SubprocessError, lzma.LZMAError) as exc:
        print("nvenvelope: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
