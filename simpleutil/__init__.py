__version__ = '1.0.0'
VERSION = tuple(map(int, __version__.split('.')))

import logging
import functools
import eventlet
import sys
reload(sys)
from simpleutil.utils import systemutils


if systemutils.WINDOWS:
    # eventlet monkey patching the os and thread modules causes
    # subprocess.Popen to fail on Windows when using pipes due
    # to missing non-blocking IO support.
    #
    # bug report on eventlet:
    # https://bitbucket.org/eventlet/eventlet/issue/132/
    #       eventletmonkey_patch-breaks
    sys.setdefaultencoding('gb2312')
    eventlet.monkey_patch(os=False, thread=False)
    import amqp.transport
    import socket
    # Remove TCP_MAXSEG, Avoid koumbu raise socket error on windows
    opt_name = 'TCP_MAXSEG'
    opt_id = getattr(socket, 'TCP_MAXSEG')
    if opt_id and opt_id in amqp.transport.TCP_OPTS:
        amqp.transport.TCP_OPTS.remove(opt_id)
    if opt_name in amqp.transport.KNOWN_TCP_OPTS:
        amqp.transport.KNOWN_TCP_OPTS = list(amqp.transport.KNOWN_TCP_OPTS)
        amqp.transport.KNOWN_TCP_OPTS.remove(opt_name)
        amqp.transport.KNOWN_TCP_OPTS = tuple(amqp.transport.KNOWN_TCP_OPTS)
    # import eventlet.debug
    # eventlet.debug.hub_prevent_multiple_readers(False)
else:
    eventlet.monkey_patch()
    sys.setdefaultencoding('utf-8')



if not hasattr(logging, '_checkLevel'):
    # Patch for python 2.6 logging
    def _checkLevel(level):
        if isinstance(level, (int, long)):
            rv = level
        elif str(level) == level:
            if level not in logging._levelNames:
                raise ValueError("Unknown level: %r" % level)
            rv = logging._levelNames[level]
        else:
            raise TypeError("Level not an integer or a valid string: %r" % level)
        return rv
    # setattr(logging, '_checkLevel', _checkLevel)
    def setLevel(self, level):
        self.level = _checkLevel(level)
    logging.Logger.setLevel = setLevel
    logging.Handler.setLevel = setLevel

if not hasattr(functools, 'total_ordering'):

    def total_ordering(cls):
        """Class decorator that fills in missing ordering methods"""
        convert = {
            '__lt__': [('__gt__', lambda self, other: not (self < other or self == other)),
                       ('__le__', lambda self, other: self < other or self == other),
                       ('__ge__', lambda self, other: not self < other)],
            '__le__': [('__ge__', lambda self, other: not self <= other or self == other),
                       ('__lt__', lambda self, other: self <= other and not self == other),
                       ('__gt__', lambda self, other: not self <= other)],
            '__gt__': [('__lt__', lambda self, other: not (self > other or self == other)),
                       ('__ge__', lambda self, other: self > other or self == other),
                       ('__le__', lambda self, other: not self > other)],
            '__ge__': [('__le__', lambda self, other: (not self >= other) or self == other),
                       ('__gt__', lambda self, other: self >= other and not self == other),
                       ('__lt__', lambda self, other: not self >= other)]
        }
        roots = set(dir(cls)) & set(convert)
        if not roots:
            raise ValueError('must define at least one ordering operation: < > <= >=')
        root = max(roots)       # prefer __lt__ to __le__ to __gt__ to __ge__
        for opname, opfunc in convert[root]:
            if opname not in roots:
                opfunc.__name__ = opname
                opfunc.__doc__ = getattr(int, opname).__doc__
                setattr(cls, opname, opfunc)
        return cls

    setattr(functools, 'total_ordering', total_ordering)
