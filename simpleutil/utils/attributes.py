# Copyright (c) 2012 OpenStack Foundation.
# All Rights Reserved.
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

import functools
import re
import six

import netaddr
# from simpleutil.log import log as logging
from simpleutil.utils import uuidutils

# import webob.exc

# from neutron._i18n import _
# from neutron.common import constants
# from neutron.common import exceptions as n_exc
from simpleutil.common import exceptions as n_exc


# LOG = logging.getLogger(__name__)

ATTR_NOT_SPECIFIED = object()
# Defining a constant to avoid repeating string literal in several modules
SHARED = 'shared'

# # Used by range check to indicate no limit for a bound.
# UNLIMITED = None
#
# NAME_MAX_LEN = 255
# TENANT_ID_MAX_LEN = 255
# DESCRIPTION_MAX_LEN = 255
# LONG_DESCRIPTION_MAX_LEN = 1024
# DEVICE_ID_MAX_LEN = 255
# DEVICE_OWNER_MAX_LEN = 255


def _verify_dict_keys(expected_keys, target_dict, strict=True):
    """Allows to verify keys in a dictionary.

    :param expected_keys: A list of keys expected to be present.
    :param target_dict: The dictionary which should be verified.
    :param strict: Specifies whether additional keys are allowed to be present.
    :return: True, if keys in the dictionary correspond to the specification.
    """
    if not isinstance(target_dict, dict):
        msg = ("Invalid input. '%(target_dict)s' must be a dictionary "
                 "with keys: %(expected_keys)s" %
               {'target_dict': target_dict, 'expected_keys': expected_keys})
        # LOG.debug(msg)
        return msg

    expected_keys = set(expected_keys)
    provided_keys = set(target_dict.keys())

    predicate = expected_keys.__eq__ if strict else expected_keys.issubset

    if not predicate(provided_keys):
        msg = ("Validation of dictionary's keys failed. "
                 "Expected keys: %(expected_keys)s "
                 "Provided keys: %(provided_keys)s" %
               {'expected_keys': expected_keys,
                'provided_keys': provided_keys})
        # LOG.debug(msg)
        return msg


def is_attr_set(attribute):
    return not (attribute is None or attribute is ATTR_NOT_SPECIFIED)


def _validate_list_of_items(item_validator, data, *args, **kwargs):
    if not isinstance(data, list):
        msg = "'%s' is not a list" % data
        return msg

    if len(set(data)) != len(data):
        msg = "Duplicate items in the list: '%s'" % ', '.join(data)
        return msg

    for item in data:
        msg = item_validator(item, *args, **kwargs)
        if msg:
            return msg


def _validate_values(data, valid_values=None):
    if data not in valid_values:
        msg = ("'%(data)s' is not in %(valid_values)s" %
               {'data': data, 'valid_values': valid_values})
        # LOG.debug(msg)
        return msg


def _validate_not_empty_string(data, max_len=None):
    msg = _validate_string(data, max_len=max_len)
    if msg:
        return msg
    if not data.strip():
        msg = "'%s' Blank strings are not permitted" % data
        # LOG.debug(msg)
        return msg


def _validate_string(data, max_len=None):
    if not isinstance(data, six.string_types):
        msg = "'%s' is not a valid string" % data
        # LOG.debug(msg)
        return msg

    if max_len is not None and len(data) > max_len:
        msg = ("'%(data)s' exceeds maximum length of %(max_len)s" %
               {'data': data, 'max_len': max_len})
        # LOG.debug(msg)
        return msg


validate_list_of_unique_strings = functools.partial(_validate_list_of_items,
                                                    _validate_string)


def _validate_boolean(data, valid_values=None):
    try:
        convert_to_boolean(data)
    except n_exc.InvalidInput:
        msg = "'%s' is not a valid boolean value" % data
        # LOG.debug(msg)
        return msg


def _validate_no_whitespace(data):
    """Validates that input has no whitespace."""
    if re.search(r'\s', data):
        msg = "'%s' contains whitespace" % data
        # LOG.debug(msg)
        raise n_exc.InvalidInput(msg=msg)
    return data


def _validate_mac_address(data, valid_values=None):
    try:
        valid_mac = netaddr.valid_mac(_validate_no_whitespace(data))
    except Exception:
        valid_mac = False

    if valid_mac:
        valid_mac = not netaddr.EUI(data) in map(netaddr.EUI,
                    ['00:00:00:00:00:00', 'FF:FF:FF:FF:FF:FF'])
                    # constants.INVALID_MAC_ADDRESSES)
    if not valid_mac:
        msg = "'%s' is not a valid MAC address" % data
        # LOG.debug(msg)
        return msg


def _validate_ip_address(data, valid_values=None):
    msg = None
    _validate_no_whitespace(data)
    if not netaddr.valid_ipv4(data, netaddr.core.INET_PTON) \
            and not netaddr.valid_ipv6(data, netaddr.core.INET_PTON):
        msg = "'%s' not ip address" % data
        raise n_exc.InvalidInput(msg=msg)
    return msg


def _validate_hostname(value):
    if len(value) == 0:
        raise ValueError("Cannot have an empty hostname")
    if len(value) > 253:
        raise ValueError("hostname is greater than 253 characters: %s"
                         % value)
    if value.endswith("."):
        value = value[:-1]
    allowed = re.compile("(?!-)[A-Z0-9-]{1,63}(?<!-)$", re.IGNORECASE)
    if any((not allowed.match(x)) for x in value.split(".")):
        raise ValueError("%s is an invalid hostname" % value)
    return value


def _validate_port(value):
    if isinstance(value, basestring) and value.isdigit():
        value = int(value)
    if isinstance(value, (int, long)):
        if value < 1 or value > 65535:
            raise ValueError('Port value over range')
        return int(value)
    raise ValueError('Port value type not int')


def _validate_ports_range(value):
    if isinstance(value, basestring):
        ports_range = value.split('-')
        if len(ports_range) == 2:
            d_port = _validate_port(ports_range[0])
            u_port = _validate_port(ports_range[1])
            if u_port > d_port:
                return value
        raise ValueError('Port range error')
    if isinstance(value, (int, long, basestring)):
        port = _validate_port(value)
        return '%d-%d' % (port, port+1)
    raise ValueError('Port range value error')


def _validate_ports_range_list(value):
    if isinstance(value, (int, long, basestring)):
        return [_validate_ports_range(value), ]
    if isinstance(value, (list, tuple)):
        ports_range_list = []
        for port_range in value:
            ports_range_list.append(_validate_ports_range(port_range))
        ports_range_list.sort(key=lambda x: int(x.split('-')[0]))
        last = 0
        for ports_range in ports_range_list:
            d_port, u_port = map(int, ports_range.split('-'))
            if last == 0:
                last = u_port
                continue
            if d_port < last:
                raise ValueError('Port range find duplicate ports range')
            last = u_port
        return ports_range_list
    raise ValueError('Port range list type error')


def _validate_nameservers(data, valid_values=None):
    if not hasattr(data, '__iter__'):
        msg = "Invalid data format for nameserver: '%s'" % data
        # LOG.debug(msg)
        return msg

    hosts = []
    for host in data:
        # This must be an IP address only
        msg = _validate_ip_address(host)
        if msg:
            msg = "'%(host)s' is not a valid nameserver. %(msg)s" % {
                'host': host, 'msg': msg}
            # LOG.debug(msg)
            return msg
        if host in hosts:
            msg = "Duplicate nameserver '%s'" % host
            # LOG.debug(msg)
            return msg
        hosts.append(host)


def _validate_ip_address_or_none(data, valid_values=None):
    if data is not None:
        return _validate_ip_address(data, valid_values)


def _validate_regex(data, valid_values=None):
    try:
        if re.match(valid_values, data):
            return
    except TypeError:
        pass

    msg = "'%s' is not a valid input" % data
    # LOG.debug(msg)
    return msg


def _validate_uuid(data, valid_values=None):
    if not uuidutils.is_uuid_like(data):
        msg = "'%s' is not a valid UUID" % data
        # LOG.debug(msg)
        return msg


_validate_uuid_list = functools.partial(_validate_list_of_items,
                                        _validate_uuid)


def _validate_dict_item(key, key_validator, data):
    # Find conversion function, if any, and apply it
    conv_func = key_validator.get('convert_to')
    if conv_func:
        data[key] = conv_func(data.get(key))
    # Find validator function
    # TODO(salv-orlando): Structure of dict attributes should be improved
    # to avoid iterating over items
    val_func = val_params = None
    for (k, v) in six.iteritems(key_validator):
        if k.startswith('type:'):
            # ask forgiveness, not permission
            try:
                val_func = validators[k]
            except KeyError:
                msg = "Validator '%s' does not exist." % k
                # LOG.debug(msg)
                return msg
            val_params = v
            break
    # Process validation
    if val_func:
        return val_func(data.get(key), val_params)


def _validate_dict(data, key_specs=None):
    if not isinstance(data, dict):
        msg = "'%s' is not a dictionary" % data
        # LOG.debug(msg)
        return msg
    # Do not perform any further validation, if no constraints are supplied
    if not key_specs:
        return

    # Check whether all required keys are present
    required_keys = [key for key, spec in six.iteritems(key_specs)
                     if spec.get('required')]

    if required_keys:
        msg = _verify_dict_keys(required_keys, data, False)
        if msg:
            return msg

    # Perform validation and conversion of all values
    # according to the specifications.
    for key, key_validator in [(k, v) for k, v in six.iteritems(key_specs)
                               if k in data]:
        msg = _validate_dict_item(key, key_validator, data)
        if msg:
            return msg


def _validate_dict_or_empty(data, key_specs=None):
    if data != {}:
        return _validate_dict(data, key_specs)


def _validate_non_negative(data, valid_values=None):
    try:
        data = int(data)
    except (ValueError, TypeError):
        msg = "'%s' is not an integer" % data
        # LOG.debug(msg)
        return msg

    if data < 0:
        msg = "'%s' should be non-negative" % data
        # LOG.debug(msg)
        return msg


def convert_to_boolean(data):
    if isinstance(data, six.string_types):
        val = data.lower()
        if val == "true" or val == "1":
            return True
        if val == "false" or val == "0":
            return False
    elif isinstance(data, bool):
        return data
    elif isinstance(data, int):
        if data == 0:
            return False
        elif data == 1:
            return True
    msg = "'%s' cannot be converted to boolean" % data
    raise n_exc.InvalidInput(msg=msg)


def convert_to_boolean_if_not_none(data):
    if data is not None:
        return convert_to_boolean(data)


def convert_to_int(data):
    try:
        return int(data)
    except (ValueError, TypeError):
        msg = "'%s' is not an integer" % data
        raise n_exc.InvalidInput(msg=msg)


def convert_to_int_if_not_none(data):
    if data is not None:
        return convert_to_int(data)
    return data


def convert_to_positive_float_or_none(val):
    # NOTE(salv-orlando): This conversion function is currently used by
    # a vendor specific extension only at the moment  It is used for
    # port's RXTX factor in neutron.plugins.vmware.extensions.qos.
    # It is deemed however generic enough to be in this module as it
    # might be used in future for other API attributes.
    if val is None:
        return
    try:
        val = float(val)
        if val < 0:
            raise ValueError()
    except (ValueError, TypeError):
        msg = "'%s' must be a non negative decimal." % val
        raise n_exc.InvalidInput(msg=msg)
    return val


def convert_kvp_str_to_list(data):
    """Convert a value of the form 'key=value' to ['key', 'value'].

    :raises: n_exc.InvalidInput if any of the strings are malformed
                                (e.g. do not contain a key).
    """
    kvp = [x.strip() for x in data.split('=', 1)]
    if len(kvp) == 2 and kvp[0]:
        return kvp
    msg = "'%s' is not of the form <key>=[value]" % data
    raise n_exc.InvalidInput(msg=msg)


def convert_kvp_list_to_dict(kvp_list):
    """Convert a list of 'key=value' strings to a dict.

    :raises: n_exc.InvalidInput if any of the strings are malformed
                                (e.g. do not contain a key) or if any
                                of the keys appear more than once.
    """
    if kvp_list == ['True']:
        # No values were provided (i.e. '--flag-name')
        return {}
    kvp_map = {}
    for kvp_str in kvp_list:
        key, value = convert_kvp_str_to_list(kvp_str)
        kvp_map.setdefault(key, set())
        kvp_map[key].add(value)
    return dict((x, list(y)) for x, y in six.iteritems(kvp_map))


def convert_none_to_empty_list(value):
    return [] if value is None else value


def convert_none_to_empty_dict(value):
    return {} if value is None else value


def convert_to_list(data):
    if data is None:
        return []
    elif hasattr(data, '__iter__') and not isinstance(data, six.string_types):
        return list(data)
    else:
        return [data]


HEX_ELEM = '[0-9A-Fa-f]'
UUID_PATTERN = '-'.join([HEX_ELEM + '{8}', HEX_ELEM + '{4}',
                         HEX_ELEM + '{4}', HEX_ELEM + '{4}',
                         HEX_ELEM + '{12}'])
# Note: In order to ensure that the MAC address is unicast the first byte
# must be even.
MAC_PATTERN = "^%s[aceACE02468](:%s{2}){5}$" % (HEX_ELEM, HEX_ELEM)

# Dictionary that maintains a list of validation functions
validators = {'type:dict': _validate_dict,
              'type:dict_or_empty': _validate_dict_or_empty,
              'type:ip_address': _validate_ip_address,
              'type:hostname': _validate_hostname,
              'type:ip_address_or_none': _validate_ip_address_or_none,
              'type:mac_address': _validate_mac_address,
              'type:port': _validate_port,
              'type:ports_range': _validate_ports_range,
              'type:ports_range_list': _validate_ports_range_list,
              'type:nameservers': _validate_nameservers,
              'type:non_negative': _validate_non_negative,
              'type:regex': _validate_regex,
              'type:string': _validate_string,
              'type:not_empty_string': _validate_not_empty_string,
              'type:uuid': _validate_uuid,
              'type:uuid_list': _validate_uuid_list,
              'type:values': _validate_values,
              'type:boolean': _validate_boolean,
              'type:list_of_unique_strings': validate_list_of_unique_strings}