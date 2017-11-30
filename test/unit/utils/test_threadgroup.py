import eventlet

from simpleutil.utils import threadgroup



def error_test():
    eventlet.sleep(1)
    raise NotImplementedError

def warp(func):
    try:
        func()
    except Exception as e:
        print 'wtfffffffffff'
        print e.__class__.__name__


pool = threadgroup.ThreadGroup()

th = pool.add_thread(warp, error_test)


print 'start ed '

pool.wait()

print th.thread._exit_event.ready()

import contextlib

@contextlib.contextmanager
def empty_lock():
    yield


x = empty_lock()
with x:
    print 'wtf'

print 'ok'


import functools

class W(object):

    def x(self, a):
        print 'x get', a


    def y(self):
        f = functools.partial(self.x, '1')
        return f

t = W()


ff = t.y()

print ff
type(ff)

ff()
