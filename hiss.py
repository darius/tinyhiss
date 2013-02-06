"""
Tie together the parser and interpreter.
"""

import fileout, parser, terp

changes = open('changes.hiss', 'a')

def add_method(class_name, text, classes):
    (selector, method), = parser.grammar.top_method(text)
    ensure_class(class_name, classes).put_method(selector, method)
    changes.write(fileout.unparse1(class_name + ' ' + text) + '\n')

def ensure_class(name, classes):
    if name not in classes:
        classes[name] = terp.Class({}, ())
    return classes[name]

def run(text, classes):
    block = parser.parse_code(text, classes)
    return terp.trampoline((None, (), terp.final_k), block)

fact = """\
factorial: n

0 = n
    ifTrue: [1]
    ifFalse: [n * (self factorial: n-1)]
"""
## add_method('Factorial', fact, terp.global_env)
## run("Factorial new factorial: 5", terp.global_env)
#. 120

fact2 = """\
factorial

0 = self
    ifTrue: [1]
    ifFalse: [self * (self-1) factorial]
"""
## add_method('Number', fact2, terp.global_env)
## run("5 factorial", terp.global_env)
#. 120

## run("3 + 4 * 5", terp.global_env)
#. 35
