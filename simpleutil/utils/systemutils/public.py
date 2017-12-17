# -*- coding: UTF-8 -*-
import os
import sys
import errno
import eventlet
import contextlib


# copy from psutils
POSIX = os.name == "posix"
WINDOWS = os.name == "nt"
LINUX = sys.platform.startswith("linux")
OSX = sys.platform.startswith("darwin")
FREEBSD = sys.platform.startswith("freebsd")
OPENBSD = sys.platform.startswith("openbsd")
NETBSD = sys.platform.startswith("netbsd")
BSD = FREEBSD or OPENBSD or NETBSD
SUNOS = sys.platform.startswith("sunos") or sys.platform.startswith("solaris")
AIX = sys.platform.startswith('aix')

INTERVAL = 0.01



class ExitBySIG(Exception):
    """"""


class UnExceptExit(Exception):
    """"""


def empty(*args, **kwargs):
    """do nothing"""

@contextlib.contextmanager
def empty_context(*args, **kwargs):
    yield


def find_executable(executable):
    if os.path.exists(executable):
        if not os.path.isfile(executable):
            raise
        return os.path.abspath(executable)
    if WINDOWS:
        if not executable.endswith(('.exe', '.EXE')):
            executable += '.exe'
    paths = os.environ['PATH'].split(os.pathsep)
    for path in paths:
        if not os.path.exists(path):
            continue
        for _file in os.listdir(path):
            if executable.lower() == _file.lower():
                full_path = os.path.join(path, _file)
                if os.path.isfile(full_path):
                    return full_path
    raise NotImplementedError('executable %s not found' % executable)


def subwait(sub, timeout=None):
        used_time = 0.0
        timeout = float(timeout) if timeout else None
        while True:
            try:
                # same as eventlet.green.os.wait
                if sub.poll() is None:
                    if timeout and used_time > timeout:
                        sub.terminate()
                        if sub.poll() is None:
                            sub.kill()
                        sub.wait()
                        raise ExitBySIG('sub process exit with by signal, maybe timeout')
                    eventlet.sleep(INTERVAL)
                    used_time += INTERVAL
                    continue
                else:
                    code = sub.wait()
                    if code != 0:
                        raise UnExceptExit('sup process exit code %d' % code)
                    break
            except OSError as exc:
                if exc.errno not in (errno.EINTR, errno.ECHILD):
                    raise OSError('waitpid get errorno %d' % exc.errno)
                continue
