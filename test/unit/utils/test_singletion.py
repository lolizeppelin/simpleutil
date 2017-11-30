
from simpleutil.utils import singleton

@singleton.singleton
class Me(object):
    pass


@singleton.singleton
class Ma(object):
    pass


@singleton.singleton
class G(object):

    def __init__(self):
        x = Me()

x = Me()
y = Ma()

print x.__class__.__class__
print y.__class__.__class__

print Me._instances
print Ma._instances

z = G()

print 'ok'