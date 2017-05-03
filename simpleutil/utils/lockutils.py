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
        self.priority_lock = {}

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