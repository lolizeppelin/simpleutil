import os
import abc
import six
import signal
import tarfile
import zipfile
import subprocess
import time

from simpleutil.utils import systemutils

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

    def hookextractall(self, dst, exclude, overtime):
        for tarinfo in self:
            if int(time.time()) > overtime:
                break
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

    def hookextractall(self, dst, exclude, overtime):
        for zipinfo in self.namelist():
            if int(time.time()) > overtime:
                break
            if exclude and exclude(zipinfo):
                continue
            self.extract(zipinfo, dst, None)


@six.add_metaclass(abc.ABCMeta)
class Adapter(object):

    def __init__(self, src):
        self.src = src

    @abc.abstractmethod
    def extractall(self, dst, exclude=None, timeout=None):
        """execute extractall"""

    @abc.abstractmethod
    def cancel(self):
        """cancel extractall"""


class ShellAdapter(Adapter):
    def __init__(self, src, comptype, prefunc):
        super(ShellAdapter, self).__init__(src)
        self.comptype = comptype
        self.prefunc = prefunc
        self.sub = None

    @staticmethod
    def command_build_untar(src, dst, exclude):
        if TAR:
            ARGS = [TAR, ]
            if exclude:
                for _exclude in exclude():
                    ARGS.append('--exclude=%s' % _exclude)
            ARGS.extend(['-xf', src, '-C', dst])
            return TAR, ARGS
        raise NotImplementedError('can not find tar')

    @staticmethod
    def command_build_unzip(src, dst, exclude):
        if UNZIP:
            ARGS = [UNZIP, src]
            if exclude:
                ARGS.append('-x')
                for _exclude in exclude():
                    ARGS.append(_exclude)
            ARGS.extend(['-qq', '-o', '-d', dst])
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

    def extractall(self, dst, exclude=None, timeout=None):
        exclude = exclude(compretype=self.comptype, shell=True) if exclude else None
        executable, args = ShellAdapter.build_command(self.comptype, self.src, dst, exclude)
        self.sub = subprocess.Popen(args, executable=executable,
                                    close_fds=True, preexec_fn=self.prefunc)
        systemutils.subwait(self.sub, timeout)
        self.sub = None

    def cancel(self):
        if self.sub:
            self.sub.kill()


class NativeAdapter(Adapter):
    MAP = {'gz': NativeTarFile,
           'tar': NativeTarFile,
           'bz2': NativeTarFile,
           'zip': NativeZipFile}

    def __init__(self, src, compretype, fork=None):
        super(NativeAdapter, self).__init__(src)
        self.compretype = compretype
        self.native_cls = NativeAdapter[compretype]
        self.fork = fork
        self.pid = None
        self.overtime = int(time.time())

    def extractall(self, dst, exclude=None, timeout=None):
        exclude = exclude(compretype=self.compretype, shell=False) if exclude else None
        if not timeout:
            self.overtime = self.overtime + 3600
        else:
            self.overtime = self.overtime + timeout
        with self.native_cls.native_open(self.src) as ex:
            if self.fork:
                self.pid = pid = self.fork()
                if pid == 0:
                    os.closerange(3, systemutils.MAXFD)
                    ex.hookextractall(dst, exclude, self.overtime)
                    os._exit(0)
                else:
                    from simpleutil.utils.systemutils import posix
                    posix.wait(pid, timeout)
                    self.pid = None
            else:
                ex.hookextractall(dst, exclude, self.overtime)

    def cancel(self):
        self.overtime = 0
        if self.pid:
            os.kill(self.pid, signal.SIGKILL)


class Extract(object):

    def __init__(self, src, native=False, fork=None, prefunc=None):
        if fork and not systemutils.POSIX:
            raise TypeError('Can not fork on windows system')
        compretype = Extract.find_compretype(src)
        self.native = native
        if native:
            self.adapter = NativeAdapter(src, compretype, fork)
        else:
            self.adapter = ShellAdapter(src, compretype, prefunc)

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

    def extractall(self, dst, exclude, timeout=None):
        self.adapter.extractall(dst, exclude, timeout)

    def cancel(self):
        self.adapter.cancel()
