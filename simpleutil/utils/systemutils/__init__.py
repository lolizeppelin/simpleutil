# -*- coding: UTF-8 -*-
import time
from simpleutil.utils import strutils
from simpleutil.utils.systemutils.public import *

PY27 = True if sys.version_info[0:2] >= (2, 7) else False
TIMEOUT = object()
# system encode
SYSENCODE = sys.getfilesystemencoding()

PID = 0


def touch(path):
    mtime = os.stat(path).st_mtime
    os.utime(path, (int(time.time()), int(mtime)))


def acctime(path):
    return int(os.stat(path).st_atime)


if POSIX:
    import subprocess
    from simpleutil.utils.systemutils import posix

    is_admin = posix.is_admin
    run_as_admin = posix.run_as_admin
    set_cloexec_flag = posix.set_cloexec_flag

    if LINUX:
        from simpleutil.utils.systemutils.posix import linux

        umask = linux.umask
        chmod = linux.chmod
        chown = linux.chown
        drop_user = linux.drop_user
        drop_group = linux.drop_group
        prepare_user = linux.prepare_user
        drop_privileges = linux.drop_privileges
        unlimit_core = linux.unlimit_core
        open_file_limit = linux.open_file_limit
    else:
        umask = empty_context
        chmod = empty
        chown = empty
        drop_user = empty
        drop_group = empty
        prepare_user = empty_context
        drop_privileges = empty
        unlimit_core = empty
        open_file_limit = empty

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
        # TODO rewrite with C
        args = [DU, '-sk']
        if excludes:
            if isinstance(excludes, basestring):
                excludes = [excludes, ]
            for exclude in excludes:
                args.append('--exclude=%s' % exclude)
        args.append(path)
        r, w = os.pipe()
        posix.set_cloexec_flag(r)
        posix.set_cloexec_flag(w)
        with open(os.devnull, 'wb') as null:
            sub = subprocess.Popen(executable=DU, args=args, stdout=w,
                                   stderr=null.fileno(), close_fds=True)
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
            return int(strutils.Split(f.read(512))[0]) * 1024

elif WINDOWS:
    from simpleutil.utils.systemutils import windows

    umask = empty_context
    chmod = empty
    chown = empty
    drop_user = empty
    drop_group = empty
    prepare_user = empty_context
    drop_privileges = empty
    unlimit_core = empty
    open_file_limit = empty
    set_cloexec_flag = empty

    get_partion_free_bytes = windows.get_partion_free_bytes
    directory_size = windows.directory_size

    is_admin = windows.is_admin
    run_as_admin = windows.run_as_admin


else:
    raise RuntimeError('System type unkonwn')
