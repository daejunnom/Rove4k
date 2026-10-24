"""One runtime start-position constructor change over frozen ASCII Rust D."""
from hashlib import sha256
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPECTED = {
    "main.rs": "e10e1b797085c1f032edcbfe28a828cf91e8cf2c71f3f11c063328744c34b8a3",
    "board.rs": "1a1ff1a0693a1b3f53ade2435d2996684a1bcd7b7eee333f28fe669645340b82",
    "search.rs": "da2583806efea022b1b3b1337557b896a373a561f11d665b1ca747c29e3aed81",
    "runtime.rs": "802b497371a409744ad231cd8f621ea3d8b7cd931627e0396f3ec92ad1345b2d",
    "os.rs": "892cc62e2c126ebcbc171eb6f8059aacf92cf255d85341487e46effe2b94986e",
    "link.ld": "1e8f17bb2f06a6ddabf1f56d155bd7bdcd8c4406d140c22770bcfda96d459bbc",
    "build.py": "08f28ebdc45ad49c2a23f7eb8e28b086612ea9a33dbc39cb8ccbd66bfcf68e89",
}


def produce(files: dict[str, bytes]) -> tuple[dict[str, bytes], dict]:
    if files.keys() != EXPECTED.keys():
        raise ValueError("exactly seven frozen production inputs required")
    for name, data in files.items():
        if sha256(data).hexdigest() != EXPECTED[name]:
            raise ValueError("unreviewed control input: " + name)
    source = files["board.rs"].decode("utf-8")
    begin = source.index("    pub fn start() -> Self {\n")
    end = source.index("    pub fn rebuild(&mut self) {\n", begin)
    old = source[begin:end]
    expected = """    pub fn start() -> Self {
        let mut b = Self::empty(); b.castle = 15;
        let back = [4, 2, 3, 5, 6, 3, 2, 4];
        for f in 0..8 {
            b.cells[f] = back[f]; b.cells[f + 16] = 1;
            b.cells[f + 96] = -1; b.cells[f + 112] = -back[f];
        }
        b.rebuild(); b
    }
"""
    if old != expected:
        raise ValueError("unreviewed start constructor shape")
    replacement = (HERE / "start.rs.in").read_text(encoding="utf-8")
    output = dict(files)
    output["board.rs"] = (source[:begin] + replacement + source[end:]).encode()
    changed = [name for name in files if files[name] != output[name]]
    if changed != ["board.rs"]:
        raise ValueError("unexpected changed production input")
    return output, {
        "changed_files": changed,
        "input_sha256": {n: sha256(b).hexdigest() for n, b in files.items()},
        "output_sha256": {n: sha256(b).hexdigest() for n, b in output.items()},
        "only_board_start_body_changed": True,
        "other_six_inputs_and_other_board_bodies_byte_exact": True,
        "representation": "runtime empty +32 calls to existing put, final state/context",
        "const_factory": False,
        "unsafe_added": False,
        "public_value_and_rebuild_unchanged": True,
        "first_profile": "fixed2 workers/TT18; scalar andHQ; unchanged recipe",
    }


def merged_for_measurement(files: dict[str, bytes]) -> bytes:
    text = files["main.rs"].decode()
    for name in ("board", "os", "search", "runtime"):
        marker = "mod " + name + ";"
        if text.count(marker) != 1:
            raise ValueError("module declaration drift")
        text = text.replace(marker, "mod " + name + " {\n" + files[name + ".rs"].decode() + "}\n", 1)
    return text.encode()
