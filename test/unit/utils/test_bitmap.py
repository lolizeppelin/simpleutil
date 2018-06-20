from simpleutil.utils.bitmap import BitMap

bt = BitMap(3000)

bt.add(59)
bt.add(51)
bt.add(11)
bt.add(13)
bt.add(13)
bt.add(17)
bt.add(19)
bt.add(59)
bt.add(6)
bt.add(72)

print bt.get(59)
print bt.get(51)
print bt.get(6)
print bt.get(8)

a = [x for x in bt.all()]
b = [x for x in bt.all(reverse=True)]

print a
print b
