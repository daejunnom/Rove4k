"""Corpus tests use explicit fixtures, never claim real-data readiness."""
import io
import hashlib
import json
from pathlib import Path
import random
import tempfile
import unittest

import chess
import chess.pgn

import data


def legal_game(seed, prefix=(), plies=48, label="1-0", name=None):
    generator = random.Random(seed)
    board = chess.Board()
    game = chess.pgn.Game()
    game.headers.update(White=name or f"White{seed}", Black=f"Black{seed}", WhiteElo="1800", BlackElo="1900", TimeControl="180+0", Result=label)
    node = game
    seen = set()
    for value in prefix:
        move = chess.Move.from_uci(value)
        assert move in board.legal_moves
        node = node.add_variation(move)
        board.push(move)
    while board.ply() < plies:
        choices = []
        for move in sorted(board.legal_moves, key=lambda value: value.uci()):
            board.push(move)
            position = " ".join(board.fen(en_passant="legal").split()[:4])
            if not board.is_game_over() and position not in seen:
                choices.append((move, position))
            board.pop()
        if not choices:
            raise AssertionError("fixture failed to reach the requested legal length")
        move, position = generator.choice(choices)
        seen.add(position)
        node = node.add_variation(move)
        board.push(move)
    return game


def parsed(game):
    return chess.pgn.read_game(io.StringIO(str(game)), Visitor=data._CorpusBuilder)


class CorpusPreparation(unittest.TestCase):
    def test_bounded_concatenated_archive_with_multimegabyte_window(self):
        import zstandard
        body = (str(legal_game(7)) + "\n{" + "archive comment " * 100000 + "}\n").encode()
        compressor = zstandard.ZstdCompressor(write_content_size=False)
        frame = compressor.compress(body)
        self.assertGreater(zstandard.get_frame_parameters(frame).window_size, 256 * 1024)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "fixture.pgn.zst"
            path.write_bytes(compressor.compress(b" \n") + frame)
            with data.open_pgn(path) as source:
                self.assertEqual(source.read(), " \n" + body.decode())

    def test_header_filters_and_optional_metadata(self):
        game = legal_game(1)
        game.headers.pop("Date", None)
        game.headers.pop("Round", None)
        row, reason = data.game_record(parsed(game), "fixture", 1, data.SEED, set())
        self.assertIsNone(reason)
        self.assertTrue(row["positions"])
        for field, value, expected in (("WhiteElo", "1599", "rating"), ("TimeControl", "60+0", "time_control"),
                                       ("SetUp", "1", "nonstandard_start"), ("Result", "*", "unfinished_or_invalid_result"),
                                       ("White", game.headers["Black"].upper(), "same_player")):
            with self.subTest(field=field):
                headers = dict(game.headers)
                headers[field] = value
                self.assertEqual(data.header_rejection(headers), expected)
        self.assertIsNone(data.header_rejection(dict(game.headers, TimeControl="60+3")))

    def test_parser_error_is_rejected(self):
        text = '[White "A"]\n[Black "B"]\n[WhiteElo "1800"]\n[BlackElo "1800"]\n[TimeControl "300+0"]\n[Result "1-0"]\n\n1. e5 e5 1-0\n'
        game = chess.pgn.read_game(io.StringIO(text), Visitor=data._CorpusBuilder)
        self.assertTrue(game.errors)
        self.assertEqual(data.game_record(game, "fixture", 1, data.SEED, set())[1], "pgn_parse_error")

    def test_header_and_movetext_result_disagreement_is_rejected(self):
        text = str(legal_game(8))
        index = text.rfind("1-0")
        text = text[:index] + "0-1" + text[index + 3:]
        game = chess.pgn.read_game(io.StringIO(text), Visitor=data._CorpusBuilder)
        self.assertTrue(any("results disagree" in str(error) for error in game.errors))
        self.assertEqual(data.game_record(game, "fixture", 1, data.SEED, set())[1], "pgn_parse_error")

    def test_legal_move_after_result_is_rejected(self):
        original = legal_game(9)
        board = original.end().board()
        following = board.san(next(iter(board.legal_moves)))
        game = chess.pgn.read_game(io.StringIO(str(original) + " " + following + " 1-0\n"), Visitor=data._CorpusBuilder)
        self.assertTrue(any("move after" in str(error) for error in game.errors))
        self.assertEqual(data.game_record(game, "fixture", 1, data.SEED, set())[1], "pgn_parse_error")

    def test_missing_movetext_result_is_rejected(self):
        text = str(legal_game(10))
        index = text.rfind("1-0")
        game = chess.pgn.read_game(io.StringIO(text[:index]), Visitor=data._CorpusBuilder)
        self.assertTrue(any("missing its movetext result" in str(error) for error in game.errors))
        self.assertEqual(data.game_record(game, "fixture", 1, data.SEED, set())[1], "pgn_parse_error")

    def test_real_holdout_moves_are_required(self):
        game = legal_game(2)
        moves = [move.uci() for move in game.mainline_moves()]
        family = data.family_id(moves)
        self.assertEqual(data.game_record(game, "fixture", 1, data.SEED, {family})[1], "league_holdout_family")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "holdout.json"
            path.write_text(json.dumps({"openings": [{"moves": moves[:8], "family": family}]}))
            families, receipt = data.load_holdout(path)
            self.assertEqual(families, {family})
            self.assertFalse(receipt["verified"])
            source = {"url": "https://github.com/lichess-org/chess-openings", "revision": data.OPENING_REVISION,
                      "sha256": "a" * 64, "license": "CC0-1.0", "verified": True}
            path.write_text(json.dumps({"source": source, "openings": [{"moves": moves[:8], "family": family}]}))
            self.assertFalse(data.load_holdout(path)[1]["verified"])
            with self.assertRaisesRegex(ValueError, "independently supplied"):
                data.load_holdout(path, expected_sha256="0" * 64)
            self.assertTrue(data.load_holdout(path, expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest())[1]["verified"])
            source["url"] += "-other"
            path.write_text(json.dumps({"source": source, "openings": [{"moves": moves[:8], "family": family}]}))
            self.assertFalse(data.load_holdout(path, expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest())[1]["verified"])
            path.write_text(json.dumps({"openings": [{"moves": ["e2e5"] * 8}]}))
            with self.assertRaisesRegex(ValueError, "illegal"):
                data.load_holdout(path)

    def test_deterministic_selection_and_no_false_fixture_readiness(self):
        games = []
        found = set()
        for seed in range(100):
            game = legal_game(seed)
            family = data.family_id([move.uci() for move in game.mainline_moves()])
            split = data.split_for_family(family)
            if split not in found:
                games.append(game)
                found.add(split)
            if len(found) == 3:
                break
        self.assertEqual(found, {"train", "validation", "test"})
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            pgn = base / "fixture.pgn"
            pgn.write_text("\n\n".join(map(str, games)) + "\n", encoding="utf-8")
            first = data.prepare_dataset([pgn], None, base / "first")
            second = data.prepare_dataset([pgn], None, base / "second")
            self.assertTrue(first["complete"])
            self.assertTrue(first["pipeline_ready"])
            self.assertFalse(first["data_ready"])
            keys, game_splits, weights = set(), {}, {}
            for split in data.PRIORITY:
                self.assertEqual(first["shards"][split]["sha256"], second["shards"][split]["sha256"])
                for line in Path(first["shards"][split]["path"]).read_text().splitlines():
                    row = json.loads(line)
                    self.assertNotIn(row["position_key"], keys)
                    keys.add(row["position_key"])
                    self.assertEqual(game_splits.setdefault(row["game_id"], split), split)
                    weights[row["game_id"]] = weights.get(row["game_id"], 0) + row["weight"]
                    board = chess.Board()
                    for value in row["moves"]:
                        board.push_uci(value)
                    self.assertEqual(board.fen(en_passant="legal"), row["fen"])
                    self.assertGreaterEqual(row["ply"], 24)
                    self.assertLessEqual(row["ply"], 160)
            self.assertTrue(all(abs(weight - 1) < 1e-12 for weight in weights.values()))

    def test_cross_family_transposition_prefers_test_over_train(self):
        first = "g1f3 g8f6 b1c3 b8c6 e2e4 e7e5 d2d4 d7d5".split()
        second = "b1c3 b8c6 g1f3 g8f6 e2e4 e7e5 d2d4 d7d5".split()
        seed = next(value for value in range(10000)
                    if data.split_for_family(data.family_id(first), value) == "train"
                    and data.split_for_family(data.family_id(second), value) == "test")
        game_a = legal_game(50, first, plies=40, name="A")
        game_b = legal_game(50, second, plies=40, name="B")
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            pgn = base / "transpositions.pgn"
            pgn.write_text(str(game_a) + "\n\n" + str(game_b) + "\n")
            report = data.prepare_dataset([pgn], None, base / "dataset", seed=seed)
            train_rows = [json.loads(line) for line in Path(report["shards"]["train"]["path"]).read_text().splitlines()]
            test_rows = [json.loads(line) for line in Path(report["shards"]["test"]["path"]).read_text().splitlines()]
            self.assertEqual(len(test_rows), 16)
            self.assertGreater(report["counts"]["duplicate_positions"], 0)
            self.assertFalse({row["position_key"] for row in train_rows} & {row["position_key"] for row in test_rows})

    def test_named_official_archive_cannot_be_a_fixture(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / next(iter(data.CORPUS.values()))["filename"]
            path.write_bytes(b"fixture")
            with self.assertRaisesRegex(ValueError, "frozen complete archive"):
                data.corpus_source(path)


if __name__ == "__main__":
    unittest.main()
