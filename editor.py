"""
Hacked up from https://github.com/darius/sketchbook/tree/master/editor
"""

import os, sys, traceback
import ansi
import hiss, parser, parson, terp

class Buffer(object):

    def __init__(self, filename, extent, top_left):
        self.filename = filename
        self.extent = extent
        self.top_left = top_left
        self.point = 0
        self.origin = 0
        self.column = None
        self.text = load(filename) if filename is not None else ''

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

    def replace(self, start, end, string):
        self.text = self.text[:start] + string + self.text[end:]
        if start <= self.point < end:
            self.point = min(self.point, start + len(string))
        elif end <= self.point:
            self.point = start + len(string) + (self.point - end)

    def redisplay(self):
        (cols, rows) = self.extent
        if not try_redisplay(self, lambda s: None):
            for self.origin in range(max(0, self.point - cols * rows), self.point+1):
                if try_redisplay(self, lambda s: None):
                    break
        try_redisplay(self, sys.stdout.write)

def load(filename):
    try:            f = open(filename)
    except IOError: result = ''
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

@bind('down')
def forward_move_line(buf): buf.move_line(1)

@bind('up')
def backward_move_line(buf): buf.move_line(-1)

@bind(C('j'))
def smalltalk_print_it(buf):
    bol, eol = buf.start_of_line(buf.point), buf.end_of_line(buf.point)
    line = buf.text[bol:eol]
    # XXX hacky error-prone matching; move this to parser module
    old_result = buf.text.find(' --> ', bol, eol)
    if old_result == -1: old_result = buf.text.find(' --| ', bol, eol)
    if old_result == -1: old_result = eol
    try:
        comment = '-->'
        result = repr(hiss.run(line, terp.global_env))
    except:
        comment = '--|'
        if False:               # Set to True for tracebacks
            result = traceback.format_exc()
        else:
            result = format_exception(sys.exc_info())
    buf.replace(old_result, eol,
                ' %s %s' % (comment, result.replace('\n', ' / ')))

def format_exception((etype, value, tb), limit=None):
    lines = traceback.format_exception_only(etype, value)
    return '\n'.join(lines).rstrip('\n')

@bind(M('a'))
def smalltalk_accept(buf):
    try:
        class_name, method_decl = buf.text.split(None, 1)
        hiss.add_method(class_name, method_decl, terp.global_env)
    except parson.Unparsable, exc:
        buf.point = len(buf.text) - len(method_decl) + exc.position
        buf.insert('<<Unparsable>>')

@bind('pgdn')
def next_method(buf): visit_methods(buf)
@bind('pgup')
def next_method(buf): visit_methods(buf, reverse=True)

def visit_methods(buf, reverse=False):
    class_name, method_decl = buf.text.split(None, 1)
    try:
        class_ = terp.global_env[class_name]
    except KeyError:
        return
    try:
        (selector, _), = parser.grammar.method_header(method_decl)
    except parson.Unparsable:
        selector = None
    selector, method = class_.next_method(selector, reverse)
    if selector:
        buf.text = class_name + ' ' + get_source(selector, method)
        buf.point = 0           # XXX move to start of body, I guess

def get_source(selector, method):
    # XXX oh wow, ugly.
    if hasattr(method, 'source'):
        if method.source: return method.source
    if ':' in selector:
        head = ' '.join('%s: foo' % part
                        for part in selector.split(':') if part)
    elif selector[:1].isalnum():
        head = selector
    else:
        head = selector + ' foo'
    return head + '\n\n  <<primitive>>'

@bind('end')                    # XXX a silly key for it
def next_buffer(buf):
    global current_buffer
    i = all_buffers.index(buf)
    current_buffer = all_buffers[(i+1) % len(all_buffers)]

keys = {esc+'[1~': 'home',  esc+'[A': 'up',    esc+'OA': 'up',
        esc+'[3~': 'del',   esc+'[B': 'down',  esc+'OB': 'down',
        esc+'[4~': 'end',   esc+'[C': 'right', esc+'OC': 'right',
        esc+'[5~': 'pgup',  esc+'[D': 'left',  esc+'OD': 'left',
        esc+'[6~': 'pgdn'}
key_prefixes = set(k[:i] for k in keys for i in range(1, len(k)))

def read_key():
    k = sys.stdin.read(1)
    while k in key_prefixes:
        k1 = sys.stdin.read(1)
        if not k1: break
        k += k1
    return keys.get(k, k)

def main():
    hiss.startup()
    os.system('stty raw -echo')
    try:
        sys.stdout.write(ansi.clear_screen)
        reacting()
    finally:
        os.system('stty sane')

def reacting():
    for buf in all_buffers:
        buf.redisplay()
    while True:
        current_buffer.redisplay()
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
    ROWS, COLS = map(int, os.popen('stty size', 'r').read().split())
    all_buffers = [Buffer(sys.argv[i+1] if i+1 < len(sys.argv) else None,
                          (COLS//2-1, ROWS),
                          (i*(COLS//2+1), 0))
                   for i in range(2)]
    current_buffer = all_buffers[0]
    main()
