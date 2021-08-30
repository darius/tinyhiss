"""
Tinyhiss main program.
Augment the text-editing UI with means to edit and run code.
"""

import os, sys, traceback
import ansi

import core, hiss, parser, parson, terp
from editor import UI, Buffer, C, M, bind

def main(ui):
    hiss.start_up()
    os.system('stty raw -echo')
    try:
        sys.stdout.write(ansi.clear_screen) # TODO move this stuff to editor module
        ui.reacting()
    finally:
        os.system('stty sane')

workspace_env = terp.Env({}, terp.global_env)

def workspace_run(text):
    code = parser.parse_code(text)
    if isinstance(code.expr, terp.Constant) and code.expr.value is None:
        # Special case to add variables to the workspace. I know, yuck.
        for var in code.locals:
            workspace_env.enter(var, None)
    block = terp.Block(text, workspace_env, code) # XXX redundant with hiss.run()
    return core.trampoline(block.enter((), terp.final_k))

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
        result = repr(workspace_run(line))
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
    class_name, method_decl = split2(buf.text)
    try:
        hiss.add_method(class_name, method_decl, terp.global_env)
    except parson.Unparsable, exc:
        buf.point = len(buf.text) - len(method_decl) + exc.position
        buf.insert('<<Unparsable>>')

@bind('pgdn')
def next_method(buf): visit_methods(buf)
@bind('pgup')
def next_method(buf): visit_methods(buf, reverse=True)

def visit_methods(buf, reverse=False):
    class_name, method_decl = split2(buf.text)
    try:
        class_ = terp.global_env.get(class_name)
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

def split2(text):
    splits = text.split(None, 1)
    return splits + [''] if len(splits) == 1 else splits

def get_source(selector, method):
    # Ugly logic because the 'method' may be primitive (just a Python
    # function, with no Smalltalk source).
    if hasattr(method, 'source'):
        if method.source: return method.source
    return head_from_selector(selector) + '\n\n  <<primitive>>'

def head_from_selector(selector):
    if ':' in selector:
        return ' '.join('%s: foo' % part
                        for part in selector.split(':') if part)
    elif selector[:1].isalnum():
        return selector
    else:
        return selector + ' foo'

@bind('end')                    # XXX a silly key for it
def next_buffer(buf):
    ui = buf.ui
    ui.current_buffer = (ui.current_buffer+1) % len(ui.buffers)


if __name__ == '__main__':
    ROWS, COLS = map(int, os.popen('stty size', 'r').read().split())
    the_buffers = []
    the_ui = UI(the_buffers)
    for i in range(2):
        the_buffers.append(Buffer(the_ui,
                                  sys.argv[i+1] if i+1 < len(sys.argv) else None,
                                  (COLS//2-1, ROWS),
                                  (i*(COLS//2+1), 0)))
    main(the_ui)
