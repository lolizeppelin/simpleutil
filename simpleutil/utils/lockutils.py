# -*- coding: UTF-8 -*-
import time
import heapq
import contextlib

import weakref
import threading
import eventlet
import eventlet.hubs
import eventlet.semaphore

from simpleutil.utils.timeutils import monotonic

hub = eventlet.hubs.get_hub()


def avoid_making_same_scheduled_time():
    """Default eventlet.hubs use time.time() as order key
    time.time() can not guarantee the accuracy of time
    If schedule_call_global too fast
    That will lead to an order error
    So call eventlet.sleep(0) to avoid
    """
    s = time.time()
    while time.time() == s:
        eventlet.sleep(0)


class DummyLock(object):
    def acquire(self):
        pass

    def release(self):
        pass

    def __enter__(self):
        self.acquire()

    def __exit__(self, type, value, traceback):
        self.release()

    def set_defalut_priority(self, priority):
        pass

    @contextlib.contextmanager
    def priority(self, priority):
        self.acquire()
        try:
            yield
        finally:
            self.release()


class PriorityGreenlet(object):
    """Greenlet with priority
    """
    def __init__(self, priority, greenlet):
        self.priority = priority
        self.greenlet = greenlet

    def __lt__(self, other):
        """Priority is the value for sort"""
        # if self.priority == priority.level:
        #     return id(self.greenlet) < id(other.greenlet)
        return self.priority < other.priority


class PriorityLock(DummyLock):
    """lock with priority
    code copy from Semaphore
    """
    def __init__(self):
        self.locked = False
        self._waiters = []
        self.default_priority = 0

    def set_defalut_priority(self, priority):
        """set defalut priority of lock
        defalut priority is 0
        zero is the highest lock
        you can set it lower if you want
        """
        if not isinstance(priority, int) or self.locked:
            raise RuntimeError('Priority not int or Lock is Locked')
        self.default_priority = priority

    def release(self):
        self.locked = False
        if self._waiters:
            waiter = heapq.heappop(self._waiters)
            hub.schedule_call_global(0, waiter.greenlet.switch)

    def acquire(self):
        """Alloc a lock with default priority"""
        self.acquire_with_priority(self.default_priority)

    def acquire_with_priority(self, priority):
        """Implement of alloc lock"""
        current_thread = eventlet.getcurrent()
        for _waiters in self._waiters:
            # 避免当前线程再锁
            if current_thread is _waiters.greenlet:
                return
        if self.locked:
            locker = PriorityGreenlet(priority, current_thread)
            heapq.heappush(self._waiters, locker)
            hub.switch()
        self.locked = True

    @contextlib.contextmanager
    def priority(self, priority):
        """Alloc a lock with specific priority"""
        self.acquire_with_priority(priority)
        try:
            yield
        finally:
            self.release()


class OrderedLock(DummyLock):

    def __init__(self):
        """waiters empty means not locked"""
        self._waiters = set()

    def acquire(self):
        current_thread = eventlet.getcurrent()
        if current_thread in self._waiters:
            return
        if self._waiters:
            self._waiters.add(current_thread)
            hub.switch()
        else:
            self._waiters.add(current_thread)

    def release(self):
        current_thread = eventlet.getcurrent()
        if self._waiters:
            last = self._waiters.pop()
            if last is not current_thread:
                hub.schedule_call_global(0, last.switch)
                avoid_making_same_scheduled_time()

    def wait(self, timeout=None):
        current_thread = eventlet.getcurrent()
        if current_thread in self._waiters:
            return
        if timeout is None:
            self.acquire()
        else:
            s = monotonic()
            while True:
                if self._waiters:
                    if monotonic() - s >= timeout:
                        return
                    eventlet.sleep(0)
                else:
                    # TODO recheck this code by gcy
                    self.acquire()

    def notify(self):
        current_thread = eventlet.getcurrent()
        if self._waiters:
            last = self._waiters.pop()
            if last is not current_thread:
                hub.schedule_call_global(0, last.switch)
                avoid_making_same_scheduled_time()

    def notify_all(self):
        while self._waiters:
            self.notify()

    notifyAll = notify_all


class Semaphores(object):
    """A garbage collected container of semaphores.

    This collection internally uses a weak value dictionary so that when a
    semaphore is no longer in use (by any threads) it will automatically be
    removed from this container by the garbage collector.

    .. versionadded:: 0.3
    """

    def __init__(self):
        self._semaphores = weakref.WeakValueDictionary()
        self._lock = threading.Lock()

    def get(self, name):
        """Gets (or creates) a semaphore with a given name.

        :param name: The semaphore name to get/create (used to associate
                     previously created names with the same semaphore).

        Returns an newly constructed semaphore (or an existing one if it was
        already created for the given name).
        """
        with self._lock:
            try:
                return self._semaphores[name]
            except KeyError:
                sem = threading.Semaphore()
                self._semaphores[name] = sem
                return sem

    def __len__(self):
        """Returns how many semaphores exist at the current time."""
        return len(self._semaphores)
