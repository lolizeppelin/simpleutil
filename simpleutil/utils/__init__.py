# -*- coding: UTF-8 -*-
import six
from eventlet import patcher
# 防止调用被eventlet patch过threading
# openstack里为了避免threading被eventlet覆盖用了自写的Lock函数
# 这里通过patcher或取原生的threading.Lock
SingletonLock = patcher.original('threading').Lock()

_threadlocal = patcher.original('threading').local()


class Singleton(type):
    """Metaclass for build Singleton Class
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with SingletonLock:
                # 单例生成时间过长会长时间占用SingletonLock
                # 影响到其他单例生成
                # 单利初始化的时候,内部不能再有单例在初始化
                # 否则会死锁,请避免单例嵌套
                if cls not in cls._instances:
                    cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


def get_current():
    """Return this thread's current context

    If no context is set, returns None
    """
    return getattr(_threadlocal, 'context', None)


# 单例专用装饰器
singleton = six.add_metaclass(Singleton)
