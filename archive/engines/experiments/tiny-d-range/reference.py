#!/usr/bin/env python3
"""Independent reference range decoder; imports no encoder or model code."""
from array import array


def decode(frame, maximum=1 << 24):
    if len(frame) < 25 or frame[:4] != b"DRC1" or frame[4] > 1 or any(frame[5:8]):
        raise ValueError("invalid range frame")
    raw_size = int.from_bytes(frame[8:12], "little")
    packed_size = int.from_bytes(frame[12:16], "little")
    checksum = int.from_bytes(frame[16:20], "little")
    profile = frame[4]
    if raw_size > maximum or packed_size != len(frame)-20 or packed_size < 5 or frame[20]:
        raise ValueError("invalid range sizes/initial byte")
    model = array("H", [32768]) * (131328 if profile else 65536)
    cursor = 25
    interval = (1 << 32)-1
    code = int.from_bytes(frame[21:25], "big")
    output = bytearray()
    previous = older = 0
    a, b = 1, 0
    for _ in range(raw_size):
        node = 1
        for _ in range(8):
            one = 256*previous + node
            if profile:
                zero = 65536 + node
                two = 65792 + ((257*(251*older+previous)+node) % 65536)
                probability = (model[zero]+model[one]+model[two]) // 3
            else:
                probability = model[one]
            partition = (interval // 65536) * probability
            bit = int(code >= partition)
            if bit:
                code -= partition
                interval -= partition
            else:
                interval = partition
            active = (zero, one, two) if profile else (one,)
            for context in active:
                state = model[context]
                model[context] = state-state//32 if bit else state+(65536-state)//32
            while interval < 16777216:
                if cursor == len(frame):
                    raise ValueError("truncated range stream")
                interval *= 256
                code = ((code * 256) + frame[cursor]) % (1 << 32)
                cursor += 1
            if code >= interval:
                raise ValueError("range code outside interval")
            node = node*2+bit
        value = node-256
        output.append(value)
        older, previous = previous, value
        a = (a+value) % 65521
        b = (b+a) % 65521
    if cursor != len(frame) or code != 0:
        raise ValueError("noncanonical range termination")
    if a+(b << 16) != checksum:
        raise ValueError("range checksum mismatch")
    return bytes(output)
