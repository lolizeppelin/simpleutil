# -*- coding: UTF-8 -*-
import os
import eventlet
from simpleutil.utils import importutils
from simpleutil.utils import futurist
from simpleutil.utils.zlibutils.compress import impl


class Recver(object):
    """
    压缩写入对象
    模拟file objet
    """
    def __init__(self, cache_size=0):
        # 缓存字符串长度
        # gz已经缓存过不需要再缓存
        # 当前位置
        self.pos = 0
        # 末尾位置
        self.end_pos = 0
        # 最后发送的结尾
        self.fire_pos = 0
        # write缓存字符
        self.cache_buffer = ""
        # 缓存buffer长度
        self.cache_size = cache_size
        # 偏移写入列表
        self.seek_write_list = []
        self.canceld = False

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.canceld:
            self.close()

    def cancel(self):
        self.canceld = True
        self.write = self.ioerror

    def ioerror(self, *args, **kwargs):
        raise IOError('Recver cancel')

    def fire(self, fire_list):
        """
        实际处理压缩后字符串的接口
        @param fire_list: 需要处理的位置+字符串组成的列表[(pos, buffer), (pos, buffer)]
        """
        raise NotImplementedError('function fire not exist')

    def cachewrite(self, buffer):
        # 偏移写入列表
        if len(self.seek_write_list) >= 30:
            self.fire(self.seek_write_list)
            del self.seek_write_list[:]
        self.cache_buffer += buffer
        self.pos += len(buffer)
        self.end_pos = self.pos
        # 发送所有缓存数据
        if len(self.cache_buffer) > self.cache_size:
            self.fire([(self.fire_pos, self.cache_buffer)])
            self.fire_pos += len(self.cache_buffer)
            self.cache_buffer = ""

    def seek_write(self, buffer):
        # 当前写入位置已经被发送过
        if self.pos < self.fire_pos:
            # 写入长度小于当前已经处理位置,直接添加到替换列表
            if self.pos + len(buffer) <= self.fire_pos:
                self.seek_write_list.append((self.pos, buffer))
                self.pos += len(buffer)
            else:
                # 切片
                cut_pos = self.fire_pos - self.pos
                self.seek_write_list.append((self.pos, buffer[:cut_pos]))
                # 剩余部分递归调用替换
                self.pos = self.fire_pos
                self.seek_write(buffer[cut_pos:])
        # 未发送过,还在缓存字符串里
        else:
            # 没有超出结束位置
            if self.pos + len(buffer) <= self.end_pos:
                self.cache_buffer = self.cache_buffer[:self.pos-self.fire_pos] \
                                    + buffer \
                                    + self.cache_buffer[self.pos+len(buffer)-self.fire_pos:]
                self.pos += len(buffer)
            # 总长度超出
            else:
                self.cache_buffer = self.cache_buffer[:self.pos-self.fire_pos] + buffer
                self.pos += len(buffer)
                self.end_pos = self.pos

    def close(self):
        if self.cache_buffer:
            self.fire([(self.fire_pos, self.cache_buffer)])
            self.fire_pos += len(self.cache_buffer)
            self.cache_buffer = ""
        if self.seek_write_list:
            self.fire(self.seek_write_list)
            del self.seek_write_list[:]

    def __call__(self, buffer):
        self.write(buffer)

    def write(self, buffer):
        if not buffer:
            return
        # 有偏移量
        if self.pos < self.end_pos:
            self.seek_write(buffer)
        else:
            # 当前位置没有变化
            self.cachewrite(buffer)

    def flush(self):
        pass

    def tell(self):
        return self.pos

    def seek(self, pos, whence):
        if not whence:
            seek_pos = pos
        elif whence == 1:
            seek_pos = self.pos + pos
        elif whence == 2:
            seek_pos = self.end_pos - pos
        else:
            raise ValueError('Whence value error')
        if seek_pos < 0:
            raise ValueError('Pos less then zero')
        if seek_pos > self.end_pos:
            raise IOError('Seek pos over end pos')
        self.pos = seek_pos

    def set_cache(self, cache_size):
        if self.cache_buffer or self.fire_pos or self.end_pos:
            raise RuntimeError('Recver is working')
        if not isinstance(cache_size, (int, long)):
            raise TypeError('Recver find cache size type error')
        self.cache_size = cache_size

    def set_parent(self, parent):
        self.parent = parent


class FileRecver(Recver):
    """
    直接写文件的Recver,无缓存
    """
    def __init__(self, targetfile):
        super(FileRecver, self).__init__()
        self.targetfile = targetfile
        self.obj = None

    def __enter__(self):
        self.obj = open(self.targetfile, 'wb')

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.obj.close()
        except (OSError, IOError):
            self.obj = None

    def write(self, buffer):
        if not buffer:
            return
        eventlet.sleep(0)
        self.obj.write(buffer)

    def seek(self, pos, whence):
        self.obj.seek(pos, whence)

    def flush(self):
        self.obj.flush()

    def fire(self, fire_list):
        pass

    def close(self):
        self.obj.close()

    def tell(self):
        return self.obj.tell()


class FileCachedRecver(Recver):

    def __init__(self, targetfile, cache_size=0):
        super(FileCachedRecver, self).__init__(cache_size)
        self.targetfile = targetfile
        self.obj = None

    def __enter__(self):
        self.obj = open(self.targetfile, 'wb')

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.close()
        except (OSError, IOError):
            self.obj = None

    def fire(self, fire_list):
        for data in fire_list:
            self.obj.seek(data[0])
            self.obj.write(data[1])

    def close(self):
        super(FileCachedRecver, self).close()
        self.obj.close()

    def flush(self):
        self.obj.flush()


class ZlibStream(object):

    def __init__(self, path, comptype, recv=None):
        """
        不支持设置压缩等级,需要继承后改动函数,不确定兼容性
        zip压缩使用压缩等级8
        gz压缩使用等级9
        """
        if not os.path.exists(path):
            raise ValueError('path not exists')
        self.path = path
        cls = importutils.import_class('simpleutil.utils.zlibutils.compress.impl.%sCompress' %
                                       comptype.capitalize())
        self.recvobj = recv
        if not isinstance(self.recvobj, Recver):
            raise TypeError('Recver type error')
        self.compper = cls(path)

    def compress(self, exclude=None):
        if exclude:
            if not callable(exclude):
                raise RuntimeError('exclude is not callable')
        def wapper():
            with self.recvobj:
                self.compper.compress(self.recvobj, exclude)
        self.ft = futurist.Future(wapper)
        self.ft.link()

    def wait(self, timeout=None):
        try:
            self.ft.result(timeout)
        except futurist.TimeoutError:
            self.ft.cancel()
        except futurist.CancelledError:
            pass

    def cancel(self):
        self.recvobj.cancel()
        self.compper.cancel()
