"""Integer arithmetic bits for the independently authored context decoder.

Bit 1 selects the lower interval; bit 0 selects the upper interval.  Temporal
bits are stored at byte bit positions 0 through 7, in that order.  The result
contains only the arithmetic body: no model header and no four-byte zero tail.

The carry and finish equations use a 32-bit low endpoint L, range R, and a
temporal binary prefix P of q bits.  After T normalizations q = T - 1 and the
unbounded lower endpoint is P * 2**32 + L.  Incrementing the prefix propagates
carry; no output bit is prematurely assumed stable.  This deterministic short
finish chooses an integer inside the final interval.  Decoder compatibility
alone does not establish identity with another encoder's termination bytes.
"""

_TOP = 1 << 31
_MASK = (1 << 32) - 1


class Encoder:
    """Encode update(bit, p0, p1) calls, then finish() to immutable body bytes.

    Probabilities obey the decoder's unsigned 32-bit sum contract and must give
    two nonempty integer subintervals.  The real context model's base counts
    meet this condition.  ``body_bits`` is set by finish(); unused high bits of
    its last byte are zero.  Finish is idempotent; update after finish is an
    error.  An empty update sequence has an empty body by convention.
    """

    def __init__(self):
        self.low = 0
        self.range = _TOP
        self.cursor = -1
        self.normalizations = 0
        self.updates = 0
        self.body_bits = None
        self._data = bytearray()
        self._result = None

    def _increment(self, prefix_bits):
        """Add one to the temporal prefix; discard a carry past position 0."""
        if prefix_bits <= 0:
            return
        needed = (prefix_bits + 7) // 8
        self._data.extend(bytes(max(0, needed - len(self._data))))
        position = prefix_bits - 1
        while position >= 0:
            at, bit = divmod(position, 8)
            mask = 1 << bit
            self._data[at] ^= mask
            if self._data[at] & mask:
                break
            position -= 1

    def update(self, bit, p0, p1):
        if self._result is not None:
            raise ValueError("cannot update a finished arithmetic encoder")
        if not isinstance(bit, int) or bit not in (0, 1):
            raise ValueError("arithmetic bit must be integer 0 or 1")
        if type(p0) is not int or type(p1) is not int:
            raise ValueError("probability counts must be integers")
        if p0 <= 0 or p1 <= 0 or p0 + p1 > _MASK:
            raise ValueError("probability counts require a positive u32 sum")
        cut = self.range * p1 // (p0 + p1)
        if not 0 < cut < self.range:
            raise ValueError("probabilities produce an empty integer interval")

        if bit:
            self.range = cut
        else:
            full_low = self.low + cut
            self.low = full_low & _MASK
            self.range -= cut
            if full_low > _MASK:
                self._increment(self.cursor)
        while self.range < _TOP:
            self.cursor += 1
            if self.low & _TOP:
                self._increment(self.cursor)
            self.low = (self.low << 1) & _MASK
            self.range <<= 1
            self.normalizations += 1
        self.updates += 1

    def finish(self):
        if self._result is not None:
            return self._result
        prefix_bits = max(0, self.cursor)
        if self.low:
            # R >= 2**31.  With no 32-bit endpoint crossing, L <= 2**31
            # and the next half-unit boundary is inside [L, L + R).
            if self.low + self.range - 1 <= _MASK:
                prefix_bits += 1
            self._increment(prefix_bits)
        length = (prefix_bits + 7) // 8
        self._data.extend(bytes(max(0, length - len(self._data))))
        result = self._data[:length]
        if prefix_bits & 7:
            result[-1] &= (1 << (prefix_bits & 7)) - 1
        self.body_bits = prefix_bits
        self._result = bytes(result)
        return self._result
