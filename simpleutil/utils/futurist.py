import eventlet
import eventlet.hubs
import functools

from eventlet.semaphore import Semaphore
from simpleutil.utils import threadgroup

NOT_FINISH = object()

hub = eventlet.hubs.get_hub()


class CancelledError(Exception):
    """"""


class Future(object):

    def __init__(self, func):
        self._func = func
        self._thread = None
        self._result = NOT_FINISH
        self.canceled = False

    def link(self, thread):
        if self._thread:
            if thread is not  self._thread:
                raise RuntimeError('Do not link twice')
        self._thread = thread

    def __call__(self):
        self._result = self._func()

    def result(self, timeout=None):
        if self.canceled:
            raise CancelledError('Future has been canceled')
        if self._result is not NOT_FINISH:
            return self._result
        if timeout is None:
            self._thread.wait()
            return self._result
        else:
            me = eventlet.getcurrent()
            # switch back when thread finished
            self._thread.link(me.switch)
            # switch back when timeout
            timer = hub.schedule_call_global(timeout, me.switch)
            # swith to main hub
            # switch back by thread done, cancel timer
            if hub.switch():
                timer.cancel()
            return self._result

    def cancel(self):
        if self._result is not NOT_FINISH:
            raise RuntimeError('Work has been finished')
        self._thread.stop()
        self.canceled = True


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
        thread = self._pool.add_thread(fut)
        fut.link(thread)
        return fut

    def shutdown(self, wait=True):
        with self._shutdown_lock:
            if not self._shutdown:
                self._pool.stop(graceful=wait)


class SynchronousExecutor(GreenThreadPoolExecutor):

    def __init__(self):
        super(SynchronousExecutor, self).__init__(max_workers=1)

    def _submit(self, fn, *args, **kwargs):
        func = functools.partial(fn, *args, **kwargs)
        fut = Future(func)
        thread = self._pool.add_thread(fut)
        fut.link(thread)
        thread.wait()
        return fut
