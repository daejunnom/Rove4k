"""Pure storage-domain/admission checks; no native compiler or engine runs.

These checks independently model logical path addresses and all legal 0x88
history addresses. Actual search/runtime and whole-file cost remain separate.
"""
import importlib.util
from pathlib import Path
import random
import sys
import unittest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


STORAGE = load("D_storage_projection", HERE / "storage.py")
SOURCE = load("D_storage_source", HERE / "source.py")


def dense_index(q):
    return (q + (q & 7)) >> 1


def old_window(flat, half):
    """Logical histories: prior same-side visits since irreversible move."""
    current = len(flat) - 1
    return [(i, value) for i, value in reversed(list(enumerate(flat)))
            if max(0, current - half) <= i < current and (current - i) % 2 == 0]


def shared_window(prefix, path, ply, half):
    length = len(prefix) + ply
    end = max(0, length - 1 - half)
    return [(i, prefix[i] if i < len(prefix) else path[i - len(prefix)])
            for i in range(length - 3, end - 1, -2)]


class DStorage(unittest.TestCase):
    def test_complete_source_cohorts_and_full_inverse(self):
        api = SOURCE.production()
        for profile_name in ("test-p4", "test-p28", "tcec-provisional"):
            for equivalent in (False, True):
                files, _ = SOURCE.prepare(api.resource_profile(profile_name), equivalent_edits=equivalent)
                for prefix in (False, True):
                    for dense in (False, True):
                        with self.subTest(profile=profile_name, equivalent=equivalent, prefix=prefix, dense=dense):
                            transformed, proof = STORAGE.transform(files, prefix=prefix, dense=dense)
                            self.assertEqual(STORAGE.restore(transformed, proof), files)
                            for name in ("runtime.c", "board.c", "start.S", "image.ld"):
                                self.assertEqual(transformed[name], files[name])
                            if prefix:
                                self.assertNotIn(b"w->length", transformed["search.c"])
                                self.assertNotIn(b"memcpy(w->keys,game_keys", transformed["search.c"])
                                self.assertIn(b"w->keys[ply]=q.h;", transformed["search.c"])
                            if dense:
                                self.assertIn(b"history[64][64]", transformed["tiny.h"])

    def test_input_and_output_complements_are_not_relaxed(self):
        files, _ = SOURCE.prepare(SOURCE.production().resource_profile("test-p4"))
        mutated = dict(files)
        mutated["runtime.c"] += b"\n"
        with self.assertRaisesRegex(ValueError, "exact complete scalar D profile cohort"):
            STORAGE.transform(mutated)
        injected = dict(files, **{"other.c": b"int other;\n"})
        with self.assertRaisesRegex(ValueError, "exact complete scalar D profile cohort"):
            STORAGE.transform(injected)
        transformed, proof = STORAGE.transform(files)
        transformed["image.ld"] += b"\n"
        with self.assertRaisesRegex(ValueError, "complete storage output cohort"):
            STORAGE.restore(transformed, proof)
        with self.assertRaisesRegex(ValueError, "explicit Boolean"):
            STORAGE.transform(files, prefix=1)

    def test_all_square_pairs_and_persistent_history_addresses(self):
        squares = [rank * 16 + file for rank in range(8) for file in range(8)]
        self.assertEqual([dense_index(q) for q in squares], list(range(64)))
        for source in squares:
            for target in squares:
                self.assertEqual(dense_index(source) * 64 + dense_index(target),
                                 ((source // 16) * 8 + source % 16) * 64 +
                                 (target // 16) * 8 + target % 16)
        rng = random.Random(20261025)
        sparse, dense = [0] * (128 * 128), [0] * (64 * 64)
        # Arbitrary signed writes model storage, independently of unchanged learn().
        for _ in range(20000):
            source, target = rng.choice(squares), rng.choice(squares)
            value = rng.randint(-32768, 32767)
            sparse[source * 128 + target] = value
            dense[dense_index(source) * 64 + dense_index(target)] = value
            self.assertEqual(sparse[source * 128 + target],
                             dense[dense_index(source) * 64 + dense_index(target)])
        for source in squares:
            for target in squares:
                self.assertEqual(sparse[source * 128 + target],
                                 dense[dense_index(source) * 64 + dense_index(target)])

    def test_prefix_boundary_halfmove_and_parity_windows(self):
        rng = random.Random(20261025)
        for length in (1, 2, 3, 6, 4095, 4096):
            prefix = [rng.randrange(11) for _ in range(length)]
            stale_path = [rng.randrange(11) for _ in range(128)]
            for ply in (0, 1, 2, 3, 64, 126, 127):
                flat = prefix + stale_path[:ply]
                for half in (0, 1, 2, 3, 99, 100, 4096, 99999):
                    with self.subTest(length=length, ply=ply, half=half):
                        old = old_window(flat, half)
                        new = shared_window(prefix, stale_path, ply, half)
                        self.assertEqual(new, old)
                        self.assertEqual(sum(v == flat[-1] for _, v in new),
                                         sum(v == flat[-1] for _, v in old))
                        self.assertTrue(all(i < length or i - length < ply for i, _ in new))

    def test_research_cancel_and_next_go_ignore_stale_tail(self):
        rng = random.Random(20261025)
        private = [0xDEAD] * 128
        visits = 0
        for game_length in (1, 7, 4096):
            prefix = [rng.randrange(23) for _ in range(game_length)]
            flat = list(prefix)

            def visit(ply, depth):
                nonlocal visits
                visits += 1
                half = rng.choice((0, 1, 2, 100, 99999))
                self.assertEqual(shared_window(prefix, private, ply, half), old_window(flat, half))
                if not depth or rng.randrange(13) == 0:
                    return  # cancellation leaves deeper private slots untouched
                for _ in range(2):
                    child = rng.randrange(23)
                    private[ply] = child
                    flat.append(child)
                    visit(ply + 1, depth - 1)
                    visit(ply + 1, depth - 1)  # PVS re-search: same pushed child
                    flat.pop()
                    self.assertEqual(shared_window(prefix, private, ply, half), old_window(flat, half))

            visit(0, 5)
            self.assertEqual(flat, prefix)
            # A new GO at root reads no stale private slot from the prior tree.
            self.assertEqual(shared_window(prefix, private, 0, 99999), old_window(prefix, 99999))
        self.assertGreater(visits, 100)


if __name__ == "__main__":
    unittest.main()
