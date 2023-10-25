
class EncoderError(Exception):
    """
    Exception for errors that occur while encoding/decoding
    a short URL.
    """
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class DigitEncoder(object):
    block_size = 24
    min_length = 2
    mask = (1 << block_size) - 1
    mapping = list(reversed(range(block_size)))

    def encode_id(self, id):
        """
        Encodes an integer.

        :param id: The integer to encode.
        :type id: int.
        :returns: str -- the encoded value.
        """
        return self.enbase(self.encode(id))

    def encode(self, n):
        return (n & ~self.mask) | self._encode(n & self.mask)

    def _encode(self, n):
        result = 0
        for i, b in enumerate(self.mapping):
            if n & (1 << i):
                result |= (1 << b)
        return result

    def enbase(self, x):
        result = self._enbase(x)
        padding = self.alphabet[0] * (self.min_length - len(result))
        return '%s%s' % (padding, result)

    def _enbase(self, x):
        n = len(self.alphabet)
        if x < n:
            return self.alphabet[x]
        return self._enbase(x // n) + self.alphabet[x % n]

    def decode_id(self, encoded):
        """
        Decodes a value encoded with :func:`UrlEncoder.encode_id`.

        :param encoded: The value to decode.
        :type encoded: str.
        :returns: int -- the decoded value.
        """
        return self.decode(self.debase(encoded))

    def decode(self, n):
        return (n & ~self.mask) | self._decode(n & self.mask)

    def _decode(self, n):
        result = 0
        for i, b in enumerate(self.mapping):
            if n & (1 << b):
                result |= (1 << i)
        return result

    def debase(self, x):
        n = len(self.alphabet)
        result = 0
        for i, c in enumerate(reversed(x)):
            try:
                result += self.alphabet.index(c) * (n ** i)
            except ValueError:
                raise EncoderError("Encoded value characters don't match the "
                                   "defined alphabet.")
        return result


class IDEncoder(DigitEncoder):
    alphabet = 'exjdy5b4wcusm72r6pftgznkiq3ah98'
