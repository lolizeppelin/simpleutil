try:
    from simpleutil.utils import _cutils

    class BitMap(_cutils.bitMap):
        """Bit map from _cutils"""

        def __init__(self, max):
            if max <= 0 or max >= 1 << 64:
                raise ValueError('Bit map init value error')
            _cutils.bitMap.__init__(self, max)

        def add(self, num):
            if num < 0 or num > self.max:
                raise ValueError('Value over range')
            _cutils.bitMap.add(self, num)

        def has(self, num):
            if num < 0 or num > self.max:
                raise ValueError('Value over range')
            return _cutils.bitMap.has(self, num) > 0

        def all(self, reverse=False):
            return self.big2small() if reverse else self.small2big()

        def big2small(self):
            length = int(self.max / self.size) + 1
            for index in xrange(length - 1, -1, -1):
                bitmap = self.get(index)
                for i in range(self.size - 1, -1, -1):
                    if (1 << i) & bitmap:
                        yield (index * self.size) + i

        def small2big(self):
            length = int(self.max / self.size) + 1
            for index in xrange(length):
                bitmap = self.get(index)
                for i in range(0, self.size):
                    if (1 << i) & bitmap:
                        yield (index * self.size) + i
except ImportError:

    class BitMap(object):
        """Bit map native"""

        def __init__(self, max):
            if max <= 0 or max >= 1 << 64:
                raise ValueError('Bit map init value error')
            self.max = max
            self.size = 64 if max >= (1 << 32) else 32
            self.array = [0] * (int(max / self.size) + 1)

        def add(self, num):
            if num < 0 or num > self.max:
                raise ValueError('Value over range')
            self.array[num / self.size] |= (1 << (num % self.size))

        def has(self, num):
            if num < 0 or num > self.max:
                raise ValueError('Value over range')
            return (self.array[num / self.size] & (1 << (num % self.size)) > 0)

        def all(self, reverse=False):
            return self.big2small() if reverse else self.small2big()

        def big2small(self):
            for index in xrange(len(self.array) - 1, -1, -1):
                bitmap = self.array[index]
                for i in range(self.size - 1, -1, -1):
                    if (1 << i) & bitmap:
                        yield (index * self.size) + i

        def small2big(self):
            for index, bitmap in enumerate(self.array):
                for i in range(0, self.size):
                    if (1 << i) & bitmap:
                        yield (index * self.size) + i
