"""
Hacked up from https://github.com/darius/sketchbook/tree/master/editor
"""

import re, sys

import ansi

class UI(object):
    "Top-level user-interface state."

    def __init__(self, buffers):
        self.buffers = buffers
        self.current_buffer = 0
        self.killed = ''

    @property
    def buf(self):
        return self.buffers[self.current_buffer]

    def reacting(self):
        for buf in self.buffers:
            buf.redisplay()
        while True:
            self.buf.redisplay()
            key = read_key()
            if key in ('', C('x'), C('q')):
                break
            last_buf = self.buf
            keybindings.get(key, lambda buf: buf.insert(key))(self.buf)
            last_buf.last_key = key
        if key != C('q'):
            for buf in self.buffers:
                buf.save()

class Buffer(object):
    "A pane of editable text on screen."

    # filename: source/destination of the text to edit, or None.
    # extent:   (cols, rows) size of the pane.
    # top_left: (x, y) coordinates of the top-left of the pane.
    def __init__(self, ui, filename, extent, top_left):
        self.ui = ui
        self.filename = filename
        self.extent = extent
        self.top_left = top_left
        self.text = load(filename) if filename is not None else ''
        self.point = 0
        self.origin = 0
        self.column = None
        self.last_key = ''      # TODO make this a UI field instead?

    def save(self):
        if self.filename is None:
            print 'Not saving\r'
        else:
            with open(self.filename, 'w') as f:
                f.write(self.text)

    def move_char(self, d):
        self.point = max(0, min(self.point + d, len(self.text)))

    def forward_word(self):     # XXX TODO forward/backward move/kill
        pat = re.compile(r'\W*\w+') # TODO hoist
        m = pat.match(self.text, self.point)
        self.point = m.end()

    def move_line(self, d):
        p = self.start_of_line(self.point)
        if self.last_key not in ('up', 'down'):
            self.column = None
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
        eol = self.end_of_line(p)
        # XXX step forward until current column == column -- could be different
        self.point = min(p + self.column, eol)

    def start_of_line(self, p):
        return self.text.rfind('\n', 0, p) + 1

    def end_of_line(self, p):
        eol = self.text.find('\n', p)
        return eol if eol != -1 else len(self.text)

    def go_start_of_line(self):
        self.point = self.start_of_line(self.point)

    def go_end_of_line(self):
        self.point = self.end_of_line(self.point)

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

    def replace(self, start, end, string):
        self.text = self.text[:start] + string + self.text[end:]
        if start <= self.point < end:
            self.point = min(self.point, start + len(string))
        elif end <= self.point:
            self.point = start + len(string) + (self.point - end)

    def kill_line(self):
        p = self.end_of_line(self.point)
        if self.point == p:                # If already at end of line,
            p = min(p + 1, len(self.text)) #   only then eat the \n character.
        self.kill(self.point, p)

    def kill(self, start, end):
        killing = self.text[start:end]
        self.replace(start, end, '')
        if self.last_key != C('k'):
            self.ui.killed = ''
        self.ui.killed += killing
        
    def yank(self):
        self.insert(self.ui.killed)

    def redisplay(self):
        (cols, rows) = self.extent
        if not try_redisplay(self, lambda s: None):
            for self.origin in range(max(0, self.point - cols * rows), self.point+1):
                if try_redisplay(self, lambda s: None):
                    break
        try_redisplay(self, sys.stdout.write)

def load(filename):
    try:            f = open(filename)
    except IOError: result = '' # XXX too-broad catch
    else:           result = f.read(); f.close()
    return result

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
                      else ch if 32 <= ord(ch) < 127
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

esc = chr(27)
def M(ch): return esc + ch
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

@bind(C('a'))
def start_of_line(buf): buf.go_start_of_line()

@bind(C('e'))
def end_of_line(buf): buf.go_end_of_line()

@bind('down')
def forward_move_line(buf): buf.move_line(1)

@bind('up')
def backward_move_line(buf): buf.move_line(-1)

@bind(M('<'))
def start_of_buffer(buf): buf.point = 0

@bind(M('>'))
def end_of_buffer(buf): buf.point = len(buf.text)

@bind(C('k'))
def kill_line(buf): buf.kill_line()

@bind(C('y'))
def yank(buf): buf.yank()

# @bind(M('right'))  XXX won't work
def forward_word(buf): buf.forward_word()

keys = {
    esc+'[1~': 'home',
    esc+'[3~': 'del',
    esc+'[4~': 'end',  esc+'[F': 'end',
    esc+'[5~': 'pgup',
    esc+'[6~': 'pgdn',
    esc+'[A': 'up',    esc+'OA': 'up',
    esc+'[B': 'down',  esc+'OB': 'down',
    esc+'[C': 'right', esc+'OC': 'right',
    esc+'[D': 'left',  esc+'OD': 'left',
}
key_prefixes = set(k[:i] for k in keys for i in range(1, len(k)))

def read_key():
    k = sys.stdin.read(1)
    while k in key_prefixes:
        k1 = sys.stdin.read(1)
        if not k1: break
        k += k1
    return keys.get(k, k)
