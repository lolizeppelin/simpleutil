class BitMap(object):

    def __init__(self, max):
        self.max = max
        self.size = 64 if max >= (1 << 32) else 32
        self.array = [0] * (int(max / self.size) + 1)

    def add(self, num):
        assert num > 0 and num < self.max
        self.array[num / self.size] |= (1 << (num % self.size))

    def has(self, num):
        assert num > 0 and num < self.max
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
