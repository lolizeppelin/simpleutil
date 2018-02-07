# -*- coding: UTF-8 -*-
import re
from simpleutil.common.exceptions import InvalidArgument

# regx = re.compile('^([0-9]+?)-([0-9]+?)$')
regx = re.compile('^([1-9]\d*?)-([1-9]\d*?)$')


def map_with(ids, func):
    if isinstance(ids, basestring):
        ids_list = ids.split(',')
    elif isinstance(ids, (list, tuple, set, frozenset)):
        ids_list = ids
    elif isinstance(ids, (int, long)):
        ids_list = [ids, ]
    else:
        raise InvalidArgument('id can not be formated from %s' % ids.__class__.__name__)
    try:
        ids_set = set(map(func, ids_list))
    except (TypeError, ValueError) as e:
        raise InvalidArgument('id can not be formated: %(class)s' % e.__class__.__name__)
    if len(ids_set) < 1:
        raise InvalidArgument('Input list is empty')
    return ids_set


def map_to_int(ids):
    if isinstance(ids, basestring):
        ids_list = ids.split(',')
    elif isinstance(ids, (list, tuple, set, frozenset)):
        ids_list = ids
    elif isinstance(ids, (int, long)):
        ids_list = [ids, ]
    else:
        raise InvalidArgument('id can not be formated from %s' % ids.__class__.__name__)
    _ids = set()
    for value in ids_list:
        if isinstance(value, (int, long)):
            _ids.add(value)
        if isinstance(value, basestring):
            if value.isdigit():
                _ids.add(int(value))
                continue
            match = re.match(regx, value)
            if match:
                down, up = int(match.group(1)), int(match.group(2))
                if up == down:
                    _ids.add(down)
                    continue
                if down > up:
                    down, up = up, down
                    # raise InvalidArgument('down value big thne up value')
                for i in xrange(down, up+1):
                    _ids.add(i)
            else:
                raise InvalidArgument('%s can not format to int' % str(value))
    return _ids


def unmap(ids, split='-'):
    if isinstance(ids, (list, tuple)):
        ids = list(set(ids))
    elif isinstance(ids, (frozenset, set)):
        ids = list(ids)
    else:
        raise InvalidArgument('ids is not list set or tuple')
    ids.sort()
    results = []
    tmp = []
    for index, value in enumerate(ids):
        if index == 0:
            tmp.append(value)
            continue
        if value - 1 != ids[index - 1]:
            if len(tmp) < 2:
                results.append(str(tmp[0]))
            else:
                results.append('%s%s%s' % (str(tmp[0]), split, str(tmp[-1])))
            del tmp[:]
        tmp.append(value)
    if tmp:
        if len(tmp) < 2:
            results.append(str(tmp[0]))
        else:
            results.append('%s%s%s' % (str(tmp[0]), split, str(tmp[-1])))
        del tmp[:]
    return results


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
