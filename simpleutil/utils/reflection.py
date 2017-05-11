# -*- coding: utf-8 -*-

#    Copyright (C) 2012-2013 Yahoo! Inc. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Reflection module.

.. versionadded:: 1.1
"""
import warnings
import inspect
import types
import six

try:
    _TYPE_TYPE = types.TypeType
except AttributeError:
    _TYPE_TYPE = type

# See: https://docs.python.org/2/library/__builtin__.html#module-__builtin__
# and see https://docs.python.org/2/reference/executionmodel.html (and likely
# others)...
_BUILTIN_MODULES = ('builtins', '__builtin__', '__builtins__', 'exceptions')

# if six.PY3:
#     Parameter = inspect.Parameter
#     Signature = inspect.Signature
#     get_signature = inspect.signature
# else:
#     # Provide an equivalent but use funcsigs instead...
#     import funcsigs
#     Parameter = funcsigs.Parameter
#     Signature = funcsigs.Signature
#     get_signature = funcsigs.signature


def get_members(obj, exclude_hidden=True):
    """Yields the members of an object, filtering by hidden/not hidden.

    .. versionadded:: 2.3
    """
    for (name, value) in inspect.getmembers(obj):
        if name.startswith("_") and exclude_hidden:
            continue
        yield (name, value)


def get_member_names(obj, exclude_hidden=True):
    """Get all the member names for a object."""
    return [name for (name, _obj) in
            get_members(obj, exclude_hidden=exclude_hidden)]


def get_class_name(obj, fully_qualified=True):
    """Get class name for object.

    If object is a type, returns name of the type. If object is a bound
    method or a class method, returns its ``self`` object's class name.
    If object is an instance of class, returns instance's class name.
    Else, name of the type of the object is returned. If fully_qualified
    is True, returns fully qualified name of the type. For builtin types,
    just name is returned. TypeError is raised if can't get class name from
    object.
    """
    if inspect.isfunction(obj):
        raise TypeError("Can't get class name.")

    if inspect.ismethod(obj):
        obj = get_method_self(obj)
    if not isinstance(obj, six.class_types):
        obj = type(obj)
    try:
        built_in = obj.__module__ in _BUILTIN_MODULES
    except AttributeError:  # nosec
        pass
    else:
        if built_in:
            return obj.__name__

    if fully_qualified and hasattr(obj, '__module__'):
        return '%s.%s' % (obj.__module__, obj.__name__)
    else:
        return obj.__name__


def get_all_class_names(obj, up_to=object):
    """Get class names of object parent classes.

    Iterate over all class names object is instance or subclass of,
    in order of method resolution (mro). If up_to parameter is provided,
    only name of classes that are sublcasses to that class are returned.
    """
    if not isinstance(obj, six.class_types):
        obj = type(obj)
    for cls in obj.mro():
        if issubclass(cls, up_to):
            yield get_class_name(cls)


def get_callable_name(function):
    """Generate a name from callable.

    Tries to do the best to guess fully qualified callable name.
    """
    method_self = get_method_self(function)
    if method_self is not None:
        # This is a bound method.
        if isinstance(method_self, six.class_types):
            # This is a bound class method.
            im_class = method_self
        else:
            im_class = type(method_self)
        try:
            parts = (im_class.__module__, function.__qualname__)
        except AttributeError:
            parts = (im_class.__module__, im_class.__name__, function.__name__)
    elif inspect.ismethod(function) or inspect.isfunction(function):
        # This could be a function, a static method, a unbound method...
        try:
            parts = (function.__module__, function.__qualname__)
        except AttributeError:
            if hasattr(function, 'im_class'):
                # This is a unbound method, which exists only in python 2.x
                im_class = function.im_class
                parts = (im_class.__module__,
                         im_class.__name__, function.__name__)
            else:
                parts = (function.__module__, function.__name__)
    else:
        im_class = type(function)
        if im_class is _TYPE_TYPE:
            im_class = function
        try:
            parts = (im_class.__module__, im_class.__qualname__)
        except AttributeError:
            parts = (im_class.__module__, im_class.__name__)
    return '.'.join(parts)


def get_method_self(method):
    """Gets the ``self`` object attached to this method (or none)."""
    if not inspect.ismethod(method):
        return None
    try:
        return six.get_method_self(method)
    except AttributeError:
        return None


def is_same_callback(callback1, callback2, strict=True):
    """Returns if the two callbacks are the same."""
    if callback1 is callback2:
        # This happens when plain methods are given (or static/non-bound
        # methods).
        return True
    if callback1 == callback2:
        if not strict:
            return True
        # Two bound methods are equal if functions themselves are equal and
        # objects they are applied to are equal. This means that a bound
        # method could be the same bound method on another object if the
        # objects have __eq__ methods that return true (when in fact it is a
        # different bound method). Python u so crazy!
        try:
            self1 = six.get_method_self(callback1)
            self2 = six.get_method_self(callback2)
            return self1 is self2
        except AttributeError:  # nosec
            pass
    return False


def is_bound_method(method):
    """Returns if the given method is bound to an object."""
    return get_method_self(method) is not None


def is_subclass(obj, cls):
    """Returns if the object is class and it is subclass of a given class."""
    return inspect.isclass(obj) and issubclass(obj, cls)


# def get_callable_args(function, required_only=False):
#     """Get names of callable arguments.
#
#     Special arguments (like ``*args`` and ``**kwargs``) are not included into
#     output.
#
#     If required_only is True, optional arguments (with default values)
#     are not included into output.
#     """
#     sig = get_signature(function)
#     function_args = list(six.iterkeys(sig.parameters))
#     for param_name, p in six.iteritems(sig.parameters):
#         if (p.kind in (Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD)
#                 or (required_only and p.default is not Parameter.empty)):
#             function_args.remove(param_name)
#     return function_args


# def accepts_kwargs(function):
#     """Returns ``True`` if function accepts kwargs otherwise ``False``."""
#     sig = get_signature(function)
#     return any(p.kind == Parameter.VAR_KEYWORD
#                for p in six.itervalues(sig.parameters))

#  --------------code from python2-debtcollector-1.3.0-1.el7---------------------

_enabled = True

def get_qualified_name(obj):
    # Prefer the py3.x name (if we can get at it...)
    try:
        return (True, obj.__qualname__)
    except AttributeError:
        return (False, obj.__name__)


def _get_qualified_name(obj):
    return get_qualified_name(obj)[1]


def deprecation(message, stacklevel=None, category=None):
    """Warns about some type of deprecation that has been (or will be) made.

    This helper function makes it easier to interact with the warnings module
    by standardizing the arguments that the warning function recieves so that
    it is easier to use.

    This should be used to emit warnings to users (users can easily turn these
    warnings off/on, see https://docs.python.org/2/library/warnings.html
    as they see fit so that the messages do not fill up the users logs with
    warnings that they do not wish to see in production) about functions,
    methods, attributes or other code that is deprecated and will be removed
    in a future release (this is done using these warnings to avoid breaking
    existing users of those functions, methods, code; which a library should
    avoid doing by always giving at *least* N + 1 release for users to address
    the deprecation warnings).
    """
    if not _enabled:
        return
    if category is None:
        category = DeprecationWarning
    if stacklevel is None:
        warnings.warn(message, category=category)
    else:
        warnings.warn(message, category=category, stacklevel=stacklevel)


def _fetch_first_result(fget, fset, fdel, apply_func, value_not_found=None):
    """Fetch first non-none/empty result of applying ``apply_func``."""
    for f in filter(None, (fget, fset, fdel)):
        result = apply_func(f)
        if result:
            return result
    return value_not_found


def generate_message(prefix, postfix=None, message=None,
                     version=None, removal_version=None):
    """Helper to generate a common message 'style' for deprecation helpers."""
    message_components = [prefix]
    if version:
        message_components.append(" in version '%s'" % version)
    if removal_version:
        if removal_version == "?":
            message_components.append(" and will be removed in a future"
                                      " version")
        else:
            message_components.append(" and will be removed in version '%s'"
                                      % removal_version)
    if postfix:
        message_components.append(postfix)
    if message:
        message_components.append(": %s" % message)
    return ''.join(message_components)


class removed_property(object):
    """Property descriptor that deprecates a property.

    This works like the ``@property`` descriptor but can be used instead to
    provide the same functionality and also interact with the :mod:`warnings`
    module to warn when a property is accessed, set and/or deleted.

    :param message: string used as ending contents of the deprecate message
    :param version: version string (represents the version this deprecation
                    was created in)
    :param removal_version: version string (represents the version this
                            deprecation will be removed in); a string
                            of '?' will denote this will be removed in
                            some future unknown version
    :param stacklevel: stacklevel used in the :func:`warnings.warn` function
                       to locate where the users code is when reporting the
                       deprecation call (the default being 3)
    :param category: the :mod:`warnings` category to use, defaults to
                     :py:class:`DeprecationWarning` if not provided
    """

    # Message templates that will be turned into real messages as needed.
    _PROPERTY_GONE_TPLS = {
        'set': "Setting the '%s' property is deprecated",
        'get': "Reading the '%s' property is deprecated",
        'delete': "Deleting the '%s' property is deprecated",
    }

    def __init__(self, fget=None, fset=None, fdel=None, doc=None,
                 stacklevel=3, category=DeprecationWarning,
                 version=None, removal_version=None, message=None):
        self.fset = fset
        self.fget = fget
        self.fdel = fdel
        self.stacklevel = stacklevel
        self.category = category
        self.version = version
        self.removal_version = removal_version
        self.message = message
        if doc is None and inspect.isfunction(fget):
            doc = getattr(fget, '__doc__', None)
        self._message_cache = {}
        self.__doc__ = doc

    def _fetch_message_from_cache(self, kind):
        try:
            out_message = self._message_cache[kind]
        except KeyError:
            prefix_tpl = self._PROPERTY_GONE_TPLS[kind]
            prefix = prefix_tpl % _fetch_first_result(
                self.fget, self.fset, self.fdel, _get_qualified_name,
                value_not_found="???")
            out_message = generate_message(
                prefix, message=self.message, version=self.version,
                removal_version=self.removal_version)
            self._message_cache[kind] = out_message
        return out_message

    def __call__(self, fget, **kwargs):
        self.fget = fget
        self.message = kwargs.get('message', self.message)
        self.version = kwargs.get('version', self.version)
        self.removal_version = kwargs.get('removal_version',
                                          self.removal_version)
        self.stacklevel = kwargs.get('stacklevel', self.stacklevel)
        self.category = kwargs.get('category', self.category)
        self.__doc__ = kwargs.get('doc',
                                  getattr(fget, '__doc__', self.__doc__))
        # Regenerate all the messages...
        self._message_cache.clear()
        return self

    def __delete__(self, obj):
        if self.fdel is None:
            raise AttributeError("can't delete attribute")
        out_message = self._fetch_message_from_cache('delete')
        deprecation(out_message, stacklevel=self.stacklevel, category=self.category)
        self.fdel(obj)

    def __set__(self, obj, value):
        if self.fset is None:
            raise AttributeError("can't set attribute")
        out_message = self._fetch_message_from_cache('set')
        deprecation(out_message, stacklevel=self.stacklevel, category=self.category)
        self.fset(obj, value)

    def __get__(self, obj, value):
        if obj is None:
            return self
        if self.fget is None:
            raise AttributeError("unreadable attribute")
        out_message = self._fetch_message_from_cache('get')
        deprecation(out_message, stacklevel=self.stacklevel, category=self.category)
        return self.fget(obj)

    def getter(self, fget):
        o = type(self)(fget, self.fset, self.fdel, self.__doc__)
        o.message = self.message
        o.version = self.version
        o.stacklevel = self.stacklevel
        o.removal_version = self.removal_version
        o.category = self.category
        return o

    def setter(self, fset):
        o = type(self)(self.fget, fset, self.fdel, self.__doc__)
        o.message = self.message
        o.version = self.version
        o.stacklevel = self.stacklevel
        o.removal_version = self.removal_version
        o.category = self.category
        return o

    def deleter(self, fdel):
        o = type(self)(self.fget, self.fset, fdel, self.__doc__)
        o.message = self.message
        o.version = self.version
        o.stacklevel = self.stacklevel
        o.removal_version = self.removal_version
        o.category = self.category
        return o
