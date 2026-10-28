"""Independent expected SAN and ordered opening-PGN binding tests."""
import hashlib
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

try:
    from . import opening_pgn, run
except ImportError:
    import opening_pgn
    import run


def row(name, eco, moves):
    return {"id": name, "eco": eco, "moves": moves.split()}


def game(name, eco, moves):
    return (f'[Event "Rove4k {name}"]\n[ECO "{eco}"]\n[Result "*"]\n\n'
            + moves + ' *\n').encode('ascii')


class CanonicalOpeningPgnTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules = run.rules_module()

    def test_standard_start_castling_en_passant_and_promotion(self):
        rows = [
            row('castle', 'C60', 'e2e4 e7e5 g1f3 b8c6 f1b5 a7a6 b5a4 g8f6 e1g1'),
            row('ep', 'B00', 'e2e4 a7a6 e4e5 d7d5 e5d6'),
            row('promotion', 'A00', 'a2a4 h7h5 a4a5 h5h4 a5a6 h4h3 a6b7 h3g2 b7a8q'),
        ]
        expected = b'\n'.join([
            game('castle', 'C60', '1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O'),
            game('ep', 'B00', '1. e4 a6 2. e5 d5 3. exd6'),
            game('promotion', 'A00', '1. a4 h5 2. a5 h4 3. a6 h3 4. axb7 hxg2 5. bxa8=Q'),
        ])
        self.assertEqual(opening_pgn.canonical(rows, self.rules), expected)
        self.assertIsNone(opening_pgn.validate(expected, rows, self.rules))

    def test_checkmate_san_and_terminal_opening_rejection(self):
        initial = 'e2e4 e7e5 d1h5 b8c6 f1c4 g8f6'.split()
        board = self.rules.Board.from_fen()
        for move in initial:
            board = board.play(move)
        san, after = opening_pgn._san(board, 'h5f7', self.rules)
        self.assertEqual(san, 'Qxf7#')
        self.assertTrue(after.in_check())
        self.assertFalse(list(after.legal_moves()))
        with self.assertRaisesRegex(ValueError, 'terminal'):
            opening_pgn.canonical([row('mate', 'C20', ' '.join(initial + ['h5f7']))], self.rules)

    def test_san_disambiguates_file_rank_and_both_by_legal_moves(self):
        cases = (
            ('4k3/8/8/8/8/8/8/1N2KN2 w - - 0 1', 'b1d2', 'Nbd2'),
            ('4k3/8/8/8/8/1N6/8/1N2K3 w - - 0 1', 'b1d2', 'N1d2'),
            ('4k3/8/8/8/8/1N6/8/1N2KN2 w - - 0 1', 'b1d2', 'Nb1d2'),
            # The e2 rook is pinned to its king: a pseudo-legal rival must
            # not force source-file disambiguation of the legal a2 rook.
            ('4r2k/8/8/8/8/8/R3R3/4K3 w - - 0 1', 'a2d2', 'Rd2'),
            ('k7/8/8/8/8/8/8/1R2K3 w - - 0 1', 'b1a1', 'Ra1+'),
            ('r6k/1P6/8/8/8/8/8/4K3 w - - 0 1', 'b7a8n', 'bxa8=N'),
            ('r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1', 'e1c1', 'O-O-O'),
        )
        for fen, move, expected in cases:
            with self.subTest(expected=expected):
                board = self.rules.Board.from_fen(fen)
                san, after = opening_pgn._san(board, move, self.rules)
                self.assertEqual(san, expected)
                self.assertEqual(after.fen(), board.play(move).fen())

    def test_mainline_index_reorder_missing_extra_and_variations_fail(self):
        rows = [row('first', 'C20', 'e2e4 e7e5'), row('second', 'D00', 'd2d4 d7d5')]
        one = game('first', 'C20', '1. e4 e5')
        two = game('second', 'D00', '1. d4 d5')
        opening_pgn.validate(one + b'\n' + two, rows, self.rules)
        bad = [two + b'\n' + one, one, one + b'\n' + two + b'\n' + two,
               (one + b'\n' + two).replace(b'1. e4 e5', b'1. e4 (1. d4) e5'),
               (one + b'\n' + two).replace(b'1. e4 e5', b'1. e4 {x} e5'),
               (one + b'\n' + two).replace(b'[Result "*"]', b'[FEN "bad"]', 1),
               (one + b'\n' + two).replace(b'1. e4 e5', b'1. e4 c5')]
        for raw in bad:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                opening_pgn.validate(raw, rows, self.rules)

    def test_illegal_uci_and_header_injection_are_rejected(self):
        for candidate in (
            row('x', 'C20', 'e2e5'),
            row('x"\n[FEN "bad', 'C20', 'e2e4'),
            row('valid', 'X99', 'e2e4'),
        ):
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                opening_pgn.canonical([candidate], self.rules)

    def test_repetition_length_and_duplicate_ids_are_rejected(self):
        cycle = 'g1f3 g8f6 f3g1 f6g8'
        # The third occurrence appears on the eighth ply; a later move must
        # not make the full PGN appear loaded by Fastchess.
        with self.assertRaisesRegex(ValueError, 'terminal'):
            opening_pgn.canonical([row('cycle', 'A00', cycle + ' ' + cycle + ' e2e4')], self.rules)
        sixteen = 'a2a3 a7a6 b2b3 b7b6 c2c3 c7c6 d2d3 d7d6 e2e3 e7e6 f2f3 f7f6 g2g3 g7g6 h2h3 h7h6'
        self.assertTrue(opening_pgn.canonical([row('sixteen', 'A00', sixteen)], self.rules))
        with self.assertRaisesRegex(ValueError, 'canonical bank format'):
            opening_pgn.canonical([row('seventeen', 'A00', sixteen + ' a1a2')], self.rules)
        with self.assertRaisesRegex(ValueError, 'unique'):
            opening_pgn.canonical([row('same', 'A00', 'e2e4'), row('same', 'D00', 'd2d4')], self.rules)

    @unittest.skipUnless(os.name == 'posix' and hasattr(os, 'O_NOFOLLOW') and hasattr(os, 'O_DIRECTORY'),
                         'POSIX no-follow required')
    def test_snapshot_pin_checks_length_and_hash_before_returning_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp).resolve() / 'bank.pgn'
            data = game('opening', 'C20', '1. e4 e5')
            path.write_bytes(data)
            pin = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
            snapshot = opening_pgn.read_snapshot(path, pin)
            self.assertEqual(snapshot, data)
            self.assertIsNone(opening_pgn.validate(snapshot, [row('opening', 'C20', 'e2e4 e7e5')], self.rules))
            # Wrong file length must be rejected before a stream can read.
            with patch.object(opening_pgn.os, 'fdopen', side_effect=AssertionError('unexpected read')):
                with self.assertRaisesRegex(ValueError, 'bounded ordinary'):
                    opening_pgn.read_snapshot(path, {**pin, 'bytes': len(data) + 1})
            with self.assertRaisesRegex(ValueError, 'snapshot differs'):
                opening_pgn.read_snapshot(path, {**pin, 'sha256': '0' * 64})

    @unittest.skipUnless(os.name == 'posix' and hasattr(os, 'O_NOFOLLOW') and hasattr(os, 'O_DIRECTORY'),
                         'POSIX no-follow required')
    def test_snapshot_rejects_leaf_parent_symlinks_and_hardlinks_before_read(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            real = root / 'real'
            real.mkdir()
            source = real / 'bank.pgn'
            source.write_bytes(b'opening')
            pin = {'bytes': 7, 'sha256': hashlib.sha256(b'opening').hexdigest()}
            leaf = root / 'leaf.pgn'
            leaf.symlink_to(source)
            directory = root / 'alias'
            directory.symlink_to(real, target_is_directory=True)
            hard = root / 'hard.pgn'
            os.link(source, hard)
            for candidate in (leaf, directory / 'bank.pgn', source, hard):
                with self.subTest(candidate=candidate), patch.object(opening_pgn.os, 'fdopen',
                        side_effect=AssertionError('unexpected read')):
                    with self.assertRaises((OSError, ValueError)):
                        opening_pgn.read_snapshot(candidate, pin)

    @unittest.skipUnless(os.name == 'posix' and hasattr(os, 'O_NOFOLLOW') and hasattr(os, 'O_DIRECTORY'),
                         'POSIX no-follow required')
    def test_snapshot_rejects_path_replacement_after_fd_read(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            path = root / 'bank.pgn'
            replacement = root / 'replacement.pgn'
            path.write_bytes(b'opening')
            replacement.write_bytes(b'opening')
            pin = {'bytes': 7, 'sha256': hashlib.sha256(b'opening').hexdigest()}
            original_stat = os.stat
            replaced = []

            def replace_before_final_stat(name, *args, **kwargs):
                if name == path.name and kwargs.get('dir_fd') is not None:
                    os.replace(replacement, path)
                    replaced.append(True)
                return original_stat(name, *args, **kwargs)

            with patch.object(opening_pgn.os, 'stat', side_effect=replace_before_final_stat) as fake_stat:
                with patch.object(opening_pgn.os, 'supports_dir_fd', os.supports_dir_fd | {fake_stat}):
                    with self.assertRaisesRegex(ValueError, 'identity changed'):
                        opening_pgn.read_snapshot(path, pin)
            self.assertEqual(replaced, [True])

    def test_unsupported_platform_rejects_bank_and_pgn_before_open(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp).resolve() / 'missing'
            pin = {'bytes': 1, 'sha256': '0' * 64}
            unsupported = SimpleNamespace(name='nt', open=lambda *args, **kwargs: self.fail('unexpected open'))
            with patch.object(opening_pgn, 'os', unsupported):
                with self.assertRaisesRegex(RuntimeError, 'no-follow'):
                    opening_pgn.read_snapshot(path, pin)
                with self.assertRaisesRegex(RuntimeError, 'no-follow'):
                    opening_pgn.read_bank(path, '0' * 64)
            if os.name == 'nt':
                # Also exercise the actual host platform, not just a fake OS.
                with patch.object(opening_pgn.os, 'open', side_effect=AssertionError('unexpected open')):
                    with self.assertRaisesRegex(RuntimeError, 'no-follow'):
                        opening_pgn.read_snapshot(path, pin)
                    with self.assertRaisesRegex(RuntimeError, 'no-follow'):
                        opening_pgn.read_bank(path, '0' * 64)


if __name__ == '__main__':
    unittest.main()
