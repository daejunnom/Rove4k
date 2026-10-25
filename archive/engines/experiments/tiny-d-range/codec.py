#!/usr/bin/env python3
"""Original bounded online binary range encoder. No learned tables or training.

Profiles are fixed algorithms: order1 (previous byte and current bit prefix),
and mix2 (equal mixture of prefix/order1/a bounded hash of two previous bytes).
Each state is a 16-bit probability of zero, initially 32768, updated by 1/32.
The byte coder uses a 32-bit range and a 64-bit carry accumulator.
"""
import struct
import zlib

PROFILES = ("order1", "mix2")
HEADER = struct.Struct("<4sB3xIII")
MAX_OUTPUT = 1 << 24


def bcj(data, inverse=False):
    out = bytearray(data)
    pos = 0
    while pos + 4 < len(out):
        if out[pos] & 254 == 232:
            value = int.from_bytes(out[pos+1:pos+5], "little")
            value = value - pos - 5 if inverse else value + pos + 5
            out[pos+1:pos+5] = (value & 0xffffffff).to_bytes(4, "little")
            pos += 5
        else:
            pos += 1
    return bytes(out)


def encode(data, profile="order1"):
    if profile not in PROFILES or len(data) > MAX_OUTPUT:
        raise ValueError("unsupported profile/output bound")
    which = PROFILES.index(profile)
    states = [32768] * (65536 if not which else 131328)
    low, width, cache, pending = 0, 0xffffffff, 0, 1
    coded = bytearray()

    def shift():
        nonlocal low, cache, pending
        lower, carry = low & 0xffffffff, low >> 32
        if lower < 0xff000000 or carry:
            value = cache
            for _ in range(pending):
                coded.append((value + carry) & 255)
                value = 255
            cache = lower >> 24
            pending = 0
        pending += 1
        low = (lower << 8) & 0xffffffff

    previous, older = 0, 0
    for value in data:
        prefix = 1
        for shiftby in range(7, -1, -1):
            first = (previous << 8) | prefix
            indices = (first,) if not which else (
                65536 + prefix, first,
                65792 + (((older * 251 + previous) * 257 + prefix) & 65535))
            probability = sum(states[index] for index in indices) // len(indices)
            bound = (width >> 16) * probability
            bit = (value >> shiftby) & 1
            if bit:
                low += bound
                width -= bound
            else:
                width = bound
            for index in indices:
                probability = states[index]
                states[index] = probability - (probability >> 5) if bit else probability + ((65536-probability) >> 5)
            while width < (1 << 24):
                width <<= 8
                shift()
            prefix = prefix * 2 + bit
        older, previous = previous, value
    for _ in range(5):
        shift()
    return HEADER.pack(b"DRC1", which, len(data), len(coded), zlib.adler32(data)) + coded


if __name__ == "__main__":
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--profile", choices=PROFILES, default="order1")
    args = parser.parse_args()
    args.output.write_bytes(encode(args.input.read_bytes(), args.profile))
