"""
Tie together the parser and interpreter.
"""

import fileout, parser, terp

saving_changes = False
changes = open('changes.hiss', 'a')

def start_up():
    global saving_changes
    saving_changes = False
    with open('changes.hiss') as f:
        changes = f.read()
    for chunk in fileout.parse(changes.splitlines()):
        load_chunk(chunk)
    saving_changes = True

def load_chunk(text):
    if text.startswith('+ '): # Method definition
        _, class_name, method_decl = text.split(None, 2)
        raw_add_method(class_name, method_decl, terp.global_env)
    elif text.startswith('> '): # Command
        run(text[2:], terp.global_env)
    else:
        raise Exception("Unknown chunk type", text)

def add_change(chunk_type, text):
    if saving_changes:
        changes.write(fileout.unparse1(chunk_type + ' ' + text) + '\n')
        changes.flush()

def add_method(class_name, text, classes):
    raw_add_method(class_name, text, classes)
    add_change('+', class_name + ' ' + text)

def raw_add_method(class_name, text, classes):
    (selector, method), = parser.grammar.top_method(text)
    method = terp.Method(text, method.code)
    ensure_class(class_name, classes).put_method(selector, method)

def ensure_class(name, classes):
    return classes.enter(name, terp.Class({}, ()))

def run(text, env):
    block = parse_block(text, env)
    return terp.trampoline(block.enter((), terp.final_k))

def parse_block(text, env):
    # XXX why is text the receiver? what was I thinking?
    return terp.Block(text, env, parser.parse_code(text))


def make_class_method(_, (name, slots), k):
    slot_tuple = tuple(slots.split()) # since we don't have Smalltalk arrays yet

    genv = terp.global_env
    old = ensure_class(name, genv)
    if old.slots != slot_tuple:
        old_methods = getattr(old, 'methods', {})
        genv.adjoin(name, terp.Class(old_methods, slot_tuple))
        # XXX for now we're leaving old instances alone, and they share
        #  the method table. But their Thing data field ought to get updated
        #  consistent with the change to slots (as far as possible). 
    add_change('>', 'Make-class named: %r with-slots: %r' % (name, slots))
    return k, name

make_class_class = terp.Class({'named:with-slots:': make_class_method}, ())
make_class = terp.Thing(make_class_class, ())

terp.global_env.adjoin('Make-class', make_class)


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

## run("Make-class named: 'A' with-slots: 'a'", terp.global_env)
#. 'A'
