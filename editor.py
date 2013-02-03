"""
Hacked up from https://github.com/darius/sketchbook/tree/master/editor
"""

import os, sys
import ansi

filename = sys.argv[1]
cols, rows = 80, 24             # XXX query window size somehow
pane_left, pane_top = 2, 1
pane_right, pane_bottom = pane_left + cols, pane_top + rows

class Buffer(object):

    def __init__(self):
        self.point = 0
        self.origin = 0
        self.column = None
        self.text = ''

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

thebuf = Buffer()
thebuf.text = load(filename)

def C(ch): return chr(ord(ch.upper()) - 64)

def redisplay(buf, new_origin, write):
    p, x, y = new_origin, pane_left, pane_top
    write(ansi.hide_cursor + ansi.goto(x, y))
    found_point = False
    while y < pane_bottom:
        if p == buf.point:
            write(ansi.save_cursor_pos)
            found_point = True
        ch = buf.text[p] if p < len(buf.text) else '\n'
        p += 1
        for glyph in (' ' * (pane_right - x) if ch == '\n'
                      else ' ' * (8 - (x - pane_left) % 8) if ch == '\t'
                      else ch if 32 <= ord(ch) < 126
                      else '\\%03o' % ord(ch)):
            write(glyph)
            x += 1
            if x == pane_right:
                x, y = pane_left, y+1
                if y == pane_bottom: break
                write(ansi.goto(x, y))
    if found_point:
        write(ansi.show_cursor + ansi.restore_cursor_pos)
    return found_point

keybindings = {}

def set_key(ch, fn):
    keybindings[ch] = fn
    return fn

def bind(ch): return lambda fn: set_key(ch, fn)

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
            return chr(27) + '[' + ch
        else:
            return chr(27) + ch
    return ch

def main():
    os.system('stty raw -echo')
    try:

        sys.stdout.write(ansi.clear_screen)
        while True:

            if not redisplay(thebuf, thebuf.origin, lambda s: None):
                for thebuf.origin in range(max(0, thebuf.point - cols * rows), thebuf.point+1):
                    if redisplay(thebuf, thebuf.origin, lambda s: None):
                        break
            redisplay(thebuf, thebuf.origin, sys.stdout.write)

            ch = read_key()
            if ch in ('', C('x'), C('q')):
                break
            if ch in keybindings:
                keybindings[ch](thebuf)
            else:
                thebuf.insert('\n' if ch == '\r' else ch)

            if ch not in ('up', 'down'):
                thebuf.column = None

        if ch != C('q'):
            open(filename, 'w').write(thebuf.text)

    finally:
        os.system('stty sane')

if __name__ == '__main__':
    main()
