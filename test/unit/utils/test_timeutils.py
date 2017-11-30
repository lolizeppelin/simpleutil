
from simpleutil.utils import timeutils
import datetime

x = timeutils.utcnow()

print x

y = timeutils.realnow()

print x
print y
print datetime.datetime.fromtimestamp(int(y))

print 'ntp check===============\n\n'

stat = timeutils.ntptime('172.17.0.3', version=4)

cur = timeutils.realnow()
print '=====%.6f' % cur

print 'tx_time %.6f' % stat.tx_time
print 'offset %.6f' % stat.offset
print 'delay %.6f' % stat.delay
print 'recv_time %.6f' % stat.recv_time
print 'orig_time %.6f' % stat.orig_time

print '\n=====%.6f' % timeutils.realnow()

print cur-stat.tx_time, stat.delay
print cur-stat.recv_time, stat.delay
print cur-stat.orig_time, stat.delay
print stat.offset