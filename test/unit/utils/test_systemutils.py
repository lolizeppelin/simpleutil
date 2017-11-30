

from simpleutil.utils.sysemutils import get_partion_free_bytes


x = get_partion_free_bytes('c:\\windows')
# x = get_partion_free_size('c:\\')
print 'b', x
print 'kb',x/1024
print 'mb',x/(1024*1024)
print 'gb',x/(1024*1024*1024)


y =  4096*5822989
print 'b', y
print 'kb',y/1024
print 'mb',y/(1024*1024)
print 'gb',y/(1024*1024*1024)
