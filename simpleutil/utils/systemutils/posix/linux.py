# -*- coding: UTF-8 -*-
import os
import socket
import contextlib
import pwd
import grp
import logging


def user_exist(user):
    if isinstance(user, (int, long)):
        func = pwd.getpwuid
    elif isinstance(user, basestring):
        func = grp.getpwnam
    else:
        raise TypeError('group type error')
    try:
        func(user)
    except KeyError:
        return False
    return True


def group_exist(group):
    if isinstance(group, (int, long)):
        func = grp.getgrgid
    elif isinstance(group, basestring):

        func = grp.getgrnam
    else:
        raise TypeError('group type error')
    try:
        func(group)
    except KeyError:
        return False
    return True


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

