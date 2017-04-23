# -*- coding: UTF-8 -*-
from eventlet import patcher
# 防止调用被eventlet patch过threading
# openstack里为了避免threading被eventlet覆盖用了自写的Lock函数
SingletonLock = patcher.original('threading').Lock()


class Singleton(type):
    """Metaclass for build Singleton Class
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            try:
                # 单例生成时间过长会长时间占用SingletonLock
                # 影响到其他单例生成
                SingletonLock.acquire()
                if cls not in cls._instances:
                    cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
            finally:
                SingletonLock.release()
        return cls._instances[cls]


# 插入元类的装饰器
def add_metaclass(metaclass):
    """Class decorator for creating a class with a metaclass."""
    def wrapper(cls):
        orig_vars = cls.__dict__.copy()
        orig_vars.pop('__dict__', None)
        orig_vars.pop('__weakref__', None)
        for slots_var in orig_vars.get('__slots__', ()):
            orig_vars.pop(slots_var)
        return metaclass(cls.__name__, cls.__bases__, orig_vars)
    return wrapper

# 单例专用装饰器
singleton = add_metaclass(Singleton)
