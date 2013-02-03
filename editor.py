"""
Hacked up from https://github.com/darius/sketchbook/tree/master/editor
"""

import os, sys
import ansi

filename = sys.argv[1]
cols, rows = 80, 24             # XXX query window size somehow

class Buffer: pass
buf = Buffer()
buf.point, buf.origin = 0, 0
buf.column = None
try:            f = open(filename)
except IOError: buf.text = ''
else:           buf.text = f.read(); f.close()

def C(ch): return chr(ord(ch.upper()) - 64)

seen = []

def redisplay(new_origin, write):
    write(ansi.hide_cursor + ansi.home)
    p, x, y = new_origin, 0, 0
    found_point = False
    while y < rows:
        if p == buf.point:
            write(ansi.save_cursor_pos)
            found_point = True
        if p == len(buf.text):
            write(ansi.clear_to_bottom)
            break
        ch = buf.text[p]
        if ch == '\n':
            write(ansi.clear_to_eol + '\r\n')
            x, y = 0, y+1
        else:
            if ch == '\t':
                glyphs = ' ' * (8 - x % 8)
            elif 32 <= ord(ch) < 126:
                glyphs = ch
            else:
                glyphs = '\\%03o' % ord(ch)
            for glyph in glyphs:
                write(glyph)
                x += 1
                if x == cols: x, y = 0, y+1
        p += 1
    write(ansi.goto(0, 30))
    write(' '.join(map(str, seen)))
    if found_point:
        write(ansi.show_cursor + ansi.restore_cursor_pos)
    return found_point

def move_char(d):
    buf.point = max(0, min(buf.point + d, len(buf.text)))

def move_line(d):
    p = start_of_line(buf.point)
    if buf.column is None:
        buf.column = buf.point - p
    if d < 0:
        for _ in range(d, 0):
            p = start_of_line(p - 1) # XXX ok?
    else:
        for _ in range(d):
            nl = buf.text.find('\n', p) + 1
            if nl == 0: break
            p = nl
    eol = buf.text.find('\n', p)
    buf.point = min(p + buf.column, (eol if eol != -1 else len(buf.text)))

def start_of_line(p):
    return buf.text.rfind('\n', 0, p) + 1

def end_of_line(p):
    eol = buf.text.find('\n', p)
    return eol if eol != -1 else len(buf.text)

def insert(s):
    buf.text = buf.text[:buf.point] + s + buf.text[buf.point:]
    buf.point += len(s)

keybindings = {}

def set_key(ch, fn):
    keybindings[ch] = fn
    return fn

def bind(ch): return lambda fn: set_key(ch, fn)

@bind(chr(127))
def backward_delete_char():
    if 0 == buf.point: return
    buf.text = buf.text[:buf.point-1] + buf.text[buf.point:]
    buf.point -= 1

@bind(C('b'))
@bind('left')
def backward_move_char(): move_char(-1)

@bind(C('f'))
@bind('right')
def forward_move_char(): move_char(1)

@bind('down')
def forward_move_line(): move_line(1)

@bind('up')
def backward_move_line(): move_line(-1)

@bind(C('j'))
def smalltalk_print_it():
    import parser, terp
    bol, eol = start_of_line(buf.point), end_of_line(buf.point)
    line = buf.text[bol:eol]
    try:
        result = parser.run(line, terp.global_env)
    except Exception, e:
        result = e
    old_result = buf.text.find(' "=> ', bol, eol)
    if old_result == -1: old_result = eol
    # XXX acting on hacky error-prone matching
    replace(old_result, eol, ' "=> %r"' % result)

def replace(start, end, string):
    buf.text = buf.text[:start] + string + buf.text[end:]
    if start <= buf.point < end:
        buf.point = min(buf.point, start + len(string))
    elif end <= buf.point:
        buf.point = start + len(string) + (buf.point - end)

def really_read_key():
    ch = sys.stdin.read(1)
    del seen[:-3]
    seen.append(ord(ch))
    return ch

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

            if not redisplay(buf.origin, lambda s: None):
                for buf.origin in range(max(0, buf.point - cols * rows), buf.point+1):
                    if redisplay(buf.origin, lambda s: None):
                        break
            redisplay(buf.origin, sys.stdout.write)

            ch = read_key()
            if ch in ('', C('x'), C('q')):
                break
            if ch in keybindings:
                keybindings[ch]()
            else:
                insert('\n' if ch == '\r' else ch)

            if ch not in ('up', 'down'):
                buf.column = None

        if ch != C('q'):
            open(filename, 'w').write(buf.text)

    finally:
        os.system('stty sane')

if __name__ == '__main__':
    main()
