import os
import sys
import fcntl
import errno
import ctypes
import ctypes.util

from simpleutil.utils import systemutils


class CtypesLibcINotify(object):
    """
    Abstract class wrapping access to inotify's functions. This is an
    internal class.
    """

    def __init__(self):
        self._libc = None
        self._get_errno_func = None

    def init(self):
        assert ctypes

        try_libc_name = 'c'
        if systemutils.FREEBSD:
            try_libc_name = 'inotify'

        libc_name = None
        try:
            libc_name = ctypes.util.find_library(try_libc_name)
        except (OSError, IOError):
            pass  # Will attemp to load it with None anyway.

        self._libc = ctypes.CDLL(libc_name, use_errno=True)
        self._get_errno_func = ctypes.get_errno

        # Eventually check that libc has needed inotify bindings.
        if (not hasattr(self._libc, 'inotify_init') or
                not hasattr(self._libc, 'inotify_add_watch') or
                not hasattr(self._libc, 'inotify_rm_watch')):
            return False

        self._libc.inotify_init.argtypes = []
        self._libc.inotify_init.restype = ctypes.c_int
        self._libc.inotify_add_watch.argtypes = [ctypes.c_int, ctypes.c_char_p,
                                                 ctypes.c_uint32]
        self._libc.inotify_add_watch.restype = ctypes.c_int
        self._libc.inotify_rm_watch.argtypes = [ctypes.c_int, ctypes.c_int]
        self._libc.inotify_rm_watch.restype = ctypes.c_int
        return True

    def _inotify_init(self):
        if self._libc is None:
            self.init()
        assert self._libc is not None
        return self._libc.inotify_init()

    def inotify_init(self):
        return self._inotify_init()

    def get_errno(self):
        """
        Return None is no errno code is available.
        """
        return self._get_errno()

    def str_errno(self):
        code = self.get_errno()
        if code is None:
            return 'Errno: no errno support'
        return 'Errno=%s (%s)' % (os.strerror(code), errno.errorcode[code])

    def inotify_add_watch(self, fd, pathname, mask):
        # Unicode strings must be encoded to string prior to calling this
        # method.
        assert isinstance(pathname, str)
        return self._inotify_add_watch(fd, pathname, mask)

    def inotify_rm_watch(self, fd, wd):
        return self._inotify_rm_watch(fd, wd)

    def _get_errno(self):
        if self._get_errno_func is not None:
            return self._get_errno_func()
        return None

    def _inotify_add_watch(self, fd, pathname, mask):
        assert self._libc is not None
        pathname = ctypes.create_string_buffer(pathname)
        return self._libc.inotify_add_watch(fd, pathname, mask)

    def _inotify_rm_watch(self, fd, wd):
        assert self._libc is not None
        return self._libc.inotify_rm_watch(fd, wd)
