"""Independent decoder for the single SPP1 order-4 PPM-C format.

The model starts empty, uses exclusion, and is updated only after each decoded
byte. Counts are never rescaled. The framing and integer range arithmetic are
deliberately explicit so this module can serve as a separate reference.
"""

from __future__ import annotations

import struct
import zlib


MAGIC = b"SPP1"
ORDER = 4
MAX_RAW_LENGTH = 1 << 20
_MASK = (1 << 32) - 1
_RENORMALIZE = 1 << 24
_HEADER_LENGTH = 12


class _RangeDecoder:
    def __init__(self, body: bytes) -> None:
        if len(body) < 5:
            raise ValueError("truncated range-coder initialization")
        if body[0] != 0:
            raise ValueError("invalid range-coder leading byte")
        self.body = body
        self.position = 5
        self.width = _MASK
        self.code = int.from_bytes(body[1:5], "big")
        self._check_code()

    def _check_code(self) -> None:
        if not 0 <= self.code < self.width:
            raise ValueError("range code is outside the current interval")

    def locate(self, total: int) -> tuple[int, int]:
        """Return the integer unit and cumulative-frequency index."""
        if total <= 0:
            raise ValueError("empty probability distribution")
        self._check_code()
        unit = self.width // total
        if unit == 0:
            raise ValueError("probability total exceeds range precision")
        index = self.code // unit
        if index >= total:
            raise ValueError("range code occupies unused interval space")
        return unit, index

    def consume(self, cumulative: int, frequency: int, unit: int) -> None:
        if cumulative < 0 or frequency <= 0 or unit <= 0:
            raise ValueError("invalid arithmetic interval")
        self.code -= unit * cumulative
        self.width = unit * frequency
        self._check_code()
        while self.width < _RENORMALIZE:
            if self.position == len(self.body):
                raise ValueError("truncated range-coder body")
            self.width <<= 8
            self.code = (
                (self.code << 8) | self.body[self.position]
            ) & _MASK
            self.position += 1
            self._check_code()

    def finish(self) -> None:
        self._check_code()
        if self.position != len(self.body):
            raise ValueError("trailing range-coder bytes")
        if self.code != 0:
            raise ValueError("nonzero final range code")


def decode(frame: bytes | bytearray | memoryview) -> bytes:
    """Decode one complete SPP1 frame or raise ValueError for invalid input.

    The frame is ``SPP1``, little-endian u32 raw length, little-endian u32
    Adler-32, and the range-coder body. A body includes its zero leading byte
    and five-byte-flush representation; it must be consumed exactly.
    """
    if not isinstance(frame, (bytes, bytearray, memoryview)):
        raise TypeError("frame must be a bytes-like object")
    frame = bytes(frame)
    if len(frame) < _HEADER_LENGTH:
        raise ValueError("truncated SPP1 header")
    if frame[:4] != MAGIC:
        raise ValueError("invalid SPP1 magic")
    raw_length, expected_adler = struct.unpack_from("<II", frame, 4)
    if raw_length > MAX_RAW_LENGTH:
        raise ValueError("SPP1 raw length exceeds the fixed limit")

    arithmetic = _RangeDecoder(frame[_HEADER_LENGTH:])
    # Context lengths distinguish orders, including the empty order-0 context.
    model: dict[bytes, dict[int, int]] = {}
    output = bytearray()

    for position in range(raw_length):
        excluded: set[int] = set()
        decoded: int | None = None

        for order in range(min(ORDER, position), -1, -1):
            context = bytes(output[-order:]) if order else b""
            counts = model.get(context)
            if counts is None:
                # An unknown context has no symbols and emits no escape.
                continue
            eligible = sorted(symbol for symbol in counts if symbol not in excluded)
            if not eligible:
                excluded.update(counts)
                continue

            symbol_total = sum(counts[symbol] for symbol in eligible)
            escape_frequency = len(eligible)
            unit, index = arithmetic.locate(symbol_total + escape_frequency)
            if index >= symbol_total:
                arithmetic.consume(symbol_total, escape_frequency, unit)
                excluded.update(counts)
                continue

            cumulative = 0
            for symbol in eligible:
                frequency = counts[symbol]
                if index < cumulative + frequency:
                    arithmetic.consume(cumulative, frequency, unit)
                    decoded = symbol
                    break
                cumulative += frequency
            if decoded is None:
                raise ValueError("symbol interval was not found")
            break

        if decoded is None:
            remaining = [symbol for symbol in range(256) if symbol not in excluded]
            unit, index = arithmetic.locate(len(remaining))
            arithmetic.consume(index, 1, unit)
            decoded = remaining[index]

        # All orders learn the same symbol using the pre-symbol history.
        for order in range(min(ORDER, position) + 1):
            context = bytes(output[-order:]) if order else b""
            counts = model.setdefault(context, {})
            counts[decoded] = counts.get(decoded, 0) + 1
        output.append(decoded)

    arithmetic.finish()
    raw = bytes(output)
    if zlib.adler32(raw) != expected_adler:
        raise ValueError("SPP1 Adler-32 mismatch")
    return raw
