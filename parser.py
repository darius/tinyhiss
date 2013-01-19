"""
Based on http://chronos-st.blogspot.com/2007/12/smalltalk-in-one-page.html
"""

from parson import Grammar

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

code = locals? stmts?.

locals = '|'_ bindable* '|'_.

stmts = stmt ('.'_ stmt)* ('.'_)?.

stmt = bindable ':='_ expr
     | '^'_ expr
     | expr.

expr = operand m1 (';'_ m1)*.
m1 = unary_selector m1? | m2.
e1 = operand unary_selector*.
m2 = binary_selector e1 m2? | m3.
e2 = e1 (binary_selector e1)*.
m3 = (keyword e2)+.

operand = block | literal | bindable | '('_ stmt ')'_.

block = '['_ block_args? code ']'_.
block_args = (':'_ bindable)* '|'_.

literal = constant_ref
        | /self\b/_ | /super\b/_
        | /-?(\d+)/_    # XXX add base-r literals, floats, and scaled decimals
        | '$' /(.)/_    # char literal
        | string_literal
        | '#['_ (/(\d+)/_)* ']'_
        | '#' nested_array
        | '#'_ (symbol_in_array | constant_ref | string_literal).

constant_ref = /nil\b/_ | /false\b/_ | /true\b/_.

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

sg = Grammar(grammar)()
## sg.code('2 + 3 negate')
#. ('2', '+', '3', 'negate')
