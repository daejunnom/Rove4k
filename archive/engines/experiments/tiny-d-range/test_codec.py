#!/usr/bin/env python3
"""Independent reference round trips and finite malformed-stream checks."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import time
import codec
import reference


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if not args.out.is_absolute() or out.exists() or any((p/".git").exists() for p in (out,*out.parents)):
        parser.error("--out must be new, absolute and outside Git")
    args.out = out
    args.out.mkdir(parents=True)
    started = time.monotonic()
    rng = random.Random(20261020)
    fixtures = [b"", bytes(range(256)), bytes(range(255,-1,-1)), b"\0"*8192, b"\xff"*8192]
    fixtures.extend(bytes([value]) for value in range(256))
    fixtures.extend(rng.randbytes(size) for size in range(256))
    fixtures.extend(rng.randbytes(size) for size in (257,511,512,1023,1024,8192))
    fixtures.extend(bytes([value])*513 for value in (0,1,127,128,254,255))
    fixtures.extend((b"\xe8\0\0\0\0\xe9\xff\xff\xff\xff"*500,
                     b"\x48\x89\xe5\x48\x83\xec\x20\x31\xc0\xc3"*500))
    roundtrips = negatives = mutations = mutation_rejections = 0
    hashes = {}
    for profile in codec.PROFILES:
        running = hashlib.sha256()
        for data in fixtures:
            frame = codec.encode(data,profile)
            if reference.decode(frame,maximum=len(data)) != data or frame != codec.encode(bytes(data),profile):
                raise ValueError("identity/reproduction failure")
            if codec.bcj(codec.bcj(data),inverse=True) != data:
                raise ValueError("BCJ identity failure")
            running.update(frame)
            roundtrips += 1
        hashes[profile] = running.hexdigest()
        frame = codec.encode(bytes(range(256)),profile)
        invalid = [frame[:cut] for cut in range(len(frame))]
        invalid += [frame+b"\0",b"BAD!"+frame[4:]]
        for offset in (4,5,8,12,16,20):
            bad = bytearray(frame);bad[offset] ^= 255;invalid.append(bytes(bad))
        for bad in invalid:
            try: reference.decode(bad)
            except ValueError: negatives += 1
            else: raise ValueError("accepted invalid fixture")
        try: reference.decode(frame,maximum=255)
        except ValueError: negatives += 1
        else: raise ValueError("output bound ignored")
        # Finite mutation study. Adler32 is accidental-corruption detection,
        # not authentication and no claim is made about arbitrary collisions.
        for index in range(20,len(frame)):
            for bit in range(8):
                bad = bytearray(frame);bad[index] ^= 1<<bit;mutations += 1
                try: decoded = reference.decode(bytes(bad))
                except ValueError: mutation_rejections += 1
                else:
                    if decoded != bytes(range(256)):
                        raise ValueError("undetected sample mutation")
    report = {"passed":True,"roundtrips":roundtrips,"negative_frames":negatives,"mutated_frames":mutations,
              "mutation_rejections":mutation_rejections,"fixture_stream_sha256":hashes,
              "wall_seconds":time.monotonic()-started,"training":False,"profiles":list(codec.PROFILES)}
    (args.out/"codec.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
