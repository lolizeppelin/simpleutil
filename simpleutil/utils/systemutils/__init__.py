# -*- coding: UTF-8 -*-
import ctypes
import subprocess
from simpleutil.utils import strutils
from simpleutil.utils.systemutils.public import *

PID = 0

TIMEOUT = object()
# system encode
SYSENCODE = sys.getfilesystemencoding()


if POSIX:
    from simpleutil.utils.systemutils.posix import set_cloexec_flag

    if LINUX:
        from simpleutil.utils.systemutils.posix.linux import umask
        from simpleutil.utils.systemutils.posix.linux import chmod
        from simpleutil.utils.systemutils.posix.linux import chown
        from simpleutil.utils.systemutils.posix.linux import prepare_user
    else:
        umask = empty_context
        chmod = empty
        chown = empty
        prepare_user = empty_context

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

    umask = empty_context
    chmod = empty
    chown = empty
    prepare_user = empty_context

    def get_partion_free_bytes(folder):
        """ Return folder/drive free space (in bytes)
        """
        free_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(folder), None, None,
                                                   ctypes.pointer(free_bytes))
        return free_bytes.value

    def directory_size(path, excludes=None, timeout=None):
        fso = win32com.client.Dispatch("Scripting.FileSystemObject")
        folder = fso.GetFolder(path)
        rootsize = folder.Size
        if excludes:
            if isinstance(excludes, basestring):
                excludes = [excludes, ]
            for exclude in excludes:
                exclude = os.path.join(path, exclude)
                if not os.path.exists(exclude):
                    continue
                if os.path.isfile(exclude):
                    rootsize -= os.path.getsize(exclude)
                else:
                    folder = fso.GetFolder(exclude)
                    rootsize -= folder.Size
        return rootsize

else:
    raise RuntimeError('System type unkonwn')
