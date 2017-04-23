# -*- coding: UTF-8 -*-
from eventlet import patcher
# 防止调用被eventlet patch过threading
orig_threading = patcher.original('threading')
Lock = orig_threading.Lock()


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            try:
                # 通过线程锁做双重检查
                # thread Lock必须在最初就生成实例
                # 否则会被eventlet的monkey path覆盖
                # openstack里为了避免这个问题用自己的lock函数
                Lock.acquire()
                if cls not in cls._instances:
                    cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
            finally:
                Lock.release()
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
