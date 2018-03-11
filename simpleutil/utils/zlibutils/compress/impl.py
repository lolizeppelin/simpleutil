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
    def __init__(self, path, native=True, topdir=True):
        if path.endswith('/'):
            path = path[:-1]
        self.native = native
        self.topdir = topdir
        self.src = os.path.abspath(path)
        self.root, self.target = os.path.split(self.src)
        # 目标对象是根目录
        if not self.target:
            raise RuntimeError('Target path is root')

    def compress(self, outputobj, exclude=None):
        """压缩函数
        outputobj  class of zlibutils.compress.Recver
        """
        if self.native:
            self._native_compress(outputobj, exclude)
        else:
            self._shell_compress(outputobj, exclude)

    @abc.abstractmethod
    def _native_compress(self, outputobj, exclude):
        """python原生解压函数"""

    def _shell_compress(self, outputobj, exclude):
        """python原生解压函数"""
        raise NotImplementedError('Can not compress by system util')

    @abc.abstractmethod
    def cancel(self):
        """压缩取消"""


class GzCompress(ImplCompress):
    def __init__(self, path, native=True, topdir=True):
        super(GzCompress, self).__init__(path, native, topdir)
        self.worker = None

    def _native_compress(self, outputobj, exclude):
        """"""
        worker = GzFile.get_intance(outputobj)
        if os.path.isfile(self.src) or self.topdir:
            worker.add(name=self.src,
                       arcname=self.target,
                       recursive=True, exclude=exclude)
        else:
            for target in os.listdir(self.src):
                worker.add(name=os.path.join(self.src, target),
                           arcname=target,
                           recursive=True, exclude=exclude)
        worker.close()

    def cancel(self):
        def stopper(*args, **kwargs):
            raise CancelledError
        self.worker.add = stopper
        self.worker.addfile = stopper


class ZipCompress(ImplCompress):
    def __init__(self, path, native=True, topdir=True):
        super(ZipCompress, self).__init__(path, native, topdir)
        self.canceled = False

    def _native_compress(self, outputobj, exclude):
        """"""
        worker = ZipFile(file=outputobj, compression=ZIP_DEFLATED, mode='w')
        if os.path.isdir(self.src):
            cut = len(self.src) + 1
            if self.topdir:
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
