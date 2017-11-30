import test
import eventlet
import eventlet.hubs
from simpleutil.utils.lockutils import PriorityLock


lock = PriorityLock()

lock.set_defalut_priority(2)
lock.set_defalut_priority(0)

with lock:
    print 'get lock success'

with lock.priority(1):
    print 'get priority lock success\n'

def locker_0():
    with lock:
        print 'locker 0 success'
        eventlet.sleep(1)
        print 'locker 0 unlock'

def locker_1():
    with lock.priority(1):
        print 'get lokcer_1'
    print 'out lock 1'

def locker_2():
    with lock.priority(2):
        print 'get lokcer_2'
    print 'out lock 2'

def locker_3():
    with lock.priority(3):
        print 'get lokcer_3'
    print 'out lock 3'

def locker_none():
    with lock:
        print 'get lokcer_none'
    print 'out lock none'


eventlet.spawn_n(locker_0)
# To sure thread locker_0 in in front of next
eventlet.sleep(0)
eventlet.spawn_n(locker_3)
eventlet.spawn_n(locker_2)
eventlet.spawn_n(locker_1)
eventlet.spawn_n(locker_2)
eventlet.spawn_n(locker_3)
eventlet.spawn_n(locker_1)
eventlet.spawn_n(locker_1)
eventlet.spawn_n(locker_1)
eventlet.spawn_n(locker_none)
# to print before sys exit
eventlet.sleep(1.5)


# while True:
#     eventlet.sleep(0)
#
# print '\nall finish'
