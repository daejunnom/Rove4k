import copy
from pathlib import Path
import random
import unittest

from generate import FORMATS, MODEL_DIR, load_model, metadata, pack_weights, sources, static_consumer, unpack_weights
from prepare import transform_sources
from verify import validate_formats, validate_producer_metadata


class RepresentationTests(unittest.TestCase):
    def test_all_current_weights_and_independent_parameter_identity(self):
        model = load_model()
        weights = model["evaluation"]["weights"] + model["ordering"]["weights"]
        sizes = dict(zip(FORMATS, (26, 42, 26, 21, 17, 42)))
        hashes = set()
        for fmt in FORMATS:
            with self.subTest(format=fmt):
                packed = pack_weights(fmt, weights)
                self.assertEqual(len(packed), sizes[fmt])
                self.assertEqual(unpack_weights(fmt, packed), weights)
                hashes.add(metadata(fmt, model)["restored_i16le_sha256"])
                self.assertEqual(set(sources(fmt, model)), {"frozen.h", "frozen.rs"})
        self.assertEqual(len(hashes), 1)

    def test_extreme_signed_values_within_each_declared_format(self):
        rng = random.Random(20261020)
        for fmt in FORMATS:
            for _ in range(1000):
                if fmt in ("varint", "int16", "static16"):
                    weights = [rng.randint(-32768, 32767) for _ in range(21)]
                elif fmt == "split8":
                    weights = [rng.randint(-32768, 32767) for _ in range(5)] + [rng.randint(-128, 127) for _ in range(16)]
                else:
                    limit = 128 if fmt == "scaled8" else 32
                    weights = [10 * rng.randint(-128, 127) for _ in range(5)] + [rng.randrange(-limit, limit) for _ in range(16)]
                self.assertEqual(unpack_weights(fmt, pack_weights(fmt, weights)), weights)
        for fmt in ("scaled8", "scaled6"):
            weights = [-1280, 1270, -1280, 1270, 0] + [-32, 31] * 8
            self.assertEqual(unpack_weights(fmt, pack_weights(fmt, weights)), weights)

    def test_restricted_codecs_fail_on_unsupported_models_and_lengths(self):
        model = load_model()
        weights = model["evaluation"]["weights"] + model["ordering"]["weights"]
        for fmt in FORMATS:
            packed = pack_weights(fmt, weights)
            for invalid in (packed[:-1], packed + b"\0"):
                with self.subTest(format=fmt), self.assertRaises(ValueError):
                    unpack_weights(fmt, invalid)
        for fmt in ("scaled8", "scaled6"):
            for index, value in ((0, 101), (0, 1280), (0, -1290), (5, 128)):
                bad = weights.copy(); bad[index] = value
                with self.subTest(format=fmt, index=index, value=value), self.assertRaises(ValueError):
                    pack_weights(fmt, bad)
        bad = weights.copy(); bad[5] = 32
        with self.assertRaises(ValueError):
            pack_weights("scaled6", bad)

    def test_static_consumer_transform_is_explicit_and_rejects_unknown_inputs(self):
        for language in ("c", "rust"):
            with self.assertRaisesRegex(ValueError, "consumer contract changed"):
                static_consumer(language, "unknown source")

    def test_codegen_rejects_overflowing_inference_even_when_codec_could_store_it(self):
        model = copy.deepcopy(load_model())
        model["evaluation"]["weights"][:5] = [-32768, 32767, 32767, 32767, 32767]
        model["ordering"]["weights"] = [-32768] * 5
        for fmt in FORMATS:
            with self.subTest(format=fmt), self.assertRaisesRegex(ValueError, "overflow"):
                sources(fmt, model)

    def test_pure_source_transform_preserves_baseline_and_only_changes_named_consumers(self):
        model = load_model()
        for language, consumer in (("c", "c/model.h"), ("rust", "rust/eval.rs")):
            header = "frozen.h" if language == "c" else "frozen.rs"
            # C remains a production integration check. The Rust transform is
            # a generic model-format contract and owns a small independent
            # fixture, rather than importing the retired Rust engine.
            consumer_path = (MODEL_DIR.parent / consumer if language == "c" else
                             Path(__file__).with_name("fixtures") / "rust_consumer.rs.in")
            files = {"model/" + header: sources("varint", model)[header].replace("\n", "\r\n").encode(),
                     consumer: consumer_path.read_bytes(),
                     "unrelated/source": b"unchanged\r\n"}
            original = files.copy()
            baseline, base_metadata = transform_sources(files, representation="varint", language=language, model=model)
            self.assertEqual(baseline, original)
            self.assertEqual(base_metadata["changed_sources"], [])
            selected, record = transform_sources(files, representation="static16", language=language, model=model)
            self.assertEqual(files, original)
            self.assertEqual(selected["unrelated/source"], original["unrelated/source"])
            self.assertEqual({c["path"] for c in record["changed_sources"]}, {consumer, "model/" + header})
            self.assertEqual(record["restored_i16le_sha256"], base_metadata["restored_i16le_sha256"])
            self.assertNotIn(b"OnceLock" if language == "rust" else b"static int16_t rove_model_weights", selected[consumer])

    def test_pure_transform_rejects_unknown_model_inputs(self):
        with self.assertRaisesRegex(ValueError, "missing canonical"):
            transform_sources({}, representation="static16", language="c", model=load_model())
        with self.assertRaisesRegex(ValueError, "exact canonical"):
            transform_sources({"model/frozen.h": b"unknown"}, representation="varint", language="c", model=load_model())

    def test_verifier_rejects_output_path_formats_and_mislabeled_producers(self):
        for candidates, selected in (({"../escape": {}}, ["../escape"]),
                                      ({"varint": {}}, ["varint", "varint"]),
                                      ({"varint": {}}, ["unknown"]), ({"varint": {}}, [])):
            with self.assertRaises(ValueError):
                validate_formats(candidates, selected)
        model = load_model()
        record = metadata("static16", model)
        record["language"] = "rust"
        validate_producer_metadata(record, "static16", "rust", model)
        for key, value in (("runtime_representation", "varint"), ("language", "c"),
                           ("canonical_reference_sha256", "wrong"), ("restored_i16le_sha256", "wrong")):
            wrong = dict(record, **{key: value})
            with self.subTest(field=key), self.assertRaises(ValueError):
                validate_producer_metadata(wrong, "static16", "rust", model)


if __name__ == "__main__":
    unittest.main()
