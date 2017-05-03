# -*- coding: UTF-8 -*-
import heapq
import contextlib

import eventlet
import eventlet.hubs
import eventlet.semaphore

hub = eventlet.hubs.get_hub()


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
        try:
            yield
        finally:
            self.release()


class PriorityGreenlet(object):

    def __init__(self, priority, greenlet):
        self.priority = priority
        self.greenlet = greenlet

    def __lt__(self, other):
        # if self.priority == priority.level:
        #     return id(self.greenlet) < id(other.greenlet)
        return self.priority < other.priority


class PriorityLock(DummyLock):
    """lock with priority
    a copy of Semaphore
    """
    def __init__(self):
        self.locked = False
        self._waiters = []
        self.default_priority = 0
        self.priority_lock = {}

    def set_defalut_priority(self, priority):
        if not isinstance(priority, int) or self.locked:
            raise RuntimeError('Priority not int or Lock is Locked')
        self.default_priority = priority

    def release(self):
        self.locked = False
        if self._waiters:
            waiter = heapq.heappop(self._waiters)
            hub.schedule_call_global(0, waiter.greenlet.switch)

    def acquire(self):
        self.acquire_with_priority(self.default_priority)

    def acquire_with_priority(self, priority):
        current_thread = eventlet.getcurrent()
        for _waiters in self._waiters:
            # 避免当前线程再锁
            if current_thread is _waiters.greenlet:
                return
        if self.locked:
            locker = PriorityGreenlet(priority, current_thread)
            heapq.heappush(self._waiters, locker)
            hub.switch()
            # self._waiters.remove(locker)
        self.locked = True

    @contextlib.contextmanager
    def priority(self, priority):
        self.acquire_with_priority(priority)
        try:
            yield
        finally:
            self.release()