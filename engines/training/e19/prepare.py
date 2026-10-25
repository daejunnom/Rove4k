#!/usr/bin/env python3
"""Bind real corpus, canonical E19 and actual shipping consumers at step zero.

Generated model/render/receipts are external build artifacts. This command
performs a forward/gradient smoke and exact current integer export; it never
calls the optimizer or overwrites a source model or shipping recipe.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
from hashlib import sha256
import itertools
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.dont_write_bytecode = True
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from engines.model.e19 import DEFAULT_MODEL, Model
from engines.training.e19.trainer import Sample, TrainingConfig, TrainingState, prepare
from engines.training.e19.fetch_data import CORPUS, external_output, sha256_file


def _file_pin(path: Path) -> dict:
    path = Path(path).resolve()
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def validate_dataset(path: Path, *, expected_holdout_sha256: str) -> tuple[dict, dict]:
    """Recheck concrete input bytes, not a stored data_ready boolean alone."""
    from engines.training.e19.data import FILTERS, load_holdout
    if not re.fullmatch(r"[0-9a-f]{64}", expected_holdout_sha256):
        raise ValueError("independently supplied league holdout SHA-256 is required")
    path = Path(path).resolve()
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("format") != 1 or manifest.get("kind") != "e19-wdl-dataset":
        raise ValueError("real E19 dataset manifest required")
    if manifest.get("complete") is not True or manifest.get("data_ready") is not True:
        raise ValueError("dataset is incomplete or not qualified as real corpus")
    if manifest.get("training_updates") != 0 or manifest.get("filters") != FILTERS:
        raise ValueError("dataset filters/training state differ")
    if manifest.get("seed") != 20261025 or manifest.get("max_games") != 50000:
        raise ValueError("production preparation requires the agreed seed/game cap")
    expected = {row["sha256"]: row for row in CORPUS.values()}
    sources = manifest.get("sources", [])
    if len(sources) != 2 or {row.get("sha256") for row in sources} != set(expected):
        raise ValueError("both complete frozen monthly CC0 archives are required")
    for source in sources:
        frozen = expected[source["sha256"]]
        actual = Path(source["path"])
        if actual.name != frozen["filename"] or actual.is_symlink():
            raise ValueError("public corpus path differs")
        if source.get("kind") != "lichess-standard-rated-cc0" or source.get("license") != "CC0-1.0" or source.get("url") != frozen["url"]:
            raise ValueError("public corpus provenance differs")
        if sha256_file(actual) != source["sha256"] or actual.stat().st_size != source["bytes"]:
            raise ValueError("public corpus bytes changed after preparation")
    holdout = manifest.get("holdout", {})
    _, actual_holdout = load_holdout(Path(holdout["path"]), expected_sha256=expected_holdout_sha256)
    if actual_holdout != holdout or actual_holdout.get("verified") is not True:
        raise ValueError("actual league holdout differs")
    for name in ("data.py", "fetch_data.py", "requirements.txt"):
        producer = manifest.get("producer", {}).get(name)
        if not producer or sha256_file(Path(producer["path"])) != producer["sha256"]:
            raise ValueError("frozen dataset producer input changed")
        if sha256_file(Path(__file__).with_name(name)) != producer["sha256"]:
            raise ValueError("dataset producer differs from the current admitted preparation code")
    shards = manifest.get("shards", {})
    if set(shards) != {"train", "validation", "test"}:
        raise ValueError("all three frozen dataset splits are required")
    shard_pins = {}
    for split, row in shards.items():
        actual = Path(row["path"])
        if actual.is_symlink() or actual.resolve() != path.parent / (split + ".jsonl"):
            raise ValueError("dataset shard escaped its owned directory")
        if row.get("rows", 0) <= 0 or row.get("games", 0) <= 0 or row.get("families", 0) <= 0:
            raise ValueError("dataset split lacks retained real observations")
        pin = _file_pin(actual)
        if pin["sha256"] != row["sha256"] or pin["bytes"] != row["bytes"]:
            raise ValueError("dataset shard changed after preparation")
        shard_pins[split] = pin
    return manifest, {"manifest": _file_pin(path), "archives_rechecked": True,
                      "producer_snapshots_rechecked": True, "holdout": actual_holdout,
                      "shards": shard_pins}


def export_baseline(state: TrainingState, out: Path) -> dict:
    model = state.export()
    raw = model.canonical_bytes()
    (out / "model.json").write_bytes(raw)
    fragment = model.render_model_fragment()
    (out / "model19.h").write_bytes(fragment)
    physical = ("static const int16_t e19_physical[21]={" + ",".join(map(str, model.physical_coefficients())) + "};\n").encode()
    (out / "physical21.c.inc").write_bytes(physical)
    return {"model_id": model.model_id, "model_json_sha256": sha256(raw).hexdigest(),
            "coefficient_sha256": model.coefficient_sha256(),
            "readable_fragment_sha256": sha256(fragment).hexdigest(),
            "physical_fragment_sha256": sha256(physical).hexdigest(), "trained_model": False,
            "integer_bounds": model.bounds()}


def audit_dataset_shards(dataset: dict) -> dict:
    """Walk retained real records once for split/weight integrity and distributions."""
    from engines.training.e19.data import family_id, load_holdout, split_for_family
    holdout, _ = load_holdout(Path(dataset["holdout"]["path"]), expected_sha256=dataset["holdout"]["expected_sha256"])
    all_positions: set[bytes] = set()
    all_games: dict[str, tuple[str, str, float]] = {}
    distributions = {}
    material_units = {"n": 320, "b": 330, "r": 500, "q": 900}
    for split in ("test", "validation", "train"):
        row_count = 0
        games: dict[str, list] = {}
        families = set()
        side, ply_bucket, piece_count, pawn_count, nonpawn_count, phase, labels = (Counter() for _ in range(7))
        with Path(dataset["shards"][split]["path"]).open(encoding="utf-8") as stream:
            for line in stream:
                record = json.loads(line)
                if record.get("split") != split or record.get("white_label") not in (0.0, 0.5, 1.0):
                    raise ValueError("retained split or White WDL target differs")
                label, game_id = record["white_label"], record["game_id"]
                family = family_id(record["moves"])
                if family != record["family_id"] or family in holdout or split_for_family(family, dataset["seed"]) != split:
                    raise ValueError("retained family split or league holdout exclusion differs")
                identity = (split, family, label)
                if game_id in all_games and all_games[game_id] != identity:
                    raise ValueError("one game crosses splits, families or WDL labels")
                all_games[game_id] = identity
                fen_fields = record["fen"].split()
                if len(fen_fields) != 6 or fen_fields[1] not in ("w", "b"):
                    raise ValueError("retained standard FEN differs")
                key = sha256(" ".join(fen_fields[:4]).encode()).digest()
                if key.hex() != record["position_key"] or key in all_positions:
                    raise ValueError("retained position duplicate or normalized position key differs")
                all_positions.add(key)
                ply = record["ply"]
                if type(ply) is not int or not 24 <= ply <= 160 or len(record["moves"]) != ply or fen_fields[1] != ("w" if ply % 2 == 0 else "b"):
                    raise ValueError("retained ply, full prefix or side-to-move differs")
                weight = record["weight"]
                if not math.isfinite(weight) or weight <= 0:
                    raise ValueError("retained sample weight differs")
                if game_id not in games:
                    games[game_id] = [0, 0.0, label]
                games[game_id][0] += 1
                games[game_id][1] += weight
                if games[game_id][0] > 16:
                    raise ValueError("retained game exceeds its 16-position cap")
                pieces = [char for char in fen_fields[0] if char.isalpha()]
                if any(char not in "PNBRQKpnbrqk" for char in pieces) or max(sum(char.isupper() for char in pieces), sum(char.islower() for char in pieces)) > 16:
                    raise ValueError("retained piece domain differs")
                pawns = sum(char.lower() == "p" for char in pieces)
                nonpawns = sum(char.lower() in material_units for char in pieces)
                nonpawn_material = sum(material_units.get(char.lower(), 0) for char in pieces)
                side[fen_fields[1]] += 1
                ply_bucket["24-39" if ply < 40 else "40-79" if ply < 80 else "80-119" if ply < 120 else "120-160"] += 1
                piece_count[str(len(pieces))] += 1
                pawn_count[str(pawns)] += 1
                nonpawn_count[str(nonpawns)] += 1
                phase["high>=4800" if nonpawn_material >= 4800 else "medium>=2400" if nonpawn_material >= 2400 else "low<2400"] += 1
                labels[str(float(label))] += 1
                families.add(family)
                row_count += 1
        if any(abs(row[1] - 1.0) > 1e-12 for row in games.values()):
            raise ValueError("retained game sample weights do not total one")
        declared = dataset["shards"][split]
        if (row_count, len(games), len(families), dict(labels)) != (declared["rows"], declared["games"], declared["families"], declared["labels"]):
            raise ValueError("retained split observations differ from dataset manifest")
        game_labels = Counter(str(float(row[2])) for row in games.values())
        distributions[split] = {"rows": row_count, "games": len(games), "families": len(families),
                                "white_wdl_position_counts": dict(labels), "white_wdl_game_counts": dict(game_labels),
                                "side_to_move": dict(side), "ply_buckets": dict(ply_bucket),
                                "total_piece_counts": dict(piece_count), "pawn_counts": dict(pawn_count),
                                "nonpawn_piece_counts": dict(nonpawn_count), "material_phase": dict(phase)}
    return {"complete": True, "positions": len(all_positions), "games": len(all_games),
            "game_splits_disjoint": True, "normalized_positions_unique": True,
            "league_holdout_excluded": True, "per_game_total_weight": 1.0,
            "material_phase_definition": "total both-color N=320,B=330,R=500,Q=900; coarse preparation diagnostic, not engine strength",
            "splits": distributions}


def prepare_training(dataset_path: Path, shipping_source: Path, out: Path, *, model_path: Path = DEFAULT_MODEL,
                     expected_holdout_sha256: str, cc: str = "cc", config: TrainingConfig = TrainingConfig()) -> dict:
    out = external_output(out)
    out.mkdir(parents=True)
    result = {"format": 1, "kind": "e19-training-preparation", "complete": False,
              "trainer_ready": False, "production_optimizer_steps": 0,
              "trained_model": False, "config": asdict(config)}

    def save():
        (out / "preparation.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    save()
    try:
        model = Model.load(model_path)
        dataset, dataset_proof = validate_dataset(dataset_path, expected_holdout_sha256=expected_holdout_sha256)
        result["dataset"] = dataset_proof
        result["data_audit"] = audit_dataset_shards(dataset)
        result["model_input"] = _file_pin(Path(model_path))
        result["shipping_source"] = _file_pin(Path(shipping_source))
        result["implementation"] = {name: _file_pin(Path(__file__).with_name(name))
                                    for name in ("prepare.py", "trainer.py", "train.py", "check_consumer.py")}
        result["implementation"]["e19.py"] = _file_pin(ROOT / "engines/model/e19.py")
        snapshots = out / "inputs"
        snapshots.mkdir()
        snapshot_paths = {name: Path(row["path"]) for name, row in result["implementation"].items()}
        snapshot_paths.update({"e19.json": Path(model_path), "shipping.c": Path(shipping_source),
                               "dataset.json": Path(dataset_path)})
        result["input_snapshots"] = {}
        for name, path in snapshot_paths.items():
            destination = snapshots / name
            destination.write_bytes(path.read_bytes())
            result["input_snapshots"][name] = _file_pin(destination)
        records = []
        with Path(dataset["shards"]["train"]["path"]).open(encoding="utf-8") as stream:
            for line in itertools.islice((line for line in stream if line.strip()), config.batch_size):
                records.append(json.loads(line))
        samples = [Sample.from_record(row) for row in records]
        if len(samples) != config.batch_size:
            raise ValueError("real training shard lacks a complete smoke batch")
        result["real_batch"] = {"count": len(samples), "game_count": len({row.game_id for row in samples}),
                                "records_sha256": sha256(json.dumps(records, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}
        state = TrainingState(model)
        result["forward_gradient"] = prepare(state, samples, config)
        result["integer_export"] = export_baseline(state, out)
        from engines.training.e19.check_consumer import check_actual_consumer
        result["actual_consumer"] = check_actual_consumer(Path(shipping_source), out / "actual-consumer", model=model,
                                                         cc=cc, additional_fens=[row["fen"] for row in records[:32]])
        if result["actual_consumer"].get("complete") is not True:
            raise ValueError("actual shipping inference/ordering consumer did not pass")
        if state.optimizer_steps != 0 or state.values != list(map(float, model.coefficients)):
            raise RuntimeError("production state changed during preparation")
        result["data_ready"] = True
        result["parameters_unchanged"] = True
        result["complete"] = True
        result["trainer_ready"] = True
        result["submission_qualified"] = False
        result["qualification_scope"] = "real-data/model/loss/gradient/export/actual-consumer preparation; no optimizer update, strength or submission qualification"
        save()
        return result
    except Exception as error:
        result["error"] = {"type": type(error).__name__, "message": str(error)}
        save()
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--shipping-source", type=Path, required=True)
    parser.add_argument("--holdout-sha256", required=True, help="SHA-256 supplied by the independent league bank producer")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cc", default="cc")
    args = parser.parse_args()
    result = prepare_training(args.dataset, args.shipping_source, args.out, model_path=args.model,
                              expected_holdout_sha256=args.holdout_sha256, cc=args.cc)
    print(json.dumps({"complete": result["complete"], "trainer_ready": result["trainer_ready"],
                      "production_optimizer_steps": result["production_optimizer_steps"], "out": str(args.out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
