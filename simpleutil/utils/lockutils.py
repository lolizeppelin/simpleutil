# -*- coding: UTF-8 -*-
import time
import heapq
import six
import contextlib

import weakref
import eventlet
import eventlet.hubs
from eventlet.semaphore import Semaphore

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


class Semaphores(object):
    """A garbage collected container of semaphores.

    This collection internally uses a weak value dictionary so that when a
    semaphore is no longer in use (by any threads) it will automatically be
    removed from this container by the garbage collector.

    .. versionadded:: 0.3
    """

    def __init__(self):
        self._semaphores = weakref.WeakValueDictionary()
        self._lock = Semaphore(1)

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
                sem = Semaphore(1)
                self._semaphores[name] = sem
                return sem

    def __len__(self):
        """Returns how many semaphores exist at the current time."""
        return len(self._semaphores)


class LockStack(object):
    """Simple lock stack to get and release many locks.

    An instance of this should **not** be used by many threads at the
    same time, as the stack that is maintained will be corrupted and
    invalid if that is attempted.
    """

    def __init__(self):
        self._stack = []

    def acquire_lock(self, lock):
        gotten = lock.acquire()
        if gotten:
            self._stack.append(lock)
        return gotten

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        while self._stack:
            lock = self._stack.pop()
            try:
                lock.release()
            except Exception:
                pass


class ReaderWriterLock(object):
    """A reader/writer lock.

    This lock allows for simultaneous readers to exist but only one writer
    to exist for use-cases where it is useful to have such types of locks.

    Currently a reader can not escalate its read lock to a write lock and
    a writer can not acquire a read lock while it is waiting on the write
    lock.

    In the future these restrictions may be relaxed.

    This can be eventually removed if http://bugs.python.org/issue8800 ever
    gets accepted into the python standard threading library...
    """

    #: Writer owner type/string constant.
    WRITER = 'w'

    #: Reader owner type/string constant.
    READER = 'r'

    def __init__(self):
        self._writer = None
        self._pendings = []
        self._readers = {}

    @property
    def owner(self):
        """Returns whether the lock is locked by a writer or reader."""
        if self._writer is not None:
            return self.WRITER
        if self._readers:
            return self.READER
        return None

    @contextlib.contextmanager
    def read_lock(self):
        """Context manager that grants a read lock.

        Will wait until no active or pending writers.

        Raises a ``RuntimeError`` if a pending writer tries to acquire
        a read lock.
        """
        me = eventlet.getcurrent()
        i_am_writer = (self._writer == me)
        if self._writer is None or i_am_writer:
            try:
                self._readers[me] = self._readers[me] + 1
            except KeyError:
                self._readers[me] = 1
        else:
            if self._pendings:
                last = self._pendings.pop(0)
                self._pendings.append(me)
                last.switch()
        try:
            yield self
        finally:
            try:
                me_instances = self._readers[me]
                if me_instances > 1:
                    self._readers[me] = me_instances - 1
                else:
                    self._readers.pop(me)
            except KeyError:
                pass
            self.notify()

    @contextlib.contextmanager
    def write_lock(self):
        """Context manager that grants a write lock.

        Will wait until no active readers. Blocks readers after acquiring.

        Raises a ``RuntimeError`` if an active reader attempts to acquire
        a lock.
        """
        me = eventlet.getcurrent()
        i_am_writer = (self._writer == me)
        i_am_reader = (me in self._readers)
        if i_am_reader and not i_am_writer:
            raise RuntimeError("Reader %s to writer privilege"
                               " escalation not allowed" % me)
        if i_am_writer:
            # Already the writer; this allows for basic reentrancy.
            yield self
        else:
            if len(self._readers) == 0 and self._writer is None:
                self._writer = me
            else:
                if self._pendings:
                    last = self._pendings.pop(0)
                    self._pendings.append(me)
                    last.switch()
            try:
                yield self
            finally:
                self._writer = None
                self.notify()

    def notify(self):
        me = eventlet.getcurrent()
        if self._pendings:
            last = self._pendings.pop(0)
            if last is not me:
                hub.schedule_call_global(0, last.switch)
                avoid_making_same_scheduled_time()

    def notify_all(self):
        while self._pendings:
            self.notify()


def read_locked(*args, **kwargs):
    """Acquires & releases a read lock around call into decorated method.

    NOTE(harlowja): if no attribute name is provided then by default the
    attribute named '_lock' is looked for (this attribute is expected to be
    a :py:class:`.ReaderWriterLock`) in the instance object this decorator
    is attached to.
    """

    def decorator(f):
        attr_name = kwargs.get('lock', '_lock')

        @six.wraps(f)
        def wrapper(self, *args, **kwargs):
            rw_lock = getattr(self, attr_name)
            with rw_lock.read_lock():
                return f(self, *args, **kwargs)

        return wrapper

    # This is needed to handle when the decorator has args or the decorator
    # doesn't have args, python is rather weird here...
    if kwargs or not args:
        return decorator
    else:
        if len(args) == 1:
            return decorator(args[0])
        else:
            return decorator


def write_locked(*args, **kwargs):
    """Acquires & releases a write lock around call into decorated method.

    NOTE(harlowja): if no attribute name is provided then by default the
    attribute named '_lock' is looked for (this attribute is expected to be
    a :py:class:`.ReaderWriterLock` object) in the instance object this
    decorator is attached to.
    """

    def decorator(f):
        attr_name = kwargs.get('lock', '_lock')

        @six.wraps(f)
        def wrapper(self, *args, **kwargs):
            rw_lock = getattr(self, attr_name)
            with rw_lock.write_lock():
                return f(self, *args, **kwargs)

        return wrapper

    # This is needed to handle when the decorator has args or the decorator
    # doesn't have args, python is rather weird here...
    if kwargs or not args:
        return decorator
    else:
        if len(args) == 1:
            return decorator(args[0])
        else:
            return decorator


def stlocked(*args, **kwargs):
    """A locking **method** decorator.

    It will look for a provided attribute (typically a lock or a list
    of locks) on the first argument of the function decorated (typically this
    is the 'self' object) and before executing the decorated function it
    activates the given lock or list of locks as a context manager,
    automatically releasing that lock on exit.

    NOTE(harlowja): if no attribute name is provided then by default the
    attribute named '_lock' is looked for (this attribute is expected to be
    the lock/list of locks object/s) in the instance object this decorator
    is attached to.

    NOTE(harlowja): a custom logger (which will be used if lock release
    failures happen) can be provided by passing a logger instance for keyword
    argument ``logger``.
    """

    def decorator(f):
        attr_name = kwargs.get('lock', '_lock')

        @six.wraps(f)
        def wrapper(self, *args, **kwargs):
            attr_value = getattr(self, attr_name)
            if isinstance(attr_value, (tuple, list)):
                with LockStack() as stack:
                    for lock in attr_value:
                        stack.acquire_lock(lock)
                    return f(self, *args, **kwargs)
            else:
                lock = attr_value
                with lock:
                    return f(self, *args, **kwargs)

        return wrapper

    # This is needed to handle when the decorator has args or the decorator
    # doesn't have args, python is rather weird here...
    if kwargs or not args:
        return decorator
    else:
        if len(args) == 1:
            return decorator(args[0])
        else:
            return decorator
