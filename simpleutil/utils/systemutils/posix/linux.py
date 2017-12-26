# -*- coding: UTF-8 -*-
import os
import socket
import contextlib
import pwd
import grp
import logging
import subprocess

from simpleutil.utils.systemutils import public

USERADD = public.find_executable('useradd')
USERDEL = public.find_executable('userdel')
GROUPADD = public.find_executable('groupadd')
GROUPDEL = public.find_executable('groupdel')


def user_exist(user):
    if isinstance(user, (int, long)):
        func = pwd.getpwuid
    elif isinstance(user, basestring):
        func = pwd.getpwnam
    else:
        raise TypeError('user type error, not int or basestring')
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
        raise TypeError('group type error, not int or basestring')
    try:
        func(group)
    except KeyError:
        return False
    return True


@contextlib.contextmanager
def prepare_group(group):
    if not isinstance(group, basestring):
        raise TypeError('group must be basestring')
    try:
        _group = grp.getgrnam(group)
    except KeyError:
        _group = None

    if not _group:
        with open(os.devnull, 'wb') as f:
            args = [GROUPADD, group]
            sub = subprocess.Popen(executable=GROUPADD, args=args, stderr=f.fileno(), stdout=f.fileno())
            public.subwait(sub)
            _group = grp.getgrnam(group)
    else:
        _group = None

    try:
        yield
    except:
        if _group and _group.gr_gid > 0:
            args = [GROUPDEL, _group.gr_name]
            try:
                with open(os.devnull, 'wb') as f:
                    sub = subprocess.Popen(executable=GROUPDEL, args=args, stderr=f.fileno(), stdout=f.fileno())
                    public.subwait(sub)
            except:
                logging.critical('Remove group %s fail' % _group.gr_name)
        raise


@contextlib.contextmanager
def prepare_user(user, group, home=None):
    if not isinstance(user, basestring):
        raise TypeError('user or group must be basestring')
    if home:
        if not isinstance(home, basestring):
            raise TypeError('home must be basesting')
        if home == '/':
            raise TypeError('home is root path')
    try:
        _user = pwd.getpwnam(user)
    except KeyError:
        _user = None

    if _user and _user.pw_uid > 0:
        raise ValueError('User exist, not root')

    with prepare_group(group):
        if not _user:
            with open(os.devnull, 'wb') as f:
                args = [USERADD, '-M', '-N', '-s', '/sbin/nologin',
                        '-g', group, '-d', home, user]
                sub = subprocess.Popen(executable=USERADD, args=args, stderr=f.fileno(), stdout=f.fileno())
                public.subwait(sub)
                _user = pwd.getpwnam(user)
        else:
            _user = None
        try:
            yield
        except:
            if _user and _user.pw_uid > 0:
                args = [USERDEL, _user.pw_name]
                try:
                    with open(os.devnull, 'wb') as f:
                        sub = subprocess.Popen(executable=USERDEL, args=args, stderr=f.fileno(), stdout=f.fileno())
                        public.subwait(sub)
                except:
                    logging.critical('Remove user %s fail' % _user.pw_name)
            raise


def drop_user(user):
    if not isinstance(user, basestring):
        raise TypeError('user or group must be basestring')
    try:
        _user = pwd.getpwnam(user)
    except KeyError:
        return
    if _user.pw_uid > 0:
        args = [USERDEL, _user.pw_name]
        try:
            with open(os.devnull, 'wb') as f:
                sub = subprocess.Popen(executable=USERDEL, args=args, stderr=f.fileno(), stdout=f.fileno())
                public.subwait(sub)
        except:
            logging.critical('Remove user %s fail' % _user.pw_name)


def drop_group(group):
    if not isinstance(group, basestring):
        raise TypeError('group must be basestring')
    try:
        _group = grp.getgrnam(group)
    except KeyError:
        return
    if _group.gr_gid > 0:
        args = [GROUPDEL, _group.gr_name]
        try:
            with open(os.devnull, 'wb') as f:
                sub = subprocess.Popen(executable=GROUPDEL, args=args, stderr=f.fileno(), stdout=f.fileno())
                public.subwait(sub)
        except:
            logging.critical('Remove group %s fail' % _group.gr_name)


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


@contextlib.contextmanager
def umask(umask=022):
    default = os.umask(umask)
    try:
        yield umask
    finally:
        os.umask(default)


def chmod(path, mask):
    if os.path.isdir(path):
        os.chmod(path, 0777-mask)
    else:
        os.chmod(path, 0666-mask)


def chown(path, user, group):
    try:
        uid = int(user)
    except (TypeError, ValueError):
        uid = pwd.getpwnam(user).pw_uid
    try:
        gid = int(group)
    except (TypeError, ValueError):
        gid = grp.getgrnam(group).gr_gid
    os.chown(path, uid, gid)


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

    # logging.info("Process runs with uid/gid: %(uid)s/%(gid)s" % {'uid': os.getuid(), 'gid': os.getgid()})


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

