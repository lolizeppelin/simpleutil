import platform
from simpleutil.utils import systemutils

def empty(*args, **kwargs):
    """do nothing"""


daemon = empty
notify_once = empty
notify = empty
onready = empty

# systemd function
if systemutils.LINUX:
    from simpleutil.utils.systemutils.posix import linux
    sysname, verison, mark = platform.dist()
    if sysname.lower() in ('redhat', 'centos') and float(verison) >= 7.0:
        notify_once = linux.notify_once
        notify = linux.notify
        onready = linux.onready
    else:
        daemon = linux.daemon
