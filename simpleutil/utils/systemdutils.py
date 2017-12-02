import platform
from simpleutil.utils import systemutils

notify_once = systemutils.empty
notify = systemutils.empty
onready = systemutils.empty
daemon = systemutils.empty

# systemd function
if systemutils.LINUX:
    from simpleutil.utils.systemutils.posix import linux
    sysname, verison, mark = platform.dist()
    if sysname.lower() in ('redhat', 'centos') and float(verison) >= 7.0:
        notify_once = linux.notify_once
        notify = linux.notify
        onready = linux.onready
    if sysname.lower() in ('redhat', 'centos') and float(verison) < 7.0:
        from simpleutil.utils import daemonutils
        daemon = daemonutils.daemon

