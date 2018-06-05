import os
import time
import eventlet
import shutil
eventlet.monkey_patch(all=True)
from eventlet import hubs

hub = hubs.get_hub()

from simpleutil.utils.zlibutils import compress
from simpleutil.utils.zlibutils import recvobj
from simpleutil.utils import zlibutils


def cachefile_recver(src, dst):
    comptype = os.path.splitext(dst)[1][1:]
    # recver = recvobj.FileCachedRecver(dst, cache_size=60000)
    s = time.time()
    compr = compress.ZlibStream(src, compretype=comptype)
    compr.compr2file(dst)
    print time.time() - s, 'comper %s success' % comptype


def cancel_recver(src, dst):
    comptype = os.path.splitext(dst)[1][1:]
    s = time.time()
    compr = compress.ZlibStream(src, compretype=comptype)
    eventlet.spawn_after(1, compr.cancel)
    # eventlet.sleep(0.3)
    print 'cancel spawned'
    compr.compr2file(dst)
    print 'finish, waiting'
    print time.time() - s, 'comper %s success' % comptype


def extract(src, dst):
    comptype = os.path.splitext(src)[1][1:]
    zlibutils.async_extract(src, dst, native=True)
    zlibutils.async_extract(src, dst, native=False)
    print 'native extract %s success' % comptype


def clean(path):
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)


def main():
    empty_dir = r'C:\Users\loliz_000\Desktop\empty'
    source_dir = r'C:\Users\loliz_000\Desktop\etc'
    gz_file = r'C:\Users\loliz_000\Desktop\1.tar.gz'
    zip_file = r'C:\Users\loliz_000\Desktop\1.zip'
    cachefile_recver(source_dir, gz_file)
    cachefile_recver(source_dir, zip_file)

    clean(empty_dir)
    w1 = zlibutils.async_extract(gz_file, empty_dir, native=True)
    clean(empty_dir)
    w2 = zlibutils.async_extract(gz_file, empty_dir, native=False)
    clean(empty_dir)
    w3 = zlibutils.async_extract(zip_file, empty_dir, native=True)
    clean(empty_dir)
    w4 = zlibutils.async_extract(zip_file, empty_dir, native=False)
    # clean(empty_dir)

    w1.wait()
    w2.wait()
    w3.wait()
    w4.wait()

if __name__ == '__main__':
    main()