# -*- coding: UTF-8 -*-
import os
import six
import abc
import time
import stat
import signal
import eventlet
import subprocess
from zipfile import ZIP_DEFLATED
from tarfile import _Stream
from tarfile import RECORDSIZE

from simpleutil.utils import systemutils

if not systemutils.PY27:
    import zipfile
    import tarfile


    class ZipFile(zipfile.ZipFile):

        def __enter__(self):
            return self

        def __exit__(self, type, value, traceback):
            self.close()


    class TarFile(tarfile.TarFile):

        def __enter__(self):
            self._check()
            return self

        def __exit__(self, type, value, traceback):
            if type is None:
                self.close()
            else:
                # An exception occurred. We must not call close() because
                # it would try to write end-of-archive blocks and padding.
                if not self._extfileobj:
                    self.fileobj.close()
                self.closed = True
else:
    from zipfile import ZipFile
    from tarfile import TarFile


class CompressBreak(Exception):
    """Compress Stop Exception"""


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
        self.comprer = None

    @abc.abstractmethod
    def compress(self, fileobj, exclude=None, timeout=None):
        """压缩函数
        fileobj  object like file object
        """

    @abc.abstractmethod
    def cancel(self):
        """压缩取消"""


@six.add_metaclass(abc.ABCMeta)
class Adapter(object):
    def __init__(self, src):
        self.src = src

    @abc.abstractmethod
    def compress(self, fileobj, topdir=True, timeout=None):
        """execute compress"""

    @abc.abstractmethod
    def cancel(self):
        """cancel compress"""


class GzCompress(ImplCompress):
    def __init__(self, path):
        super(GzCompress, self).__init__(path)
        self.gzobj = None
        self.timer = None

    def compress(self, fileobj, topdir=True, exclude=None, timeout=None):
        hub = eventlet.hubs.get_hub()
        timeout = timeout or 1200
        self.timer = hub.schedule_call_global(timeout, self.cancel)
        with TarFile(name=None, mode='w', fileobj=_Stream(None, 'w', 'gz', fileobj, RECORDSIZE)) as gzobj:
            self.gzobj = gzobj
            gzobj._extfileobj = False
            self.comprer = gzobj
            if os.path.isfile(self.src) or topdir:
                gzobj.add(name=self.src,
                          arcname=self.target,
                          recursive=True, exclude=exclude)
            else:
                for target in os.listdir(self.src):
                    gzobj.add(name=os.path.join(self.src, target),
                              arcname=target,
                              recursive=True, exclude=exclude)

    def cancel(self):
        def raise_to_stop(*args, **kwargs):
            raise CompressBreak('Cancel called')

        if self.timer:
            self.timer.cancel()
            self.timer = None
        if self.gzobj:
            self.gzobj.add = raise_to_stop
            self.gzobj.addfile = raise_to_stop


class ZipCompress(ImplCompress):
    def __init__(self, path):
        super(ZipCompress, self).__init__(path)
        self.overtime = 0

    def compress(self, fileobj, topdir=True, exclude=None, timeout=None):
        """"""
        now = int(time.time())
        self.overtime = now + int(timeout if timeout else 3600)
        with ZipFile(file=fileobj, compression=ZIP_DEFLATED, mode='w') as zipobj:
            if os.path.isdir(self.src):
                cut = len(self.src) + 1
                if topdir:
                    cut = len(self.root) + 1
                    zipobj.write(filename=self.src, arcname=self.target)
                for root, dirs, files in os.walk(self.src):
                    if int(time.time()) > self.overtime:
                        raise CompressBreak('Cancel called or overtime')
                    for _dir in dirs:
                        dir_name = os.path.join(root, _dir)
                        if exclude and exclude(dir_name[cut:]):
                            continue
                        zipobj.write(filename=dir_name, arcname=dir_name[cut:])
                    for _file in files:
                        if int(time.time()) > self.overtime:
                            raise CompressBreak('Cancel called or overtime')
                        file_name = os.path.join(root, _file)
                        if exclude and exclude(file_name[cut:]):
                            continue
                        zipobj.write(filename=file_name, arcname=file_name[cut:])
            elif os.path.isfile(self.src):
                file_stat = os.stat(self.src)
                # 文件是否为普通文件
                if not stat.S_ISREG(file_stat[stat.ST_MODE]):
                    raise IOError('file type error')
                zipobj.write(filename=self.src, arcname=self.target)
            else:
                raise IOError('not file or dir %s' % self.src)

    def cancel(self):
        self.overtime = 0


class ShellAdapter(Adapter):
    """shell compress"""

    def __init__(self, src, comptype, exclude=None, prefunc=None):
        super(ShellAdapter, self).__init__(src)
        self.comptype = comptype
        self.exclude = exclude(compretype=self.compretype, shell=True) if exclude else None
        self.prefunc = prefunc
        self.sub = None

    @staticmethod
    def build_command(compretype, src, fileobj, exclude):
        raise NotImplementedError('Shel comper adapter not impl')

    def compress(self, fileobj, topdir=True, timeout=None):
        exclude = self.exclude
        executable, args = ShellAdapter.build_command(self.comptype, self.src, fileobj, exclude)
        self.sub = subprocess.Popen(args, executable=executable, stdout=fileobj.fileno(),
                                    close_fds=True, preexec_fn=self.prefunc)
        systemutils.subwait(self.sub, timeout)
        self.sub = None

    def cancel(self):
        if self.sub:
            self.sub.kill()


class NativeAdapter(Adapter):
    MAP = {'gz': GzCompress,
           'zip': ZipCompress}

    def __init__(self, src, compretype, exclude=None, fork=None):
        super(NativeAdapter, self).__init__(src)
        self.compretype = compretype
        comprer_cls = NativeAdapter.MAP[compretype]
        self.comprer = comprer_cls(src)
        self.exclude = exclude(compretype=self.compretype, shell=False) if exclude else None
        self.fork = fork
        self.pid = None

    def compress(self, fileobj, topdir=True, timeout=None):
        exclude = self.exclude
        if self.fork:
            self.pid = pid = self.fork()
            if pid == 0:
                # close fd exclude file object fd
                os.closerange(3, fileobj.fileno())
                os.closerange(fileobj.fileno() + 1, systemutils.MAXFD)
                self.comprer.compress(fileobj, topdir, exclude, timeout)
                os._exit(0)
            else:
                from simpleutil.utils.systemutils import posix
                posix.wait(pid, timeout)
        else:
            self.comprer.compress(fileobj, topdir, exclude, timeout)

    def cancel(self):
        if self.pid:
            os.kill(self.pid, signal.SIGKILL)
        else:
            self.comprer.cancel()


class ZlibStream(object):

    def __init__(self, path, compretype,
                 native=True, exclude=None, fork=None, prefunc=None):
        """
        不支持设置压缩等级,需要继承后改动函数,不确定兼容性
        zip压缩使用压缩等级8
        gz压缩使用等级9
        """
        if fork and not systemutils.POSIX:
            raise TypeError('Can not fork on windows system')

        if not os.path.exists(path):
            raise ValueError('source path not exists')
        self.native = native
        if native:
            self.adapter = NativeAdapter(path, compretype, exclude, fork)
        else:
            self.adapter = ShellAdapter(path, compretype, exclude, prefunc)

    def compr2fobj(self, fileobj, topdir=True, timeout=None):
        self.adapter.compress(fileobj, topdir, timeout)

    def compr2file(self, dst, topdir=True, timeout=None):
        with open(dst, 'wb') as fileobj:
            self.compr2fobj(fileobj, topdir, timeout)

    def cancel(self):
        self.adapter.cancel()
