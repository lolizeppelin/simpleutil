# -*- coding: UTF-8 -*-
import os
import sys
import errno
import ctypes
import subprocess
import eventlet
import contextlib

from eventlet import hubs

from simpleutil.utils import strutils

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

# system encode
SYSENCODE = sys.getfilesystemencoding()
INTERVAL = 0.01

TIMEOUT = object()

hub = eventlet.hubs.get_hub()

class ExitBySIG(Exception):
    """"""


class UnExceptExit(Exception):
    """"""


def empty(*args, **kwargs):
    """do nothing"""


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


if POSIX:
    import pwd
    import grp
    from .posix import set_cloexec_flag

    @contextlib.contextmanager
    def umask(umask=022):
        default = os.umask(umask)
        try:
            yield umask
        finally:
            os.umask(default)

    def chmod(path, mask):
        if os.path.isdir(path):
            os.chmod(path, 777-mask)
        else:
            os.chmod(path, 666-mask)

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

    def get_partion_free_bytes(folder):
        # f_bsize: 文件系统块大小
        # f_frsize: 分栈大小
        # f_blocks: 文件系统数据块总数
        # f_bfree: 可用块数
        # f_bavail:非超级用户可获取的块数
        # f_files: 文件结点总数
        # f_ffree: 可用文件结点数
        # f_favail: 非超级用户的可用文件结点数
        # f_fsid: 文件系统标识 ID
        # f_flag: 挂载标记
        # f_namemax: 最大文件名长度
        st = os.statvfs(folder)
        return st.f_frsize * st.f_bavail

    DU = find_executable('du')

    def directory_size(path, excludes=None, timeout=None):
        args = [DU, '-sk']
        if excludes:
            if isinstance(excludes, basestring):
                excludes = [excludes, ]
            for exclude in excludes:
                args.append('--exclude=%s' % exclude)
        args.append(path)
        r, w = os.pipe()
        set_cloexec_flag(r)
        set_cloexec_flag(w)
        with open(os.devnull, 'wb') as null:
            sub = subprocess.Popen(executable=DU, args=args, stdout=w, stderr=null.fileno(),
                                   close_fds=False)
        os.close(w)
        try:
            subwait(sub, timeout)
        except (OSError, ExitBySIG, UnExceptExit):
            os.close(r)
            return 0
        except Exception:
            os.close(r)
            raise
        with os.fdopen(r, 'rb') as f:
            buffer = f.read(512)
        return int(strutils.Split(buffer)[0])*1024

elif WINDOWS:
    import win32com.client

    @contextlib.contextmanager
    def umask(*args):
        yield None

    chmod = empty

    chown = empty

    def get_partion_free_bytes(folder):
        """ Return folder/drive free space (in bytes)
        """
        free_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(folder), None, None,
                                                   ctypes.pointer(free_bytes))
        return free_bytes.value

    def directory_size(path, excludes=None, **kwargs):
        fso = win32com.client.Dispatch("Scripting.FileSystemObject")
        folder = fso.GetFolder(path)
        rootsize = folder.Size
        if excludes:
            if isinstance(excludes, basestring):
                excludes = [excludes, ]
            for exclude in excludes:
                folder = fso.GetFolder(os.path.join(path, exclude))
                rootsize -= folder.Size
        return rootsize

else:
    raise RuntimeError
