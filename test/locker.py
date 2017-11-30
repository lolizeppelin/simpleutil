from simpleutil.utils.timeutils import monotonic
import time

l = []


import heapq

class T(object):

    def __init__(self, level, t=monotonic()):
        self.level = level
        self.t = t

    def __lt__(self, other):
        return self.level < other.level

heapq.heappush(l,T(1))
time.sleep(0.001)

heapq.heappush(l,T(2))
time.sleep(0.001)

heapq.heappush(l,T(2))
time.sleep(0.001)

heapq.heappush(l,T(1, 0))
time.sleep(0.001)

while l:
    x = heapq.heappop(l)
    print x.level, x.t

