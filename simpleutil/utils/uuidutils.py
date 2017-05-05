import time
import struct
import uuid

from simpleutil.utils.timeutils import monotonic

def generate_uuid():
    """Creates a random uuid string.

    :returns: string
    """
    return str(uuid.uuid4())


def _format_uuid_string(string):
    return (string.replace('urn:', '')
                  .replace('uuid:', '')
                  .strip('{}')
                  .replace('-', '')
                  .lower())


def is_uuid_like(val):
    """Returns validation of a value as a UUID.

    :param val: Value to verify
    :type val: string
    :returns: bool

    .. versionchanged:: 1.1.1
       Support non-lowercase UUIDs.
    """
    try:
        return str(uuid.UUID(val)).replace('-', '') == _format_uuid_string(val)
    except (TypeError, ValueError, AttributeError):
        return False


class Gprimarykey(object):
    """A global primark key maker like Snowflake
    0-47  time
    48-55 sid  max 255
    56-63 sequence  max 255
    """

    PREFIX = chr(0)*2

    def __init__(self, sid,
                 diff=int(time.time()*1000) - int(monotonic()*1000),
                 ):
        self.__diff = diff
        self.__last = 0
        self.__sequence = 0
        self.__mark = sid

    def update_diff(self, diff):
        self.__diff = diff

    def __call__(self):
        return self.makekey(self.__mark)

    def makekey(self, sid):
        """Make a global primark key"""
        cur = int(monotonic()*1000) + self.__diff
        if self.__last == cur:
            if self.__sequence >= 255:
                time.sleep(0.001)
                # recursive call
                return self.__call__()
            self.__sequence += 1
        else:
            self.__sequence = 0
            self.__last = cur
        return struct.unpack('>Q', struct.pack('>QBB', cur, sid, self.__sequence)[2:])[0]

    def format(self, key):
        if isinstance(key, (int, long)):
            key = struct.pack('>Q', key)
        return struct.unpack('>QBB', Gprimarykey.PREFIX + key)

    def timeformat(self, key):
        return self.format(key)[0]

    def sidformat(self, key):
        return self.format(key)[1]
