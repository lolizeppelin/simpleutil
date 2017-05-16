from simpleutil.utils.uuidutils import Gprimarykey
import time

guid = Gprimarykey(sid=1, pid=2)

key = guid()
t = int(time.time()*1000)

print 'primary key', key
print 'time.time',t
print 'timeformat', guid.timeformat(key)
print 'sid format', guid.sidformat(key)

# while True:
#     x = guid()
#     print x()

x = '1'*11 + '0'*11

x = int(x, 2)
print 'max', x