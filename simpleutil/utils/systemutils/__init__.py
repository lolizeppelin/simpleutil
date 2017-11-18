# -*- coding: UTF-8 -*-
import os
import sys
import platform
import ctypes


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


def get_partion_free_bytes(folder):
    """ Return folder/drive free space (in bytes)
    """
    if WINDOWS:
        free_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(folder), None, None,
                                                   ctypes.pointer(free_bytes))
        return free_bytes.value
    else:
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

