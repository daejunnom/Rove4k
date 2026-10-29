"""Pure codec checks; optional TINY_D_FROZEN_ROOT pins actual TinyD images.

Run on any Python 3.10+ interpreter. This file does not invoke a compiler,
execute an ELF, modify stable sources or create engine artifacts.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import unittest
import zlib

import codec


class FixedStream:
    """Small test-only writer using the literal RFC fixed-code intervals."""
    def __init__(self):
        self.data = [1, 1, 0]  # final + fixed block

    def field(self, value, count):
        self.data.extend((value >> bit) & 1 for bit in range(count))

    def canonical(self, value, count):
        self.data.extend((value >> bit) & 1 for bit in reversed(range(count)))

    def symbol(self, value):
        if value <= 143:
            self.canonical(value+0x30, 8)
        elif value <= 255:
            self.canonical(value-144+0x190, 9)
        elif value <= 279:
            self.canonical(value-256, 7)
        else:
            self.canonical(value-280+0xC0, 8)

    def finish(self, end=True):
        if end:
            self.symbol(256)
        result = bytearray((len(self.data)+7)//8)
        for position, bit in enumerate(self.data):
            result[position//8] |= bit << (position % 8)
        return bytes(result)


class CodecChecks(unittest.TestCase):
    def test_bcj_golden_and_roundtrip(self):
        for raw, encoded in [("e8fbffffff", "e800000000"),
                             ("e9ffffffff", "e904000000"),
                             ("90e8faffffff", "90e800000000"),
                             ("e8000000", "e8000000"),
                             ("e8e8e9e8e9", "e8ede9e8e9")]:
            self.assertEqual(codec.bcj(bytes.fromhex(raw)), bytes.fromhex(encoded))
            self.assertEqual(codec.bcj(bytes.fromhex(encoded), inverse=True), bytes.fromhex(raw))
        rng = random.Random(20261020)
        cases = [b"", b"\xe8"*4099, b"\xe9"*4099, bytes(range(256))*300]
        cases.extend(rng.randbytes(n) for n in range(520))
        for raw in cases:
            self.assertEqual(codec.bcj(codec.bcj(raw), inverse=True), raw)

    def test_lz_boundaries_and_rejections(self):
        for packed, expected in [(b"\0x\x80\1\0", b"x"*4),
                                 (b"\0x\xff\1\0", b"x"*131),
                                 (b"\x7f"+bytes(range(128)), bytes(range(128)))]:
            self.assertEqual(codec.lz_decompress(packed, len(expected)), expected)
        for packed, size in [(b"\x80\0\0", 3), (b"\x80\1\0", 3),
                             (b"\x7fabc", 128), (b"\x80\1", 3),
                             (b"\0x", 2), (b"\0x", 0), (b"\0x\x80\1\0", 3)]:
            with self.assertRaises(ValueError):
                codec.lz_decompress(packed, size)
        rng = random.Random(20261020)
        block = rng.randbytes(70000)
        for raw in [b"", b"a"*131073, block, block+block[:2048], bytes(range(256))*300]:
            packed = codec.lz_compress(raw)
            self.assertEqual(codec.lz_decompress(packed, len(raw)), raw)
            self.assertEqual(codec.lz_compress(raw), packed)

    def test_fixed_literal_classes_and_overlapping_matches(self):
        raw = bytes(range(256))
        stream = FixedStream()
        for value in raw:
            stream.symbol(value)
        encoded = stream.finish()
        self.assertEqual(codec.fixed_decompress(encoded, len(raw)), raw)
        self.assertEqual(zlib.decompress(encoded, -15), raw)
        # Check every length class against independent RFC base/extra tables.
        bases = [3,4,5,6,7,8,9,10,11,13,15,17,19,23,27,31,35,43,51,59,67,83,99,115,131,163,195,227,258]
        extras = [0,0,0,0,0,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5,0]
        for index, (base, extra) in enumerate(zip(bases, extras)):
            for added in (0, (1 << extra)-1):
                stream = FixedStream()
                stream.symbol(ord("x"))
                stream.symbol(257+index)
                stream.field(added, extra)
                stream.canonical(0, 5)  # distance one; overlapping forward copy
                encoded = stream.finish()
                raw = b"x"*(1+base+added)
                self.assertEqual(codec.fixed_decompress(encoded, len(raw)), raw)
                self.assertEqual(zlib.decompress(encoded, -15), raw)

    def test_fixed_distance_classes(self):
        bases = [1,2,3,4,5,7,9,13,17,25,33,49,65,97,129,193,257,385,513,769,1025,1537,2049,3073,4097,6145,8193,12289,16385,24577]
        extras = [0,0,0,0,1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8,9,9,10,10,11,11,12,12,13,13]
        rng = random.Random(73)
        prefix = rng.randbytes(32768)
        for index, (base, extra) in enumerate(zip(bases, extras)):
            for added in (0, (1 << extra)-1):
                distance = base+added
                stream = FixedStream()
                history = prefix[:max(3, distance)]
                for byte in history:
                    stream.symbol(byte)
                stream.symbol(257)  # length three
                stream.canonical(index, 5)
                stream.field(added, extra)
                encoded = stream.finish()
                expected = bytearray(history)
                for _ in range(3):
                    expected.append(expected[-distance])
                self.assertEqual(codec.fixed_decompress(encoded, len(expected)), expected)
                self.assertEqual(zlib.decompress(encoded, -15), expected)

    def test_fixed_rejects_unsupported_and_malformed_streams(self):
        encoded = codec.fixed_compress(b"hello hello hello")
        for end in range(len(encoded)):
            with self.assertRaises(ValueError):
                codec.fixed_decompress(encoded[:end], 17)
        for bad in [b"", b"\x01\x01\x00\xfe\xffx",  # final stored block
                    bytes([encoded[0] & ~1])+encoded[1:],  # non-final
                    bytes([(encoded[0] & ~6) | 4])+encoded[1:],  # dynamic
                    bytes([(encoded[0] & ~6) | 6])+encoded[1:],  # reserved type
                    encoded+b"\0"]:
            with self.assertRaises(ValueError):
                codec.fixed_decompress(bad, 17)
        literal = codec.fixed_compress(b"A")
        with self.assertRaisesRegex(ValueError, "padding"):
            codec.fixed_decompress(literal[:-1]+bytes([literal[-1] | 128]), 1)
        for declared in (0, 16, 18):
            with self.assertRaises(ValueError):
                codec.fixed_decompress(encoded, declared)
        for reserved in (286, 287):
            stream = FixedStream()
            stream.symbol(reserved)
            with self.assertRaisesRegex(ValueError, "reserved.*length"):
                codec.fixed_decompress(stream.finish(), 3)
        for distance in (30, 31):
            stream = FixedStream()
            stream.symbol(ord("x"))
            stream.symbol(257)
            stream.canonical(distance, 5)
            with self.assertRaisesRegex(ValueError, "reserved.*distance"):
                codec.fixed_decompress(stream.finish(), 4)
        for literal_count, distance_code in ((0, 0), (1, 1)):
            stream = FixedStream()
            for _ in range(literal_count):
                stream.symbol(ord("x"))
            stream.symbol(257)
            stream.canonical(distance_code, 5)
            with self.assertRaisesRegex(ValueError, "distance exceeds"):
                codec.fixed_decompress(stream.finish(), literal_count+3)

    def test_fixed_compressor_admission_and_random_data(self):
        rng = random.Random(20261020)
        for raw in [b"", b"a"*70000, bytes(range(256))*10,
                    *(rng.randbytes(size) for size in (1, 7, 31, 128, 2048, 32768))]:
            producer = zlib.compressobj(level=9, wbits=-15, strategy=zlib.Z_FIXED)
            produced = producer.compress(raw)+producer.flush()
            self.assertEqual(zlib.decompress(produced, -15), raw)
            if produced[0] & 7 == 3:
                # A later block could still be unsupported; admit only a full
                # strict parse, not merely the first header/producer strategy.
                try:
                    decoded = codec.fixed_decompress(produced, len(raw))
                except ValueError:
                    with self.assertRaises(ValueError):
                        codec.fixed_compress(raw)
                else:
                    self.assertEqual(decoded, raw)
                    self.assertEqual(codec.fixed_compress(raw), produced)
            else:
                with self.assertRaises(ValueError):
                    codec.fixed_compress(raw)

    @unittest.skipUnless(os.environ.get("TINY_D_FROZEN_ROOT"), "set TINY_D_FROZEN_ROOT to verify actual frozen image controls")
    def test_frozen_payload_controls(self):
        root = Path(os.environ["TINY_D_FROZEN_ROOT"])
        path = root / "recipe/engines/scripts/elf_loader.py"
        spec = importlib.util.spec_from_file_location("frozen_generic_loader", path)
        frozen = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(frozen)
        images = [("scalar-shipping", "ef14e2839af96d111fa9ce1a2928749ceec518e3be652cc6d36ee8975cae47d0"),
                  ("hq-shipping", "387a00209ffcc14446f662a56cc2ff778ae7873c2dfebebbee9906fd19e5cd0c")]
        records = []
        for form, expected_hash in images:
            original = (root / form / "x").read_bytes()
            self.assertEqual(hashlib.sha256(original).hexdigest(), expected_hash)
            filtered = codec.bcj(original)
            self.assertEqual(filtered, frozen._bcj(original))
            lz = codec.lz_compress(filtered)
            self.assertEqual(lz, frozen._compress(filtered))
            fixed = codec.fixed_compress(filtered)
            for stream, decode in [(lz, codec.lz_decompress), (fixed, codec.fixed_decompress)]:
                self.assertEqual(codec.bcj(decode(stream, len(original)), inverse=True), original)
            records.append({"form": form, "original_bytes": len(original), "original_sha256": expected_hash,
                            "lz_bcj_bytes": len(lz), "lz_sha256": hashlib.sha256(lz).hexdigest(),
                            "fixed_bcj_bytes": len(fixed), "fixed_sha256": hashlib.sha256(fixed).hexdigest()})
        print(json.dumps({"frozen_image_checks": records}, indent=2))


if __name__ == "__main__":
    unittest.main()
