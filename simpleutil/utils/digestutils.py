import os
import zlib
import hashlib
import contextlib
import six

from simpleutil.common import exceptions

BLOCK = 4096

@contextlib.contextmanager
def openfile(path):
    if not os.path.exists(path) or not os.access(path, os.R_OK):
        raise exceptions.InvalidArgument('file not exist or can not be read')
    with open(path, 'rb') as f:
        yield f
    # try:
    #     yield f
    # finally:
    #     f.close()


def filemd5(path):
    md5_instance = hashlib.md5()
    with openfile(path) as f:
        bytes = f.read(BLOCK)
        while(bytes != six.binary_type('')):
            md5_instance.update(bytes)
            bytes = f.read(BLOCK)
    return md5_instance.hexdigest()


def strmd5(buffer):
    md5_instance = hashlib.md5()
    md5_instance.update(buffer)
    return md5_instance.hexdigest()



def filecrc32(path):
    with openfile(path) as f:
        bytes = f.read(BLOCK)
        crc = 0
        while(bytes != six.binary_type('')):
            crc = zlib.crc32(bytes, crc)
            bytes = f.read(BLOCK)
        return str(crc & 0xffffffff)
