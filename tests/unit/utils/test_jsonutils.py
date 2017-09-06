from simpleutil.utils import jsonutils


buffer = None

try:
    print jsonutils.loads_as_bytes(buffer)
except TypeError:
    print 'test success'