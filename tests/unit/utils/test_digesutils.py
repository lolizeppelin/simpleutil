
from simpleutil.utils import digestutils


src = r'C:\Users\loliz_000\Desktop\backup\wtf.tar.gz'

print digestutils.filecrc32(src)
print digestutils.filemd5(src)