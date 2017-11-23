import json
from simpleutil.utils import jsonutils

buffer = None

try:
    print jsonutils.loads_as_bytes(buffer)
except TypeError:
    print 'test success'




n = {'a': [u"8000-9000", u"9500-10000"], 'b':2}
u = jsonutils.dumps(n)


n = [{'a':1, 'b': 2}, {'a':1, 'b': 2},]
n = ['a', 'b', {'a': 1}]
u = jsonutils.dumps(n)


print u

# print u, type(u)
#
#
# v = json.dumps(default)
# print v, type(u)
#
#

print jsonutils.loads_as_bytes(u)
