"""
Based on http://chronos-st.blogspot.com/2007/12/smalltalk-in-one-page.html
"""

from parson import Grammar, hug, join
import terp

grammar = r"""
top = _ code ~/./.
other_top = method_decl ~/./.

method_decl = method_header code.
method_header = unary_selector :mk_unary_header
              | binary_selector bindable :mk_binary_header
              | (keyword bindable)+ :mk_keyword_header.

unary_selector = id ~':' _.
binary_selector = /([~!@%&*\-+=|\\<>,?\/]+)/_.
keyword = id /(:)/_ :join.

code = locals? :hug opt_stmts.
opt_stmts = stmts | :mk_self.
locals = '|'_ bindable* '|'_.

stmts = stmt ('.'_ stmt :mk_then)* ('.'_)?.

stmt = bindable ':='_ expr :mk_var_put
     | '^'_ expr :mk_return
     | expr.

expr = operand (m1 :mk_send (';'_ m1 :mk_cascade)*)?.
m1 = unary_selector m1? :mk_m1 | m2.
e1 = operand (unary_selector :mk_e1)*.
m2 = binary_selector e1 m2? :mk_m2 | m3.
e2 = e1 (binary_selector e1 :mk_e2)*.
m3 = (keyword e2)+ :mk_m3.

operand = block
        | literal
        | bindable :mk_var_get
        | '('_ stmt ')'_.

block = '['_ block_args? :hug code ']'_ :mk_block.
block_args = (':'_ bindable)* '|'_.

literal = constant_ref
        | /self\b/_   :mk_self
        | /super\b/_  :mk_super
        | /-?(\d+)/_  :mk_int  # XXX add base-r literals, floats, and scaled decimals
        | string_literal :mk_string
        | '#' nested_array.

constant_ref = /nil\b/_    :mk_nil
             | /false\b/_  :mk_false
             | /true\b/_   :mk_true.

string_literal = /'/ qchar* /'/_  :join.
qchar = /'(')/ | /([^'])/.

nested_array = '('_ array_element* ')'_ :mk_array.
array_element = literal | nested_array.

id = /([A-Za-z]\w*)/.
bindable = ~reserved id _.
reserved = constant_ref | /self\b/_ | /super\b/_.

_ = (/\s/ | comment)*.
comment = /"[^"]*"/.
"""

mk_unary_header   = lambda selector: (selector, ())
mk_binary_header  = lambda selector, param: (selector, (param,))
mk_keyword_header = lambda *args: (''.join(args[::2]), args[1::2])

mk_nil    = lambda: terp.Constant(None)
mk_false  = lambda: terp.Constant(False)
mk_true   = lambda: terp.Constant(True)
mk_self   = terp.Self
mk_super  = lambda: XXX
mk_int    = lambda s: terp.Constant(int(s))
mk_string = lambda s: terp.Constant(s)

mk_var_get = terp.VarGet
mk_var_put = terp.VarPut

mk_block = terp.BlockLiteral

mk_then = terp.Then

mk_return = lambda e: XXX
mk_array  = lambda *literals: XXX

def mk_cascade(operand, m1):
    send = m1(operand)
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

sg = Grammar(grammar)(**globals())

## sg.code('2 + 3 negate')
#. ((), _Send(subject=_Constant(value=2), selector='+', operands=(_Send(subject=_Constant(value=3), selector='negate', operands=()),)))

## sg.code('a b; c; d')
#. ((), _Cascade(subject=_Cascade(subject=_Send(subject=_VarGet(name='a'), selector='b', operands=()), selector='c', operands=()), selector='d', operands=()))

## sg.top("2")
#. ((), _Constant(value=2))
## sg.top("'hi'")
#. ((), _Constant(value='hi'))

## sg.method_decl('+ n\nmyValue + n')
#. (('+', ('n',)), (), _Send(subject=_VarGet(name='myValue'), selector='+', operands=(_VarGet(name='n'),)))
## sg.method_decl('hurray  "comment" [42] if: true else: [137]')
#. (('hurray', ()), (), _Send(subject=_BlockLiteral(params=(), locals=(), expr=_Constant(value=42)), selector='if:else:', operands=(_Constant(value=True), _BlockLiteral(params=(), locals=(), expr=_Constant(value=137)))))
## sg.method_decl("at: x put: y   myTable at: '$'+x put: y")
#. (('at:put:', ('x', 'y')), (), _Send(subject=_VarGet(name='myTable'), selector='at:put:', operands=(_Send(subject=_Constant(value='$'), selector='+', operands=(_VarGet(name='x'),)), _VarGet(name='y'))))

## sg.method_decl('foo |whee| whee := 42. whee')
#. (('foo', ()), ('whee',), _Then(expr1=_VarPut(name='whee', expr=_Constant(value=42)), expr2=_VarGet(name='whee')))


(selector, params), lvars, body = sg.method_decl("""factorial: n
0 = n
    ifTrue: [1]
    ifFalse: [n * (self factorial: n-1)]
""")

terp.global_env['Factorial'] = terp.Class({selector: terp.Method(params, lvars, body)}, ())

lvars, body = sg.top("Factorial new factorial: 5")
factorial = terp.Block(None, terp.Env({}, None), (), lvars, body)
try_factorial = (5, (), terp.final_k), factorial
## terp.trampoline(*try_factorial)
#. 120
