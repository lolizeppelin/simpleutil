# -*- coding: UTF-8 -*-
# 代码来源oslo.service-1.8.0.oslo_service.threadgroup.py
from simpleutil.log import log as logging

import eventlet
from eventlet import greenpool

LOG = logging.getLogger(__name__)


# def _on_thread_done(_greenthread, group, thread):
#     """Callback function to be passed to GreenThread.link() when we spawn().
#
#     Calls the :class:`ThreadGroup` to notify it to remove this thread from
#     the associated group.
#     """
#     group.thread_done(thread)


class Thread(object):
    """Wrapper around a greenthread.

     Holds a reference to the :class:`ThreadGroup`. The Thread will notify
     the :class:`ThreadGroup` when it has done so it can be removed from
     the threads list.
    """
    def __init__(self, thread, group):
        self.thread = thread
        self.thread.link(self.on_thread_done, group)
        self._ident = id(thread)

    def on_thread_done(self, greenthread, group):
        """Callback function to be passed to GreenThread.link() when we spawn().
        Calls the :class:`ThreadGroup` to notify it to remove this thread from
        the associated group.
        """
        group.thread_done(self)

    @property
    def ident(self):
        return self._ident

    def stop(self):
        self.thread.kill()

    def wait(self):
        return self.thread.wait()

    def link(self, func, *args, **kwargs):
        self.thread.link(func, *args, **kwargs)

    def unlink(self, func, *args, **kwargs):
        # fix buf of unlink
        target = None
        for funcs in getattr(self.thread, '_exit_funcs', []):
            if funcs[0] is func and funcs[1] == args and funcs[2] == kwargs:
                target = funcs
                break
        if target:
            self.thread._exit_funcs.remove(target)
            return True
        return False

    @property
    def dead(self):
        return self.thread.dead


class ThreadGroup(object):
    """The point of the ThreadGroup class is to:
    # 去除了定时器相关的变量和方法
    # 定时器相关实现将专写一个可分布的定时器进程
    """
    def __init__(self, thread_pool_size=10):
        self.pool = greenpool.GreenPool(thread_pool_size)
        self.threads = []

    def add_thread(self, callback, *args, **kwargs):
        gt = self.pool.spawn(callback, *args, **kwargs)
        th = Thread(gt, self)
        self.threads.append(th)
        return th

    def add_thread_n(self, callback, *args, **kwargs):
        self.pool.spawn_n(callback, *args, **kwargs)

    def thread_done(self, thread):
        self.threads.remove(thread)

    def _perform_action_on_threads(self, action_func, on_error_func):
        # current = threading.current_thread()
        # threading.current_thread is eventlet.getcurrent
        # after patched, so do not need threading
        current = eventlet.getcurrent()
        # Iterate over a copy of self.threads so thread_done doesn't
        # modify the list while we're iterating
        for x in self.threads[:]:
            if x.ident == id(current):
                # Don't perform actions on the current thread.
                continue
            try:
                action_func(x)
            except eventlet.greenlet.GreenletExit:  # nosec
                # greenlet exited successfully
                pass
            except Exception:
                on_error_func(x)

    def _stop_threads(self):
        self._perform_action_on_threads(
            lambda x: x.stop(),
            lambda x: LOG.exception('Error stopping thread.'))

    def stop(self, graceful=False):
        """stop function has the option of graceful=True/False.

        * In case of graceful=True, wait for all threads to be finished.
          Never kill threads.
        * In case of graceful=False, kill threads immediately.
        """
        if graceful:
            # In case of graceful=True, wait for all threads to be
            # finished, never kill threads
            self.wait()
        else:
            # In case of graceful=False(Default), kill threads
            # immediately
            self._stop_threads()

    def wait(self):
        self._perform_action_on_threads(
            lambda x: x.wait(),
            lambda x: LOG.exception('Error waiting on thread.'))
        # For add_thread_n
        self.pool.waitall()
