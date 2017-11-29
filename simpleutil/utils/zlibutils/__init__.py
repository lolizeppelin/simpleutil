# -*- coding: UTF-8 -*-
"""异步压缩解压方法"""
import os
from simpleutil.utils import systemutils
from simpleutil.utils.zlibutils.extract import Extract
from simpleutil.utils.zlibutils.compress import FileRecver
from simpleutil.utils.zlibutils.compress import ZlibStream

def async_extract(src, dst, exclude=None,
                  native=False,
                  timeout=None, fork=None):
    """
    @param src:             解压源文件
    @param dst:             解压目标文件夹
    @param exclude:         解压排除文件,callable
    @param native:          是否使用python原生代码解压,速度慢,但是排除支持较好
    @param timeout:         超时时间
    @param fork:            封装好的fork函数,可在fork中进行切换用户修改umask等操作,在linux上推举传入
                            如果使用原生解压且fork为None, 解压将使用大量cpu时间(单核)
    @return None:           当前方法无返回值
    @raise TypeError:       源文件无法被当前方法解压
    """
    if not os.path.isdir(dst):
        raise RuntimeError('Destination is not folder')
    extracter = Extract(src, native)
    extracter.extractall(dst, exclude, timeout, fork)


def async_compress(src, dst, exclude=None,
                   native=True,
                   timeout=None, fork=None):
    """
    压缩至文件,需要传输到流中需要使用其他recv
    @param src:             压缩源文件/文件夹
    @param dst:             压缩输出文件
    @param exclude:         压缩排除文件,callable
    @param native:          是否使用python原生代码压缩,速度慢,但是排除支持较好
                            目前只支持native方式压缩
    @param timeout:         超时时间
    @param fork:            封装好的fork函数,在linux上推举传入
    @return None:           当前方法无返回值
    @raise TypeError:       压缩方式不支持
    """
    timeout = float(timeout) if timeout else None
    comptype = os.path.splitext(dst)[1][1:]
    worker = ZlibStream(src, comptype=comptype,
                        recv=FileRecver(dst))
    if fork:
        if not systemutils.POSIX:
            raise RuntimeError('Can not fork on windows system when async_compress')
        from simpleutil.utils.systemutils import posix
        pid = fork()
        if pid == 0:
            worker.compress(exclude)
            worker.wait(timeout)
            os._exit(0)
        else:
            posix.wait(pid)
    else:
        worker.compress(exclude)
        worker.wait(timeout)
