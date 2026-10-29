"""Own fixed literal source draft. No AST, compiler, codec or engine calls."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def prepare(family, source, destination):
    policy = json.loads(Path(__file__).with_name("fixed.json").read_text())
    rule = policy["families"][family]
    raw = Path(source).read_bytes()
    assert sha(raw) == rule["source_sha256"], "fixed shipping source pin"
    old = raw.decode("ascii")
    new = old
    spans = []
    cursor = 0
    for pair in rule["spans"]:
        a, b = pair["old"], pair["new"]
        assert old.count(a) == 1, pair["role"]
        start = old.index(a)
        assert start >= cursor, "fixed non-overlapping source order"
        cursor = start + len(a)
        assert new.count(a) == 1
        new = new.replace(a, b, 1)
        spans.append(dict(pair, old_offset=start, old_bytes=len(a),
                          new_bytes=len(b), old_sha256=sha(a.encode()),
                          new_sha256=sha(b.encode())))
    old_parts, new_parts = [], []
    oc = nc = 0
    for pair in spans:
        pair["new_offset"] = new.index(pair["new"])
        old_parts.append(old[oc:pair["old_offset"]])
        new_parts.append(new[nc:pair["new_offset"]])
        oc = pair["old_offset"] + pair["old_bytes"]
        nc = pair["new_offset"] + pair["new_bytes"]
    old_parts.append(old[oc:])
    new_parts.append(new[nc:])
    assert old_parts == new_parts, "protected complement"
    inverse = new
    for pair in reversed(spans):
        i = pair["new_offset"]
        assert inverse[i:i+pair["new_bytes"]] == pair["new"]
        inverse = inverse[:i] + pair["old"] + inverse[i+pair["new_bytes"]:]
    assert inverse == old, "exact literal inverse"
    encoded = new.encode("ascii")
    assert len(encoded)-len(raw) == rule["expected_delta"]
    output = Path(destination)
    output.mkdir(parents=True, exist_ok=False)
    (output/"draft.c").write_bytes(encoded)
    receipt = dict(family=family, source_path=str(Path(source)),
                   source_bytes=len(raw), source_sha256=sha(raw),
                   draft_bytes=len(encoded), draft_sha256=sha(encoded),
                   delta=len(encoded)-len(raw), exact_inverse=True,
                   protected_complement_exact=True,
                   protected_complement_bytes=sum(map(len, old_parts)),
                   protected_complement_sha256=sha("".join(old_parts).encode()),
                   spans=spans, AST_PP_compile_codec_engine=0)
    (output/"source-record.json").write_text(json.dumps(receipt, indent=2)+"\n")
    return receipt


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("family", choices=["A", "F"])
    cli.add_argument("source")
    cli.add_argument("destination")
    args = cli.parse_args()
    record = prepare(args.family, args.source, args.destination)
    print(json.dumps({k:v for k,v in record.items() if k != "spans"}, indent=2))
