import os
import array
import struct
import fcntl
import termios
import select

from simpleutil.log import log as logging
from simpleutil import system
from simpleutil.posix.inotify import event
from simpleutil.posix.inotify.clib import CtypesLibcINotify

LOG = logging.getLogger(__name__)


def format_path(path):
    """
    Format path to its internal (stored in watch manager) representation.
    """
    # Unicode strings are converted back to strings, because it seems
    # that inotify_add_watch from ctypes does not work well when
    # it receives an ctypes.create_unicode_buffer instance as argument.
    # Therefore even wd are indexed with bytes string and not with
    # unicode paths.
    if isinstance(path, unicode):
        path = path.encode(system.SYSENCODE)
    return os.path.normpath(path)


class Notifier(object):

    def __init__(self, path, threshold=0):

        if not os.path.isfile(path):
            raise RuntimeError('Just for file')
        self.path = format_path(path)
        self.inotify =  CtypesLibcINotify()
        self._fd = None
        self._threshold = threshold
        self.wds = set()

    def start(self):
        if self._fd:
            LOG.waring('Do not call notifier start twice')
        else:
            self._fd = self.inotify.inotify_init()

    def close(self):
        if not self._fd:
            LOG.waring('Do not call notifier before start')
        else:
            self.del_watch()
            os.close(self._fd)

    def read_events(self):
        """
        Read events from device, build _RawEvents, and enqueue them.
        """
        buf_ = array.array('i', [0])
        # get event queue size
        if fcntl.ioctl(self._fd, termios.FIONREAD, buf_, 1) == -1:
            return
        queue_size = buf_[0]
        if queue_size < self._threshold:
            LOG.debug('(fd: %d) %d bytes available to read but threshold is '
                      'fixed to %d bytes', self._fd, queue_size,
                      self._threshold)
            return

        r = os.read(self._fd, queue_size)
        LOG.debug('Event queue size: %d', queue_size)
        event_queue = set()
        rsum = 0  # counter
        while rsum < queue_size:
            s_size = 16
            # Retrieve wd, mask, cookie and fname_len
            wd, mask, cookie, fname_len = struct.unpack('iIII',
                                                        r[rsum:rsum+s_size])

            # Retrieve name
            fname, = struct.unpack('%ds' % fname_len,
                                   r[rsum + s_size:rsum + s_size + fname_len])
            rsum += s_size + fname_len
            if mask & event.IN_IGNORED:
                continue
            rawevent = dict(wd=wd, mask=mask, cookie=cookie, fname=fname)
            event_queue.add(rawevent)
        return event_queue

    def loop(self, callable):
        watch_list = [self._fd, ]
        empty_w_list = []
        empty_e_list = []
        while True:
            if not self._fd:
                break
            try:
                # select is eventlet.green.select
                rlist, wlist, errlist = select.select(watch_list, empty_w_list, empty_e_list)
            except (OSError, IOError):
                continue
            else:
                if rlist:
                    callable(self.read_events())

    def add_watch(self, mask):
        wd = self.inotify.inotify_add_watch(self._fd, self.path, mask)
        if wd < 0:
            msg = 'add_watch: cannot watch %s WD=%d, %s' % (self.path, wd, self.inotify.str_errno())
            LOG.error(msg)
            raise
        self.wds.add(wd)
        return wd

    def del_watch(self):
        while self.wds:
            wd = self.wds.pop()
            ret = self.inotify.inotify_rm_watch(self._fd, wd)
            if ret < 0:
                msg = 'del_watch: cannot remove WD=%d, %s' % (wd, self.inotify.str_errno())
                LOG.error(msg)
