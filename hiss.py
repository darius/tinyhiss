"""
Tie together the parser and interpreter.
"""

import fileout, parser, terp

changes = open('changes.hiss', 'a')

def add_method(class_name, text, classes):
    (selector, method), = parser.grammar.top_method(text)
    ensure_class(class_name, classes).put_method(selector, method)
    changes.write(fileout.unparse1(class_name + ' ' + text) + '\n')
    changes.flush()

def ensure_class(name, classes):
    if name not in classes:
        classes[name] = terp.Class({}, ())
    return classes[name]

def run(text, env):
    block = parse_block(text, env)
    return terp.trampoline(block(None, (), terp.final_k))

def parse_block(text, env):
    return terp.Block(None, env, parser.parse_code(text))

fact = """\
factorial: n

0 = n
    if-so: {1}
    if-not: {n * (I factorial: n - 1)}
"""
## add_method('Factorial', fact, terp.global_env)
## run("Factorial new factorial: 5", terp.global_env)
#. 120

fact2 = """\
factorial

I = 0
    if-so: {1}
    if-not: {me * (me - 1) factorial}
"""
## add_method('Number', fact2, terp.global_env)
## run("5 factorial", terp.global_env)
#. 120

## run("3 + 4 * 5", terp.global_env)
#. 35
