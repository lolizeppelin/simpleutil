CLOSURES = {
    '"': '"',
    '[': ']',
    '{': '}',
    '<': '>',
    '(': ')',
}

def split_line(line, splits=None, closures=None):
    if splits is None:
        splits = [' ']
    if closures is None:
        closures = CLOSURES
    if len(line) > 4096:
        raise ValueError('Over size')
    if set(splits) & set(closures.keys()):
        raise ValueError('split string in closures')
    line = line.strip()
    cmark = None
    block = ''
    column = []
    splits = frozenset(splits)

    for s in line:
        if cmark:
            if s == closures[cmark]:
                cmark = None
                column.append(split_line(block, splits, closures={}))
                block = ''
            else:
                block += s
        else:
            if s in splits:
                if block:
                    column.append(block)
                    block = ''
            elif s in closures:
                if block:
                    column.append(block)
                    block = ''
                cmark = s
            else:
                block += s
    return column


def split_file(target, split=' ', closures=None):

    if not closures:
        closures = CLOSURES

    with open(target, 'r') as f:
        num = 0
        block = ""
        column = []
        cmark = None
        while True:
            buf = f.read(4096)
            if not buf:
                break
            for s in buf:
                if s == '\n':
                    if cmark:
                        raise RuntimeError('closure not end %d' % num)
                    column.append(block)
                    block = ''
                    yield column
                    column = []
                elif cmark:
                    if s == closures[cmark]:
                        cmark = None
                        column.append(block)
                        block = ''
                    else:
                        block += s
                else:
                    if s == split:
                        if block:
                            column.append(block)
                            block = ''
                    elif s in closures:
                        if block:
                            column.append(block)
                            block = ''
                        cmark = s
                    else:
                        block += s
        if column:
            column.append(block)
            yield column