#!/usr/bin/env python3
"""Fetch the two complete, checksum-pinned CC0 standard-rated PGN archives.

Downloads and receipts belong outside Git. Failed/partial downloads remain
with their receipt; this tool never substitutes another month or a fixture.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import urllib.request

DATABASE_URL = "https://database.lichess.org/"
CHECKSUM_URL = DATABASE_URL + "standard/sha256sums.txt"
CORPUS = {
    "2013-01": {"filename": "lichess_db_standard_rated_2013-01.pgn.zst",
                "sha256": "aa40b3671fa3cf1072eb182892cd90b0e1e003a4a5943492f64b77e7f3fd1635"},
    "2013-02": {"filename": "lichess_db_standard_rated_2013-02.pgn.zst",
                "sha256": "c136acdf343293c45252906fee91e3b561fb26a936979f52dbe04bb649a2fd86"},
}
for _month, _record in CORPUS.items():
    _record["url"] = DATABASE_URL + "standard/" + _record["filename"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def external_output(path: Path) -> Path:
    path = Path(path)
    if not path.is_absolute():
        raise ValueError("output must be an absolute path outside Git")
    resolved = path.resolve()
    if any((p / ".git").exists() for p in (resolved, *resolved.parents)):
        raise ValueError("data and receipts must be outside every Git checkout")
    if resolved.exists():
        raise ValueError("output must be new; existing evidence is preserved")
    return resolved


def _download(url: str, destination: Path, *, limit: int, wall_seconds: float = 180) -> dict:
    start = time.monotonic()
    digest = hashlib.sha256()
    count = 0
    request = urllib.request.Request(url, headers={"Accept-Encoding": "identity", "User-Agent": "Rove4k-E19-data/1"})
    with urllib.request.urlopen(request, timeout=30) as response, destination.open("xb") as target:
        if response.status != 200:
            raise ValueError("source did not return a complete HTTP 200 response")
        declared = response.headers.get("Content-Length")
        if declared is not None and int(declared) > limit:
            raise ValueError("source exceeds the declared download bound")
        while True:
            if time.monotonic() - start > wall_seconds:
                raise TimeoutError("download exceeded its total wall-time bound")
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            count += len(chunk)
            if count > limit:
                raise ValueError("source exceeds the download byte bound")
            target.write(chunk)
            digest.update(chunk)
        if declared is not None and count != int(declared):
            raise ValueError("incomplete HTTP entity")
        return {"url": url, "resolved_url": response.url, "bytes": count,
                "sha256": digest.hexdigest(), "content_length": int(declared) if declared else None}


def fetch_corpus(out: Path) -> dict:
    out = external_output(out)
    out.mkdir(parents=True)
    report = {"format": 1, "kind": "lichess-standard-cc0-fetch", "complete": False,
              "fetched_at_utc": datetime.now(timezone.utc).isoformat(), "sources": [],
              "license": "CC0-1.0", "training_updates": 0}

    def save() -> None:
        (out / "fetch.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    save()
    try:
        report["license_snapshot"] = _download(DATABASE_URL, out / "license-source.html", limit=2 * 1024 * 1024)
        license_html = (out / "license-source.html").read_text(encoding="utf-8")
        if "Creative Commons CC0" not in license_html:
            raise ValueError("official license statement is not present in the saved source")
        report["checksums"] = _download(CHECKSUM_URL, out / "sha256sums.txt", limit=256 * 1024)
        current = {}
        for line in (out / "sha256sums.txt").read_text(encoding="utf-8").splitlines():
            fields = line.split()
            if len(fields) == 2:
                current[fields[1].lstrip("*")] = fields[0]
        for month, frozen in CORPUS.items():
            if current.get(frozen["filename"]) != frozen["sha256"]:
                raise ValueError("official monthly checksum changed; a new corpus revision is required")
            partial = out / (frozen["filename"] + ".part")
            actual = _download(frozen["url"], partial, limit=64 * 1024 * 1024)
            row = dict(actual, month=month, filename=frozen["filename"], expected_sha256=frozen["sha256"], verified=False)
            report["sources"].append(row)
            save()
            if actual["sha256"] != frozen["sha256"]:
                raise ValueError("download does not match the frozen complete monthly archive")
            partial.rename(out / frozen["filename"])
            row["verified"] = True
            save()
        report["complete"] = True
        save()
        return report
    except Exception as error:
        report["error"] = {"type": type(error).__name__, "message": str(error)}
        save()
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = fetch_corpus(args.out)
    print(json.dumps({"complete": report["complete"], "months": len(report["sources"]), "out": str(args.out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
