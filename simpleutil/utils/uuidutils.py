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
    0-42    time                   42  bit
    42-53   sid       max 2047     11  bit
    53-61   pid       max 255      8   bit
    61-64   sequence  max 7        3   bit
    """
    def __init__(self, sid, pid,
                 diff=int(time.time()*1000) - int(monotonic()*1000),
                 ):
        self.__diff = diff
        self.__last = 0
        self.__sequence = 0
        if pid >=256 or sid >= 2048:
            raise RuntimeError('sid should less then 2048 pid should less then 256')
        self.__sid = sid
        self.__pid = pid

    def update_diff(self, diff):
        self.__diff = diff

    def __call__(self):
        return self.makekey(self.__sid, self.__pid)

    def makekey(self, sid, pid):
        """Make a global primark key"""
        if pid >=256 or sid >= 2048:
            raise RuntimeError('sid should less then 2048 pid should less then 256')
        cur = int(monotonic()*1000) + self.__diff
        if self.__last == cur:
            if self.__sequence >= 8:
                time.sleep(0.001)
                # recursive call
                return self.makekey(sid, pid)
            self.__sequence += 1
        else:
            self.__sequence = 0
            self.__last = cur
            # over time at 4398046511103 == 2109-05-15 15:35:11
            part_time = cur << 22
            part_server = sid << 11
            part_pid = pid << 3
            key = part_time | part_server |  part_pid | self.__sequence
            return key

    def timeformat(self, key):
        return key >> 22

    def sidformat(self, key):
        return (key & (2047 << 53) >> 42) >> 11
