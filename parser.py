"""
Based on http://chronos-st.blogspot.com/2007/12/smalltalk-in-one-page.html
"""

from parson import Grammar, hug
import terp

grammar = r"""
top = _ code.
other_top = method_decl.

method_decl = method_header code.
method_header = unary_selector
              | binary_selector bindable
              | (keyword id)+.

unary_selector = id ~':'.
binary_selector = /([~!@%&*\-+=|\\<>,?\/]+)/_.
keyword = id ':'_.

code = locals? :hug opt_stmts.
opt_stmts = stmts | :mk_self.
locals = '|'_ bindable* '|'_.

stmts = stmt ('.'_ stmt)* ('.'_)?.  # XXXsemantics

stmt = bindable ':='_ expr :mk_var_set
     | '^'_ expr  # XXXsemantics
     | expr.

expr = operand m1 (';'_ m1)*  :mk_cascade.
m1 = unary_selector m1? :mk_m1 | m2.
e1 = operand unary_selector* :mk_e1.
m2 = binary_selector e1 m2? :mk_m2 | m3.
e2 = e1 (binary_selector e1)* :mk_e2.
m3 = (keyword e2)+ :mk_m3.

operand = block
        | literal
        | bindable :mk_var_ref
        | '('_ stmt ')'_.

block = '['_ block_args? :hug code ']'_ :mk_block.
block_args = (':'_ bindable)* '|'_.

literal = constant_ref
        | /self\b/_   :mk_self
        | /super\b/_  # XXXsemantics
        | /-?(\d+)/_  :mk_int  # XXX add base-r literals, floats, and scaled decimals
        | '$' /(.)/_  # XXXsemantics  # char literal
        | string_literal          # XXXsemantics
        | '#['_ (/(\d+)/_)* ']'_  # XXXsemantics
        | '#' nested_array        # XXXsemantics
        | '#'_ (symbol_in_array | constant_ref | string_literal). # XXXsemantics

constant_ref = /nil\b/_    :mk_nil
             | /false\b/_  :mk_false
             | /true\b/_   :mk_true.

string_literal = /'/ qchar* /'/_.
qchar = /'(')/ | /([^'])/.

nested_array = '('_ array_element* ')'_.
array_element = literal | nested_array | constant_ref | symbol_in_array.

symbol_in_array = ~constant_ref unary_selector | keyword | binary_selector.

id = /([A-Za-z]\w*)/_.
bindable = ~reserved id.
reserved = constant_ref | /self\b/_ | /super\b/_.

_ = (/\s/ | comment)*.
comment = /"[^"]*"/.
"""

mk_nil   = lambda: terp.Constant(None)
mk_false = lambda: terp.Constant(False)
mk_true  = lambda: terp.Constant(True)
mk_self  = terp.Self
mk_int   = lambda s: terp.Constant(int(s))

mk_var_ref = lambda s: terp.LocalGet(s) # XXX too specific
mk_var_set = lambda s, expr: terp.LocalGet(s, expr) # XXX too specific

mk_block = terp.BlockLiteral

def mk_cascade(operand, m1, *ms):
    assert not ms               # XXX
    print operand
    print m1
    return m1(operand)

def mk_m1(selector, opt_m1=None):
    assert opt_m1 is None       # XXX
    return lambda operand: terp.Send(operand, selector, ())

def mk_e1(operand, *selectors):
    for selector in selectors:
        operand = terp.Send(operand, selector, ())
    return operand

def mk_m2(selector, e1, opt_m2=None):
    assert opt_m2 is None       # XXX
    return lambda operand: terp.Send(operand, selector, (e1,))

def mk_e2(operand, *args):
    for selector, arg in zip(selectors[::2], selectors[1::2]):
        operand = terp.Send(operand, selector, (arg,))
    return operand

def mk_m3(*args):
    selector = ''.join(args[::2])
    rands = args[1::2]
    return lambda operand: terp.Send(operand, selector, rands)

sg = Grammar(grammar)(**globals())
## sg.code('2 + 3 negate')
#. _Constant(value=2)
#. <function <lambda> at 0xffe328b4>
#. 
#. ((), _Send(subject=_Constant(value=2), selector='+', operands=(_Send(subject=_Constant(value=3), selector='negate', operands=()),)))
