"""Build-time codecs for the owned fixed-layout TinyD loader experiment.

BCJ and LZ runs originate in this repository's handwritten
engines/scripts/elf_loader.py implementation. They are copied here so a frozen
experimental recipe has no dependency on later changes to the generic packer.
The fixed-Huffman decoder is independently written from RFC 1951; no external
decoder source is incorporated. zlib is used only by the build-time compressor.
"""
from collections import deque
import hashlib
import zlib

BCJ_VERSION = "e8-e9-whole-image-add-next-offset-le32-v1"
LZ_VERSION = "rove4k-lz-runs-v1"
FIXED_VERSION = "rfc1951-one-final-fixed-zero-padding-v1"
MAX_IMAGE_BYTES = 256 * 1024 * 1024
BODY_VERSION = 'tiny-rust-d-result-data8-body232-zero-prefix-v1'
BODY_IMAGES = {
    'a5e0d3814d1dd432bbb2b0145f222726a86a80f93333f28c455ea22946afd74d':
        '9abcbf7accfcc919c046aaac7b134f479b58d81adf4e7195937601d12125e25f',
    '3cfdfd2748e31525da832555069c2b5cabf056ebd0527ae22d52ebbc93be94d2':
        '049504665155d8a5d498b9ba5e646a0efa1d42a440f8a279b091373251c049c8',
}


def restoration_image(load, prefix):
    """Explicit full-load or exact Rust body232 image, before whole-offset BCJ.

    The caller separately admits the compiled ELF and its sectionless load.
    This is not an ELF image for kernel execution. Only the unused header
    prefix is zeroed; entry240 and initialized data8 are preserved verbatim.
    """
    if type(load) is not bytes or type(prefix) is not int or prefix not in (0, 232):
        raise ValueError('explicit full or body232 restoration policy required')
    digest = lambda raw: hashlib.sha256(raw).hexdigest()
    source = digest(load)
    if prefix == 0:
        return load, {'policy': 'legacy-full', 'prefix_zero_bytes': 0,
                      'compiled_load_sha256': source, 'restored_image_sha256': source,
                      'full_body_complement_equal': True}
    expected = BODY_IMAGES.get(source)
    if len(load) != 16392 or expected is None:
        raise ValueError('unknown exact Rust Result data8 load image')
    at, crossing = 0, []
    while at+4 < len(load):
        if load[at] in (232, 233):
            if at < prefix < at+5:
                crossing.append(at)
            at += 5
        else:
            at += 1
    if crossing:
        raise ValueError('BCJ operand crosses declared header cut')
    result = bytes(prefix) + load[prefix:]
    if digest(result) != expected or result[prefix:] != load[prefix:] or result[0x4000:0x4008] != bytes.fromhex('4601400000000000'):
        raise ValueError('Rust body232 image/data8 differs')
    return result, {'policy': 'body232', 'format': BODY_VERSION, 'prefix_zero_bytes': prefix,
                    'compiled_load_sha256': source, 'restored_image_sha256': expected,
                    'BCJ_cross_cut': crossing, 'BCJ_offsets': 'full restored-image offsets',
                    'full_body_complement_equal': True, 'initialized_data8_preserved': True,
                    'entry_offset': 240, 'runtime_qualified': False}


def _size(expected_size):
    if not isinstance(expected_size, int) or not 0 <= expected_size <= MAX_IMAGE_BYTES:
        raise ValueError("expected image size must be 0..256 MiB")


def bcj(data, *, inverse=False):
    """Transform every complete E8/E9 sequence, skipping its four operands.

    Both passes use offsets in this exact byte sequence, including ELF headers.
    Arithmetic wraps modulo 2^32. The transformed opcode is never modified, so
    operands containing opcode-looking bytes cannot change the inverse scan.
    """
    result = bytearray(data)
    at = 0
    while at+4 < len(result):
        if result[at] in (0xE8, 0xE9):
            value = int.from_bytes(result[at+1:at+5], "little")
            value = (value-(at+5) if inverse else value+(at+5)) & 0xFFFFFFFF
            result[at+1:at+5] = value.to_bytes(4, "little")
            at += 5
        else:
            at += 1
    return bytes(result)


def lz_compress(data):
    """Literal runs 1..128; matches length 3..130, 16-bit nonzero distance."""
    chains = {}
    encoded = bytearray()
    literals = bytearray()
    size = len(data)

    def flush():
        if literals:
            encoded.append(len(literals)-1)
            encoded.extend(literals)
            literals.clear()

    def remember(at):
        expired = at-65535
        if expired >= 0:
            key = data[expired:expired+3]
            positions = chains.get(key)
            if positions and positions[0] == expired:
                positions.popleft()
                if not positions:
                    del chains[key]
        if at+2 < size:
            chains.setdefault(data[at:at+3], deque(maxlen=64)).append(at)

    at = 0
    while at < size:
        best, distance = 0, 0
        if at+2 < size:
            maximum = min(130, size-at)
            for previous in reversed(chains.get(data[at:at+3], ())):
                delta = at-previous
                if delta > 65535:
                    break
                length = 3
                while length < maximum and data[previous+length] == data[at+length]:
                    length += 1
                if length > best:
                    best, distance = length, delta
                    if best == maximum:
                        break
        if best >= 3:
            flush()
            encoded.append(128+best-3)
            encoded.extend(distance.to_bytes(2, "little"))
            for position in range(at, at+best):
                remember(position)
            at += best
        else:
            literals.append(data[at])
            remember(at)
            at += 1
            if len(literals) == 128:
                flush()
    flush()
    return bytes(encoded)


def lz_decompress(data, expected_size):
    _size(expected_size)
    result = bytearray()
    at = 0
    while at < len(data):
        control = data[at]
        at += 1
        if control < 128:
            count = control+1
            if at+count > len(data):
                raise ValueError("truncated LZ literal run")
            if len(result)+count > expected_size:
                raise ValueError("LZ output exceeds declared image size")
            result.extend(data[at:at+count])
            at += count
        else:
            if at+2 > len(data):
                raise ValueError("truncated LZ match")
            distance = int.from_bytes(data[at:at+2], "little")
            at += 2
            if not 0 < distance <= len(result):
                raise ValueError("invalid LZ match distance")
            count = (control & 127)+3
            if len(result)+count > expected_size:
                raise ValueError("LZ output exceeds declared image size")
            for _ in range(count):
                result.append(result[-distance])
    if len(result) != expected_size:
        raise ValueError("LZ output has wrong image size")
    return bytes(result)


def fixed_decompress(data, expected_size):
    """Decode exactly one final RFC1951 BTYPE=1 block, with strict bounds.

    Dynamic/stored/non-final blocks, reserved codes, trailing bytes and nonzero
    end padding are outside this dedicated format and explicitly rejected.
    Huffman codes are read MSB first, while ordinary fields/extras are LSB first.
    """
    _size(expected_size)
    bit = 0
    output = bytearray()

    def bits(count):
        nonlocal bit
        if bit+count > len(data)*8:
            raise ValueError("truncated fixed-Huffman stream")
        value = 0
        for shift in range(count):
            value |= ((data[bit//8] >> (bit % 8)) & 1) << shift
            bit += 1
        return value

    def canonical(count):
        value = 0
        for _ in range(count):
            value = (value << 1) | bits(1)
        return value

    if bits(3) != 3:  # BFINAL=1, BTYPE=01, in LSB-first field order.
        raise ValueError("requires exactly one final fixed-Huffman block")
    while True:
        code = canonical(7)
        if code < 24:
            symbol = code+256
        else:
            code = (code << 1) | bits(1)
            if code < 192:
                symbol = code-48
            elif code < 200:
                symbol = code+88
            else:
                symbol = ((code << 1) | bits(1))-256
        if symbol < 256:
            if len(output) >= expected_size:
                raise ValueError("fixed-Huffman output exceeds declared image size")
            output.append(symbol)
        elif symbol == 256:
            break
        elif symbol <= 285:
            index = symbol-257
            if index < 8:
                length = index+3
            elif index == 28:
                length = 258
            else:
                extra = (index >> 2)-1
                length = ((4+(index & 3)) << extra)+3+bits(extra)
            distance_code = canonical(5)
            if distance_code >= 30:
                raise ValueError("reserved fixed-Huffman distance code")
            if distance_code < 4:
                distance = distance_code+1
            else:
                extra = (distance_code >> 1)-1
                distance = ((2+(distance_code & 1)) << extra)+1+bits(extra)
            if distance > len(output):
                raise ValueError("fixed-Huffman distance exceeds produced bytes")
            if len(output)+length > expected_size:
                raise ValueError("fixed-Huffman output exceeds declared image size")
            for _ in range(length):
                output.append(output[-distance])
        else:
            raise ValueError("reserved fixed-Huffman length code")
    if len(output) != expected_size:
        raise ValueError("fixed-Huffman output has wrong image size")
    if (bit+7)//8 != len(data):
        raise ValueError("trailing bytes after fixed-Huffman block")
    if bit % 8 and data[-1] >> (bit % 8):
        raise ValueError("nonzero padding after fixed-Huffman block")
    return bytes(output)


def fixed_compress(data):
    """Build a strict fixed block; zlib strategy alone is not admission proof.

    Z_FIXED can emit stored blocks, which this dedicated subset rejects. The
    entire generated stream is parsed here rather than checking its first bits.
    """
    compressor = zlib.compressobj(level=9, wbits=-15, strategy=zlib.Z_FIXED)
    encoded = compressor.compress(data)+compressor.flush()
    if fixed_decompress(encoded, len(data)) != data:
        raise ValueError("fixed-Huffman compression roundtrip mismatch")
    return encoded
