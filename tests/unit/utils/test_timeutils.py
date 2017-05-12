
from simpleutil.utils import timeutils
import datetime

x = timeutils.utcnow()

print x

y = timeutils.realnow()

print x
print y
print datetime.datetime.fromtimestamp(int(y))