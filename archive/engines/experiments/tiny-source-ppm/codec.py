#!/usr/bin/env python3
"""Original fixed order-4 PPM-C encoder with exclusions and byte range coding.

Contexts contain intrinsic online symbol counts. Escape frequency is the number
of eligible distinct symbols; escape excludes that context's symbols before
backoff. After order zero, unseen symbols use a uniform remaining alphabet.
There are no trained tables, fitted parameters, rescaling or alternate profiles.
"""
import struct
import zlib

ORDER = 4
MAX_OUTPUT = 1 << 20


def encode(source):
    if len(source) > MAX_OUTPUT:
        raise ValueError("source exceeds fixed bound")
    model = {}
    width, low, cache, pending = 0xffffffff, 0, 0, 1
    output = bytearray()

    def shift():
        nonlocal low, cache, pending
        lower, carry = low & 0xffffffff, low >> 32
        if lower < 0xff000000 or carry:
            last = cache
            for _ in range(pending):
                output.append((last+carry) & 255)
                last = 255
            cache, pending = lower >> 24, 0
        pending += 1
        low = (lower << 8) & 0xffffffff

    def event(cumulative, frequency, total):
        nonlocal low, width
        unit = width // total
        if not unit or not frequency or cumulative+frequency > total:
            raise ValueError("invalid coder distribution")
        low += unit*cumulative
        width = unit*frequency
        while width < 16777216:
            width <<= 8
            shift()

    for position, symbol in enumerate(source):
        excluded = set()
        matched = False
        for order in range(min(ORDER,position),-1,-1):
            context = source[position-order:position] if order else b""
            counts = model.get(context,{})
            eligible = sorted(value for value in counts if value not in excluded)
            if eligible:
                total = sum(counts[value] for value in eligible)
                if symbol in eligible:
                    cumulative = sum(counts[value] for value in eligible if value < symbol)
                    event(cumulative,counts[symbol],total+len(eligible))
                    matched = True
                    break
                event(total,len(eligible),total+len(eligible))
            excluded.update(counts)
        if not matched:
            alphabet = [value for value in range(256) if value not in excluded]
            event(alphabet.index(symbol),1,len(alphabet))
        for order in range(min(ORDER,position)+1):
            context = source[position-order:position] if order else b""
            counts = model.setdefault(context,{})
            counts[symbol] = counts.get(symbol,0)+1
    for _ in range(5):
        shift()
    frame = b"SPP1"+struct.pack("<II",len(source),zlib.adler32(source))+output
    return frame, {"order":ORDER,"contexts":len(model),"symbol_entries":sum(map(len,model.values())),
                   "raw_bytes":len(source),"framed_bytes":len(frame),"coded_body_bytes":len(output)}
