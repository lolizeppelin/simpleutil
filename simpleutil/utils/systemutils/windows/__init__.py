import os
import sys
import ctypes
import six
import win32com.client


def is_admin():
    return ctypes.windll.shell32.IsUserAnAdmin()


def run_as_admin():
    if not is_admin():
        if six.PY3:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)
        else:
            ctypes.windll.shell32.ShellExecuteW(None, u"runas", unicode(sys.executable), unicode(__file__), None, 1)
    sys.stderr.flush()
    sys.stdout.flush()
    sys.exit(0)


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
