# -*- coding: UTF-8 -*-
import six
import contextlib
from simpleutil.utils import lockutils


@contextlib.contextmanager
def slock(name, semaphores):
    with semaphores.get(name) as int_lock:
        yield int_lock


class Singleton(type):
    """Metaclass for build Singleton Class
    """
    _instances = {}
    _semaphores = lockutils.Semaphores()

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with slock('singleton_lock', semaphores=cls._semaphores):
                if cls not in cls._instances:
                    cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


# 单例专用装饰器
singleton = six.add_metaclass(Singleton)
