# -*- coding: UTF-8 -*-
"""异步压缩解压方法"""
import os
from simpleutil.utils.zlibutils.extract import Extract
from simpleutil.utils.zlibutils.compress import ZlibStream

from simpleutil.utils.futurist import GreenThreadPoolExecutor


class Waiter(object):
    """等待压缩/解压完成"""
    def __init__(self, ft, cancel):
        self.ft = ft
        self.cancel = cancel

    def wait(self):
        self.ft.result()

    def stop(self):
        self.cancel()

    @property
    def finished(self):
        return self.ft.finished


def async_extract(src, dst,
                  exclude=None, timeout=None,
                  native=False, fork=None, prefunc=None):
    """
    @param src:             解压源文件
    @param dst:             解压目标文件夹
    @param exclude:         解压排除文件,callable
    @param timeout:         超时时间
    @param native:          是否使用python原生代码解压,速度慢,但是排除支持较好
    @param fork:            封装好的fork函数,可在fork中进行切换用户修改umask等操作,在linux上推举传入
                            如果使用原生解压且fork为None, 解压将使用大量cpu时间(单核)
                            原生方法不使用fork的情况下,解压大文件时间只能在解压完一个文件后才退出(timeout控制)
    @return None:           当前方法无返回值
    @raise TypeError:       源文件无法被当前方法解压
    """
    if not os.path.isdir(dst):
        raise RuntimeError('Destination is not folder')
    extracter = Extract(src, native, fork, prefunc)
    executor = GreenThreadPoolExecutor(max_workers=1)
    return Waiter(ft=executor.submit(extracter.extractall, dst, exclude, timeout),
                  cancel=extracter.cancel)

def async_compress(src, dst, topdir=True,
                   exclude=None, timeout=None,
                   native=True, fork=None, prefunc=None):
    """
    压缩至文件,需要传输到流中需要使用其他recv
    @param src:             压缩源文件/文件夹
    @param dst:             压缩输出文件
    @param exclude:         压缩排除文件,callable
    @param native:          是否使用python原生代码压缩,速度慢,但是排除支持较好
    @param timeout:         超时时间
    @param fork:            封装好的fork函数,在linux上推举传入
    @return None:           当前方法无返回值
    @raise TypeError:       压缩方式不支持
    """
    timeout = float(timeout) if timeout else None
    compretype = os.path.splitext(dst)[1][1:]
    comptyper = ZlibStream(src, compretype, native, fork, prefunc)
    executor = GreenThreadPoolExecutor(max_workers=1)
    return Waiter(ft=executor.submit(comptyper.compr2file, dst, topdir, exclude, timeout),
                  cancel=comptyper.cancel)
