try:
    from simpleutil.utils import _cutils


    class BitMap(_cutils.bitMap):

        def __init__(self, max):
            if max <= 0:
                raise ValueError('Bit map init value error')
            super(_cutils.bitMap, self).__init__(max)

        def add(self, num):
            assert num > 0 and num <= self.max
            _cutils.bitMap.add(self, num)

        def has(self, num):
            assert num > 0 and num <= self.max
            return _cutils.bitMap.has(self, num)

        def all(self, reverse=False):
            return self.small2big() if reverse else self.big2small()

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

        def __init__(self, max):
            if max <= 0:
                raise ValueError('Bit map init value error')
            self.max = max
            self.size = 64 if max >= (1 << 32) else 32
            self.array = [0] * (int(max / self.size) + 1)

        def add(self, num):
            assert num > 0 and num <= self.max
            self.array[num / self.size] |= (1 << (num % self.size))

        def has(self, num):
            assert num > 0 and num <= self.max
            return (self.array[num / self.size] & (1 << (num % self.size)) > 0)

        def all(self, reverse=False):
            return self.small2big() if reverse else self.big2small()

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
