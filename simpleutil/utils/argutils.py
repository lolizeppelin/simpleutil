# -*- coding: UTF-8 -*-
from simpleutil.common.exceptions import InvalidArgument

class Idformater(object):
    """This Descriptor code copy from Wsgify
    This class will format server_id on kwargs
    Instance must has attr all_id
    这里的描述器实现参考来源是webob.dec.wsgify
    作用在于格式化传入的id转为int组成的list
    使用这个描述其的类必须有一个all_id属性返回为set
    """
    def __init__(self, func=None, key='id', zero_as_all=True):
        self.func = func
        self.key = key
        self.zero_as_all = zero_as_all
        self.all_id = None

    def __get__(self, instance, owner):
        if hasattr(self.func, '__get__'):
            formater = self.__class__(func = self.func.__get__(instance, owner),
                                      key=self.key,
                                      zero_as_all = self.zero_as_all)
            formater.all_id = instance.all_id
            return formater
        else:
            return self

    def __call__(self, *args, **kwargs):
        if self.func is None:
            return self.__class__(func=args[0],
                                  key=self.key,
                                  zero_as_all=self.zero_as_all)
        else:
            id_string = kwargs.pop(self.key, None)
            if not isinstance(id_string, basestring):
                raise InvalidArgument('%s not basestring' % self.key)
            id_list = set()
            if id_string.isdigit():
                id_list.add(int(id_string))
            else:
                try:
                    id_list = set(map(int, id_string.split(',')))
                except TypeError:
                    InvalidArgument('member in %s not int' % self.key)
            if 0 in id_list and len(id_list) == 1:
                if self.zero_as_all:
                    id_list = self.all_id
            elif 0 in id_list and len(id_list) > 1:
                raise InvalidArgument('%s:0 with other id in same list' % self.key)
            if len(id_list) < 1:
                InvalidArgument('%s is empty' % self.key)
            kwargs[self.key] = id_list
        return self.func(*args, **kwargs)