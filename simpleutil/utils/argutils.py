# -*- coding: UTF-8 -*-
from simpleutil.common.exceptions import InvalidArgument


def map_to_int(ids):
        if isinstance(ids, basestring):
            ids_list = set(ids.split(','))
        elif isinstance(ids, (list, tuple, set)):
            ids_list = ids
        elif isinstance(ids, (int, long)):
            ids_list = [int(ids), ]
        else:
            raise InvalidArgument('id can not be formated from %s' % ids.__class__.__name__)
        try:
            ids_set = set(map(int, ids_list))
        except (TypeError, ValueError) as e:
            raise InvalidArgument('id can not be formated: %(class)s' % e.__class__.__name__)
        if len(ids_set) < 1:
            raise InvalidArgument('No entity found for id')
        return ids_set


class Idformater(object):
    """This Descriptor code copy from Wsgify
    This class will format server_id on kwargs
    Instance must has attr all_id
    这里的描述器实现参考来源是webob.dec.wsgify
    作用在于格式化传入的id转为校验后的list
    formatfunc 传入的id被实例的指定方法格式化
    """
    def __init__(self, func=None, key='id', formatfunc=None):
        self.func = func
        self.key = key
        self.formatfunc = formatfunc

    def __get__(self, instance, owner):
        if hasattr(self.func, '__get__'):
            if self.formatfunc is not None:
                if not hasattr(instance, self.formatfunc):
                    raise RuntimeError('%s dose not has attr %s' % (owner.__name__, self.formatfunc))
                formatfunc = getattr(instance, self.formatfunc)
            else:
                formatfunc = None
            formater = self.__class__(func=self.func.__get__(instance, owner),
                                      key=self.key,
                                      formatfunc=formatfunc)
            return formater
        else:
            return self

    def __call__(self, *args, **kwargs):
        if self.func is None:
            return self.__class__(func=args[0],
                                  key=self.key,
                                  formatfunc=self.formatfunc)
        else:

            if self.formatfunc is not None:
                ids = kwargs.pop(self.key, None)
                kwargs[self.key] = self.formatfunc(ids)
        return self.func(*args, **kwargs)
