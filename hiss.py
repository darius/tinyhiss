"""
Tie together the parser and interpreter.
"""

import fileout, parser, terp

changes = open('changes.hiss', 'a')

def add_method(class_name, text, classes):
    raw_add_method(class_name, text, classes)
    add_change('+', class_name + ' ' + text)

def add_change(chunk_type, text):
    changes.write(fileout.unparse1(chunk_type + ' ' + text) + '\n')
    changes.flush()

def raw_add_method(class_name, text, classes):
    (selector, method), = parser.grammar.top_method(text)
    method = terp.Method(text, method.code)
    ensure_class(class_name, classes).put_method(selector, method)

def ensure_class(name, classes):
    if name not in classes:
        classes[name] = terp.Class({}, ())
    return classes[name]

def run(text, env):
    block = parse_block(text, env)
    return terp.trampoline(block.enter((), terp.final_k))

def parse_block(text, env):
    return terp.Block(text, env, parser.parse_code(text))

def startup():
    for chunk in fileout.parse(open('changes.hiss').read().splitlines()):
        load_chunk(chunk)

def load_chunk(text):
    if text.startswith('+ '): # Method definition
        _, class_name, method_decl = text.split(None, 2)
        try:
            raw_add_method(class_name, method_decl, terp.global_env)
        except parson.Unparsable:
            sys.stderr.write("Failed to load chunk %r\n" % text.splitlines()[1])
    elif text.startswith('> '): # Command
        try:
            code = parse_block(text[2:], terp.global_env)
        except parson.Unparsable, exc:
            sys.stderr.write("Failed to run chunk %r\n" % text)
    else:
        raise Exception("Unknown chunk type", text)


# Smoke test

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
