import abc
import six


@six.add_metaclass(abc.ABCMeta)
class Excluder(object):
    @abc.abstractmethod
    def __call__(self, compretype, shell=False):
        """find excluder function"""
