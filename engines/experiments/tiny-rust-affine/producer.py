"""One exact affine-HCE representation candidate, without changing its control."""
from hashlib import sha256
from pathlib import Path

EXPECTED = {
    "main.rs": "8b72a5561b85ae87177198f08257ddfeca0fe954c6ca20ac74756b39c199723c",
    "board.rs": "f27472ea055b67e61cdd82a3d7747feced50c899bef72365ffdc940043dedef3",
    "search.rs": "da2583806efea022b1b3b1337557b896a373a561f11d665b1ca747c29e3aed81",
    "runtime.rs": "802b497371a409744ad231cd8f621ea3d8b7cd931627e0396f3ec92ad1345b2d",
    "os.rs": "892cc62e2c126ebcbc171eb6f8059aacf92cf255d85341487e46effe2b94986e",
    "link.ld": "1e8f17bb2f06a6ddabf1f56d155bd7bdcd8c4406d140c22770bcfda96d459bbc",
    "build.py": "08f28ebdc45ad49c2a23f7eb8e28b086612ea9a33dbc39cb8ccbd66bfcf68e89",
}

ORIGINAL_VALUE = """pub fn value(p: i8, square: usize) -> i32 {
    let a = p.abs() as usize;
    let rank = (square >> 4) as i32;
    let advance = if p > 0 { rank } else { 7 - rank };
    let center = 7 - (2 * (square & 7) as i32 - 7).abs() - (2 * rank - 7).abs();
    let positional = match a {
        1 => advance * 7 + center * 2, 2 => center * 9,
        3 => center * 5, 4 => advance * 2, 5 => center * 2,
        6 => -center * 3, _ => 0,
    };
    p.signum() as i32 * ([0, 100, 320, 330, 500, 900, 0][a] + positional)
}
"""


def transform(source: str) -> str:
    """Preserve every source byte outside the reviewed value definition."""
    if sha256(source.encode("utf-8")).hexdigest() != EXPECTED["board.rs"]:
        raise ValueError("unreviewed original board bytes")
    if source.count(ORIGINAL_VALUE) != 1:
        raise ValueError("unexpected original value shape")
    replacement = Path(__file__).with_name("value.rs.in").read_text(encoding="utf-8")
    if not replacement.endswith("}\n") or replacement.count("pub fn value(") != 1:
        raise ValueError("unexpected affine candidate shape")
    return source.replace(ORIGINAL_VALUE, replacement, 1)


def produce(files: dict[str, bytes]) -> tuple[dict[str, bytes], dict]:
    if files.keys() != EXPECTED.keys():
        raise ValueError("expected exactly seven reviewed production inputs")
    for name, data in files.items():
        if sha256(data).hexdigest() != EXPECTED[name]:
            raise ValueError("production input drift: " + name)
    output = dict(files)
    output["board.rs"] = transform(files["board.rs"].decode("utf-8")).encode("utf-8")
    changed = [name for name in files if output[name] != files[name]]
    if changed != ["board.rs"]:
        raise ValueError("candidate changed an unexpected input")
    return output, {
        "changed_files": changed,
        "input_sha256": {name: sha256(data).hexdigest() for name, data in files.items()},
        "output_sha256": {name: sha256(data).hexdigest() for name, data in output.items()},
        "scope": "only value() and its one static packed coefficient table",
        "unsafe_added": False,
        "safe_index_rejection_preserved": True,
    }


def merged_for_measurement(files: dict[str, bytes]) -> bytes:
    """One identical inline-module layout for byte counts only, never built."""
    text = files["main.rs"].decode("utf-8")
    for name in ("board", "os", "search", "runtime"):
        old = f"mod {name};"
        if text.count(old) != 1:
            raise ValueError("unexpected module declaration: " + name)
        body = files[name + ".rs"].decode("utf-8")
        text = text.replace(old, f"mod {name} {{\n{body}}}\n", 1)
    return text.encode("utf-8")
