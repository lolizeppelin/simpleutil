# -*- coding: UTF-8 -*-
from simpleutil.common.exceptions import InvalidArgument


class IdformaterBase(object):

    def _all_id(self):
        raise NotImplemented

    @property
    def all_id(self):
        return self._all_id()


class Idformater(object):
    """This Descriptor code copy from Wsgify
    This class will format server_id on kwargs
    Instance must has attr all_id
    这里的描述器实现参考来源是webob.dec.wsgify
    作用在于格式化传入的id转为校验后的list
    使用这个描述其的类必须有一个all_id属性返回为set
    all_key不为None的时候,当id值为all_key的时候表示所有id
    formatfunc每个id都被formatfunc格式化处理
    """
    def __init__(self, func=None, key='id', all_key=None, formatfunc=None):
        self.func = func
        self.key = key
        self.all_key = all_key
        self.formatfunc = formatfunc
        self.all_id = None

    def __get__(self, instance, owner):
        if not isinstance(instance, IdformaterBase):
            raise TypeError('Instance not IdformaterBase')
        if hasattr(self.func, '__get__'):
            formater = self.__class__(func=self.func.__get__(instance, owner),
                                      key=self.key,
                                      all_key=self.all_key,
                                      formatfunc=self.formatfunc)
            formater.all_id = instance.all_id
            return formater
        else:
            return self

    def __call__(self, *args, **kwargs):
        if self.func is None:
            return self.__class__(func=args[0],
                                  key=self.key,
                                  all_key=self.all_key,
                                  formatfunc=self.formatfunc)
        else:
            id_string = kwargs.pop(self.key, None)
            if not isinstance(id_string, basestring):
                raise InvalidArgument('%s not basestring' % self.key)
            id_set = set(id_string.split(','))
            if self.all_key is not None:
                if self.all_key in id_set and len(id_set) == 1:
                    id_set = self.all_id
                elif self.all_key in id_set and len(id_set) > 1:
                    raise InvalidArgument('%s:0 with other id in same list' % self.key)
            elif self.formatfunc:
                try:
                    id_set = set(map(self.formatfunc, id_set))
                except (TypeError, ValueError) as e:
                    raise InvalidArgument('%(key)s can not be formated: %(class)s' %
                                          {'key': self.key,
                                           'class': e.__class__.__name__
                                           })
            if len(id_set) < 1:
                raise InvalidArgument('%s is empty or no entity found' % self.key)
            kwargs[self.key] = id_set
        return self.func(*args, **kwargs)
