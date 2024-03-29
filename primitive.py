"""
Primitive data types
"""
from __future__ import division
import itertools
from collections import namedtuple

from core import call, class_from_type

class Thing(namedtuple('_Thing', 'class_ data')):
    def get(self, key):
        return self.data[self.class_.slot_index[key]]
    def put(self, key, value):
        self.data[self.class_.slot_index[key]] = value
    def __repr__(self):
        return '%r(%s)' % (self.class_,
                           ', '.join(map(repr, self.data)))

class Class(namedtuple('_Class', 'methods slots')): # TODO a name slot too?
    class_ = None  # (stub, filled in below)
    def __init__(self, methods, slots):
        self.slot_index = dict(zip(slots, range(len(slots))))
    def get_method(self, selector):
        try:
            return self.methods[selector]
        except KeyError:
            assert False, "Method %r unknown by %r" % (selector, self)
    def put_method(self, selector, method):
        self.methods[selector] = method
    def make(self):
        return Thing(self, [None] * len(self.slots))
    def next_method(self, selector, reverse=False):
        if selector not in self.methods:
            name = min(self.methods or (None,))
        else:
            keys = sorted(self.methods.keys())
            if reverse: keys.reverse()
            name = cyclic_next(selector, keys)
        return (None, None) if name is None else (name, self.methods[name])
    def __repr__(self):
        import terp
        name = terp.global_env.find_value(self)
        if name is not None: return name
        return '<<Class %s | %s>>' % (' '.join(self.slots),
                                      self.methods)

def new_method(receiver, arguments, k):
    return k, receiver.make()

Class.class_ = Class(dict(new=new_method), ())

def cyclic_next(key, lot):
    it = itertools.cycle(lot)
    for x in it:
        if key == x:
            result = next(it)
            return result
        
true_class = Class({}, ())   # Filled in at startup
false_class = Class({}, ())  # ditto

primitive_method_class = Class({}, ())  # TODO: fill this in

def find_default(rcvr, (other, default), k):
    try:
        return k, rcvr.index(other)
    except ValueError:
        return call(default, 'value', (), k)

def has(rcvr, (other,), k):  return (k, other in rcvr)
def at(rcvr, (i,), k):       return (k, rcvr[i])
def find(rcvr, (other,), k): return (k, rcvr.index(other))
def size(rcvr, _, k):        return (k, len(rcvr))
def add(rcvr, (other,), k):  return (k, rcvr + other)
def mul(rcvr, (other,), k):  return (k, rcvr * other)
def eq(rcvr, (other,), k):   return (k, rcvr == other)
def lt(rcvr, (other,), k):   return (k, rcvr < other)
def gt(rcvr, (other,), k):   return (k, rcvr > other)

def myself(rcvr, args, k):   return (k, rcvr)
def to_string(rcvr, args, k): return (k, str(rcvr))
def to_number(rcvr, args, k): return (k, number_from_string(rcvr))
def join(rcvr, (other,), k): return (k, rcvr.join(other))

def number_from_string(s):
    try:
        return int(s)
    except ValueError:
        return float(s)

str_types = (str, unicode)

string_methods = {
    'has:':  has,
    'at:':   at,
    'find:': find,
    'find:default:': find_default,
    'size':  size,
    '++':    add,
    '*':     mul,
    '=':     eq,
    '<':     lt,
    '>':     gt,
    'join:': join,
    'string': myself,
    'number': to_number,
}
string_class = Class(string_methods, ())
class_from_type[str] = string_class
class_from_type[unicode] = string_class

def array_append(receiver, (arg,), k):
    receiver.append(arg)
    return k, None

def at_put(rcvr, (i,value), k):
    rcvr[i] = value
    return (k, None)

array_methods = {
    'has:':  has,
    'at:':   at,
    'at:put:': at_put,
    'find:': find,
    'find:default:': find_default,
    'size':  size,
    '++':    add,
    '*':     mul,
    '=':     eq,
    '<':     lt,
    '>':     gt,
    'append:': array_append,
}
array_class = Class(array_methods, ())
class_from_type[list] = array_class

nil_methods = {}
nil_class = Class(nil_methods, ())
class_from_type[type(None)] = nil_class

num_types = (int, long, float)

def as_number(thing):
    if isinstance(thing, num_types):
        return thing
    assert False, "Not a number: %r" % (thing,)

num_methods = {
    '+': lambda rcvr, (other,), k: (k, rcvr + as_number(other)),
    '-': lambda rcvr, (other,), k: (k, rcvr - as_number(other)),
    '*': lambda rcvr, (other,), k: (k, rcvr * as_number(other)),
    '/': lambda rcvr, (other,), k: (k, rcvr / as_number(other)),
    '%': lambda rcvr, (other,), k: (k, rcvr % as_number(other)),
    '=': eq,
    '<': lt,
    '>': gt,
    'string': to_string,
    'number': myself,
}
num_class = Class(num_methods, ())
for nt in num_types:
    class_from_type[nt] = num_class
