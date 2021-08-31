"""
Based on http://chronos-st.blogspot.com/2007/12/smalltalk-in-one-page.html
"""

from parson import Grammar
import terp
from primitive import number_from_string

# This is an unusual grammar in that Parson's "keyword" syntax would
# do the wrong thing, because identifiers can include dashes. Instead
# we use negative lookahead rather often, and disable fnords with ~:
# rather often.
grammar_text = r"""
top_code    :  '' code :end.
top_method  :  method_decl :end.

method_decl :  method_header code :mk_method.
method_header: unary_selector :mk_unary_header
            |  binary_selector name :mk_binary_header
            |  (keyword name)+ :mk_keyword_header.

keyword         :  id /(:)/ :join.
unary_selector ~:  id !':' _.
binary_selector :  /([~!@%&*\-+=|\\<>,?\/]+)/.

code        :  locals? :hug opt_stmts.
locals      :  '|' name* '|'.
opt_stmts   :  stmts | :mk_nil.
stmts       :  stmt ('.' stmt :mk_then)* '.'?.

stmt        :  my name ':=' expr :mk_slot_put
            |     name ':=' expr :mk_local_put
            |  '^' expr :mk_return
            |  expr.

expr        :  operand (m1 :mk_send (';' m1 :mk_cascade)*)?.
m1          :  unary_selector m1? :mk_m1 | m2.
e1          :  operand (unary_selector :mk_e1)*.
m2          :  binary_selector e1 m2? :mk_m2 | m3.
e2          :  e1 (binary_selector e1 :mk_e2)*.
m3          :  (keyword e2)+ :mk_m3.

operand     :  block
            |  reserved
            |  my name            :mk_slot_get
            |  name               :mk_var_get
            |  /(-?\d+(?:[.]\d+)?(?:e\d+)?)/ :mk_num  # TODO add base-r literals, floats, and scaled decimals
            |  string_literal     :mk_string
            |  '(' stmt ')'
            |  '[' expr**'.' '.'? ']' :hug :mk_array.

block       :  '{' block_args? :hug code '}' :mk_block.
block_args  :  (':' name)+ '|'.

reserved   ~:  'nil'   !idchar _  :mk_nil
            |  'false' !idchar _  :mk_false
            |  'true'  !idchar _  :mk_true
            |  'I'     !idchar _  :mk_self
            |  'me'    !idchar _  :mk_self.

my         ~:  'my' whitespace+.

name       ~:  !(reserved | 'my' !idchar) id _.

id         ~:  /([A-Za-z][_A-Za-z0-9-]*)/.   # XXX could restrict the dashes some more
idchar     ~:           /[_A-Za-z0-9-]/.

string_literal
           ~:  /'/ qchar* /'/ _  :join.
qchar      ~:  /'(')/ | /([^'])/.

_          ~:  whitespace*.
whitespace ~:  /\s/ | comment | '###' :anyone*.
comment    ~:  /--[>|\s][^\n]*/.

FNORD      ~:  whitespace*.
"""

mk_unary_header   = lambda selector: (selector, ())
mk_binary_header  = lambda selector, param: (selector, (param,))
mk_keyword_header = lambda *args: (''.join(args[::2]), args[1::2])

def mk_method((selector, params), localvars, expr):
    return selector, terp.make_method(params, localvars, expr)

mk_nil    = lambda: terp.Constant(None)
mk_false  = lambda: terp.Constant(False)
mk_true   = lambda: terp.Constant(True)
mk_self   = terp.Self
mk_num    = lambda s: terp.Constant(number_from_string(s))
mk_string = lambda s: terp.Constant(s)

mk_slot_get = terp.SlotGet
mk_slot_put = terp.SlotPut

mk_array = terp.MakeArray

def mk_var_get(name):
    return terp.GlobalGet(name) if name[:1].isupper() else terp.LocalGet(name)

def mk_local_put(name, expr):
    assert not name[:1].isupper(), "Local variables must be lowercase"
    return terp.LocalPut(name, expr)

mk_block = terp.Code

mk_then = terp.Then

mk_return = lambda e: XXX

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

def parse_code(text):
    localvars, body = grammar.top_code(text)
    return terp.Code((), localvars, body)

## grammar.code('2 + 3 negate')
#. ((), (2 + (3 negate)))

## grammar.code('a b; c; d')
#. ((), (((a b); c); d))

## grammar.top_code("2")
#. ((), 2)
## grammar.top_code("'hi'")
#. ((), 'hi')

## grammar.method_decl('+ n\nmyValue + n')
#. (('+', {:n | (myValue + n)}),)
## grammar.method_decl('hurray  -- comment\n {42} if: true else: {137}')
#. (('hurray', {({42} if: True else: {137})}),)
## grammar.method_decl("at: x put: y   myTable at: '$'+x put: y")
#. (('at:put:', {:x :y | (myTable at: ('$' + x) put: y)}),)

## grammar.method_decl('foo |whee| whee := 42. whee')
#. (('foo', {|whee| whee <- 42. whee}),)
