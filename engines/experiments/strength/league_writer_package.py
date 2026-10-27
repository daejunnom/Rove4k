"""Build the two-file diagnostic Lambda archive in memory; do not upload it."""
import base64
import hashlib
import io
from pathlib import Path
import zipfile


SOURCE_FILES = ("league_writer_history.py", "league_writer_lambda.py")


def package(directory):
    """Return reproducible bytes and source/code hashes, without other files.

    The source directory and eventual S3 object/version/signing identity still
    require independent provenance review; these hashes are not signatures.
    """
    root = Path(directory).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("source directory required")
    payloads = {}
    for name in SOURCE_FILES:
        path = root / name
        if path.is_symlink() or not path.is_file() or path.resolve(strict=True).parent != root:
            raise ValueError("source path must be a regular file in the source directory")
        payloads[name] = path.read_bytes()
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED) as archive:
        for name in SOURCE_FILES:
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, payloads[name])
    raw = stream.getvalue()
    sha = hashlib.sha256(raw).digest()
    # Signing may change the archive. The Lambda Version parameter must use
    # the digest of the exact signed S3 object, not this unsigned digest.
    return {"bytes": raw, "unsigned_sha256_base64": base64.b64encode(sha).decode("ascii"),
            "unsigned_sha256_hex": sha.hex(),
            "source_sha256": {name: hashlib.sha256(payloads[name]).hexdigest() for name in SOURCE_FILES}}
