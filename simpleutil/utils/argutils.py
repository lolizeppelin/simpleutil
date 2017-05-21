# -*- coding: UTF-8 -*-
from simpleutil.common.exceptions import InvalidArgument


class IdformaterBase(object):
    def __init__(self):
        self._all_id = set()

    @property
    def all_id(self):
        return self._all_id


class Idformater(object):
    """This Descriptor code copy from Wsgify
    This class will format server_id on kwargs
    Instance must has attr all_id
    这里的描述器实现参考来源是webob.dec.wsgify
    作用在于格式化传入的id转为int组成的list
    使用这个描述其的类必须有一个all_id属性返回为set
    """
    def __init__(self, func=None, key='id', all_key="all"):
        self.func = func
        self.key = key
        self.all_key = all_key
        self.all_id = None

    def __get__(self, instance, owner):
        if not isinstance(instance, IdformaterBase):
            raise TypeError('Instance not IdformaterBase')
        if hasattr(self.func, '__get__'):
            formater = self.__class__(func=self.func.__get__(instance, owner),
                                      key=self.key,
                                      zero_as_all=self.all_key)
            formater.all_id = instance.all_id
            return formater
        else:
            return self

    def __call__(self, *args, **kwargs):
        if self.func is None:
            return self.__class__(func=args[0],
                                  key=self.key,
                                  all_key=self.all_key)
        else:
            id_string = kwargs.pop(self.key, None)
            if not isinstance(id_string, basestring):
                raise InvalidArgument('%s not basestring' % self.key)
            if id_string.isdigit():
                id_set = set()
                id_set.add(int(id_string))
            else:
                id_set = set(id_string.split(','))
                try:
                    id_set = set(map(int, id_set))
                except TypeError:
                    pass
            if self.all_key is not None:
                if self.all_key in id_set and len(id_set) == 1:
                    id_set = self.all_id
                elif self.all_key in id_set and len(id_set) > 1:
                    raise InvalidArgument('%s:0 with other id in same list' % self.key)
            if len(id_set) < 1:
                InvalidArgument('%s is empty' % self.key)
            kwargs[self.key] = id_set
        return self.func(*args, **kwargs)
