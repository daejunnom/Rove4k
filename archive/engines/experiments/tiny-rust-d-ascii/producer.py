"""Freeze one declared ASCII-ingress policy with unchanged Tiny D engine core."""
from hashlib import sha256
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPECTED = {
    "main.rs": "8b72a5561b85ae87177198f08257ddfeca0fe954c6ca20ac74756b39c199723c",
    "board.rs": "f27472ea055b67e61cdd82a3d7747feced50c899bef72365ffdc940043dedef3",
    "search.rs": "da2583806efea022b1b3b1337557b896a373a561f11d665b1ca747c29e3aed81",
    "runtime.rs": "802b497371a409744ad231cd8f621ea3d8b7cd931627e0396f3ec92ad1345b2d",
    "os.rs": "892cc62e2c126ebcbc171eb6f8059aacf92cf255d85341487e46effe2b94986e",
    "link.ld": "1e8f17bb2f06a6ddabf1f56d155bd7bdcd8c4406d140c22770bcfda96d459bbc",
    "build.py": "08f28ebdc45ad49c2a23f7eb8e28b086612ea9a33dbc39cb8ccbd66bfcf68e89",
}


def produce(files: dict[str, bytes]) -> tuple[dict[str, bytes], dict]:
    if files.keys() != EXPECTED.keys():
        raise ValueError("expected exactly seven reviewed production inputs")
    for name, data in files.items():
        if sha256(data).hexdigest() != EXPECTED[name]:
            raise ValueError("unreviewed source: " + name)
    original = files["board.rs"].decode("utf-8")
    start = original.index("    pub fn parse(&self, text: &str) -> Option<Move> {")
    end = original.index("    pub fn dead(&self) -> bool {", start)
    old_parse = original[start:end]
    signature = "    pub fn parse(&self, text: &str) -> Option<Move> {\n        let b = text.as_bytes();\n"
    wrapper = "    pub fn parse(&self, text: &str) -> Option<Move> {\n        self.parse_bytes(text.as_bytes())\n    }\n    pub fn parse_bytes(&self, b: &[u8]) -> Option<Move> {\n"
    if old_parse.count(signature) != 1:
        raise ValueError("unreviewed parse adapter shape")
    new_parse = (HERE / "parse-bytes.rs.in").read_text(encoding="utf-8")
    if new_parse != old_parse.replace(signature, wrapper, 1):
        raise ValueError("byte adapter changed the original parse algorithm")
    output = dict(files)
    output["main.rs"] = (HERE / "main.rs").read_bytes()
    output["board.rs"] = (original[:start] + new_parse + original[end:]).encode("utf-8")
    old_main = files["main.rs"].decode()
    new_main = output["main.rs"].decode()
    old_input = old_main.split("struct Input ", 1)[1].split("fn position(", 1)[0]
    new_input = new_main.split("struct Input ", 1)[1].split("fn whitespace(", 1)[0]
    if new_input != old_input + "\n":
        raise ValueError("line/EOF admission changed outside the declared ASCII policy")
    changed = [name for name in files if output[name] != files[name]]
    if changed != ["main.rs", "board.rs"]:
        raise ValueError("unexpected changed source set")
    return output, {
        "changed_files": changed,
        "input_sha256": {n: sha256(b).hexdigest() for n, b in files.items()},
        "output_sha256": {n: sha256(b).hexdigest() for n, b in output.items()},
        "board_delta": "parse-as-str wrapper plus byte parser; original geometry/play/parse body exact",
        "other_five_production_inputs_byte_identical": True,
        "input_line_buffer_and_EOF_algorithm_exact": True,
        "declared_policy_change": "reject a full line containing NUL or non-ASCII before command dispatch",
        "removed_token_array_bound": "2*T-1<=N<=32768 implies T<=16384",
        "unsafe_or_unchecked_UTF8_added": False,
    }


def merged_for_measurement(files: dict[str, bytes]) -> bytes:
    text = files["main.rs"].decode()
    for name in ("board", "os", "search", "runtime"):
        declaration = "mod " + name + ";"
        if text.count(declaration) != 1:
            raise ValueError("module declaration drift")
        text = text.replace(declaration, "mod " + name + " {\n" + files[name + ".rs"].decode() + "}\n", 1)
    return text.encode()
