import os
import zlib
import hashlib

import six

from simpleutil.common import exceptions


def openfile(file_path):
    if not os.path.exists(file_path) or not os.access(file_path, os.R_OK):
        raise exceptions.InvalidArgument('file not exist or can not be read')
    try:
        f = open(file_path, 'rb')
    except IOError:
        raise exceptions.InvalidArgument('open file io error')
    except OSError:
        raise exceptions.InvalidArgument('open file os error')
    return f


def filemd5(file_path):
    md5_instance = hashlib.md5()
    f = openfile(file_path)
    bytes = f.read(10240)
    while(bytes != six.binary_type('')):
        md5_instance.update(bytes)
        bytes = f.read(10240)
    f.close()
    md5value = md5_instance.hexdigest()
    return md5value


def filecrc32(file_path):
    f = openfile(file_path)
    bytes = f.read(10240)
    crc = 0
    while(bytes != six.binary_type('')):
        crc = zlib.crc32(bytes, crc)
        bytes = f.read(10240)
    f.close()
    return '%x' % (crc & 0xffffffff)
