"""Canonical E19 model, exact integer inference and shipping representation.

This is a development/build input. No JSON, Python or trainer is part of an
engine submission. The arithmetic ABI preserves C int operations before the
division, division toward zero, the final clamp and white score perspective.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import struct
from typing import Sequence

HERE = Path(__file__).resolve().parent
DEFAULT_MODEL = HERE / "e19.json"
ARITHMETIC = "e19-c-int32-trunc0-v1"
TRAINABLE = tuple(range(5, 14))
PHYSICAL_SLOTS = tuple(range(1, 6)) + tuple(range(7, 21))
NAMES = (
    "material_pawn", "material_knight", "material_bishop", "material_rook", "material_queen",
    "center_pawn", "center_knight", "center_bishop", "center_rook", "center_queen", "center_king",
    "pawn_advance", "tempo", "quadratic_gain", "order_victim", "order_attacker",
    "order_promotion", "order_center", "order_pawn_rank",
)
DOMAIN = {"pieces_per_color_max": 16, "center_max": 6,
          "pawn_advance_abs_max": 6, "clamp_abs": 20000}
PHYSICAL_ABI = {"slots": 21, "zero_slots": [0, 6], "logical_slots": list(PHYSICAL_SLOTS)}
I32_MAX = (1 << 31) - 1


def trunc0(numerator: int, denominator: int = 128) -> int:
    if denominator <= 0:
        raise ValueError("positive denominator required")
    return (-1 if numerator < 0 else 1) * (abs(numerator) // denominator)


def round_away(value: float) -> int:
    """Nearest integer; exact halves round away from zero, independent of libc."""
    if not math.isfinite(value):
        raise ValueError("coefficient must be finite")
    return (-1 if value < 0 else 1) * math.floor(abs(value) + 0.5)


def center(square: int) -> int:
    if type(square) is not int or square < 0 or square & ~127 or square & 0x88:
        raise ValueError("0x88 board square required")
    file, rank = square & 7, square >> 4
    return min(file, 7 - file) + min(rank, 7 - rank)


@dataclass(frozen=True)
class PositionFeatures:
    """White-minus-black sufficient statistics; not a fixed linear E19 model."""
    material: tuple[int, ...]
    centers: tuple[int, ...]
    pawn_advance: int
    side: int

    def __post_init__(self):
        if len(self.material) != 5 or len(self.centers) != 6 or self.side not in (-1, 1):
            raise ValueError("E19 feature ABI differs")
        if any(type(v) is not int for v in (*self.material, *self.centers, self.pawn_advance)):
            raise ValueError("integer E19 feature values required")


def features(cells: Sequence[int], side: int) -> PositionFeatures:
    if len(cells) != 128 or side not in (-1, 1):
        raise ValueError("128 mailbox cells and white/black side required")
    material, centers, populations = [0] * 5, [0] * 6, [0, 0]
    advance = 0
    for square, piece in enumerate(cells):
        if type(piece) is not int or abs(piece) > 6 or (square & 0x88 and piece):
            raise ValueError("piece/mailbox domain differs")
        if not piece:
            continue
        sign = 1 if piece > 0 else -1
        kind = abs(piece)
        populations[piece < 0] += 1
        if kind < 6:
            material[kind - 1] += sign
        centers[kind - 1] += sign * center(square)
        if kind == 1:
            own_rank = square >> 4 if piece > 0 else 7 - (square >> 4)
            advance += sign * (own_rank - 1)
    if max(populations) > 16:
        raise ValueError("model admits at most 16 pieces per color")
    return PositionFeatures(tuple(material), tuple(centers), advance, side)


def mailbox_from_fen(fen: str) -> tuple[tuple[int, ...], int, int]:
    """Parse model inputs; chess legality is independently checked by the dataset oracle."""
    fields = fen.split()
    if len(fields) != 6 or fields[1] not in ("w", "b"):
        raise ValueError("complete standard FEN required")
    ranks = fields[0].split("/")
    if len(ranks) != 8:
        raise ValueError("eight FEN ranks required")
    cells = [0] * 128
    for rank, text in zip(range(7, -1, -1), ranks):
        file = 0
        for char in text:
            if char in "12345678":
                file += int(char)
            elif char in "PNBRQKpnbrqk" and file < 8:
                cells[rank * 16 + file] = (1 if char.isupper() else -1) * ("PNBRQK".index(char.upper()) + 1)
                file += 1
            else:
                raise ValueError("FEN piece/rank differs")
        if file != 8:
            raise ValueError("eight files per rank required")
    ep = -1
    if fields[3] != "-":
        if len(fields[3]) != 2 or fields[3][0] not in "abcdefgh" or fields[3][1] not in "36":
            raise ValueError("FEN en-passant target differs")
        ep = (int(fields[3][1]) - 1) * 16 + ord(fields[3][0]) - ord("a")
    return tuple(cells), 1 if fields[1] == "w" else -1, ep


@dataclass(frozen=True)
class Model:
    model_id: str
    coefficients: tuple[int, ...]
    provenance: str = "hand-authored; untrained"

    def __post_init__(self):
        object.__setattr__(self, "coefficients", tuple(self.coefficients))
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", self.model_id) or len(self.coefficients) != 19:
            raise ValueError("model ID and nineteen coefficients required")
        if any(type(v) is not int or not -(1 << 15) <= v < (1 << 15) for v in self.coefficients):
            raise ValueError("exact signed16 coefficient required")
        self.bounds()

    @classmethod
    def load(cls, path: Path | str = DEFAULT_MODEL) -> "Model":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("format") != 1 or data.get("arithmetic") != ARITHMETIC:
            raise ValueError("E19 model arithmetic/format differs")
        if tuple(data.get("coefficient_names", ())) != NAMES or tuple(data.get("trainable_indices", ())) != TRAINABLE:
            raise ValueError("E19 coefficient/trainable ABI differs")
        if data.get("domain") != DOMAIN or data.get("physical_abi") != PHYSICAL_ABI:
            raise ValueError("E19 domain/physical ABI differs")
        return cls(data["model_id"], tuple(data["coefficients"]), data.get("provenance", "unspecified"))

    @classmethod
    def from_physical_source(cls, source: bytes, *, model_id: str, name: str | None = None) -> "Model":
        """Recover the baseline model after the caller admits its source closure.

        This reads a representation, not proof that arbitrary source implements
        E19. The owning producer and actual-consumer oracle keep that contract.
        No second hard-coded copy of the legacy coefficients is needed.
        """
        _, values = _physical_table(source, name=name)
        if values[0] != 0 or values[6] != 0:
            raise ValueError("E19 physical zero slots must remain zero")
        return cls(model_id, tuple(values[index] for index in PHYSICAL_SLOTS),
                   "baseline recovered from separately admitted shipping source")

    def as_dict(self) -> dict:
        return {"format": 1, "model_id": self.model_id, "provenance": self.provenance,
                "arithmetic": ARITHMETIC, "coefficient_names": list(NAMES),
                "coefficients": list(self.coefficients), "trainable_indices": list(TRAINABLE),
                "domain": dict(DOMAIN),
                "physical_abi": {"slots": 21, "zero_slots": [0, 6], "logical_slots": list(PHYSICAL_SLOTS)}}

    def canonical_bytes(self) -> bytes:
        return (json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":")) + "\n").encode()

    def coefficient_sha256(self) -> str:
        return sha256(struct.pack("<19h", *self.coefficients)).hexdigest()

    def physical_coefficients(self) -> tuple[int, ...]:
        values = [0] * 21
        for slot, coefficient in zip(PHYSICAL_SLOTS, self.coefficients):
            values[slot] = coefficient
        return tuple(values)

    def bounds(self) -> dict[str, int]:
        """Recompute conservative bounds, including every pre-division C product."""
        w = self.coefficients
        material = 16 * (max((0, *w[:5])) - min((0, *w[:5])))
        piece_activity = max(6 * abs(w[i + 5]) + (6 * abs(w[11]) if i == 0 else 0) for i in range(6))
        activity = 32 * piece_activity
        gain_activity = abs(w[13]) * activity
        product = gain_activity * activity
        material_activity = material + activity
        quadratic_sum = material_activity + product // 128
        raw = quadratic_sum + abs(w[12])
        material_abs = max(abs(v) for v in (0, *w[:5]))
        order_victim = abs(w[14]) * material_abs
        order_attacker = abs(w[15]) * material_abs
        order_promotion = abs(w[16]) * max(abs(w[k] - w[0]) for k in range(1, 5))
        order_sum = 6 * abs(w[17]) + order_victim + order_attacker + order_promotion + 7 * abs(w[18])
        # The protected h consumer adds at most a 1,000,000 TT priority and
        # a 400,000+5,000 promotion priority before/with these model terms.
        # Validating R alone would admit near-INT_MAX values that overflow h.
        preordering_sum = order_sum + 1_405_000
        result = {"material_abs_upper": material, "activity_abs_upper": activity,
                  "gain_activity_abs_upper": gain_activity, "quadratic_product_abs_upper": product,
                  "material_activity_abs_upper": material_activity,
                  "quadratic_sum_abs_upper": quadratic_sum, "raw_abs_upper": raw,
                  "ordering_victim_product_abs_upper": order_victim,
                  "ordering_attacker_product_abs_upper": order_attacker,
                  "ordering_promotion_product_abs_upper": order_promotion,
                  "ordering_abs_upper": order_sum,
                  "preordering_abs_upper": preordering_sum, "clamp_abs": 20000}
        for name, bound in result.items():
            if bound > I32_MAX:
                raise ValueError(f"C signed32 bound exceeded before clamp: {name}={bound}")
        return result

    def integer_score(self, value: PositionFeatures) -> int:
        w = self.coefficients
        material = sum(a * b for a, b in zip(value.material, w[:5]))
        activity = sum(a * b for a, b in zip(value.centers, w[5:11])) + value.pawn_advance * w[11]
        bounds = self.bounds()
        if abs(material) > bounds["material_abs_upper"] or abs(activity) > bounds["activity_abs_upper"]:
            raise ValueError("feature accumulator exceeds admitted E19 board domain")
        raw = material + activity + trunc0(w[13] * activity * abs(activity)) + value.side * w[12]
        return min(20000, max(-20000, raw))

    def ordering(self, cells: Sequence[int], ep: int, origin: int, target: int, promotion: int = 0) -> int:
        center(origin); center(target)
        kind, victim = abs(cells[origin]), abs(cells[target])
        if not 1 <= kind <= 6 or victim > 6 or promotion not in (0, 2, 3, 4, 5):
            raise ValueError("piece/move ordering domain differs")
        if kind == 1 and target == ep and not victim:
            victim = 1
        w = self.coefficients
        result = w[17] * (center(target) - center(origin))
        if victim:
            result += w[14] * (w[victim - 1] if victim < 6 else 0)
            result += w[15] * (w[kind - 1] if kind < 6 else 0)
        if promotion:
            result += w[16] * (w[promotion - 1] - w[0])
        if kind == 1:
            result += w[18] * ((target >> 4) - (origin >> 4)) * (1 if cells[origin] > 0 else -1)
        return result

    def with_trainable(self, values: Sequence[float], *, model_id: str | None = None) -> "Model":
        if len(values) != len(TRAINABLE):
            raise ValueError("nine trainable coefficients required")
        coefficients = list(self.coefficients)
        for index, value in zip(TRAINABLE, values):
            coefficients[index] = round_away(value)
        if tuple(coefficients) != self.coefficients and (not model_id or model_id == self.model_id):
            raise ValueError("changed integer coefficients require a new model ID")
        return replace(self, coefficients=tuple(coefficients), model_id=model_id or self.model_id)

    def render_model_fragment(self) -> bytes:
        initializer = ",".join(map(str, self.coefficients))
        return ("/* Canonical E19 build fragment; " + self.model_id + ". */\n"
                "static const int16_t tiny_weights[19]={" + initializer + "};\n" + _C_BODIES).encode()

    def validate_physical_table(self, source: bytes, *, name: str | None = None) -> dict:
        """Validate the actual numeric table; does not claim consumer semantics."""
        match, values = _physical_table(source, name=name)
        if values != self.physical_coefficients():
            raise ValueError("actual E19 physical21 table differs")
        return {"table": match[1].decode(), "logical_count": 19, "physical_count": 21,
                "zero_slots": [0, 6], "coefficient_sha256": self.coefficient_sha256(),
                "consumer_semantics_checked": False}

    def bind_physical_table(self, source: bytes, *, source_model: "Model", name: str | None = None) -> tuple[bytes, dict]:
        """Bind a canonical model to a separately admitted source-model consumer.

        The owning producer still admits the complete source/consumer closure.
        Only its numeric physical table is changed here; no caller or model
        arithmetic rewrite is inferred from matching literal coefficients.
        """
        source_model.validate_physical_table(source, name=name)
        match, _ = _physical_table(source, name=name)
        before = match[2]
        after = ",".join(map(str, self.physical_coefficients())).encode()
        result = source[:match.start(2)] + after + source[match.end(2):]
        if result[:match.start(2)] + before + result[match.start(2) + len(after):] != source:
            raise RuntimeError("model table binding inverse differs")
        self.validate_physical_table(result, name=match[1].decode())
        return result, {"stage": "canonical-e19-physical-binding", "table": match[1].decode(),
                        "source_model_id": source_model.model_id, "model_id": self.model_id,
                        "source_coefficient_sha256": source_model.coefficient_sha256(),
                        "coefficient_sha256": self.coefficient_sha256(),
                        "source_sha256": sha256(source).hexdigest(), "result_sha256": sha256(result).hexdigest(),
                        "before": before.decode(), "after": after.decode(), "table_value_offset": match.start(2),
                        "unchanged_prefix_sha256": sha256(source[:match.start(2)]).hexdigest(),
                        "unchanged_suffix_sha256": sha256(source[match.end(2):]).hexdigest(),
                        "full_inverse": True, "consumer_code_changed": False,
                        "model_parameters_changed": self.coefficients != source_model.coefficients,
                        "change_kind": "model-parameters" if self.coefficients != source_model.coefficients else "model-input-binding"}


def _physical_table(source: bytes, *, name: str | None = None):
    aliases = {b"int16_t"}
    typedefs = re.findall(rb"\btypedef\s+([A-Za-z_]\w*)\s+([A-Za-z_]\w*)\s*;", source)
    for _ in range(len(typedefs) + 1):
        for original, alias in typedefs:
            if original in aliases:
                aliases.add(alias)
    type_pattern = b"(?:" + b"|".join(sorted(map(re.escape, aliases))) + b")"
    expression = rb"(?:static\s+)?(?:const\s+)?" + type_pattern + rb"\s+([A-Za-z_]\w*)\s*\[\s*21\s*\]\s*=\s*\{([^{}]*)\}"
    matches = []
    for match in re.finditer(expression, source):
        if name is not None and match[1].decode() != name:
            continue
        parts = [part.strip() for part in match[2].split(b",") if part.strip()]
        if any(not re.fullmatch(rb"[+-]?[0-9]+", part) for part in parts):
            continue
        values = tuple(map(int, parts))
        if len(values) == 21:
            matches.append((match, values))
    if len(matches) != 1:
        raise ValueError("actual E19 physical21 table differs or is ambiguous")
    return matches[0]


_C_BODIES = """static int Q(int q){
    int f=q&7,r=q>>4;
    return(f<4?f:7-f)+(r<4?r:7-r);
}
static uint64_t piece(za*p,int v,int q,int d){
    int a=abs(v),s=v>0?d:-d;
    p->v+=s*(a<6?tiny_weights[a-1]:0);
    p->a+=s*(tiny_weights[a+4]*Q(q)+
        (a==1?tiny_weights[11]*((v<0?7-(q>>4):q>>4)-1):0));
    return mix((uint64_t)(q+(v+6)*128));
}
static int S(const za*p){
    int s=p->v+p->a+tiny_weights[13]*p->a*abs(p->a)/128+
        p->s*tiny_weights[12];
    return s>20000?20000:s< -20000?-20000:s;
}
static int R(const za*p,Move m){
    int d=FROM(m),f=TO(m),i=p->b[d],a=abs(i),v=abs(p->b[f]),j=PROMO(m);
    if(a==1&&f==p->e&&!v)v=1;
    int s=tiny_weights[17]*(Q(f)-Q(d));
    if(v)s+=tiny_weights[14]*(v<6?tiny_weights[v-1]:0)+
        tiny_weights[15]*(a<6?tiny_weights[a-1]:0);
    if(j)s+=tiny_weights[16]*(tiny_weights[j-1]-tiny_weights[0]);
    if(a==1)s+=tiny_weights[18]*((f>>4)-(d>>4))*(i<0?-1:1);
    return s;
}
"""
