# -*- coding: UTF-8 -*-
import os
import sys
import atexit
import socket
import contextlib
import fcntl
import pwd
import grp
import fcntl

import logging as std_logging
from logging import handlers

from simpleutil.log import log as logging
from simpleutil.config import cfg

STDIN_FILENO = 0
STDOUT_FILENO = 1
STDERR_FILENO = 2

DEVNULL = object()

CONF = cfg.CONF

LOG = logging.getLogger(__name__)


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
            LOG.critical(msg)
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
            LOG.critical(msg)
            raise


def drop_privileges(user=None, group=None):
    """Drop privileges to user/group privileges."""
    if user is None and group is None:
        return

    if os.geteuid() != 0:
        msg = 'Root permissions are required to drop privileges.'
        LOG.critical(msg)
        raise OSError(msg)

    if group is not None:
        try:
            os.setgroups([])
        except OSError:
            msg = 'Failed to remove supplemental groups'
            LOG.critical(msg)
            raise
        setgid(group)

    if user is not None:
        setuid(user)

    LOG.info("Process runs with uid/gid: %(uid)s/%(gid)s",
             {'uid': os.getuid(), 'gid': os.getgid()})


def unwatch_log():
    """Replace WatchedFileHandler handlers by FileHandler ones.

    Neutron logging uses WatchedFileHandler handlers but they do not
    support privileges drop, this method replaces them by FileHandler
    handlers supporting privileges drop.
    """
    log_root = logging.getLogger(None).logger
    to_replace = [h for h in log_root.handlers
                  if isinstance(h, handlers.WatchedFileHandler)]
    for handler in to_replace:
        # NOTE(cbrandily): we use default delay(=False) to ensure the log file
        # is opened before privileges drop.
        new_handler = std_logging.FileHandler(handler.baseFilename,
                                              mode=handler.mode,
                                              encoding=handler.encoding)
        log_root.removeHandler(handler)
        log_root.addHandler(new_handler)


class Pidfile(object):
    def __init__(self, pidfile, procname, uuid=None):
        self.pidfile = pidfile
        self.procname = procname
        self.uuid = uuid
        try:
            self.fd = os.open(pidfile, os.O_CREAT | os.O_RDWR)
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            LOG.exception("Error while handling pidfile: %s", pidfile)
            sys.exit(1)

    def __str__(self):
        return self.pidfile

    def unlock(self):
        fcntl.flock(self.fd, fcntl.LOCK_UN)

    def write(self, pid):
        os.ftruncate(self.fd, 0)
        os.write(self.fd, "%d" % pid)
        os.fsync(self.fd)

    def read(self):
        try:
            pid = int(os.read(self.fd, 128))
            os.lseek(self.fd, 0, os.SEEK_SET)
            return pid
        except ValueError:
            return

    def is_running(self):
        pid = self.read()
        if not pid:
            return False

        cmdline = '/proc/%s/cmdline' % pid
        try:
            with open(cmdline, "r") as f:
                exec_out = f.readline()
            return self.procname in exec_out and (not self.uuid or
                                                  self.uuid in exec_out)
        except IOError:
            return False


class Daemon(object):
    """A generic daemon class.

    Usage: subclass the Daemon class and override the run() method
    """
    def __init__(self, pidfile, stdin=DEVNULL, stdout=DEVNULL,
                 stderr=DEVNULL, procname='python', uuid=None,
                 user=None, group=None, watch_log=True):
        """Note: pidfile may be None."""
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.procname = procname
        self.pidfile = Pidfile(pidfile if pidfile is not None else os.path.join(CONF.state_path, 'lock'),
                               procname, uuid)
        self.user = user
        self.group = group
        self.watch_log = watch_log

    def _fork(self):
        try:
            pid = os.fork()
            if pid > 0:
                os._exit(0)
        except OSError:
            LOG.exception('Fork failed')
            sys.exit(1)

    def daemonize(self):
        """Daemonize process by doing Stevens double fork."""

        # flush any buffered data before fork/dup2.
        if self.stdout is not DEVNULL:
            self.stdout.flush()
        if self.stderr is not DEVNULL:
            self.stderr.flush()
        # sys.std* may not match STD{OUT,ERR}_FILENO.  Tough.
        for f in (sys.stdout, sys.stderr):
            f.flush()

        # fork first time
        self._fork()

        # decouple from parent environment
        os.chdir("/")
        os.setsid()
        os.umask(0)

        # fork second time
        self._fork()

        # redirect standard file descriptors
        with open(os.devnull, 'w+') as devnull:
            stdin = devnull if self.stdin is DEVNULL else self.stdin
            stdout = devnull if self.stdout is DEVNULL else self.stdout
            stderr = devnull if self.stderr is DEVNULL else self.stderr
            os.dup2(stdin.fileno(), STDIN_FILENO)
            os.dup2(stdout.fileno(), STDOUT_FILENO)
            os.dup2(stderr.fileno(), STDERR_FILENO)

        if self.pidfile is not None:
            # write pidfile
            atexit.register(self.delete_pid)
            self.pidfile.write(os.getpid())

    def delete_pid(self):
        if self.pidfile is not None:
            os.remove(str(self.pidfile))

    def start(self):
        """Start the daemon."""

        if self.pidfile is not None and self.pidfile.is_running():
            self.pidfile.unlock()
            LOG.error('Pidfile %s already exist. Daemon already running?',
                      self.pidfile)
            sys.exit(1)

        # Start the daemon
        self.daemonize()
        self.run()

    def run(self):
        """Override this method and call super().run when subclassing Daemon.

        start() will call this method after the process has daemonized.
        """
        if not self.watch_log:
            unwatch_log()
        drop_privileges(self.user, self.group)


def daemon(pidfile, user=None, group=None):
    daemon_intance = Daemon(pidfile=pidfile, user=user, group=group)
    daemon_intance.start()


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
                LOG.debug("Systemd notification failed", exc_info=True)


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
