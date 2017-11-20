# -*- coding: UTF-8 -*-
import os
import eventlet
import socket
import contextlib
import pwd
import grp
import fcntl
import errno
import signal

import logging

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


def setuid(user_id_or_name):
    try:
        new_uid = int(user_id_or_name)
    except (TypeError, ValueError):
        new_uid = pwd.getpwnam(user_id_or_name).pw_uid
    if new_uid != 0:
        try:
            os.setuid(new_uid)
        except OSError:
            msg = 'Failed to set uid %s' % new_uid
            logging.critical(msg)
            raise


def setgid(group_id_or_name):
    try:
        new_gid = int(group_id_or_name)
    except (TypeError, ValueError):
        new_gid = grp.getgrnam(group_id_or_name).gr_gid
    if new_gid != 0:
        try:
            os.setgid(new_gid)
        except OSError:
            msg = 'Failed to set gid %s' % new_gid
            logging.critical(msg)
            raise


def drop_privileges(user=None, group=None):
    """Drop privileges to user/group privileges."""
    if user is None and group is None:
        return

    if os.geteuid() != 0:
        msg = 'Root permissions are required to drop privileges.'
        logging.critical(msg)
        raise OSError(msg)

    if group is not None:
        try:
            os.setgroups([])
        except OSError:
            msg = 'Failed to remove supplemental groups'
            logging.critical(msg)
            raise
        setgid(group)

    if user is not None:
        setuid(user)

    logging.info("Process runs with uid/gid: %(uid)s/%(gid)s" % {'uid': os.getuid(), 'gid': os.getgid()})


# -----------------------下面是systemd相关通知函数------------------#

def _abstractify(socket_name):
    if socket_name.startswith('@'):
        # abstract namespace socket
        socket_name = '\0%s' % socket_name[1:]
    return socket_name


def _sd_notify(unset_env, msg):
    notify_socket = os.getenv('NOTIFY_SOCKET')
    if notify_socket:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        with contextlib.closing(sock):
            try:
                sock.connect(_abstractify(notify_socket))
                sock.sendall(msg)
                if unset_env:
                    del os.environ['NOTIFY_SOCKET']
            except EnvironmentError:
                pass
                # LOG.debug("Systemd notification failed", exc_info=True)


def notify():
    """Send notification to Systemd that service is ready.

    For details see
    http://www.freedesktop.org/software/systemd/man/sd_notify.html
    """
    _sd_notify(False, 'READY=1')


def notify_once():
    """Send notification once to Systemd that service is ready.

    Systemd sets NOTIFY_SOCKET environment variable with the name of the
    socket listening for notifications from services.
    This method removes the NOTIFY_SOCKET environment variable to ensure
    notification is sent only once.
    """
    _sd_notify(True, 'READY=1')


def onready(notify_socket, timeout):
    """Wait for systemd style notification on the socket.

    :param notify_socket: local socket address
    :type notify_socket:  string
    :param timeout:       socket timeout
    :type timeout:        float
    :returns:             0 service ready
                          1 service not ready
                          2 timeout occurred
    """
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    sock.bind(_abstractify(notify_socket))
    with contextlib.closing(sock):
        try:
            msg = sock.recv(512)
        except socket.timeout:
            return 2
        if 'READY=1' in msg:
            return 0
        else:
            return 1


def wait(pid, timeout=None):
    used_time = 0.0
    timeout = float(timeout) if timeout else None
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
