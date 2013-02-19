"""
Based on http://chronos-st.blogspot.com/2007/12/smalltalk-in-one-page.html
"""

from parson import Grammar, hug, join
import terp

grammar_text = r"""
top_code = _ code ~/./.
top_method = method_decl ~/./.

method_decl = method_header code :mk_method.
method_header = unary_selector :mk_unary_header
              | binary_selector name :mk_binary_header
              | (keyword name)+ :mk_keyword_header.

unary_selector = id ~':' _.
binary_selector = /([~!@%&*\-+=|\\<>,?\/]+)/_.
keyword = id /(:)/_ :join.

code = locals? :hug opt_stmts.
locals = '|'_ name* '|'_.
opt_stmts = stmts | :mk_nil.
stmts = stmt ('.'_ stmt :mk_then)* ('.'_)?.

stmt = 'my'__ name ':='_ expr :mk_slot_put
     |        name ':='_ expr :mk_local_put
     | '^'_ expr :mk_return
     | expr.

expr = operand (m1 :mk_send (';'_ m1 :mk_cascade)*)?.
m1 = unary_selector m1? :mk_m1 | m2.
e1 = operand (unary_selector :mk_e1)*.
m2 = binary_selector e1 m2? :mk_m2 | m3.
e2 = e1 (binary_selector e1 :mk_e2)*.
m3 = (keyword e2)+ :mk_m3.

operand = block
        | 'nil'   ~idchar _  :mk_nil
        | 'false' ~idchar _  :mk_false
        | 'true'  ~idchar _  :mk_true
        | 'I'     ~idchar _  :mk_self
        | 'me'    ~idchar _  :mk_self
        | 'my'__ name        :mk_slot_get
        | name               :mk_var_get
        | /-?(\d+)/_         :mk_int  # XXX add base-r literals, floats, and scaled decimals
        | string_literal     :mk_string
        | '('_ stmt ')'_.

reserved = /nil|false|true|I|me|my/ ~idchar.

block = '{'_ block_args? :hug code '}'_ :mk_block.
block_args = (':'_ name)* '|'_.

string_literal = /'/ qchar* /'/_  :join.
qchar = /'(')/ | /([^'])/.

name = ~reserved id _.  # XXX this ~reserved should look for just 'my', not 'my'__name

id = /([A-Za-z][_A-Za-z0-9-]*)/.   # XXX could restrict the dashes some more
idchar = /[_A-Za-z0-9-]/.

__ = whitespace+.
_ = whitespace*.
whitespace = (/\s/ | comment).
comment = /--[>|\s][^\n]*/.
"""

mk_unary_header   = lambda selector: (selector, ())
mk_binary_header  = lambda selector, param: (selector, (param,))
mk_keyword_header = lambda *args: (''.join(args[::2]), args[1::2])

def mk_method((selector, params), localvars, expr):
    return selector, terp.Method(params, localvars, expr)

mk_nil    = lambda: terp.Constant(None)
mk_false  = lambda: terp.Constant(False)
mk_true   = lambda: terp.Constant(True)
mk_self   = terp.Self
mk_super  = lambda: XXX
mk_int    = lambda s: terp.Constant(int(s))
mk_string = lambda s: terp.Constant(s)

mk_slot_get = terp.SlotGet
mk_slot_put = terp.SlotPut

def mk_var_get(name):
    return terp.GlobalGet(name) if name[:1].isupper() else terp.LocalGet(name)

def mk_local_put(name, expr):
    assert not name[:1].isupper()
    return terp.LocalPut(name, expr)

mk_block = terp.Code

mk_then = terp.Then

mk_return = lambda e: XXX
mk_array  = lambda *literals: XXX

def mk_cascade(operand, m1):
    send = m1(operand)
    # XXX I think the innermost Send still needs to be rewritten
    return terp.Cascade(send.subject, send.selector, send.operands)

def mk_send(operand, m1):
    return m1(operand)

def mk_m1(selector, m1=lambda e: e):
    return lambda operand: m1(mk_e1(operand, selector))

def mk_e1(operand, selector):
    return terp.Send(operand, selector, ())

def mk_m2(selector, e1, m2=lambda e: e):
    return lambda operand: m2(mk_e2(operand, selector, e1))

def mk_e2(operand, selector, arg):
    return terp.Send(operand, selector, (arg,))

def mk_m3(*args):
    selector = ''.join(args[::2])
    rands = args[1::2]
    return lambda operand: terp.Send(operand, selector, rands)

grammar = Grammar(grammar_text)(**globals())

def parse_code(text, classes):
    localvars, body = grammar.top_code(text)
    return terp.Block(None, None, terp.Code((), localvars, body))

## grammar.code('2 + 3 negate')
#. ((), _Send(subject=_Constant(value=2), selector='+', operands=(_Send(subject=_Constant(value=3), selector='negate', operands=()),)))

## grammar.code('a b; c; d')
#. ((), _Cascade(subject=_Cascade(subject=_Send(subject=_LocalGet(name='a'), selector='b', operands=()), selector='c', operands=()), selector='d', operands=()))

## grammar.top_code("2")
#. ((), _Constant(value=2))
## grammar.top_code("'hi'")
#. ((), _Constant(value='hi'))

## grammar.method_decl('+ n\nmyValue + n')
#. (('+', _Block(receiver=None, env=None, code=_Code(params=('n',), locals=(), expr=_Send(subject=_LocalGet(name='myValue'), selector='+', operands=(_LocalGet(name='n'),))))),)
## grammar.method_decl('hurray  -- comment\n {42} if: true else: {137}')
#. (('hurray', _Block(receiver=None, env=None, code=_Code(params=(), locals=(), expr=_Send(subject=_Code(params=(), locals=(), expr=_Constant(value=42)), selector='if:else:', operands=(_Constant(value=True), _Code(params=(), locals=(), expr=_Constant(value=137))))))),)
## grammar.method_decl("at: x put: y   myTable at: '$'+x put: y")
#. (('at:put:', _Block(receiver=None, env=None, code=_Code(params=('x', 'y'), locals=(), expr=_Send(subject=_LocalGet(name='myTable'), selector='at:put:', operands=(_Send(subject=_Constant(value='$'), selector='+', operands=(_LocalGet(name='x'),)), _LocalGet(name='y')))))),)

## grammar.method_decl('foo |whee| whee := 42. whee')
#. (('foo', _Block(receiver=None, env=None, code=_Code(params=(), locals=('whee',), expr=_Then(expr1=_LocalPut(name='whee', expr=_Constant(value=42)), expr2=_LocalGet(name='whee'))))),)
