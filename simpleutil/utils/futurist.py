import eventlet
import eventlet.hubs
from eventlet.support.greenlets import GreenletExit
import functools
from collections import Iterable

from eventlet.semaphore import Semaphore
from simpleutil.utils import threadgroup

NOT_FINISH = object()
FINISH = object()
TIMEOUT = object()


class Error(Exception):
    """Base class for all future-related exceptions."""
    pass


class CancelledError(Error):
    """"""


class TimeoutError(Error):
    """The operation exceeded the given deadline."""


class Future(object):

    def __init__(self, func):
        self._func = func
        self._thread = None
        self._state = NOT_FINISH
        self._result = None
        self._exception = None
        self.canceled = False

    def link(self, pool=None):
        if self._state is not NOT_FINISH:
            raise RuntimeError('Do not link finished future')
        if self._thread:
            raise RuntimeError('Do not link twice')
        if pool is None:
            self._thread = threadgroup.Thread(eventlet.spawn(self))
        else:
            self._thread = pool.add_thread(self)

    start = link

    def __call__(self):
        # do not raise anything from _func
        # this Future can not catch any error
        if self.canceled or self._state is not NOT_FINISH:
            raise RuntimeError('Do not call future twice')
        try:
            self._result = self._func()
        except Exception as e:
            self._exception = e
        finally:
            self._state = FINISH

    @property
    def finished(self):
        return self._state is not NOT_FINISH

    @property
    def _return(self):
        if self._state is NOT_FINISH:
            raise RuntimeError('Future is not finishd, do not call for return value')
        if self._exception:
            raise self._exception
        return self._result

    def result(self, timeout=None):
        if self.canceled:
            raise CancelledError('Future has been canceled')
        if self._state is not NOT_FINISH:
            return self._return
        if timeout is None:
            if self._thread is None:
                self._thread = threadgroup.Thread(eventlet.spawn(self))
            try:
                self._thread.wait()
            except GreenletExit:
                if self.canceled:
                    raise CancelledError('Future has been canceled')
                raise RuntimeError('Future unexcept switch back')
            return self._return
        else:
            if not self._thread:
                raise RuntimeError('Future thred is None, async is disable')
            # _finish = object()
            # _timeout = object()
            hub = eventlet.hubs.get_hub()
            me = eventlet.getcurrent()
            # switch back when thread finished
            callback = me.switch
            self._thread.link(callback, FINISH)
            # switch back when timeout
            timer = hub.schedule_call_global(timeout, callback, TIMEOUT)
            # swith to main hub
            # switch back by thread done, cancel timer
            ret = hub.switch()
            if ret is TIMEOUT:
                # call back by timeout timer
                if not self._thread.unlink(callback, FINISH):
                    raise RuntimeError('Remove switch back fail')
                raise TimeoutError('Future fetch result timeout')
            elif isinstance(ret, Iterable) and FINISH in ret:
                timer.cancel()
                if self.canceled:
                    raise CancelledError('Future canceled')
                return self._return
            else:
                raise RuntimeError('Unexcept switch back')

    def cancel(self):
        if self.canceled:
            return
        if self._state is not NOT_FINISH:
            raise RuntimeError('Future has been finished')
        self.canceled = True
        self._thread.stop()


class GreenThreadPoolExecutor(object):

    def __init__(self, max_workers=1000):

        self._max_workers = max_workers
        self._pool = threadgroup.ThreadGroup(thread_pool_size=max_workers)
        self._shutdown_lock = Semaphore(1)
        self._shutdown = False

    @property
    def alive(self):
        """Accessor to determine if the executor is alive/active."""
        return not self._shutdown

    def submit(self, fn, *args, **kwargs):
        with self._shutdown_lock:
            if self._shutdown:
                raise RuntimeError('Can not schedule new futures'
                                   ' after being shutdown')
            return self._submit(fn, *args, **kwargs)

    def _submit(self, fn, *args, **kwargs):
        func = functools.partial(fn, *args, **kwargs)
        fut = Future(func)
        fut.link(self._pool)
        return fut

    def shutdown(self, wait=True):
        with self._shutdown_lock:
            if not self._shutdown:
                self._pool.stop(graceful=wait)


class SynchronousExecutor(GreenThreadPoolExecutor):

    def __init__(self, *args, **kwargs):
        super(SynchronousExecutor, self).__init__(max_workers=1)

    def _submit(self, fn, *args, **kwargs):
        func = functools.partial(fn, *args, **kwargs)
        fut = Future(func)
        fut()
        return fut


def if_future_done(future):
    # future._thread.dead
    return future._result is not NOT_FINISH or \
           future.canceled or \
           future._thread is None


def future_wait(futures, timeout, ok_count=1):
    done = set()
    not_done = set()
    if not futures:
        return done, not_done
    for future in futures:
        if if_future_done(future):
            done.add(future)
        else:
            not_done.add(future)
    if len(done) >= ok_count:
        return done, not_done
    _finish = object()
    _timeout = object()
    me = eventlet.getcurrent()
    callback = me.switch
    for future in not_done:
        future._thread.link(callback, _finish)
    hub = eventlet.hubs.get_hub()
    timer = hub.schedule_call_global(timeout, callback, _timeout)
    count = len(done)
    while True:
        ret = hub.switch()
        if ret is _timeout:
            # swith by timeout
            break
        elif isinstance(ret, Iterable) and _finish in ret:
            count += 1
            # all success
            if count == ok_count:
                timer.cancel()
                break
        else:
            raise RuntimeError('Wait future unexcept switch back')
    tmp = set()
    for future in not_done:
        if if_future_done(future):
            done.add(future)
            tmp.add(future)
        else:
            # still not done!
            if not future._thread.unlink(callback, _finish):
                raise RuntimeError('unlink switch function')
    not_done = not_done - tmp
    return done, not_done


def wait_for_any(futures, timeout):
    return future_wait(futures, timeout, ok_count=1)


def wait_for_all(futures, timeout):
    return future_wait(futures, timeout, ok_count=len(futures))
