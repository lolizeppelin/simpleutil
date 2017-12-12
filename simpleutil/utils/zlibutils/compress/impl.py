# -*- coding: UTF-8 -*-
import os
import six
import abc
import stat
from zipfile import ZipFile
from zipfile import ZIP_DEFLATED

from tarfile import _Stream
from tarfile import TarFile
from tarfile import RECORDSIZE

from simpleutil.utils.futurist import CancelledError


class GzFile(TarFile):
    #  通过get_intance初始化
    @classmethod
    def get_intance(cls, fileobj):
        t = cls(name=None, mode='w', fileobj=_Stream(None, 'w', 'gz', fileobj, RECORDSIZE))
        t._extfileobj = False
        return t


@six.add_metaclass(abc.ABCMeta)
class ImplCompress(object):

    def __init__(self, path):
        if path.endswith('/'):
            path = path[:-1]
        self.src = os.path.abspath(path)
        self.root, self.target = os.path.split(self.src)
        # 目标对象是根目录
        if not self.target:
            raise RuntimeError('Target path is root')

    @abc.abstractmethod
    def compress(self, outputobj, exclude=None):
        """"""
    @abc.abstractmethod
    def cancel(self):
        pass


class GzCompress(ImplCompress):

    def __init__(self, path):
        super(GzCompress, self).__init__(path)
        self.worker = False

    def compress(self, outputobj, exclude=None):
        """"""
        worker = GzFile.get_intance(outputobj)
        worker.add(name=self.src,
                   arcname=self.target,
                   recursive=True, exclude=exclude)
        worker.close()

    def cancel(self):
        def stopper(*args, **kwargs):
            raise CancelledError
        self.worker.add = stopper
        self.worker.addfile = stopper


class ZipCompress(ImplCompress):

    def __init__(self, path):
        super(ZipCompress, self).__init__(path)
        self.canceled = False

    def compress(self, outputobj, exclude=None):
        """"""
        worker = ZipFile(file=outputobj, compression=ZIP_DEFLATED, mode='w')
        if os.path.isdir(self.src):
            cut = len(self.root) + 1
            worker.write(filename=self.src, arcname=self.target)
            for root, dirs, files in os.walk(self.src):
                if self.canceled:
                    raise CancelledError
                for _dir in dirs:
                    dir_name = os.path.join(root, _dir)
                    if exclude and exclude(dir_name[cut:]):
                        continue
                    worker.write(filename=dir_name, arcname=dir_name[cut:])
                for _file in files:
                    file_name = os.path.join(root, _file)
                    if exclude and exclude(file_name[cut:]):
                        continue
                    worker.write(filename=file_name, arcname=file_name[cut:])
        elif os.path.isfile(self.src):
            file_stat = os.stat(self.src)
            # 文件是否为普通文件
            if not stat.S_ISREG(file_stat[stat.ST_MODE]):
                raise IOError('file type error')
            worker.write(filename=self.src, arcname=self.target)
        else:
            raise IOError('not file or dir %s' % self.src)
        worker.close()

    def cancel(self):
        self.canceled = True
