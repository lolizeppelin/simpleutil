# -*- coding: UTF-8 -*-
#  为了方便在windows调试
#  linux相关代码移到linux.py中
"""
Helper module for systemd service readiness notification.
"""
import sys
import platform

def empty(*args, **kwargs):
    """do nothing"""

daemon = empty
notify_once = empty
notify = empty
onready = empty


if (sys.platform != "win32"):
    from simpleutil.posix import linux
    sysname, verison, mark = platform.dist()
    if sysname.lower() in ('redhat', 'centos') and float(verison) >= 7.0:
        notify_once = linux.notify_once
        notify = linux.notify
        onready = linux.onready
    else:
        daemon = linux.daemon
