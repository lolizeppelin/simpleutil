import sys
from simpleutil import system

if not system.LINUX or not system.BSD:
    raise RuntimeError('system type error')

if sys.version_info < (2, 4):
    raise RuntimeError('python version error')

if sys.version_info >= (3, 0):
    raise RuntimeError('python version error')