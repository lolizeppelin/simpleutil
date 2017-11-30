import inspect


class A(object):
    pass

    def test(self):
        pass

    @classmethod
    def cls_fun(cls):
        pass

    @staticmethod
    def static_fun():
        pass

    def wtf(self):
        pass

class B:
    pass

    def test(self):
        pass

    @classmethod
    def cls_fun(cls):
        pass

    @staticmethod
    def static_fun():
        pass


def func():
    pass

a = A()
b = B()

print inspect.isfunction(func)
print inspect.isfunction(A)
print inspect.isfunction(A.cls_fun)
print inspect.isfunction(A.static_fun)
print inspect.isfunction(a)
print inspect.isfunction(a.cls_fun)
print inspect.isfunction(a.static_fun)

print '-----------'

print inspect.ismethod(func)
print inspect.ismethod(A)
print inspect.ismethod(A.cls_fun)
print inspect.ismethod(A.static_fun)
print inspect.ismethod(a)
print inspect.ismethod(a.cls_fun)
print inspect.ismethod(a.static_fun)



print '----------'

print inspect.isclass(func)
print inspect.isclass(A)
print inspect.isclass(A.cls_fun)
print inspect.isclass(A.static_fun)
print inspect.isclass(a)
print inspect.isclass(a.cls_fun)
print inspect.isclass(a.static_fun)

print inspect.ismethod(A.wtf)