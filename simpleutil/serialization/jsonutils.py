import datetime
import itertools
import six
import netaddr
import uuid
import json
import functools
import six.moves.xmlrpc_client as xmlrpclib
import inspect


PERFECT_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'
_simple_types = (six.string_types + six.integer_types + (type(None), bool, float))
_nasty_type_tests = [inspect.ismodule, inspect.isclass, inspect.ismethod,
                     inspect.isfunction, inspect.isgeneratorfunction,
                     inspect.isgenerator, inspect.istraceback, inspect.isframe,
                     inspect.iscode, inspect.isbuiltin, inspect.isroutine,
                     inspect.isabstract]


def to_primitive(value, convert_instances=False, convert_datetime=True,
                 level=0, max_depth=3):
    if isinstance(value, _simple_types):
        return value

    if isinstance(value, xmlrpclib.DateTime):
        value = datetime.datetime(*tuple(value.timetuple())[:6])

    if isinstance(value, datetime.datetime):
        if convert_datetime:
            return value.strftime(PERFECT_TIME_FORMAT)
        else:
            return value

    if isinstance(value, uuid.UUID):
        return six.text_type(value)

    if netaddr and isinstance(value, netaddr.IPAddress):
        return six.text_type(value)

    if type(value) == itertools.count:
        return six.text_type(value)

    if any(test(value) for test in _nasty_type_tests):
        return six.text_type(value)

    if getattr(value, '__module__', None) == 'mox':
        return 'mock'

    if level > max_depth:
        return '?'

    try:
        recursive = functools.partial(to_primitive,
                                      convert_instances=convert_instances,
                                      convert_datetime=convert_datetime,
                                      level=level,
                                      max_depth=max_depth)
        if isinstance(value, dict):
            return dict((recursive(k), recursive(v))
                        for k, v in six.iteritems(value))
        elif hasattr(value, 'iteritems'):
            return recursive(dict(value.iteritems()), level=level + 1)
        # Python 3 does not have iteritems
        elif hasattr(value, 'items'):
            return recursive(dict(value.items()), level=level + 1)
        elif hasattr(value, '__iter__'):
            return list(map(recursive, value))
        elif convert_instances and hasattr(value, '__dict__'):
            # Likely an instance of something. Watch for cycles.
            # Ignore class member vars.
            return recursive(value.__dict__, level=level + 1)
    except TypeError:
        # Class objects are tricky since they may define something like
        # __iter__ defined but it isn't callable as list().
        return six.text_type(value)
    return value


def dumps(obj, default=to_primitive, **kwargs):
    return json.dumps(obj, default=default, **kwargs)
