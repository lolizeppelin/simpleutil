import os
import fcntl
import errno
import signal

import eventlet

from simpleutil.utils.systemutils import ExitBySIG
from simpleutil.utils.systemutils import UnExceptExit
from simpleutil.utils.systemutils import INTERVAL

def set_cloexec_flag(fd, cloexec=True):
    try:
        cloexec_flag = fcntl.FD_CLOEXEC
    except AttributeError:
        cloexec_flag = 1

    old = fcntl.fcntl(fd, fcntl.F_GETFD)
    if cloexec:
        fcntl.fcntl(fd, fcntl.F_SETFD, old | cloexec_flag)
    else:
        fcntl.fcntl(fd, fcntl.F_SETFD, old & ~cloexec_flag)


def wait(pid, timeout=None):
    used_time = 0.0
    timeout = float(timeout) + 0.1 if timeout else None
    while True:
        try:
            # same as eventlet.green.os.wait
            _pid, status = os.waitpid(pid, os.WNOHANG)
            if not _pid:
                if timeout and used_time > timeout:
                    os.kill(pid, signal.SIGTERM)
                    _pid, status = os.waitpid(pid, os.WNOHANG)
                    if not _pid:
                        os.kill(pid, signal.SIGKILL)
                    os.waitpid(pid, 0)
                    raise ExitBySIG('sub process terminated or killed')
                eventlet.sleep(INTERVAL)
                used_time += INTERVAL
                continue
            else:
                if not os.WIFSIGNALED(status):
                    code = os.WEXITSTATUS(status)
                    if code != 0:
                        raise UnExceptExit('sup process exit code %d' % code)
                    break
                else:
                    raise ExitBySIG('sub process exit with by signal, maybe timeout')
        except OSError as exc:
            if exc.errno not in (errno.EINTR, errno.ECHILD):
                raise OSError('waitpid get errno %d' % exc.errno)
            continue
