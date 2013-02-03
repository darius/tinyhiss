"""
Hacked up from https://github.com/darius/sketchbook/tree/master/editor
"""

import os, sys
import ansi

filename = sys.argv[1]
cols, rows = 80, 24             # XXX query window size somehow

try:            f = open(filename)
except IOError: text = ''
else:           text = f.read(); f.close()

def C(ch): return chr(ord(ch.upper()) - 64)

seen = []

point, origin = 0, 0

def redisplay(new_origin, write):
    write(ansi.hide_cursor + ansi.home)
    p, x, y = new_origin, 0, 0
    found_point = False
    while y < rows:
        if p == point:
            write(ansi.save_cursor_pos)
            found_point = True
        if p == len(text):
            write(ansi.clear_to_bottom)
            break
        ch = text[p]
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
    global point
    point = max(0, min(point + d, len(text)))

column = None

def move_line(d):
    global point, column
    p = start_of_line(point)
    if column is None:
        column = point - p
    if d < 0:
        for _ in range(d, 0):
            p = start_of_line(p - 1) # XXX ok?
    else:
        for _ in range(d):
            nl = text.find('\n', p) + 1
            if nl == 0: break
            p = nl
    eol = text.find('\n', p)
    point = min(p + column, (eol if eol != -1 else len(text)))

def start_of_line(p):
    return text.rfind('\n', 0, p) + 1

def end_of_line(p):
    eol = text.find('\n', p)
    return eol if eol != -1 else len(text)

def insert(s):
    global text, point
    text = text[:point] + s + text[point:]
    point += len(s)

keybindings = {}

def set_key(ch, fn):
    keybindings[ch] = fn
    return fn

def bind(ch): return lambda fn: set_key(ch, fn)

@bind(chr(127))
def backward_delete_char():
    global text, point
    if 0 == point: return
    text = text[:point-1] + text[point:]
    point -= 1

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
    bol, eol = start_of_line(point), end_of_line(point)
    line = text[bol:eol]
    try:
        result = parser.run(line, terp.global_env)
    except Exception, e:
        result = e
    old_result = text.find(' "=> ', bol, eol)
    if old_result == -1: old_result = eol
    # XXX acting on hacky error-prone matching
    replace(old_result, eol, ' "=> %r"' % result)

def replace(start, end, string):
    global text, point
    text = text[:start] + string + text[end:]
    if start <= point < end:
        point = min(point, start + len(string))
    elif end <= point:
        point = start + len(string) + (point - end)

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
    global column, origin
    os.system('stty raw -echo')
    try:

        sys.stdout.write(ansi.clear_screen)
        while True:

            if not redisplay(origin, lambda s: None):
                for origin in range(max(0, point - cols * rows), point+1):
                    if redisplay(origin, lambda s: None):
                        break
            redisplay(origin, sys.stdout.write)

            ch = read_key()
            if ch in ('', C('x'), C('q')):
                break
            if ch in keybindings:
                keybindings[ch]()
            else:
                insert('\n' if ch == '\r' else ch)

            if ch not in ('up', 'down'):
                column = None

        if ch != C('q'):
            open(filename, 'w').write(text)

    finally:
        os.system('stty sane')

if __name__ == '__main__':
    main()
