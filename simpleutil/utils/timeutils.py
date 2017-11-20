# Copyright 2011 OpenStack Foundation.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Time related utilities and helper functions.
"""
import os
import time
import datetime
import ntplib
# import sys
import ctypes
import ctypes.util

from simpleutil.utils import systemutils
from simpleutil.utils import reflection


# ISO 8601 extended time format with microseconds
_ISO8601_TIME_FORMAT_SUBSECOND = '%Y-%m-%dT%H:%M:%S.%f'
_ISO8601_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S'
PERFECT_TIME_FORMAT = _ISO8601_TIME_FORMAT_SUBSECOND
_BUILTIN_MODULES = ('builtins', '__builtin__', '__builtins__', 'exceptions')
_MAX_DATETIME_SEC = 59

ntpclinet = ntplib.NTPClient()

# copy from monotonic
if systemutils.WINDOWS:
    kernel32 = ctypes.windll.kernel32
    GetTickCount64 = getattr(kernel32, 'GetTickCount64', None)
    if GetTickCount64:
        # Windows Vista / Windows Server 2008 or newer.
        GetTickCount64.restype = ctypes.c_ulonglong

        def monotonic():
            """Monotonic clock, cannot go backward."""
            return GetTickCount64() / 1000.0
    else:
        raise RuntimeError
else:
    try:
        clock_gettime = ctypes.CDLL(ctypes.util.find_library('c'),
                                    use_errno=True).clock_gettime
    except AttributeError:
        clock_gettime = ctypes.CDLL(ctypes.util.find_library('rt'),
                                    use_errno=True).clock_gettime

    class timespec(ctypes.Structure):
        """Time specification, as described in clock_gettime(3)."""
        _fields_ = (('tv_sec', ctypes.c_long),
                    ('tv_nsec', ctypes.c_long))

    # if sys.platform.startswith('linux'):
    if systemutils.LINUX:
        CLOCK_MONOTONIC = 1
    if systemutils.FREEBSD:
        CLOCK_MONOTONIC = 4
    if systemutils.SUNOS:
        CLOCK_MONOTONIC = 4
    if systemutils.BSD:
        CLOCK_MONOTONIC = 3
    if systemutils.AIX:
        CLOCK_MONOTONIC = ctypes.c_longlong(10)

    def monotonic():
        """Monotonic clock, cannot go backward."""
        ts = timespec()
        if clock_gettime(CLOCK_MONOTONIC, ctypes.pointer(ts)):
            errno = ctypes.get_errno()
            raise OSError(errno, os.strerror(errno))
        return ts.tv_sec + ts.tv_nsec / 1.0e9

if monotonic() - monotonic() > 0:
    raise ValueError('monotonic() is not monotonic!')


class RealNow(object):

    def __init__(self):
        self.__diff = time.time() - monotonic()

    def update_diff(self, diff):
        self.__diff = diff

    def __call__(self):
        if self.__diff is None:
            return time.time()
        return monotonic() + self.__diff


realnow = RealNow()
now = monotonic


def utcnow(t=None):
    if not t:
        t = realnow()
    return datetime.datetime.fromtimestamp(int(t))


class Split(object):
    """A *immutable* stopwatch split.

    See: http://en.wikipedia.org/wiki/Stopwatch for what this is/represents.

    .. versionadded:: 1.4
    """

    __slots__ = ['_elapsed', '_length']

    def __init__(self, elapsed, length):
        self._elapsed = elapsed
        self._length = length

    @property
    def elapsed(self):
        """Duration from stopwatch start."""
        return self._elapsed

    @property
    def length(self):
        """Seconds from last split (or the elapsed time if no prior split)."""
        return self._length

    def __repr__(self):
        r = reflection.get_class_name(self, fully_qualified=False)
        r += "(elapsed=%s, length=%s)" % (self._elapsed, self._length)
        return r


class StopWatch(object):
    """A simple timer/stopwatch helper class.

    Inspired by: apache-commons-lang java stopwatch.

    Not thread-safe (when a single watch is mutated by multiple threads at
    the same time). Thread-safe when used by a single thread (not shared) or
    when operations are performed in a thread-safe manner on these objects by
    wrapping those operations with locks.

    It will use the `monotonic`_ pypi library to find an appropriate
    monotonically increasing time providing function (which typically varies
    depending on operating system and python version).

    .. _monotonic: https://pypi.python.org/pypi/monotonic/

    .. versionadded:: 1.4
    """
    _STARTED = 'STARTED'
    _STOPPED = 'STOPPED'

    def __init__(self, duration=None):
        if duration is not None and duration < 0:
            raise ValueError("Duration must be greater or equal to"
                             " zero and not %s" % duration)
        self._duration = duration
        self._started_at = None
        self._stopped_at = None
        self._state = None
        self._splits = []

    def start(self):
        """Starts the watch (if not already started).

        NOTE(harlowja): resets any splits previously captured (if any).
        """
        if self._state == self._STARTED:
            return self
        self._started_at = now()
        self._stopped_at = None
        self._state = self._STARTED
        self._splits = []
        return self

    @property
    def splits(self):
        """Accessor to all/any splits that have been captured."""
        return tuple(self._splits)

    def split(self):
        """Captures a split/elapsed since start time (and doesn't stop)."""
        if self._state == self._STARTED:
            elapsed = self.elapsed()
            if self._splits:
                length = self._delta_seconds(self._splits[-1].elapsed, elapsed)
            else:
                length = elapsed
            self._splits.append(Split(elapsed, length))
            return self._splits[-1]
        else:
            raise RuntimeError("Can not create a split time of a stopwatch"
                               " if it has not been started or if it has been"
                               " stopped")

    def restart(self):
        """Restarts the watch from a started/stopped state."""
        if self._state == self._STARTED:
            self.stop()
        self.start()
        return self

    @staticmethod
    def _delta_seconds(earlier, later):
        # Uses max to avoid the delta/time going backwards (and thus negative).
        return max(0.0, later - earlier)

    def elapsed(self, maximum=None):
        """Returns how many seconds have elapsed."""
        if self._state not in (self._STARTED, self._STOPPED):
            raise RuntimeError("Can not get the elapsed time of a stopwatch"
                               " if it has not been started/stopped")
        if self._state == self._STOPPED:
            elapsed = self._delta_seconds(self._started_at, self._stopped_at)
        else:
            elapsed = self._delta_seconds(self._started_at, now())
        if maximum is not None and elapsed > maximum:
            elapsed = max(0.0, maximum)
        return elapsed

    def __enter__(self):
        """Starts the watch."""
        self.start()
        return self

    def __exit__(self, type, value, traceback):
        """Stops the watch (ignoring errors if stop fails)."""
        try:
            self.stop()
        except RuntimeError:  # nosec: errors are meant to be ignored
            pass

    def leftover(self, return_none=False):
        """Returns how many seconds are left until the watch expires.

        :param return_none: when ``True`` instead of raising a ``RuntimeError``
                            when no duration has been set this call will
                            return ``None`` instead.
        :type return_none: boolean
        """
        if self._state != self._STARTED:
            raise RuntimeError("Can not get the leftover time of a stopwatch"
                               " that has not been started")
        if self._duration is None:
            if not return_none:
                raise RuntimeError("Can not get the leftover time of a watch"
                                   " that has no duration")
            return None
        return max(0.0, self._duration - self.elapsed())

    def expired(self):
        """Returns if the watch has expired (ie, duration provided elapsed)."""
        if self._state not in (self._STARTED, self._STOPPED):
            raise RuntimeError("Can not check if a stopwatch has expired"
                               " if it has not been started/stopped")
        if self._duration is None:
            return False
        return self.elapsed() > self._duration

    def has_started(self):
        return self._state == self._STARTED

    def has_stopped(self):
        return self._state == self._STOPPED

    def resume(self):
        """Resumes the watch from a stopped state."""
        if self._state == self._STOPPED:
            self._state = self._STARTED
            return self
        else:
            raise RuntimeError("Can not resume a stopwatch that has not been"
                               " stopped")

    def stop(self):
        """Stops the watch."""
        if self._state == self._STOPPED:
            return self
        if self._state != self._STARTED:
            raise RuntimeError("Can not stop a stopwatch that has not been"
                               " started")
        self._stopped_at = monotonic()
        self._state = self._STOPPED
        return self


def ntptime(host, version=2, port=123, timeout=5):
    try:
        stat = ntpclinet.request(host, version, port, timeout=timeout)
    except ntplib.NTPException as e:
        raise RuntimeError('NTP error: ' + e.message)
    return stat


def unix_to_iso(t):
    return datetime.datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S')
