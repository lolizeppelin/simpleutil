# -*- coding: UTF-8 -*-
from simpleutil.common.exceptions import InvalidArgument


class IdformaterBase(object):
    """使用下面Idformater描述器的类需要继承这个类"""

    def _all_id(self):
        """返回具体的所有id"""
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
    使用这个描述其的类必须继承自IdformaterBase
    magic == 'all' 意味着all能表示所有key
    magic == 'onlyone' 标志只允许一个key
    formatfunc每个id都被formatfunc格式化处理
    """
    def __init__(self, func=None, key='id', magic="onlyone", formatfunc=None):
        self.func = func
        self.key = key
        if magic not in ('all', 'onlyone'):
            raise ValueError("Magic not 'onlyone' or 'all'")
        self.magic = magic
        self.formatfunc = formatfunc
        self.all_id = None

    def __get__(self, instance, owner):
        if not isinstance(instance, IdformaterBase):
            raise TypeError('Instance not IdformaterBase')
        if hasattr(self.func, '__get__'):
            formater = self.__class__(func=self.func.__get__(instance, owner),
                                      key=self.key,
                                      magic=self.magic,
                                      formatfunc=self.formatfunc)
            if self.magic == 'all':
                formater.all_id = instance.all_id
            return formater
        else:
            return self

    def __call__(self, *args, **kwargs):
        if self.func is None:
            return self.__class__(func=args[0],
                                  key=self.key,
                                  magic=self.magic,
                                  formatfunc=self.formatfunc)
        else:
            id_string = kwargs.pop(self.key, None)
            if not isinstance(id_string, basestring):
                raise InvalidArgument('%s is None or not basestring' % self.key)
            id_set = set(id_string.split(','))
            if self.magic == "all":
                if self.magic in id_set and len(id_set) == 1:
                    id_set = self.all_id
                    if len(id_set) > 0:
                        kwargs[self.key] = id_set
                        return self.func(*args, **kwargs)
                raise InvalidArgument('%s:0 with other id in same list' % self.key)
            if self.formatfunc:
                try:
                    id_set = set(map(self.formatfunc, id_set))
                except (TypeError, ValueError) as e:
                    raise InvalidArgument('%(key)s can not be formated: %(class)s' %
                                          {'key': self.key,
                                           'class': e.__class__.__name__
                                           })
            if len(id_set) < 1:
                raise InvalidArgument('No entity found for %s' % self.key)
            if self.magic == 'onlyone' and len(id_set) > 1:
                raise InvalidArgument('More then one entity found')
            kwargs[self.key] = id_set.pop() if self.magic == 'onlyone' else id_set
        return self.func(*args, **kwargs)
