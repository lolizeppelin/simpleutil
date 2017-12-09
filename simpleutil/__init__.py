__version__ = '1.0.0'
VERSION = tuple(map(int, __version__.split('.')))

import logging
import logging
import warnings
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
    setattr(logging, '_checkLevel', _checkLevel)
    def setLevel(self, level):
        self.level = _checkLevel(level)

    logging.Logger.setLevel = setLevel
    logging.Handler.setLevel = setLevel


if not hasattr(logging, '_warnings_showwarning'):
    setattr(logging, '_warnings_showwarning', None)


if not hasattr(logging, 'NullHandler'):
    class NullHandler(logging.Handler):
        """
        This handler does nothing. It's intended to be used to avoid the
        "No handlers could be found for logger XXX" one-off warning. This is
        important for library code, which may contain code to log events. If a user
        of the library does not configure logging, the one-off warning might be
        produced; to avoid this, the library developer simply needs to instantiate
        a NullHandler and add it to the top-level logger of the library module or
        package.
        """
        def handle(self, record):
            pass

        def emit(self, record):
            pass

        def createLock(self):
            self.lock = None

    setattr(logging, 'NullHandler', NullHandler)


if not hasattr(logging, '_showwarning'):
    def _showwarning(message, category, filename, lineno, file=None, line=None):
        if file is not None:
            if logging._warnings_showwarning is not None:
                logging._warnings_showwarning(message, category, filename, lineno, file, line)
        else:
            s = warnings.formatwarning(message, category, filename, lineno, line)
            logger = logging.getLogger("py.warnings")
            if not logger.handlers:
                logger.addHandler(logging.NullHandler())
            logger.warning("%s", s)

    setattr(logging, '_showwarning', _showwarning)


if not hasattr(logging, 'captureWarnings'):
    def captureWarnings(capture):
        """
        If capture is true, redirect all warnings to the logging package.
        If capture is False, ensure that warnings are not redirected to logging
        but to their original destinations.
        """
        if capture:
            if logging._warnings_showwarning is None:
                logging._warnings_showwarning = warnings.showwarning
                warnings.showwarning = _showwarning
        else:
            if logging._warnings_showwarning is not None:
                warnings.showwarning = logging._warnings_showwarning
                logging._warnings_showwarning = None

    setattr(logging, 'captureWarnings', captureWarnings)


if not hasattr(logging.Logger, 'isEnabledFor'):

    def isEnabledFor(self, level):
        """
        Is this logger enabled for level 'level'?
        """
        if self.manager.disable >= level:
            return 0
        return level >= self.getEffectiveLevel()

    setattr(logging.Logger, 'isEnabledFor', isEnabledFor)

if not hasattr(logging.LoggerAdapter, 'isEnabledFor'):

    def isEnabledFor(self, level):
        """
        See if the underlying logger is enabled for the specified level.
        """
        return self.logger.isEnabledFor(level)

    setattr(logging.LoggerAdapter, 'isEnabledFor', isEnabledFor)


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


warnings.filterwarnings("ignore", category=DeprecationWarning)
