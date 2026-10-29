"""Small CPU E19 trainer with an explicit, unchanged-weight prepare path.

The float objective relaxes C integer truncation; it is not the integer model.
Only the exact integer exporter/oracle can qualify deployment coefficients.
No function trains at import, and prepare() never calls the optimizer.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
import math
from pathlib import Path
import random
import struct
import sys
from typing import Callable, Iterable, Iterator, Sequence

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from engines.model.e19 import Model, PositionFeatures, TRAINABLE, features, mailbox_from_fen


@dataclass(frozen=True)
class TrainingConfig:
    scale: float = 400.0
    l2: float = 1e-4
    learning_rate: float = 1e-3
    batch_size: int = 256
    seed: int = 20261025
    shuffle_buffer: int = 4096

    def __post_init__(self):
        if any(not math.isfinite(x) or x <= 0 for x in (self.scale, self.learning_rate)):
            raise ValueError("finite positive scale/learning rate required")
        if not math.isfinite(self.l2) or self.l2 < 0:
            raise ValueError("finite nonnegative L2 required")
        if type(self.batch_size) is not int or self.batch_size <= 0 or self.shuffle_buffer < self.batch_size:
            raise ValueError("positive batch size and sufficient shuffle buffer required")


@dataclass(frozen=True)
class Sample:
    value: PositionFeatures
    label: float
    weight: float
    game_id: str = ""

    def __post_init__(self):
        if not math.isfinite(self.label) or not 0 <= self.label <= 1:
            raise ValueError("White WDL target must be in [0,1]")
        if not math.isfinite(self.weight) or self.weight <= 0:
            raise ValueError("sample weight must be finite and positive")

    @classmethod
    def from_record(cls, record: dict) -> "Sample":
        cells, side, _ = mailbox_from_fen(record["fen"])
        return cls(features(cells, side), float(record["white_label"]), float(record["weight"]), record["game_id"])


@dataclass
class TrainingState:
    initial: Model
    values: list[float] = field(default_factory=list)
    optimizer_steps: int = 0

    def __post_init__(self):
        if not self.values:
            self.values = list(map(float, self.initial.coefficients))
        self.validate()

    def validate(self):
        if len(self.values) != 19 or any(not math.isfinite(v) for v in self.values):
            raise ValueError("nineteen finite float64 parameters required")
        if type(self.optimizer_steps) is not int or self.optimizer_steps < 0:
            raise ValueError("nonnegative optimizer step counter required")
        for index, value in enumerate(self.values):
            if index not in TRAINABLE and value != self.initial.coefficients[index]:
                raise ValueError("fixed material/ordering coefficients changed")

    def parameter_bytes(self) -> bytes:
        self.validate()
        return struct.pack("<19d", *self.values)

    def parameter_sha256(self) -> str:
        return sha256(self.parameter_bytes()).hexdigest()

    def export(self, *, model_id: str | None = None) -> Model:
        self.validate()
        return self.initial.with_trainable([self.values[i] for i in TRAINABLE], model_id=model_id)


def sigmoid(value: float) -> float:
    if value >= 0:
        return 1.0 / (1.0 + math.exp(-value))
    exp_value = math.exp(value)
    return exp_value / (1.0 + exp_value)


def relaxed_score(values: Sequence[float], feature: PositionFeatures) -> tuple[float, tuple[float, ...]]:
    """Return relaxed white score and d(score)/d(the nineteen coefficients)."""
    material = sum(a * b for a, b in zip(feature.material, values[:5]))
    activity = sum(a * b for a, b in zip(feature.centers, values[5:11])) + feature.pawn_advance * values[11]
    raw = material + activity + values[13] * activity * abs(activity) / 128.0 + feature.side * values[12]
    if not all(map(math.isfinite, (material, activity, raw))):
        raise ValueError("nonfinite relaxed inference before clamp")
    gradient = [0.0] * 19
    if -20000.0 < raw < 20000.0:
        activity_derivative = 1.0 + values[13] * abs(activity) / 64.0
        for index, count in enumerate(feature.centers, 5):
            gradient[index] = count * activity_derivative
        gradient[11] = feature.pawn_advance * activity_derivative
        gradient[12] = float(feature.side)
        gradient[13] = activity * abs(activity) / 128.0
    return min(20000.0, max(-20000.0, raw)), tuple(gradient)


def loss_gradient(state: TrainingState, samples: Sequence[Sample], config: TrainingConfig) -> tuple[float, tuple[float, ...]]:
    """Weighted MSE + lambda*sum((w-w0)^2), normalized by sample weights."""
    state.validate()
    if not samples:
        raise ValueError("nonempty batch required")
    total = math.fsum(sample.weight for sample in samples)
    gradient = [0.0] * 19
    losses = []
    for sample in samples:
        score, derivative = relaxed_score(state.values, sample.value)
        prediction = sigmoid(score / config.scale)
        residual = prediction - sample.label
        weight = sample.weight / total
        losses.append(weight * residual * residual)
        factor = weight * 2.0 * residual * prediction * (1.0 - prediction) / config.scale
        for index in TRAINABLE:
            gradient[index] += factor * derivative[index]
    regularization = 0.0
    for index in TRAINABLE:
        difference = state.values[index] - state.initial.coefficients[index]
        regularization += config.l2 * difference * difference
        gradient[index] += 2.0 * config.l2 * difference
    loss = math.fsum(losses) + regularization
    if not math.isfinite(loss) or any(not math.isfinite(v) for v in gradient):
        raise ValueError("nonfinite loss or gradient")
    return loss, tuple(gradient)


def optimizer_step(state: TrainingState, gradient: Sequence[float], config: TrainingConfig):
    """An actual SGD update. The production prepare path must not call this."""
    if len(gradient) != 19 or any(not math.isfinite(v) for v in gradient):
        raise ValueError("nineteen finite gradient values required")
    if any(gradient[index] != 0 for index in range(19) if index not in TRAINABLE):
        raise ValueError("gradient attempts to update fixed coefficients")
    updated = list(state.values)
    for index in TRAINABLE:
        updated[index] -= config.learning_rate * gradient[index]
    candidate = TrainingState(state.initial, updated, state.optimizer_steps + 1)
    state.values, state.optimizer_steps = candidate.values, candidate.optimizer_steps


def shuffled(samples: Iterable[Sample], rng: random.Random, buffer_size: int) -> Iterator[Sample]:
    buffer: list[Sample] = []
    for sample in samples:
        if len(buffer) < buffer_size:
            buffer.append(sample)
        else:
            index = rng.randrange(len(buffer))
            yield buffer[index]
            buffer[index] = sample
    rng.shuffle(buffer)
    yield from buffer


def train(state: TrainingState, samples: Callable[[], Iterable[Sample]], config: TrainingConfig, *, max_steps: int) -> dict:
    """Bounded real training loop; caller explicitly supplies a positive step limit."""
    if type(max_steps) is not int or max_steps <= 0:
        raise ValueError("actual training needs an explicit positive step limit")
    records, epoch = [], 0
    while len(records) < max_steps:
        batch: list[Sample] = []
        seen = 0
        for sample in shuffled(samples(), random.Random(config.seed + epoch), config.shuffle_buffer):
            seen += 1
            batch.append(sample)
            if len(batch) == config.batch_size:
                loss, gradient = loss_gradient(state, batch, config)
                optimizer_step(state, gradient, config)
                records.append({"step": state.optimizer_steps, "loss": loss, "samples": len(batch)})
                batch = []
                if len(records) == max_steps:
                    break
        if len(records) < max_steps and batch:
            loss, gradient = loss_gradient(state, batch, config)
            optimizer_step(state, gradient, config)
            records.append({"step": state.optimizer_steps, "loss": loss, "samples": len(batch)})
        if not seen:
            raise ValueError("training dataset is empty")
        epoch += 1
    return {"config": asdict(config), "optimizer_steps": state.optimizer_steps,
            "parameter_sha256": state.parameter_sha256(), "updates": records}


def prepare(state: TrainingState, samples: Sequence[Sample], config: TrainingConfig) -> dict:
    """Observe real forward/gradient/export at step zero with parameter bytes unchanged."""
    if state.optimizer_steps != 0 or state.values != list(map(float, state.initial.coefficients)):
        raise ValueError("preparation requires the unchanged hand-authored initial state")
    before = state.parameter_bytes()
    loss, gradient = loss_gradient(state, samples, config)
    integer_model = state.export()
    after = state.parameter_bytes()
    if before != after or state.optimizer_steps != 0 or integer_model.coefficients != state.initial.coefficients:
        raise RuntimeError("prepare changed production parameters")
    return {"mode": "prepare-only", "optimizer_steps": 0, "parameters_unchanged": True,
            "parameter_sha256_before": sha256(before).hexdigest(),
            "parameter_sha256_after": sha256(after).hexdigest(),
            "initial_coefficient_sha256": state.initial.coefficient_sha256(),
            "export_coefficient_sha256": integer_model.coefficient_sha256(),
            "samples": len(samples), "loss": loss, "gradient": list(gradient),
            "finite_loss_gradient": True, "config": asdict(config),
            "objective": "weighted-mse(sigmoid(clamp(relaxed-E19)/scale),white-WDL)+l2*sum((w-w0)^2)",
            "integer_bounds": integer_model.bounds(), "trained_model": False}


def shard_samples(path: Path) -> Iterator[Sample]:
    with Path(path).open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield Sample.from_record(json.loads(line))
