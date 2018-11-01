import os
# import sys
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


def _handle_exitstatus(sts, _WIFSIGNALED=os.WIFSIGNALED,
        _WTERMSIG=os.WTERMSIG, _WIFEXITED=os.WIFEXITED,
        _WEXITSTATUS=os.WEXITSTATUS):
    # This method is called (indirectly) by __del__, so it cannot
    # refer to anything outside of its local scope."""
    if _WIFSIGNALED(sts):
        sig = -_WTERMSIG(sts)
        raise ExitBySIG('sub process exit with by signal, maybe timeout')
    elif _WIFEXITED(sts):
        return _WEXITSTATUS(sts)
    else:
        # Should never happen
        raise RuntimeError("Unknown child exit status!")


def _eintr_retry_call(func, *args):
    while True:
        try:
            return func(*args)
        except (OSError, IOError) as e:
            if e.errno == errno.EINTR:
                continue
            raise


def wait(pid, timeout=None):
    # copy from subprocess
    used_time = 0.0
    returncode = None
    kill = False
    echild = False
    while returncode is None:
        try:
            _pid, sts = _eintr_retry_call(os.waitpid, pid, 0)
        except OSError as e:
            if e.errno != errno.ECHILD:
                raise
            # This happens if SIGCLD is set to be ignored or waiting
            # for child processes has otherwise been disabled for our
            # process.  This child is dead, we can't get the status.
            echild = True
            _pid = pid
            sts = 0
        # Check the pid and loop as waitpid has been known to return
        # 0 even without WNOHANG in odd situations.  issue14396.
        if pid == _pid:
            returncode = _handle_exitstatus(sts)
            break

        if timeout and used_time > timeout:
            if not kill:
                os.kill(pid, signal.SIGTERM)
            else:
                os.kill(pid, signal.SIGKILL)
        else:
            eventlet.sleep(INTERVAL)
            used_time += INTERVAL

    if echild:
        raise UnExceptExit('sup process waitpid get errorno ECHILD')
    if kill:
        raise ExitBySIG('sub process exit with by signal, maybe timeout')
    if returncode != 0:
        raise UnExceptExit('sup process exit code %d' % returncode)


def is_admin():
    return os.getuid() == 0


def run_as_admin():
    if not is_admin():
        raise RuntimeError('User is not admin run with sudo please')
