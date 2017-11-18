import sys
from simpleutil.utils import systemutils

if not systemutils.LINUX or not systemutils.BSD:
    raise RuntimeError('system type error')

if sys.version_info < (2, 4):
    raise RuntimeError('python version error')

if sys.version_info >= (3, 0):
    raise RuntimeError('python version error')