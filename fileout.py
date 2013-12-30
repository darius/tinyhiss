"""
One idea for a fileout format:
A sequence of chunks.
A chunk is terminated by a line with a lone '!'.
A leading '!' in a line in the contents is escaped as '!!'.
"""

import itertools

def unparse(chunks):
    return itertools.imap(unparse1, chunks)

def unparse1(chunk):
    return '\n'.join(map(escape, chunk.splitlines()) + ['!'])

def parse(lines):
    chunk = []
    for line in lines:
        if line == '!':
            yield '\n'.join(chunk)
            chunk = []
        else:
            chunk.append(unescape(line))
    if chunk:
        yield '\n'.join(chunk)

def escape(s):
    return '!'+s if s.startswith('!') else s

def unescape(s):
    if s.startswith('!!'): return s[1:] 
    elif s.startswith('!'): raise Exception("Unknown '!' escape", s)
    else: return s

## list(unparse(['hi', '!there']))
#. ['hi\n!', '!!there\n!']

## list(parse(''.splitlines()))
#. []
## list(parse('hi there'.splitlines()))
#. ['hi there']
## list(parse('hi there\n!'.splitlines()))
#. ['hi there']
## list(parse('a\n!\n!!howdy\nhow are you?\n!\nhi there\n!'.splitlines()))
#. ['a', '!howdy\nhow are you?', 'hi there']

## unescape('hi')
#. 'hi'
## unescape('!hi')
#. Traceback (most recent call last):
#.   File "fileout.py", line 32, in unescape
#.     elif s.startswith('!'): raise Exception("Unknown '!' escape", s)
#. Exception: ("Unknown '!' escape", '!hi')
## unescape('!!hi')
#. '!hi'
