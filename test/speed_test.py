import time
from simpleutil.utils.timeutils import monotonic

i = 30000000

s = time.time()
while i:
    monotonic()
    i = i - 1

print time.time() - s



i = 30000000

s = time.time()
while i:
    time.time()
    i = i - 1

print time.time() - s