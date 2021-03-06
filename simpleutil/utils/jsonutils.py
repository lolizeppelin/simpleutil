import re
import datetime
import functools
import inspect
import itertools
import json
import uuid
import codecs

import six
import netaddr
import jsonschema
from jsonschema import exceptions as schema_exc
from jsonschema import _format


try:
    import six.moves.xmlrpc_client as xmlrpclib
except:
    import xmlrpclib as xmlrpclib

from simpleutil.utils import encodeutils
from simpleutil.utils import attributes
from simpleutil.utils.timeutils import PERFECT_TIME_FORMAT


# Special jsonschema validation types/adjustments.
_SCHEMA_TYPES = {
    # See: https://github.com/Julian/jsonschema/issues/148
    'array': (list, tuple, set, frozenset),
}

# Expose these types so that people don't have to import the same exceptions.
ValidationError = schema_exc.ValidationError
SchemaError = schema_exc.SchemaError

_simple_types = (six.string_types + six.integer_types + (type(None), bool, float))
_nasty_type_tests = [inspect.ismodule, inspect.isclass, inspect.ismethod,
                     inspect.isfunction, inspect.isgeneratorfunction,
                     inspect.isgenerator, inspect.istraceback, inspect.isframe,
                     inspect.iscode, inspect.isbuiltin, inspect.isroutine,
                     inspect.isabstract]

MAX_DEEP = 5


def _encode_list(json_list, encoding):
    rv = []
    for item in json_list:
        if isinstance(item, basestring):
            item = encodeutils.safe_encode(item, encoding)
        elif isinstance(item, (list, tuple, set)):
            item = _encode_list(item, encoding)
        elif isinstance(item, dict):
            item = _encode_dict(item, encoding)
        rv.append(item)
    return rv


def _encode_dict(json_dict, encoding):
    rv = {}
    for key, value in json_dict.iteritems():
        if isinstance(key, basestring):
            key = encodeutils.safe_encode(key, encoding)
        else:
            raise TypeError("%s can't be encoded" % type(key))
        if isinstance(value, basestring):
            value = encodeutils.safe_encode(value, encoding)
        elif isinstance(value, (list, tuple, set)):
            value = _encode_list(value, encoding)
        elif isinstance(value, dict):
            value = _encode_dict(value, encoding)
        rv[key] = value
    return rv


def _object_hook(encoding):

    def wrapper(obj):
        if isinstance(obj, dict):
            return _encode_dict(obj, encoding)
        elif isinstance(obj, (list, set, tuple)):
            return _encode_list(obj, encoding)

    return wrapper


def to_primitive(value, convert_instances=False, convert_datetime=True,
                 level=0, max_depth=MAX_DEEP):
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


def loads(s, encoding='utf-8', **kwargs):
    """Deserialize ``s`` (a ``str`` or ``unicode`` instance containing a JSON

    :param s: string to deserialize
    :param encoding: encoding used to interpret the string
    :param kwargs: extra named parameters, please see documentation \
    of `json.loads <https://docs.python.org/2/library/json.html#basic-usage>`_
    :returns: python object
    """
    return json.loads(encodeutils.safe_decode(s, encoding), **kwargs)


def loads_as_bytes(s, encoding='utf-8'):
    object_hook = _object_hook(encoding)
    obj = loads(s, encoding, object_hook=object_hook)
    if isinstance(obj, list):
        for index, value in enumerate(obj):
            if isinstance(value, unicode):
                obj[index] = encodeutils.safe_encode(value, encoding)
    return obj


def safe_loads(var):
    if var is None:
        return None
    return loads(var)


def safe_loads_as_bytes(var, encoding='utf-8'):
    if var is None:
        return None
    return loads_as_bytes(var, encoding)


def dumps(obj, default=to_primitive, **kwargs):
    serialized = json.dumps(obj, default=default, **kwargs)
    if isinstance(serialized, six.binary_type):
        serialized = serialized.decode(kwargs.get('encoding', 'utf-8'))
    return serialized


def dumps_as_bytes(obj, default=to_primitive, encoding='utf-8', **kwargs):
    """Serialize ``obj`` to a JSON formatted ``bytes``.

    :param obj: object to be serialized
    :param default: function that returns a serializable version of an object,
                    :func:`to_primitive` is used by default.
    :param encoding: encoding used to encode the serialized JSON output
    :param kwargs: extra named parameters, please see documentation \
    of `json.dumps <https://docs.python.org/2/library/json.html#basic-usage>`_
    :returns: json formatted string

    .. versionadded:: 1.10
    """
    serialized = dumps(obj, default=default, **kwargs)
    if isinstance(serialized, six.text_type):
        # On Python 3, json.dumps() returns Unicode
        serialized = serialized.encode(encoding)
    return serialized


def safe_dumps(var):
    if var is None:
        return None
    return dumps(var)


def safe_dumps_as_bytes(var):
    if var is None:
        return None
    return dumps_as_bytes(var)


def dump(obj, fp, *args, **kwargs):
    """Serialize ``obj`` as a JSON formatted stream to ``fp``

    :param obj: object to be serialized
    :param fp: a ``.write()``-supporting file-like object
    :param default: function that returns a serializable version of an object,
                    :func:`to_primitive` is used by default.
    :param args: extra arguments, please see documentation \
    of `json.dump <https://docs.python.org/2/library/json.html#basic-usage>`_
    :param kwargs: extra named parameters, please see documentation \
    of `json.dump <https://docs.python.org/2/library/json.html#basic-usage>`_

    .. versionchanged:: 1.3
       The *default* parameter now uses :func:`to_primitive` by default.
    """
    default = kwargs.get('default', to_primitive)
    return json.dump(obj, fp, default=default, *args, **kwargs)


def load(fp, encoding='utf-8', **kwargs):
    """Deserialize ``fp`` to a Python object.

    :param fp: a ``.read()`` -supporting file-like object
    :param encoding: encoding used to interpret the string
    :param kwargs: extra named parameters, please see documentation \
    of `json.loads <https://docs.python.org/2/library/json.html#basic-usage>`_
    :returns: python object
    """
    return json.load(codecs.getreader(encoding)(fp), **kwargs)

# add formater date-time for jsonschema 2.4
if not hasattr(_format, 'is_datetime'):
    try:
        import strict_rfc3339
    except ImportError:
        try:
            import isodate
        except ImportError:
            def is_datetime(instance):
                if not isinstance(instance, six.string_types):
                    return True
                return datetime.datetime.strptime(instance, "%Y-%m-%d %H:%M:%S")
        else:
            def is_datetime(instance):
                if not isinstance(instance, six.string_types):
                    return True
                return isodate.parse_datetime(instance)
    else:
        def is_datetime(instance):
            if not isinstance(instance, six.string_types):
                return True
            return strict_rfc3339.validate_rfc3339(instance)

    for _draft_name, _draft in six.iteritems(_format._draft_checkers):
        if 'date-time' not in _draft:
            _format._draft_checkers[_draft_name].append('date-time')
        func = _format.FormatChecker.cls_checks('date-time', (ValueError, ))(is_datetime)
        setattr(_format, 'is_datetime', func)


for _draft_name, _draft in six.iteritems(_format._draft_checkers):
    _format._draft_checkers[_draft_name].append('uuid')
    _format._draft_checkers[_draft_name].append('md5')
    _format._draft_checkers[_draft_name].append('crc32')

func = _format.FormatChecker.cls_checks('uuid', (ValueError,))(attributes.is_uuid_like)
setattr(_format, 'is_uuid', func)
func = _format.FormatChecker.cls_checks('md5', (ValueError,))(attributes.is_md5_like)
setattr(_format, 'is_md5', func)
func = _format.FormatChecker.cls_checks('crc32', (ValueError,))(attributes.is_crc32_like)
setattr(_format, 'is_crc32', func)

FormatChecker = jsonschema.FormatChecker()


def schema_validate(data, schema, checker=None):
    """Validates given data using provided json schema."""
    jsonschema.validate(data, schema, types=_SCHEMA_TYPES,
                        format_checker=checker or FormatChecker)
