import os
import abc
import six
import tarfile
import zipfile
import subprocess
import signal

from simpleutil.utils import systemutils
from simpleutil.utils import futurist
from simpleutil.utils.zlibutils.waiter import Waiter

UNZIP = systemutils.find_executable('unzip')
TAR = systemutils.find_executable('tar')


class NativeTarFile(tarfile.TarFile):
    """native taifle"""

    @classmethod
    def native_open(self, file):
        return self.open(file)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def chown(self, tarinfo, targetpath):
        pass

    def chmod(self, tarinfo, targetpath):
        pass

    def hookextractall(self, dst, exclude):
        for tarinfo in self:
            if exclude and exclude(tarinfo):
                continue
            self.extract(tarinfo, dst)


class NativeZipFile(zipfile.ZipFile):
    """native zipfile"""

    @classmethod
    def native_open(cls, file):
        return cls(file)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def hookextractall(self, dst, exclude):
        for zipinfo in self.namelist():
            if exclude and exclude(zipinfo):
                continue
            self.extract(zipinfo, dst, None)


@six.add_metaclass(abc.ABCMeta)
class Adapter(object):

    def __init__(self, src):
        self.src = src

    @abc.abstractmethod
    def extractall(self, dst, exclude=None):
        """"""

    @abc.abstractmethod
    def wait(self, timeout=None):
        """wait extract"""

    @abc.abstractmethod
    def stop(self):
        """stop extract"""

class ShellAdapter(Adapter):

    def __init__(self, src, comptype):
        super(ShellAdapter, self).__init__(src)
        self.comptype = comptype
        self.sub = None

    @staticmethod
    def command_build_untar(src, dst, exclude):
        if TAR:
            ARGS = [TAR, ]
            if exclude:
                for exclude in exclude():
                    ARGS.append('--exclude=%s' % exclude)
            ARGS.extend(['-xf', src, '-C', dst])
            return TAR, ARGS
        raise NotImplementedError('can not find tar')
        # return BinAdapter.command_build_un7za(src, dst)

    @staticmethod
    def command_build_unzip(src, dst, exclude):
        if UNZIP:
            ARGS = [UNZIP, ]
            if exclude:
                for exclude in exclude():
                    ARGS.extend(['-x' % exclude])
            ARGS.extend(['-qq', '-o', src, '-d', dst])
            return UNZIP, ARGS
        return NotImplementedError('can not unzip')

    @staticmethod
    def build_command(comptype, src, dst, exclude):
        if comptype == 'tar':
            return ShellAdapter.command_build_untar(src, dst, exclude)
        elif comptype == 'zip':
            return ShellAdapter.command_build_unzip(src, dst, exclude)
        else:
            raise TypeError('Can not extract for %s' % comptype)

    def extractall(self, dst, exclude=None):
        executable, args = ShellAdapter.build_command(self.comptype, self.src, dst, exclude)
        self.sub = subprocess.Popen(args, executable=executable)

    def wait(self, timeout=None):
        if self.sub:
            systemutils.subwait(self.sub, timeout)
        else:
            raise RuntimeError('BinAdapter not started')

    def stop(self):
        if self.sub:
            self.sub.terminate()


class NativeAdapter(Adapter):

    def __init__(self, src, native_cls):
        super(NativeAdapter, self).__init__(src)
        self.native_cls = native_cls
        self.ft = None

    def extractall(self, dst, exclude=None):
        def _extractall():
            with self.native_cls.native_open(self.src) as ex:
                ex.hookextractall(dst, exclude)
        self.ft = futurist.Future(_extractall)
        self.ft.start()

    def wait(self, timeout=None):
        self.ft.result(timeout=timeout)

    def stop(self):
        if self.ft:
            self.ft.cancel()


class Extract(object):

    MAP = {'gz': NativeTarFile,
           'tar': NativeTarFile,
           'bz2': NativeTarFile,
           'zip': NativeZipFile}

    def __init__(self, src, native=False):
        compretype = Extract.find_compretype(src)
        if native:
            self.adapter = NativeAdapter(src, Extract.MAP[compretype])
        else:
            self.adapter = ShellAdapter(src, compretype)

    @staticmethod
    def find_compretype(src):
        with open(src, 'rb') as f:
            try:
                tarfile.TarFile.open(fileobj=f)
                return 'tar'
            except (tarfile.CompressionError, tarfile.ReadError):
                try:
                    zipfile.ZipFile(file=f)
                    return 'zip'
                except zipfile.BadZipfile:
                    raise TypeError('Source file is can not be extract')

    def extractall(self, dst, exclude, timeout=None, fork=None):
        if fork:
            if not systemutils.POSIX:
                raise TypeError('Can not fork on windows system when extractall')
            from simpleutil.utils.systemutils import posix
            pid = fork()
            if pid == 0:
                os.closerange(3, systemutils.MAXFD)
                self.adapter.extractall(dst)
                self.adapter.wait(timeout)
                os._exit(0)
            else:
                def wait():
                    posix.wait(pid, timeout)

                def stop():
                    try:
                        os.kill(pid, signal.SIGTERM)
                    except OSError:
                        pass

                return Waiter(wait=wait, stop=stop)
        else:
            self.adapter.extractall(dst, exclude)

            def wait():
                self.adapter.wait(timeout)

            return Waiter(wait=wait, stop=self.adapter.stop)