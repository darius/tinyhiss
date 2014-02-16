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
        raw_add_method(class_name, method_decl, terp.global_env)
    elif text.startswith('> '): # Command
        run(text[2:], terp.global_env)
    else:
        raise Exception("Unknown chunk type", text)


def make_class_method(_, (name, slots), k):
    result = raw_make_class_method(_, (name, slots), k)
    add_change('>', 'Make-class raw-named: %r with-slots: %r' % (name, slots))
    return result

def raw_make_class_method(_, (name, slots), k):
    slot_tuple = tuple(slots.split()) # since we don't have Smalltalk arrays yet
    env = terp.global_env
    old = env.get(name)
    old_methods = getattr(old, 'methods', {})
    if not isinstance(old, terp.Class) or old.slots != slot_tuple:
        env[name] = terp.Class(old_methods, slot_tuple)
        # XXX for now we're leaving old instances alone, and they share
        #  the method table. But their Thing data field ought to get updated
        #  consistent with the change to slots (as far as possible). 
    return k, name

make_class_class = terp.Class({'named:with-slots:': make_class_method,
                               'raw-named:with-slots:': raw_make_class_method},
                              ())
make_class = terp.Thing(make_class_class, ())

terp.global_env['Make-class'] = make_class


# Smoke test

fact = """\
factorial: n

0 = n
    if-so: {1}
    if-not: {n * (I factorial: n - 1)}
"""
## raw_add_method('Factorial', fact, terp.global_env)
## run("Factorial new factorial: 5", terp.global_env)
#. 120

fact2 = """\
factorial

I = 0
    if-so: {1}
    if-not: {me * (me - 1) factorial}
"""
## raw_add_method('Number', fact2, terp.global_env)
## run("5 factorial", terp.global_env)
#. 120

## run("3 + 4 * 5", terp.global_env)
#. 35

## run("Make-class named: 'A' with-slots: 'a'", terp.global_env)
#. 'A'
