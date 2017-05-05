from simpleutil.utils.uuidutils import Gprimarykey


guid = Gprimarykey(sid=128)

key = guid()

print key, '~~~~~~~'

import time
print int(time.time()*1000)
print guid.timeformat(key)
print guid.sidformat(key)

while True:
    x = guid()
    print x