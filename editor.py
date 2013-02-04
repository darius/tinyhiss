"""
Hacked up from https://github.com/darius/sketchbook/tree/master/editor
"""

import os, sys
import ansi

class Buffer(object):

    def __init__(self, filename, extent, top_left):
        self.filename = filename
        self.extent = extent
        self.top_left = top_left
        self.point = 0
        self.origin = 0
        self.column = None
        self.text = load(filename)

    def save(self):
        open(self.filename, 'w').write(self.text)

    def move_char(self, d):
        self.point = max(0, min(self.point + d, len(self.text)))

    def move_line(self, d):
        p = self.start_of_line(self.point)
        if self.column is None:
            self.column = self.find_column(p, self.point)
        if d < 0:
            for _ in range(d, 0):
                if p == 0: break
                p = self.start_of_line(p - 1)
        else:
            for _ in range(d):
                nl = self.end_of_line(p)
                if nl == len(self.text): break
                p = nl + 1
        eol = self.text.find('\n', p)
        # XXX step forward until current column == column -- could be different
        self.point = min(p + self.column, (eol if eol != -1 else len(self.text)))

    def start_of_line(self, p):
        return self.text.rfind('\n', 0, p) + 1

    def end_of_line(self, p):
        eol = self.text.find('\n', p)
        return eol if eol != -1 else len(self.text)

    def find_column(self, bol, p):
        # XXX code duplication wrt redisplay()
        # XXX doesn't handle escaped chars
        # A simpler solution: require tab on input to expand into spaces
        # in the text, immediately. Um, but that doesn't do escapes either.
        column = 0
        for c in self.text[bol:p]:
            if c == '\t':
                column = (column + 7) // 8 * 8
            else:
                column += 1
        return column

    def insert(self, s):
        self.text = self.text[:self.point] + s + self.text[self.point:]
        self.point += len(s)

    def replace(buf, start, end, string):
        buf.text = buf.text[:start] + string + buf.text[end:]
        if start <= buf.point < end:
            buf.point = min(buf.point, start + len(string))
        elif end <= buf.point:
            buf.point = start + len(string) + (buf.point - end)

def load(filename):
    try:            f = open(filename)
    except IOError: result = ''
    else:           result = f.read(); f.close()
    return result

def redisplay(buf):
    (cols, rows) = buf.extent
    if not try_redisplay(buf, lambda s: None):
        for buf.origin in range(max(0, buf.point - cols * rows), buf.point+1):
            if try_redisplay(buf, lambda s: None):
                break
    try_redisplay(buf, sys.stdout.write)

def try_redisplay(buf, write):
    (left, top), (cols, rows) = buf.top_left, buf.extent
    right, bottom = left + cols, top + rows
    p, (x, y) = buf.origin, buf.top_left
    write(ansi.hide_cursor + ansi.goto(x, y))
    found_point = False
    while y < bottom:
        if p == buf.point:
            write(ansi.save_cursor_pos)
            found_point = True
        ch = buf.text[p] if p < len(buf.text) else '\n'
        p += 1
        for glyph in (' ' * (right - x) if ch == '\n'
                      else ' ' * (8 - (x - left) % 8) if ch == '\t'
                      else ch if 32 <= ord(ch) < 126
                      else '\\%03o' % ord(ch)):
            write(glyph)
            x += 1
            if x == right:
                x, y = left, y+1
                if y == bottom: break
                write(ansi.goto(x, y))
    if found_point:
        write(ansi.show_cursor + ansi.restore_cursor_pos)
    return found_point

def C(ch): return chr(ord(ch.upper()) - 64)

keybindings = {}

def set_key(ch, fn):
    keybindings[ch] = fn
    return fn

def bind(ch): return lambda fn: set_key(ch, fn)

set_key('\r', lambda buf: buf.insert('\n'))

@bind(chr(127))
def backward_delete_char(buf):
    if 0 == buf.point: return
    buf.text = buf.text[:buf.point-1] + buf.text[buf.point:]
    buf.point -= 1

@bind(C('b'))
@bind('left')
def backward_move_char(buf): buf.move_char(-1)

@bind(C('f'))
@bind('right')
def forward_move_char(buf): buf.move_char(1)

@bind('down')
def forward_move_line(buf): buf.move_line(1)

@bind('up')
def backward_move_line(buf): buf.move_line(-1)

@bind(C('j'))
def smalltalk_print_it(buf):
    import parser, terp
    bol, eol = buf.start_of_line(buf.point), buf.end_of_line(buf.point)
    line = buf.text[bol:eol]
    try:
        result = parser.run(line, terp.global_env)
    except Exception, e:
        result = e
    old_result = buf.text.find(' "=> ', bol, eol)
    if old_result == -1: old_result = eol
    # XXX acting on hacky error-prone matching
    buf.replace(old_result, eol, ' "=> %r"' % result)

@bind('pgdn')
def next_buffer(buf):
    global current_buffer
    i = all_buffers.index(buf)
    current_buffer = all_buffers[(i+1) % len(all_buffers)]

def really_read_key():
    return sys.stdin.read(1)

def read_key():
    ch = really_read_key()
    if ch == chr(27):
        ch = really_read_key()
        if ch == '[':
            ch = really_read_key()
            if ch == 'A': return 'up'
            if ch == 'B': return 'down'
            if ch == 'C': return 'right'
            if ch == 'D': return 'left'
            if ch in '13456':
                lastch = really_read_key()
                if lastch == '~':
                    return {'1': 'home',
                            '3': 'del',
                            '4': 'end',
                            '5': 'pgup',
                            '6': 'pgdn'}[ch]
                return chr(27) + '[' + ch + lastch
            return chr(27) + '[' + ch
        else:
            return chr(27) + ch
    return ch

def main():
    os.system('stty raw -echo')
    try:
        sys.stdout.write(ansi.clear_screen)
        reacting()
    finally:
        os.system('stty sane')

def reacting():
    for buf in all_buffers:
        redisplay(buf)
    while True:
        redisplay(current_buffer)
        ch = read_key()
        if ch in ('', C('x'), C('q')):
            break
        keybindings.get(ch, lambda buf: buf.insert(ch))(current_buffer)
        if ch not in ('up', 'down'):
            current_buffer.column = None
    if ch != C('q'):
        for buf in all_buffers:
            buf.save()

if __name__ == '__main__':
    # XXX other ways to find out the window size?
    COLS, ROWS = (int(os.environ.get('COLUMNS', 80)),
                  int(os.environ.get('LINES', 24)))
    all_buffers = [Buffer(sys.argv[1], (COLS//2-1, ROWS), (0, 0)),
                   Buffer(sys.argv[2], (COLS//2-1, ROWS), (COLS//2+1, 0))]
    current_buffer = all_buffers[0]
    main()
