#!/usr/bin/env python3
"""Explicit future training entry; not invoked by production preparation.

The current task stops before this command. An explicit positive --steps and
new model ID are required; all outputs remain candidates outside Git.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.dont_write_bytecode = True
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from engines.model.e19 import DEFAULT_MODEL, Model
from engines.training.e19.fetch_data import external_output
from engines.training.e19.prepare import validate_dataset
from engines.training.e19.trainer import TrainingConfig, TrainingState, shard_samples, train


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--steps", type=int, required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--holdout-sha256", required=True)
    args = parser.parse_args()
    if args.steps <= 0:
        parser.error("--steps must be positive; use prepare.py for production step zero")
    model = Model.load(args.model)
    if args.model_id == model.model_id:
        parser.error("an explicit new model ID is required")
    dataset, proof = validate_dataset(args.dataset, expected_holdout_sha256=args.holdout_sha256)
    out = external_output(args.out)
    out.mkdir(parents=True)
    config = TrainingConfig()
    state = TrainingState(model)
    report = {"format": 1, "kind": "e19-training-candidate", "complete": False,
              "dataset": proof, "config": asdict(config), "submission_qualified": False,
              "integer_consumer_qualified": False, "strength_qualified": False}
    try:
        report["training"] = train(state, lambda: shard_samples(Path(dataset["shards"]["train"]["path"])), config, max_steps=args.steps)
        exported = state.export(model_id=args.model_id)
        exported = replace(exported, provenance=f"offline SGD candidate; optimizer_steps={state.optimizer_steps}; unqualified")
        (out / "model.json").write_bytes(exported.canonical_bytes())
        (out / "model19.h").write_bytes(exported.render_model_fragment())
        report["export"] = {"model_id": exported.model_id, "coefficient_sha256": exported.coefficient_sha256(),
                            "bounds": exported.bounds()}
        report["complete"] = True
        return 0
    except Exception as error:
        report["error"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        report["optimizer_steps"] = state.optimizer_steps
        report["parameters"] = state.values
        report["parameter_sha256"] = state.parameter_sha256()
        (out / "training.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
